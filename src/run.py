# flake8: noqa
from vnpy.event import EventEngine

from vnpy.trader.engine import MainEngine
from vnpy.trader.ui import MainWindow, create_qapp

from src.vnpy_LongPort import LongBridgeGateway


from vnpy_datamanager import DataManagerApp
from vnpy_ctastrategy import CtaStrategyApp
from vnpy_chartwizard import ChartWizardApp


def main():
    """"""
    qapp = create_qapp()

    event_engine = EventEngine()

    main_engine = MainEngine(event_engine)

    main_engine.add_gateway(LongBridgeGateway, "LongPort")

    main_engine.add_app(DataManagerApp)

    main_engine.add_app(CtaStrategyApp)

    # main_engine.add_app(CtaBacktesterApp)
    #

    main_engine.add_app(ChartWizardApp)

    main_window = MainWindow(main_engine, event_engine)
    main_window.show()

    qapp.exec()


if __name__ == "__main__":
    main()
