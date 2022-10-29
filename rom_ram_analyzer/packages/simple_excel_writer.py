import xlwt
from xlwt import Worksheet
import typing
from typing import Optional
from collections.abc import Iterable


class SimpleExcelWriter:
    def __init__(self, default_sheet_name: str = "sheet1"):
        self.__book = xlwt.Workbook(encoding='utf-8', style_compression=0)
        self.__sheet_dict = {
            default_sheet_name: self.__book.add_sheet(
                sheetname=default_sheet_name, cell_overwrite_ok=True)
        }
        self.__sheet_pos = {
            default_sheet_name: (0, 0)  # 记录各个sheet页已经写到什么位置了，当前值为还没有写的
        }
        self.__default_sheet_name = default_sheet_name
        # 表头样式
        self.__head_style = xlwt.XFStyle()
        # 内容样式
        self.__content_style = xlwt.XFStyle()
        # 字体
        font = xlwt.Font()
        font.bold = True

        # 居中对齐
        alignment = xlwt.Alignment()
        alignment.horz = xlwt.Alignment.HORZ_CENTER  # 水平方向
        alignment.vert = xlwt.Alignment.VERT_CENTER  # 垂直方向

        # 设置背景颜色
        pattern = xlwt.Pattern()
        pattern.pattern = xlwt.Pattern.SOLID_PATTERN
        pattern.pattern_fore_colour = 22  # 背景颜色

        self.__head_style.font = font
        self.__head_style.alignment = alignment
        self.__head_style.pattern = pattern
        self.__content_style.alignment = alignment

    def __increment_y(self, sheet_name: str, value: int = 1) -> int:
        if sheet_name in self.__sheet_pos.keys():
            x, y = self.__sheet_pos.get(sheet_name)
            y = y + value
            self.__sheet_pos[sheet_name] = (x, y)
            return y

    def __increment_x(self, sheet_name: str, value: int = 1) -> int:
        if sheet_name in self.__sheet_pos.keys():
            x, y = self.__sheet_pos.get(sheet_name)
            x = x + value
            self.__sheet_pos[sheet_name] = (x, 0)
            return x

    def append_line(self, content: list, sheet_name: str = None):
        sheet_name = self.__default_sheet_name if sheet_name is None else sheet_name
        if sheet_name not in self.__sheet_dict.keys():
            print("error: sheet name '{}' not exist".format(sheet_name))
            return
        sheet: Worksheet = self.__sheet_dict.get(sheet_name)
        x, y = self.__sheet_pos.get(sheet_name)
        for ele in content:
            sheet.write(x, y, ele, style=self.__content_style)
            y = self.__increment_y(sheet_name)
        self.__increment_x(sheet_name)

    def write_merge(self, x0: int, y0: int, x1: int, y1: int, content: typing.Any,
                    sheet_name: str = None):
        sheet_name = self.__default_sheet_name if sheet_name is None else sheet_name
        if sheet_name not in self.__sheet_dict.keys():
            print("error: sheet name '{}' not exist".format(sheet_name))
            return
        sheet: Worksheet = self.__sheet_dict.get(sheet_name)
        sheet.write_merge(x0, x1, y0, y1, content, style=self.__content_style)

    def set_sheet_header(self, headers: Iterable, sheet_name: str = None):
        """
        给sheet页设置表头
        """
        sheet_name = self.__default_sheet_name if sheet_name is None else sheet_name
        if sheet_name not in self.__sheet_dict.keys():
            print("error: sheet name '{}' not exist".format(sheet_name))
            return
        x, y = self.__sheet_pos.get(sheet_name)
        if x != 0 or y != 0:
            print(
                "error: pos of sheet '{}' is not (0,0). set_sheet_header must before write".format(sheet_name))
            return
        sheet: Worksheet = self.__sheet_dict.get(sheet_name)
        for h in headers:
            sheet.write(x, y, h, self.__head_style)
            y = self.__increment_y(sheet_name)
        self.__increment_x(sheet_name)

    def add_sheet(self, sheet_name: str, cell_overwrite_ok=True) -> Optional[xlwt.Worksheet]:
        if sheet_name in self.__sheet_dict.keys():
            print("error: sheet name '{}' has exist".format(sheet_name))
            return
        self.__sheet_dict[sheet_name] = self.__book.add_sheet(
            sheetname=sheet_name, cell_overwrite_ok=cell_overwrite_ok)
        self.__sheet_pos[sheet_name] = (0, 0)
        return self.__sheet_dict.get(sheet_name)

    def save(self, file_name: str):
        self.__book.save(file_name)


if __name__ == '__main__':
    writer = SimpleExcelWriter(default_sheet_name="first")
    writer.add_sheet("second")
    writer.add_sheet("third")
    writer.set_sheet_header(["h", "m", "n"])
    writer.append_line([1, 2, 3])
    writer.append_line([2, 3, 4], "second")
    writer.append_line([3, 4, 5], "third")
    writer.append_line([3, 2, 1])
    writer.save("demo.xls")
