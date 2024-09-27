import enum

class TradeStatus(enum):
  NORMAL = 0
  HALTED = 1
  DELISTED = 2
  FUSE = 3
  PREPARE_LIST = 4
  CODE_MOVED = 5
  TO_BE_OPENED = 6
  SPLIT_STOCK_HALTS = 7
  EXPIRED = 8
  WARRANT_PREPARE_LIST = 9
  SUSPEND_TRADE = 10


class TradeSession(enum):
    NORMAL_TRADE = 0
    PRE_TRADE = 1
    POST_TRADE = 2

