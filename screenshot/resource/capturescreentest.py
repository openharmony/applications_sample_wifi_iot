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

def MyPrint(str):
    print(str)
    with open(os.path.join(args.save_path, 'shot_test.log'), mode='a', encoding='utf-8') as log_file:
        console = sys.stdout
        sys.stdout = log_file
        print(str)
        sys.stdout = console
    log_file.close()

def EnterCmd(mycmd, waittime = 0, printresult = 1):
    if mycmd == "":
        return
    with open(os.path.join(args.save_path, 'shot_test.bat'), mode='a', encoding='utf-8') as cmd_file:
        cmd_file.write(mycmd + '\n')
    cmd_file.close()
    with os.popen(mycmd) as p:
        bf = p._stream.buffer.read()
    try:
        result=bf.decode().strip()
    except UnicodeDecodeError:
        result=bf.decode('gbk', errors='ignore').strip()

    if printresult == 1:
        MyPrint(mycmd)
        MyPrint(result)
        sys.stdout.flush()
    if waittime != 0:
        time.sleep(waittime)
        with open(os.path.join(args.save_path, 'shot_test.bat'), mode='a', encoding='utf-8') as cmd_file:
            cmd_file.write("ping -n {} 127.0.0.1>null\n".format(waittime))
        cmd_file.close()
    return result

def connect_to_wifi(tools_path):
    EnterCmd("hdc_std shell mkdir /data/l2tool", 1)
    EnterCmd("hdc_std file send {}\\l2tool\\busybox /data/l2tool".format(tools_path), 1)
    EnterCmd("hdc_std file send {}\\l2tool\\dhcpc.sh /data/l2tool".format(tools_path), 1)
    EnterCmd("hdc_std file send {}\\l2tool\\entry-debug-rich-signed.hap /data/l2tool".format(tools_path), 1)
    EnterCmd("hdc_std file send {}\\l2tool\\hostapd.conf /data/l2tool".format(tools_path), 1)
    EnterCmd("hdc_std file send {}\\l2tool\\iperf /data/l2tool".format(tools_path), 1)
    EnterCmd("hdc_std file send {}\\l2tool\\p2p_supplicant.conf /data/l2tool".format(tools_path), 1)
    EnterCmd("hdc_std file send {}\\l2tool\\p2p_supplicant1.conf /data/l2tool".format(tools_path), 1)
    EnterCmd("hdc_std file send {}\\l2tool\\udhcpd.conf /data/l2tool".format(tools_path), 1)
    EnterCmd("hdc_std file send {}\\l2tool\\wpa_supplicant.conf /data/l2tool".format(tools_path), 1)
    EnterCmd("hdc_std shell wpa_supplicant -B -d -i wlan0 -c /data/l2tool/wpa_supplicant.conf", 1)
    EnterCmd("hdc_std shell chmod 777 ./data/l2tool/busybox", 1)
    cnt = 2
    while cnt:
        try:
            MyPrint("hdc_std shell ./data/l2tool/busybox udhcpc -i wlan0 -s /data/l2tool/dhcpc.sh")
            p = subprocess.check_output("hdc_std shell ./data/l2tool/busybox udhcpc -i wlan0 -s /data/l2tool/dhcpc.sh", timeout=8)
            MyPrint(p.decode(encoding="utf-8"))
            with open(os.path.join(args.save_path, 'shot_test.bat'), mode='a', encoding='utf-8') as      cmd_file:
                cmd_file.write('hdc_std shell ./data/l2tool/busybox udhcpc -i wlan0 -s /data/l2tool/dhcpc.sh' + '\n')
            cmd_file.close()
            ret_code = 0
        except subprocess.TimeoutExpired as time_e:
            MyPrint(time_e)
            ret_code = 1
        if ret_code == 0:
            ip = re.findall(r"\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b", p.decode(encoding="utf-8"))
            MyPrint(ip)
            if len(ip) <= 0:
                break
            if len(re.findall(r'(?<!\d)\d{1,3}\.\d{1,3}\.\d{1,3}(?=\.\d)', ip[0])) <= 0:
                break
            gate = str(re.findall(r'(?<!\d)\d{1,3}\.\d{1,3}\.\d{1,3}(?=\.\d)', ip[0])[0]) + ".1"
            MyPrint(gate)
            ifconfig="hdc_std shell ifconfig wlan0 {}".format(ip[0])
            EnterCmd(ifconfig)
            routeconfig="hdc_std shell ./data/l2tool/busybox route add default gw {} dev wlan0".format(gate)
            EnterCmd(routeconfig)
            break
        MyPrint("try {}".format(cnt))
        cnt -= 1
        time.sleep(5)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='manual to this script')
    parser.add_argument('--config', type=str, default = './app_capture_screen_test_config.json')
    parser.add_argument('--test_num', type=int, nargs='+', default = [])
    parser.add_argument('--tools_path', type=str, default = 'D:\\DeviceTestTools')
    parser.add_argument('--anwser_path', type=str, default = 'screenshot\\RK\\')
    parser.add_argument('--save_path', type=str, default = './report/screenshot_1/')
    args = parser.parse_args()

    with open(args.config) as f:
        all_app = json.load(f)
    with open(os.path.join(args.save_path, 'shot_test.bat'), mode='w', encoding='utf-8') as cmd_file:
        cmd_file.close()
    with open(os.path.join(args.save_path, 'shot_test.log'), mode='w', encoding='utf-8') as log_file:
        log_file.close()
    cmp_status = 0
    global_pos = all_app[0]
    return_cmd = "hdc_std shell uinput -M -m {} {} -c 0".format(global_pos['return-x-y'][0], global_pos['return-x-y'][1])
    recent_cmd = "hdc_std shell uinput -M -m {} {} -c 0".format(global_pos['recent-x-y'][0], global_pos['recent-x-y'][1])
    home_cmd = "hdc_std shell uinput -M -m {} {} -c 0".format(global_pos['home-x-y'][0], global_pos['home-x-y'][1])
    recent_del_cmd = "hdc_std shell uinput -M -m {} {} -c 0".format(global_pos['recent_del-x-y'][0], global_pos['recent_del-x-y'][1])
    os.system("hdc_std start")
    EnterCmd("hdc_std shell hilog -w stop", 1)
    EnterCmd("hdc_std shell \"cd /data/log/hilog && tar -cf system_start_log.tar *\"", 1)
    EnterCmd("hdc_std file recv /data/log/hilog/system_start_log.tar {}".format(args.save_path), 1)
    EnterCmd("hdc_std list targets", 1)
    EnterCmd("hdc_std list targets", 1)
    EnterCmd("hdc_std shell rm -rf /data/screen_test/train_set")
    EnterCmd("hdc_std shell mkdir -p /data/screen_test/train_set")
    EnterCmd("hdc_std file send {} {}".format(os.path.join(os.path.dirname(args.config), "printscreen"), "/data/screen_test/"))
    EnterCmd("hdc_std shell chmod 777 /data/screen_test/printscreen")

    if len(args.test_num) == 0:
        idx_list = list(range(1, len(all_app)))
    else:
        idx_list = args.test_num

    fail_idx_list = []
    for idx in idx_list:
        single_app = all_app[idx]
        sys.stdout.flush()
        call_app_cmd = "hdc_std shell " + single_app['entry']
        send_file_cmd = "hdc_std file send {} {}"
        capture_screen_cmd = "hdc_std shell /data/screen_test/printscreen -f /data/screen_test/{}"
        recv_file_cmd = "hdc_std file recv /data/screen_test/{} {}"
        cmp_cmd = "hdc_std shell \"cmp -l /data/screen_test/{} /data/screen_test/train_set/{} | wc -l\""
        MyPrint("\n\n########## case {} : {} test start ##############".format(idx, single_app['app_name']))
        with open(os.path.join(args.save_path, 'shot_test.bat'), mode='a', encoding='utf-8') as cmd_file:
            cmd_file.write("\n\n::::::case {} --- {} test start \n".format(idx, single_app['app_name']))
        cmd_file.close()
        testcnt = 2
        while testcnt:
            testok = 0
            if testcnt == 1:
                MyPrint(">>>>>>>>>>>>>>>>>>>>>>>Try again:\n")
                with open(os.path.join(args.save_path, 'shot_test.bat'), mode='a', encoding='utf-8') as cmd_file:
                    cmd_file.write("\n::::::Last failed, Try again \n")
                cmd_file.close()
            EnterCmd("hdc_std shell \"rm /data/log/hilog/*;hilog -r;hilog -w start -l 400000000 -m none\"", 1)
            if single_app['entry'] != "":
                EnterCmd(call_app_cmd, 5)
            MyPrint(single_app['all_actions'])
            for single_action in single_app['all_actions']:
                #shot_cmd is stable, different to other cmd,so handle it specialy
                if type(single_action[1]) == str and single_action[1] == 'shot_cmd':
                    if len(single_action) == 3:
                        pic_name = single_action[2] + ".png"
                        raw_pic_name = single_action[2] + ".pngraw"
                    else:
                        pic_name = single_app['app_name'] + ".png"
                        raw_pic_name = single_app['app_name'] + ".pngraw"
                    EnterCmd(capture_screen_cmd.format(pic_name), 1)
                    EnterCmd(recv_file_cmd.format(pic_name, args.save_path), 1)
                    EnterCmd(recv_file_cmd.format(raw_pic_name, args.save_path), 1)
                    next_cmd = ""
                #cmp_cmd-level is stable, different to other cmd,so handle it specialy
                elif type(single_action[1]) == str and single_action[1] == 'cmp_cmd-level':
                    next_cmd = ""
                    MyPrint(send_file_cmd.format(os.path.join(args.anwser_path, raw_pic_name), "/data/screen_test/train_set"))
                    sys.stdout.flush()
                    EnterCmd(send_file_cmd.format(os.path.join(args.anwser_path, raw_pic_name), "/data/screen_test/train_set"))
                    new_cmp_cmd = cmp_cmd.format(raw_pic_name, raw_pic_name)
                    if len(single_action) == 3:
                        tolerance = single_action[2]
                    else:
                        tolerance = global_pos['cmp_cmd-level'][1]
                    p = EnterCmd(new_cmp_cmd, single_action[0])
                    num = re.findall(r'[-+]?\d+', p)
                    MyPrint(num)
                    if type(num) == list and len(num) > 0 and int(num[0]) < tolerance:
                        testok = 1
                        MyPrint("{} screenshot check is ok!\n\n".format(raw_pic_name))
                    else:
                        testok = -1
                        MyPrint("{} screenshot check is abnarmal!\n\n".format(raw_pic_name))
                    sys.stdout.flush()
                elif type(single_action[1]) == str and single_action[1] == 'recv_log-file':
                    next_cmd = ""
                    if len(single_action) == 3:
                        logfilepath = single_action[2]
                        next_cmd = "hdc_std file recv {} {}".format(logfilepath, args.save_path)
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
                        p = EnterCmd(target_[0], single_action[0])
                        result = "".join(p)
                        if len(target_) > 1:
                            findsome = result.find(target_[1], 0, len(result))
                            if findsome != -1:
                                testok = 1
                                MyPrint("\"{}\" check execut result is ok, find \"{}\"!\n".format(target_[0], target_[1]))
                            else:
                                testok = -1
                                MyPrint("\"{}\" check execut result is not ok, not find \"{}\"!\n".format(target_[0], target_[1]))
                            sys.stdout.flush()
                    #this cmd only is a name of x,y postion, to get x,y an click it
                    else:
                        next_cmd = "hdc_std shell uinput -M -m {} {} -c 0".format(target_[0], target_[1])
                #uinput x,y postion, to click it
                else:
                    next_cmd = "hdc_std shell uinput -M -m {} {} -c 0".format(single_action[1], single_action[2])
                EnterCmd(next_cmd, single_action[0])
            if fail_idx_list.count(idx):
                fail_idx_list.remove(idx)
            if testok == 1:
                MyPrint("testcase {}, {} is ok!\n\n".format(idx, single_app['app_name']))
                testcnt = 0
            elif testok == -1:
                MyPrint("ERROR:testcase {}, {} is failed!\n\n".format(idx, single_app['app_name']))
                fail_idx_list.append(idx)
                testcnt -= 1
            else:
                testcnt = 0
            EnterCmd("hdc_std shell hilog -w stop", 1)

    if len(fail_idx_list) != 0:
        MyPrint("ERROR: {}, these testcase is failed".format(fail_idx_list))
        MyPrint("End of check, test failed!")
    else:
        MyPrint("All testcase is ok")
        MyPrint("End of check, test succeeded!")
    sys.stdout.flush()
    sys.exit(len(fail_idx_list))