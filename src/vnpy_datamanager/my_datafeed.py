from datetime import datetime, timedelta
from typing import List, Optional, Callable

from longport.openapi import Config, QuoteContext, Period, AdjustType

from vnpy.trader.setting import SETTINGS
from vnpy.trader.constant import Exchange, Interval
from vnpy.trader.object import BarData, HistoryRequest
from vnpy.trader.datafeed import BaseDatafeed
from vnpy.trader.utility import ZoneInfo
from vnpy.trader.locale import _

EXCHANGE_VT2UDATA = {
    Exchange.SH: "SH",
    Exchange.SZ: "SZ",
    Exchange.HK: "HK"
}

CHINA_TZ = ZoneInfo("Asia/Shanghai")

to_interval: dict = {
    Interval.DAILY: Period.Day,
    Interval.MINUTE: Period.Min_1,
    Interval.HOUR: Period.Min_60,
    Interval.WEEKLY: Period.Week
}


def convert_symbol(symbol: str, exchange: Exchange) -> str:
    """将交易所代码转换为UData代码"""
    exchange_str = EXCHANGE_VT2UDATA.get(exchange)
    return f"{symbol.upper()}.{exchange_str}"


class MyDatafeed(BaseDatafeed):
    """数据服务接口"""

    def __init__(self):
        """"""
        self.quote_ctx = None
        self.inited: bool = False

    def init(self, output: Callable = print) -> bool:
        """初始化"""
        config = Config(app_key=SETTINGS['datafeed.key'],
                        app_secret=SETTINGS['datafeed.app_secret'],
                        access_token=SETTINGS['datafeed.access_token'])
        self.quote_ctx: QuoteContext = QuoteContext(config)
        self.inited = True
        return True

    def query_bar_history(self, req: HistoryRequest, output: Callable = print) -> Optional[List[BarData]]:
        if req.exchange not in EXCHANGE_VT2UDATA:
            output(f"UData数据服务获取K线数据失败：不支持的交易所{req.exchange.value}！")
            return None
        if not self.inited:
            self.init()
        time_multiplier: float
        # 只支持1d线
        if req.interval == Interval.DAILY:
            time_multiplier = 1
        elif req.interval == Interval.HOUR:
            time_multiplier = 4
        elif req.interval == Interval.MINUTE:
            time_multiplier = 4 * 60
        elif req.interval == Interval.WEEKLY:
            time_multiplier = 1 / 7

        data: List[BarData] = []
        end: datetime = req.end
        start: datetime = req.start

        # TODO 间隔计算有问题
        inter = int((end - start).days * time_multiplier)
        print('间隔k线数量', inter)
        # k线数量小于1000
        if inter <= 1000:
            return self.query_bar_data(req, inter)

        # k线数量多余1000
        # 每隔30秒最多请求60次
        previous_datatime = datetime.now()
        count: int = 0

        while True:
            if count >= 30:
                count = 0
                while datetime.now() - previous_datatime < timedelta(seconds=30):
                    continue
                previous_datatime = datetime.now()
            count += 1
            temp_data = self.query_history_bar_data(req)
            if temp_data:
                data.extend(temp_data)
                if temp_data[0].datetime.date() == temp_data[-1].datetime.date():
                    break
                req.start = temp_data[-1].datetime + timedelta(days=1)
            else:
                if req.end >= end:
                    return data
                else:
                    req.start = req.end + timedelta(days=1)
        return data

    def query_history_bar_data(self, req: HistoryRequest) -> Optional[List[BarData]]:
        symbol: str = req.symbol
        exchange: Exchange = req.exchange
        udata_symbol = convert_symbol(symbol, exchange)

        resp = self.quote_ctx.history_candlesticks_by_date(udata_symbol, to_interval[req.interval], AdjustType.NoAdjust,
                                                           req.start)
        data: List[BarData] = []

        for candle in resp:
            data.append(BarData(
                gateway_name='feedback',
                symbol=req.symbol,
                exchange=req.exchange,
                interval=req.interval,
                close_price=candle.close,
                open_price=candle.open,
                low_price=candle.low,
                high_price=candle.high,
                volume=candle.volume,
                turnover=candle.turnover,
                datetime=candle.timestamp,
            ))

        return data

    def query_bar_data(self, req: HistoryRequest, inter: int) -> Optional[List[BarData]]:
        """查询分钟K线数据"""
        symbol: str = req.symbol
        exchange: Exchange = req.exchange
        udata_symbol = convert_symbol(symbol, exchange)

        resp = self.quote_ctx.candlesticks(udata_symbol, to_interval[req.interval], inter, AdjustType.NoAdjust)

        data: List[BarData] = []

        for candle in resp:
            data.append(BarData(
                gateway_name='feedback',
                symbol=req.symbol,
                exchange=req.exchange,
                interval=req.interval,
                close_price=candle.close,
                open_price=candle.open,
                low_price=candle.low,
                high_price=candle.high,
                volume=candle.volume,
                turnover=candle.turnover,
                datetime=candle.timestamp,
            ))

        return data


datafeed: MyDatafeed = None


def get_datafeed() -> BaseDatafeed:
    """"""
    # Return datafeed object if already inited
    global datafeed
    if datafeed:
        return datafeed

    # Read datafeed related global setting
    datafeed_name: str = SETTINGS["datafeed.name"]

    if not datafeed_name:
        datafeed = BaseDatafeed()

        print(_("没有配置要使用的数据服务，请修改全局配置中的datafeed相关内容"))
    else:
        datafeed = MyDatafeed()

    return datafeed


if __name__ == '__main__':
    fd = get_datafeed()
    req = HistoryRequest('600900', Exchange.SH, datetime(2024, 10, 10), datetime(2024, 11, 8), Interval.DAILY)
    print(fd.query_bar_history(req))
