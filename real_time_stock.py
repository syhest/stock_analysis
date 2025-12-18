# -*- coding:utf-8 -*-
import pandas as pd
import numpy as np

import datetime
import time
import requests
import os
import argparse
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
import matplotlib.dates as mdates
import sqlite3
import json  # 添加json模块导入

# 设置中文显示
plt.rcParams['font.sans-serif'] = ['SimHei']
plt.rcParams['axes.unicode_minus'] = False

class StockDataFetcher:
    """股票数据获取器类，封装所有数据获取方法"""
    
    def __init__(self):
        """初始化会话"""
        self.session = requests.Session()
        self.today_data = None
        # 添加更完整的请求头，模拟浏览器请求
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Referer': 'http://quote.eastmoney.com/',
            'Accept-Encoding': 'gzip, deflate',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Connection': 'keep-alive'
        })
    
    def get_market_code(self, code):
        """根据股票代码判断市场类型"""
        if (code.startswith('00') or code.startswith('30')) and len(code) == 6:
            return 'sz'
        elif code.startswith('60') and len(code) == 6:
            return 'sh'
        elif (code.startswith('8') or code.startswith('4')) and len(code) == 6:
            return 'bj'
        else:
            return 'hk'

    def get_real_time_data(self, code):
        """
        获取港股或A股实时数据
        """
        try:
            if not code:
                print("股票代码为空")
                return None

            print(f"获取{code}的实时数据开始")
            market_code = self.get_market_code(code)
            print(f"market_code: {market_code}")
            
            if market_code == 'hk':
                # 优先使用新浪财经接口获取港股实时数据
                real_time_data = self._get_hk_stock_data_from_sina(code)
                if real_time_data:
                    return real_time_data
                else:
                    # 新浪财经接口失败，尝试使用东方财富网接口
                    print("新浪财经接口获取失败，尝试使用东方财富网接口")
                    return self._get_hk_stock_data_from_eastmoney(code)
            else:
                # 获取A股实时数据
                if market_code == 'sh':
                    sina_code = f"sh{code}"
                elif market_code == 'sz':
                    sina_code = f"sz{code}"
                elif market_code == 'bj':
                    sina_code = f"bj{code}"
                else:
                    print(f"未知的市场代码: {market_code}")
                    return None
                
                url = f"https://hq.sinajs.cn/list={sina_code}"
                print(f"A股URL: {url}")
                
                # 构建完整的请求头
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                    'Accept': '*/*',
                    'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
                    'Referer': 'https://finance.sina.com.cn/',
                    'Connection': 'keep-alive',
                    'Accept-Encoding': 'gzip, deflate, br'
                }
                
                response = self.session.get(url, headers=headers)
                print(f"响应状态码: {response.status_code}")
                print(f"响应内容类型: {response.headers.get('Content-Type')}")
                
                if response.status_code == 200:
                    # 解码响应内容
                    response.encoding = 'gb2312'
                    content = response.text
                    print(f"响应内容长度: {len(content)}")
                    print(f"响应内容: {content[:200]}...")
                    
                    # A股数据格式：var hq_str_sh600000="浦发银行,10.15,10.16,10.13,10.18,10.12,10.13,10.14,11443414,116052386.000,306800,10.13,125100,10.12,157500,10.11,123900,10.10,470400,10.14,301400,10.15,250400,10.16,138700,10.17,81700,10.18,2024-11-29,15:00:00,00"
                    data_str = content.split('"')[1]
                    data_list = data_str.split(',')
                    print(f"A股数据列表长度: {len(data_list)}")
                    
                    if len(data_list) >= 10:
                        return {
                            'symbol': code,
                            'name': data_list[0],
                            'price': float(data_list[3]),
                            'pre_close': float(data_list[2]),
                            'open': float(data_list[1]),
                            'high': float(data_list[4]),
                            'low': float(data_list[5]),
                            'volume': int(data_list[8]),
                            'amount': float(data_list[9]),
                            'time': data_list[-3] + ' ' + data_list[-2]
                        }
                    else:
                        print(f"A股数据不完整: {data_list}")
                        return None
                else:
                    print(f"请求失败，状态码: {response.status_code}")
                    # 打印响应内容以了解更多信息
                    print(f"响应内容: {response.text[:500]}...")
                    return None
        except Exception as e:
            print(f"获取实时数据错误: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def _get_hk_stock_data_from_sina(self, code):
        """
        使用新浪财经接口获取港股数据
        """
        url = f"https://hq.sinajs.cn/list=r_hk{code}"
        print(f"港股新浪财经URL: {url}")
        
        # 构建完整的请求头
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': '*/*',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Referer': 'https://finance.sina.com.cn/',
            'Connection': 'keep-alive',
            'Accept-Encoding': 'gzip, deflate, br'
        }
        
        response = self.session.get(url, headers=headers)
        print(f"新浪财经响应状态码: {response.status_code}")
        
        if response.status_code == 200:
            # 解码响应内容
            response.encoding = 'gb2312'
            content = response.text
            print(f"新浪财经响应内容长度: {len(content)}")
            print(f"新浪财经响应内容: {content[:200]}...")
            
            # 解析港股数据
            # 港股数据格式：var hq_str_r_hk00700="腾讯控股,351.600,351.600,349.200,351.800,346.000,349.200,349.400,24364946,8512798280,83900,349.200,11400,349.000,7900,348.800,1800,348.600,2700,348.400,15000,349.400,5200,349.600,2100,349.800,2300,350.000,1900,350.200,2024-11-29,16:08:01,00"
            if '"' in content:
                data_str = content.split('"')[1]
                data_list = data_str.split(',')
                print(f"港股数据列表长度: {len(data_list)}")
                
                if len(data_list) >= 10:
                    return {
                        'symbol': code,
                        'name': data_list[0],
                        'price': float(data_list[2]),
                        'pre_close': float(data_list[1]),
                        'open': float(data_list[3]),
                        'high': float(data_list[4]),
                        'low': float(data_list[5]),
                        'volume': int(data_list[8]),
                        'amount': float(data_list[9]),
                        'time': data_list[-2] + ' ' + data_list[-3]
                    }
                else:
                    print(f"港股数据不完整: {data_list}")
        return None
        
    def _get_hk_stock_data_from_eastmoney(self, code):
        """
        使用东方财富网接口获取港股数据
        """
        market_code = '116'  # 港股的东方财富市场代码
        secid = f"{market_code}.{code}"
        
        # 实时行情接口
        url = f"http://push2.eastmoney.com/api/qt/stock/get?fields=f1,f2,f3,f4,f5,f6,f43,f44,f45,f46,f57,f58,f59,f60,f61&secid={secid}&ut=f057cbcbce2a86e2866ab8877db1d059&fltt=2&invt=2"
        print(f"港股东方财富网URL: {url}")
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Referer': 'https://hkstock.eastmoney.com/',
            'Accept': '*/*',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Connection': 'keep-alive',
            'Accept-Encoding': 'gzip, deflate, br'
        }
        
        response = self.session.get(url, headers=headers)
        print(f"东方财富网响应状态码: {response.status_code}")
        
        if response.status_code == 200:
            # 解码响应内容
            response.encoding = 'utf-8'
            content = response.text
            print(f"东方财富网响应内容长度: {len(content)}")
            print(f"东方财富网响应内容: {content[:200]}...")
            
            # 解析JSON数据
            try:
                import json
                data = json.loads(content)
                print(f"东方财富网JSON解析结果状态码: {data.get('rc')}")
                
                if data.get('rc') == 0 and 'data' in data and data['data']:
                    stock_data = data['data']
                    
                    # 获取当前时间
                    import datetime
                    current_time = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    
                    return {
                        'symbol': code,
                        'name': stock_data.get('f58', code),  # 使用f58字段获取股票名称
                        'price': float(stock_data.get('f43', 0.0)),
                        'pre_close': float(stock_data.get('f57', 0.0)),
                        'open': float(stock_data.get('f46', 0.0)),
                        'high': float(stock_data.get('f44', 0.0)),
                        'low': float(stock_data.get('f45', 0.0)),
                        'volume': int(stock_data.get('f59', 0)),
                        'amount': float(stock_data.get('f60', 0.0)),
                        'time': current_time
                    }
                else:
                    print(f"东方财富网未获取到有效数据: {data.get('msg')}")
                    if 'data' in data:
                        print(f"数据部分: {data['data']}")
            except json.JSONDecodeError as e:
                print(f"东方财富网JSON解析失败: {e}")
        return None

    def get_stock_config(self, code, time_range):
        """
        根据股票代码和时间范围获取配置信息
        :param code: 股票代码
        :param time_range: 时间范围
        :return: 包含市场代码、referer、secid、klt、lmt的配置字典
        """
        if code.startswith('6'):
            # 上证股票
            market_code = '1'
            referer = 'https://quote.eastmoney.com/'
        elif code.startswith(('00', '000', '001', '002', '003', '30')) and len(code) == 6:
            # 深证股票：000xxx（深市主板）、002xxx（中小板）、300xxx（创业板）
            market_code = '0'
            referer = 'https://quote.eastmoney.com/'
        else:
            # 港股股票（通常是5位或6位数字）
            market_code = '116'
            referer = 'https://hkstock.eastmoney.com/'
        
        # 构建东方财富网的secid
        secid = f"{market_code}.{code}"
        
        # 设置时间周期参数
        if time_range == 'year':
            klt = 104  # 年线
            lmt = 20  # 约20年的年线数据
        elif time_range == 'month':
            klt = 103  # 月线
            lmt = 36  # 约3年的月线数据
        elif time_range == 'week':
            klt = 102  # 周线
            lmt = 250  # 约5年的周线数据
        elif time_range == 'day':
            klt = 101  # 日线
            lmt = 100  # 约100个交易日的数据
        elif time_range == '1min':
            klt = 1  # 1分钟线
            lmt = 1000  # 默认获取1000条1分钟数据
        else:
            klt = 101  # 默认使用日线
            lmt = 100
        
        return {
            'market_code': market_code,
            'referer': referer,
            'secid': secid,
            'klt': klt,
            'lmt': lmt
        }
    
    def fetch_kline_data(self, secid, klt, lmt, referer):
        """
        从东方财富网API获取K线数据
        :param secid: 东方财富网的secid
        :param klt: 时间周期参数
        :param lmt: 数据条数
        :param referer: 请求头中的referer
        :return: 解析后的JSON数据，如果失败返回None
        """
        # 构建API请求URL
        url = f"https://push2his.eastmoney.com/api/qt/stock/kline/get?secid={secid}&fields1=f1,f2,f3,f4,f5,f6&fields2=f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61&klt={klt}&fqt=1&end=20500101&lmt={lmt}"
        
        # 设置请求头
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': '*/*',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Referer': referer,
            'Connection': 'keep-alive'
        }
        
        # 发送API请求
        try:
            response = self.session.get(url, headers=headers, timeout=5)
            response.raise_for_status()  # 抛出HTTP错误
            data_str = response.text
        except Exception as e:
            print(f"API请求失败: {e}")
            import traceback
            traceback.print_exc()
            return None
        
        # 解析JSON响应
        try:
            data = json.loads(data_str)
        except Exception as e:
            print(f"JSON解析失败: {e}")
            return None
        
        # 检查响应状态
        if data.get('rc') != 0:
            print(f"东方财富API返回错误: {data.get('msg', '未知错误')}")
            return None
        
        return data
    
    def parse_kline_data(self, klines, code):
        """
        解析K线数据
        :param klines: 原始K线数据列表
        :param code: 股票代码
        :return: 包含K线数据的DataFrame
        """
        # 解析K线数据
        stock_data = []
        for kline in klines:
            kline_data = kline.split(',')
            if len(kline_data) < 7:
                continue
            
            # 解析日期、开盘价、收盘价、最高价、最低价、成交量、成交额
            stock_data.append({
                'date': kline_data[0],
                'open': float(kline_data[1]) if kline_data[1] != '' else 0,
                'close': float(kline_data[2]) if kline_data[2] != '' else 0,
                'high': float(kline_data[3]) if kline_data[3] != '' else 0,
                'low': float(kline_data[4]) if kline_data[4] != '' else 0,
                'volume': int(float(kline_data[5])) if kline_data[5] != '' else 0,
                'amount': float(kline_data[6]) if kline_data[6] != '' else 0,
                'code': code
            })
        
        # 创建DataFrame
        df = pd.DataFrame(stock_data)
        
        # 设置索引为datetime类型，保留原始时间格式
        df['date'] = pd.to_datetime(df['date'])
        
        # 使用reset_index避免索引重复问题
        df.reset_index(drop=True, inplace=True)
        
        # 设置日期为索引
        df.set_index('date', inplace=True)
        
        return df
    
    def get_stock_data_by_time_range(self, code, time_range):
        """
        获取不同时间范围的股票数据
        """
        try:
            if not code or not time_range:
                return None

            print(f"正在获取{code}的{time_range}数据...")

            # 获取股票配置信息
            config = self.get_stock_config(code, time_range)
            if not config:
                return None
            
            # 从API获取K线数据
            data = self.fetch_kline_data(config['secid'], config['klt'], config['lmt'], config['referer'])
            if not data or 'data' not in data or data['data'] is None:
                print(f"未获取到{code}的{time_range}数据")
                return None
            
            # 提取K线数据
            klines = data['data'].get('klines', [])
            if not klines:
                print(f"K线数据为空")
                return None
            
            print(f"成功获取{len(klines)}条K线数据")
            
            # 解析K线数据
            df = self.parse_kline_data(klines, code)
            
            print(f"成功解析{len(df)}条{time_range}数据")
            return df
        except Exception as e:
            print(f"获取{code}的{time_range}数据失败: {e}")
            import traceback
            traceback.print_exc()
            return None

class StockDatabaseManager:
    """股票数据库管理器类，封装所有数据库操作"""
    
    def __init__(self, db_path):
        """初始化数据库连接"""
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """初始化SQLite数据库"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 创建系统表
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS system_info (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            key TEXT NOT NULL UNIQUE,
            value TEXT NOT NULL
        )
        ''')
        
        # 创建分钟数据表
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS minute_stock_data (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            symbol TEXT NOT NULL,
            date TEXT NOT NULL,
            time TEXT NOT NULL,
            open REAL NOT NULL,
            close REAL NOT NULL,
            high REAL NOT NULL,
            low REAL NOT NULL,
            volume INTEGER NOT NULL,
            timestamp INTEGER NOT NULL
        )
        ''')
        
        # 创建当天数据表
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS today_stock_data (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            symbol TEXT NOT NULL,
            date TEXT NOT NULL,
            open REAL NOT NULL,
            close REAL NOT NULL,
            high REAL NOT NULL,
            low REAL NOT NULL,
            volume INTEGER NOT NULL,
            timestamp INTEGER NOT NULL
        )
        ''')
        
        # 创建历史数据表
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS stock_history_data (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            symbol TEXT NOT NULL,
            date TEXT NOT NULL,
            open REAL NOT NULL,
            close REAL NOT NULL,
            high REAL NOT NULL,
            low REAL NOT NULL,
            volume INTEGER NOT NULL,
            timestamp INTEGER NOT NULL,
            time_range TEXT NOT NULL
        )
        ''')
        
        conn.commit()
        conn.close()
    
    def save_today_data_to_db(self, symbol, data):
        """保存当天股票数据到数据库"""
        if data is None:
            print("没有数据可保存")
            return False
        
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # 清除当天旧数据
            today = datetime.datetime.now().strftime('%Y-%m-%d')
            cursor.execute('DELETE FROM today_stock_data WHERE symbol = ? AND date = ?', (symbol, today))
            
            # 批量插入新数据
            rows = []
            for index, row in data.iterrows():
                rows.append((
                    symbol,
                    index.strftime('%Y-%m-%d'),
                    row['open'],
                    row['close'],
                    row['high'],
                    row['low'],
                    int(row['volume']),
                    int(index.timestamp())
                ))
            
            cursor.executemany('''
            INSERT INTO today_stock_data (symbol, date, open, close, high, low, volume, timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', rows)
            
            conn.commit()
            conn.close()
            print(f"成功保存{len(rows)}条当天数据")
            return True
        except Exception as e:
            print(f"保存当天数据失败: {e}")
            return False
    
    def save_data_to_db(self, symbol, data, time_range='day'):
        """保存股票数据到数据库"""
        if data is None:
            print("没有数据可保存")
            return False
        
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # 批量插入数据
            rows = []
            for index, row in data.iterrows():
                rows.append((
                    symbol,
                    index.strftime('%Y-%m-%d'),
                    row['open'],
                    row['close'],
                    row['high'],
                    row['low'],
                    int(row['volume']),
                    int(index.timestamp()),
                    time_range
                ))
            
            cursor.executemany('''
            INSERT INTO stock_history_data (symbol, date, open, close, high, low, volume, timestamp, time_range)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', rows)
            
            conn.commit()
            conn.close()
            print(f"成功保存{len(rows)}条{time_range}数据")
            return True
        except Exception as e:
            print(f"保存{time_range}数据失败: {e}")
            return False
    
    def get_today_data_from_db(self, symbol):
        """从数据库获取当天股票数据"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            today = datetime.datetime.now().strftime('%Y-%m-%d')
            cursor.execute('''
            SELECT date, open, close, high, low, volume, timestamp
            FROM today_stock_data
            WHERE symbol = ? AND date = ?
            ORDER BY timestamp ASC
            ''', (symbol, today))
            
            data = cursor.fetchall()
            conn.close()
            
            if data:
                df = pd.DataFrame(data, columns=['date', 'open', 'close', 'high', 'low', 'volume', 'timestamp'])
                df['date'] = pd.to_datetime(df['timestamp'], unit='s')
                df = df.set_index('date')
                df = df[['open', 'close', 'high', 'low', 'volume']]
                return df
            else:
                return None
        except Exception as e:
            print(f"获取当天数据失败: {e}")
            return None
    
    def get_data_from_db(self, symbol, time_range='day', start_date=None, end_date=None):
        """从数据库获取指定时间范围的股票数据"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            query = '''
            SELECT date, open, close, high, low, volume, timestamp
            FROM stock_history_data
            WHERE symbol = ? AND time_range = ?
            '''
            params = [symbol, time_range]
            
            if start_date:
                query += ' AND date >= ?'
                params.append(start_date)
            if end_date:
                query += ' AND date <= ?'
                params.append(end_date)
            
            query += ' ORDER BY timestamp ASC'
            
            cursor.execute(query, params)
            data = cursor.fetchall()
            conn.close()
            
            if data:
                df = pd.DataFrame(data, columns=['date', 'open', 'close', 'high', 'low', 'volume', 'timestamp'])
                df['date'] = pd.to_datetime(df['timestamp'], unit='s')
                df = df.set_index('date')
                df = df[['open', 'close', 'high', 'low', 'volume']]
                return df
            else:
                return None
        except Exception as e:
            print(f"获取{time_range}数据失败: {e}")
            return None

class RealTimeStockMonitor:
    def __init__(self, symbol, interval=60, with_gui=True):
        """
        实时股票监控器
        :param symbol: 股票代码
        :param interval: 数据更新间隔（秒）
        :param with_gui: 是否启用图形输出
        """
        self.symbol = symbol
        self.interval = interval
        self.with_gui = with_gui
        self.data = []  # 存储实时数据
        self.today_data = None  # 存储当天的1分钟数据
        self.running = False
        self.db_path = 'stock_data.db'  # SQLite数据库文件路径
        
        # 初始化数据获取器和数据库管理器
        self.data_fetcher = StockDataFetcher()
        self.db_manager = StockDatabaseManager(self.db_path)
        
        # 初始化时获取当天的历史1分钟数据
        self.update_today_data()
    
    def update_today_data(self):
        """
        更新当天的1分钟数据
        """
        self.today_data = self.data_fetcher.get_stock_data_by_time_range(self.symbol, 'day')
        if self.today_data is not None:
            print(f"获取了{len(self.today_data)}条当天1分钟数据")
        else:
            print("未能获取当天数据")
    
    def get_real_time_data(self):
        """
        获取实时股票数据
        :return: 包含实时数据的字典，如果获取失败则返回None
        """
        return self.data_fetcher.get_real_time_data(self.symbol)

    def save_today_data_to_db(self):
        """
        将当天股票数据保存到SQLite数据库
        """
        return self.db_manager.save_today_data_to_db(self.symbol, self.today_data)

    def save_data_to_db(self, data, time_range='day'):
        """
        将指定时间范围的股票数据保存到SQLite数据库
        :param data: DataFrame数据
        :param time_range: 时间范围，可选值：day/week/month
        :return: bool
        """
        return self.db_manager.save_data_to_db(self.symbol, data, time_range)

    def get_today_data_from_db(self):
        """
        从SQLite数据库获取当天股票数据
        :return: DataFrame
        """
        return self.db_manager.get_today_data_from_db(self.symbol)

    def get_data_from_db(self, time_range='day', start_date=None, end_date=None):
        """
        从SQLite数据库获取指定时间范围的股票数据
        - 1分钟数据从按股票代码和月份分表中获取
        - 其他时间范围从按股票代码分表中获取
        :param time_range: 时间范围，可选值：day/week/month/year/1min
        :param start_date: 开始日期，格式为YYYY-MM-DD或YYYY-MM-DD HH:MM:SS
        :param end_date: 结束日期，格式为YYYY-MM-DD或YYYY-MM-DD HH:MM:SS
        :return: DataFrame
        """
        return self.db_manager.get_data_from_db(self.symbol, time_range, start_date, end_date)

    def clear_terminal(self):
        """清除终端屏幕"""
        if os.name == 'nt':  # Windows
            os.system('cls')
        else:  # Linux/macOS
            os.system('clear')
    
    def display_real_time_data(self, data):
        """显示实时数据"""
        self.clear_terminal()
        print(f"{'='*60}")
        print(f"实时股票监控 - {data['name']}({data['symbol']})")
        print(f"{'='*60}")
        
        # 计算涨跌幅和涨跌额，避免除零错误
        change = data['price'] - data['pre_close']
        if data['pre_close'] != 0:
            change_pct = (change / data['pre_close']) * 100
        else:
            change_pct = 0.0
        
        print(f"当前价格: {data['price']:.2f}")
        print(f"涨跌额: {change:.2f}")
        print(f"涨跌幅: {change_pct:.2f}%")
        print(f"开盘价: {data['open']:.2f}")
        print(f"最高价: {data['high']:.2f}")
        print(f"最低价: {data['low']:.2f}")
        print(f"成交量: {data['volume']:,} 股")
        print(f"成交金额: {data['amount']:,} 元")
        print(f"更新时间: {data['time']}")
        
        # 显示当日K线数量
        if self.today_data is not None:
            print(f"今日1分钟K线数: {len(self.today_data)}")
        
        print(f"{'='*60}")
        print("按 Ctrl+C 停止监控...")
    
    def update_display(self):
        """更新终端显示"""
        print("=== update_display开始 ===")
        # 获取实时数据
        real_time = self.get_real_time_data()
        print(f"获取到的实时数据: {real_time}")
        if real_time:
            print("有实时数据，开始更新显示")
            # 更新当天数据
            self.update_today_data()
            
            # 添加到实时数据列表
            self.data.append({
                'time': datetime.datetime.now(),
                'price': real_time['price'],
                'high': real_time['high'],
                'low': real_time['low'],
                'volume': real_time['volume']
            })
            
            # 只保留最近60条数据
            if len(self.data) > 60:
                self.data = self.data[-60:]
            
            # 清除终端并显示实时数据
            self.clear_terminal()
            self.display_real_time_data(real_time)
            
            # 绘制K线图（如果启用了图形输出）
            if self.with_gui:
                print("正在绘制K线图...")
                self.plot_kline_chart(real_time)
        else:
            print("没有获取到实时数据")
        print("=== update_display结束 ===")
    
    def main_loop(self):
        """
        主循环，持续更新数据和显示
        """
        print(f"main_loop开始，初始running状态: {self.running}")
        iteration = 0
        try:
            # 设置running为True，开始循环
            self.running = True
            while self.running:
                iteration += 1
                print(f"\n=== 主循环迭代 {iteration} 开始 ===")
                print(f"当前时间: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
                print(f"running状态: {self.running}")
                
                # 更新显示
                self.update_display()
                
                # 等待指定间隔
                print(f"等待 {self.interval} 秒...")
                time.sleep(self.interval)
                
        except KeyboardInterrupt:
            print("\n收到中断信号，即将退出主循环")
        except Exception as e:
            print(f"主循环出错: {e}")
            import traceback
            traceback.print_exc()
        finally:
            print(f"主循环结束，iteration: {iteration}")
    
    def start(self):
        """启动实时监控"""
        print("=== 启动监控 ===")
        print(f"股票代码: {self.symbol}")
        print(f"更新间隔: {self.interval} 秒")
        print("按 Ctrl+C 停止监控")
        
        # 直接调用主循环
        self.main_loop()
        
        # 主循环结束后停止监控
        self.stop()
    
    def plot_kline_chart(self, real_time_data=None):
        """
        绘制当天的K线图，包括成交量
        :param real_time_data: 实时数据
        """
        # 检查是否启用图形输出
        if not self.with_gui:
            print("图形输出已禁用，跳过绘制K线图")
            return
            
        if self.today_data is None:
            print("没有当天数据，无法绘制K线图")
            return
        
        print("正在绘制K线图...")
        
        # 检查是否已经创建了图形窗口
        if not hasattr(self, 'fig') or not hasattr(self, 'ax1') or not hasattr(self, 'ax2'):
            # 创建图形和坐标轴（只创建一次）
            self.fig, (self.ax1, self.ax2) = plt.subplots(2, 1, figsize=(15, 12), gridspec_kw={'height_ratios': [3, 1]})
            plt.ion()  # 启用交互式模式
        else:
            # 清除之前的绘图内容
            self.ax1.clear()
            self.ax2.clear()
        
        self.fig.suptitle(f'{real_time_data["name"]}({real_time_data["symbol"]}) 当天K线图', fontsize=16)
        
        # 绘制K线图
        for i, date in enumerate(self.today_data.index):
            open_p = self.today_data['open'].iloc[i]
            close_p = self.today_data['close'].iloc[i]
            high_p = self.today_data['high'].iloc[i]
            low_p = self.today_data['low'].iloc[i]
            volume = self.today_data['volume'].iloc[i]
            
            # 阳线（红）和阴线（绿）
            if close_p >= open_p:
                color = 'red'
                bottom = open_p
                height = close_p - open_p
            else:
                color = 'green'
                bottom = close_p
                height = open_p - close_p
            
            # 绘制实体
            rect = Rectangle((i, bottom), 0.3, height, facecolor=color, edgecolor='black')
            self.ax1.add_patch(rect)
            
            # 绘制上下影线
            self.ax1.plot([i, i], [low_p, high_p], color='black', linewidth=0.5)
            
            # 绘制成交量柱状图
            if close_p >= open_p:
                color = 'red'
            else:
                color = 'green'
            self.ax2.bar(i, volume, color=color, width=0.3)
        
        # 设置坐标轴
        self.ax1.set_xticks(range(len(self.today_data)))
        self.ax1.set_xticklabels([date.strftime('%H:%M') for date in self.today_data.index], rotation=45)
        self.ax1.set_ylabel('价格 (元)')
        self.ax1.grid(True, linestyle='--', alpha=0.7)
        
        self.ax2.set_xticks(range(len(self.today_data)))
        self.ax2.set_xticklabels([date.strftime('%H:%M') for date in self.today_data.index], rotation=45)
        self.ax2.set_ylabel('成交量')
        self.ax2.grid(True, linestyle='--', alpha=0.7)
        
        # 添加实时数据信息
        if hasattr(self, 'info_text'):
            self.info_text.remove()  # 移除之前的文本
        if real_time_data:
            self.info_text = self.fig.text(0.1, 0.02, f'实时价格: {real_time_data["price"]:.2f}元 | 涨跌幅: {(real_time_data["price"]/real_time_data["pre_close"]-1)*100:.2f}% | 成交量: {real_time_data["volume"]:,}股', fontsize=12, bbox=dict(facecolor='yellow', alpha=0.5))
        
        # 保存图片
        plt.tight_layout()
        plt.savefig(f'{self.symbol}_kline.png', dpi=300, bbox_inches='tight')
        print(f"K线图已保存为 {self.symbol}_kline.png")
        
        # 更新显示
        plt.pause(0.1)
        
    def stop(self):
        """停止监控"""
        if self.running:
            self.running = False
            # 关闭交互式模式
            plt.ioff()
            plt.close()
            print("实时股票监控已停止")

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='实时股票监控工具')
    parser.add_argument('--symbol', type=str, default='600000', help='股票代码')
    parser.add_argument('--interval', type=int, default=5, help='数据更新间隔（秒）')
    parser.add_argument('--time-range', type=str, default='day', choices=['day', 'week', 'month', 'year'], help='数据时间范围')
    parser.add_argument('--save-to-db', action='store_true', help='保存数据到数据库')
    parser.add_argument('--load-from-db', action='store_true', help='从数据库加载数据')
    parser.add_argument('--with-gui', action='store_true', help='启用图形输出')
    parser.add_argument('--no-gui', action='store_false', dest='with_gui', help='禁用图形输出')
    parser.set_defaults(with_gui=True)  # 默认启用图形输出
    
    args = parser.parse_args()
    
    symbol = args.symbol
    interval = args.interval
    time_range = args.time_range
    with_gui = args.with_gui
    
    print("实时股票数据监控工具")
    print("========================================")
    print(f"使用股票代码：{symbol}")
    print(f"数据更新间隔：{interval} 秒")
    print(f"时间范围：{time_range}")
    print(f"图形输出：{'启用' if with_gui else '禁用'}")
    
    # 创建监控实例
    monitor = RealTimeStockMonitor(symbol, interval, with_gui)
    
    if args.save_to_db:
        # 获取指定时间范围的股票数据并保存到数据库
        print(f"正在获取{time_range}的股票数据...")
        data = monitor.data_fetcher.get_stock_data_by_time_range(symbol, time_range)
        if data is not None:
            print(f"成功获取{len(data)}条{time_range}数据")
            monitor.save_data_to_db(data, time_range)
        else:
            print(f"获取{time_range}数据失败")
    elif args.load_from_db:
        # 从数据库加载指定时间范围的数据并绘制K线图
        print(f"正在从数据库加载{time_range}的股票数据...")
        data = monitor.get_data_from_db(time_range)
        if data is not None:
            print(f"成功从数据库加载{len(data)}条{time_range}数据")
            # 创建一个简单的实时数据结构用于绘制图表
            real_time = {
                'symbol': symbol,
                'name': symbol,  # 从数据库加载时没有股票名称信息
                'price': data['close'].iloc[-1],  # 使用最后一条数据的收盘价
                'pre_close': data['open'].iloc[0],  # 使用第一条数据的开盘价作为昨收
                'high': data['high'].max(),
                'low': data['low'].min(),
                'volume': int(data['volume'].sum()),
                'time': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
            # 设置today_data用于绘图
            monitor.today_data = data
            if with_gui:
                monitor.plot_kline_chart(real_time)
        else:
            print(f"从数据库加载{time_range}数据失败")
    else:
        # 启动实时监控
        monitor.start()

    print("\n程序已停止")

if __name__ == '__main__':
    main()