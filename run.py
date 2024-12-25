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

    event_engine = EventEngine()

    main_engine = MainEngine(event_engine)

    main_engine.add_gateway(LongBridgeGateway, "LongPort")
    #
    # main_engine.add_app(DataManagerApp)
    #
    # main_engine.add_app(CtaStrategyApp)
    #
    # main_engine.add_app(DataRecorderApp)
    #
    # main_engine.add_app(CtaBacktesterApp)
    # #
    #
    # main_engine.add_app(ChartWizardApp)

    # sleep(3)

    main_window = MainWindow(main_engine, event_engine)
    main_window.show()
    splash.close()

    qapp.exec()


if __name__ == "__main__":
    main()
