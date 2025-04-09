import sys
from PyQt5.QtWidgets import QApplication
from server_gui import ServerWindow
from server_network import ServerNetwork

class ServerApp:
    def __init__(self):
        self.gui = ServerWindow()
        self.network = ServerNetwork("0.0.0.0", 8080, self.gui)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    server = ServerApp()
    server.gui.show()
    sys.exit(app.exec_())