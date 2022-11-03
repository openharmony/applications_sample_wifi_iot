# -*- coding: utf-8 -*-
import time
import threading
import re
from devicetest.core.test_case import TestCase
from devicetest.aw.OpenHarmony import CommonOH
from testcases.orc import Orc


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
        CommonOH.click(self.Phone1, 500, 1130)
        CommonOH.click(self.Phone1, 500, 1130)
        CommonOH.hdc_std(self.Phone1, "shell snapshot_display -f /data/distributedcalc_step1.jpeg")
        CommonOH.hdc_std(self.Phone1, "file recv /data/distributedcalc_step1.jpeg testcases\\distributedcalc_step1.jpeg")
        CommonOH.click(self.Phone1, 610, 110)
        time.sleep(2)
        CommonOH.click(self.Phone1, 380, 1150)
        CommonOH.click(self.Phone1, 610, 110)
        time.sleep(2)
        CommonOH.hdc_std(self.Phone1, "shell snapshot_display -f /data/distributedcalc_step2.jpeg")
        CommonOH.hdc_std(self.Phone1, "file recv /data/distributedcalc_step2.jpeg testcases\\distributedcalc_step2.jpeg")
        CommonOH.click(self.Phone1, 580, 1090)
        time.sleep(2)
        CommonOH.hdc_std(self.Phone2, "shell snapshot_display -f /data/distributedcalc_step3.jpeg")
        CommonOH.hdc_std(self.Phone2, "file recv /data/distributedcalc_step3.jpeg testcases\\distributedcalc_step3.jpeg")
        #确定
        CommonOH.click(self.Phone2, 520, 520)
        CommonOH.click(self.Phone2, 520, 520)
        CommonOH.hdc_std(self.Phone2, "shell snapshot_display -f /data/distributedcalc_step4.jpeg")
        CommonOH.hdc_std(self.Phone2, "file recv /data/distributedcalc_step4.jpeg testcases\\distributedcalc_step4.jpeg")
        time.sleep(2)
        code = Orc("testcases\\distributedcalc_step4.jpeg")
        self.code = re.findall("[0-9]{6}", code)[0]
        #输pin码
        CommonOH.click(self.Phone1, 340, 530)
        CommonOH.click(self.Phone1, 340, 530)
        time.sleep(1)
        #切换至数字输入
        CommonOH.click(self.Phone1, 60, 1145)
        time.sleep(1)
        for i in self.code:
            if i == "0":
                CommonOH.click(self.Phone1, 676, 778)
            else:
                j = int(i) - 1
                CommonOH.click(self.Phone1, 46 + j * 70, 778)
        time.sleep(1)
        CommonOH.click(self.Phone1, 60, 1145)
        CommonOH.hdc_std(self.Phone1, "shell snapshot_display -f /data/distributedcalc_step5.jpeg")
        # 确定
        CommonOH.click(self.Phone1, 500, 600)
        CommonOH.hdc_std(self.Phone1, "file recv /data/distributedcalc_step5.jpeg testcases\\distributedcalc_step5.jpeg")

    def sub_distributed_smoke_testcase_0300(self):
        # 切入后台，结束进程
        CommonOH.click(self.Phone1, 512, 1246)
        CommonOH.click(self.Phone1, 360, 1168)
        # 重启计算器应用
        CommonOH.startAbility(self.Phone1, "ohos.samples.distributedcalc.MainAbility", "ohos.samples.distributedcalc")
        time.sleep(2)
        # 拉起远端设备
        CommonOH.click(self.Phone1, 610, 110)
        time.sleep(3)
        CommonOH.hdc_std(self.Phone1, "shell snapshot_display -f /data/distributedcalc_step6.jpeg")
        CommonOH.hdc_std(self.Phone1, "file recv /data/distributedcalc_step6.jpeg testcases\\distributedcalc_step6.jpeg")
        CommonOH.click(self.Phone1, 580, 1090)
        CommonOH.click(self.Phone1, 580, 1090)
        # 设备二授权
        time.sleep(2)
        CommonOH.click(self.Phone2, 500, 1130)
        CommonOH.click(self.Phone2, 500, 1130)
        # 校验远端计算器是否被拉起
        CommonOH.hdc_std(self.Phone2, "shell snapshot_display -f /data/distributedcalc_step7.jpeg")
        CommonOH.hdc_std(self.Phone2, "file recv /data/distributedcalc_step7.jpeg testcases\\distributedcalc_step7.jpeg")
        CommonOH.hdc_std(self.Phone2, 'shell "aa dump -a | grep distributedcalc > /data/report.txt"')
        CommonOH.hdc_std(self.Phone2, "file recv /data/report.txt testcases\\report.txt")
        time.sleep(1)
        CommonOH.hdc_std(self.Phone1, "file send testcases\\report.txt /data/report.txt")

    def net_connect1(self):
        # 点亮屏幕
        CommonOH.wake(self.Phone1)
        # 设置不息屏
        CommonOH.hdc_std(self.Phone1, 'shell "power-shell setmode 602"')

    def net_connect2(self):
        # 点亮屏幕
        CommonOH.wake(self.Phone2)
        # 设置不息屏
        CommonOH.hdc_std(self.Phone2, 'shell "power-shell setmode 602"')

    def teardown(self):
        # 切入后台，结束进程
        CommonOH.hdc_std(self.Phone1, "shell killall ohos.samples.distributedcalc")
        CommonOH.hdc_std(self.Phone2, "shell killall ohos.samples.distributedcalc")