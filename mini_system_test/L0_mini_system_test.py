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
import serial
import threading

def GetDirSize(dir_path):
    if  not os.path.exists(dir_path):
        PrintToLog("\n\nERROR: %s, dir are not exist!!!\n" % dir_path)
        PrintToLog("End of check, test failed!")
        sys.exit(99)
    size = 0
    for root, dirs, files in os.walk(dir_path):
        for name in files:
            sz = os.path.getsize(os.path.join(root, name))
            print('{} : {}byte'.format(os.path.join(root, name), sz))
            size += sz
    PrintToLog('total size: {:.2f}M'.format(size/1024/1024))
    return size

def PrintToLog(str):
    time = datetime.datetime.now()
    str = "[{}] {}".format(time, str)
    print(str)
    with open(os.path.join(args.save_path, 'L0_mini_test.log'), mode='a', encoding='utf-8') as log_file:
        console = sys.stdout
        sys.stdout = log_file
        print(str)
        sys.stdout = console
    log_file.close()

def WriteToComPort(com_port, cmd):
    len = com_port.write(cmd.encode('utf-8'))
    print('{}'.format(len))
    return

def ReadFromComPort(com_port, timeout):
    time_start = datetime.datetime.now()
    time_end = time_start
    #print((time_end - time_start).seconds)
    global com_output
    com_output = ''
    while (time_end - time_start).seconds < timeout:
        com_output_once = ''
        while com_port.inWaiting() > 0:
            com_output_once += com_port.read(com_port.inWaiting()).decode()
        if com_output_once != '':
            com_output += com_output_once
            print('{}'.format(com_output_once), end='')
        time_end = datetime.datetime.now()
    return com_output

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='manual to this script')
    parser.add_argument('--com_port', type=str, default = 'COM5')
    parser.add_argument('--com_baudrate', type=int, default = 115200)
    parser.add_argument('--save_path', type=str, default = 'D:\\DeviceTestTools\\screenshot')
    parser.add_argument('--archive_path', type=str, default = 'Z:\workspace\ohos_L2\ohos\out\hispark_pegasus\hispark_pegasus_mini_system')
    args = parser.parse_args()

    com_port = serial.Serial(args.com_port, args.com_baudrate)
    if com_port.isOpen():
        PrintToLog("{} is open successed".format(com_port))
    else:
        PrintToLog("{} is open failed".format(com_port))
        PrintToLog("End of check, test failed!")
        sys.exit(99)

    read_com_thread = threading.Thread(target=ReadFromComPort, args=(com_port, 10))
    read_com_thread.setDaemon(True)
    print('read wait:')
    read_com_thread.start()
    time.sleep(1)
    WriteToComPort(com_port, '\r\n\r\n')
    WriteToComPort(com_port, 'AT+SYSINFO\r\n')
    print('enter AT+SYSINFO')
    time.sleep(3)
    hivew_proc_find = re.findall('hiview,id=\d{1,3},status=\d{1,10},pri=\d{1,3},size=', com_output)
    #Bootstrap_proc_find = re.findall('Bootstrap,id=\d{1,3},status=\d{1,10},pri=\d{1,3},size=', com_output)
    print(hivew_proc_find)
    if type(hivew_proc_find) == list and len(hivew_proc_find) > 0:
        PrintToLog('hivew_proc found')
    else:
        PrintToLog('hivew_proc not found')
        PrintToLog("End of check, test failed!")
        sys.exit(99)

    target_file = os.path.normpath(os.path.join(args.archive_path, "Hi3861_wifiiot_app_allinone.bin"))
    ret_size = os.path.getsize(target_file)/1024/1024
    PrintToLog('Size of Hi3861_wifiiot_app_allinone.bin : {:.2f}M'.format(ret_size))
    if ret_size > 1:
        PrintToLog('ERROR: Size of Hi3861_wifiiot_app_allinone.bin ({:.2f}M) is over the upper limit(1M)'.format(ret_size))
        target_dir = os.path.normpath(os.path.join(args.archive_path, "libs"))
        GetDirSize(target_dir)
        PrintToLog("End of check, test failed!")
        sys.exit(99)

    PrintToLog("End of check, test succeeded!")
    sys.exit(0)

