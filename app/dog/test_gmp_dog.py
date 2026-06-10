#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
加密狗工具 (GmpDogTool.exe)
功能：命令行工具，接受操作，返回 JSON 数据
使用：
  GmpDogTool.exe find          # 查找狗，返回 {"success":1}
  GmpDogTool.exe get_bid       # 获取绑定 ID，返回 {"success":1,"bid":"ID"}
  GmpDogTool.exe set_bid SN123 # 设置绑定 ID，返回 {"success":1}
  GmpDogTool.exe reset         # 重置狗，返回 {"success":1}
  GmpDogTool.exe verify_user   # User PIN 验证，返回 {"success":1}
  GmpDogTool.exe verify_so     # SO PIN 验证，返回 {"success":1}
失败返回 {"success":0,"error":"描述"}
"""

import sys
import json
import argparse
from gmp_dog import GmpDog  # 导入你的 GmpDog 类

def main():
    parser = argparse.ArgumentParser(description="加密狗工具")
    parser.add_argument("action", choices=["find", "get_bid", "set_bid", "reset", "verify_user", "verify_so"],
                        help="操作类型")
    parser.add_argument("sn", nargs="?", default=None,
                        help="绑定 ID（仅 set_bid 用）")
    # args = parser.parse_args()
    dog_status = 'old'

    dog = GmpDog()
    result = {"success": 0, "error": ""}
    BID = None

    try:
        
        # if dog.findDog():
        #     result["success"] = 1
        # else:
        #     result["error"] = dog.getLastError()

        # # # 查询id
        if dog.findDog():  # 先找狗
            bid = dog.getBindId()
            if bid == 'new_dog':
                assert bid == 'new_dog'
            elif bid:
                result["success"] = 1
                result["bid"] = bid
            else:
                result["error"] = dog.getLastError()
        else:
            result["error"] = dog.getLastError()

        # 绑定id
        if dog.findDog():
            b_id = dog.generate_bid()
            BID = bid
            if dog.setBindId(b_id):
                result["success"] = 1
            else:
                result["error"] = dog.getLastError()
        else:
            result["error"] = dog.getLastError()
        
        # 验证id
        if dog.findDog():  # 先找狗
            bid = dog.getBindId()
            if bid:
                result["success"] = 1
                result["bid"] = bid
            else:
                result["error"] = dog.getLastError()
        else:
            result["error"] = dog.getLastError()

        # 验证硬件是否更换
        verify_hardware = dog.verify_hardware()
        print(verify_hardware)
        
        # if dog.findDog() and dog.open():
        #     if dog.verify(use_so=True, bid=BID):
        #         result["success"] = 1
        #     else:
        #         result["error"] = dog.getLastError()
        #     dog.close()
        # else:
        #     result["error"] = dog.getLastError()
    
        # # # 重置狗
        # if dog.findDog():
        #     if dog.reset():
        #         result["success"] = 1
        #     else:
        #         result["error"] = dog.getLastError()
        # else:
        #     result["error"] = dog.getLastError()


        # if dog.findDog() and dog.open():
        #     if dog.verify(use_so=True):
        #         result["success"] = 1
        #     else:
        #         result["error"] = dog.getLastError()
        #     dog.close()
        # else:
        #     result["error"] = dog.getLastError()

    except Exception as e:
        result["error"] = str(e)

    finally:
        dog.close()

    print(json.dumps(result, ensure_ascii=False))  # 输出 JSON

if __name__ == "__main__":
    main()