import sys
from xdevice.__main__ import main_process
from testcases.set_sn import get_devices_sn

if __name__ == '__main__':
    get_devices_sn()
    argv = "{} {} {}".format(sys.argv[1], sys.argv[2], sys.argv[3])
    print(">>>>>>>:{}".format(argv))
    main_process(argv)