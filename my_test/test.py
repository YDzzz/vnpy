import sys
from PySide6 import QtWidgets, QtGui, QtCore
from pathlib import Path
from time import sleep


class MainWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("主窗口")
        self.resize(800, 600)

class SplashScreen(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()
        
        # 创建标签并添加图片
        label = QtWidgets.QLabel(self)
        current_dir = Path(__file__).parent
        pixmap = QtGui.QPixmap(str(current_dir / "bg37.jpg"))
        scaled_pixmap = pixmap.scaled(720, 480,  
                                    QtCore.Qt.KeepAspectRatio,
                                    QtCore.Qt.SmoothTransformation)
        label.setPixmap(scaled_pixmap)
        
        # 设置固定窗口大小为720*480
        self.setFixedSize(720, 480)
        
        # 移除窗口边框并置顶
        self.setWindowFlags(QtCore.Qt.FramelessWindowHint | QtCore.Qt.WindowStaysOnTopHint)
        
        # 移动到屏幕中央
        screen = QtWidgets.QApplication.primaryScreen().geometry()
        self.move((screen.width() - self.width()) // 2,
                 (screen.height() - self.height()) // 2)
        
        # 创建定时器
        self.timer = QtCore.QTimer(self)
        self.timer.timeout.connect(self.close_splash)
        self.timer.start(3000)  # 3000毫秒 = 3秒
        
        # 显示窗口
        self.show()
        
    def close_splash(self):
        self.timer.stop()
        self.close()
        main_window.show()

if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    main_window = MainWindow()
    splash = SplashScreen()
    sleep(3)
    sys.exit(app.exec())