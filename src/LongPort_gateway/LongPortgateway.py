import sys
import json
from datetime import datetime
from typing import Dict, List
from pathlib import Path
from decimal import Decimal

from longport.openapi import Market, OrderStatus, OrderSide, Config, QuoteContext, SubType, TradeContext
from longport.openapi import OrderType as LongPortOrderType

from src.tools.property import Property
from src.event import EventEngine
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
def MK_LPT2VT(market):
    if market == Market.HK:
        return Exchange.SEHK
    elif market == Market.US:
        return Exchange.AMEX


def MK_VT2LPT(exchange):
    if exchange == Exchange.SEHK:
        return Market.HK
    elif exchange == Exchange.AMEX:
        return Market.US


# 委托状态映射
def ORDERSTATUS_LPT2VT(status):
    if status == OrderStatus.NotReported:
        return Status.SUBMITTING
    elif status == OrderStatus.New:
        return Status.NOTTRADED
    elif status == OrderStatus.PartialFilled:
        return Status.PARTTRADED
    elif status == OrderStatus.Filled:
        return Status.ALLTRADED
    elif status == OrderStatus.PendingCancel:
        return Status.SUBMITTING
    elif status == OrderStatus.Canceled:
        return Status.CANCELLED
    elif status == OrderStatus.Expired:
        return Status.CANCELLED
    elif status == OrderStatus.PartialWithdrawal:
        return Status.CANCELLED
    elif status == OrderStatus.Rejected:
        return Status.REJECTED


# 委托类型映射
def ORDERTYPE_LPT2VT(order_type):
    if order_type == LongPortOrderType.ELO:
        return OrderType.LIMIT
    elif order_type == LongPortOrderType.MO:
        return OrderType.MARKET


def ORDERTYPE_VT2LPT(order_type):
    if order_type == OrderType.LIMIT:
        return LongPortOrderType.ELO
    elif order_type == OrderType.MARKET:
        return LongPortOrderType.MO


# 交易所映射
def EXCHANGE_LPT2VT(exchange):
    if exchange == Market.HK:
        return Exchange.SEHK
    elif exchange == Market.US:
        return Exchange.AMEX


def EXCHANGE_VT2LPT(exchange):
    if exchange == Exchange.SEHK:
        return Market.HK
    elif exchange == Exchange.AMEX:
        return Market.US


# 多空方向映射
def SIDE_LPT2VT(order_side):
    if order_side == OrderSide.Buy:
        return (Direction.LONG, Offset.OPEN)
    elif order_side == OrderSide.Sell:
        return (Direction.LONG, Offset.CLOSE)


def SIDE_VT2LPT(direction_offset):
    direction, offset = direction_offset
    if direction == Direction.LONG and offset == Offset.OPEN:
        return OrderSide.Buy
    elif direction == Direction.LONG and offset == Offset.CLOSE:
        return OrderSide.Sell


# 其他常量
MAX_FLOAT = sys.float_info.max  # 浮点数极限值
CHINA_TZ = ZoneInfo("Asia/Shanghai")  # 中国时区

# 合约数据全局缓存字典
symbol_contract_map: Dict[str, ContractData] = {}


class LongPortgateway(BaseGateway):
    """
    VeighNa用于对接国泰君安的交易接口。
    """

    default_name: str = "HFT"

    default_setting: Dict[str, str] = {
        'LONGPORT_APP_KEY': Property.get_property('LONGPORT_APP_KEY'),
        'LONGPORT_APP_SECRET': Property.get_property('LONGPORT_APP_SECRET'),
        'LONGPORT_ACCESS_TOKEN': Property.get_property('LONGPORT_ACCESS_TOKEN'),
    }

    exchanges: List[str] = [Exchange.HK, Exchange.AMEX]

    def __init__(self, event_engine: EventEngine, gateway_name: str) -> None:
        """构造函数"""
        super().__init__(event_engine, gateway_name)

        self.count = None
        self.query_functions = None
        self.td_api: "LpTdApi" = LpTdApi(self)
        self.md_api: "LpMdApi" = LpMdApi(self)

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
        self.query_functions: list = [self.query_account, self.query_position]
        self.event_engine.register(EVENT_TIMER, self.process_timer_event)


class LpMdApi:

    def __init__(self, gateway: LongPortgateway) -> None:
        """构造函数"""
        super().__init__()

        self.date = None
        self.quote_ctx = None
        self.gateway: LongPortgateway = gateway
        self.gateway_name: str = gateway.gateway_name

        self.key = gateway.default_setting["LONGPORT_APP_KEY"]
        self.secret = gateway.default_setting["LONGPORT_APP_SECRET"]
        self.access_token = gateway.default_setting['LONGPORT_ACCESS_TOKEN']

        self.connect_status: bool = False
        self.login_status: bool = False

        self.sehk_inited: bool = False
        self.amex_inited: bool = False

    def onDisconnected(self, reason: int) -> None:
        """服务器连接断开回报"""
        self.connect_status = False
        self.login_status = False
        self.gateway.write_log(f"行情服务器连接断开, 原因{reason}")

        self.login_server()

    def onSubscribe(self, error) -> None:
        """订阅行情回报"""
        if error["errcode"]:
            self.gateway.write_log(
                f"订阅失败，错误码{error['errcode']}，信息{error['errstr']}"
            )

    def onMarketData(self, mk_type: int, symbol: str, data: dict) -> None:
        """行情数据推送"""
        timestamp: str = f"{self.date} {str(data['nTime'])}"
        dt: datetime = generate_datetime(timestamp)

        tick: TickData = TickData(
            symbol=symbol,
            exchange=MK_LPT2VT(mk_type),
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
        cfg = Config(app_key=key,
                     app_secret=secret,
                     access_token=access_token
                     )

        self.date = datetime.now().strftime("%Y%m%d")

        if not self.connect_status:
            try:
                self.quote_ctx: QuoteContext = QuoteContext(cfg)
                self.query_contract()
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
            exchange = MK_VT2LPT(req.exchange)
            self.quote_ctx.subscribe([f'{req.symbol}.{exchange}'], [SubType.Quote])

    # 合约查询
    def query_contract(self) -> None:
        pass

    def onHKBaseInfo(self, code, data) -> None:
        """香港合约查询回报"""
        contract: ContractData = ContractData(
            gateway_name=self.gateway_name,
            symbol=str(code),
            exchange=Exchange.SEHK,
            name=data["szStkNameZN"].split(" ")[0],
            product=Product.EQUITY,
            min_volume=data["i64BuyNumUnit"],
            pricetick=data["i64PriceLevel"] / 10000,
            size=1,
            net_position=True
        )
        self.gateway.on_contract(contract)
        symbol_contract_map[contract.symbol] = contract

    def onUSBaseInfo(self, code, data) -> None:
        """美国合约查询回报"""
        contract: ContractData = ContractData(
            gateway_name=self.gateway_name,
            symbol=str(code),
            exchange=Exchange.AMEX,
            name=data["sSymbol"],
            product=Product.EQUITY,
            min_volume=data["i64BuyQtyUnit"],
            pricetick=data.get("i64PriceTick", 100) / 10000,
            size=1,
            net_position=True
        )

        self.gateway.on_contract(contract)
        symbol_contract_map[contract.symbol] = contract


class LpTdApi:
    """"""

    def __init__(self, gateway) -> None:
        """构造函数"""
        super().__init__()

        self.trade_ctx = None
        self.gateway: LongPortgateway = gateway
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
        # self.margin_trading = False

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

        direction, offset = SIDE_LPT2VT(data["side"])

        order: OrderData = self.orders.get(orderid, None)
        if not order:
            order = OrderData(
                orderid=orderid,
                gateway_name=self.gateway_name,
                symbol=symbol,
                exchange=EXCHANGE_LPT2VT(exchange),
                direction=direction,
                offset=offset,
                type=ORDERTYPE_LPT2VT(data["order_type"]),
                price=data["price"] / 10000,
                volume=data["volume"],
                traded=data["filled_volume"],
                status=ORDERSTATUS_LPT2VT(data["order_status"]),
                datetime=dt,
            )
            self.orders[orderid] = order
        elif not order.datetime:
            order.datetime = dt

        order.traded = data["filled_volume"]
        order.status = ORDERSTATUS_LPT2VT(data["order_status"])

        self.gateway.on_order(order)

    def onTradeReport(self, data) -> None:
        """成交数据推送"""
        exchange, symbol = data["symbol"].split(".")

        orderid: str = data["cl_order_id"]
        sysid: str = data["order_id"]
        if not orderid:
            orderid = sysid

        timestamp: str = f"{data['trade_date']} {data['trade_time']}"
        dt: datetime = generate_datetime(timestamp)

        direction, offset = SIDE_LPT2VT(data["side"])

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
                exchange=EXCHANGE_LPT2VT(exchange),
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
            exchange=EXCHANGE_LPT2VT(exchange),
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

            direction, offset = SIDE_LPT2VT(data["side"])

            order: OrderData = OrderData(
                orderid=orderid,
                gateway_name=self.gateway_name,
                symbol=symbol,
                exchange=EXCHANGE_LPT2VT(exchange),
                direction=direction,
                offset=offset,
                type=ORDERTYPE_LPT2VT(data["order_type"]),
                price=data["price"] / 10000,
                volume=data["volume"],
                status=ORDERSTATUS_LPT2VT(data["order_status"]),
                traded=data["filled_volume"],
                datetime=dt,
            )
            self.orders[orderid] = order
            self.gateway.on_order(order)

            if last:
                self.query_order(pos)

        elif error["err_code"] != 14020:
            self.gateway.write_error(error)

        else:
            self.gateway.write_log("查询委托信息成功")

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

            direction, offset = SIDE_LPT2VT(data["side"])

            trade: TradeData = TradeData(
                tradeid=data["report_no"],
                orderid=orderid,
                gateway_name=self.gateway_name,
                symbol=symbol,
                exchange=EXCHANGE_LPT2VT(exchange),
                direction=direction,
                offset=offset,
                price=data["price"] / 10000,
                volume=data["volume"],
                datetime=dt,
            )
            self.gateway.on_trade(trade)

            if last:
                self.query_trade(pos)

        elif error["err_code"] != 14020:
            self.gateway.write_error(error)

        else:
            self.gateway.write_log("查询成交信息成功")

    def connect(
            self,
            key: str,
            secret: str,
            token: str
    ) -> None:
        """连接服务器"""
        self.prefix = datetime.now().strftime("%Y%m%d%H%M%S")

        if not self.connect_status:
            path: Path = get_folder_path(self.gateway_name.lower())
            # TODO 设置日志
            # self.setLogConfig(str(path).encode("UTF_8"))

            self.trade_ctx: TradeContext = TradeContext(Config(
                app_key=key,
                app_secret=secret,
                access_token=token
            ))

            self.connect_status = True
            self.query_account()
            self.query_position()

    def send_order(self, req: OrderRequest) -> str:
        """委托下单"""
        if req.type not in [OrderType.LIMIT, OrderType.MARKET]:
            self.gateway.write_log(f"当前接口不支持该类型的委托{req.type.value}")
            return ""

        if self.margin_trading and req.offset == Offset.NONE:
            self.gateway.write_log("委托失败，两融交易需要选择开平方向")
            return ""

        elif not self.margin_trading and req.offset != Offset.NONE:
            self.gateway.write_log("委托失败，现货交易不需要选择开平方向")
            return ""

        self.order_count += 1
        suffix: str = str(self.order_count).rjust(6, "0")
        orderid: str = f"{self.prefix}_{suffix}"

        exchange: Exchange = EXCHANGE_VT2LPT(req.exchange)
        lpt_symbol: str = f"{exchange}.{req.symbol}"

        order_req: dict = {
            "cl_order_id": orderid,
            "symbol": lpt_symbol,
            "order_type": ORDERTYPE_VT2LPT(req.type),
            "volume": int(req.volume),
            "price": int(Decimal(str(req.price)) * 10000),  # int(req.price * 10000),
            "side": SIDE_VT2LPT((req.direction, req.offset))
        }

        self.reqid += 1
        self.order(order_req, self.reqid)

        order: OrderData = req.create_order_data(orderid, self.gateway_name)
        self.orders[orderid] = order
        self.gateway.on_order(order)
        return order.vt_orderid

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

    def query_account(self) -> AccountData:
        """查询资金"""
        self.reqid += 1
        resp = self.trade_ctx.account_balance()
        balance: float = float(resp[0].total_cash)
        frozen: float = float(resp[0].cash_infos[0].frozen_cash)
        account: AccountData = AccountData('trader', 'LongPort', balance, frozen)
        self.gateway.on_account(account)


    def query_position(self) -> None:
        """查询持仓"""
        positions = self.trade_ctx.stock_positions()
        print(positions)

        # if self.margin_trading:
        #     self.reqid += 1
        #     self.queryCreditShortsell(hft_req, self.reqid)

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


def generate_cfg(ip: str, port: int, username: str, password: str) -> str:
    """生成配置信息"""
    setting: dict = {
        "ip0": ip,
        "port0": port,
        "connect_mode": "NR",
        "username": username,
        "password": password
    }
    cfg: str = json.dumps(setting, separators=("|", ":"))
    return cfg


if __name__ == '__main__':

    key = '423fb4ecbf32328a8af12f63d5938a25'
    secret = '82424c3cdbc3663b13735d4a6d1149d684304fca7388127d77e66fefd1dd9a29'
    token = 'm_eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJsb25nYnJpZGdlIiwic3ViIjoiYWNjZXNzX3Rva2VuIiwiZXhwIjoxNzM1MTIyNDkyLCJpYXQiOjE3MjczNDY0OTQsImFrIjoiNDIzZmI0ZWNiZjMyMzI4YThhZjEyZjYzZDU5MzhhMjUiLCJhYWlkIjoyMDQwOTQ3NCwiYWMiOiJsYl9wYXBlcnRyYWRpbmciLCJtaWQiOjE0MTk2NDI1LCJzaWQiOiJIRzA2OGdpb1FIellFREtmVkwzd013PT0iLCJibCI6MSwidWwiOjAsImlrIjoibGJfcGFwZXJ0cmFkaW5nXzIwNDA5NDc0In0.ZQ-J52s1FwSPBCT7n_6vsRpw26VYFCHJSa_Xrf8D0aGIgwuBaWPjqqTK2r41kl7W5e08LoHe-jPLSib7wh70_w8zs5tleyNZb_a7QY6HBaaFaTDUqEwoiDZDsURmAHEIEZyF7FY9hnNSX-SrhprzG3n8cZ2DoVse635_MWNPkD_79N_Xu5Sic7ZWVMTgjRuBLC1VQzqjdBwLo2Lr-EM2Ow51J8sVx6TLq8y352sGnrWfS0lGgoU802P7PKlKvDpNe39r8cv2-57g5kWMikcoEjlNGdF5V9vBYEIi12PREQupCr2O6bX7sUlpcYBPHEJpVefMYba_0Cw2BKAeqF_Lul_QL8opAPoE2O6tVdvGOKYsIMcyoZBD-Zs3zLkkLeu-KCDs4VquKHnE-TCFvO0orI2YbOomC7nqvRPTL8GijvEboR7Hv1YZZJuqF2adx5cFgje52Qqzia6qx2Mj7Ht3K0h9ONpYRhwNyiRF7BfOA6D6CXgDmkT-inAWU67r3TF4v378O1tjj0Oo9aaBiv7dosNqF1vxnRzZT9N93ITIXP7djlCz1Pgyrv4ZmuNayeLReUtX0N3nUYP8j4PkDeSMQjUeZ1xN3CKwwRxA2D9FEFjU30r2p2TBUG1LhRMEiCoSC0FxavqCFPI-7DfS5zBQLg6FQvr7nc0FT-9165PJ-6c'

    config = Config(app_key=key,
                    app_secret=secret,
                    access_token=token)
    ctx = TradeContext(config)
    resp = ctx.stock_positions()
    print(resp.channels)
