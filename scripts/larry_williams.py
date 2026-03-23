from DWX_ZeroMQ_Connector_v2_0_1_RC8 import DWX_ZeroMQ_Connector  # 确保此文件在同一目录
import pandas as pd
import time

class larry_williams(object):
    def __init__(self,zmq): 
        _zmq._DWX_MTX_SEND_TRACKRATES_REQUEST_(self._instruments)
        
    def calculate_atr(df, period=14):
        """计算真实波幅 ATR"""
        df = df.copy()
        df['H-L'] = df['最高价'] - df['最低价']
        df['H-PC'] = abs(df['最高价'] - df['收盘价'].shift(1))
        df['L-PC'] = abs(df['最低价'] - df['收盘价'].shift(1))
        df['TR'] = df[['H-L', 'H-PC', 'L-PC']].max(axis=1)
        df['ATR'] = df['TR'].rolling(window=period).mean()
        return df['ATR'].iloc[-1]

    def larry_williams_comex(data,symbol, k=0.6, atr_period=14):
        print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] 正在获取 COMEX {symbol} 数据...")
        try:
            # 1. 获取外盘历史日线数据 (计算昨日振幅和 ATR)
            # 新浪外盘历史接口返回的列名通常为：日期、开盘价、最高价、最低价、收盘价等
            daily_df = data['yesterday']
            if daily_df.empty:
                return "获取历史数据失败，请检查 COMEX 合约代码。"
            
            current_atr = calculate_atr(daily_df, period=atr_period)
        
            # 获取昨日数据 (倒数第二条是完整的昨日数据)
            yesterday_data = daily_df.iloc[-2]
            yesterday_range = yesterday_data['最高价'] - yesterday_data['最低价']
        
            # 2. 获取今日实时盘口数据
            # 使用新浪全球商品实时行情接口
            spot_df = data['today']
            if spot_df.empty:
                return f"无法获取 {symbol} 的实时盘口数据。"
            
            today_open = float(spot_data['开盘价'].iloc[0])
            current_price = float(spot_data['最新价'].iloc[0])
        
            # 3. 计算核心点位
            buy_line = today_open + (yesterday_range * k)
            sell_line = today_open - (yesterday_range * k) 
        
            # 4. 风险控制参数 (计算具体点位)
            stop_loss_long = buy_line - (1.5 * current_atr)
            take_profit_long = buy_line + (2.0 * current_atr)

            # 5. 计算单手合约的美元风险金额
            # 1 手 COMEX 黄金为 100 盎司，若是白银 SI 通常为 5000 盎司
            lot_size = 100 if symbol == "XAUUSD" else 5000 
            risk_per_lot_long_usd = (buy_line - stop_loss_long) * lot_size
            profit_per_lot_long_usd = (take_profit_long - buy_line) * lot_size

            # 6. 打印实时监控面板
            print("-" * 50)
            print(f"📊 【COMEX {symbol}】Larry Williams 监控面板")
            print(f"昨日振幅: {yesterday_range:.2f} | 当前 ATR: {current_atr:.2f}")
            print(f"今日开盘: {today_open:.2f} | 当前价格: {current_price:.2f}")
            print("-" * 50)
            print(f"🟢 做多突破线: {buy_line:.2f}")
            print(f"   └─ 建议止损位: {stop_loss_long:.2f} (-1.5 ATR)")
            print(f"   └─ 建议止盈位: {take_profit_long:.2f} (+2.0 ATR)")
            print(f"   💰 单手做多风险: -${risk_per_lot_long_usd:.2f} | 预期利润: +${profit_per_lot_long_usd:.2f}")
            print("-" * 50)
            print(f"🔴 做空突破线: {sell_line:.2f}")
            print("-" * 50)

            # 7. 信号判定
            if current_price >= buy_line:
                return f"🔥 【触发买入】当前价格 {current_price} 已向上突破做多线 {buy_line:.2f}！"
            elif current_price <= sell_line:
                return f"📉 【触发做空】当前价格 {current_price} 已向下突破做空线 {sell_line:.2f}！"
            else:
                return f"💤 盘整中，未突破。距离上方突破还有 {buy_line - current_price:.2f} 个点。"

        except Exception as e:
            return f"运行出错: {e}"