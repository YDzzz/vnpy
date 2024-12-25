import sys
from PySide6 import QtWidgets, QtGui, QtCore

class MainWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("主窗口")
        self.resize(800, 600)

class SplashScreen(QtWidgets.QWidget):
    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        
        # 创建标签并添加图片
        label = QtWidgets.QLabel(self)
        pixmap = QtGui.QPixmap(r"g:\code\vnpy\my_test\bg37.jpg")
        scaled_pixmap = pixmap.scaled(720, 480,  # 修改为720*480
                                    QtCore.Qt.IgnoreAspectRatio,
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
        
        # 显示窗口
        self.show()
        
        # 创建定时器，3秒后关闭启动画面并显示主窗口
        QtCore.QTimer.singleShot(3000, self.switch_to_main)
    
    def switch_to_main(self):
        self.close()  # 关闭启动画面
        self.main_window.show()  # 显示主窗口

if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    main_window = MainWindow()
    splash = SplashScreen(main_window)
    sys.exit(app.exec())