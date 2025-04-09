import sys
from PyQt5.QtWidgets import QApplication
from client_gui import ClientWindow
from client_network import ClientNetwork


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
