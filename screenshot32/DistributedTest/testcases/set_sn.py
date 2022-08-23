import encodings
import os
import re
from xml.dom.minidom import parse

def get_devices_sn():
    cmd_sn = os.popen("hdc_std list targets").read()
    device_sn = re.findall('[\w+]{32}', cmd_sn) + re.findall('[\w+]{16}', cmd_sn)
    dom_tree = parse('config\\user_config.xml')
    collection = dom_tree.documentElement
    sn1 = collection.getElementsByTagName('sn')[0]
    if len(device_sn[0]) == len(device_sn[1]):
        sn1.childNodes[0].data = "{};{}".format(device_sn[0], device_sn[1])
    else:
        sn1.childNodes[0].data = device_sn[0]
    with open('config\\user_config.xml', 'w', encoding='utf-8') as f:
        dom_tree.writexml(f, encoding='utf-8')
    f.close()

if __name__ == '__main__':
    get_devices_sn()