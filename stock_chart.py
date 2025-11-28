# -*- coding:utf-8 -*-
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.patches import Rectangle
import datetime
import os
import requests
import json

# 设置中文显示
plt.rcParams['font.sans-serif'] = ['SimHei']
plt.rcParams['axes.unicode_minus'] = False

# 获取1分钟级别股票数据
# 简单的价格缓存，存储股票代码和对应的(价格, 时间戳)对
price_cache = {}
# 缓存有效期，单位：秒
CACHE_EXPIRY = 3600  # 1小时

# 初始化新浪股票API相关配置
# 使用更可靠的新浪财经API格式
SINA_STOCK_API = "https://finance.sina.com.cn/realstock/company/"

def get_minute_data(symbol, days=1):
    """
    获取股票的1分钟级别交易数据
    :param symbol: 股票代码
    :param days: 获取最近几天的数据
    :return: DataFrame格式的分钟数据
    """
    global price_cache
    
    try:
        print(f"正在尝试获取股票 {symbol} 的1分钟数据...")
        
        # 构造东方财富网的股票代码
        # A股：6开头的为沪市(1)，其他为深市(0)
        # 港股：5位数字的为港股(116)
        if symbol.startswith('6'):
            market = '1'  # 沪市A股
        elif len(symbol) == 5:
            market = '116'  # 港股
        else:
            market = '0'  # 深市A股
        
        # 计算时间范围
        end_time = datetime.datetime.now()
        start_time = end_time - datetime.timedelta(days=days)
        
        # 格式化时间参数
        beg_str = start_time.strftime('%Y%m%d%H%M%S')
        end_str = end_time.strftime('%Y%m%d%H%M%S')
        
        # 构造东方财富网的1分钟K线数据接口
        url = f"http://push2his.eastmoney.com/api/qt/stock/kline/get?fields1=f1,f2,f3,f4,f5,f6&fields2=f51,f52,f53,f54,f55,f56,f57&beg={beg_str}&end={end_str}&ut=fa5fd1943c7b386f172d6893dbfba10b&secid={market}.{symbol}&klt=1&fqt=1"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Referer': 'http://quote.eastmoney.com/'
        }
        
        print(f"尝试从东方财富网获取 {symbol} 的1分钟K线数据...")
        print(f"请求URL: {url}")
        
        # 发送请求获取数据
        response = requests.get(url, headers=headers)
        response.encoding = 'utf-8'
        
        print(f"东方财富网API响应状态: {response.status_code}")
        
        if response.status_code == 200:
            data_json = response.json()
            
            if data_json['data'] and 'klines' in data_json['data']:
                kline_data = data_json['data']['klines']
                print(f"成功获取 {symbol} 的1分钟K线数据，共 {len(kline_data)} 条")
                
                # 解析K线数据
                # 东方财富返回的K线数据格式为："时间,开盘价,收盘价,最高价,最低价,成交量,成交额"
                kline_list = []
                for kline in kline_data:
                    parts = kline.split(',')
                    if len(parts) >= 6:
                        kline_list.append({
                            'date': parts[0],
                            'open': float(parts[1]),
                            'close': float(parts[2]),
                            'high': float(parts[3]),
                            'low': float(parts[4]),
                            'volume': float(parts[5])
                        })
                
                # 转换为DataFrame
                df = pd.DataFrame(kline_list)
                df['date'] = pd.to_datetime(df['date'])
                df.set_index('date', inplace=True)
                df = df.rename(columns={'volume': 'volume'})
                
                # 过滤掉休市时间的数据
                # 港股交易时间：9:30-12:00和13:00-16:00
                # A股交易时间：9:30-11:30和13:00-15:00
                if market == '116':
                    # 港股交易时间
                    morning_data = df.between_time('09:30:00', '12:00:00')
                    afternoon_data = df.between_time('13:00:00', '16:00:00')
                else:
                    # A股交易时间
                    morning_data = df.between_time('09:30:00', '11:30:00')
                    afternoon_data = df.between_time('13:00:00', '15:00:00')
                df = pd.concat([morning_data, afternoon_data]).sort_index()
                
                print(f"过滤后数据条数: {len(df)}")
                print(f"数据示例: {df.head()}")
                
                return df
            else:
                print(f"东方财富网返回K线数据为空")
        else:
            print(f"东方财富网API请求失败，状态码: {response.status_code}")
            print(f"响应内容: {response.text}")
    except Exception as e:
        print(f"获取1分钟K线数据时发生异常: {type(e).__name__}: {e}")
    
    # 如果获取真实数据失败，生成模拟数据
    print("无法获取真实1分钟数据，正在生成模拟数据...")
    
    # 构造东方财富网的股票代码，用于后续获取当前价格
    # A股：6开头的为沪市(1)，其他为深市(0)
    # 港股：5位数字的为港股(116)
    if symbol.startswith('6'):
        market = '1'  # 沪市A股
    elif len(symbol) == 5:
        market = '116'  # 港股
    else:
        market = '0'  # 深市A股
    current_price = None
    
    # 检查缓存中是否有有效的价格数据
    current_time = datetime.datetime.now().timestamp()
    if symbol in price_cache:
        cached_price, cached_time = price_cache[symbol]
        if current_time - cached_time < CACHE_EXPIRY:
            current_price = cached_price
            print(f"从缓存中获取 {symbol} 的当前价格: {current_price}")
    
    # 如果缓存中没有有效数据，尝试从东方财富网获取当前价格
    if current_price is None:
        try:
            # 使用东方财富网的实时行情接口获取当前价格
            url = f"http://push2.eastmoney.com/api/qt/stock/get?fields=f43,f46,f44,f45&secid={market}.{symbol}&ut=f057cbcbce2a86e2866ab8877db1d059&fltt=2&invt=2"
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                'Referer': 'http://quote.eastmoney.com/'
            }
            
            print(f"尝试从东方财富网获取 {symbol} 的当前价格...")
            response = requests.get(url, headers=headers)
            response.encoding = 'utf-8'
            
            if response.status_code == 200:
                data_json = response.json()
                if data_json['data']:
                    # f43: 最新价
                    current_price = float(data_json['data']['f43'])
                    print(f"成功获取 {symbol} 的当前价格: {current_price}")
                    # 更新缓存
                    price_cache[symbol] = (current_price, current_time)
        except Exception as e:
            print(f"无法从东方财富网获取 {symbol} 的当前价格: {type(e).__name__}: {e}")
    
    # 生成模拟数据
    df = generate_simulation_data(symbol, days, current_price)
    
    return df

# 生成模拟股票数据
def generate_simulation_data(symbol, days=1, current_price=None):
    """
    生成模拟的股票分钟数据
    :param symbol: 股票代码
    :param days: 生成几天的数据
    :param current_price: 股票当前价格（可选），用于生成更真实的模拟数据
    :return: 模拟的DataFrame数据
    """
    # 计算总分钟数
    total_minutes = days * 24 * 60
    
    # 生成时间序列
    end_time = datetime.datetime.now()
    start_time = end_time - datetime.timedelta(minutes=total_minutes)
    # 生成total_minutes个时间点，而不是total_minutes+1个
    # 生成时间索引，使用'min'代替弃用的'T'
    index = pd.date_range(start=start_time, periods=total_minutes, freq='1min')    
    # 生成随机价格数据
    # 根据股票代码生成动态随机种子，确保不同股票生成不同数据
    seed = hash(symbol) % 1000000  # 使用股票代码的哈希值作为种子
    np.random.seed(seed)  # 设置基于股票代码的随机种子
    
    # 为不同股票设置不同的基准价格
    if current_price is not None:
        # 如果提供了当前价格，则使用它作为基准价格
        base_price = current_price
        print(f"使用基准价格 {current_price} 作为基准生成模拟数据")
    else:
        # 否则根据股票代码哈希值调整
        base_price = 10.0 + (seed % 100) * 0.1  # 基准价格在10-20之间
        print(f"使用随机基准价格 {base_price} 生成模拟数据")
    
    price_changes = np.random.normal(0, 0.01, total_minutes + 1)
    prices = base_price + np.cumsum(price_changes)
    
    # 生成开盘价、最高价、最低价、收盘价
    open_prices = prices[:-1]
    close_prices = prices[1:]
    
    # 生成最高价和最低价（在开盘价和收盘价的基础上添加随机波动）
    high_prices = np.maximum(open_prices, close_prices) + np.random.uniform(0, 0.02, total_minutes)
    low_prices = np.minimum(open_prices, close_prices) - np.random.uniform(0, 0.02, total_minutes)
    
    # 生成成交量（随机整数）
    volumes = np.random.randint(10000, 1000000, total_minutes)
    
    # 创建DataFrame
    df = pd.DataFrame({
        'Open': open_prices,
        'High': high_prices,
        'Low': low_prices,
        'Close': close_prices,
        'Volume': volumes
    }, index=index)
    
    # 重命名列名为小写，与原有代码兼容
    df.columns = [col.lower() for col in df.columns]
    
    # 过滤掉休市时间的数据
    # 根据股票代码判断是港股还是A股
    # 港股交易时间：9:30-12:00和13:00-16:00
    # A股交易时间：9:30-11:30和13:00-15:00
    if len(symbol) == 5:
        # 港股交易时间
        morning_data = df.between_time('09:30:00', '12:00:00')
        afternoon_data = df.between_time('13:00:00', '16:00:00')
    else:
        # A股交易时间
        morning_data = df.between_time('09:30:00', '11:30:00')
        afternoon_data = df.between_time('13:00:00', '15:00:00')
    df = pd.concat([morning_data, afternoon_data]).sort_index()
    
    return df

# 识别缠论分型
def identify_fractals(df):
    """
    识别缠论分型（顶分型和底分型）
    :param df: 包含high和low列的DataFrame
    :return: 添加了顶分型和底分型标记的DataFrame
    """
    df['top_fractal'] = False
    df['bottom_fractal'] = False
    
    # 识别顶分型：中间K线最高价高于相邻两根K线
    for i in range(2, len(df)-2):
        if (df['high'].iloc[i] > df['high'].iloc[i-1] and 
            df['high'].iloc[i] > df['high'].iloc[i+1] and
            df['high'].iloc[i-1] > df['high'].iloc[i-2] and
            df['high'].iloc[i+1] > df['high'].iloc[i+2]):
            df.loc[df.index[i], 'top_fractal'] = True
    
    # 识别底分型：中间K线最低价低于相邻两根K线
    for i in range(2, len(df)-2):
        if (df['low'].iloc[i] < df['low'].iloc[i-1] and 
            df['low'].iloc[i] < df['low'].iloc[i+1] and
            df['low'].iloc[i-1] < df['low'].iloc[i-2] and
            df['low'].iloc[i+1] < df['low'].iloc[i+2]):
            df.loc[df.index[i], 'bottom_fractal'] = True
    
    return df

# 识别缠论笔
def identify_pens(df):
    """
    识别缠论笔
    :param df: 包含顶分型和底分型标记的DataFrame
    :return: 笔的列表，每个笔包含起始点、结束点和方向
    """
    pens = []
    fractals = []
    
    # 收集所有分型点
    for i in range(len(df)):
        if df['top_fractal'].iloc[i]:
            fractals.append((df.index[i], df['high'].iloc[i], 'top'))
        elif df['bottom_fractal'].iloc[i]:
            fractals.append((df.index[i], df['low'].iloc[i], 'bottom'))
    
    # 识别笔：顶底交替，且有一定涨幅
    if len(fractals) < 2:
        return pens
    
    current_type = fractals[0][2]
    current_point = fractals[0]
    
    for i in range(1, len(fractals)):
        next_point = fractals[i]
        next_type = next_point[2]
        
        # 顶底交替
        if next_type != current_type:
            # 计算笔的幅度
            amplitude = abs(next_point[1] - current_point[1])
            
            # 简单过滤：幅度大于0
            if amplitude > 0:
                direction = 'up' if next_type == 'top' else 'down'
                # 计算笔的最高价和最低价
                high = max(current_point[1], next_point[1])
                low = min(current_point[1], next_point[1])
                pens.append({
                    'start': current_point,
                    'end': next_point,
                    'direction': direction,
                    'high': high,
                    'low': low
                })
                current_type = next_type
                current_point = next_point
    
    return pens

# 识别缠论中枢
def identify_zhongshu(pens):
    """
    识别缠论中枢
    :param pens: 笔的列表
    :return: 中枢列表，每个中枢包含起始点、结束点、中枢区间（high, low）
    """
    zhongshus = []
    
    # 中枢需要至少3个笔
    if len(pens) < 3:
        return zhongshus
    
    # 遍历所有可能的笔组合，寻找中枢
    for i in range(len(pens) - 2):
        # 取连续的3个笔
        pen1 = pens[i]
        pen2 = pens[i + 1]
        pen3 = pens[i + 2]
        
        # 计算这三个笔的价格区间
        high1 = pen1['high']
        low1 = pen1['low']
        high2 = pen2['high']
        low2 = pen2['low']
        high3 = pen3['high']
        low3 = pen3['low']
        
        # 计算三个笔的最高高点和最低低点
        combined_high = min(high1, high2, high3)  # 中枢上沿是三个笔高点的最小值
        combined_low = max(low1, low2, low3)      # 中枢下沿是三个笔低点的最大值
        
        # 如果存在重叠，即中枢上沿大于中枢下沿，则形成中枢
        if combined_high > combined_low:
            # 初始中枢
            zhongshu = {
                'start': pen1['start'][0],
                'end': pen3['end'][0],
                'high': combined_high,
                'low': combined_low,
                'pens': [i, i + 1, i + 2]
            }
            
            # 检查后续笔是否继续扩展该中枢
            j = i + 3
            while j < len(pens):
                next_pen = pens[j]
                next_high = next_pen['high']
                next_low = next_pen['low']
                
                # 如果后续笔与当前中枢有重叠，则扩展中枢
                if next_high > zhongshu['low'] and next_low < zhongshu['high']:
                    # 更新中枢区间
                    zhongshu['high'] = min(zhongshu['high'], next_high)
                    zhongshu['low'] = max(zhongshu['low'], next_low)
                    zhongshu['end'] = pens[j]['end'][0]
                    zhongshu['pens'].append(j)
                    j += 1
                else:
                    break
            
            zhongshus.append(zhongshu)
    
    return zhongshus

# 识别缠论线段
def identify_segments(df, pens):
    """
    识别缠论线段
    :param df: 原始数据
    :param pens: 笔的列表
    :return: 线段的列表
    """
    segments = []
    
    if len(pens) < 3:
        return segments
    
    # 简单线段识别：笔的方向一致，且有重叠
    current_direction = pens[0]['direction']
    current_segment = [pens[0]]
    
    for i in range(1, len(pens)):
        pen = pens[i]
        
        if pen['direction'] == current_direction:
            current_segment.append(pen)
        else:
            # 检查是否形成线段（至少3笔）
            if len(current_segment) >= 3:
                segments.append({
                    'start': current_segment[0]['start'],
                    'end': current_segment[-1]['end'],
                    'direction': current_direction,
                    'pens': current_segment
                })
            # 开始新的线段
            current_direction = pen['direction']
            current_segment = [pen]
    
    # 检查最后一个线段
    if len(current_segment) >= 3:
        segments.append({
            'start': current_segment[0]['start'],
            'end': current_segment[-1]['end'],
            'direction': current_direction,
            'pens': current_segment
        })
    
    return segments

# 绘制K线图并标记缠论结构
def plot_candlestick_with_chan(df, pens, segments, zhongshus):
    """
    绘制K线图并标记缠论的分型、笔、线段和中枢
    :param df: 分钟数据
    :param pens: 笔的列表
    :param segments: 线段的列表
    :param zhongshus: 中枢列表
    """
    # 创建图形和坐标轴
    fig, ax = plt.subplots(figsize=(15, 10))
    
    # 创建一个新的索引，用于在图形上跳过中午休市时间
    # 将时间转换为数值，并为每个时间点分配一个连续的数值，跳过中午休市时间
    time_values = []
    time_labels = []
    current_value = 0
    
    for i, date in enumerate(df.index):
        # 将时间转换为小时和分钟
        hour = date.hour
        minute = date.minute
        
        # 添加当前时间点
        time_values.append(current_value)
        time_labels.append(date)
        
        # 如果不是最后一个时间点，计算下一个时间点的索引
        if i < len(df.index) - 1:
            next_date = df.index[i+1]
            next_hour = next_date.hour
            next_minute = next_date.minute
            
            # 检查是否需要跳过中午休市时间
            # 如果当前时间是上午11:30，下一个时间是下午13:00，跳过中午休市时间
            if hour == 11 and minute == 30 and next_hour == 13 and next_minute == 0:
                # 跳过中午休市时间，增加较大的间隔
                current_value += 60  # 跳过60分钟的间隔
            else:
                # 正常增加1分钟
                current_value += 1
        else:
            # 最后一个时间点，不需要增加
            pass
    
    # 绘制K线
    for i in range(len(df)):
        date = df.index[i]
        open_p = df['open'].iloc[i]
        high_p = df['high'].iloc[i]
        low_p = df['low'].iloc[i]
        close_p = df['close'].iloc[i]
        
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
        rect = Rectangle((time_values[i], bottom), 0.3, height, facecolor=color, edgecolor='black')
        ax.add_patch(rect)
        
        # 绘制上下影线
        ax.plot([time_values[i], time_values[i]], [low_p, high_p], color='black', linewidth=0.5)
    
    # 绘制中枢
    for i, zhongshu in enumerate(zhongshus):
        # 获取中枢对应的时间范围
        # 查找中枢开始和结束时间在time_values中的索引
        start_idx = df.index.get_loc(zhongshu['start'])
        end_idx = df.index.get_loc(zhongshu['end'])
        start_time = time_values[start_idx]
        end_time = time_values[end_idx]
        
        # 绘制中枢矩形
        ax.add_patch(Rectangle(
            (start_time, zhongshu['low']),
            end_time - start_time,
            zhongshu['high'] - zhongshu['low'],
            facecolor='yellow',
            alpha=0.3,
            label='中枢' if i == 0 else ""
        ))
        
        # 绘制中枢上沿和下沿
        ax.hlines(zhongshu['high'], start_time, end_time, colors='red', linestyles='--', alpha=0.7)
        ax.hlines(zhongshu['low'], start_time, end_time, colors='green', linestyles='--', alpha=0.7)
        
        # 添加中枢文本标注
        zhongshu_text = f"中枢{i+1}: [{zhongshu['low']:.2f}, {zhongshu['high']:.2f}]"
        ax.text(
            start_time, 
            zhongshu['high'] + (zhongshu['high'] - zhongshu['low']) * 0.1, 
            zhongshu_text, 
            fontsize=8, 
            color='red', 
            rotation=45, 
            bbox=dict(facecolor='white', alpha=0.8, boxstyle='round,pad=0.2')
        )
    
    # 标记顶分型和底分型
    top_fractals = df[df['top_fractal']]
    bottom_fractals = df[df['bottom_fractal']]
    
    # 获取顶分型和底分型在time_values中的索引
    top_indices = [df.index.get_loc(date) for date in top_fractals.index]
    bottom_indices = [df.index.get_loc(date) for date in bottom_fractals.index]
    
    ax.scatter([time_values[i] for i in top_indices], top_fractals['high'], 
               marker='^', color='purple', s=100, label='顶分型')
    ax.scatter([time_values[i] for i in bottom_indices], bottom_fractals['low'], 
               marker='v', color='blue', s=100, label='底分型')
    
    # 添加分型文本标注
    for i, (date, row) in enumerate(top_fractals.iterrows()):
        idx = df.index.get_loc(date)
        ax.text(
            time_values[idx], 
            row['high'] + 0.05, 
            f"顶分型{i+1}", 
            fontsize=8, 
            color='purple', 
            ha='center', 
            bbox=dict(facecolor='white', alpha=0.8, boxstyle='round,pad=0.2')
        )
    
    for i, (date, row) in enumerate(bottom_fractals.iterrows()):
        idx = df.index.get_loc(date)
        ax.text(
            time_values[idx], 
            row['low'] - 0.05, 
            f"底分型{i+1}", 
            fontsize=8, 
            color='blue', 
            ha='center', 
            bbox=dict(facecolor='white', alpha=0.8, boxstyle='round,pad=0.2')
        )
    
    # 绘制笔
    for i, pen in enumerate(pens):
        # 获取笔的开始和结束时间在time_values中的索引
        start_idx = df.index.get_loc(pen['start'][0])
        end_idx = df.index.get_loc(pen['end'][0])
        start_date = time_values[start_idx]
        start_price = pen['start'][1]
        end_date = time_values[end_idx]
        end_price = pen['end'][1]
        
        color = 'orange' if pen['direction'] == 'up' else 'cyan'
        ax.plot([start_date, end_date], [start_price, end_price], 
                color=color, linewidth=2, label='笔' if i == 0 else "")
        
        # 添加笔文本标注
        mid_date = (start_date + end_date) / 2
        mid_price = (start_price + end_price) / 2
        pen_text = f"笔{i+1}: {pen['direction']}"
        ax.text(
            mid_date, 
            mid_price + 0.1 if pen['direction'] == 'up' else mid_price - 0.1, 
            pen_text, 
            fontsize=9, 
            color='orange' if pen['direction'] == 'up' else 'cyan', 
            ha='center', 
            bbox=dict(facecolor='white', alpha=0.8, boxstyle='round,pad=0.2')
        )
    
    # 绘制线段
    for i, segment in enumerate(segments):
        # 获取线段的开始和结束时间在time_values中的索引
        start_idx = df.index.get_loc(segment['start'][0])
        end_idx = df.index.get_loc(segment['end'][0])
        start_date = time_values[start_idx]
        start_price = segment['start'][1]
        end_date = time_values[end_idx]
        end_price = segment['end'][1]
        
        color = 'red' if segment['direction'] == 'up' else 'green'
        ax.plot([start_date, end_date], [start_price, end_price], 
                color=color, linewidth=3, linestyle='--', label='线段' if i == 0 else "")
        
        # 添加线段文本标注
        mid_date = (start_date + end_date) / 2
        mid_price = (start_price + end_price) / 2
        segment_text = f"线段{i+1}: {segment['direction']}"
        ax.text(
            mid_date, 
            mid_price + 0.15 if segment['direction'] == 'up' else mid_price - 0.15, 
            segment_text, 
            fontsize=10, 
            color=color, 
            ha='center', 
            bbox=dict(facecolor='white', alpha=0.8, boxstyle='round,pad=0.2')
        )
    
    # 设置时间轴格式
    # 使用我们创建的time_labels作为x轴标签
    # 选择一些关键时间点作为刻度
    num_ticks = 10
    tick_indices = [int(i * (len(time_values) - 1) / (num_ticks - 1)) for i in range(num_ticks)]
    ax.set_xticks([time_values[i] for i in tick_indices])
    ax.set_xticklabels([time_labels[i].strftime('%Y-%m-%d %H:%M') for i in tick_indices], rotation=45)
    
    # 设置标题和标签
    ax.set_title('缠论K线分析图', fontsize=16)
    ax.set_xlabel('时间', fontsize=12)
    ax.set_ylabel('价格', fontsize=12)
    
    # 添加缠论定义文本框
    chan_definition = """缠论元素定义：
    分型：相邻三根K线中，中间K线的最高价（顶分型）或最低价（底分型）
         高于（低于）相邻两根K线的最高价（最低价）
    笔：由两个相邻的、方向相反的分型组成
       向上笔：底分型 + 顶分型
       向下笔：顶分型 + 底分型
    线段：由至少三笔组成，且前三笔必须有重叠
       向上线段：以向上笔开始，向下笔结束
       向下线段：以向下笔开始，向上笔结束
    中枢：某级别走势类型中，被至少三个连续次级别走势类型所重叠的部分
       由至少三个连续的、有重叠的笔或线段构成"""
    
    ax.text(0.02, 0.02, chan_definition, transform=ax.transAxes, 
            fontsize=9, verticalalignment='bottom', 
            bbox=dict(boxstyle='round', facecolor='lightyellow', alpha=0.8))
    
    # 添加网格和图例
    ax.grid(True, linestyle='--', alpha=0.7)
    ax.legend(loc='upper left')
    
    # 调整布局
    plt.tight_layout()
    
    # 保存图像
    plt.savefig('chan_analysis.png', dpi=300)
    print("缠论分析图已保存为 chan_analysis.png")
    
    # 显示图像
    plt.show()

# 主函数

def main():
    print("缠论K线分析工具")
    print("=" * 30)
    
    # 添加命令行参数解析
    import argparse
    parser = argparse.ArgumentParser(description='缠论K线分析工具')
    parser.add_argument('symbol', nargs='?', help='股票代码，例如：600000')
    parser.add_argument('days', nargs='?', type=int, default=1, help='获取数据的天数，默认：1')
    args = parser.parse_args()
    
    # 如果命令行没有提供股票代码，则交互式输入
    if args.symbol:
        symbol = args.symbol
    else:
        # 交互式输入股票代码
        symbol = input("请输入股票代码（默认：600000）：").strip()
        
        # 如果用户没有输入，使用默认股票代码
        if not symbol:
            symbol = "600000"
            print(f"使用默认股票代码：{symbol}（浦发银行）")
        else:
            print(f"使用股票代码：{symbol}")
    
    days = args.days
    print(f"获取最近 {days} 天的1分钟数据")
    
    # 获取1分钟级别数据
    print(f"正在获取股票 {symbol} 的1分钟数据...")
    df = get_minute_data(symbol, days=days)
    
    if df is None:
        return
    
    print(f"成功获取 {len(df)} 条1分钟数据")
    
    # 识别分型
    print("正在识别分型...")
    df = identify_fractals(df)
    
    # 识别笔
    print("正在识别笔...")
    pens = identify_pens(df)
    print(f"识别到 {len(pens)} 个笔")
    
    # 识别线段
    print("正在识别线段...")
    segments = identify_segments(df, pens)
    print(f"识别到 {len(segments)} 个线段")
    
    # 识别中枢
    print("正在识别中枢...")
    zhongshus = identify_zhongshu(pens)
    print(f"识别到 {len(zhongshus)} 个中枢")
    
    # 绘制K线图并标记缠论结构
    print("正在绘制缠论分析图...")
    plot_candlestick_with_chan(df, pens, segments, zhongshus)

if __name__ == "__main__":
    main()