from DWX_ZeroMQ_Connector_v2_0_1_RC8 import DWX_ZeroMQ_Connector
import pandas as pd
import time 
from time import sleep
from datetime import datetime, timedelta
import pandas_market_calendars as mcal
from dateutil.relativedelta import relativedelta
import pytz

# 适配pandas-market-calendars的合法交易所名称
EXCHANGE_CALENDARS = {
    "CME": "CME_TradeDate",          # CME通用交易日历（兼容性最好）
    "EUREX": "EUREX",
    "ICE": "ICE",
    "NYMEX": "CMEGlobex_Energy",
    "CBOT": "CMEGlobex_Grains"
}

# 交易所时区映射（避免从日历获取时区出错）
EXCHANGE_TIMEZONES = {
    "CME": "America/Chicago",
    "EUREX": "Europe/Berlin",
    "ICE": "Europe/London",
    "NYMEX": "America/Chicago",
    "CBOT": "America/Chicago"
}

class larry_williams(object):
    def __init__(self, zmq, instruments):
        self._current_atr={}
        self._today_open={}
        self._yesterday_range={}
        try:
            prev_trading_day = self.get_prev_trading_day_for_forex_futures().strftime("%Y.%m.%d %H:%M:%S")
            today_time = datetime.now().date()
            for symbol, display_name, multiplier in instruments:
                zmq._History_DB.clear()
                zmq._DWX_MTX_SEND_HIST_REQUEST_(_symbol=symbol,_timeframe=1440,_start=prev_trading_day)
                sleep(1)
                for histdata in zmq._History_DB[symbol+'_D1']:
                    if datetime.strptime(histdata['time'], '%Y.%m.%d %H:%M').date() == today_time:
                        self._today_open[symbol]=histdata['open']
                    else:
                        df=self.calculate_atr(histdata).iloc[-1]
                        print(df)
                        self._current_atr[symbol]=df['ATR']
                        self._yesterday_range[symbol]=df['H-L']
                                             
        except Exception as e:
            print(f"初始化报错：{e}")
    
    def calculate_atr(self, df, period=1):
        """计算真实波幅 ATR"""
        df = pd.DataFrame([df])
        df['H-L'] = df['high'] - df['low']
        df['H-PC'] = abs(df['high'] - df['close'])
        df['L-PC'] = abs(df['low'] - df['close'])
        df['TR'] = df[['H-L', 'H-PC', 'L-PC']].max(axis=1)
        df['ATR'] = float(df['TR'].rolling(window=period).mean().iloc[-1].round(2))
        return df

    def larry_williams_comex(self,symbol, data, k=0.6, atr_period=1):
        try:
            current_atr = self._current_atr[symbol]
            today_open = self._today_open[symbol]
            current_price = data['open']
            yesterday_range = self._yesterday_range[symbol]

            buy_line = today_open + (yesterday_range * k)
            sell_line = today_open - (yesterday_range * k) 
        
            stop_loss_long = buy_line - (1.5 * current_atr)
            take_profit_long = buy_line + (2.0 * current_atr)

            lot_size = 100 if symbol == "XAUUSD" else 5000 
            risk_per_lot_long_usd = (buy_line - stop_loss_long) * lot_size
            profit_per_lot_long_usd = (take_profit_long - buy_line) * lot_size

            print("-" * 50)
            print(f"📊 【COMEX {symbol}】Larry Williams 监控面板")
            print(f"昨日振幅: {yesterday_range} | 当前 ATR: {current_atr}")
            print(f"今日开盘: {today_open} | 当前价格: {current_price}")
            print("-" * 50)
            print(f"🟢 做多突破线: {buy_line:.2f}")
            print(f"   └─ 建议止损位: {stop_loss_long:.2f} (-1.5 ATR)")
            print(f"   └─ 建议止盈位: {take_profit_long:.2f} (+2.0 ATR)")
            print(f"   💰 单手做多风险: -${risk_per_lot_long_usd:.2f} | 预期利润: +${profit_per_lot_long_usd:.2f}")
            print("-" * 50)
            print(f"🔴 做空突破线: {sell_line:.2f}")
            print("-" * 50)

            if current_price >= buy_line:
                return f"🔥 【触发买入】当前价格 {current_price} 已向上突破做多线 {buy_line:.2f}！"
            elif current_price <= sell_line:
                return f"📉 【触发做空】当前价格 {current_price} 已向下突破做空线 {sell_line:.2f}！"
            else:
                return f"💤 盘整中，未突破。距离上方突破还有 {buy_line - current_price:.2f} 个点。"

        except Exception as e:
            return f"运行出错:"

    def get_exchange_trading_dates(self, exchange: str = "CME", start_date: datetime = None, end_date: datetime = None):
        """获取交易所有效交易日（纯日期，无时区，避免冲突）"""
        # 1. 初始化日历（容错）
        try:
            cal_name = EXCHANGE_CALENDARS[exchange.upper()]
            cal = mcal.get_calendar(cal_name)
        except (KeyError, RuntimeError):
            cal = mcal.get_calendar("CME_TradeDate")
    
        # 2. 设置默认时间范围（转为纯日期，剥离时区）
        if start_date is None:
            start_date = datetime.now(pytz.UTC).date() - relativedelta(days=30)
        else:
            start_date = start_date.date() if hasattr(start_date, 'date') else start_date
        
        if end_date is None:
            end_date = datetime.now(pytz.UTC).date()
        else:
            end_date = end_date.date() if hasattr(end_date, 'date') else end_date
    
        # 3. 获取纯日期的有效交易日（关键：避免Timestamp时区问题）
        valid_days = cal.valid_days(start_date=start_date, end_date=end_date)
        # 转换为Python原生date对象（完全剥离时区）
        trading_dates = [day.date() for day in valid_days]
        return trading_dates

    def get_prev_trading_day_for_forex_futures(self,
        base_datetime: datetime = None,
        exchange: str = "CME",
        tz_local: str = "America/Chicago"
    ) -> datetime:
        """
        获取前一个交易日（纯日期计算，最后再绑定时区）
        核心：先算日期，再加时区，避免Timestamp本地化冲突
        """
        # 1. 处理基准时间（转为交易所时区的纯日期）
        tz_local_obj = pytz.timezone(tz_local)
        if base_datetime is None:
            base_datetime = datetime.now(tz_local_obj)
        else:
            if base_datetime.tzinfo is None:
                base_datetime = tz_local_obj.localize(base_datetime)
        
        # 转为交易所时区，提取纯日期
        exchange_tz_obj = pytz.timezone(EXCHANGE_TIMEZONES[exchange.upper()])
        base_exchange_dt = base_datetime.astimezone(exchange_tz_obj)
        base_exchange_date = base_exchange_dt.date()
        
        # 2. 获取交易所有效交易日列表（纯date对象）
        trading_dates = self.get_exchange_trading_dates(exchange)
        if not trading_dates:
            raise ValueError("未找到有效交易日（时间范围过小）")
        
        # 3. 找前一个交易日（纯日期比较，无时区）
        prev_candidate_date = base_exchange_date - timedelta(days=1)
        # 筛选小于等于候选日期的交易日
        valid_dates_filtered = [d for d in trading_dates if d <= prev_candidate_date]
        if not valid_dates_filtered:
            raise ValueError("未找到有效交易日（时间范围过小）")
        
        # 取最新的有效交易日（纯date）
        prev_trading_day_date = max(valid_dates_filtered)
        
        # 4. 最后绑定时区（避免Timestamp问题）
        # 步骤1：转为naive datetime（0点）
        prev_trading_day_naive = datetime.combine(prev_trading_day_date, datetime.min.time())
        # 步骤2：绑定交易所时区
        prev_trading_day_exchange = exchange_tz_obj.localize(prev_trading_day_naive, is_dst=None)
        # 步骤3：转换回本地时区
        prev_trading_day_local = prev_trading_day_exchange.astimezone(tz_local_obj)
        
        return prev_trading_day_local