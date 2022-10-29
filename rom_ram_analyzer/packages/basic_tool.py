import sys
import typing
import os
from pathlib import Path
from typing import *


class BasicTool:
    @classmethod
    def find_all_files(cls, folder: str, real_path: bool = True, apply_abs: bool = True, de_duplicate: bool = True,
                       p_filter: typing.Callable = lambda x: True) -> list:
        filepath_list = set()
        for root, _, file_names in os.walk(folder):
            filepath_list.update(
                [os.path.abspath(os.path.realpath(
                    os.path.join(root, f) if real_path else os.path.join(root, f))) if apply_abs else os.path.relpath(
                    os.path.realpath(os.path.join(root, f) if real_path else os.path.join(root, f))) for f in file_names
                 if p_filter(os.path.join(root, f))])
        if de_duplicate:
            filepath_list = set(filepath_list)
        filepath_list = sorted(filepath_list, key=str.lower)
        return filepath_list

    @classmethod
    def get_abs_path(cls, path: str) -> str:
        return os.path.abspath(os.path.expanduser(path))


if __name__ == '__main__':
    # print(BasicTool.get_abs_path("~/git/.."))
    for i in BasicTool.find_all_files(".", apply_abs=False):
        print(i)