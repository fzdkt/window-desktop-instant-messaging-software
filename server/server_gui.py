from PyQt5.QtWidgets import QMainWindow, QTextEdit, QLabel


class ServerWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("服务器控制台")
        self.setGeometry(100, 100, 600, 400)

        self.log_display = QTextEdit(self)
        self.log_display.setGeometry(20, 20, 560, 300)
        self.log_display.setReadOnly(True)

        self.status_label = QLabel("服务器状态：运行中", self)
        self.status_label.setGeometry(20, 330, 200, 30)

    def log_message(self, message):
        formatted_msg = f"[{datetime.now().strftime('%H:%M:%S')}] {message}"
        self.log_display.append(formatted_msg)
