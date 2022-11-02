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
import encodings
import json
import sys
import os
import time
import argparse
import re
import subprocess
import shlex
import datetime
import sqlite3
import shutil


def PrintToLog(str):
    time = datetime.datetime.now()
    str = "[{}] {}".format(time, str)
    print(str)
    with open(os.path.join(args.save_path, 'test_{}.log'.format(args.device_num)),\
    mode='a', encoding='utf-8') as log_file:
        console = sys.stdout
        sys.stdout = log_file
        print(str)
        sys.stdout = console
    log_file.close()


def EnterCmd(mycmd, waittime=0, printresult=1):
    if mycmd == "":
        return
    global CmdRetryCnt
    CmdRetryCnt = 1
    EnterCmdRetry = 2
    while EnterCmdRetry:
        EnterCmdRetry -= 1
        try:
            p = subprocess.Popen(mycmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            result, unused_err = p.communicate(timeout=25)
            try:
                result=result.decode(encoding="utf-8")
            except UnicodeDecodeError:
                result=result.decode('gbk', errors='ignore')
            break
        except Exception as e:
            result = 'retry failed again'
            PrintToLog(e)
            CmdRetryCnt += 1
            p.kill()
    if printresult == 1:
        with open(os.path.join(args.save_path, 'test_{}.bat'.format(args.device_num)),\
        mode='a', encoding='utf-8') as cmd_f:
            cmd_f.write(mycmd + '\n')
        cmd_f.close()
        PrintToLog(mycmd)
        PrintToLog(result)
        sys.stdout.flush()
    if waittime != 0:
        time.sleep(waittime)
        if printresult == 1:
            with open(os.path.join(args.save_path, 'test_{}.bat'.format(args.device_num)),\
            mode='a', encoding='utf-8') as cmd_f:
                cmd_f.write("ping -n {} 127.0.0.1>null\n".format(waittime))
            cmd_f.close()
    return result


def EnterShellCmd(shellcmd, waittime=0, printresult=1):
    if shellcmd == "":
        return
    cmd = "hdc_std -t {} shell \"{}\"".format(args.device_num, shellcmd)
    return EnterCmd(cmd, waittime, printresult)


def SysExit():
    EnterShellCmd("cd /data/log/faultlog/temp && tar -cf after_test_cppcrash{}.tar cppcrash*".format(args.device_num))
    GetFileFromDev("/data/log/faultlog/temp/after_test_cppcrash{}.tar".format(args.device_num), \
    os.path.normpath(args.save_path))
    EnterShellCmd("cd /data/log/faultlog/faultlogger && tar -cf after_test_jscrash{}.tar jscrash*".format(args.device_num))
    GetFileFromDev("/data/log/faultlog/faultlogger/after_test_jscrash{}.tar".format(args.device_num), \
    os.path.normpath(args.save_path))
    PrintToLog("SmokeTest:: SmokeTest find some key problems!")
    PrintToLog("SmokeTest:: End of check, test failed!")
    sys.exit(98)


def SendFileToDev(src, dst):
    cmd = "hdc_std -t {} file send \"{}\" \"{}\"".format(args.device_num, src, dst)
    return EnterCmd(cmd, 1, 1)


def GetFileFromDev(src, dst):
    cmd = "hdc_std -t {} file recv \"{}\" \"{}\"".format(args.device_num, src, dst)
    return EnterCmd(cmd, 1, 1)


def ImageCheck(str, testnum=1):
    conn = sqlite3.connect(str)
    cursor_image = conn.cursor()
    cursor_video = conn.cursor()
    PrintToLog("SmokeTest:: start to check media library path")
    try:
        PrintToLog("SmokeTest:: select * from  files where mime_type = image/*")
        cursor_image.execute("""select * from  files where mime_type = "image/*" """)
    except:
        PrintToLog("SmokeTest:: error: media_library.db cannot be found, please check media library path")
        return -1
    if testnum == 2:
        try:
            PrintToLog("SmokeTest:: select * from  files where mime_type = video/mp4")
            cursor_video.execute("""select * from  files where mime_type = "video/mp4" """)
        except:
            PrintToLog("SmokeTest:: error: media_library.db cannot be found, please check media library path")
            return -1
    PrintToLog("SmokeTest:: media library is ok")
    image_result = cursor_image.fetchone()
    video_result = cursor_video.fetchone()
    PrintToLog("SmokeTest:: image: {}".format(image_result))
    PrintToLog("SmokeTest:: video: {}".format(video_result))
    PrintToLog("SmokeTest:: start to check photos and videos in the album")
    if image_result is not None and testnum == 1:
        PrintToLog("SmokeTest:: success: There are some photos in the album!!")
        return 1
    elif image_result is not None and video_result is not None and testnum == 2:
        PrintToLog("SmokeTest:: success: There are some photos and videos in the album!!")
        return 1
    else:
        PrintToLog("SmokeTest:: error: There are no photos or videos in the album!!")
        return -1


def ConnectionJudgment():
    connection_status = EnterCmd("hdc_std list targets", 2)
    connection_cnt = 0
    while args.device_num not in connection_status and connection_cnt < 15:
        connection_status = EnterCmd("hdc_std list targets", 2)
        connection_cnt += 1
    if connection_cnt == 15:
        PrintToLog("SmokeTest:: Device disconnection!!")
        PrintToLog("SmokeTest:: End of check, test failed!")
        sys.exit(101)


def sandbox_check(process):
    PrintToLog("SmokeTest:: start to check sandbox path")
    medialibrarydata_pidnum = EnterShellCmd("pgrep -f {}".format(process), 1)
    medialibrarydata_pidnum = medialibrarydata_pidnum.strip()
    sandboxf = EnterShellCmd("echo \"ls /storage/media/local/\"|nsenter -t {} -m sh".format(medialibrarydata_pidnum), 1)
    if "files" not in sandboxf:
        PrintToLog("SmokeTest:: error: can not find sandbox path : /storage/media/local/files")
        return -1
    else:
        PrintToLog("SmokeTest:: success: find sandbox path : /storage/media/local/files")
        return 1


def is_image_file(filename):
    IMG_EXTENSIONS = ['.png', '.PNG']
    return any(filename.endswith(extension) for extension in IMG_EXTENSIONS)

def picture_save(pic_path):
    for root, dirs, files in os.walk(pic_path):
        for file in files:
            file_path = os.path.join(root, file)
            if is_image_file(file_path):
                shutil.copy2(file_path, args.save_path)
                PrintToLog("SmokeTest:: send {} to save_path Successfully".format(file_path))


def ConnectToWifi(tools_path):
    EnterShellCmd("mkdir /data/l2tool", 1)
    SendFileToDev(os.path.normpath(os.path.join(tools_path, "l2tool/busybox")), "/data/l2tool/")
    SendFileToDev(os.path.normpath(os.path.join(tools_path, "l2tool/dhcpc.sh")), "/data/l2tool/")
    SendFileToDev(os.path.normpath(os.path.join(tools_path, "l2tool/wpa_supplicant.conf")), "/data/l2tool/")
    EnterShellCmd("wpa_supplicant -B -d -i wlan0 -c /data/l2tool/wpa_supplicant.conf", 1)
    EnterShellCmd("chmod 777 ./data/l2tool/busybox", 1)
    cnt = 2
    while cnt:
        try:
            PrintToLog("SmokeTest:: hdc_std shell ./data/l2tool/busybox udhcpc -i wlan0 -s /data/l2tool/dhcpc.sh")
            p = subprocess.check_output(shlex.split("hdc_std -t {} shell ./data/l2tool/busybox udhcpc -i wlan0 -s \
            /data/l2tool/dhcpc.sh".format(args.device_num)), timeout=8)
            PrintToLog(p.decode(encoding="utf-8"))
            with open(os.path.join(args.save_path, 'test_{}.bat'.format(args.device_num)),\
            mode='a', encoding='utf-8') as cmd_f:
                cmd_f.write('hdc_std shell ./data/l2tool/busybox udhcpc -i wlan0 -s /data/l2tool/dhcpc.sh' + '\n')
            cmd_f.close()
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
    parser.add_argument('--pr_url', type=str, default = 'https://gitee.com/openharmony/applications_sample_wifi_iot/')
    args = parser.parse_args()

    if args.device_num == 'null':
        result = EnterCmd("hdc_std list targets", 1, 0)
        print(result)
        args.device_num = result.split()[0]
    with open(args.config) as f:
        all_app = json.load(f)
    cmp_status = 0
    global_pos = all_app[0]

    rebootcnt = 2
    while rebootcnt:
        rebootcnt -= 1
        EnterCmd("hdc_std list targets", 1)
        EnterShellCmd("mkdir -p /data/screen_test/train_set")
        SendFileToDev(os.path.normpath(os.path.join(args.tools_path, "resource/printscreen")), "/data/screen_test/")
        EnterShellCmd("chmod 777 /data/screen_test/printscreen")
        rmlockcnt = 3
        while rmlockcnt:
            EnterShellCmd("uinput -T -m 425 1000 425 400;power-shell wakeup;uinput -T -m 425 400 425 1000;\
            power-shell setmode 602;uinput -T -m 425 1000 425 400;", 1)
            rmlockcnt -= 1
        EnterShellCmd("hilog -w stop", 1)
        EnterShellCmd("cd /data/log/hilog && tar -cf system_start_log_{}.tar *".format(args.device_num), 1)
        GetFileFromDev("/data/log/hilog/system_start_log_{}.tar".format(args.device_num), args.save_path)
        SendFileToDev(os.path.normpath(os.path.join(args.anwser_path, "launcher.pngraw")),\
        "/data/screen_test/train_set")
        EnterShellCmd("/data/screen_test/printscreen -f /data/screen_test/launcher_{}.png".format(args.device_num), 1)
        GetFileFromDev("/data/screen_test/launcher_{}.pngraw".format(args.device_num), args.save_path)
        GetFileFromDev("/data/screen_test/launcher_{}.png".format(args.device_num), args.save_path)
        ConnectionJudgment()
        cmp_launcher = "cmp -l /data/screen_test/launcher_{}.pngraw \
        /data/screen_test/train_set/launcher.pngraw | wc -l".format(args.device_num)
        p = EnterShellCmd(cmp_launcher, 1)
        num = re.findall(r'[-+]?\d+', p)
        PrintToLog(num)
        if type(num) == list and len(num) > 0 and int(num[0]) < 147456 and\
        p.find('No such file or directory', 0, len(p)) == -1:
            PrintToLog("SmokeTest:: launcher screenshot comparison is ok!")
            break
        elif rebootcnt >= 1:
            PrintToLog("SmokeTest:: launcher screenshot comparison failed, reboot and try!!!")
            EnterShellCmd("rm -rf /data/*;reboot")
            for i in range(5):
                EnterCmd("hdc_std list targets", 10)
        else:
            PrintToLog("SmokeTest:: launcher screenshot comparison failed")
            SysExit()

    PrintToLog("\nSmokeTest:: ########## First check key processes start ##############")
    lose_process = []
    process_pid = {}
    with open(os.path.normpath(os.path.join(args.tools_path, "resource/process.txt")), "r+") as f:
        text = f.read()
        two_check_process_list = text.split('#####')[1].split()[0:-1]
        other_process_list = text.split('#####')[2].split()
        for pname in two_check_process_list:
            pids = EnterCmd("hdc_std -t {} shell pidof {}".format(args.device_num, pname), 0, 1)
            try:
                pidlist = pids.split()
                int(pidlist[0])
                for pid in pidlist:
                    int(pid)
                process_pid[pname] = pidlist
            except:
                lose_process.append(pname)
        all_p = EnterShellCmd("ps -elf")
        for pname in other_process_list:
            findp = all_p.find(pname, 0, len(all_p))
            if findp == -1:
                lose_process.append(pname)

    if lose_process:
        PrintToLog("SmokeTest:: error: %s, These processes are not exist!!!" % lose_process)
        SysExit()
    else:
        PrintToLog("SmokeTest:: first processes check is ok")

    if "1/2" in args.test_num or "2/2" in args.test_num:
        EnterShellCmd("param set persist.ace.testmode.enabled 1", 1)
        EnterShellCmd("rm /data/log/hilog/*;hilog -r;hilog -Q pidoff;hilog -Q domainoff;hilog -G 512M;hilog -b D", 1)
        picture_path = os.path.normpath(os.path.join(args.tools_path, "DistributedTest\\testcases"))
        report_path = os.path.normpath(os.path.join(args.tools_path, "DistributedTest\\testcases\\report.txt"))
        if args.test_num == "2/2":
            EnterShellCmd("ifconfig eth0 192.168.0.1", 1)
            ping_result = EnterShellCmd("ping 192.168.0.2 -i 1 -c 2", 3)
            file_is_exist = EnterShellCmd("cd /data; find . -name report.txt")
            ping_cnt = 0
            wait_cnt = 0
            while "2 packets transmitted, 2 received" not in ping_result and ping_cnt < 60:
                ping_result = EnterShellCmd("ping 192.168.0.2 -i 1 -c 2", 3)
                ping_cnt += 1
            if ping_cnt == 60:
                PrintToLog("SmokeTest:: Ping failed, timeout of 3 minutes")
                SysExit()
            while "report.txt" not in file_is_exist and wait_cnt < 60:
                PrintToLog("SmokeTest:: waiting for the distributed test to end ")
                file_is_exist = EnterShellCmd("cd /data; find . -name report.txt", 3)
                wait_cnt += 1
        elif args.test_num == "1/2":
            EnterShellCmd("ifconfig eth0 192.168.0.2", 1)
            ping_result = EnterShellCmd("ping 192.168.0.1 -i 1 -c 2", 3)
            ping_cnt = 0
            while "2 packets transmitted, 2 received" not in ping_result and ping_cnt < 60:
                ping_result = EnterShellCmd("ping 192.168.0.1 -i 1 -c 2", 3)
                ping_cnt += 1
            if ping_cnt == 60:
                PrintToLog("SmokeTest:: Ping failed, timeout of 3 minutes")
            PrintToLog("SmokeTest:: ##### case 0 : distributed test start #####")
            execute_path = os.path.normpath(os.path.join(args.tools_path, "DistributedTest"))
            PrintToLog("SmokeTest:: execute_path {}".format(execute_path))
            os.system("cd {} && python main.py run -l DistributedTest".format(execute_path))
            distributed_result = ""
            try:
                with open(report_path, mode='r', encoding='utf-8', errors='ignore') as f:
                    f.seek(0)
                    distributed_result = f.read()
                f.close()
            except Exception as reason:
                PrintToLog("SmokeTest:: report.txt is not exist!")
            if "distributedcalc" in distributed_result:
                picture_save(picture_path)
                PrintToLog("SmokeTest:: testcase 0, distributed is ok!")
            else:
                picture_save(picture_path)
                PrintToLog("SmokeTest:: error:testcase 0, distributed failed!")
        EnterShellCmd("ifconfig eth0 down", 1)

    try:
        args.test_num.index('/')
        idx_total = args.test_num.split('/')
        if len(idx_total) != 2:
            PrintToLog("SmokeTest:: test_num is invaild !!!")
            SysExit()
        elif idx_total[1] == '1':
            idx_list = list(range(1, len(all_app)))
        else:
            idx_list = global_pos['DEVICE_{}'.format(idx_total[0])]
    except ValueError as e:
        PrintToLog(e)
        idx_list = list(map(eval, args.test_num.split()))
    PrintToLog("SmokeTest:: start to carry out the following testcases: ")
    PrintToLog("SmokeTest:: testcase number: {} ".format(idx_list))

    fail_idx_list = []
    fail_name_list = []
    smoke_first_failed = ''
    for idx in idx_list:
        single_app = all_app[idx]
        sys.stdout.flush()
        call_app_cmd = single_app['entry']
        capture_screen_cmd = "/data/screen_test/printscreen -f /data/screen_test/{}_{}"
        cmp_cmd = "cmp -l /data/screen_test/{}_{} /data/screen_test/train_set/{} | wc -l"
        PrintToLog("\nSmokeTest:: ##### case {} : {} test start #####".format(idx, single_app['app_name']))
        with open(os.path.join(args.save_path, 'test_{}.bat'.format(args.device_num)),\
        mode='a', encoding='utf-8') as cmd_f:
            cmd_f.write("\nSmokeTest::::::case {} --- {} test start \n".format(idx, single_app['app_name']))
        cmd_f.close()
        testcnt = 3
        while testcnt:
            testok = 0
            if testcnt != 3:
                PrintToLog("SmokeTest:: this testcase try again >>>>>>:\n")
                with open(os.path.join(args.save_path, 'test_{}.bat'.format(args.device_num)),\
                mode='a', encoding='utf-8') as cmd_f:
                    cmd_f.write("\nSmokeTest::::::Last failed, try again \n")
                cmd_f.close()
            if idx == 2 or idx == 8:
                testcnt = 1
            if single_app['entry'] != "":
                EnterShellCmd(call_app_cmd, 5)
            PrintToLog("SmokeTest:: execute command {}".format(single_app['all_actions']))
            raw_pic_name = ''
            pic_name = ''
            for single_action in single_app['all_actions']:
                if type(single_action[1]) == str and single_action[1] == 'shot_cmd':
                    if len(single_action) == 3:
                        pic_name = "{}{}".format(single_action[2], ".png")
                        raw_pic_name = single_action[2] + ".pngraw"
                    else:
                        pic_name = "{}{}".format(single_app['app_name'], ".png")
                        raw_pic_name = single_app['app_name'] + ".pngraw"
                    EnterShellCmd("rm /data/screen_test/{}_{}*".format(4 - testcnt, pic_name), 1)
                    EnterShellCmd(capture_screen_cmd.format(4 - testcnt, pic_name), 1)
                    GetFileFromDev("/data/screen_test/{}_{}".format(4 - testcnt, pic_name), args.save_path)
                    next_cmd = ""
                elif type(single_action[1]) == str and single_action[1] == 'cmp_cmd-level':
                    next_cmd = ""
                    sys.stdout.flush()
                    EnterShellCmd("rm /data/train_set/{}".format(raw_pic_name), 1)
                    SendFileToDev(os.path.normpath(os.path.join(args.anwser_path, raw_pic_name)),\
                    "/data/screen_test/train_set")
                    new_cmp_cmd = cmp_cmd.format(4 - testcnt, raw_pic_name, raw_pic_name)
                    if len(single_action) == 3:
                        tolerance = single_action[2]
                    else:
                        tolerance = global_pos['cmp_cmd-level'][1]
                    PrintToLog("SmokeTest:: start to contrast screenshot")
                    p = EnterShellCmd(new_cmp_cmd, single_action[0])
                    num = re.findall(r'[-+]?\d+', p)
                    PrintToLog("SmokeTest:: contrast pixel difference {}".format(num))
                    if type(num) == list and len(num) > 0 and int(num[0]) < tolerance and\
                    p.find('No such file or directory', 0, len(p)) == -1:
                        if testok == 0:
                            testok = 1
                        PrintToLog("SmokeTest:: {} screenshot check is ok!".format(raw_pic_name))
                    else:
                        testok = -1
                        PrintToLog("SmokeTest:: {} screenshot check is abnarmal!".format(raw_pic_name))
                    sys.stdout.flush()
                    if testok == 1 or testcnt == 1 or smoke_first_failed != '':
                        old_name = os.path.normpath(os.path.join(args.save_path, "{}_{}".format(4 - testcnt, pic_name)))
                        GetFileFromDev("/data/screen_test/{}_{}".format(4 - testcnt, raw_pic_name), args.save_path)
                        os.system("rename {} {}".format(old_name, pic_name))
                        os.system("rename {}raw {}raw".format(old_name, pic_name))
                    raw_pic_name = ''
                elif type(single_action[1]) == str and single_action[1] == 'install_hap':
                    next_cmd = ""
                    if len(single_action) == 3:
                        EnterCmd("hdc_std -t {} install \"{}\"".format(args.device_num,\
                        os.path.normpath(os.path.join(args.tools_path, single_action[2]))))
                elif type(single_action[1]) == str and single_action[1] == 'get_file_from_dev':
                    next_cmd = ""
                    if len(single_action) == 3:
                        EnterCmd("hdc_std -t {} file recv \"{}\" \"{}\"".format(args.device_num,\
                        single_action[2], os.path.normpath(args.save_path)))
                elif type(single_action[1]) == str and single_action[1] == 'send_file_to_dev':
                    next_cmd = ""
                    if len(single_action) == 4:
                        EnterCmd("hdc_std -t {} file send \"{}\" \"{}\"".format(args.device_num,\
                        os.path.normpath(os.path.join(args.tools_path, single_action[2])), single_action[3]))
                elif type(single_action[1]) == str and single_action[1] == 'connect_wifi':
                    next_cmd = ""
                    ConnectToWifi(args.tools_path)
                elif type(single_action[1]) == str and single_action[1] == 'sandbox_path_check':
                    next_cmd = ""
                    if sandbox_check("com.ohos.medialibrary.medialibrarydata") == 1 and testok == 1:
                        testok = 1
                    else:
                        testok = -1
                elif type(single_action[1]) == str and single_action[1] == 'photo_check':
                    next_cmd = ""
                    if ImageCheck("{}\\media_library.db".format(os.path.normpath(args.save_path)), 1) == 1 and testok == 1:
                        testok = 1
                    else:
                        testok = -1
                elif type(single_action[1]) == str and single_action[1] == 'process_check':
                    next_cmd = ""
                    if len(single_action) == 3:
                        p = EnterShellCmd("ps -elf", single_action[0])
                        result = "".join(p)
                        findsome = result.find(single_action[2], 0, len(result))
                        if findsome != -1 and testok == 1:
                            testok = 1
                            PrintToLog("SmokeTest:: \"{}\" is ok, find process \"{}\"!".format(single_action[1],\
                            single_action[2]))
                        else:
                            testok = -1
                            PrintToLog("SmokeTest:: \"{}\" failed, not find process \"{}\"!".format(single_action[1],\
                            single_action[2]))
                        sys.stdout.flush()
                elif type(single_action[1]) == str and single_action[1] == 'process_crash_check':
                    next_cmd = ""
                    if len(single_action) == 3:
                        p = EnterShellCmd("cd /data/log/faultlog/temp && grep \"Process name\" -rnw ./",\
                        single_action[0])
                        result = "".join(p)
                        findsome = result.find(single_action[2], 0, len(result))
                        if findsome != -1:
                            testok = -1
                            PrintToLog("SmokeTest:: \"{}\" error:find fatal crash \"{}\"!".format(single_action[1],\
                            single_action[2]))
                            SysExit()
                        else:
                            testok = 1
                            PrintToLog("SmokeTest:: \"{}\" result is ok, not find fatal\
                            crash \"{}\"!".format(single_action[1], single_action[2]))
                        sys.stdout.flush()
                elif type(single_action[1]) == str:
                    if single_action[1] not in single_app.keys():
                        target_ = global_pos[single_action[1]]
                    else:
                        target_ = single_app[single_action[1]]
                    if type(target_[0]) == str:
                        next_cmd = ""
                        p = EnterShellCmd(target_[0], single_action[0])
                        result = "".join(p)
                        if len(target_) > 1:
                            findsome = result.find(target_[1], 0, len(result))
                            if findsome != -1:
                                testok = 1
                                PrintToLog("SmokeTest:: \"{}\" check result is ok, find \"{}\"!".format(target_[0],\
                                target_[1]))
                            else:
                                testok = -1
                                PrintToLog("SmokeTest:: \"{}\" result is not ok, not find \"{}\"!".format(target_[0],\
                                target_[1]))
                            sys.stdout.flush()
                    else:
                        next_cmd = "uinput -M -m {} {} -c 0".format(target_[0], target_[1])
                else:
                    next_cmd = "uinput -M -m {} {} -c 0".format(single_action[1], single_action[2])
                EnterShellCmd(next_cmd, single_action[0])

            if testok == 1:
                PrintToLog("SmokeTest:: testcase {}, {} is ok!".format(idx, single_app['app_name']))
                testcnt = 0
            elif testok == -1 and smoke_first_failed == '':
                if testcnt == 1:
                    fail_idx_list.append(idx)
                    fail_name_list.append(single_app['app_name'])
                    smoke_first_failed = single_app['app_name']
                    PrintToLog("SmokeTest:: error:testcase {}, {} is failed!".format(idx, single_app['app_name']))
                testcnt -= 1
            elif testok == -1 and smoke_first_failed != '':
                fail_idx_list.append(idx)
                fail_name_list.append(single_app['app_name'])
                PrintToLog("SmokeTest:: error:testcase {}, {} is failed!".format(idx, single_app['app_name']))
                testcnt = 0
            else:
                testcnt = 0
            ConnectionJudgment()

    PrintToLog("\nSmokeTest:: ########## Second check key processes start ##############")
    second_check_lose_process = []
    for pname in two_check_process_list:
        pids = EnterCmd("hdc_std -t {} shell pidof {}".format(args.device_num, pname), 0, 1)
        try:
            pidlist = pids.split()
            if process_pid[pname] != pidlist:
                if pname in two_check_process_list:
                    PrintToLog("SmokeTest:: error: pid of %s is different the first check" % pname)
                else:
                    PrintToLog("SmokeTest:: warnning: pid of %s is different the first check" % pname)
            elif len(pidlist) != 1:
                if pname in two_check_process_list:
                    PrintToLog("SmokeTest:: error: pid of %s is not only one" % pname)
                else:
                    PrintToLog("SmokeTest:: warnning: pid of %s is not only one" % pname)
        except:
            second_check_lose_process.append(pname)

    if second_check_lose_process:
        PrintToLog("SmokeTest:: error: pid of %s is not exist" % pname)
    else:
        PrintToLog("SmokeTest:: second processes check is ok")

    EnterShellCmd("cd /data/log/faultlog/temp && grep \"Process name\" -rnw ./", 1)
    EnterShellCmd("cd /data/log/faultlog/faultlogger && grep \"Process name\" -rnw ./", 1)

    fail_str_list = [str(x) for x in fail_idx_list]
    reboot_test_num = " ".join(fail_str_list)
    if len(fail_idx_list) != 0:
        PrintToLog("SmokeTest:: failed testcase number: {} ".format(fail_str_list))
        PrintToLog("SmokeTest:: check \"reboot\" in reboot.txt".format(args.save_path))
        with open(os.path.normpath(os.path.join(args.tools_path, "reboot.txt")), mode='a+') as f:
            f.seek(0)
            reboot_result = f.read()
        f.close()
        if len(reboot_result) < 1 and rebootcnt >= 1:
            PrintToLog("SmokeTest:: \"reboot\" is not found in the reboot.txt")
            PrintToLog("SmokeTest:: the device will reboot and try the failed testcase")
            PrintToLog("SmokeTest:: mkdir {}\\reboot".format(args.save_path))
            os.system("mkdir {}\\reboot".format(args.save_path))
            PrintToLog("SmokeTest:: write \"reboot\" into reboot.txt".format(args.save_path))
            with open(os.path.normpath(os.path.join(args.tools_path, "reboot.txt")), mode='w') as f:
                f.write("reboot")
            f.close()
            PrintToLog("SmokeTest:: error: name {}, index {}, failed, rm /data/* and reboot".format(fail_name_list,\
            fail_idx_list))
            EnterShellCmd("rm -rf /data/* && reboot")
            reboot_result_list = EnterCmd("hdc_std list targets", 2)
            number = 0
            while args.device_num not in reboot_result_list and number < 15:
                reboot_result_list = EnterCmd("hdc_std list targets", 2)
                number += 1
            EnterShellCmd("rm /data/log/hilog/*;hilog -r;hilog -w start -l 400000000 -m none", 1)
            py_cmd = os.system("python {}\\resource\\capturescreentest.py --config \
            {}\\resource\\app_capture_screen_test_config.json --anwser_path {} \
            --save_path {}\\reboot --tools_path {} --device_num {} --test_num \"{}\"".format(args.tools_path, \
            args.tools_path, args.anwser_path, args.save_path, args.tools_path, args.device_num, reboot_test_num))
            if py_cmd == 0:
                sys.exit(0)
            elif py_cmd == 98:
                sys.exit(98)
            elif py_cmd == 99:
                sys.exit(99)
            else:
                sys.exit(101)
        else:
            PrintToLog("SmokeTest:: error: name {}, index {}, these testcase is failed".format(fail_name_list,\
            fail_idx_list))
            SysExit()
    else:
        PrintToLog("SmokeTest:: all testcase is ok")
        PrintToLog("SmokeTest:: End of check, test succeeded!")
        sys.exit(0)