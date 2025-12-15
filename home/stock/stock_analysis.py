import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import matplotlib.pyplot as plt
import mplfinance as mpf
from matplotlib.ticker import MultipleLocator, FormatStrFormatter
import logging
import sys
import argparse
import urllib.request
import json
from tqdm import tqdm

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# API配置常量
API_CONFIG = {
    'EAST_MONEY_BASE_URL': 'https://push2his.eastmoney.com/api/qt/stock/kline/get',
    'MARKET_CODE_MAP': {
        'sh': '1',       # 上海证券交易所
        'sz': '0',       # 深圳证券交易所
        'hk': '116'      # 香港证券交易所
    },
    'DEFAULT_STOCK_CODE': 'sh600000',
    'DEFAULT_KLINE_LENGTH': 100,
    'DEFAULT_KLINE_SCALE': 1
}

# 缠论参数配置
CHANLUN_CONFIG = {
    'FRACTAL_BAR_COUNT': 2,
    'MIN_PENS_FOR_SEGMENT': 3,
    'MIN_PENS_FOR_CENTRAL': 3,
    'PRICE_CHANGE_THRESHOLD': 0.01
}

# 可视化配置
VISUAL_CONFIG = {
    'FIG_SCALE': 1.5,
    'FIG_RATIO': (15, 8),
    'CANDLE_STYLE': 'chinese',
    'VOLUME_ENABLED': True
}

# 股票数据获取模块
class StockDataFetcher:
    def __init__(self):
        self.base_url = "http://hq.sinajs.cn/list="
    
    def fetch_minute_data(self, stock_code):
        """获取股票的1分钟K线数据，支持上海、深圳和香港证券交易所
        
        向后兼容方法，调用fetch_kline_data获取1分钟数据
        """
        return self.fetch_kline_data(stock_code, period='1min')
    
    def fetch_kline_data(self, stock_code, period='1min'):
        """获取股票的K线数据，支持上海、深圳和香港证券交易所
        
        参数:
        stock_code: 股票代码，格式如 sh600000, sz000001, hk09988
        period: K线周期，支持 1min, 5min, 15min, 30min, 60min, 1d, 1w, 1M
        """
        try:
            # 处理不同交易所的股票代码
            stock_code = stock_code.lower()
            
            # 周期参数映射表
            period_map = {
                '1min': 1,
                '5min': 5,
                '15min': 15,
                '30min': 30,
                '60min': 60,
                '1d': 101,
                '1w': 102,
                '1M': 103
            }
            
            # 获取对应的K线周期参数
            klt = period_map.get(period, 1)
            
            # 确定交易所和对应的市场代码
            if stock_code.startswith('sh'):
                logger.info(f"正在从东方财富获取上海证券交易所{stock_code}的{period}K线数据...")
                market_code = '1'
                stock_num = stock_code[2:]
            elif stock_code.startswith('sz'):
                logger.info(f"正在从东方财富获取深圳证券交易所{stock_code}的{period}K线数据...")
                market_code = '0'
                stock_num = stock_code[2:]
            elif stock_code.startswith('hk'):
                logger.info(f"正在获取香港证券交易所{stock_code}的{period}K线数据...")
                market_code = '116'
                stock_num = stock_code[2:]
            else:
                logger.error(f"不支持的股票代码格式: {stock_code}")
                return self._generate_mock_data(stock_code)
            
            # 构建东方财富代码和API URL
            eastmoney_code = f"{market_code}.{stock_num}"
            # 使用当前时间作为结束时间，确保获取最新的数据
            end_time = datetime.now().strftime('%Y%m%d%H%M%S')
            url = f"https://push2his.eastmoney.com/api/qt/stock/kline/get?secid={eastmoney_code}&fields1=f1,f2,f3,f4,f5,f6&fields2=f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61&klt={klt}&fqt=1&end={end_time}&lmt=200"
            
            logger.debug(f"请求URL: {url}")
            
            # 添加请求头，模拟真实浏览器访问
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                'Accept': '*/*',
                'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
                'Referer': 'https://quote.eastmoney.com/' if market_code != '116' else 'https://finance.sina.com.cn/',
                'Connection': 'keep-alive'
            }
            
            # 创建请求对象
            req = urllib.request.Request(url, headers=headers)
            
            print(f"\n[步骤1.1] 正在从东方财富获取{stock_code}的{period}K线数据...")
            try:
                # 使用内置的urllib库获取数据，设置较短的超时时间
                with urllib.request.urlopen(req, timeout=5) as response:
                    logger.info(f"响应状态码: {response.getcode()}")
                    data_str = response.read().decode('utf-8')  # 使用utf-8编码
                
                logger.info(f"成功获取到{stock_code}的{period}K线数据，响应长度: {len(data_str)}字符")
                logger.debug(f"原始响应数据: {data_str[:500]}...")  # 显示更多的响应数据
                
                # 解析JSON数据
                print(f"[步骤1.2] 正在解析JSON数据...")
                try:
                    data = json.loads(data_str)
                    logger.info(f"成功解析JSON数据")
                except json.JSONDecodeError as e:
                    logger.error(f"解析JSON数据失败: {str(e)}")
                    logger.error(f"原始响应数据: {data_str}")
                    return self._generate_mock_data(stock_code)
                
                # 处理不同交易所的数据格式
                kline_data = []
                
                # 检查响应状态
                if data.get('rc') != 0:
                    logger.error(f"东方财富API返回错误: {data.get('msg', '未知错误')}")
                    return self._generate_mock_data(stock_code)
                
                # 提取K线数据
                klines = data.get('data', {}).get('klines', [])
                logger.info(f"提取到{len(klines)}条{period}K线数据")
                
                if not klines:
                    logger.warning(f"未获取到{stock_code}的{period}K线数据，将返回模拟数据")
                    return self._generate_mock_data(stock_code)
            except urllib.error.URLError as e:
                logger.error(f"网络请求失败: {str(e)}")
                return self._generate_mock_data(stock_code)
            except Exception as e:
                logger.error(f"获取数据时发生未知错误: {str(e)}")
                import traceback
                traceback.print_exc()
                return self._generate_mock_data(stock_code)
            
            # 解析K线数据（适用于上海、深圳和香港证券交易所）
            print(f"\n[步骤1.1] 正在解析{stock_code}的{period}K线数据...")
            for kline in tqdm(klines, desc="解析K线数据", unit="条"):
                parts = kline.split(',')
                if len(parts) >= 6:
                    datetime_str = parts[0]
                    open_price = float(parts[1])
                    close_price = float(parts[2])
                    high_price = float(parts[3])
                    low_price = float(parts[4])
                    volume = float(parts[5])
                    
                    kline_data.append({
                        'datetime': datetime_str,
                        'open': open_price,
                        'close': close_price,
                        'high': high_price,
                        'low': low_price,
                        'volume': volume
                    })
            
            # 转换为DataFrame
            print(f"\n[步骤1.2] 正在转换数据格式...")
            df = pd.DataFrame(kline_data)
            
            # 转换时间格式
            df['datetime'] = pd.to_datetime(df['datetime'])
            df.set_index('datetime', inplace=True)
            
            # 只保留需要的列
            df = df[['open', 'high', 'low', 'close', 'volume']]
            
            logger.info(f"成功获取{stock_code}的{period}K线数据，共{len(df)}条记录")
            return df
        except Exception as e:
            logger.error(f"从东方财富获取数据失败: {str(e)}，将返回模拟数据")
            import traceback
            traceback.print_exc()
            return self._generate_mock_data(stock_code)
    
    def _generate_mock_data(self, stock_code):
        """生成模拟的1分钟K线数据用于演示"""
        print(f"\n[步骤1.1] 正在生成{stock_code}的模拟K线数据...")
        
        # 生成固定的100分钟数据，不依赖当前时间
        today = datetime.now().date()
        start_time = datetime.combine(today, datetime.min.time()) + timedelta(hours=9, minutes=30)
        times = [start_time + timedelta(minutes=i) for i in range(101)]
        
        # 生成价格数据（使用随机游走，添加一些波动以产生分型）
        base_price = 10.0 if not stock_code.startswith('6') else 50.0
        # 添加一些趋势和波动，确保产生足够的分型
        returns = np.random.normal(0, 0.002, len(times))
        
        # 添加一些趋势成分
        print(f"\n[步骤1.2] 正在生成价格趋势数据...")
        for i in tqdm(range(len(returns)), desc="生成趋势数据", unit="个"):
            if 20 <= i < 40:
                returns[i] += 0.003  # 上升趋势
            elif 60 <= i < 80:
                returns[i] -= 0.003  # 下降趋势
        
        prices = base_price * np.exp(np.cumsum(returns))
        
        # 生成OHLC数据
        opens = prices[:-1]
        closes = prices[1:]
        highs = np.maximum(opens, closes) + np.random.uniform(0, base_price * 0.005, len(opens))
        lows = np.minimum(opens, closes) - np.random.uniform(0, base_price * 0.005, len(opens))
        volumes = np.random.uniform(1000, 10000, len(opens))
        
        # 创建DataFrame
        df = pd.DataFrame()
        df['datetime'] = pd.to_datetime(times[1:])  # 从第二个时间开始
        df.set_index('datetime', inplace=True)
        df['open'] = opens
        df['high'] = highs
        df['low'] = lows
        df['close'] = closes
        df['volume'] = volumes
        
        return df

# 缠论分析模块
class ChanlunAnalyzer:
    def __init__(self):
        self.top_fractals = []  # 顶分型
        self.bottom_fractals = []  # 底分型
        self.pens = []  # 笔
        self.segments = []  # 线段
        self.centrals = []  # 中枢
        
    def visualize_all(self, df, show_figure=True, save_path=None):
        """
        可视化K线图及缠论元素（分型、笔、线段、中枢）
        
        参数:
        df: 包含数据DataFrame
        show_figure: 是否显示图表，默认为True
        save_path: 保存图表的路径，默认为None
        """
        # 设置中文字体，使用更可靠的方法
        try:
            # 尝试使用matplotlib的字体管理器来查找合适的中文字体
            from matplotlib.font_manager import FontProperties
            import matplotlib.font_manager as fm
            
            # 查找系统中可用的中文字体
            chinese_fonts = []
            for font in fm.fontManager.ttflist:
                if 'SimHei' in font.name or 'Microsoft YaHei' in font.name or 'Arial Unicode MS' in font.name:
                    chinese_fonts.append(font.name)
            
            if chinese_fonts:
                # 使用找到的第一个中文字体
                plt.rcParams['font.sans-serif'] = chinese_fonts
            else:
                # 如果没有找到中文字体，使用默认字体列表
                plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'Arial Unicode MS', 'DejaVu Sans', 'WenQuanYi Micro Hei', 'Heiti TC']
        except Exception as e:
            # 如果字体管理器出现问题，使用默认字体列表
            plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'Arial Unicode MS', 'DejaVu Sans', 'WenQuanYi Micro Hei', 'Heiti TC']
        
        plt.rcParams['axes.unicode_minus'] = False  # 用来正常显示负号
        
        # 使用mplfinance绘制K线图
        mc = mpf.make_marketcolors(up='red', down='green', wick='inherit', edge='inherit', volume='inherit')
        s = mpf.make_mpf_style(marketcolors=mc, gridaxis='both', gridstyle='-.', y_on_right=False, rc={'font.sans-serif': plt.rcParams['font.sans-serif']})
        
        # 计算MACD和KDJ指标
        df = self.calculate_macd(df)
        df = self.calculate_kdj(df)
        
        # 准备额外的绘图元素
        addplot = []
        
        # 添加分型点
        if hasattr(self, 'top_fractals') and self.top_fractals:
            # 直接创建与df等长的数据数组
            top_data = [np.nan] * len(df)
            for fractal in self.top_fractals:
                try:
                    # 检查数据结构类型
                    if isinstance(fractal, tuple) and len(fractal) >= 2:
                        # 元组格式 (index, ..., price, ...)
                        idx = fractal[0]
                        value = fractal[2] if len(fractal) > 2 else fractal[1]
                        if idx >= 0 and idx < len(df):
                            top_data[idx] = value
                    elif isinstance(fractal, dict):
                        # 字典格式，添加键存在性检查
                        idx = fractal.get('index')
                        value = fractal.get('high', fractal.get('price'))
                        if idx is not None and value is not None and idx >= 0 and idx < len(df):
                            top_data[idx] = value
                except (KeyError, IndexError, TypeError):
                    pass  # 忽略数据结构不匹配或索引错误的分型
            
            addplot.append(mpf.make_addplot(top_data, type='scatter', markersize=80, marker='^', color='red', label='顶分型'))
            
        if hasattr(self, 'bottom_fractals') and self.bottom_fractals:
            # 直接创建与df等长的数据数组
            bottom_data = [np.nan] * len(df)
            for fractal in self.bottom_fractals:
                try:
                    # 检查数据结构类型
                    if isinstance(fractal, tuple) and len(fractal) >= 2:
                        # 元组格式 (index, ..., price, ...)
                        idx = fractal[0]
                        value = fractal[2] if len(fractal) > 2 else fractal[1]
                        if idx >= 0 and idx < len(df):
                            bottom_data[idx] = value
                    elif isinstance(fractal, dict):
                        # 字典格式，添加键存在性检查
                        idx = fractal.get('index')
                        value = fractal.get('low', fractal.get('price'))
                        if idx is not None and value is not None and idx >= 0 and idx < len(df):
                            bottom_data[idx] = value
                except (KeyError, IndexError, TypeError):
                    pass  # 忽略数据结构不匹配或索引错误的分型
            
            addplot.append(mpf.make_addplot(bottom_data, type='scatter', markersize=80, marker='v', color='green', label='底分型'))
        
        # 添加笔
        if hasattr(self, 'pens') and self.pens:
            for i, pen in enumerate(self.pens):
                try:
                    start_idx = pen['start_index']
                    end_idx = pen['end_index']
                    start_price = pen['start_price']
                    end_price = pen['end_price']
                    # 确保索引在有效范围内
                    if start_idx >= 0 and end_idx < len(df) and start_idx < end_idx:
                        # 缠论笔应该是连接两个分型点的直线
                        # 填充起点到终点之间的所有值，使用直线连接
                        pen_data = [np.nan] * len(df)
                        # 填充起点和终点
                        pen_data[start_idx] = start_price
                        pen_data[end_idx] = end_price
                        # 填充中间点，使用直线插值
                        for idx in range(start_idx + 1, end_idx):
                            # 计算直线上的中间点值
                            pen_data[idx] = start_price + (end_price - start_price) * (idx - start_idx) / (end_idx - start_idx)
                        
                        # 根据方向选择颜色
                        color = 'blue' if pen['direction'] == 'up' else 'purple'
                        
                        # 添加笔到额外绘图元素
                        if i == 0:
                            addplot.append(mpf.make_addplot(pen_data, type='line', color=color, label='笔'))
                        else:
                            addplot.append(mpf.make_addplot(pen_data, type='line', color=color))
                except (KeyError, IndexError):
                    pass  # 忽略数据结构不匹配或索引错误的笔
        
        # 添加线段
        if hasattr(self, 'segments') and self.segments:
            for i, segment in enumerate(self.segments):
                try:
                    pens = segment.get('pens', [])
                    if pens and len(pens) >= 2:
                        # 使用与df等长的数据数组
                        line_data = [np.nan] * len(df)
                        
                        # 线段应该连接各个笔的端点，形成折线
                        # 首先处理第一个笔的起点
                        first_pen = pens[0]
                        line_data[first_pen['start_index']] = first_pen['start_price']
                        
                        # 然后处理所有笔的端点
                        for pen in pens:
                            line_data[pen['end_index']] = pen['end_price']
                        
                        # 对于线段中的相邻笔，连接它们的端点
                        for j in range(len(pens) - 1):
                            current_pen = pens[j]
                            next_pen = pens[j + 1]
                            
                            start_idx = current_pen['end_index']
                            end_idx = next_pen['end_index']
                            start_price = current_pen['end_price']
                            end_price = next_pen['end_price']
                            
                            # 填充相邻笔端点之间的所有值，使用直线连接
                            for idx in range(start_idx + 1, end_idx):
                                if 0 <= idx < len(df):
                                    ratio = (idx - start_idx) / (end_idx - start_idx)
                                    line_data[idx] = start_price + (end_price - start_price) * ratio
                        
                        # 根据方向选择颜色
                        color = 'orange' if segment.get('direction') == 'up' else 'cyan'
                        
                        if i == 0:
                            addplot.append(mpf.make_addplot(line_data, type='line', color=color, label='线段', linewidth=2.5))
                        else:
                            addplot.append(mpf.make_addplot(line_data, type='line', color=color, linewidth=2.5))
                except (KeyError, IndexError):
                    pass  # 忽略数据结构不匹配或索引错误的线段
        
        # 添加中枢
        if hasattr(self, 'centrals') and self.centrals:
            for i, central in enumerate(self.centrals):
                try:
                    start_idx = central.get('start_index')
                    end_idx = central.get('end_index')
                    central_high = central.get('high')
                    central_low = central.get('low')
                    
                    # 确保索引在有效范围内
                    if start_idx is not None and end_idx is not None and central_high is not None and central_low is not None:
                        if start_idx >= 0 and end_idx < len(df) and start_idx < end_idx:
                            # 中枢颜色
                            central_type = central.get('type', 'neutral')
                            if central_type == 'up':
                                color = 'yellow'
                            elif central_type == 'down':
                                color = 'pink'
                            else:
                                color = 'gray'
                            
                            # 创建与df等长的数据数组
                            upper_data = [np.nan] * len(df)
                            lower_data = [np.nan] * len(df)
                            
                            # 中枢上限和下限
                            for idx in range(start_idx, end_idx + 1):
                                if 0 <= idx < len(df):
                                    upper_data[idx] = central_high
                                    lower_data[idx] = central_low
                            
                            # 使用填充区域来表示中枢，更加直观
                            # 添加中枢上限
                            addplot.append(mpf.make_addplot(upper_data, type='line', color=color, alpha=0.7, linewidth=1.5))
                            # 添加中枢下限
                            addplot.append(mpf.make_addplot(lower_data, type='line', color=color, alpha=0.7, linewidth=1.5))
                            # 添加中枢填充区域
                            # 由于mplfinance不直接支持填充区域，我们使用两条线之间的填充
                            # 这里使用中间线来表示填充区域
                            mid_data = [np.nan] * len(df)
                            for idx in range(start_idx, end_idx + 1):
                                if 0 <= idx < len(df):
                                    mid_data[idx] = (central_high + central_low) / 2
                            # 添加填充区域的中间线，用于视觉参考
                            addplot.append(mpf.make_addplot(mid_data, type='line', color=color, alpha=0.5, linestyle='--', linewidth=1))
                except (KeyError, IndexError):
                    pass  # 忽略数据结构不匹配或索引错误的中枢
        
        # 配置面板布局，确保所有指标都能正确显示
        # 价格面板（默认）、成交量面板、MACD面板、KDJ面板
        panel_ratios = (4, 1, 2, 2)  # 各面板高度比例
        
        # 添加MACD指标到面板2
        # 添加DIF线
        addplot.append(mpf.make_addplot(df['dif'], panel=2, type='line', color='blue', label='DIF'))
        # 添加DEA线
        addplot.append(mpf.make_addplot(df['dea'], panel=2, type='line', color='yellow', label='DEA'))
        # 添加MACD柱状图
        macd_colors = ['red' if val >= 0 else 'green' for val in df['macd']]
        addplot.append(mpf.make_addplot(df['macd'], panel=2, type='bar', color=macd_colors, label='MACD'))
        
        # 添加KDJ指标到面板3
        # 添加K线
        addplot.append(mpf.make_addplot(df['k'], panel=3, type='line', color='blue', label='K'))
        # 添加D线
        addplot.append(mpf.make_addplot(df['d'], panel=3, type='line', color='yellow', label='D'))
        # 添加J线
        addplot.append(mpf.make_addplot(df['j'], panel=3, type='line', color='purple', label='J'))
        # 添加超买线（80）
        addplot.append(mpf.make_addplot([80] * len(df), panel=3, type='line', color='gray', linestyle='--', label='超买线'))
        # 添加超卖线（20）
        addplot.append(mpf.make_addplot([20] * len(df), panel=3, type='line', color='gray', linestyle='--', label='超卖线'))
        
        # 绘制图表，启用成交量显示，并配置面板布局
        fig, axlist = mpf.plot(df, type='candle', style=s, title='股票K线图 - 缠论分析', 
                             ylabel='价格', addplot=addplot, figscale=1.5, 
                             figratio=(15, 8), volume=True, volume_panel=1, 
                             panel_ratios=panel_ratios, returnfig=True, tight_layout=True)
        
        # 获取主绘图区域
        ax = axlist[0]
        
        # 添加图例
        handles, labels = ax.get_legend_handles_labels()
        # 移除重复的标签
        by_label = dict(zip(labels, handles))
        ax.legend(by_label.values(), by_label.keys(), loc='upper left')
        
        # 保存图表
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            logger.info(f"图表已保存至: {save_path}")
        
        # 显示图表
        if show_figure:
            plt.show()
        
        return fig, ax
    
    def identify_fractals(self, df, bar_count=2):
        """
        识别分型（顶分型和底分型）
        
        参数:
        df: 包含OHLC数据的DataFrame
        bar_count: 分型所需的相邻K线数量，默认为2（即通常的3根K线分型）
        
        返回:
        包含分型信息的DataFrame
        """
        # 创建结果DataFrame，复制原始数据并添加分型标记列
        result_df = df.copy()
        result_df['top_fractal'] = 0
        result_df['bottom_fractal'] = 0
        
        # 重置顶底分型列表
        self.top_fractals = []
        self.bottom_fractals = []
        
        # 提取价格数据到numpy数组，提高访问速度
        highs = df['high'].values
        lows = df['low'].values
        
        # 遍历数据，识别分型
        print(f"\n正在识别分型...")
        for i in tqdm(range(bar_count, len(df) - bar_count), desc="识别分型", unit="个"):
            # 顶分型识别: 中间K线的高点是相邻bar_count根K线中最高的
            current_high = highs[i]
            # 使用numpy切片和向量化操作提高效率
            if (highs[i-bar_count:i] < current_high).all() and (highs[i+1:i+bar_count+1] < current_high).all():
                result_df.loc[result_df.index[i], 'top_fractal'] = 1
                self.top_fractals.append({
                    'index': i,
                    'datetime': df.index[i],
                    'price': current_high
                })
            
            # 底分型识别: 中间K线的低点是相邻bar_count根K线中最低的
            current_low = lows[i]
            # 使用numpy切片和向量化操作提高效率
            if (lows[i-bar_count:i] > current_low).all() and (lows[i+1:i+bar_count+1] > current_low).all():
                result_df.loc[result_df.index[i], 'bottom_fractal'] = 1
                self.bottom_fractals.append({
                    'index': i,
                    'datetime': df.index[i],
                    'price': current_low
                })
        
        logger.info(f"识别出 {len(self.top_fractals)} 个顶分型和 {len(self.bottom_fractals)} 个底分型")
        return result_df
    
    def filter_fractals(self, df):
        """
        过滤分型，去除无效的分型
        
        参数:
        df: 包含分型标记的DataFrame
        
        返回:
        过滤后的分型列表
        """
        # 合并并按时间排序所有分型
        all_fractals = []
        
        # 添加顶分型
        all_fractals.extend((f['index'], f['datetime'], f['price'], 'top') for f in self.top_fractals)
        # 添加底分型
        all_fractals.extend((f['index'], f['datetime'], f['price'], 'bottom') for f in self.bottom_fractals)
        
        # 按时间排序
        all_fractals.sort(key=lambda x: x[0])
        
        # 过滤分型：确保顶底交替出现
        filtered_fractals = []
        last_type = None
        
        for idx, dt, price, f_type in all_fractals:
            # 如果是第一个分型，或者与上一个分型类型不同，则保留
            if last_type is None or f_type != last_type:
                filtered_fractals.append((idx, dt, price, f_type))
                last_type = f_type
            # 如果与上一个分型类型相同，保留价格更极端的那个
            elif last_type == 'top' and f_type == 'top':
                if price > filtered_fractals[-1][2]:  # 新顶分型更高
                    filtered_fractals[-1] = (idx, dt, price, f_type)
            elif last_type == 'bottom' and f_type == 'bottom':
                if price < filtered_fractals[-1][2]:  # 新底分型更低
                    filtered_fractals[-1] = (idx, dt, price, f_type)
        
        # 更新分型列表
        self.top_fractals = []
        self.bottom_fractals = []
        
        for f in filtered_fractals:
            fractal_dict = {'index': f[0], 'datetime': f[1], 'price': f[2]}
            if f[3] == 'top':
                self.top_fractals.append(fractal_dict)
            else:
                self.bottom_fractals.append(fractal_dict)
        
        logger.info(f"过滤后剩余 {len(self.top_fractals)} 个顶分型和 {len(self.bottom_fractals)} 个底分型")
        return filtered_fractals
    
    def divide_pens(self, df, filtered_fractals, threshold_percent=0.005):
        """
        基于分型划分笔
        
        参数:
        df: 包含OHLC数据的DataFrame
        filtered_fractals: 过滤后的分型列表
        threshold_percent: 笔的最小价格波动阈值百分比，默认为0.5%
        
        返回:
        笔的列表
        """
        if len(filtered_fractals) < 2:
            logger.warning("分型数量不足，无法划分笔")
            return []
        
        self.pens = []
        current_pen_start = filtered_fractals[0]
        
        # 遍历分型，构建笔
        for current_fractal in filtered_fractals[1:]:
            # 计算价格波动幅度
            price_change = abs(current_fractal[2] - current_pen_start[2])
            price_change_percent = price_change / current_pen_start[2]
            
            # 检查是否满足笔的条件：价格波动超过阈值
            if price_change_percent >= threshold_percent:
                # 创建笔
                # 笔的方向应该根据实际价格变化来判断，而不仅仅是分型类型的组合
                pen_direction = 'up' if current_fractal[2] > current_pen_start[2] else 'down'
                pen = {
                    'start_index': current_pen_start[0],
                    'start_datetime': current_pen_start[1],
                    'start_price': current_pen_start[2],
                    'start_type': current_pen_start[3],
                    'end_index': current_fractal[0],
                    'end_datetime': current_fractal[1],
                    'end_price': current_fractal[2],
                    'end_type': current_fractal[3],
                    'direction': pen_direction,
                    'length': abs(current_fractal[0] - current_pen_start[0]),
                    'price_change': price_change,
                    'price_change_percent': price_change_percent
                }
                
                self.pens.append(pen)
                current_pen_start = current_fractal
            else:
                # 价格波动未超过阈值，继续使用当前分型作为笔的起点
                # 但记录日志，方便调试
                logger.debug(f"跳过分型 {current_fractal[1]}，价格波动 {price_change_percent:.4%} 未超过阈值 {threshold_percent:.4%}")
            
        logger.info(f"成功划分 {len(self.pens)} 笔")
        return self.pens
    
    def validate_pens(self):
        """
        验证笔的有效性，确保笔之间没有重叠或违反缠论规则
        
        返回:
        有效的笔列表
        """
        if len(self.pens) < 2:
            return self.pens
        
        valid_pens = [self.pens[0]]
        
        for i in range(1, len(self.pens)):
            current_pen = self.pens[i]
            last_valid_pen = valid_pens[-1]
            
            # 检查笔的方向是否交替
            if current_pen['direction'] == last_valid_pen['direction']:
                # 如果方向相同，需要更仔细的处理
                # 保留价格变动更大的笔，并且确保笔的端点更极端
                if current_pen['price_change_percent'] > last_valid_pen['price_change_percent']:
                    # 检查笔的端点是否更极端
                    if current_pen['direction'] == 'up':
                        # 向上笔，检查结束价格是否更高
                        if current_pen['end_price'] > last_valid_pen['end_price']:
                            valid_pens[-1] = current_pen
                    else:
                        # 向下笔，检查结束价格是否更低
                        if current_pen['end_price'] < last_valid_pen['end_price']:
                            valid_pens[-1] = current_pen
            else:
                # 方向不同，直接添加
                valid_pens.append(current_pen)
        
        # 进一步检查笔的完整性，确保笔的起点和终点都是有效的分型
        final_pens = []
        for pen in valid_pens:
            # 确保笔的起点和终点都是有效的分型点
            # 检查笔的长度是否合理，实时数据中笔的长度可能较短
            if pen['length'] >= 1:  # 笔至少包含1根K线
                final_pens.append(pen)
        
        # 最终检查：确保笔的方向严格交替
        if len(final_pens) >= 3:
            # 多次检查，直到所有笔的方向都交替
            all_alternating = False
            max_iterations = 5  # 最大迭代次数，避免无限循环
            iterations = 0
            
            while not all_alternating and iterations < max_iterations:
                all_alternating = True
                for i in range(1, len(final_pens) - 1):
                    prev_pen = final_pens[i-1]
                    curr_pen = final_pens[i]
                    next_pen = final_pens[i+1]
                    
                    if prev_pen['direction'] == next_pen['direction'] and prev_pen['direction'] != curr_pen['direction']:
                        # 出现了方向交替的情况，这是正常的，继续检查
                        continue
                    else:
                        # 发现方向不交替的情况，需要移除中间的笔
                        # 比较三个笔的价格变动，保留价格变动最大的两个笔
                        max_change_pen = max([prev_pen, curr_pen, next_pen], key=lambda x: x['price_change_percent'])
                        min_change_pen = min([prev_pen, curr_pen, next_pen], key=lambda x: x['price_change_percent'])
                        
                        # 移除价格变动最小的笔
                        if min_change_pen == prev_pen:
                            final_pens.pop(i-1)
                        elif min_change_pen == curr_pen:
                            final_pens.pop(i)
                        else:
                            final_pens.pop(i+1)
                        
                        # 标记为需要重新检查
                        all_alternating = False
                        break
                iterations += 1
        
        # 更新笔列表
        self.pens = final_pens
        logger.info(f"验证后剩余 {len(self.pens)} 笔")
        return self.pens
    
    def divide_segments(self):
        """
        基于笔划分线段
        
        返回:
        线段的列表
        """
        if len(self.pens) < 3:
            logger.warning("笔的数量不足，无法划分线段（至少需要3笔）")
            return []
        
        self.segments = []
        current_segments = []
        
        # 线段的起始方向由前三笔决定
        # 收集前三笔
        first_three_pens = self.pens[:3]
        
        # 检查是否有重叠区域
        if self._has_overlap(first_three_pens):
            # 确定线段方向（由第一笔方向决定）
            segment_direction = first_three_pens[0]['direction']
            
            # 创建初始线段
            current_segment = {
                'start_index': first_three_pens[0]['start_index'],
                'start_datetime': first_three_pens[0]['start_datetime'],
                'start_price': first_three_pens[0]['start_price'],
                'end_index': first_three_pens[2]['end_index'],
                'end_datetime': first_three_pens[2]['end_datetime'],
                'end_price': first_three_pens[2]['end_price'],
                'direction': segment_direction,
                'pens': first_three_pens.copy()
            }
            current_segments.append(current_segment)
        
        # 处理剩余的笔
        for i in range(3, len(self.pens)):
            current_pen = self.pens[i]
            last_segment = current_segments[-1] if current_segments else None
            
            if last_segment:
                # 检查是否形成新的线段
                # 新线段形成的条件：当前笔与线段中的某些笔形成相反方向且破坏原线段
                if self._is_segment_break(last_segment, current_pen):
                    # 创建新线段
                    new_segment_direction = 'up' if last_segment['direction'] == 'down' else 'down'
                    new_segment = {
                        'start_index': last_segment['end_index'],
                        'start_datetime': last_segment['end_datetime'],
                        'start_price': last_segment['end_price'],
                        'end_index': current_pen['end_index'],
                        'end_datetime': current_pen['end_datetime'],
                        'end_price': current_pen['end_price'],
                        'direction': new_segment_direction,
                        'pens': [last_segment['pens'][-1], current_pen]
                    }
                    current_segments.append(new_segment)
                else:
                    # 扩展当前线段
                    last_segment['end_index'] = current_pen['end_index']
                    last_segment['end_datetime'] = current_pen['end_datetime']
                    last_segment['end_price'] = current_pen['end_price']
                    last_segment['pens'].append(current_pen)
            else:
                # 尝试形成新的初始线段
                if i + 2 < len(self.pens):
                    test_pens = self.pens[i:i+3]
                    if self._has_overlap(test_pens):
                        segment_direction = test_pens[0]['direction']
                        new_segment = {
                            'start_index': test_pens[0]['start_index'],
                            'start_datetime': test_pens[0]['start_datetime'],
                            'start_price': test_pens[0]['start_price'],
                            'end_index': test_pens[2]['end_index'],
                            'end_datetime': test_pens[2]['end_datetime'],
                            'end_price': test_pens[2]['end_price'],
                            'direction': segment_direction,
                            'pens': test_pens.copy()
                        }
                        current_segments.append(new_segment)
        
        self.segments = current_segments
        logger.info(f"成功划分 {len(self.segments)} 个线段")
        return self.segments
    
    def _has_overlap(self, pens):
        """
        检查一组笔是否有价格重叠区域
        
        参数:
        pens: 笔的列表
        
        返回:
        是否有重叠
        """
        if len(pens) < 2:
            return False
        
        # 找出所有笔的价格范围
        all_highs = []
        all_lows = []
        
        for pen in pens:
            if pen['direction'] == 'up':
                all_lows.append(pen['start_price'])
                all_highs.append(pen['end_price'])
            else:
                all_highs.append(pen['start_price'])
                all_lows.append(pen['end_price'])
        
        # 计算整体的最高高点和最低低点
        max_high = max(all_highs)
        min_low = min(all_lows)
        
        # 检查是否有重叠（至少三笔中任意两笔有重叠）
        for i in range(len(pens)):
            for j in range(i+1, len(pens)):
                pen_i_high = pens[i]['end_price'] if pens[i]['direction'] == 'up' else pens[i]['start_price']
                pen_i_low = pens[i]['start_price'] if pens[i]['direction'] == 'up' else pens[i]['end_price']
                
                pen_j_high = pens[j]['end_price'] if pens[j]['direction'] == 'up' else pens[j]['start_price']
                pen_j_low = pens[j]['start_price'] if pens[j]['direction'] == 'up' else pens[j]['end_price']
                
                # 检查两笔是否有重叠
                if not (pen_i_high < pen_j_low or pen_i_low > pen_j_high):
                    return True
        
        return False
    
    def _is_segment_break(self, segment, new_pen):
        """
        检查新笔是否破坏了原线段
        
        参数:
        segment: 当前线段
        new_pen: 新的笔
        
        返回:
        是否破坏原线段
        """
        # 线段破坏的条件：新笔的方向与线段方向相反，且突破线段的高点或低点
        if new_pen['direction'] == segment['direction']:
            return False
        
        # 检查是否突破线段的极值点
        if segment['direction'] == 'up':
            # 向上线段被向下笔破坏的条件：向下笔的低点低于线段中某一笔的低点
            for pen in segment['pens']:
                # 由于我们的笔数据中没有存储high和low，这里使用价格范围估计
                pen_low = min(pen['start_price'], pen['end_price'])
                if new_pen['end_price'] < pen_low:
                    return True
        else:
            # 向下线段被向上笔破坏的条件：向上笔的高点高于线段中某一笔的高点
            for pen in segment['pens']:
                pen_high = max(pen['start_price'], pen['end_price'])
                if new_pen['end_price'] > pen_high:
                    return True
        
        return False
    
    def calculate_macd(self, df, fast_period=12, slow_period=26, signal_period=9):
        """
        计算MACD指标
        
        参数:
        df: 包含收盘价数据的DataFrame
        fast_period: 快速移动平均线周期，默认为12
        slow_period: 慢速移动平均线周期，默认为26
        signal_period: 信号线周期，默认为9
        
        返回:
        包含MACD指标的DataFrame
        """
        # 计算EMA12和EMA26
        df['ema12'] = df['close'].ewm(span=fast_period, adjust=False).mean()
        df['ema26'] = df['close'].ewm(span=slow_period, adjust=False).mean()
        
        # 计算DIF
        df['dif'] = df['ema12'] - df['ema26']
        
        # 计算DEA（信号线）
        df['dea'] = df['dif'].ewm(span=signal_period, adjust=False).mean()
        
        # 计算MACD柱状图
        df['macd'] = (df['dif'] - df['dea']) * 2
        
        return df
    
    def calculate_kdj(self, df, n=9, m1=3, m2=3):
        """
        计算KDJ指标
        
        参数:
        df: 包含最高价、最低价和收盘价数据的DataFrame
        n: RSV计算周期，默认为9
        m1: K线计算周期，默认为3
        m2: D线计算周期，默认为3
        
        返回:
        包含KDJ指标的DataFrame
        """
        # 计算n日内最高价
        df['highest'] = df['high'].rolling(window=n).max()
        
        # 计算n日内最低价
        df['lowest'] = df['low'].rolling(window=n).min()
        
        # 计算RSV值
        df['rsv'] = (df['close'] - df['lowest']) / (df['highest'] - df['lowest']) * 100
        
        # 计算K线
        df['k'] = df['rsv'].ewm(com=m1-1, adjust=False).mean()
        
        # 计算D线
        df['d'] = df['k'].ewm(com=m2-1, adjust=False).mean()
        
        # 计算J线
        df['j'] = 3 * df['k'] - 2 * df['d']
        
        return df
    
    def identify_centrals(self, min_pens=3):
        """
        识别中枢
        
        参数:
        min_pens: 形成中枢所需的最少笔数量，默认为3
        
        返回:
        中枢的列表
        """
        if len(self.pens) < min_pens:
            logger.warning(f"笔的数量不足，无法识别中枢（至少需要{min_pens}笔）")
            return []
        
        self.centrals = []
        
        # 遍历所有可能的笔组合来寻找中枢
        for i in range(len(self.pens) - min_pens + 1):
            # 获取当前的笔组合
            pen_group = self.pens[i:i+min_pens]
            
            # 检查是否满足中枢条件：有重叠区域且方向交替
            if self._is_central(pen_group):
                # 计算中枢的价格范围
                high_prices = []
                low_prices = []
                
                for pen in pen_group:
                    high_prices.append(max(pen['start_price'], pen['end_price']))
                    low_prices.append(min(pen['start_price'], pen['end_price']))
                
                central_high = min(high_prices)  # 中枢的上沿是各组笔高点的最小值
                central_low = max(low_prices)    # 中枢的下沿是各组笔低点的最大值
                central_mid = (central_high + central_low) / 2
                
                # 确定中枢类型
                # 根据笔的方向序列判断是上涨中枢还是下跌中枢
                directions = [pen['direction'] for pen in pen_group]
                if directions[0] == 'up' and directions[1] == 'down' and directions[2] == 'up':
                    central_type = 'up'  # 上涨中枢
                elif directions[0] == 'down' and directions[1] == 'up' and directions[2] == 'down':
                    central_type = 'down'  # 下跌中枢
                else:
                    central_type = 'neutral'  # 中性中枢
                
                # 创建中枢
                central = {
                    'start_index': pen_group[0]['start_index'],
                    'start_datetime': pen_group[0]['start_datetime'],
                    'end_index': pen_group[-1]['end_index'],
                    'end_datetime': pen_group[-1]['end_datetime'],
                    'high': central_high,
                    'low': central_low,
                    'mid': central_mid,
                    'type': central_type,
                    'pens': pen_group.copy(),
                    'range': central_high - central_low
                }
                
                # 检查是否与已存在的中枢重叠，如果重叠则合并
                merged = False
                for existing_central in self.centrals:
                    if self._centrals_overlap(existing_central, central):
                        # 合并中枢
                        existing_central['high'] = max(existing_central['high'], central['high'])
                        existing_central['low'] = min(existing_central['low'], central['low'])
                        existing_central['mid'] = (existing_central['high'] + existing_central['low']) / 2
                        existing_central['end_index'] = max(existing_central['end_index'], central['end_index'])
                        existing_central['end_datetime'] = max(existing_central['end_datetime'], central['end_datetime'])
                        existing_central['pens'].extend(central['pens'])
                        merged = True
                        break
                
                if not merged:
                    self.centrals.append(central)
        
        logger.info(f"成功识别 {len(self.centrals)} 个中枢")
        return self.centrals
    
    def _is_central(self, pen_group):
        """
        检查一组笔是否形成中枢
        
        参数:
        pen_group: 笔的列表
        
        返回:
        是否形成中枢
        """
        if len(pen_group) < 3:
            return False
        
        # 检查是否有重叠区域
        if not self._has_overlap(pen_group):
            return False
        
        # 检查笔的方向是否符合中枢的基本结构
        directions = [pen['direction'] for pen in pen_group]
        
        if len(pen_group) == 3:
            # 三笔中枢的基本结构：上-下-上 或 下-上-下
            if (directions[0] == 'up' and directions[1] == 'down' and directions[2] == 'up') or \
               (directions[0] == 'down' and directions[1] == 'up' and directions[2] == 'down'):
                return True
        else:
            # 对于更多笔的中枢，检查是否包含基本的三笔中枢结构
            # 遍历所有可能的三笔组合，检查是否存在基本的中枢结构
            for i in range(len(pen_group) - 2):
                sub_directions = directions[i:i+3]
                if (sub_directions[0] == 'up' and sub_directions[1] == 'down' and sub_directions[2] == 'up') or \
                   (sub_directions[0] == 'down' and sub_directions[1] == 'up' and sub_directions[2] == 'down'):
                    return True
        
        # 默认返回False
        return False
    
    def _centrals_overlap(self, central1, central2):
        """
        检查两个中枢是否重叠
        
        参数:
        central1: 第一个中枢
        central2: 第二个中枢
        
        返回:
        是否重叠
        """
        # 检查价格范围是否重叠
        price_overlap = not (central1['high'] < central2['low'] or central1['low'] > central2['high'])
        
        # 检查时间范围是否连续或重叠
        time_overlap = not (central1['end_index'] < central2['start_index'] - 5 or \
                           central1['start_index'] > central2['end_index'] + 5)
        
        return price_overlap and time_overlap

def main(stock_code="sh600000", use_mock_data=False, save_chart=None):
    """
    主程序入口，执行完整的缠论分析流程
    
    参数:
    stock_code: 股票代码，默认为浦发银行(sh600000)
    use_mock_data: 是否使用模拟数据，默认为False
    save_chart: 保存图表的路径，默认为None（不保存）
    """
    # 解析命令行参数
    parser = argparse.ArgumentParser(description='缠论自动分析系统')
    parser.add_argument('-c', '--code', type=str, default=stock_code, 
                        help='股票代码，支持格式：sh600000（浦发银行）、sz000001（平安银行）、hk09988（阿里巴巴）等')
    parser.add_argument('-m', '--mock', action='store_true', default=use_mock_data, help='使用模拟数据')
    parser.add_argument('-s', '--save', type=str, default=save_chart, help='保存图表的路径')
    parser.add_argument('-i', '--interactive', action='store_true', help='交互式输入股票代码')
    parser.add_argument('-p', '--period', type=str, default='1min', 
                        choices=['1min', '5min', '15min', '30min', '60min', '1d', '1w', '1M'],
                        help='K线周期，支持：1min（1分钟）、5min（5分钟）、15min（15分钟）、30min（30分钟）、60min（60分钟）、1d（日线）、1w（周线）、1M（月线）')
    
    # 打印调试信息
    logger.debug(f"[调试] 原始命令行参数: {sys.argv}")
    
    args = parser.parse_args()
    
    # 打印解析后的参数
    logger.debug(f"[调试] 解析后的参数: code={args.code}, mock={args.mock}, save={args.save}, interactive={args.interactive}, period={args.period}")
    
    # 交互式输入股票代码
    if args.interactive:
        print("\n===== 缠论自动分析系统 =====")
        print("支持的股票代码格式：")
        print("  上海证券交易所：sh600000 或 600000")
        print("  深圳证券交易所：sz000001 或 000001")
        print("  香港证券交易所：hk09988 或 09988")
        print("请输入股票代码，或按Enter键使用默认代码(sh600000)：")
        
        try:
            # 使用sys.stdin.readline()替代input()，提高兼容性
            stock_code_input = sys.stdin.readline().strip()
            logger.debug(f"[调试] 读取到的股票代码输入: '{stock_code_input}'")
            
            if stock_code_input:
                stock_code = stock_code_input
            else:
                print("使用默认股票代码: sh600000")
                stock_code = "sh600000"
            
            use_mock_data = False
            save_chart = None
        except Exception as e:
            logger.error(f"[错误] 读取股票代码时出错: {str(e)}")
            print("使用默认股票代码: sh600000")
            stock_code = "sh600000"
            use_mock_data = False
            save_chart = None
    else:
        stock_code = args.code
        use_mock_data = args.mock
        save_chart = args.save
    
    # 股票代码验证和格式化
    if stock_code:
        # 支持多种股票代码格式，自动转换为标准格式
        original_code = stock_code
        stock_code = stock_code.strip().lower()
        # 移除可能的前缀
        stock_code = stock_code.replace('sh.', 'sh')
        stock_code = stock_code.replace('sz.', 'sz')
        stock_code = stock_code.replace('hk.', 'hk')
        stock_code = stock_code.replace('.hk', 'hk')
        
        # 添加缺少的前缀
        if stock_code.isdigit():
            if len(stock_code) == 6:
                # 上海或深圳证券交易所股票代码（6位数字）
                if stock_code.startswith('6'):
                    stock_code = f"sh{stock_code}"
                else:
                    stock_code = f"sz{stock_code}"
            elif len(stock_code) in [4, 5]:
                # 香港证券交易所股票代码（4-5位数字）
                stock_code = f"hk{stock_code}"
            else:
                logger.warning(f"警告：股票代码{stock_code}格式不正确，将使用默认股票代码")
                stock_code = "sh600000"
        elif not (stock_code.startswith('sh') or stock_code.startswith('sz') or stock_code.startswith('hk')):
            logger.warning(f"警告：股票代码{stock_code}格式不正确，将使用默认股票代码")
            stock_code = "sh600000"
        
        # 输出处理后的股票代码
        if original_code != stock_code:
            print(f"已将股票代码 '{original_code}' 转换为标准格式: {stock_code}")
    
    print("===== 缠论自动分析系统 =====")
    print(f"股票代码: {stock_code}")
    print(f"K线周期: {args.period}")
    print(f"使用模拟数据: {use_mock_data}")
    print("="*40)
    
    try:
        # 1. 创建股票数据获取器并获取数据
        fetcher = StockDataFetcher()
        
        print(f"\n[步骤1] 正在获取股票数据...")
        if use_mock_data:
            df = fetcher._generate_mock_data(stock_code)
            print(f"已生成模拟数据，共 {len(df)} 条记录")
        else:
            df = fetcher.fetch_kline_data(stock_code, args.period)
        
        print("数据示例:")
        print(df.head())
        
        # 2. 创建缠论分析器
        analyzer = ChanlunAnalyzer()
        
        # 3. 识别分型
        print(f"\n[步骤2] 正在识别分型...")
        analyzer.identify_fractals(df)
        filtered_fractals = analyzer.filter_fractals(df)
        
        print(f"识别到 {len([f for f in filtered_fractals if f[3] == 'top'])} 个顶分型，{len([f for f in filtered_fractals if f[3] == 'bottom'])} 个底分型")
        
        # 4. 划分笔
        print(f"\n[步骤3] 正在划分笔...")
        analyzer.divide_pens(df, filtered_fractals)
        valid_pens = analyzer.validate_pens()
        
        print(f"成功划分 {len(valid_pens)} 支笔")
        
        # 5. 划分线段
        print(f"\n[步骤4] 正在划分线段...")
        segments = analyzer.divide_segments()
        
        print(f"划分得到 {len(segments)} 条线段")
        
        # 6. 识别中枢
        print(f"\n[步骤5] 正在识别中枢...")
        centrals = analyzer.identify_centrals()
        
        # 7. 可视化分析结果
        print(f"\n[步骤6] 正在可视化分析结果...")
        analyzer.visualize_all(df, show_figure=True, save_path=save_chart)
        
        print(f"\n===== 缠论分析完成 =====")
        
    except KeyboardInterrupt:
        print("\n程序已被用户中断")
    except ValueError as e:
        logger.error(f"\n数据处理错误: {str(e)}")
        print(f"\n数据处理错误: {str(e)}")
    except Exception as e:
        logger.error(f"\n发生未知错误: {str(e)}")
        print(f"\n发生未知错误: {str(e)}")
        import traceback
        traceback.print_exc()

# 主程序入口
if __name__ == "__main__":
    # 直接调用main函数，使用命令行参数
    main()