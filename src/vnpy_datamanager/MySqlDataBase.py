from datetime import datetime
from typing import List

import pymysql
from pymysql import IntegrityError

from vnpy.trader.constant import Exchange, Interval
from vnpy.trader.database import BaseDatabase, TickOverview, BarOverview, DB_TZ
from vnpy.trader.object import TickData, BarData
from vnpy.trader.setting import SETTINGS


class MySqlDataBase(BaseDatabase):
    connection = pymysql.connect(host=SETTINGS['database.host'],
                                 port=SETTINGS['database.port'],
                                 user=SETTINGS['database.user'],
                                 password=SETTINGS['database.password'],
                                 database=SETTINGS['database.database'])

    sql_date_format = "%Y-%m-%d %H:%M:%S"

    save_bar_data_sql: str = ("INSERT INTO `vnpy`.`BarData` (`symbol`, `exchange`, `date`, `interval`, "
                              "`volume`, `turnover`, `open_interest`, `open`, `high`, `low`, `close`) "
                              "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s);")
    load_bar_data_sql: str = 'SELECT * FROM `vnpy`.`BarData` WHERE `symbol` = %s AND `exchange` = %s AND `interval` = %s AND `date` BETWEEN %s and %s'
    delete_bar_data_sql: str = 'DELETE FROM `vnpy`.`BarData` WHERE `symbol` = %s AND `exchange` = %s AND `interval` = %s'

    load_bar_overview_sql: str = 'SELECT `symbol`, `exchange`, `interval`, COUNT(*), MIN(`date`), MAX(`date`) FROM `vnpy`.`BarData` GROUP BY `symbol`, `exchange`,   `interval`'
    save_tick_data_sql: str = None

    def save_bar_data(self, bars: List[BarData], stream: bool = False) -> bool:
        with MySqlDataBase.connection.cursor() as cursor:
            duplicate_num: int = 0
            for bar in bars:
                try:
                    cursor.execute(MySqlDataBase.save_bar_data_sql,
                                   (bar.symbol, bar.exchange.value, bar.datetime, bar.interval.value, bar.volume,
                                         bar.turnover, bar.open_interest, bar.open_price, bar.high_price, bar.low_price,
                                         bar.close_price))
                except IntegrityError as e:
                    duplicate_num += 1
            MySqlDataBase.connection.commit()
            print("duplicate data num is ", duplicate_num)
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
            cursor.execute(self.load_bar_data_sql, (symbol, exchange.value, interval.value, start, end))
            # Fetch the results
            results = cursor.fetchall()
            for row in results:
                bar_data = BarData(
                    gateway_name="db",
                    symbol=symbol,
                    exchange=exchange,
                    datetime=row[2],
                    interval=interval,
                    volume=row[4],
                    turnover=row[5],
                    open_interest=row[6],
                    open_price=row[7],
                    high_price=row[8],
                    low_price=row[9],
                    close_price=row[10],
                )
                bar_data_list.append(bar_data)
        return bar_data_list
    
    def load_tick_data(self, symbol: str, exchange: Exchange, start: datetime, end: datetime) -> List[TickData]:
        pass

    def delete_bar_data(self, symbol: str, exchange: Exchange, interval: Interval) -> int:
        deleted_count: int
        try:
            with MySqlDataBase.connection.cursor() as cursor:
                # 你的删除SQL语句
                cursor.execute(self.delete_bar_data_sql, (symbol, exchange.value, interval.value))
                # 获取删除的记录数量
                deleted_count = cursor.rowcount
                print(f"删除了 {deleted_count} 条记录")
            MySqlDataBase.connection.commit()
        except pymysql.MySQLError as e:
            print(f"数据库错误: {e}")
            MySqlDataBase.connection.rollback()
        return deleted_count

    def delete_tick_data(self, symbol: str, exchange: Exchange) -> int:
        pass

    def get_bar_overview(self) -> List[BarOverview]:
        bar_list: List[BarOverview] = list()
        try:
            with self.connection.cursor() as cursor:
                # SQL查询
                cursor.execute(MySqlDataBase.load_bar_overview_sql)
                # 获取查询结果
                results = cursor.fetchall()

                # 保存结果
                for row in results:
                    bar = BarOverview(
                        symbol=row[0],
                        exchange=Exchange(row[1]),
                        interval=Interval(row[2]),
                        count=row[3],
                        start=row[4],
                        end=row[5]
                    )
                    bar_list.append(bar)

        finally:
            pass
        return bar_list

    def get_tick_overview(self) -> List[TickOverview]:
        pass


database: BaseDatabase = None


def get_database() -> BaseDatabase:
    """"""
    # Return database object if already inited
    global database
    if database:
        return database

    # Create database object from module
    database = MySqlDataBase()
    return database


if __name__ == '__main__':
    db=get_database()
    res = db.load_bar_data('600900', Exchange.SH, Interval.DAILY, datetime(2024,11,4), datetime(2024,11,8))
    print(res)

