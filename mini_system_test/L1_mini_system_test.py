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
    with open(os.path.join(args.save_path, 'L1_mini_test.log'), mode='a', encoding='utf-8') as log_file:
        console = sys.stdout
        sys.stdout = log_file
        print(str)
        sys.stdout = console
    log_file.close()

def WriteToComPort(com_port, cmd):
    len = com_port.write(cmd.encode('utf-8'))
    #print('{}'.format(len))
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
    parser.add_argument('--com_port', type=str, default = 'COM8')
    parser.add_argument('--com_baudrate', type=int, default = 115200)
    parser.add_argument('--save_path', type=str, default = 'D:\\DeviceTestTools\\screenshot')
    parser.add_argument('--archive_path', type=str, default = 'D:\DeviceTestTools')
    args = parser.parse_args()

    com_port = serial.Serial(args.com_port, args.com_baudrate)
    if com_port.isOpen():
        PrintToLog("{} is open successed".format(com_port))
    else:
        PrintToLog("{} is open failed".format(com_port))
        PrintToLog("End of check, test failed!")
        sys.exit(99)
        
    res = com_port.write("free".encode('utf-8'));
    read_com_thread = threading.Thread(target=ReadFromComPort, args=(com_port, 10))
    read_com_thread.setDaemon(True)
    print('read wait:')
    read_com_thread.start()
    time.sleep(1)
    WriteToComPort(com_port, '\r\n\r\n\r\n')
    WriteToComPort(com_port, 'task\r\n')
    print('enter task')
    time.sleep(3)
    print(com_output)
    foundation_proc_find = re.findall('\d{1,4}\s*\d{1,4}\s*\d{1,4}\s*\d{1,4}.\d{1,4}\s*foundation', com_output)
    print(foundation_proc_find)
    if type(foundation_proc_find) == list and len(foundation_proc_find) > 0:
        PrintToLog('found foundation process')
    else:
        PrintToLog('not found foundation process')
        PrintToLog("End of check, test failed!")
        sys.exit(99)
    shell_proc_find = re.findall('\d{1,4}\s*\d{1,4}\s*\d{1,4}\s*\d{1,4}.\d{1,4}\s*shell', com_output)
    print(shell_proc_find)
    if type(shell_proc_find) == list and len(shell_proc_find) > 0:
        PrintToLog('found shell process')
    else:
        PrintToLog('not found shell process')
        PrintToLog("End of check, test failed!")
        sys.exit(99)
    apphilogcat_proc_find = re.findall('\d{1,4}\s*\d{1,4}\s*\d{1,4}\s*\d{1,4}.\d{1,4}\s*apphilogcat', com_output)
    print(apphilogcat_proc_find)
    if type(apphilogcat_proc_find) == list and len(apphilogcat_proc_find) > 0:
        PrintToLog('found apphilogcat process')
    else:
        PrintToLog('not found apphilogcat process')
        PrintToLog("End of check, test failed!")
        sys.exit(99)
    deviceauth_service_proc_find = re.findall('\d{1,4}\s*\d{1,4}\s*\d{1,4}\s*\d{1,4}.\d{1,4}\s*deviceauth_service', com_output)
    print(deviceauth_service_proc_find)
    if type(deviceauth_service_proc_find) == list and len(deviceauth_service_proc_find) > 0:
        PrintToLog('found deviceauth_service process')
    else:
        PrintToLog('not found deviceauth_service process')
        PrintToLog("End of check, test failed!")
        sys.exit(99)
    softbus_server_proc_find = re.findall('\d{1,4}\s*\d{1,4}\s*\d{1,4}\s*\d{1,4}.\d{1,4}\s*softbus_server', com_output)
    print(softbus_server_proc_find)
    if type(softbus_server_proc_find) == list and len(softbus_server_proc_find) > 0:
        PrintToLog('found softbus_server process')
    else:
        PrintToLog('not found softbus_server process')
        PrintToLog("End of check, test failed!")
        sys.exit(99)
    mem_find = re.findall('Mem:\s*\d*\s*\d*\s*\d*\s*\d*', com_output)
    print(mem_find)
    if len(mem_find) > 0:
        mem_size = int(mem_find[0].split()[2]) / 1024 / 1024
    else:
        PrintToLog('Error:can find memory usage info!')
        PrintToLog("End of check, test failed!")
        sys.exit(99)
    if mem_size > 25:
        PrintToLog(
            'Error:memory usage is over the upper limit(25M),now is {:.2f}'.format(mem_size))
        PrintToLog("End of check, test failed!")
        sys.exit(99)

    target_dir = os.path.normpath(os.path.join(args.archive_path, "rootfs"))
    ret_size = GetDirSize(target_dir)/1024/1024
    PrintToLog('Size of rootfs is ({:.2f}M)'.format(ret_size))
    if ret_size > 15:
        PrintToLog('ERROR: Size of rootfs({:.2f}M) is over the upper limit(15M)'.format(ret_size))
        PrintToLog("End of check, test failed!")
        sys.exit(99)

    target_dir = os.path.normpath(os.path.join(args.archive_path, "userfs"))
    ret_size = GetDirSize(target_dir)/1024/1024
    PrintToLog('Size of userfs is ({:.2f}M)'.format(ret_size))
    if ret_size > 15:
        PrintToLog('ERROR: Size of userfs({:.2f}M) is over the upper limit(15M)'.format(ret_size))
        PrintToLog("End of check, test failed!")
        sys.exit(99)

    PrintToLog("End of check, test succeeded!")
    sys.exit(0)
