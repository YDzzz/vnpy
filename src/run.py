# flake8: noqa
from vnpy.event import EventEngine

from vnpy.trader.engine import MainEngine
from vnpy.trader.ui import MainWindow, create_qapp

from src.LongPortGateway import LongPortGateway


# from vnpy_datamanager import DataManagerApp


def main():
    """"""
    qapp = create_qapp()

    event_engine = EventEngine()

    main_engine = MainEngine(event_engine)

    main_engine.add_gateway(LongPortGateway)



    # main_engine.add_app(CtaStrategyApp)
    # main_engine.add_app(CtaBacktesterApp)
    #
    # main_engine.add_app(DataManagerApp)


    main_window = MainWindow(main_engine, event_engine)
    main_window.show()

    qapp.exec()


if __name__ == "__main__":
    main()
