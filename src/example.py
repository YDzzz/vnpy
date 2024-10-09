import sys
from datetime import datetime, timedelta

from longport.openapi import Period

from src.LongPortGateway import LongPortGateway
from src.MySqlDataBase import MySqlDataBase
from src.tools.property import Property
from vnpy.event import EventEngine
from vnpy.trader.constant import Exchange
from vnpy.trader.object import HistoryRequest

if __name__ == '__main__':
    db = MySqlDataBase()
    gateway = LongPortGateway(EventEngine(), 'longport')
    setting = {
        'LONGPORT_APP_KEY': Property.get_property("LONGPORT_APP_KEY"),
        'LONGPORT_APP_SECRET': Property.get_property("LONGPORT_APP_SECRET"),
        'LONGPORT_ACCESS_TOKEN': Property.get_property("LONGPORT_ACCESS_TOKEN"),
    }
    gateway.connect(setting)
    sql = "SELECT symbol, exchange FROM StockInformation where exchange='SH' AND symbol > '688692'"
    with db.connection.cursor() as cursor:
        cursor.execute(sql)
        results = cursor.fetchall()
        previous_datatime = datetime.now()
        for row in results:
            while datetime.now() - previous_datatime < timedelta(seconds=0.05):
                continue
            previous_datatime = datetime.now()
            bar_list = gateway.query_candlesticks(HistoryRequest(row['symbol'], Exchange[row['exchange']], interval=Period.Day))
            db.save_bar_data(bar_list)