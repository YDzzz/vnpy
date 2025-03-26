import ctypes
from pathlib import Path
import platform
import sys
from time import sleep
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
        background-color: transparent;
    }
    
    /*输入框*/
    QLineEdit {
        background-color: #3E3E3E;
        color: #EDEDED;
        border: 1px solid #555555;
        border-radius: 3px;
        padding: 2px;
        min-height: 16px;
        max-height: 16px;
    }
    
    QLineEdit:hover {
        background-color: #4E4E4E;
        border: 1px solid #666666;
    }
    
    QLineEdit:focus {
        background-color: #505050;
        border: 1px solid #666666;
    }
    
    /*下拉列表*/
    QComboBox {
        background-color: #3E3E3E;
        color: #EDEDED;
        border: 1px solid #555555;
        border-radius: 3px;
        padding: 2px;
        min-height: 16px;
        max-height: 16px;
        min-width: 6em;
    }
    
    QComboBox:hover {
        background-color: #4E4E4E;
        border: 1px solid #666666;
    }
    
    QComboBox:on {
        background-color: #505050;
    }
    
    QComboBox::drop-down {
        border: none;
        width: 16px;
    }
    
    QComboBox::down-arrow {
        image: url(ico/down_arrow.png);
        width: 8px;
        height: 8px;
    }
    
    QComboBox QAbstractItemView {
        background-color: #2B2B2B;
        color: #EDEDED;
        selection-background-color: #3C3C3C;
        selection-color: #FFFFFF;
        border: 1px solid #555555;
    }
    
    QComboBox QAbstractItemView::item {
        min-height: 16px;
        padding: 2px;
    }
    
    QComboBox QAbstractItemView::item:hover {
        background-color: #444444;
    }
    
    QComboBox QAbstractItemView::item:selected {
        background: #3C3C3C;
    }
    
    /*按钮*/
    QPushButton {
        background-color: #343434;
        color: #EDEDED;
        border: 1px solid #555555;
        border-radius: 4px;
        padding: 5px 15px;
        min-width: 80px;
    }
    
    QPushButton:hover {
        background-color: #404040;
        border: 1px solid #666666;
    }
    
    QPushButton:pressed {
        background-color: #2A2A2A;
    }
    
    QPushButton:disabled {
        background-color: #2A2A2A;
        color: #666666;
        border: 1px solid #444444;
    }
    
    /*表格*/
    QTableWidget {
        background-color: #2B2B2B;
        color: #EDEDED;
        border: 1px solid #555555;
        gridline-color: #3E3E3E;
    }
    
    QTableWidget::item {
        padding: 2px;
        min-height: 16px;
        background-color: #2B2B2B;
    }
    
    QTableWidget::item:selected {
        background-color: #3C3C3C;
        color: #FFFFFF;
    }
    
    QTableWidget::item:focus {
        background-color: #3C3C3C;
        color: #FFFFFF;
    }
    
    QHeaderView::section {
        background-color: #3E3E3E;
        color: #EDEDED;
        border: 1px solid #555555;
        padding: 2px;
        min-height: 16px;
    }
    
    QTableCornerButton::section {
        background-color: #3E3E3E;
        border: 1px solid #555555;
    }
    
    /*滚动条*/
    QScrollBar:vertical {
        background-color: #2A2A2A;
        width: 12px;
        margin: 0;
    }
    
    QScrollBar::handle:vertical {
        background-color: #4A4A4A;
        min-height: 20px;
        border-radius: 6px;
    }
    
    QScrollBar::handle:vertical:hover {
        background-color: #555555;
    }
    
    QScrollBar:horizontal {
        background-color: #2A2A2A;
        height: 12px;
        margin: 0;
    }
    
    QScrollBar::handle:horizontal {
        background-color: #4A4A4A;
        min-width: 20px;
        border-radius: 6px;
    }
    
    QScrollBar::handle:horizontal:hover {
        background-color: #555555;
    }
    
    /*悬浮窗*/
    QDockWidget {
        background-color: #272727;
        color: #EDEDED;
        titlebar-close-icon: url(ico/close.png);
        titlebar-normal-icon: url(ico/restore.png);
    }
    
    QDockWidget::title {
        background-color: #222222;
        padding: 6px;
        spacing: 4px;
    }
    
    /*工具栏*/
    QToolBar {
        background: #202020;
        spacing: 6px;
        padding: 3px;
    }
    
    QToolBar QToolButton {
        background: #202020;
        border: 1px solid transparent;
        border-radius: 4px;
        padding: 5px;
    }
    
    QToolBar QToolButton:hover {
        background: #282828;
        border: 1px solid #3A3A3A;
    }
    
    /*菜单栏*/
    QMenuBar {
        background-color: #202020;
        color: #EDEDED;
    }
    
    QMenuBar::item {
        padding: 6px 10px;
        background: transparent;
    }
    
    QMenuBar::item:selected {
        background-color: #2A2A2A;
    }
    
    QMenu {
        background-color: #343434;
        color: #EDEDED;
        border: 1px solid #555555;
    }
    
    QMenu::item {
        padding: 6px 20px;
    }
    
    QMenu::item:selected {
        background-color: #3C3C3C;
    }
    
    /*标签页*/
    QTabWidget::pane {
        border: 1px solid #3A3A3A;
    }
    
    QTabBar::tab {
        background-color: #2A2A2A;
        color: #EDEDED;
        padding: 8px 12px;
        border: 1px solid #3A3A3A;
        border-bottom: none;
        margin-right: 2px;
    }
    
    QTabBar::tab:selected {
        background-color: #343434;
    }
    
    QTabBar::tab:hover {
        background-color: #303030;
    }
    
    /*分组框*/
    QGroupBox {
        border: 1px solid #3A3A3A;
        margin-top: 1.5ex;
        padding-top: 1.5ex;
    }
    
    QGroupBox::title {
        color: #EDEDED;
        subcontrol-origin: margin;
        subcontrol-position: top left;
        padding: 0 3px;
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
class SplashScreen(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()
        
        # 创建垂直布局
        layout = QtWidgets.QVBoxLayout()
        
        # 添加图片标签
        image_label = QtWidgets.QLabel(self)
        current_dir = Path(__file__).parent
        pixmap = QtGui.QPixmap(str(current_dir / "ico" / "bg37.jpg"))
        scaled_pixmap = pixmap.scaled(720, 480,  
                                    QtCore.Qt.KeepAspectRatio,
                                    QtCore.Qt.SmoothTransformation)
        image_label.setPixmap(scaled_pixmap)
        layout.addWidget(image_label)
        
        # 添加加载状态标签
        self.status_label = QtWidgets.QLabel("正在加载组件...", self)
        self.status_label.setAlignment(QtCore.Qt.AlignCenter)
        self.status_label.setStyleSheet("color: white; font-size: 14px;")
        layout.addWidget(self.status_label)
        
        # 添加进度条
        self.progress = QtWidgets.QProgressBar(self)
        self.progress.setStyleSheet("""
            QProgressBar {
                border: 2px solid grey;
                border-radius: 5px;
                text-align: center;
            }
            QProgressBar::chunk {
                background-color: #4CAF50;
            }
        """)
        layout.addWidget(self.progress)
        
        layout.setContentsMargins(20, 20, 20, 20)
        self.setLayout(layout)
        
        # 设置窗口属性
        self.setFixedSize(720, 480)
        self.setWindowFlags(QtCore.Qt.FramelessWindowHint | QtCore.Qt.WindowStaysOnTopHint)
        
        # 移动到屏幕中央
        screen = QtWidgets.QApplication.primaryScreen().geometry()
        self.move((screen.width() - self.width()) // 2,
                 (screen.height() - self.height()) // 2)
    
    def update_status(self, message: str, progress: int):
        """更新加载状态和进度"""
        self.status_label.setText(message)
        self.progress.setValue(progress)
        QtWidgets.QApplication.processEvents()
        
