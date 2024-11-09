import sys
import json
from datetime import datetime
from typing import Dict, List, Any
from pathlib import Path
from decimal import Decimal

from longport.openapi import Market, OrderStatus, OrderSide, Config, QuoteContext, SubType, TradeContext
from longport.openapi import OrderType as LongPortOrderType

from src.tools.property import Property
from vnpy.event import EventEngine
from vnpy.trader.constant import (
    Direction,
    Exchange,
    OrderType,
    Offset,
    Product,
    Status
)
from vnpy.trader.gateway import BaseGateway
from vnpy.trader.utility import round_to, get_folder_path, ZoneInfo
from vnpy.trader.object import (
    TickData,
    OrderData,
    TradeData,
    PositionData,
    AccountData,
    ContractData,
    OrderRequest,
    CancelRequest,
    SubscribeRequest,
)
from vnpy.trader.event import EVENT_TIMER

# 市场映射
MK_HFT2VT: Dict[str, Exchange] = {
    'HK': Exchange.HK,
    'SH': Exchange.SH,
    'SZ': Exchange.SZ
}
MK_VT2HFT: Dict[Exchange, str] = {v: k for k, v in MK_HFT2VT.items()}

# 产品类型映射
SH_PRODUCT_HFT2VT: Dict[str, Product] = {
    "ES": Product.EQUITY,
    "D": Product.BOND,
    "RWS": Product.OPTION,
    "FF": Product.FUTURES,
    "EU": Product.FUND
}
SZ_PRODUCT_HFT2VT: Dict[int, Product] = {
    1: Product.EQUITY,
    2: Product.EQUITY,
    3: Product.EQUITY,
    4: Product.EQUITY,
    5: Product.BOND,
    6: Product.BOND,
    7: Product.BOND,
    8: Product.BOND,
    9: Product.BOND,
    10: Product.BOND,
    11: Product.BOND,
    12: Product.BOND,
    13: Product.BOND,
    14: Product.ETF,
    15: Product.ETF,
    16: Product.ETF,
    17: Product.ETF,
    18: Product.ETF,
    19: Product.ETF,
    20: Product.ETF,
    21: Product.ETF,
    22: Product.ETF,
    23: Product.FUND,
    24: Product.FUND,
    25: Product.FUND,
    26: Product.FUND,
    28: Product.OPTION,
    29: Product.OPTION,
    30: Product.OPTION,
    33: Product.EQUITY,
    34: Product.BOND,
    35: Product.BOND,

}

# # 委托状态映射
# ORDERSTATUS_HFT2VT: Dict[Any, Status] = {
#     OrderStatus.NotReported: Status.SUBMITTING,
#     OrderStatus.New: Status.NOTTRADED,
#     OrderStatus.PartialFilled: Status.PARTTRADED,
#     OrderStatus.Filled: Status.ALLTRADED,
#     OrderStatus.PendingCancel: Status.SUBMITTING,
#     OrderStatus.WaitToCancel: Status.SUBMITTING,
#     OrderStatus.Canceled: Status.CANCELLED,
#     OrderStatus.Rejected: Status.REJECTED,
#     OrderStatus.Expired: Status.REJECTED,
# }
#
# # 委托类型映射
# ORDERTYPE_HFT2VT: Dict[Any, OrderType] = {
#     LongPortOrderType.ELO: OrderType.LIMIT,
#     LongPortOrderType.MO: OrderType.MARKET
# }
# ORDERTYPE_VT2HFT: Dict[OrderType, int] = {
#     v: k for k, v in ORDERTYPE_HFT2VT.items()
# }

# 交易所映射
EXCHANGE_HFT2VT: Dict[str, Exchange] = {
    "SH": Exchange.SH,
    "SZ": Exchange.SZ,
    'HK': Exchange.HK
}
EXCHANGE_VT2HFT: Dict[Exchange, str] = {
    v: k for k, v in EXCHANGE_HFT2VT.items()
}

# # 多空方向映射(只有多头， 乐)
# SIDE_HFT2VT: Dict[Any, Any] = {
#     OrderSide.Sell: (Direction.LONG, Offset.CLOSE),
#     OrderSide.Buy: (Direction.LONG, Offset.OPEN)
# }
# SIDE_VT2HFT: Dict[Any, int] = {
#     v: k for k, v in SIDE_HFT2VT.items()
# }

# 其他常量
MAX_FLOAT = sys.float_info.max  # 浮点数极限值
CHINA_TZ = ZoneInfo("Asia/Shanghai")  # 中国时区

# 合约数据全局缓存字典
symbol_contract_map: Dict[str, ContractData] = {}


class LongPortGateway(BaseGateway):
    """
    VeighNa用于对接长桥的交易接口。
    """

    default_name: str = "LongPort"

    default_setting: Dict[str, str] = {
        'LONGPORT_APP_KEY': Property.get_property('LONGPORT_APP_KEY'),
        'LONGPORT_APP_SECRET': Property.get_property('LONGPORT_APP_SECRET'),
        'LONGPORT_ACCESS_TOKEN': Property.get_property('LONGPORT_ACCESS_TOKEN'),
    }

    exchanges: List[str] = [Exchange.HK, Exchange.SZ, Exchange.SH]

    def __init__(self, event_engine: EventEngine, gateway_name: str) -> None:
        """构造函数"""
        super().__init__(event_engine, gateway_name)

        self.query_functions = None
        self.count = None
        self.td_api: "LongPortTdApi" = LongPortTdApi(self)
        self.md_api: "LongPortMdApi" = LongPortMdApi(self)

    def connect(self, setting: dict) -> None:
        """连接交易接口"""
        key: str = setting["LONGPORT_APP_KEY"]
        secret: str = setting["LONGPORT_APP_SECRET"]
        token: str = setting["LONGPORT_ACCESS_TOKEN"]

        self.td_api.connect(
            key,
            secret,
            token
        )

        self.md_api.connect(
            key,
            secret,
            token
        )

    def subscribe(self, req: SubscribeRequest) -> None:
        """订阅行情"""
        self.md_api.subscrbie(req)

    def send_order(self, req: OrderRequest) -> str:
        """委托下单"""
        return self.td_api.send_order(req)

    def cancel_order(self, req: CancelRequest) -> None:
        """委托撤单"""
        self.td_api.cancel_order(req)

    def query_account(self) -> None:
        """查询资金"""
        self.td_api.query_account()

    def query_position(self):
        """查询持仓"""
        self.td_api.query_position()

    def close(self) -> None:
        """关闭接口"""
        self.td_api.close()
        self.md_api.close()

    def write_error(self, msg: str, error: dict) -> None:
        """输出错误信息日志"""
        error_id: int = error["err_code"]
        error_msg: str = error["err_msg"]
        msg: str = f"{msg}，代码：{error_id}，信息：{error_msg}"
        self.write_log(msg)

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
        """初始化查询任务"""
        self.count: int = 0
        # 查询资金和持仓
        self.query_functions: list = [self.query_account, self.query_position]
        # 向时间事件处理队列注册定时时间处理事件
        self.event_engine.register(EVENT_TIMER, self.process_timer_event)


class LongPortMdApi:

    def __init__(self, gateway: LongPortGateway) -> None:
        """构造函数"""
        super().__init__()

        self.date = None
        self.quote_ctx = None
        self.gateway: LongPortGateway = gateway
        self.gateway_name: str = gateway.gateway_name

        self.key = gateway.default_setting["LONGPORT_APP_KEY"]
        self.secret = gateway.default_setting["LONGPORT_APP_SECRET"]
        self.access_token = gateway.default_setting['LONGPORT_ACCESS_TOKEN']

        self.connect_status: bool = False
        self.login_status: bool = False

        self.sse_inited: bool = False
        self.szse_inited: bool = False
        self.sehk_inited: bool = False

    def onDisconnected(self, reason: int) -> None:
        """服务器连接断开回报"""
        self.connect_status = False
        self.login_status = False
        self.gateway.write_log(f"行情服务器连接断开, 原因{reason}")

        self.quote_ctx: QuoteContext = QuoteContext(Config(
            app_key=self.key,
            app_secret=self.secret,
            access_token=self.access_token
        ))

    def onSubscribe(self, error) -> None:
        """订阅行情回报"""
        if error["errcode"]:
            self.gateway.write_log(
                f"订阅失败，错误码{error['errcode']}，信息{error['errstr']}"
            )

    def onMarketData(self, mk_type: Any, symbol: str, data: dict) -> None:
        """行情数据推送"""
        timestamp: str = f"{self.date} {str(data['nTime'])}"
        dt: datetime = generate_datetime(timestamp)

        tick: TickData = TickData(
            symbol=symbol,
            exchange=MK_HFT2VT[mk_type],
            datetime=dt,
            volume=data["iVolume"],
            last_price=data["uMatch"] / 10000,
            limit_up=data["uHighLimited"] / 10000,
            limit_down=data["uLowLimited"] / 10000,
            open_price=data["uOpen"] / 10000,
            high_price=data["uHigh"] / 10000,
            low_price=data["uLow"] / 10000,
            pre_close=data["uPreClose"] / 10000,
            gateway_name=self.gateway_name
        )
        contract: ContractData = symbol_contract_map[tick.symbol]

        tick.bid_price_1, tick.bid_price_2, tick.bid_price_3, tick.bid_price_4, tick.bid_price_5 = data["bid"][0:5]
        tick.ask_price_1, tick.ask_price_2, tick.ask_price_3, tick.ask_price_4, tick.ask_price_5 = data["ask"][0:5]
        tick.bid_volume_1, tick.bid_volume_2, tick.bid_volume_3, tick.bid_volume_4, tick.bid_volume_5 = data["bid_qty"][
                                                                                                        0:5]
        tick.ask_volume_1, tick.ask_volume_2, tick.ask_volume_3, tick.ask_volume_4, tick.ask_volume_5 = data["ask_qty"][
                                                                                                        0:5]

        pricetick: float = contract.pricetick
        if pricetick:
            tick.bid_price_1 = round_to(tick.bid_price_1 / 10000, pricetick)
            tick.bid_price_2 = round_to(tick.bid_price_2 / 10000, pricetick)
            tick.bid_price_3 = round_to(tick.bid_price_3 / 10000, pricetick)
            tick.bid_price_4 = round_to(tick.bid_price_4 / 10000, pricetick)
            tick.bid_price_5 = round_to(tick.bid_price_5 / 10000, pricetick)
            tick.ask_price_1 = round_to(tick.ask_price_1 / 10000, pricetick)
            tick.ask_price_2 = round_to(tick.ask_price_2 / 10000, pricetick)
            tick.ask_price_3 = round_to(tick.ask_price_3 / 10000, pricetick)
            tick.ask_price_4 = round_to(tick.ask_price_4 / 10000, pricetick)
            tick.ask_price_5 = round_to(tick.ask_price_5 / 10000, pricetick)

        tick.name = contract.name
        self.gateway.on_tick(tick)

    def connect(
            self,
            key: str,
            secret: int,
            access_token: str
    ) -> None:
        """连接服务器"""
        self.date = datetime.now().strftime("%Y%m%d")

        if not self.connect_status:
            try:
                self.quote_ctx: QuoteContext = QuoteContext(Config(
                    app_key=key,
                    app_secret=secret,
                    access_token=access_token
                ))
            except:
                self.gateway.write_log(f"行情登录失败")
            else:
            # 如果没有异常被抛出，则执行这里的代码
                self.gateway.write_log("行情服务器登录成功")
                self.connect_status = True
                self.login_status = True
        else:
            self.gateway.write_log("行情接口已登录，请勿重复操作")

    def close(self) -> None:
        """关闭连接"""
        if self.connect_status:
            del self.quote_ctx
            self.connect_status = False
            self.login_status = False

    def subscrbie(self, req: SubscribeRequest) -> None:
        """订阅行情"""
        if self.login_status:
            exchange = MK_VT2HFT.get(req.exchange, "")
            self.quote_ctx.subscribe([f'{req.symbol}.{exchange}'], [SubType.Quote])

    def query_contract(self) -> None:
        """查询合约"""
        # 0 -> SSE, SZSE
        # 1 -> SSE,
        # 2 -> SZSE
        self.subscribeBaseInfo(0)

    def onBaseInfo(self, code, data) -> None:
        """合约查询回报"""
        contract: ContractData = ContractData(
            gateway_name=self.gateway_name,
            symbol=str(code),
            exchange=Exchange.SH,
            name=data["szStkNameZN"].split(" ")[0],
            product=SH_PRODUCT_HFT2VT.get(
                data["szStkClass"].split(" ")[0], Product.EQUITY
            ),
            min_volume=data["i64BuyNumUnit"],
            pricetick=data["i64PriceLevel"] / 10000,
            size=1,
            net_position=True
        )
        self.gateway.on_contract(contract)
        symbol_contract_map[contract.symbol] = contract



class LongPortTdApi:
    """"""

    def __init__(self, gateway) -> None:
        """构造函数"""
        super().__init__()

        self.account_balence = None
        self.trade_ctx = None
        self.gateway: LongPortGateway = gateway
        self.gateway_name: str = gateway.gateway_name

        self.reqid: int = 0
        self.order_count: int = 0

        self.connect_status: bool = False
        self.login_status: bool = False

        self.userid: str = ""
        self.password: str = ""
        self.orders: Dict[str, OrderData] = {}
        self.short_positions: Dict[str, PositionData] = {}

        self.orderid_sysid_map: Dict[str, str] = {}

        self.prefix: str = ""

        # 账户是否支持两融交易
        self.margin_trading: bool = False

    def onError(self, error: dict, reqid: int) -> None:
        """错误回报"""
        self.gateway.write_error("错误", error)

    def onRiskNotify(self, data: dict) -> None:
        """风险警告回报"""
        status: str = data["alarm_status"]
        rule: str = data["alarm_rule"]
        self.gateway.write_log(f"触发风险警告，状态{status}，类型{rule}")

    def onDisconnect(self) -> None:
        """服务器连接断开回报"""
        self.login_status = False
        self.gateway.write_log("交易服务器连接断开")

    def onLogin(self, data: dict, error: dict) -> None:
        """用户登录请求回报"""
        if not error["err_code"]:
            self.login_status = True
            self.gateway.write_log("交易服务器登录成功")

            self.query_order()
            self.query_trade()
            self.gateway.init_query()
        else:
            self.gateway.write_error("交易服务器登录失败", error)

    def onOrderStatus(self, data) -> None:
        """委托更新推送"""
        exchange, symbol = data["symbol"].split(".")

        orderid: str = data["cl_order_id"]
        sysid: str = data["order_id"]
        if not orderid:
            orderid = sysid

        timestamp: str = f"{data['order_date']} {data['order_time']}"
        dt: datetime = generate_datetime(timestamp)

        # direction, offset = SIDE_HFT2VT[data["side"]]
        #
        # order: OrderData = self.orders.get(orderid, None)
        # if not order:
        #     order = OrderData(
        #         orderid=orderid,
        #         gateway_name=self.gateway_name,
        #         symbol=symbol,
        #         exchange=EXCHANGE_HFT2VT[exchange],
        #         direction=direction,
        #         offset=offset,
        #         type=ORDERTYPE_HFT2VT.get(data["order_type"], OrderType.MARKET),
        #         price=data["price"] / 10000,
        #         volume=data["volume"],
        #         traded=data["filled_volume"],
        #         status=ORDERSTATUS_HFT2VT[data["order_status"]],
        #         datetime=dt,
        #     )
        #     self.orders[orderid] = order
        # elif not order.datetime:
        #     order.datetime = dt
        #
        # order.traded = data["filled_volume"]
        # order.status = ORDERSTATUS_HFT2VT[data["order_status"]]

        # self.gateway.on_order(order)

    def onTradeReport(self, data) -> None:
        """成交数据推送"""
        exchange, symbol = data["symbol"].split(".")

        orderid: str = data["cl_order_id"]
        sysid: str = data["order_id"]
        if not orderid:
            orderid = sysid

        timestamp: str = f"{data['trade_date']} {data['trade_time']}"
        dt: datetime = generate_datetime(timestamp)

        # direction, offset = SIDE_HFT2VT[data["side"]]

        # if data["report_type"] == TradeReportType_Normal:
        #     trade: TradeData = TradeData(
        #         tradeid=data["report_no"],
        #         orderid=orderid,
        #         gateway_name=self.gateway_name,
        #         symbol=symbol,
        #         exchange=EXCHANGE_HFT2VT[exchange],
        #         direction=direction,
        #         offset=offset,
        #         price=data["price"] / 10000,
        #         volume=data["volume"],
        #         datetime=dt,
        #     )
        #     self.gateway.on_trade(trade)

    def onOrderRsp(
            self,
            data: dict,
            error: dict,
            reqid: int,
            last: bool
    ):
        """委托下单回报"""
        orderid: str = data["cl_order_id"]
        order: OrderData = self.orders[orderid]

        if error["err_code"]:
            self.gateway.write_error("交易委托失败", error)

            order.status = Status.REJECTED
            dt: datetime = datetime.now()
            dt: datetime = dt.replace(tzinfo=CHINA_TZ)
            order.datetime = dt
            self.gateway.on_order(order)
        else:
            sysid: str = data["order_id"]
            self.orderid_sysid_map[orderid] = sysid

    def onCancelRsp(
            self,
            data: dict,
            error: dict,
            reqid: int,
            last: bool
    ) -> None:
        """委托撤单失败回报"""
        if error["err_code"]:
            self.gateway.write_error("交易撤单失败", error)

    def onQueryCreditShortsellRsp(
            self,
            data: dict,
            error: dict,
            reqid: int,
            last: bool,
            pos: str
    ):
        if not data["symbol"]:
            return
        exchange, symbol = data["symbol"].split(".")

        pos: PositionData = self.short_positions.get(symbol, None)
        if not pos:
            pos = PositionData(
                gateway_name=self.gateway_name,
                symbol=symbol,
                exchange=EXCHANGE_HFT2VT[exchange],
                direction=Direction.SHORT,
            )
            self.short_positions[symbol] = pos
        pos.volume += data["cur_qty"]

        if last:
            for pos in self.short_positions.values():
                self.gateway.on_position(pos)

            self.short_positions.clear()

    def onQueryPositionRsp(
            self,
            data: dict,
            error: dict,
            reqid: int,
            last: bool,
            pos: str
    ) -> None:
        """持仓查询回报"""
        if not data["symbol"]:
            return
        exchange, symbol = data["symbol"].split(".")

        pos: PositionData = PositionData(
            gateway_name=self.gateway_name,
            symbol=symbol,
            exchange=EXCHANGE_HFT2VT[exchange],
            direction=Direction.NET,
            volume=data["volume"],
            price=data["cost_price"] / 10000,
            pnl=data["total_income"] / 10000,
            yd_volume=data["avail_volume"],
        )
        if self.margin_trading:
            pos.direction = Direction.LONG
        self.gateway.on_position(pos)

    def onQueryCashRsp(self, data: dict, error: dict, reqid: int) -> None:
        """资金查询回报"""
        account: AccountData = AccountData(
            accountid=data["account_id"],
            balance=data["total_amount"] / 10000,
            frozen=(data["total_amount"] - data["avail_amount"]) / 10000,
            gateway_name=self.gateway_name
        )
        print(account)
        if data["account_type"] == 4:
            self.margin_trading = True
        self.gateway.on_account(account)

    def onQueryOrderRsp(
            self,
            data: dict,
            error: dict,
            reqid: int,
            last: bool,
            pos: str
    ) -> None:
        """未成交委托查询回报"""
        if not error["err_code"]:
            exchange, symbol = data["symbol"].split(".")

            orderid: str = data["cl_order_id"]
            sysid: str = data["order_id"]
            if not orderid:
                orderid = sysid
            else:
                self.orderid_sysid_map[orderid] = sysid

            timestamp: str = f"{data['order_date']} {data['order_time']}"
            dt: datetime = generate_datetime(timestamp)

        #     direction, offset = SIDE_HFT2VT[data["side"]]
        #
        #     order: OrderData = OrderData(
        #         orderid=orderid,
        #         gateway_name=self.gateway_name,
        #         symbol=symbol,
        #         exchange=EXCHANGE_HFT2VT[exchange],
        #         direction=direction,
        #         offset=offset,
        #         type=ORDERTYPE_HFT2VT.get(data["order_type"], OrderType.MARKET),
        #         price=data["price"] / 10000,
        #         volume=data["volume"],
        #         status=ORDERSTATUS_HFT2VT[data["order_status"]],
        #         traded=data["filled_volume"],
        #         datetime=dt,
        #     )
        #     self.orders[orderid] = order
        #     self.gateway.on_order(order)
        #
        #     if last:
        #         self.query_order(pos)
        #
        # elif error["err_code"] != 14020:
        #     self.gateway.write_error(error)
        #
        # else:
        #     self.gateway.write_log("查询委托信息成功")

    def onQueryTradeRsp(
            self,
            data: dict,
            error: dict,
            reqid: int,
            last: bool,
            pos: str
    ) -> None:
        """成交信息查询回报"""
        if not error["err_code"]:
            exchange, symbol = data["symbol"].split(".")

            orderid: str = data["cl_order_id"]
            sysid: str = data["order_id"]
            if not orderid:
                orderid = sysid

            timestamp: str = f"{data['trade_date']} {data['trade_time']}"
            dt: datetime = generate_datetime(timestamp)

        #     direction, offset = SIDE_HFT2VT[data["side"]]
        #
        #     trade: TradeData = TradeData(
        #         tradeid=data["report_no"],
        #         orderid=orderid,
        #         gateway_name=self.gateway_name,
        #         symbol=symbol,
        #         exchange=EXCHANGE_HFT2VT[exchange],
        #         direction=direction,
        #         offset=offset,
        #         price=data["price"] / 10000,
        #         volume=data["volume"],
        #         datetime=dt,
        #     )
        #     self.gateway.on_trade(trade)
        #
        #     if last:
        #         self.query_trade(pos)
        #
        # elif error["err_code"] != 14020:
        #     self.gateway.write_error(error)
        #
        # else:
        #     self.gateway.write_log("查询成交信息成功")

    def connect(
            self,
            key: str,
            secret: str,
            token: str
    ) -> None:
        """连接服务器"""
        self.date = datetime.now().strftime("%Y%m%d")

        if not self.connect_status:
            try:
                self.trade_ctx: TradeContext = TradeContext(Config(
                    app_key=key,
                    app_secret=secret,
                    access_token=token
                ))
            except:
                self.gateway.write_log(f"交易登录失败")
            else:
                # 如果没有异常被抛出，则执行这里的代码
                self.gateway.write_log("交易服务器登录成功")
                self.connect_status = True
                self.login_status = True
        else:
            self.gateway.write_log("交易接口已登录，请勿重复操作")

    def send_order(self, req: OrderRequest) -> str:
        """委托下单"""
        # if req.type not in ORDERTYPE_VT2HFT:
        #     self.gateway.write_log(f"当前接口不支持该类型的委托{req.type.value}")
        #     return ""
        #
        # if self.margin_trading and req.offset == Offset.NONE:
        #     self.gateway.write_log("委托失败，两融交易需要选择开平方向")
        #     return ""
        #
        # elif not self.margin_trading and req.offset != Offset.NONE:
        #     self.gateway.write_log("委托失败，现货交易不需要选择开平方向")
        #     return ""
        #
        # self.order_count += 1
        # suffix: str = str(self.order_count).rjust(6, "0")
        # orderid: str = f"{self.prefix}_{suffix}"
        #
        # exchange: Exchange = EXCHANGE_VT2HFT[req.exchange]
        # hft_symbol: str = f"{exchange}.{req.symbol}"
        #
        # order_req: dict = {
        #     "cl_order_id": orderid,
        #     "symbol": hft_symbol,
        #     "order_type": ORDERTYPE_VT2HFT[req.type],
        #     "volume": int(req.volume),
        #     "price": int(Decimal(str(req.price)) * 10000),  # int(req.price * 10000),
        #     "side": SIDE_VT2HFT[(req.direction, req.offset)]
        # }
        #
        # self.reqid += 1
        # self.order(order_req, self.reqid)
        #
        # order: OrderData = req.create_order_data(orderid, self.gateway_name)
        # self.orders[orderid] = order
        # self.gateway.on_order(order)
        # return order.vt_orderid

    def query_order(self, pos_str: str = "") -> None:
        """查询未成交委托"""
        hft_req: dict = {
            "pos_str": pos_str,
            "query_num": 500
        }

        self.reqid += 1
        self.queryOrders(hft_req, self.reqid)

    def query_trade(self, pos_str: str = "") -> None:
        """查询成交"""
        hft_req: dict = {
            "pos_str": pos_str,
            "query_num": 500
        }

        self.reqid += 1
        self.queryTrades(hft_req, self.reqid)

    def cancel_order(self, req: CancelRequest) -> None:
        """委托撤单"""
        self.reqid += 1
        sysid: str = self.orderid_sysid_map.get(req.orderid, req.orderid)

        cancel_req: dict = {"order_id": sysid}
        self.cancelOrder(cancel_req, self.reqid)

    def query_account(self) -> None:
        """查询资金"""
        self.reqid += 1
        self.account_balence = self.trade_ctx.account_balance()
        print(self.account_balence)

    def query_position(self) -> None:
        """查询持仓"""
        self.positions = self.trade_ctx.stock_positions()
        print(self.positions)

    def close(self) -> None:
        """关闭连接"""
        if self.connect_status:
            del self.trade_ctx
            self.gateway.write_log('close td connection')


def generate_datetime(timestamp: str) -> datetime:
    """生成时间"""
    dt: datetime = datetime.strptime(timestamp, "%Y%m%d %H%M%S%f")
    dt: datetime = dt.replace(tzinfo=CHINA_TZ)
    return dt


def generate_cfg(key: str, secret: str, token: str) -> str:
    """生成配置信息"""
    setting: dict = {
        "LONGPORT_APP_KEY": key,
        "LONGPORT_APP_SECRET": secret,
        "LONGPORT_ACCESS_TOKEN": token
    }
    cfg: str = json.dumps(setting, separators=("|", ":"))
    return cfg



if __name__ == '__main__':
    setting = {
        'LONGPORT_APP_KEY': Property.get_property("LONGPORT_APP_KEY"),
        'LONGPORT_APP_SECRET': Property.get_property("LONGPORT_APP_SECRET"),
        'LONGPORT_ACCESS_TOKEN': Property.get_property("LONGPORT_ACCESS_TOKEN"),
    }
    a = LongPortGateway(EventEngine(), 'longport')
    a.connect(setting)
    a.subscribe(SubscribeRequest('700', Exchange.HK))
    print(a)