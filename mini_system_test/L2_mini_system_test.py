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
import datetime

def GetDirSize(dir_path):
    if  not os.path.exists(dir_path):
        PrintToLog("\n\nERROR: %s, dir are not exist!!!\n" % dir_path)
        PrintToLog("End of check, test failed!")
        sys.exit(99)
    size = 0
    for root, dirs, files in os.walk(dir_path):
        for name in files:
            if not os.path.islink(os.path.join(root, name)):
                sz = os.path.getsize(os.path.join(root, name))
                #print('{} : {}byte'.format(os.path.join(root, name), sz))
                size += sz
    PrintToLog('total size: {:.2f}M'.format(size/1024/1024))
    return size

def PrintToLog(str):
    time = datetime.datetime.now()
    str = "[{}] {}".format(time, str)
    print(str)
    with open(os.path.join(args.save_path, 'L2_mini_test_{}.log'.format(args.device_num)), mode='a', encoding='utf-8') as log_file:
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
        with open(os.path.join(args.save_path, 'mini_test_{}.bat'.format(args.device_num)), mode='a', encoding='utf-8') as cmd_file:
            cmd_file.write(mycmd + '\n')
        cmd_file.close()
        PrintToLog(mycmd)
        PrintToLog(result)
        sys.stdout.flush()
    if waittime != 0:
        time.sleep(waittime)
        if printresult == 1:
            with open(os.path.join(args.save_path, 'mini_test_{}.bat'.format(args.device_num)), mode='a', encoding='utf-8') as cmd_file:
                cmd_file.write("ping -n {} 127.0.0.1>null\n".format(waittime))
            cmd_file.close()
    return result

def EnterShellCmd(shellcmd, waittime = 0, printresult = 1):
    if shellcmd == "":
        return
    cmd = "hdc_std -t {} shell \"{}\"".format(args.device_num, shellcmd)
    return EnterCmd(cmd, waittime, printresult)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='manual to this script')
    parser.add_argument('--save_path', type=str, default = 'D:\\DeviceTestTools\\screenshot')
    parser.add_argument('--device_num', type=str, default = 'null')
    parser.add_argument('--archive_path', type=str, default = 'Z:\workspace\ohos_L2\ohos\out\\rk3568\packages\phone')
    args = parser.parse_args()

    if args.device_num == 'null':
        result = EnterCmd("hdc_std list targets", 1, 0)
        print(result)
        args.device_num = result.split()[0]

    PrintToLog("\n\n########## First check key processes start ##############")
    lose_process = []
    process_pid = {}

    two_check_process_list = ['huks_service', 'hilogd', 'hdf_devmgr', 'samgr', 'foundation', 'accesstoken_ser',]
    other_process_list = ['softbus_server', 'deviceauth_service']

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
        PrintToLog("\n\nERROR: %s, These processes are not exist!!!\n" % lose_process)
        PrintToLog("End of check, test failed!")
        sys.exit(99)
    else:
        PrintToLog("First processes check is ok\n")

    # check processes usage
    res = EnterCmd("hdc_std -t {} shell hidumper --mem".format(args.device_num), 0, 1)
    process_usage = int(res.split(':')[-1].split()[0]) / 1024
    if process_usage > 40:
        PrintToLog(
            "ERROR: Processes usage cannot be greater than 40M, but currently it's actually %.2fM" % process_usage)
        PrintToLog("End of check, test failed!")
        sys.exit(99)

    time.sleep(10)

    #key processes second check, and cmp to first check
    PrintToLog("\n\n########## Second check key processes start ##############")
    second_check_lose_process = []
    #for pname in two_check_process_list + other_process_list:
    for pname in two_check_process_list:
        pids = EnterCmd("hdc_std -t {} shell pidof {}".format(args.device_num, pname), 0, 1)
        try:
            pidlist = pids.split()
            if process_pid[pname] != pidlist:
                if pname in two_check_process_list:
                    PrintToLog("ERROR: pid of %s is different the first check" % pname)
                    PrintToLog("SmokeTest find some fatal problems!")
                    PrintToLog("End of check, test failed!")
                    sys.exit(99)
                else:
                    PrintToLog("WARNNING: pid of %s is different the first check" % pname)
            elif len(pidlist) != 1:
                if pname in two_check_process_list:
                    PrintToLog("ERROR: pid of %s is not only one" % pname)
                    PrintToLog("SmokeTest find some fatal problems!")
                    PrintToLog("End of check, test failed!")
                    sys.exit(99)
                else:
                    PrintToLog("WARNNING: pid of %s is not only one" % pname)
        except:
            second_check_lose_process.append(pname)

    if second_check_lose_process:
        PrintToLog("ERROR: pid of %s is not exist" % pname)
        PrintToLog("SmokeTest find some fatal problems!")
        PrintToLog("End of check, test failed!")
        sys.exit(99)
    else:
        PrintToLog("Second processes check is ok\n")
    
    target_dir = os.path.normpath(os.path.join(args.archive_path, "system"))
    PrintToLog(target_dir)
    ret_size = GetDirSize(target_dir)/1024/1024
    PrintToLog('Size of system is :{:.2f}M'.format(ret_size))
    if ret_size > 50:
        PrintToLog('ERROR: Size of system({:.2f}M) is over the upper limit(50M)'.format(ret_size))
        PrintToLog("End of check, test failed!")
        sys.exit(99)

    target_dir = os.path.normpath(os.path.join(args.archive_path, "data"))
    ret_size = GetDirSize(target_dir)/1024/1024
    PrintToLog('Size of data is :{:.2f}M'.format(ret_size))
    if ret_size > 50:
        PrintToLog('ERROR: Size of data({:.2f}M) is over the upper limit(50M)'.format(ret_size))
        PrintToLog("End of check, test failed!")
        sys.exit(99)

    target_dir = os.path.normpath(os.path.join(args.archive_path, "updater"))
    ret_size = GetDirSize(target_dir)/1024/1024
    PrintToLog('Size of updater is :{:.2f}M'.format(ret_size))
    if ret_size > 50:
        PrintToLog('ERROR: Size of updater({:.2f}M) is over the upper limit(50M)'.format(ret_size))
        PrintToLog("End of check, test failed!")
        sys.exit(99)

    target_dir = os.path.normpath(os.path.join(args.archive_path, "vendor"))
    ret_size = GetDirSize(target_dir)/1024/1024
    PrintToLog('Size of vendor is :{:.2f}M'.format(ret_size))
    if ret_size > 50:
        PrintToLog('ERROR: Size of vendor({:.2f}M) is over the upper limit(50M)'.format(ret_size))
        PrintToLog("End of check, test failed!")
        sys.exit(99)

    PrintToLog("All testcase is ok")
    PrintToLog("End of check, test succeeded!")
    sys.exit(0)
