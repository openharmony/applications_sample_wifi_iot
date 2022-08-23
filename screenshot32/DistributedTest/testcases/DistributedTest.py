# -*- coding: utf-8 -*-
import time
from devicetest.core.test_case import TestCase
from devicetest.aw.OpenHarmony import CommonOH
import threading


class DistributedTest(TestCase):
    def __init__(self, controllers):
        self.TAG = self.__class__.__name__
        self.tests = [
            # 设备组网
            "sub_distributed_smoke_testcase_0100",
            # pin码连接
            "sub_distributed_smoke_testcase_0200",
            # 结果校验
            "sub_distributed_smoke_testcase_0300"
        ]
        TestCase.__init__(self, self.TAG, controllers)

    def setup(self):
        print("预置工作：初始化设备开始...........................")
        print(self.devices[0].device_id)
        print(self.devices[1].device_id)

    def sub_distributed_smoke_testcase_0100(self):
        t1 = threading.Thread(target=self.net_connect1)
        t2 = threading.Thread(target=self.net_connect2)
        t1.start()
        t2.start()
        t1.join()
        t2.join()

    def sub_distributed_smoke_testcase_0200(self):
        CommonOH.startAbility(self.Phone1, "ohos.samples.distributedcalc.MainAbility", "ohos.samples.distributedcalc")
        time.sleep(2)
        # 授权
        CommonOH.click(self.Phone1, 500, 706)
        CommonOH.click(self.Phone1, 500, 706)
        CommonOH.touchByType(self.Phone1, "image", index=1)
        CommonOH.touchByText(self.Phone1, "取消")
        CommonOH.touchByType(self.Phone1, "image", index=1)
        CommonOH.touchByType(self.Phone1, "input", index=1)
        time.sleep(1)
        #确定
        CommonOH.click(self.Phone2, 500, 620)
        CommonOH.click(self.Phone2, 500, 620)
        code = CommonOH.getTextByCondition(self.Phone2, "请在设备端输入链接码进行验证", relativePath="AFTER")
        CommonOH.inputTextByType(self.Phone1, "input", code)
        # 确定
        CommonOH.click(self.Phone1, 500, 690)
        CommonOH.click(self.Phone1, 500, 690)

    def sub_distributed_smoke_testcase_0300(self):
        # 切入后台，结束进程
        CommonOH.click(self.Phone1, 512, 1246)
        CommonOH.click(self.Phone1, 360, 1168)
        # 重启计算器应用
        CommonOH.startAbility(self.Phone1, "ohos.samples.distributedcalc.MainAbility", "ohos.samples.distributedcalc")
        time.sleep(2)
        # 拉起远端设备
        CommonOH.touchByType(self.Phone1, "image", index=1)
        CommonOH.touchByType(self.Phone1, "input", index=1)
        # 设备二授权
        time.sleep(2)
        CommonOH.click(self.Phone2, 500, 706)
        CommonOH.click(self.Phone2, 500, 706)
        # 校验远端计算器是否被拉起
        CommonOH.checkIfTextExist(self.Phone2, "计算器", pattern="EQUALS", expect=True)

    def net_connect1(self):
        # 点亮屏幕
        CommonOH.wake(self.Phone1)
        # 设置不息屏
        CommonOH.hdc_std(self.Phone1, 'shell "power-shell setmode 602"')
        # 设置 phone1 ip
        CommonOH.hdc_std(self.Phone1, "shell ifconfig eth0 192.168.0.1")

    def net_connect2(self):
        # 点亮屏幕
        CommonOH.wake(self.Phone2)
        # 设置不息屏
        CommonOH.hdc_std(self.Phone2, 'shell "power-shell setmode 602"')
        # 设置 phone1 ip
        CommonOH.hdc_std(self.Phone2, "shell ifconfig eth0 192.168.0.2")

    def teardown(self):
        # 切入后台，结束进程
        CommonOH.click(self.Phone1, 512, 1246)
        CommonOH.click(self.Phone2, 512, 1246)
        CommonOH.click(self.Phone1, 360, 1168)
        CommonOH.click(self.Phone2, 360, 1168)
