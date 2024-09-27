from datetime import datetime
from typing import Tuple, Any

from vnpy.event import EventEngine
from vnpy.trader.constant import Exchange, Direction
from vnpy.trader.gateway import BaseGateway
from vnpy.trader.object import CancelRequest, OrderRequest, SubscribeRequest, OrderData
from src.tools.property import Property
from longport.openapi import TradeContext, Config, OrderType, OrderSide, TimeInForceType, QuoteContext


class LongPortGateway(BaseGateway):
    default_name: str = ''
    default_setting: dict = {}

    def __init__(self, event_engine: EventEngine, gateway_name: str):
        super().__init__(event_engine, gateway_name)
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
        detail_resp = self.trade_ctx.order_detail(
            order_id=resp.order_id,
        )
        data = OrderData(
            symbol=req.symbol,
            exchange=req.exchange,
            gateway_name=self.gateway_name,
            orderid=resp.order_id,
            type=req.type,
            direction=req.direction,
            offset=req.offset,
            price=req.price,
            volume=detail_resp.quantity,
            traded=detail_resp.executed_quantity,
            status=detail_resp.status,
            datetime=detail_resp.submitted_at,
        )
        return data

    def cancel_order(self, req: CancelRequest) -> None:
        pass

    def query_account(self) -> None:
        pass

    def query_position(self) -> None:
        pass


if __name__ == '__main__':
    setting = {
        'LONGPORT_APP_KEY': Property.get_property("LONGPORT_APP_KEY"),
        'LONGPORT_APP_SECRET': Property.get_property("LONGPORT_APP_SECRET"),
        'LONGPORT_ACCESS_TOKEN': Property.get_property("LONGPORT_ACCESS_TOKEN"),
    }
    a = LongPortGateway(EventEngine(), 'longport')
    a.connect(setting)
    o = OrderRequest(symbol='700', exchange=Exchange.HK, direction=Direction.LONG, type=OrderType.LO, volume=100, offset=OrderSide.Buy, price=100)
    print(a.send_order(o))