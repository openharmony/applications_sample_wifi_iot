import argparse
import copy
import glob
import json
import os
import re
import sys
import subprocess
import typing
import xml.dom.minidom as dom

from packages.simple_excel_writer import SimpleExcelWriter

debug = True if sys.gettrace() else False


class HDCTool:
    @classmethod
    def verify_hdc(cls, verify_str: str = "OpenHarmony") -> bool:
        """
        验证hdc是否可用
        True：可用
        False：不可用
        """
        cp = subprocess.run(["hdc"], capture_output=True)
        stdout = str(cp.stdout)
        stderr = str(cp.stderr)
        return verify_str in stdout or verify_str in stderr

    @classmethod
    def verify_device(cls, device_num: str) -> bool:
        """
        验证设备是否已经连接
        True：已连接
        False：未连接
        """
        cp = subprocess.run(["hdc", "list", "targets"], capture_output=True)
        stdout = str(cp.stdout)
        stderr = str(cp.stderr)
        return device_num in stderr or device_num in stdout

    __MODE = typing.Literal["stdout", "stderr"]

    @classmethod
    def exec(cls, args: list, output_from: __MODE = "stdout"):
        cp = subprocess.run(args, capture_output=True)
        if output_from == "stdout":
            return cp.stdout.decode()
        elif output_from == "stderr":
            return cp.stderr.decode()
        else:
            print("error: 'output_from' must be stdout or stdin")


def delete_values_from_dict(target_dict: typing.Dict, key_list: typing.Iterable):
    for k in key_list:
        if k not in target_dict.keys():
            continue
        del target_dict[k]


class RamAnalyzer:
    @classmethod
    def __hidumper_mem_line_process(cls, content: typing.Text) -> typing.List[typing.Text]:
        """
        将hidumper的拥有的数据行进行分割，得到
        [pid, name, pss, vss, rss, uss]格式的list
        """
        trival_pattern = re.compile(r"kB|\(.*\)(?#去除单位kB以及小括号内的任意数据，包括小括号)")
        content = re.sub(trival_pattern, "", content)
        blank_pattern = re.compile(r"\s+(?#匹配一个或多个空格)")
        return re.sub(blank_pattern, ' ', content.strip()).split()

    __SS_Mode = typing.Literal["Pss", "Vss", "Rss", "Uss"]  # 提示输入
    __ss_dict: typing.Dict[str, int] = {
        "Pss": 2,
        "Vss": 3,
        "Rss": 4,
        "Uss": 5
    }

    @classmethod
    def __parse_hidumper_mem(cls, content: typing.Text, device_num: str, ss: __SS_Mode = "Pss") -> typing.Dict[
        typing.Text, int]:
        """
        解析：hidumper --meme的结果
        返回{process_name: pss}形式的字典
        '248  	samgr              1464(0 in SwapPss) kB    15064 kB     6928 kB     1072 kB\r'
        """

        def find_full_process_name(hname: str) -> str:
            for lname in __process_name_list:
                if lname.startswith(hname):
                    return lname

        def process_ps_ef(content: str) -> list:
            line_list = content.strip().split("\n")[1:]
            process_name_list = list()
            for line in line_list:
                process_name = line.split()[7]
                if process_name.startswith('['):
                    # 内核进程
                    continue
                process_name_list.append(process_name)
            return process_name_list

        if ss not in cls.__ss_dict.keys():
            print("error: {} is not a valid parameter".format(ss))
            return dict()
        output = content.split('\n')
        process_pss_dict = dict()
        __process_name_list: typing.List[str] = process_ps_ef(
            HDCTool.exec(["hdc", "-t", device_num, "shell", "ps", "-ef"]))
        for line in output:
            if "Total Memory Usage by Size" in line:
                break
            if line.isspace():
                continue
            processed: typing.List[typing.Text] = cls.__hidumper_mem_line_process(line)
            if not processed[0].isnumeric():  # 如果第一列不是数字（pid），就过
                continue
            name = processed[1]  # 否则的话就取名字，和对应的size
            size = int(processed[cls.__ss_dict.get(ss)])
            process_pss_dict[find_full_process_name(name)] = size
        return process_pss_dict

    @classmethod
    def process_hidumper_info(cls, device_num: str, ss: __SS_Mode) -> typing.Dict[str, int]:
        """
        处理进程名与对应进程大小
        """

        def exec_once() -> typing.Dict[str, int]:
            stdout = HDCTool.exec(["hdc", "-t", device_num, "shell", "hidumper", "--mem"])
            name_size_dict = cls.__parse_hidumper_mem(stdout, device_num, ss)
            return name_size_dict

        if not HDCTool.verify_hdc():
            print("error: Command 'hdc' not found")
            return dict()
        if not HDCTool.verify_device(device_num):
            print("error: {} is inaccessible or not found".format(device_num))
            return dict()

        return exec_once()

    @classmethod
    def __parse_process_xml(cls, file_path: str, result_dict: typing.Dict[str, typing.List[str]]):
        """
        解析xml文件，结存存入 result_dict中，格式：{process_name: os_list}
        其中，so_list中是so的base_name
        """
        if not (os.path.isfile(file_path) and file_path.endswith(".xml")):
            print("warning: {} not exist or not a xml file".format(file_path))
            return
        doc = dom.parse(file_path)
        info = doc.getElementsByTagName("info")[0]
        process = info.getElementsByTagName("process")[0]
        process_name = process.childNodes[0].data
        result_dict[process_name] = list()
        libs = info.getElementsByTagName("loadlibs")[0].getElementsByTagName("libpath")
        for lib in libs:
            so = lib.childNodes[0].data
            result_dict.get(process_name).append(os.path.split(so)[-1])
            if debug:
                print(process_name, " ", so)

    @classmethod
    def get_elf_info_from_rom_result(cls, rom_result_json: str) -> typing.Dict[str, typing.Dict[str, str]]:
        """
        利用rom_analyzer.py的分析结果，重组成
        {file_base_name: {"subsystem_name":subsystem_name, "component_name":component_name}}
        的形式
        """
        with open(rom_result_json, 'r', encoding='utf-8') as f:
            rom_info_dict = json.load(f)
        elf_info_dict: typing.Dict[str, typing.Dict[str, str]] = dict()
        for subsystem_name in rom_info_dict.keys():
            sub_val_dict: typing.Dict[str, typing.Any] = rom_info_dict.get(subsystem_name)
            delete_values_from_dict(sub_val_dict, ["size", "file_count"])
            for component_name in sub_val_dict.keys():
                component_val_dict: typing.Dict[str, str] = sub_val_dict.get(component_name)
                delete_values_from_dict(component_val_dict, ["size", "file_count"])
                for file_name, size in component_val_dict.items():
                    file_basename: str = os.path.split(file_name)[-1]
                    elf_info_dict[file_basename] = {
                        "subsystem_name": subsystem_name,
                        "component_name": component_name,
                        "size": size
                    }
        return elf_info_dict

    @classmethod
    def __parse_process_cfg(cls, cfg_path: str, profile_path: str, result_dict: dict):
        """
        解析cfg，因为有的cfg会拉起xml中的进程，所以也可能会去解析xml
        """
        with open(cfg_path, 'r', encoding='utf-8') as f:
            cfg_dict = json.loads(f.read())
        services = cfg_dict.get("services")
        if services is None:
            print("warning: 'services' not in {}".format(cfg_path))
            return
        for service in services:
            process_name = service.get("name")
            first, *path_list = service.get("path")
            if first.endswith("sa_main"):
                # 由sa_main去来起进程
                xml_base_name = os.path.split(path_list[0])[-1]
                cls.__parse_process_xml(os.path.join(profile_path, xml_base_name), result_dict)
            else:
                # 直接执行
                # process_name = os.path.split(first)[-1]
                if result_dict.get(process_name) is None:
                    result_dict[process_name] = list()
                result_dict.get(process_name).append(os.path.split(first)[-1])

    @classmethod
    def get_process_so_relationship(cls, xml_path: str, cfg_path: str, profile_path: str) -> typing.Dict[
        str, typing.List[str]]:
        """
        从out/{product_name}/packages/phone/sa_profile/merged_sa查找xml文件并处理得到进程与so的对应关系
        """
        # xml_path = os.path.join(product_path, "packages", "phone", "sa_profile", "merged_sa")
        # 从merged_sa里面收集
        xml_list = glob.glob(xml_path + os.sep + "*[.]xml", recursive=True)
        process_elf_dict: typing.Dict[str, typing.List[str]] = dict()
        for xml in xml_list:
            if debug:
                print("parsing: ", xml)
            try:
                cls.__parse_process_xml(xml, process_elf_dict)
            except:
                print("parse '{}' failed".format(xml))
            finally:
                ...
        # 从system/etc/init/*.cfg中收集，如果是sa_main拉起的，则从system/profile/*.xml中进行解析
        cfg_list = glob.glob(cfg_path + os.sep + "*[.]cfg", recursive=True)
        for cfg in cfg_list:
            if debug:
                print("parsing: ", cfg)
            try:
                cls.__parse_process_cfg(cfg, profile_path, process_elf_dict)
            except:
                print("parse '{}' failed".format(cfg))
            finally:
                ...
        return process_elf_dict

    @classmethod
    def __save_result_as_excel(cls, data_dict: dict, filename: str, ss: __SS_Mode):
        """
        保存结果到excel中
        """
        tmp_dict = copy.deepcopy(data_dict)
        writer = SimpleExcelWriter("ram_info")
        writer.set_sheet_header(
            ["process_name", "process_size({}, KB)".format(ss), "component_name", "elf_name", "elf_size(KB)"])
        process_start_r = 1
        process_end_r = 0
        process_c = 0
        process_size_c = 1
        component_start_r = 1
        component_end_r = 0
        component_c = 2
        for process_name in tmp_dict.keys():
            process_val_dict: typing.Dict[str, typing.Dict[str, int]] = tmp_dict.get(process_name)
            process_size = process_val_dict.get("size")
            delete_values_from_dict(process_val_dict, ["size"])
            for component_name, component_val_dict in process_val_dict.items():
                elf_count_of_component = len(component_val_dict)
                for elf_name, size in component_val_dict.items():
                    writer.append_line([process_name, process_size, component_name, elf_name, "%.2f" % (size / 1024)])
                component_end_r += elf_count_of_component
                # 重写component
                writer.write_merge(component_start_r, component_c, component_end_r,
                                   component_c, component_name)
                component_start_r = component_end_r + 1
                process_end_r += elf_count_of_component
            writer.write_merge(process_start_r, process_c, process_end_r, process_c, process_name)
            writer.write_merge(process_start_r, process_size_c, process_end_r, process_size_c, process_size)
            process_start_r = process_end_r + 1
        writer.save(filename)

    @classmethod
    def find_elf_size_from_rom_result(cls, service_name: str, subsystem_name: str, component_name: str,
                                      evaluator: typing.Callable, rom_result_dict: typing.Dict[str, typing.Dict]) -> \
            typing.Tuple[
                bool, str, str, int]:
        """
        全局查找进程的相关elf文件
        subsystem_name与component_name可明确指定，或为*以遍历整个dict
        evaluator：评估elf文件的从phone下面开始的路径与service_name的关系，评判如何才是找到了
        returns: 是否查找到，elf文件名，部件名，size
        """
        subsystem_name_list = [subsystem_name] if subsystem_name != "*" else rom_result_dict.keys()
        for sn in subsystem_name_list:
            sub_val_dict = rom_result_dict.get(sn)
            component_name_list = [component_name] if component_name != '*' else sub_val_dict.keys()
            for cn in component_name_list:
                if cn == "size" or cn == "file_count":
                    continue
                component_val_dict: typing.Dict[str, int] = sub_val_dict.get(cn)
                for k, v in component_val_dict.items():
                    if k == "size" or k == "file_count":
                        continue
                    if not evaluator(service_name, k):
                        continue
                    return True, os.path.split(k)[-1], cn, v
        return False, str(), str(), int()

    @classmethod
    def analysis(cls, cfg_path: str, xml_path: str, rom_result_json: str, device_num: str,
                 output_file: str, ss: __SS_Mode, output_excel: bool):
        """
        process size subsystem/component so so_size
        """
        if not HDCTool.verify_hdc():
            print("error: Command 'hdc' not found")
            return
        if not HDCTool.verify_device(device_num):
            print("error: {} is inaccessible or not found".format(device_num))
            return
        with open(rom_result_json, 'r', encoding='utf-8') as f:
            rom_result_dict: typing.Dict = json.loads(f.read())
        # 从rom的分析结果中将需要的elf信息重组
        so_info_dict: typing.Dict[
            str, typing.Dict[str["component_name|subsystem_name|size"], str]] = cls.get_elf_info_from_rom_result(
            rom_result_json)
        process_elf_dict: typing.Dict[str, typing.List[str]] = cls.get_process_so_relationship(xml_path, cfg_path,
                                                                                               profile_path)
        process_size_dict: typing.Dict[str, int] = cls.process_hidumper_info(device_num, ss)
        result_dict: typing.Dict[str, typing.Dict[str, typing.Any]] = dict()

        def get(key: typing.Any, dt: typing.Dict[str, typing.Any]):
            for k, v in dt.items():
                if k.startswith(key) or key == v[0]:
                    # 要么uinput_inject的对应key为mmi_uinput_inject。对于此类特殊处理，即：如果service_name找不到，但是直接执行的bin等于这个名字，也认为找到
                    return v

        for process_name, process_size in process_size_dict.items():  # 从进程出发
            if process_name == "init":
                _, bin, _, size = cls.find_elf_size_from_rom_result(process_name, "startup", "init",
                                                                    lambda x, y: os.path.split(y)[
                                                                                     -1].lower() == x.lower(),
                                                                    rom_result_dict)
                result_dict[process_name] = dict()
                result_dict[process_name]["size"] = process_size
                result_dict[process_name]["init"] = dict()
                result_dict[process_name]["init"][bin if len(bin) != 0 else "UNKOWN"] = size
                continue
            # 如果是hap，特殊处理
            if (process_name.startswith("com.") or process_name.startswith("ohos.")):
                _, hap_name, component_name, size = cls.find_elf_size_from_rom_result(process_name, "*", "*",
                                                                                      lambda x, y: len(
                                                                                          y.split(
                                                                                              '/')) >= 3 and x.lower().startswith(
                                                                                          y.split('/')[2].lower()),
                                                                                      rom_result_dict)
                result_dict[process_name] = dict()
                result_dict[process_name]["size"] = process_size
                result_dict[process_name][component_name] = dict()
                result_dict[process_name][component_name][hap_name if len(hap_name) != 0 else "UNKOWN"] = size
                continue
            so_list: list = get(process_name, process_elf_dict)  # 得到进程相关的elf文件list
            if so_list is None:
                print("warning: process '{}' not found in .xml or .cfg".format(process_name))
                result_dict[process_name] = dict()
                result_dict[process_name]["size"] = process_size
                result_dict[process_name]["UNKOWN"] = dict()
                result_dict[process_name]["UNKOWN"]["UNKOWN"] = int()
                continue
            result_dict[process_name] = dict()
            result_dict[process_name]["size"] = process_size
            for so in so_list:
                unit = so_info_dict.get(so)
                if unit is None:
                    print("warning: '{}' in {} not found in json from rom_analysis".format(so, process_name))
                    continue
                component_name = unit.get("component_name")
                so_size = unit.get("size")
                if result_dict.get(process_name).get(component_name) is None:
                    result_dict[process_name][component_name] = dict()
                result_dict[process_name][component_name][so] = so_size
        base_dir, _ = os.path.split(output_file)
        if len(base_dir) != 0 and not os.path.isdir(base_dir):
            os.makedirs(base_dir, exist_ok=True)
        with open(output_file + ".json", 'w', encoding='utf-8') as f:
            f.write(json.dumps(result_dict, indent=4))
        if output_excel:
            cls.__save_result_as_excel(result_dict, output_file + ".xls", ss)


def get_args():
    VERSION = 1.0
    parser = argparse.ArgumentParser(
        description="analyze ram size of component"
    )
    parser.add_argument("-v", "-version", action="version",
                        version=f"version {VERSION}")
    parser.add_argument("-x", "--xml_path", type=str, required=True,
                        help="path of xml file. eg: -x ~/openharmony/out/rk3568/packages/phone/system/profile")
    parser.add_argument("-c", "--cfg_path", type=str, required=True,
                        help="path of cfg files. eg: -c ./cfgs/")
    parser.add_argument("-j", "--rom_result", type=str, default="./rom_analysis_result.json",
                        help="json file produced by rom_analyzer_v1.0.py, default: ./rom_analysis_result.json."
                             "eg: -j ./demo/rom_analysis_result.json")
    parser.add_argument("-n", "--device_num", type=str, required=True,
                        help="device number to be collect hidumper info. eg: -n 7001005458323933328a01fce16d3800")
    parser.add_argument("-o", "--output_filename", default="ram_analysis_result", type=str,
                        help="base name of output file, default: rom_analysis_result. eg: -o ram_analysis_result")
    parser.add_argument("-e", "--excel", type=bool, default=False,
                        help="if output result as excel, default: False. eg: -e True")
    args = parser.parse_args()
    return args


if __name__ == '__main__':
    args = get_args()
    cfg_path = args.cfg_path
    profile_path = args.xml_path
    rom_result = args.rom_result
    device_num = args.device_num
    output_filename = args.output_filename
    output_excel = args.excel
    RamAnalyzer.analysis(cfg_path, profile_path, rom_result,
                         device_num=device_num, output_file=output_filename, ss="Pss", output_excel=output_excel)
