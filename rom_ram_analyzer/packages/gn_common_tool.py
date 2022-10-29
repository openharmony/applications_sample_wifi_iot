import os
import json


class GnCommonTool:
    """
    处理BUILD.gn文件的通用方法
    """

    @classmethod
    def is_gn_variable(cls, target: str, has_quote: bool = True):
        """
        判断target是否是gn中的变量:
        规则：如果是有引号的模式，则没有引号均认为是变量，有引号的情况下，如有是"$xxx"的模式，则认为xxx是变量；如果是无引号模式，则只要$开头就认为是变量
        b = "xxx"
        c = b
        c = "${b}"
        "$p"
        """
        target = target.strip()
        if not has_quote:
            return target.startswith("$")
        if target.startswith('"') and target.endswith('"'):
            target = target.strip('"')
            if target.startswith("${") and target.endswith("}"):
                return True
            elif target.startswith("$"):
                return True
            return False
        else:
            return True

    # 给__find_variables_in_gn用的，减少io
    __var_val_mem_dict = dict()

    @classmethod
    def find_variables_in_gn(cls, var_name_tuple: tuple, path: str, stop_tail: str = "home") -> tuple:
        """
        同时查找多个gn变量的值
        var_name_tuple：变量名的tuple，变量名应是未经过处理后的，如：
        xxx
        "${xxx}"
        "$xxx"
        """

        if os.path.isfile(path):
            path = os.path.split(path)[0]
        var_val_dict = dict()
        not_found_count = len(var_name_tuple)
        for var in var_name_tuple:
            val = GnCommonTool.__var_val_mem_dict.get(var)
            if val is not None:
                not_found_count -= 1
            var_val_dict[var] = val
        while not path.endswith(stop_tail) and not_found_count != 0:
            for v in var_name_tuple:
                cmd = r"grep -Ern '^( *){} *= *\".*?\"' --include=*.gn* {}| grep -Ev '\$' | head -n 1 | grep -E '\".*\"' -wo".format(
                    v.strip('"').lstrip("${").rstrip('}'), path)
                output = os.popen(cmd).read().strip().strip('"')
                if len(output) != 0:
                    not_found_count -= 1
                    var_val_dict[v] = output
                    GnCommonTool.__var_val_mem_dict[v] = output
            path = os.path.split(path)[0]
        return tuple(var_val_dict.values())

    @classmethod
    def __find_part_subsystem_from_bundle(cls, gnpath: str, stop_tail: str = "home") -> tuple:
        """
        根据BUILD.gn的全路径，一层层往上面查找bundle.json文件，
        并从bundle.json中查找part_name和subsystem
        """
        filename = "bundle.json"
        part_name = None
        subsystem_name = None
        if stop_tail not in gnpath:
            return part_name, subsystem_name
        if os.path.isfile(gnpath):
            gnpath = os.path.split(gnpath)[0]
        while not gnpath.endswith(stop_tail):
            bundle_path = os.path.join(gnpath, filename)
            if not os.path.isfile(bundle_path):  # 如果该文件不在该目录下
                gnpath = os.path.split(gnpath)[0]
                continue
            with open(bundle_path, 'r', encoding='utf-8') as f:
                content = json.load(f)
                try:
                    part_name = content["component"]["name"]
                    subsystem_name = content["component"]["subsystem"]
                except KeyError:
                    ...
                finally:
                    break
        part_name = None if (part_name is not None and len(
            part_name) == 0) else part_name
        subsystem_name = None if (subsystem_name is not None and len(
            subsystem_name) == 0) else subsystem_name
        return part_name, subsystem_name

    @classmethod
    def find_part_subsystem(cls, gn_file: str, project_path: str) -> tuple:
        """
        查找gn_file对应的part_name和subsystem
        如果在gn中找不到，就到bundle.json中去找
        """
        part_name = None
        subsystem_name = None
        part_var_flag = False  # 标识这个变量从gn中取出的原始值是不是变量
        subsystem_var_flag = False
        var_list = list()
        part_name_pattern = r"part_name *=\s*\S*"
        subsystem_pattern = r"subsystem_name *=\s*\S*"
        meta_grep_pattern = "grep -E '{}' {} | head -n 1"
        part_cmd = meta_grep_pattern.format(part_name_pattern, gn_file)
        subsystem_cmd = meta_grep_pattern.format(subsystem_pattern, gn_file)
        part = os.popen(part_cmd).read().strip()
        if len(part) != 0:
            part = part.split('=')[-1].strip()
            if GnCommonTool.is_gn_variable(part):
                part_var_flag = True
                var_list.append(part)
            else:
                part_name = part.strip('"')
                if len(part_name) == 0:
                    part_name = None
        subsystem = os.popen(subsystem_cmd).read().strip()
        if len(subsystem) != 0:  # 这里是只是看有没有grep到关键字
            subsystem = subsystem.split('=')[-1].strip()
            if GnCommonTool.is_gn_variable(subsystem):
                subsystem_var_flag = True
                var_list.append(subsystem)
            else:
                subsystem_name = subsystem.strip('"')
                if len(subsystem_name) == 0:
                    subsystem_name = None
        if part_var_flag and subsystem_var_flag:
            part_name, subsystem_name = GnCommonTool.find_variables_in_gn(
                tuple(var_list), gn_file, project_path)
        elif part_var_flag:
            t = GnCommonTool.find_variables_in_gn(
                tuple(var_list), gn_file, project_path)[0]
            part_name = t if t is not None and len(t) != 0 else part_name
        elif subsystem_var_flag:
            t = GnCommonTool.find_variables_in_gn(
                tuple(var_list), gn_file, project_path)[0]
            subsystem_name = t if t is not None and len(
                t) != 0 else subsystem_name
        if part_name is not None and subsystem_name is not None:
            return part_name, subsystem_name
        # 如果有一个没有找到，就要一层层去找bundle.json文件
        t_part_name, t_subsystem_name = cls.__find_part_subsystem_from_bundle(
            gn_file, stop_tail=project_path)
        if t_part_name is not None:
            part_name = t_part_name
        if t_subsystem_name is not None:
            subsystem_name = t_subsystem_name
        return part_name, subsystem_name
