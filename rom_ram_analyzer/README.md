[toc]

# Rom_analyzer.py

## 功能介绍

基于BUILD.gn、bundle.json、编译产物system_module_info.json、out/{product_name}/packages/phone目录下的编译产物，分析各子系统及部件的rom大小。

结果以json与xls格式进行存储，其中，json格式是必输出的，xls格式需要-e参数控制。

## 使用说明

前置条件：

1. 获取整个rom_ram_analyzer目录
1. 对系统进行编译
1. linux平台
1. python3.8及以后
1. 安装requirements
    ```txt
    xlwt==1.3.0
    ```

命令介绍：

1. `-h`或`--help`命令查看帮助
   ```shell
   > python3 rom_analyzer.py -h
   usage: rom_analyzer.py [-h] [-v] -p PROJECT_PATH -j MODULE_INFO_JSON -n PRODUCT_NAME -d PRODUCT_DIR [-o OUTPUT_FILE] [-e EXCEL]
   
   analyze rom size of component.
   
   optional arguments:
     -h, --help            show this help message and exit
     -v, -version          show program\'s version number and exit
     -p PROJECT_PATH, --project_path PROJECT_PATH
                           root path of openharmony. eg: -p ~/openharmony
     -j MODULE_INFO_JSON, --module_info_json MODULE_INFO_JSON
                           path of out/{product_name}/packages/phone/system_module_info.json
     -n PRODUCT_NAME, --product_name PRODUCT_NAME
                           product name. eg: -n rk3568
     -d PRODUCT_DIR, --product_dir PRODUCT_DIR
                           subdirectories of out/{product_name}/packages/phone to be counted.eg: -d system -d vendor
     -o OUTPUT_FILE, --output_file OUTPUT_FILE
                           basename of output file, default: rom_analysis_result. eg: demo/rom_analysis_result
     -e EXCEL, --excel EXCEL
                           if output result as excel, default: False. eg: -e True
   ```
1. 使用示例
   ```shell
   python3 rom_analyzer.py -p ~/nomodify_oh/ -j ../system_module_info.json -n rk3568 -d system -d vendor -d updater -o demo/demo -e True
   # oh：rootpath of openharmony
   # rk3568: product_name, same as out/{product_name}
   # demo/demo: path of output file, where the second 'demo' is the basename of output file
   # -e True：output result in excel format additionally
   ```

## 输出格式说明(json)


```json
{
   子系统名: {
       "size": 整个子系统输出文件的总大小,
       "file_count":  整个子系统产生的文件数,
       输出文件名: 本文件的大小,
       ...
   },  
   ...
}
```

# ram_analyzer.py

## 功能介绍

基于out/{product_name}/packages/phone下所有cfg文件、out/{product_name}/packages/phone/system/profile下所有xml文件，分析各进程及对应部件的ram占用（默认取Pss）

结果以json与xls格式存储，其中，json格式是必输出的，xls格式需要-e参数控制。

## 使用说明

前置条件：

1. 获取整个rom_ram_analyzer目录
2. hdc可用
2. 设备已连接
3. python3.8及以后
4. 安装requirements
   ```txt
   xlwt==1.3.0
   ```
5. 准备好相关数据：
   1. out/{product_name}/packages/phone下所有cfg文件，并将其放置于同一个目录中（ps：同名文件仅保存一份即可）
   1. out/{product_name}/packages/phone/system/profile下所有xml文件
6. 运行rom_analyzer.py产生的json结果一份（即-o参数对应的文件，默认rom_analysis_result.json）

命令介绍：

1. 使用`-h`或`--help`查看帮助
   ```shell
   > python .\ram_analyzer.py -h
   usage: ram_analyzer.py [-h] [-v] -x XML_PATH -c CFG_PATH [-j ROM_RESULT] -n DEVICE_NUM [-o OUTPUT_FILENAME] [-e EXCEL]
   
   analyze ram size of component
   
   optional arguments:
     -h, --help            show this help message and exit
     -v, -version          show program\'s version number and exit
     -x XML_PATH, --xml_path XML_PATH
                           path of xml file. eg: -x ~/openharmony/out/rk3568/packages/phone/system/profile
     -c CFG_PATH, --cfg_path CFG_PATH
                           path of cfg files. eg: -c ./cfgs/
     -j ROM_RESULT, --rom_result ROM_RESULT
                           json file produced by rom_analyzer_v1.0.py, default: ./rom_analysis_result.json.eg: -j ./demo/rom_analysis_result.json
     -n DEVICE_NUM, --device_num DEVICE_NUM
                           device number to be collect hidumper info. eg: -n 7001005458323933328a01fce16d3800
     -o OUTPUT_FILENAME, --output_filename OUTPUT_FILENAME
                           base name of output file, default: rom_analysis_result. eg: -o ram_analysis_result
     -e EXCEL, --excel EXCEL
                           if output result as excel, default: False. eg: -e True
   ```
2. 使用示例：
   ```shell
   python .\ram_analyzer.py -x .\profile\ -c .\init\ -n 7001005458323933328a01fce16d3800 -j .\rom_analysis_result.json -o /demo/demo -e True
   # demo/demo: path of output file, where the second 'demo' is the basename of output file
   # -e True：output result in excel format additionally
   ```
## 输出格式说明（json）
```json
{
   进程名:{
       "size": 本进程占用内存的大小,
       部件名: {
           elf文件名: elf文件大小 
           ...
       }
       ...
   },
   ...
}
```