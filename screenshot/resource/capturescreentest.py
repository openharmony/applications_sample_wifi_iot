# -*- coding: utf-8 -*-
# Copyright (c) 2022 Huawei Device Co., Ltd.
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from ast import parse
import json
import sys
import os
import time
import argparse
import re
import subprocess
import shlex

def PrintToLog(str):
    print(str)
    with open(os.path.join(args.save_path, 'shot_test_{}.log'.format(args.device_num)), mode='a', encoding='utf-8') as log_file:
        console = sys.stdout
        sys.stdout = log_file
        print(str)
        sys.stdout = console
    log_file.close()

def EnterCmd(mycmd, waittime = 0, printresult = 1):
    if mycmd == "":
        return
    global CmdRetryCnt
    CmdRetryCnt = 1
    EnterCmdRetry = 2
    while EnterCmdRetry:
        EnterCmdRetry -= 1
        try:
            p = subprocess.Popen(mycmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            result, unused_err = p.communicate(timeout=15)
            try:
                result=result.decode(encoding="utf-8")
            except UnicodeDecodeError:
                result=result.decode('gbk', errors='ignore')
            break
        except Exception as e:
            result = 'retry failed again'
            PrintToLog(e)
            PrintToLog("cmd_retry_trace_{}.png".format(CmdRetryCnt))
            os.system("hdc_std -t {} shell \" snapshot_display -f /data/cmd_retry_trace_{}.png\"".format(args.device_num, CmdRetryCnt))
            GetFileFromDev("/data/cmd_retry_trace_{}.png".format(CmdRetryCnt), args.save_path)
            CmdRetryCnt += 1
            p.kill()
    if printresult == 1:
        with open(os.path.join(args.save_path, 'shot_test_{}.bat'.format(args.device_num)), mode='a', encoding='utf-8') as cmd_file:
            cmd_file.write(mycmd + '\n')
        cmd_file.close()
        PrintToLog(mycmd)
        PrintToLog(result)
        sys.stdout.flush()
    if waittime != 0:
        time.sleep(waittime)
        if printresult == 1:
            with open(os.path.join(args.save_path, 'shot_test_{}.bat'.format(args.device_num)), mode='a', encoding='utf-8') as cmd_file:
                cmd_file.write("ping -n {} 127.0.0.1>null\n".format(waittime))
            cmd_file.close()
    return result

def EnterShellCmd(shellcmd, waittime = 0, printresult = 1):
    if shellcmd == "":
        return
    cmd = "hdc_std -t {} shell \"{}\"".format(args.device_num, shellcmd)
    return EnterCmd(cmd, waittime, printresult)

def SendFileToDev(src, dst):
    cmd = "hdc_std -t {} file send \"{}\" \"{}\"".format(args.device_num, src, dst)
    return EnterCmd(cmd, 1, 1)

def GetFileFromDev(src, dst):
    cmd = "hdc_std -t {} file recv \"{}\" \"{}\"".format(args.device_num, src, dst)
    return EnterCmd(cmd, 1, 1)

def connect_to_wifi(tools_path):
    EnterShellCmd("mkdir /data/l2tool", 1)
    SendFileToDev(os.path.normpath(os.path.join(tools_path, "l2tool/busybox")), "/data/l2tool/")
    SendFileToDev(os.path.normpath(os.path.join(tools_path, "l2tool/dhcpc.sh")), "/data/l2tool/")
    SendFileToDev(os.path.normpath(os.path.join(tools_path, "l2tool/wpa_supplicant.conf")), "/data/l2tool/")
    EnterShellCmd("wpa_supplicant -B -d -i wlan0 -c /data/l2tool/wpa_supplicant.conf", 1)
    EnterShellCmd("chmod 777 ./data/l2tool/busybox", 1)
    cnt = 2
    while cnt:
        try:
            PrintToLog("hdc_std shell ./data/l2tool/busybox udhcpc -i wlan0 -s /data/l2tool/dhcpc.sh")
            p = subprocess.check_output(shlex.split("hdc_std -t {} shell ./data/l2tool/busybox udhcpc -i wlan0 -s /data/l2tool/dhcpc.sh".format(args.device_num)), timeout=8)
            PrintToLog(p.decode(encoding="utf-8"))
            with open(os.path.join(args.save_path, 'shot_test_{}.bat'.format(args.device_num)), mode='a', encoding='utf-8') as      cmd_file:
                cmd_file.write('hdc_std shell ./data/l2tool/busybox udhcpc -i wlan0 -s /data/l2tool/dhcpc.sh' + '\n')
            cmd_file.close()
            ret_code = 0
        except subprocess.TimeoutExpired as time_e:
            PrintToLog(time_e)
            ret_code = 1
        if ret_code == 0:
            ip = re.findall(r"\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b", p.decode(encoding="utf-8"))
            PrintToLog(ip)
            if len(ip) <= 0:
                break
            if len(re.findall(r'(?<!\d)\d{1,3}\.\d{1,3}\.\d{1,3}(?=\.\d)', ip[0])) <= 0:
                break
            gate = str(re.findall(r'(?<!\d)\d{1,3}\.\d{1,3}\.\d{1,3}(?=\.\d)', ip[0])[0]) + ".1"
            PrintToLog(gate)
            ifconfig="ifconfig wlan0 {}".format(ip[0])
            EnterShellCmd(ifconfig)
            routeconfig="./data/l2tool/busybox route add default gw {} dev wlan0".format(gate)
            EnterShellCmd(routeconfig)
            break
        PrintToLog("try {}".format(cnt))
        cnt -= 1
        time.sleep(5)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='manual to this script')
    parser.add_argument('--config', type=str, default = './app_capture_screen_test_config.json')
    parser.add_argument('--test_num', type=str, default = '1/1')
    parser.add_argument('--tools_path', type=str, default = 'D:\\DeviceTestTools\\screenshot\\')
    parser.add_argument('--anwser_path', type=str, default = 'D:\\DeviceTestTools\\screenshot\\resource')
    parser.add_argument('--save_path', type=str, default = 'D:\\DeviceTestTools\\screenshot')
    parser.add_argument('--device_num', type=str, default = 'null')
    args = parser.parse_args()

    if args.device_num == 'null':
        result = EnterCmd("hdc_std list targets", 1, 0)
        print(result)
        args.device_num = result.split()[0]

    with open(args.config) as f:
        all_app = json.load(f)
    with open(os.path.join(args.save_path, 'shot_test_{}.bat'.format(args.device_num)), mode='w', encoding='utf-8') as cmd_file:
        cmd_file.close()
    with open(os.path.join(args.save_path, 'shot_test_{}.log'.format(args.device_num)), mode='w', encoding='utf-8') as log_file:
        log_file.close()
    cmp_status = 0
    global_pos = all_app[0]

    #rmlock
    rebootcnt = 2
    while rebootcnt:
        rebootcnt -= 1
        os.system("hdc_std start")
        EnterCmd("hdc_std list targets", 1)
        EnterCmd("hdc_std list targets", 1)
        EnterShellCmd("rm -rf /data/screen_test/train_set")
        EnterShellCmd("mkdir -p /data/screen_test/train_set")
        SendFileToDev(os.path.normpath(os.path.join(args.tools_path, "resource/printscreen")), "/data/screen_test/")
        EnterShellCmd("chmod 777 /data/screen_test/printscreen")
        rmlockcnt = 5
        while rmlockcnt:
            EnterShellCmd("uinput -T -m 425 1000 425 400;power-shell wakeup;uinput -T -m 425 400 425 1000;power-shell setmode 602;uinput -T -m 425 1000 425 400;", 1)
            rmlockcnt -= 1

        EnterShellCmd("hilog -w stop", 1)
        EnterShellCmd("cd /data/log/hilog && tar -cf system_start_log.tar *", 1)
        GetFileFromDev("/data/log/hilog/system_start_log.tar", args.save_path)
        #print(os.path.normpath(os.path.join(args.anwser_path, "launcher.pngraw")))
        SendFileToDev(os.path.normpath(os.path.join(args.anwser_path, "launcher.pngraw")), "/data/screen_test/train_set")
        EnterShellCmd("/data/screen_test/printscreen -f /data/screen_test/rmlock.png", 1)
        cmp_launcher = "cmp -l /data/screen_test/rmlock.pngraw /data/screen_test/train_set/launcher.pngraw | wc -l"
        p = EnterShellCmd(cmp_launcher, 1)
        num = re.findall(r'[-+]?\d+', p)
        PrintToLog(num)
        if type(num) == list and len(num) > 0 and int(num[0]) < 1000000:
            PrintToLog("remove lock is ok!\n\n")
            break
        elif rebootcnt >= 1:
            PrintToLog("remove lock failed, reboot and try!!!\n\n")
            os.system("hdc_std -t {} shell reboot".format(args.device_num))
            for i in range(5):
                EnterCmd("hdc_std list targets", 10)

        else:
            PrintToLog("remove lock failed\n\n")
            break
    try:
        args.test_num.index('/')
        idx_total = args.test_num.split('/')
        if len(idx_total) != 2:
            PrintToLog("test_num is invaild !!!")
            PrintToLog("End of check, test failed!")
            sys.exit(1)
        elif idx_total[1] == '1':
            idx_list = list(range(1, len(all_app)))
        else:
            idx_list = global_pos['DEVICE_{}'.format(idx_total[0])]
    except ValueError as e:
        PrintToLog(e)
        idx_list = list(map(eval, args.test_num.split()))

    PrintToLog(idx_list)

    fail_idx_list = []
    fail_name_list = []
    smoke_first_failed = ''
    for idx in idx_list:
        single_app = all_app[idx]
        sys.stdout.flush()
        call_app_cmd = single_app['entry']
        capture_screen_cmd = "/data/screen_test/printscreen -f /data/screen_test/{}_{}"
        cmp_cmd = "cmp -l /data/screen_test/{}_{} /data/screen_test/train_set/{} | wc -l"
        PrintToLog("\n\n########## case {} : {} test start ##############".format(idx, single_app['app_name']))
        with open(os.path.join(args.save_path, 'shot_test_{}.bat'.format(args.device_num)), mode='a', encoding='utf-8') as cmd_file:
            cmd_file.write("\n\n::::::case {} --- {} test start \n".format(idx, single_app['app_name']))
        cmd_file.close()
        testcnt = 5
        while testcnt:
            testok = 0
            if testcnt != 5:
                PrintToLog(">>>>>>>>>>>>>>>>>>>>>>>Try again:\n")
                with open(os.path.join(args.save_path, 'shot_test_{}.bat'.format(args.device_num)), mode='a', encoding='utf-8') as cmd_file:
                    cmd_file.write("\n::::::Last failed, Try again \n")
                cmd_file.close()
            EnterShellCmd("rm /data/log/hilog/*;hilog -r;hilog -w start -l 400000000 -m none", 1)
            if single_app['entry'] != "":
                EnterShellCmd(call_app_cmd, 5)
            PrintToLog(single_app['all_actions'])
            raw_pic_name = ''
            pic_name = ''
            for single_action in single_app['all_actions']:
                #shot_cmd is stable, different to other cmd,so handle it specialy
                if type(single_action[1]) == str and single_action[1] == 'shot_cmd':
                    if len(single_action) == 3:
                        pic_name = "{}{}".format(single_action[2], ".png")
                        raw_pic_name = single_action[2] + ".pngraw"
                    else:
                        pic_name = "{}{}".format(single_app['app_name'], ".png")
                        raw_pic_name = single_app['app_name'] + ".pngraw"
                    EnterShellCmd(capture_screen_cmd.format(6 - testcnt, pic_name), 1)
                    GetFileFromDev("/data/screen_test/{}_{}".format(6 - testcnt, pic_name), args.save_path)
                    p = EnterShellCmd("ls -al /data/screen_test/{}_{}".format(6 - testcnt, raw_pic_name), 1)
                    no_such = re.findall(r'No such file or directory', p)
                    PrintToLog(no_such)
                    if type(no_such) == list and len(no_such) > 0 and no_such[0] == 'No such file or directory':
                        PrintToLog("ERROR: {} screenshot failed!\n\n".format(raw_pic_name))
                        PrintToLog("End of check, test failed!")
                        sys.exit(255)
                    next_cmd = ""
                #cmp_cmd-level is stable, different to other cmd,so handle it specialy
                elif type(single_action[1]) == str and single_action[1] == 'cmp_cmd-level':
                    next_cmd = ""
                    sys.stdout.flush()
                    SendFileToDev(os.path.normpath(os.path.join(args.anwser_path, raw_pic_name)), "/data/screen_test/train_set")
                    new_cmp_cmd = cmp_cmd.format(6 - testcnt, raw_pic_name, raw_pic_name)
                    if len(single_action) == 3:
                        tolerance = single_action[2]
                    else:
                        tolerance = global_pos['cmp_cmd-level'][1]
                    p = EnterShellCmd(new_cmp_cmd, single_action[0])
                    num = re.findall(r'[-+]?\d+', p)
                    PrintToLog(num)
                    if type(num) == list and len(num) > 0 and int(num[0]) < tolerance:
                        testok = 1
                        PrintToLog("{} screenshot check is ok!\n\n".format(raw_pic_name))
                    else:
                        testok = -1
                        PrintToLog("{} screenshot check is abnarmal!\n\n".format(raw_pic_name))
                    sys.stdout.flush()
                    if testok == 1 or testcnt == 1:
                        old_name = os.path.normpath(os.path.join(args.save_path, "{}_{}".format(6 - testcnt, pic_name)))
                        GetFileFromDev("/data/screen_test/{}_{}".format(6 - testcnt, raw_pic_name), args.save_path)
                        os.system("rename {} {}".format(old_name, pic_name))
                        os.system("rename {}raw {}raw".format(old_name, pic_name))
                    raw_pic_name = ''
                elif type(single_action[1]) == str and single_action[1] == 'install_hap':
                    next_cmd = ""
                    if len(single_action) == 3:
                        EnterCmd("hdc_std -t {} install \"{}\"".format(args.device_num, os.path.normpath(os.path.join(args.tools_path, single_action[2]))))
                elif type(single_action[1]) == str and single_action[1] == 'get_file_from_dev':
                    next_cmd = ""
                    if len(single_action) == 3:
                        EnterCmd("hdc_std -t {} file recv \"{}\" \"{}\"".format(args.device_num, single_action[2], os.path.normpath(args.save_path)))
                elif type(single_action[1]) == str and single_action[1] == 'send_file_to_dev':
                    next_cmd = ""
                    if len(single_action) == 4:
                        EnterCmd("hdc_std -t {} file send \"{}\" \"{}\"".format(args.device_num, os.path.normpath(os.path.join(args.tools_path, single_action[2])), single_action[3]))
                elif type(single_action[1]) == str and single_action[1] == 'connect_wifi':
                    next_cmd = ""
                    connect_to_wifi(args.tools_path)
                #other cmd handle
                elif type(single_action[1]) == str:
                    if single_action[1] not in single_app.keys():
                        target_ = global_pos[single_action[1]]
                    else:
                        target_ = single_app[single_action[1]]
                    #this cmd is real cmd,and have a except answer
                    if type(target_[0]) == str:
                        next_cmd = ""
                        p = EnterShellCmd(target_[0], single_action[0])
                        result = "".join(p)
                        if len(target_) > 1:
                            findsome = result.find(target_[1], 0, len(result))
                            if findsome != -1:
                                testok = 1
                                PrintToLog("\"{}\" check execut result is ok, find \"{}\"!\n".format(target_[0], target_[1]))
                            else:
                                testok = -1
                                PrintToLog("\"{}\" check execut result is not ok, not find \"{}\"!\n".format(target_[0], target_[1]))
                            sys.stdout.flush()
                    #this cmd only is a name of x,y postion, to get x,y an click it
                    else:
                        next_cmd = "uinput -M -m {} {} -c 0".format(target_[0], target_[1])
                #uinput x,y postion, to click it
                else:
                    next_cmd = "uinput -M -m {} {} -c 0".format(single_action[1], single_action[2])
                EnterShellCmd(next_cmd, single_action[0])

            if testok == 1:
                PrintToLog("testcase {}, {} is ok!\n\n".format(idx, single_app['app_name']))
                testcnt = 0
            elif testok == -1 and smoke_first_failed == '':
                #PrintToLog("ERROR:testcase {}, {} is failed!\n\n".format(idx, single_app['app_name']))
                if testcnt == 1:
                    fail_idx_list.append(idx)
                    fail_name_list.append(single_app['app_name'])
                    smoke_first_failed = single_app['app_name']
                    PrintToLog("ERROR:testcase {}, {} is failed!\n\n".format(idx, single_app['app_name']))
                testcnt -= 1
            elif testok == -1 and smoke_first_failed != '':
                fail_idx_list.append(idx)
                fail_name_list.append(single_app['app_name'])
                PrintToLog("ERROR:testcase {}, {} is failed!\n\n".format(idx, single_app['app_name']))
                testcnt = 0
            else:
                testcnt = 0
            EnterShellCmd("hilog -w stop", 1)
        if smoke_first_failed == 'launcher':
            break

    EnterShellCmd("cd /data/log/faultlog/temp && tar -cf after_test_crash_log.tar cppcrash*")
    EnterCmd("hdc_std -t {} file recv /data/log/faultlog/temp/after_test_crash_log.tar {}".format(args.device_num, os.path.normpath(args.save_path)))
    if len(fail_idx_list) != 0:
        PrintToLog("ERROR: name {}, index {}, these testcase is failed".format(fail_name_list, fail_idx_list))
        if fail_name_list.count('launcher') or fail_name_list.count('settings_keyboard'):
            PrintToLog("End of check, Some Key APPs(launcher or setting) failed!")
        PrintToLog("End of check, test failed!")
    else:
        PrintToLog("All testcase is ok")
        PrintToLog("End of check, test succeeded!")
    sys.stdout.flush()
    sys.exit(len(fail_idx_list))