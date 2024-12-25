import ctypes
import platform
import sys
import traceback
import webbrowser
import types
import threading

import qdarkstyle
from PySide6 import QtGui, QtWidgets, QtCore

from ..setting import SETTINGS
from ..utility import get_icon_path
from ..locale import _

Qt = QtCore.Qt
QtCore.pyqtSignal = QtCore.Signal
QtWidgets.QAction = QtGui.QAction
QtCore.QDate.toPyDate = QtCore.QDate.toPython
QtCore.QDateTime.toPyDate = QtCore.QDateTime.toPython


def create_qapp(app_name: str = "VeighNa Trader") -> QtWidgets.QApplication:
    """
    Create Qt Application.
    """
    # Set up dark stylesheet
    qapp: QtWidgets.QApplication = QtWidgets.QApplication(sys.argv)
    qapp.setStyleSheet("""
    QMainWindow {
        background-color: #202020;
        color: #EDEDED;
    }
    QWidget {
        border-radius: 4px;
        background-color: #272727;
        color: #EDEDED;
    }
    QLabel {
        color: #EDEDED;
    }
    /**/
    QLineEdit {
        background-color: #3E3E3E;
        color: #EDEDED;
    }
    
    /*下拉列表*/
    QComboBox {
        background-color: #3E3E3E;
        color: #EDEDED;
    }
    QComboBox QAbstractItemView {
        background-color: #2B2B2B;
        color: #EDEDED;
    }
    QComboBox QAbstractItemView::item {
        border: 3px solid #2B2B2B;
    }
    QComboBox QAbstractItemView::item:selected {
        background: #3C3C3C;
    }
    QPushButton {
        background-color: #343434;
        color: #EDEDED;
        border-radius: 5px;
    }
    /*悬浮窗*/
    QDockWidget {
        background-color: #272727;
        color: #EDEDED;
    }
    QDockWidget::title {
        background-color: #222; /* 标题栏背景颜色 */
        color: black; /* 标题栏字体颜色 */
        height: 20px; /* 标题栏高度 */
    }
    
    QHeaderView::section {
        border: 1px solid #202020;
        background-color: #272727;
        color: #EDEDED;
    }
    QTableWidget::item {
        background-color: #272727;
    }
    /*工具栏颜色修改*/
    QToolBar QToolButton {
        background: #202020;
        border: 10px solid transparent;
        border-radius: 4px;
    }
    QToolBar QToolButton:hover {
        background: #282828;
        border-radius: 4px;
    }
    QToolBar {
        background: #202020;
    }
    /*菜单栏样式*/
    QMenuBar {
        background-color: #202020;
        color: #EDEDED;
    }
    QMenuBar::item:selected {
        background-color: #272727;
    }
    QMenu {
            background-color: #343434;
            color: #EDEDED;
        }
    """)

    # Set up font
    font: QtGui.QFont = QtGui.QFont(SETTINGS["font.family"], SETTINGS["font.size"])
    qapp.setFont(font)

    # Set up icon
    icon: QtGui.QIcon = QtGui.QIcon(get_icon_path(__file__, "vnpy.ico"))
    qapp.setWindowIcon(icon)

    # Set up windows process ID
    if "Windows" in platform.uname():
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(
            app_name
        )

    # Hide help button for all dialogs
    # qapp.setAttribute(QtCore.Qt.AA_DisableWindowContextHelpButton)

    # Exception Handling
    exception_widget: ExceptionWidget = ExceptionWidget()

    def excepthook(exctype: type, value: Exception, tb: types.TracebackType) -> None:
        """Show exception detail with QMessageBox."""
        sys.__excepthook__(exctype, value, tb)

        msg: str = "".join(traceback.format_exception(exctype, value, tb))
        exception_widget.signal.emit(msg)

    sys.excepthook = excepthook

    if sys.version_info >= (3, 8):
        def threading_excepthook(args: threading.ExceptHookArgs) -> None:
            """Show exception detail from background threads with QMessageBox."""
            sys.__excepthook__(args.exc_type, args.exc_value, args.exc_traceback)

            msg: str = "".join(traceback.format_exception(args.exc_type, args.exc_value, args.exc_traceback))
            exception_widget.signal.emit(msg)

        threading.excepthook = threading_excepthook

    return qapp


class ExceptionWidget(QtWidgets.QWidget):
    """"""
    signal: QtCore.Signal = QtCore.Signal(str)

    def __init__(self, parent: QtWidgets.QWidget = None) -> None:
        """"""
        super().__init__(parent)

        self.init_ui()
        self.signal.connect(self.show_exception)

    def init_ui(self) -> None:
        """"""
        self.setWindowTitle(_("触发异常"))
        self.setFixedSize(600, 600)

        self.msg_edit: QtWidgets.QTextEdit = QtWidgets.QTextEdit()
        self.msg_edit.setReadOnly(True)

        copy_button: QtWidgets.QPushButton = QtWidgets.QPushButton(_("复制"))
        copy_button.clicked.connect(self._copy_text)

        community_button: QtWidgets.QPushButton = QtWidgets.QPushButton(_("求助"))
        community_button.clicked.connect(self._open_community)

        close_button: QtWidgets.QPushButton = QtWidgets.QPushButton(_("关闭"))
        close_button.clicked.connect(self.close)

        hbox: QtWidgets.QHBoxLayout = QtWidgets.QHBoxLayout()
        hbox.addWidget(copy_button)
        hbox.addWidget(community_button)
        hbox.addWidget(close_button)

        vbox: QtWidgets.QVBoxLayout = QtWidgets.QVBoxLayout()
        vbox.addWidget(self.msg_edit)
        vbox.addLayout(hbox)

        self.setLayout(vbox)

    def show_exception(self, msg: str) -> None:
        """"""
        self.msg_edit.setText(msg)
        self.show()

    def _copy_text(self) -> None:
        """"""
        self.msg_edit.selectAll()
        self.msg_edit.copy()

    def _open_community(self) -> None:
        """"""
        webbrowser.open("https://www.vnpy.com/forum/forum/2-ti-wen-qiu-zhu")


# 定义动画窗口类
class SplashScreen(QtWidgets.QLabel):
    def __init__(self):
        super().__init__()
        self.setWindowFlags(self.windowFlags() | Qt.WindowStaysOnTopHint)  # 窗口置顶
        self.setPixmap(QtGui.QPixmap("ico/bg37.jpg"))  # 设置开机动画图片
        self.resize(self.pixmap().size())  # 调整窗口大小以适应图片
        self.show()
