from datetime import datetime
from typing import List

from dateutil.rrule import DAILY
from vnpy_ctp.api import TdApi

from src.MySqlDataBase import MySqlDataBase
from vnpy.event import EventEngine, EVENT_TIMER
from vnpy.trader.constant import Exchange, Direction, Interval
from vnpy.trader.gateway import BaseGateway
from vnpy.trader.object import CancelRequest, OrderRequest, SubscribeRequest, OrderData, HistoryRequest, BarData
from src.tools.property import Property
from longport.openapi import TradeContext, Config, OrderType, OrderSide, TimeInForceType, QuoteContext, \
    AdjustType, Period


class LongPortGateway(BaseGateway):
    default_name: str = ''
    default_setting: dict = {
        'LONGPORT_APP_KEY': Property.get_property("LONGPORT_APP_KEY"),
        'LONGPORT_APP_SECRET': Property.get_property("LONGPORT_APP_SECRET"),
        'LONGPORT_ACCESS_TOKEN': Property.get_property("LONGPORT_ACCESS_TOKEN"),
    }

    def __init__(self, event_engine: EventEngine, gateway_name: str):
        super().__init__(event_engine, gateway_name)
        self.process_timer_event = None
        self.query_functions = None
        self.count = None
        self.trade_ctx = None
        self.quote_ctx = None

    def connect(self, setting: dict) -> None:
        # Load configuration from environment variables
        self.default_setting = setting
        config = Config(app_key=self.default_setting.get('LONGPORT_APP_KEY'),
                        app_secret=self.default_setting.get('LONGPORT_APP_SECRET'),
                        access_token=self.default_setting.get('LONGPORT_ACCESS_TOKEN'))

        # Create a context for trade APIs
        self.quote_ctx: QuoteContext = QuoteContext(config)
        self.trade_ctx: TradeContext = TradeContext(config)
        self.init_query()
        print('connect success')

    def process_timer_event(self, event) -> None:
        """定时事件处理"""
        self.count += 1
        if self.count < 2:
            return
        self.count = 0

        func = self.query_functions.pop(0)
        func()
        self.query_functions.append(func)



    def init_query(self) -> None:
        self.count: int = 0
        self.query_functions: list = [self.query_account, self.query_position]
        self.event_engine.register(EVENT_TIMER, self.process_timer_event)


    def close(self) -> None:
        del self.quote_ctx
        del self.trade_ctx

    def subscribe(self, req: SubscribeRequest) -> None:
        resp = self.quote_ctx.quote([req.vt_symbol])
        print(resp)

    def send_order(self, req: OrderRequest) -> OrderData:
        resp = self.trade_ctx.submit_order(
            req.vt_symbol,
            req.type,
            req.offset,
            req.volume,
            TimeInForceType.Day,
            submitted_price=req.price,
        )
        return resp.order_id

    def cancel_order(self, req: CancelRequest) -> None:
        self.trade_ctx.cancel_order(req.orderid)

    def query_account(self) -> float:
        resp = self.trade_ctx.account_balance()
        print('query account success')
        return resp[0].cash_infos[0].available_cash

    def query_position(self) -> None:
        resp = self.trade_ctx.stock_positions()
        print('query_position success')
        return resp

    def query_history(self, req: HistoryRequest) -> List[BarData]:
        resp = self.quote_ctx.history_candlesticks_by_date(req.vt_symbol,
                                                           req.interval,
                                                           AdjustType.NoAdjust,
                                                           req.start,
                                                           req.end
                                                           )
        bardata_list: List[BarData] = []
        interval: Interval
        if req.interval == Period.Day:
            interval = Interval.DAILY
        elif req.interval == Period.Week:
            interval = Interval.WEEKLY
        elif req.interval == Period.Min_60:
            interval = Interval.HOUR
        elif req.interval == Period.Min_1:
            interval = Interval.MINUTE

        for candle in resp:
            bardata_list.append(BarData(
                                    gateway_name=self.gateway_name,
                                    symbol=req.symbol,
                                    exchange=req.exchange,
                                    interval=interval,
                                    close_price=candle.close,
                                    open_price=candle.open,
                                    low_price=candle.low,
                                    high_price=candle.high,
                                    volume=candle.volume,
                                    turnover=candle.turnover,
                                    datetime=candle.timestamp,
                                    ))
        return bardata_list

    def query_candlesticks(self, req: HistoryRequest) -> List[BarData]:
        resp = self.quote_ctx.candlesticks(req.vt_symbol, req.interval, 1000, AdjustType.NoAdjust)
        bardata_list: List[BarData] = []
        interval: Interval
        if req.interval == Period.Day:
            interval = Interval.DAILY
        elif req.interval == Period.Week:
            interval = Interval.WEEKLY
        elif req.interval == Period.Min_60:
            interval = Interval.HOUR
        elif req.interval == Period.Min_1:
            interval = Interval.MINUTE

        for candle in resp:
            bardata_list.append(BarData(
                gateway_name=self.gateway_name,
                symbol=req.symbol,
                exchange=req.exchange,
                interval=interval,
                close_price=candle.close,
                open_price=candle.open,
                low_price=candle.low,
                high_price=candle.high,
                volume=candle.volume,
                turnover=candle.turnover,
                datetime=candle.timestamp,
            ))
        return bardata_list


class LongPortApi(TdApi):
    pass

if __name__ == '__main__':
    setting = {
        'LONGPORT_APP_KEY': Property.get_property("LONGPORT_APP_KEY"),
        'LONGPORT_APP_SECRET': Property.get_property("LONGPORT_APP_SECRET"),
        'LONGPORT_ACCESS_TOKEN': Property.get_property("LONGPORT_ACCESS_TOKEN"),
    }
    a = LongPortGateway(EventEngine(), 'longport')
    a.connect(setting)
  #  o = OrderRequest(symbol='700', exchange=Exchange.HK, direction=Direction.LONG, type=OrderType.LO, volume=100, offset=OrderSide.Buy, price=100)
    b: list[BarData] = a.query_history(HistoryRequest('700', Exchange.HK, datetime(2000,9,30), datetime(2024,9,30), Period.Day))
    db=MySqlDataBase()
    db.save_bar_data(b)
