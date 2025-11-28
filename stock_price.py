# -*- coding:utf-8 -*-
 
import tushare as ts
import os
import threading
import time
 
def get():
    i = os.system("cls")                                          # 清屏操作

    df = ts.get_realtime_quotes(['sh','sz','601168'])
 
    #print(df['code'][1] + "  " + df['name'][1] + "  " + str(round((float(df['price'][1]) - float(df['pre_close'][1])) / float(df['pre_close'][1]) * 100, 2)) + "%" + "  ")
    print(df['code'][0] + "  " + df['name'][0] + "  " + str(round((float(df['price'][0]) - float(df['pre_close'][0])) / float(df['pre_close'][0]) * 100, 2)) + "%" + "  ")
    print(df['code'][1] + "  " + df['name'][1] + "  " + str(round((float(df['price'][1]) - float(df['pre_close'][1])) / float(df['pre_close'][1]) * 100, 2)) + "%" + "  ")

    print(df['code'][2] + "  " + df['name'][2] + "  " + str(round((float(df['price'][2]) - float(df['pre_close'][2])) / float(df['pre_close'][2]) * 100, 2)) + "%" + "  ")
    print(df['code'][2] + "  "+ df['time'][2] + "  " + str(float(df['price'][2]))+ "  " + str(df['volume'][2]))

    global timer
    timer = threading.Timer(5.0, get, [])
    timer.start()
 
if __name__ == "__main__":
    try:
        timer = threading.Timer(3.0, get, [])
        timer.start()
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        timer.cancel()
        print("\n程序已安全退出")