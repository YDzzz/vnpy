# flake8: noqa
from time import sleep

from model.vnpy_chartwizard import ChartWizardApp
from model.vnpy_ctabacktester import CtaBacktesterApp
from model.vnpy_ctastrategy import CtaStrategyApp
from model.vnpy_datamanager import DataManagerApp
from model.vnpy_datarecorder import DataRecorderApp
from model.vnpy_LongPort import LongBridgeGateway

from vnpy.event import EventEngine
from vnpy.trader.engine import MainEngine
from vnpy.trader.ui import MainWindow, create_qapp
from vnpy.trader.ui.qt import SplashScreen


def main():
    """"""
    
    qapp = create_qapp()
    splash = SplashScreen()
    splash.show()
    
    # 初始化组件时更新进度
    splash.update_status("正在初始化引擎...", 0)
    event_engine = EventEngine()
    main_engine = MainEngine(event_engine)
    
    splash.update_status("正在加载网关...", 20)
    main_engine.add_gateway(LongBridgeGateway, "LongPort")
    
    splash.update_status("正在加载数据管理器...", 40)
    main_engine.add_app(DataManagerApp)
    
    splash.update_status("正在加载CTA策略模块...", 60)
    main_engine.add_app(CtaStrategyApp)
    
    splash.update_status("正在加载其他模块...", 80)
    main_engine.add_app(DataRecorderApp)
    main_engine.add_app(CtaBacktesterApp)
    main_engine.add_app(ChartWizardApp)
    
    splash.update_status("准备就绪...", 100)
    
    main_window = MainWindow(main_engine, event_engine)
    splash.close()
    main_window.show()
    
    qapp.exec()


if __name__ == "__main__":
    main()
