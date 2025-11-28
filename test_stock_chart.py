import pytest
import pandas as pd
import numpy as np
from unittest.mock import patch, MagicMock
import datetime
import sys
import os

# 添加源文件路径到sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# 导入被测模块
import stock_chart

class TestGetMinuteData:
    """测试 get_minute_data 方法"""
    
    def test_get_minute_data_sh_stock_success(self):
        """测试上证股票代码成功获取数据"""
        # 模拟 yf.download 返回有效数据
        mock_df = pd.DataFrame({
            'Open': [10.0, 10.1],
            'High': [10.2, 10.3],
            'Low': [9.8, 9.9],
            'Close': [10.1, 10.2],
            'Volume': [1000, 2000]
        })
        
        with patch('yfinance.download') as mock_download, \
             patch('stock_chart.generate_simulation_data') as mock_generate:
            
            mock_download.return_value = mock_df
            mock_generate.return_value = mock_df
            
            # 调用被测方法
            result = stock_chart.get_minute_data('600000', 1)
            
            # 验证结果
            assert isinstance(result, pd.DataFrame)
            assert len(result) > 0
            mock_download.assert_called_once()
            mock_generate.assert_not_called()  # 不应该调用模拟数据生成
    
    def test_get_minute_data_sz_stock_success(self):
        """测试深证股票代码成功获取数据"""
        # 模拟 yf.download 返回有效数据
        mock_df = pd.DataFrame({
            'open': [20.0, 20.1],
            'high': [20.2, 20.3],
            'low': [19.8, 19.9],
            'close': [20.1, 20.2],
            'volume': [3000, 4000]
        })
        
        with patch('yfinance.download') as mock_download, \
             patch('stock_chart.generate_simulation_data') as mock_generate:
            
            mock_download.return_value = mock_df
            mock_generate.return_value = mock_df
            
            # 调用被测方法
            result = stock_chart.get_minute_data('000001', 2)
            
            # 验证结果
            assert isinstance(result, pd.DataFrame)
            assert len(result) > 0
            mock_download.assert_called_once()
            mock_generate.assert_not_called()
    
    def test_get_minute_data_empty_data_fallback(self):
        """测试空数据时回退到模拟数据"""
        # 模拟 yf.download 返回空DataFrame
        empty_df = pd.DataFrame()
        
        with patch('yfinance.download') as mock_download, \
             patch('stock_chart.generate_simulation_data') as mock_generate:
            
            mock_download.return_value = empty_df
            mock_generate.return_value = pd.DataFrame({
                'open': [10.0], 'high': [10.1], 'low': [9.9], 'close': [10.0], 'volume': [1000]
            })
            
            # 调用被测方法
            result = stock_chart.get_minute_data('600000', 1)
            
            # 验证结果
            assert isinstance(result, pd.DataFrame)
            mock_download.assert_called_once()
            mock_generate.assert_called_once_with('600000', 1)
    
    def test_get_minute_data_download_exception_fallback(self):
        """测试下载异常时回退到模拟数据"""
        with patch('yfinance.download') as mock_download, \
             patch('stock_chart.generate_simulation_data') as mock_generate:
            
            mock_download.side_effect = Exception("Network error")
            mock_generate.return_value = pd.DataFrame({
                'open': [10.0], 'high': [10.1], 'low': [9.9], 'close': [10.0], 'volume': [1000]
            })
            
            # 调用被测方法
            result = stock_chart.get_minute_data('600000', 1)
            
            # 验证结果
            assert isinstance(result, pd.DataFrame)
            mock_download.assert_called_once()
            mock_generate.assert_called_once_with('600000', 1)
    
    def test_get_minute_data_general_exception_fallback(self):
        """测试通用异常时回退到模拟数据"""
        with patch('yfinance.download') as mock_download, \
             patch('stock_chart.generate_simulation_data') as mock_generate:
            
            # 模拟外层try块中的异常
            def mock_download_side_effect(*args, **kwargs):
                raise ValueError("Unexpected error")
            
            mock_download.side_effect = mock_download_side_effect
            mock_generate.return_value = pd.DataFrame({
                'open': [10.0], 'high': [10.1], 'low': [9.9], 'close': [10.0], 'volume': [1000]
            })
            
            # 调用被测方法
            result = stock_chart.get_minute_data('600000', 1)
            
            # 验证结果
            assert isinstance(result, pd.DataFrame)
            mock_generate.assert_called_once_with('600000', 1)
    
    def test_get_minute_data_symbol_format_conversion(self):
        """测试股票代码格式转换逻辑"""
        with patch('yfinance.download') as mock_download, \
             patch('stock_chart.generate_simulation_data') as mock_generate:
            
            mock_download.return_value = pd.DataFrame()
            mock_generate.return_value = pd.DataFrame({
                'open': [10.0], 'high': [10.1], 'low': [9.9], 'close': [10.0], 'volume': [1000]
            })
            
            # 测试上证股票代码格式转换
            stock_chart.get_minute_data('600000', 1)
            call_args = mock_download.call_args[0][0]
            assert call_args == '600000.SS'
            
            # 测试深证股票代码格式转换
            stock_chart.get_minute_data('000001', 1)
            call_args = mock_download.call_args[0][0]
            assert call_args == '000001.SZ'
            
            # 测试创业板股票代码格式转换
            stock_chart.get_minute_data('300001', 1)
            call_args = mock_download.call_args[0][0]
            assert call_args == '300001.SZ'
    
    def test_get_minute_data_days_parameter(self):
        """测试days参数的不同取值"""
        with patch('yfinance.download') as mock_download, \
             patch('stock_chart.generate_simulation_data') as mock_generate:
            
            mock_download.return_value = pd.DataFrame()
            mock_generate.return_value = pd.DataFrame({
                'open': [10.0], 'high': [10.1], 'low': [9.9], 'close': [10.0], 'volume': [1000]
            })
            
            # 测试默认days值
            stock_chart.get_minute_data('600000')
            call_kwargs = mock_download.call_args[1]
            start_time = call_kwargs['start']
            end_time = call_kwargs['end']
            time_delta = end_time - start_time
            assert time_delta.days == 1
            
            # 测试自定义days值
            stock_chart.get_minute_data('600000', 5)
            call_kwargs = mock_download.call_args[1]
            start_time = call_kwargs['start']
            end_time = call_kwargs['end']
            time_delta = end_time - start_time
            assert time_delta.days == 5
    
    def test_get_minute_data_edge_cases(self):
        """测试边界情况"""
        with patch('yfinance.download') as mock_download, \
             patch('stock_chart.generate_simulation_data') as mock_generate:
            
            mock_download.return_value = pd.DataFrame()
            mock_generate.return_value = pd.DataFrame({
                'open': [10.0], 'high': [10.1], 'low': [9.9], 'close': [10.0], 'volume': [1000]
            })
            
            # 测试days=0（边界值）
            result = stock_chart.get_minute_data('600000', 0)
            assert isinstance(result, pd.DataFrame)
            
            # 测试days为浮点数
            result = stock_chart.get_minute_data('600000', 0.5)
            assert isinstance(result, pd.DataFrame)
            
            # 测试空股票代码
            result = stock_chart.get_minute_data('', 1)
            assert isinstance(result, pd.DataFrame)
    
    def test_get_minute_data_output_structure(self):
        """测试输出数据结构"""
        with patch('yfinance.download') as mock_download, \
             patch('stock_chart.generate_simulation_data') as mock_generate:
            
            # 模拟返回标准结构的数据
            mock_data = pd.DataFrame({
                'open': [10.0, 10.1, 10.2],
                'high': [10.2, 10.3, 10.4],
                'low': [9.8, 9.9, 10.0],
                'close': [10.1, 10.2, 10.3],
                'volume': [1000, 2000, 3000]
            }, index=pd.date_range('2023-01-01', periods=3, freq='1min'))
            
            mock_download.return_value = mock_data
            mock_generate.return_value = mock_data
            
            result = stock_chart.get_minute_data('600000', 1)
            
            # 验证数据结构
            assert isinstance(result, pd.DataFrame)
            assert not result.empty
            assert all(col in result.columns for col in ['open', 'high', 'low', 'close', 'volume'])
            assert isinstance(result.index, pd.DatetimeIndex)
    
    def test_get_minute_data_yfinance_call_parameters(self):
        """测试yfinance调用参数"""
        with patch('yfinance.download') as mock_download, \
             patch('stock_chart.generate_simulation_data') as mock_generate:
            
            mock_download.return_value = pd.DataFrame()
            mock_generate.return_value = pd.DataFrame({
                'open': [10.0], 'high': [10.1], 'low': [9.9], 'close': [10.0], 'volume': [1000]
            })
            
            stock_chart.get_minute_data('600000', 2)
            
            # 验证yfinance调用参数
            mock_download.assert_called_once()
            call_args = mock_download.call_args
            
            # 验证位置参数
            assert call_args[0][0] == '600000.SS'
            
            # 验证关键字参数
            assert 'start' in call_args[1]
            assert 'end' in call_args[1]
            assert call_args[1]['interval'] == '1d'
            assert call_args[1]['auto_adjust'] is True

if __name__ == "__main__":
    pytest.main([__file__, "-v"])