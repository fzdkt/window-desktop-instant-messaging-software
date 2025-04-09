import sys
import os
from PyQt5.QtWidgets import QApplication

# from client_gui import ClientWindow
from client_gui import ClientWindow
from client_network import ClientNetwork

# 获取当前文件所在目录的父目录
# current_dir = os.path.dirname(os.path.abspath(__file__))
# project_root = os.path.dirname(current_dir)
# sys.path.append(project_root)


class ClientApp:
    def __init__(self):
        self.gui = ClientWindow()
        self.network = ClientNetwork("192.168.1.4", 8080, self.gui)
        self.gui.network = self.network  # 建立反向引用


if __name__ == "__main__":
    app = QApplication(sys.argv)
    client = ClientApp()
    client.gui.show()
    sys.exit(app.exec_())
