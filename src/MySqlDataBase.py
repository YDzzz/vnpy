from datetime import datetime
from typing import List, Any

import pandas
import pymysql
from pandas import Period

from src.tools.property import Property
from vnpy.trader.constant import Exchange, Interval
from vnpy.trader.database import BaseDatabase, TickOverview, BarOverview
from vnpy.trader.object import TickData, BarData


class MySqlDataBase(BaseDatabase):
    connection = pymysql.connect(host=Property.get_property("DB_HOST"),
                                 port=int(Property.get_property("DB_PORT")),
                                 user=Property.get_property("DB_USER"),
                                 password=Property.get_property("DB_PASSWORD"),
                                 database='vnpy',
                                 cursorclass=pymysql.cursors.DictCursor)

    sql_date_format = "%Y-%m-%d %H:%M:%S"

    save_bar_data_sql: str = ("INSERT INTO `vnpy`.`BarData` (`symbol`, `exchange`, `datetime`, `interval`,"
                              " `volume`, `turnover`, `open_interest`, `open`, `high`, `low`,"
                              " `close`) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s);")
    load_bar_data_sqp: str = 'SELECT * FROM `vnpy`.`BarData` WHERE symbol = %s, datetime BETWEEN %s AND %s LIMIT 0,1000'
    save_tick_data_sql: str = None

    def save_bar_data(self, bars: List[BarData], stream: bool = False) -> bool:
        try:
            with MySqlDataBase.connection.cursor() as cursor:
                for bar in bars:
                    cursor.execute(MySqlDataBase.save_bar_data_sql,
                                   (bar.symbol, bar.exchange.value, bar.datetime, bar.interval.value, bar.volume,
                                         bar.turnover, bar.open_interest, bar.open_price, bar.high_price, bar.low_price,
                                         bar.close_price))
        except Exception as e:
            print(e)
            return False
        finally:
            MySqlDataBase.connection.commit()
            return True


    def save_tick_data(self, ticks: List[TickData], stream: bool = False) -> bool:
        pass
        # try:
        #     with MySqlDataBase.connection.cursor() as cursor:
        #         for tick in ticks:
        #             cursor.execute(MySqlDataBase.save_tick_data_sql)
        # except Exception as e:
        #     print(e)
        #     return False
        # finally:
        #     MySqlDataBase.connection.commit()
        #     return True

    def load_bar_data(
            self,
            symbol: str,
            exchange: Exchange,
            interval: Interval,
            start: datetime,
            end: datetime
    ) -> List[BarData]:
        bar_data_list: list[BarData] = []
        with MySqlDataBase.connection.cursor() as cursor:
            # Execute the query
            cursor.execute(self.load_bar_data_sqp, (start.strftime(self.sql_date_format), end.strftime(self.sql_date_format)))
            # Fetch the results
            results = cursor.fetchall()
            for row in results:
                bar_data = BarData(
                    gateway_name="longport",
                    symbol=symbol,
                    exchange=exchange,
                    datetime=row['datetime'],
                    interval=interval,
                    volume=row['volume'],
                    turnover=row['turnover'],
                    open_interest=row['open_interest'],
                    open_price=row['open_price'],
                    high_price=row['high_price'],
                    low_price=row['low_price'],
                    close_price=row['close_price'],
                )
                bar_data_list.append(bar_data)
        return bar_data_list

    def load_tick_data(self, symbol: str, exchange: Exchange, start: datetime, end: datetime) -> List[TickData]:
        pass

    def delete_bar_data(self, symbol: str, exchange: Exchange, interval: Interval) -> int:
        pass

    def delete_tick_data(self, symbol: str, exchange: Exchange) -> int:
        pass

    def get_bar_overview(self) -> List[BarOverview]:
        pass

    def get_tick_overview(self) -> List[TickOverview]:
        pass





