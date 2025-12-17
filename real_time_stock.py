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

class RealTimeStockMonitor:
    def __init__(self, symbol, interval=60):
        """
        实时股票监控器
        :param symbol: 股票代码
        :param interval: 数据更新间隔（秒）
        """
        self.symbol = symbol
        self.interval = interval
        self.data = []  # 存储实时数据
        self.today_data = None  # 存储当天的1分钟数据
        self.running = False
        self.db_path = 'stock_data.db'  # SQLite数据库文件路径
        
        # 初始化数据获取器和数据库管理器
        self.data_fetcher = StockDataFetcher()
        self.db_manager = StockDatabaseManager(self.db_path)
        
        # 初始化时获取当天的历史1分钟数据
        self.update_today_data()
    
    def init_database(self):
        """
        初始化SQLite数据库
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 创建当天股票数据表
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
        
        # 创建历史股票数据表（支持不同时间范围）
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
            time_range TEXT NOT NULL  -- 标识数据时间范围: day/week/month
        )
        ''')
        
        conn.commit()
        conn.close()
    
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
        """在终端显示实时数据"""
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
        # 获取实时数据
        real_time = self.get_real_time_data()
        if real_time:
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
            
            # 绘制K线图和成交量
            self.plot_kline_chart(real_time)
    
    def main_loop(self):
        """主循环"""
        print("=== 主循环开始 ===")
        import sys
        print(f"Python版本: {sys.version}")
        print(f"初始running状态: {self.running}")
        
        loop_count = 0
        while True:
            try:
                print(f"\n循环迭代 {loop_count} 开始")
                print(f"循环中running状态: {self.running}")
                
                # 更新数据显示
                self.update_display()
                
                print(f"等待 {self.interval} 秒")
                time.sleep(self.interval)
                print(f"等待结束，继续执行")
                
                loop_count += 1
                print(f"循环迭代 {loop_count-1} 结束")
                
            except KeyboardInterrupt:
                print("\n接收到键盘中断")
                break
            except Exception as e:
                print(f"主循环错误: {e}")
                import traceback
                traceback.print_exc()
                # 继续执行，而不是退出
                print("错误处理完成，继续下一次循环")
                time.sleep(5)
        
        print("=== 主循环结束 ===")
    
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
    
    def stop(self):
        """停止监控"""
        if self.running:
            self.running = False
            print("实时股票监控已停止")
    
    def plot_kline_chart(self, real_time_data=None):
        """
        绘制当天的K线图，包括成交量
        :param real_time_data: 实时数据
        """
        if self.today_data is None:
            print("没有当天数据，无法绘制K线图")
            return
        
        print("正在绘制K线图...")
        
        # 创建图形和坐标轴
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(15, 12), gridspec_kw={'height_ratios': [3, 1]})
        fig.suptitle(f'{real_time_data["name"]}({real_time_data["symbol"]}) 当天K线图', fontsize=16)
        
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
            ax1.add_patch(rect)
            
            # 绘制上下影线
            ax1.plot([i, i], [low_p, high_p], color='black', linewidth=0.5)
            
            # 绘制成交量柱状图
            if close_p >= open_p:
                ax2.bar(i, volume, color='red', alpha=0.7, width=0.3)
            else:
                ax2.bar(i, volume, color='green', alpha=0.7, width=0.3)
        
        # 设置时间轴
        num_ticks = 10
        tick_indices = [int(i * (len(self.today_data) - 1) / (num_ticks - 1)) for i in range(num_ticks)]
        ax1.set_xticks(tick_indices)
        ax1.set_xticklabels([self.today_data.index[i].strftime('%H:%M') for i in tick_indices], rotation=45)
        ax2.set_xticks(tick_indices)
        ax2.set_xticklabels([self.today_data.index[i].strftime('%H:%M') for i in tick_indices], rotation=45)
        
        # 设置坐标轴标签
        ax1.set_ylabel('价格', fontsize=12)
        ax2.set_ylabel('成交量', fontsize=12)
        ax2.set_xlabel('时间', fontsize=12)
        
        # 添加网格
        ax1.grid(True, linestyle='--', alpha=0.7)
        ax2.grid(True, linestyle='--', alpha=0.7)
        
        # 添加实时数据信息
        if real_time_data:
            info_text = f"当前价格: {real_time_data['price']:.2f} | 涨跌幅: {((real_time_data['price'] - real_time_data['pre_close']) / real_time_data['pre_close'] * 100):.2f}%\n"
            info_text += f"最高价: {real_time_data['high']:.2f} | 最低价: {real_time_data['low']:.2f}\n"
            info_text += f"成交量: {real_time_data['volume']:,} 股 | 更新时间: {real_time_data['time']}"
            
            ax1.text(0.02, 0.98, info_text, transform=ax1.transAxes, 
                    fontsize=11, verticalalignment='top', 
                    bbox=dict(boxstyle='round', facecolor='lightyellow', alpha=0.8))
        
        # 调整布局
        plt.tight_layout()
        plt.subplots_adjust(top=0.95)
        
        # 保存图像
        today_str = datetime.datetime.now().strftime('%Y%m%d')
        filename = f'{real_time_data["symbol"]}_{today_str}_kline.png'
        plt.savefig(filename, dpi=300)
        print(f"K线图已保存为 {filename}")
        
        # 显示图像
        plt.show()

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
        if code.startswith('00') or code.startswith('30'):
            return 'sz'
        elif code.startswith('60'):
            return 'sh'
        elif code.startswith('8') or code.startswith('4'):
            return 'bj'
        else:
            return 'hk'
    
    def get_real_time_data(self, code):
        """获取港股或A股实时数据"""
        try:
            if not code:
                return None

            market_code = self.get_market_code(code)
            if market_code == 'hk':
                # 获取港股实时数据
                url = f"https://hq.sinajs.cn/list=r_hk{code}"
                response = self.session.get(url)
                response.encoding = 'gbk'
                data_str = response.text

                if '=' in data_str:
                    data_str = data_str.split('=')[1].strip('"\n')
                    data_list = data_str.split(',')

                    if len(data_list) >= 32:
                        # 港股数据
                        name = data_list[1]
                        current_price = float(data_list[6]) if data_list[6] != '' else 0
                        open_price = float(data_list[2]) if data_list[2] != '' else 0
                        yesterday_close = float(data_list[3]) if data_list[3] != '' else 0
                        high_price = float(data_list[4]) if data_list[4] != '' else 0
                        low_price = float(data_list[5]) if data_list[5] != '' else 0
                        volume = int(float(data_list[17])) if data_list[17] != '' else 0
                        amount = float(data_list[18]) if data_list[18] != '' else 0
                        
                        change = current_price - yesterday_close
                        change_percent = (change / yesterday_close) * 100 if yesterday_close != 0 else 0

                        return {
                            'code': code,
                            'name': name,
                            'current_price': current_price,
                            'open_price': open_price,
                            'yesterday_close': yesterday_close,
                            'high_price': high_price,
                            'low_price': low_price,
                            'volume': volume,
                            'amount': amount,
                            'change': change,
                            'change_percent': change_percent,
                            'update_time': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                        }
            else:
                # 获取A股实时数据
                url = f"https://hq.sinajs.cn/list={market_code}{code}"
                response = self.session.get(url)
                response.encoding = 'gbk'
                data_str = response.text

                if '=' in data_str:
                    data_str = data_str.split('=')[1].strip('"\n')
                    data_list = data_str.split(',')

                    if len(data_list) >= 32:
                        # A股数据
                        name = data_list[0]
                        current_price = float(data_list[3]) if data_list[3] != '' else 0
                        yesterday_close = float(data_list[2]) if data_list[2] != '' else 0
                        open_price = float(data_list[1]) if data_list[1] != '' else 0
                        high_price = float(data_list[4]) if data_list[4] != '' else 0
                        low_price = float(data_list[5]) if data_list[5] != '' else 0
                        volume = int(float(data_list[8])) if data_list[8] != '' else 0
                        amount = float(data_list[9]) if data_list[9] != '' else 0

                        change = current_price - yesterday_close
                        change_percent = (change / yesterday_close) * 100 if yesterday_close != 0 else 0

                        return {
                            'code': code,
                            'name': name,
                            'current_price': current_price,
                            'open_price': open_price,
                            'yesterday_close': yesterday_close,
                            'high_price': high_price,
                            'low_price': low_price,
                            'volume': volume,
                            'amount': amount,
                            'change': change,
                            'change_percent': change_percent,
                            'update_time': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                        }
            return None
        except Exception as e:
            print(f"获取实时数据失败: {e}")
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
            # 对于day参数，使用新浪财经API获取当日实时数据
            # 这里可能需要单独处理，因为东方财富网的API可能不支持day参数的日线数据
            return None
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


    def update_today_data(self):
        """更新当天数据"""
        try:
            # 调用日数据获取方法
            today_df = self.get_stock_data_by_time_range(self.stock_code, 'day')
            if today_df is not None and not today_df.empty:
                # 更新today_data属性
                self.today_data = today_df
                return True
            return False
        except Exception as e:
            print(f"更新当日数据失败: {e}")
            return False

    def clear_terminal(self):
        """清除终端屏幕"""
        if os.name == 'nt':  # Windows
            os.system('cls')
        else:  # Linux/macOS
            os.system('clear')
    
    def display_real_time_data(self, data):
        """在终端显示实时数据"""
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
        # 获取实时数据
        real_time = self.get_real_time_data()
        if real_time:
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
            
            # 绘制K线图和成交量
            self.plot_kline_chart(real_time)
    
    def main_loop(self):
        """主循环"""
        print("=== 主循环开始 ===")
        import sys
        print(f"Python版本: {sys.version}")
        print(f"初始running状态: {self.running}")
        
        loop_count = 0
        while True:
            try:
                print(f"\n循环迭代 {loop_count} 开始")
                print(f"循环中running状态: {self.running}")
                
                # 更新数据显示
                self.update_display()
                
                print(f"等待 {self.interval} 秒")
                time.sleep(self.interval)
                print(f"等待结束，继续执行")
                
                loop_count += 1
                print(f"循环迭代 {loop_count-1} 结束")
                
            except KeyboardInterrupt:
                print("\n接收到键盘中断")
                break
            except Exception as e:
                print(f"主循环错误: {e}")
                import traceback
                traceback.print_exc()
                # 继续执行，而不是退出
                print("错误处理完成，继续下一次循环")
                time.sleep(5)
        
        print("=== 主循环结束 ===")
    
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
    
    def stop(self):
        """停止监控"""
        if self.running:
            self.running = False
            print("实时股票监控已停止")
    
    def plot_kline_chart(self, real_time_data=None):
        """
        绘制当天的K线图，包括成交量
        :param real_time_data: 实时数据
        """
        if self.today_data is None:
            print("没有当天数据，无法绘制K线图")
            return
        
        print("正在绘制K线图...")
        
        # 创建图形和坐标轴
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(15, 12), gridspec_kw={'height_ratios': [3, 1]})
        fig.suptitle(f'{real_time_data["name"]}({real_time_data["symbol"]}) 当天K线图', fontsize=16)
        
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
            ax1.add_patch(rect)
            
            # 绘制上下影线
            ax1.plot([i, i], [low_p, high_p], color='black', linewidth=0.5)
            
            # 绘制成交量柱状图
            if close_p >= open_p:
                ax2.bar(i, volume, color='red', alpha=0.7, width=0.3)
            else:
                ax2.bar(i, volume, color='green', alpha=0.7, width=0.3)
        
        # 设置时间轴
        num_ticks = 10
        tick_indices = [int(i * (len(self.today_data) - 1) / (num_ticks - 1)) for i in range(num_ticks)]
        ax1.set_xticks(tick_indices)
        ax1.set_xticklabels([self.today_data.index[i].strftime('%H:%M') for i in tick_indices], rotation=45)
        ax2.set_xticks(tick_indices)
        ax2.set_xticklabels([self.today_data.index[i].strftime('%H:%M') for i in tick_indices], rotation=45)
        
        # 设置坐标轴标签
        ax1.set_ylabel('价格', fontsize=12)
        ax2.set_ylabel('成交量', fontsize=12)
        ax2.set_xlabel('时间', fontsize=12)
        
        # 添加网格
        ax1.grid(True, linestyle='--', alpha=0.7)
        ax2.grid(True, linestyle='--', alpha=0.7)
        
        # 添加实时数据信息
        if real_time_data:
            info_text = f"当前价格: {real_time_data['price']:.2f} | 涨跌幅: {((real_time_data['price'] - real_time_data['pre_close']) / real_time_data['pre_close'] * 100):.2f}%\n"
            info_text += f"最高价: {real_time_data['high']:.2f} | 最低价: {real_time_data['low']:.2f}\n"
            info_text += f"成交量: {real_time_data['volume']:,} 股 | 更新时间: {real_time_data['time']}"
            
            ax1.text(0.02, 0.98, info_text, transform=ax1.transAxes, 
                    fontsize=11, verticalalignment='top', 
                    bbox=dict(boxstyle='round', facecolor='lightyellow', alpha=0.8))
        
        # 调整布局
        plt.tight_layout()
        plt.subplots_adjust(top=0.95)
        
        # 保存图像
        today_str = datetime.datetime.now().strftime('%Y%m%d')
        filename = f'{real_time_data["symbol"]}_{today_str}_kline.png'
        plt.savefig(filename, dpi=300)
        print(f"K线图已保存为 {filename}")
        
        # 显示图像
        plt.show()

class StockDatabaseManager:
    """股票数据库管理类"""
    
    def __init__(self, db_path='stock_data.db'):
        """
        初始化数据库管理器
        :param db_path: 数据库文件路径
        """
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """
        初始化SQLite数据库，不再创建固定表，改为动态创建
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # 不再创建固定表，改为在保存数据时动态创建
            # 这里可以创建系统表来记录已创建的股票表
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS system_tables (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                table_type TEXT NOT NULL,  -- today_history_stock_600000
                symbol TEXT NOT NULL,
                table_name TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(table_type, symbol)
            )
            ''')
            
            conn.commit()
            conn.close()
            print(f"数据库初始化成功: {self.db_path}")
        except Exception as e:
            print(f"数据库初始化失败: {e}")
    
    def _get_today_table_name(self, symbol):
        """
        获取当天数据表的表名
        :param symbol: 股票代码
        :return: 表名
        """
        return f"today_stock_{symbol}"
    
    def _get_history_table_name(self, symbol):
        """
        获取历史数据表的表名
        :param symbol: 股票代码
        :return: 表名
        """
        return f"history_stock_{symbol}"
    
    def _get_minute_table_name(self, symbol, year_month):
        """
        获取1分钟数据的表名（按股票代码和月份分表）
        :param symbol: 股票代码
        :param year_month: 年月，格式为YYYYMM
        :return: 表名
        """
        return f"minute_stock_{symbol}_{year_month}"
    
    def _create_minute_table_if_not_exists(self, cursor, symbol, year_month):
        """
        如果不存在，创建1分钟数据表（按股票代码和月份分表）
        :param cursor: 数据库游标
        :param symbol: 股票代码
        :param year_month: 年月，格式为YYYYMM
        """
        table_name = self._get_minute_table_name(symbol, year_month)
        cursor.execute(f'''
        CREATE TABLE IF NOT EXISTS {table_name} (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            symbol TEXT NOT NULL,
            date TEXT NOT NULL,
            open REAL NOT NULL,
            close REAL NOT NULL,
            high REAL NOT NULL,
            low REAL NOT NULL,
            volume INTEGER NOT NULL,
            timestamp INTEGER NOT NULL,
            UNIQUE(timestamp)
        )
        ''')
        
        # 记录到系统表
        cursor.execute('''
        INSERT OR IGNORE INTO system_tables (table_type, symbol, table_name)
        VALUES (?, ?, ?)
        ''', ('minute', f"{symbol}_{year_month}", table_name))
    
    def _create_today_table_if_not_exists(self, cursor, symbol):
        """
        如果不存在，创建当天数据表
        :param cursor: 数据库游标
        :param symbol: 股票代码
        """
        table_name = self._get_today_table_name(symbol)
        cursor.execute(f'''
        CREATE TABLE IF NOT EXISTS {table_name} (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            symbol TEXT NOT NULL,
            date TEXT NOT NULL,
            open REAL NOT NULL,
            close REAL NOT NULL,
            high REAL NOT NULL,
            low REAL NOT NULL,
            volume INTEGER NOT NULL,
            timestamp INTEGER NOT NULL,
            UNIQUE(timestamp)
        )
        ''')
        
        # 记录到系统表
        cursor.execute('''
        INSERT OR IGNORE INTO system_tables (table_type, symbol, table_name)
        VALUES (?, ?, ?)
        ''', ('today', symbol, table_name))
    
    def _create_history_table_if_not_exists(self, cursor, symbol):
        """
        如果不存在，创建历史数据表
        :param cursor: 数据库游标
        :param symbol: 股票代码
        """
        table_name = self._get_history_table_name(symbol)
        cursor.execute(f'''
        CREATE TABLE IF NOT EXISTS {table_name} (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            symbol TEXT NOT NULL,
            date TEXT NOT NULL,
            open REAL NOT NULL,
            close REAL NOT NULL,
            high REAL NOT NULL,
            low REAL NOT NULL,
            volume INTEGER NOT NULL,
            timestamp INTEGER NOT NULL,
            time_range TEXT NOT NULL,  -- 标识数据时间范围: day/week/month
            UNIQUE(timestamp, time_range)
        )
        ''')
        
        # 记录到系统表
        cursor.execute('''
        INSERT OR IGNORE INTO system_tables (table_type, symbol, table_name)
        VALUES (?, ?, ?)
        ''', ('history', symbol, table_name))
    
    def save_today_data_to_db(self, symbol, df):
        """
        保存当天股票数据到SQLite数据库（按股票代码分表）
        :param symbol: 股票代码
        :param df: 包含当天数据的DataFrame
        :return: 保存成功返回True，失败返回False
        """
        conn = None
        try:
            if df is None or df.empty:
                print("没有数据需要保存到数据库")
                return False
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # 创建该股票的当天数据表（如果不存在）
            self._create_today_table_if_not_exists(cursor, symbol)
            
            # 获取表名
            table_name = self._get_today_table_name(symbol)
            
            # 清空当天该股票的数据
            cursor.execute(f"DELETE FROM {table_name}")
            
            # 准备要插入的数据
            rows = []
            for index, row in df.iterrows():
                timestamp = int(index.timestamp())
                date_str = index.strftime('%Y-%m-%d %H:%M:%S')
                rows.append((
                    symbol,
                    date_str,
                    row['open'],
                    row['close'],
                    row['high'],
                    row['low'],
                    int(row['volume']),
                    timestamp
                ))
            
            # 批量插入数据
            cursor.executemany(f'''
            INSERT INTO {table_name} (symbol, date, open, close, high, low, volume, timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', rows)
            
            conn.commit()
            print(f"成功将股票 {symbol} 的当天数据保存到数据库表 {table_name}")
            return True
        except Exception as e:
            print(f"保存当天数据到数据库失败: {e}")
            return False
        finally:
            if conn:
                conn.close()

    def save_data_to_db(self, symbol, df, time_range='day'):
        """
        将指定时间范围的股票数据保存到SQLite数据库
        - 1分钟数据按股票代码和月份分表存储
        - 其他时间范围按股票代码分表存储
        :param symbol: 股票代码
        :param df: 包含数据的DataFrame
        :param time_range: 时间范围 (day/week/month/year/1min)
        :return: 保存成功返回True，失败返回False
        """
        conn = None
        try:
            if df is None or df.empty:
                print("没有数据需要保存到数据库")
                return False
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # 处理1分钟数据（按股票代码和月份分表）
            if time_range == '1min':
                # 确保索引是DateTimeIndex类型
                if not isinstance(df.index, pd.DatetimeIndex):
                    df.index = pd.to_datetime(df.index)
                
                # 按月份分组数据
                df['year_month'] = df.index.strftime('%Y%m')
                for year_month, group_df in df.groupby('year_month'):
                    # 创建该股票该月份的1分钟数据表（如果不存在）
                    self._create_minute_table_if_not_exists(cursor, symbol, year_month)
                    
                    # 获取表名
                    table_name = self._get_minute_table_name(symbol, year_month)
                    
                    # 准备要插入的数据
                    rows = []
                    for index, row in group_df.iterrows():
                        timestamp = int(index.timestamp())
                        date_str = index.strftime('%Y-%m-%d %H:%M:%S')
                        rows.append((
                            symbol,
                            date_str,
                            row['open'],
                            row['close'],
                            row['high'],
                            row['low'],
                            int(row['volume']),
                            timestamp
                        ))
                    
                    # 批量插入数据到数据库
                    if rows:
                        cursor.executemany(f'''
                            INSERT OR REPLACE INTO {table_name} 
                            (symbol, date, open, close, high, low, volume, timestamp)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                        ''', rows)
                        print(f"成功保存{len(rows)}条1分钟数据到数据库表 {table_name}")
                    else:
                        print(f"表 {table_name} 没有有效数据需要保存")
                        return False
            # 处理其他时间范围数据（按股票代码分表）
            else:
                # 创建该股票的历史数据表（如果不存在）
                self._create_history_table_if_not_exists(cursor, symbol)
                
                # 获取表名
                table_name = self._get_history_table_name(symbol)
                
                # 准备要插入的数据
                rows = []
                for index, row in df.iterrows():
                    # 使用pandas的to_datetime函数简化日期解析
                    try:
                        date_obj = pd.to_datetime(index)
                        timestamp = int(date_obj.timestamp())
                        date_str = date_obj.strftime('%Y-%m-%d')
                    except Exception as e:
                        print(f"解析日期失败: {e}")
                        # 如果解析失败，使用当前时间戳
                        timestamp = int(pd.Timestamp.now().timestamp())
                        date_str = pd.Timestamp.now().strftime('%Y-%m-%d')
                    
                    rows.append((
                        symbol,
                        date_str,
                        row['open'],
                        row['close'],
                        row['high'],
                        row['low'],
                        int(row['volume']),
                        timestamp,
                        time_range
                    ))
                    
                # 批量插入数据到数据库
                if rows:
                    cursor.executemany(f'''
                        INSERT OR REPLACE INTO {table_name} 
                        (symbol, date, open, close, high, low, volume, timestamp, time_range)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', rows)
                    print(f"成功保存{len(rows)}条{time_range}数据到数据库表 {table_name}")
                else:
                    print("没有有效数据需要保存到数据库")
                    return False
            
            conn.commit()
            return True
        except Exception as e:
            print(f"保存{time_range}数据到数据库失败: {e}")
            import traceback
            traceback.print_exc()
            return False
        finally:
            if conn:
                conn.close()

    def get_today_data_from_db(self, symbol):
        """
        从SQLite数据库获取当天股票数据（按股票代码分表）
        :param symbol: 股票代码
        :return: 包含当天数据的DataFrame，如果没有数据返回None
        """
        conn = None
        try:
            conn = sqlite3.connect(self.db_path)
            
            # 获取表名
            table_name = self._get_today_table_name(symbol)
            
            # 检查表是否存在
            cursor = conn.cursor()
            cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table_name}'")
            if not cursor.fetchone():
                print(f"数据库中没有股票 {symbol} 的当天数据表")
                return None
            
            query = f"SELECT * FROM {table_name} ORDER BY timestamp"
            df = pd.read_sql_query(query, conn, parse_dates=['date'])
            
            if df.empty:
                print(f"数据库表 {table_name} 中没有数据")
                return None
            
            # 设置日期为索引
            df.set_index('date', inplace=True)
            
            # 转换数据类型
            df['open'] = df['open'].astype(float)
            df['close'] = df['close'].astype(float)
            df['high'] = df['high'].astype(float)
            df['low'] = df['low'].astype(float)
            df['volume'] = df['volume'].astype(int)
            
            print(f"成功从数据库表 {table_name} 加载股票 {symbol} 的当天数据")
            return df
        except Exception as e:
            print(f"从数据库加载当天数据失败: {e}")
            return None
        finally:
            if conn:
                conn.close()
    
    def get_data_from_db(self, symbol, time_range=None, start_date=None, end_date=None):
        """
        从SQLite数据库获取历史股票数据
        - 1分钟数据从按股票代码和月份分表中获取
        - 其他时间范围从按股票代码分表中获取
        :param symbol: 股票代码
        :param time_range: 时间范围，None表示获取所有时间范围
        :param start_date: 开始日期，格式为YYYY-MM-DD或YYYY-MM-DD HH:MM:SS
        :param end_date: 结束日期，格式为YYYY-MM-DD或YYYY-MM-DD HH:MM:SS
        :return: 包含历史数据的DataFrame，如果没有数据返回None
        """
        conn = None
        try:
            conn = sqlite3.connect(self.db_path)
            
            # 处理1分钟数据（从多个月份表中获取）
            if time_range == '1min':
                cursor = conn.cursor()
                
                # 获取该股票所有1分钟数据表名
                cursor.execute('''
                SELECT table_name FROM system_tables 
                WHERE table_type = 'minute' AND symbol LIKE ?
                ''', (f"{symbol}_%",))
                table_names = [row[0] for row in cursor.fetchall()]
                
                if not table_names:
                    print(f"数据库中没有股票 {symbol} 的1分钟数据表")
                    return None
                
                # 构建联合查询
                query_parts = []
                for table_name in table_names:
                    query_parts.append(f"SELECT * FROM {table_name}")
                
                base_query = " UNION ALL ".join(query_parts)
                
                # 添加日期过滤条件
                if start_date and end_date:
                    query = f"{base_query} WHERE date BETWEEN ? AND ? ORDER BY timestamp"
                    params = (start_date, end_date)
                else:
                    query = f"{base_query} ORDER BY timestamp"
                    params = ()
                
                df = pd.read_sql_query(query, conn, params=params, parse_dates=['date'])
            
            # 处理其他时间范围数据（从单一股票表中获取）
            else:
                # 获取表名
                table_name = self._get_history_table_name(symbol)
                
                # 检查表是否存在
                cursor = conn.cursor()
                cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table_name}'")
                if not cursor.fetchone():
                    print(f"数据库中没有股票 {symbol} 的历史数据表")
                    return None
                
                # 构建查询
                if time_range:
                    if start_date and end_date:
                        query = f"SELECT * FROM {table_name} WHERE time_range = ? AND date BETWEEN ? AND ? ORDER BY timestamp"
                        params = (time_range, start_date, end_date)
                    else:
                        query = f"SELECT * FROM {table_name} WHERE time_range = ? ORDER BY timestamp"
                        params = (time_range,)
                else:
                    if start_date and end_date:
                        query = f"SELECT * FROM {table_name} WHERE date BETWEEN ? AND ? ORDER BY timestamp"
                        params = (start_date, end_date)
                    else:
                        query = f"SELECT * FROM {table_name} ORDER BY timestamp"
                        params = ()
                
                df = pd.read_sql_query(query, conn, params=params, parse_dates=['date'])
            
            if df.empty:
                print(f"数据库中没有找到符合条件的股票 {symbol} 的{time_range}数据")
                return None
            
            # 设置日期为索引
            df.set_index('date', inplace=True)
            
            # 转换数据类型
            df['open'] = df['open'].astype(float)
            df['close'] = df['close'].astype(float)
            df['high'] = df['high'].astype(float)
            df['low'] = df['low'].astype(float)
            df['volume'] = df['volume'].astype(int)
            
            print(f"成功从数据库加载股票 {symbol} 的{time_range}数据")
            return df
        except Exception as e:
            print(f"从数据库加载{time_range}数据失败: {e}")
            import traceback
            traceback.print_exc()
            return None
        finally:
            if conn:
                conn.close()


# 以下是RealTimeStockMonitor类的实现（已存在）

# 删除错误的main函数定义

# 直接使用if __name__ == "__main__":块
if __name__ == "__main__":
    print("实时股票数据监控工具")
    print("=" * 40)
    
    # 创建命令行参数解析器
    parser = argparse.ArgumentParser(description='实时股票数据监控工具')
    parser.add_argument('-s', '--symbol', type=str, default='600000', help='股票代码')
    parser.add_argument('-i', '--interval', type=int, default=5, help='数据刷新间隔（秒）')
    parser.add_argument('--save-to-db', action='store_true', help='将股票数据保存到数据库')
    parser.add_argument('--load-from-db', action='store_true', help='从数据库加载股票数据')
    parser.add_argument('--time-range', type=str, default='day', 
                        choices=['day', 'week', 'month', 'year', '1min'], 
                        help='时间范围（默认为day）')
    
    # 解析命令行参数
    args = parser.parse_args()
    symbol = args.symbol
    interval = args.interval
    time_range = args.time_range
    
    print(f"使用股票代码：{symbol}")
    print(f"数据更新间隔：{interval} 秒")
    print(f"时间范围：{time_range}")
    
    # 创建监控器实例
    monitor = RealTimeStockMonitor(symbol, interval)
    
    if args.save_to_db:
        # 获取指定时间范围的股票数据并保存到数据库
        print(f"正在获取{time_range}的股票数据...")
        data = monitor.data_fetcher.get_stock_data_by_time_range(symbol, time_range)
        if data is not None:
            print(f"成功获取{len(data)}条{time_range}数据")
            monitor.save_data_to_db(data, time_range)  # 移除多余的symbol参数
        else:
            print(f"获取{time_range}数据失败")
    elif args.load_from_db:
        # 从数据库加载指定时间范围的数据并绘制K线图
        print(f"正在从数据库加载{time_range}的股票数据...")
        data = monitor.get_data_from_db(time_range)  # 移除多余的symbol参数
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
            monitor.plot_kline_chart(real_time)
        else:
            print(f"从数据库加载{time_range}数据失败")
    else:
        try:
            # 开始监控
            monitor.start()
        except KeyboardInterrupt:
            # 停止监控
            monitor.stop()

    print("\n程序已停止")