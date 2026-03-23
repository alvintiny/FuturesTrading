import pandas as pd
import pandas_ta as ta
from threading import Thread, Lock
from DWX_ZeroMQ_Connector_v2_0_1_RC8 import DWX_ZeroMQ_Connector  # 确保此文件在同一目录
import json
import time
from time import sleep  # 补充缺失的sleep导入

class mt4_zscore_skill(object):
    # 修复1：统一缩进（原代码类内方法缩进混乱）
    def __init__(self): 
        self._lock = Lock()
        # 修复2：定义所有缺失的变量（symbol/_delay/_instruments/计数器/_zmq）
        self._symbol = 'XAUUSD'  # 定义默认订阅品种
        self._delay = 0.01  # 极低延迟（提速关键，可按需微调）
        self._eurusd_cnt = 0  # 初始化计数器
        self._gdaxi_cnt = 0
        self._instruments = [(self._symbol, self._symbol, 1)]  # 初始化品种列表
        
        # 修复3：将dwx改为实例变量self._zmq（原局部变量后续调用会丢失）
        self._zmq = DWX_ZeroMQ_Connector(_subdata_handlers=[self],_verbose=False,_sleep_delay=1)
        self._zmq._Market_Data_DB.clear()
        self._zmq._DWX_MTX_SUBSCRIBE_MARKETDATA_(self._symbol)
        #self._zmq._DWX_MTX_SEND_TRACKPRICES_REQUEST_([self._symbol])
        self._zmq._DWX_MTX_SEND_TRACKRATES_REQUEST_(self._instruments)

    def onSubData(self, data):
        """Callback to process new data received through the SUB port"""
        # split msg to get topic and message
        print(data)
        _topic, _msg = data.split(":|:")
        # print('Data on Topic={} with Message={}'.format(_topic, _msg))

        # check if received at least 5 prices from EURUSD to cancel its feed
        if self._eurusd_cnt >= 2:
            self._instruments = [(self._symbol, self._symbol, 1)]
            # 修复4：私有方法调用（双下划线方法需通过类内调用，或改为单下划线）
            self._subscribe_to_rate_feeds()  # 改为单下划线，避免私有方法调用问题
            self._eurusd_cnt = 0
        else: 
            self._eurusd_cnt += 1
            

    # 修复5：将双下划线__subscribe_to_rate_feeds改为单下划线（双下划线是强私有，外部调用报错）
    def _subscribe_to_rate_feeds(self):
        """Starts the subscription to the self._instruments list"""
        if len(self._instruments) > 0:
            # 修复6：批量加锁（减少锁竞争，提速）
            try:
                self._lock.acquire()
                # subscribe to all instruments' rate feeds
                self._zmq._DWX_MTX_SEND_TRACKRATES_REQUEST_(self._instruments)
                sleep(self._delay)  # 批量后单次延迟，提速

            finally:
                self._lock.release()
                sleep(self._delay)

    # 修复8：补充缺失的stop方法（原代码调用self.stop()但未定义）
    def stop(self):
        """快速取消所有订阅，无冗余延迟"""
        try:
            self._lock.acquire()
            self._zmq._DWX_MTX_UNSUBSCRIBE_MARKETDATA_(self._symbol)
            print('All subscriptions canceled')
        finally:
            self._lock.release()

if __name__ == "__main__":
    example = mt4_zscore_skill()
    # 修复9：调用修改后的单下划线方法（解决AttributeError核心问题）
    example._subscribe_to_rate_feeds()
    
    print('Waiting example termination...')
    try:
        # 修复10：主循环延迟从1秒改为0.05秒（提速），并支持Ctrl+C终止
        while True:
            sleep(0.05)
    except KeyboardInterrupt:
        example.stop()
        print('Program terminated by user')
    print('Bye!!!')