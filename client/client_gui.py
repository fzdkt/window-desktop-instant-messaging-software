from PyQt5.QtCore import pyqtSignal, Qt, QObject
from PyQt5.QtWidgets import (
    QMainWindow,
    QTextEdit,
    QLineEdit,
    QPushButton,
    QFileDialog,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QInputDialog,
)


class MessageHandler(QObject):
    network_message = pyqtSignal(dict)


class ClientWindow(QMainWindow):
    append_message_signal = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.setWindowTitle("杨鲲即时通讯（客户端）")
        self.setGeometry(100, 100, 800, 600)

        self.msg_handler = MessageHandler()
        self.msg_handler.network_message.connect(self._handle_network_message)

        # 消息显示区域
        self.messages_display = QTextEdit(self)
        self.messages_display.setGeometry(20, 20, 500, 400)
        self.messages_display.setReadOnly(True)

        # 用户列表
        self.user_list = QListWidget(self)
        self.user_list.setGeometry(550, 20, 200, 400)

        # 控制区域
        self.nickname_btn = QPushButton("设置昵称", self)
        self.nickname_btn.setGeometry(550, 440, 200, 30)

        self.message_input = QLineEdit(self)
        self.message_input.setGeometry(20, 440, 400, 30)

        self.send_btn = QPushButton("发送", self)
        self.send_btn.setGeometry(440, 440, 80, 30)

        self.file_btn = QPushButton("发送文件", self)
        self.file_btn.setGeometry(20, 480, 100, 30)

        self.mode_btn = QPushButton("群聊模式", self)
        self.mode_btn.setGeometry(550, 480, 200, 30)

        # 状态栏
        self.status_label = QLabel("状态：未连接", self)
        self.status_label.setGeometry(20, 520, 500, 20)

        # 文件对话框
        self.file_dialog = QFileDialog()

        # 绑定双击事件
        self.user_list.itemDoubleClicked.connect(self.on_user_double_click)

        # 连接信号
        self.append_message_signal.connect(self._append_message)

    def _handle_network_message(self, message):
        """处理来自网络的消息"""
        try:
            if message["type"] == "user_list":
                self._update_user_list(message["users"])
            elif message["type"] == "message":
                self._show_received_message(message)
        except KeyError as e:
            print(f"无效消息格式: {str(e)}")

    def _update_user_list(self, users):
        """更新用户列表"""
        self.user_list.clear()
        for user in users:
            item = QListWidgetItem(f"{user['nickname']} ({user['ip']})")
            self.user_list.addItem(item)

    def _show_received_message(self, message):
        try:
            # 获取带默认值的字段
            sender_ip = message.get("sender_ip", "未知IP")
            nickname = message.get("nickname", "未知用户")
            timestamp = message.get(
                "timestamp", datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            )
            content = message.get("content", "空消息")

            # 判断是否是自己发送的
            is_self = hasattr(self, "network") and sender_ip == self.network.host
            display_name = "我" if is_self else nickname

            # 构造显示文本
            display_text = (
                f"[{timestamp}] {display_name}({sender_ip})\n"
                f"{content}\n"
                "------------------------"
            )
            self.append_message_signal.emit(display_text)
        except Exception as e:
            print(f"消息显示错误: {str(e)}")

    def on_user_double_click(self, item):
        selected_user = item.text().split(" (")[0]
        self.mode_btn.setText(f"私聊：{selected_user}")

    # 线程安全的消息追加方法
    def _append_message(self, text):
        self.messages_display.append(text)
        scrollbar = self.messages_display.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

        with open("chat_history.log", "a", encoding="utf-8") as f:
            f.write(text + "\n")
