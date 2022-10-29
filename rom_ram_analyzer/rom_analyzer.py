import argparse
import json
import os
import sys
import typing
from copy import deepcopy
from typing import *

from packages.basic_tool import BasicTool
from packages.gn_common_tool import GnCommonTool
from packages.simple_excel_writer import SimpleExcelWriter

debug = bool(sys.gettrace())


class RomAnalyzer:
    @classmethod
    def __collect_product_info(cls, system_module_info_json: Text,
                               project_path: Text) -> Dict[Text, Dict[Text, Text]]:
        """
        根据system_module_info.json生成target字典
        """
        with open(system_module_info_json, 'r', encoding='utf-8') as f:
            product_list = json.loads(f.read())
        project_path = BasicTool.get_abs_path(project_path)
        product_info_dict: Dict[Text, Dict[Text, Text]] = dict()
        for unit in product_list:
            dest: List = unit.get("dest")
            if dest is None:
                print("warning: keyword 'dest' not found in {}".format(system_module_info_json))
                continue
            label: Text = unit.get("label")
            gn_path = component_name = subsystem_name = None
            if label:
                gn_path = os.path.join(project_path, label.split(':')[0].lstrip('/'), "BUILD.gn")
                component_name, subsystem_name = GnCommonTool.find_part_subsystem(gn_path, project_path)
            else:
                print("warning: keyword 'label' not found in {}".format(unit))
            for target in dest:
                product_info_dict[target] = {
                    "component_name": component_name,
                    "subsystem_name": subsystem_name,
                    "gn_path": gn_path,
                }
        return product_info_dict

    @classmethod
    def __save_result_as_excel(cls, result_dict: dict, output_name: str):
        header = ["subsystem_name", "component_name", "output_file", "size(Byte)"]
        tmp_dict = deepcopy(result_dict)
        excel_writer = SimpleExcelWriter("rom")
        excel_writer.set_sheet_header(headers=header)
        subsystem_start_row = 1
        subsystem_end_row = 0
        subsystem_col = 0
        component_start_row = 1
        component_end_row = 0
        component_col = 1

        for subsystem_name in tmp_dict.keys():
            subsystem_dict = tmp_dict.get(subsystem_name)
            subsystem_size = subsystem_dict.get("size")
            subsystem_file_count = subsystem_dict.get("file_count")
            del subsystem_dict["file_count"]
            del subsystem_dict["size"]
            subsystem_end_row += subsystem_file_count

            for component_name in subsystem_dict.keys():
                component_dict: Dict[str, int] = subsystem_dict.get(component_name)
                component_size = component_dict.get("size")
                component_file_count = component_dict.get("file_count")
                del component_dict["file_count"]
                del component_dict["size"]
                component_end_row += component_file_count

                for file_name, size in component_dict.items():
                    excel_writer.append_line(
                        [subsystem_name, component_name, file_name, size])
                excel_writer.write_merge(component_start_row, component_col, component_end_row, component_col,
                                         component_name)
                component_start_row = component_end_row + 1
            excel_writer.write_merge(subsystem_start_row, subsystem_col, subsystem_end_row, subsystem_col,
                                     subsystem_name)
            subsystem_start_row = subsystem_end_row + 1
        excel_writer.save(output_name + ".xls")

    @classmethod
    def __put(cls, unit: typing.Dict[Text, Any], result_dict: typing.Dict[Text, Dict]):
        """
        {
        subsystem_name:{
                component_name: {
                    file_name: file_size
                }
            }
        }
        """
        component_name = "others" if unit.get("component_name") is None else unit.get("component_name")
        subsystem_name = "others" if unit.get("subsystem_name") is None else unit.get("subsystem_name")
        size = unit.get("size")
        relative_filepath = unit.get("relative_filepath")
        if result_dict.get(subsystem_name) is None:
            result_dict[subsystem_name] = dict()
            result_dict[subsystem_name]["size"] = 0
            result_dict[subsystem_name]["file_count"] = 0

        if result_dict.get(subsystem_name).get(component_name) is None:
            result_dict[subsystem_name][component_name] = dict()
            result_dict[subsystem_name][component_name]["size"] = 0
            result_dict[subsystem_name][component_name]["file_count"] = 0
        result_dict[subsystem_name]["size"] += size
        result_dict[subsystem_name]["file_count"] += 1
        result_dict[subsystem_name][component_name]["size"] += size
        result_dict[subsystem_name][component_name]["file_count"] += 1
        result_dict[subsystem_name][component_name][relative_filepath] = size

    @classmethod
    def analysis(cls, system_module_info_json: Text, product_dirs: List[str],
                 project_path: Text, product_name: Text, output_file: Text, output_execel: bool):
        """
        system_module_info_json: json文件
        product_dirs：要处理的产物的路径列表如["vendor", "system/"]
        project_path: 项目根路径
        product_name: eg，rk3568
        output_file: basename of output file
        """
        project_path = BasicTool.get_abs_path(project_path)
        phone_dir = os.path.join(project_path, "out", product_name, "packages", "phone")
        product_dirs = [os.path.join(phone_dir, d) for d in product_dirs]
        product_info_dict = cls.__collect_product_info(system_module_info_json, project_path)  # 所有产物信息
        result_dict: Dict[Text:Dict] = dict()
        for d in product_dirs:
            file_list: List[Text] = BasicTool.find_all_files(d)
            for f in file_list:
                size = os.path.getsize(f)
                relative_filepath = f.replace(phone_dir, "").lstrip(os.sep)
                unit: Dict[Text, Any] = product_info_dict.get(relative_filepath)
                if unit is None:
                    unit = {
                        "relative_filepath": relative_filepath,
                    }
                unit["size"] = size
                unit["relative_filepath"] = relative_filepath
                cls.__put(unit, result_dict)
        output_dir, _ = os.path.split(output_file)
        if len(output_dir) != 0:
            os.makedirs(output_dir, exist_ok=True)
        with open(output_file + ".json", 'w', encoding='utf-8') as f:
            f.write(json.dumps(result_dict, indent=4))
        if output_execel:
            cls.__save_result_as_excel(result_dict, output_file)


def get_args():
    VERSION = 2.0
    parser = argparse.ArgumentParser(
        description=f"analyze rom size of component.\n")
    parser.add_argument("-v", "-version", action="version",
                        version=f"version {VERSION}")
    parser.add_argument("-p", "--project_path", type=str, required=True,
                        help="root path of openharmony. eg: -p ~/openharmony")
    parser.add_argument("-j", "--module_info_json", required=True, type=str,
                        help="path of out/{product_name}/packages/phone/system_module_info.json")
    parser.add_argument("-n", "--product_name", required=True, type=str, help="product name. eg: -n rk3568")
    parser.add_argument("-d", "--product_dir", required=True, action="append",
                        help="subdirectories of out/{product_name}/packages/phone to be counted."
                             "eg: -d system -d vendor")
    parser.add_argument("-o", "--output_file", type=str, default="rom_analysis_result",
                        help="basename of output file, default: rom_analysis_result. eg: demo/rom_analysis_result")
    parser.add_argument("-e", "--excel", type=bool, default=False,
                        help="if output result as excel, default: False. eg: -e True")
    args = parser.parse_args()
    return args


if __name__ == '__main__':
    args = get_args()
    module_info_json = args.module_info_json
    project_path = args.project_path
    product_name = args.product_name
    product_dirs = args.product_dir
    output_file = args.output_file
    output_excel = args.excel
    RomAnalyzer.analysis(module_info_json, product_dirs, project_path, product_name, output_file, output_excel)
