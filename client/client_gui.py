from PyQt5 import QtCore, QtGui
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
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
)
from PyQt5.QtGui import QIntValidator
from datetime import datetime
import time


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
        self.user_list.setGeometry(550, 40, 200, 380)

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

        # 服务器配置区域
        self.server_config_btn = QPushButton("服务器配置", self)
        self.server_config_btn.setGeometry(20, 560, 100, 30)
        self.server_config_btn.clicked.connect(self.show_server_config_dialog)

        # 当前服务器状态显示
        self.current_server_label = QLabel("当前服务器：未连接", self)
        self.current_server_label.setGeometry(130, 565, 300, 20)

        # 刷新按钮
        self.refresh_btn = QPushButton("刷新用户", self)
        self.refresh_btn.setGeometry(550, 20, 200, 20)
        self.refresh_btn.clicked.connect(self._on_refresh_users_clicked)

        # 状态栏
        self.status_label = QLabel("状态：未连接", self)
        self.status_label.setGeometry(20, 520, 500, 20)

        # 文件对话框
        self.file_dialog = QFileDialog()

        # 绑定双击事件
        self.user_list.itemDoubleClicked.connect(self.on_user_double_click)

        # 连接历史
        self.connection_history = []

        # 连接信号
        self.append_message_signal.connect(self._append_message)

    # 处理来自网络的消息
    def _handle_network_message(self, message):
        try:
            if message["type"] == "user_list":
                self._update_user_list(message["users"])
            elif message["type"] == "message":
                self._show_received_message(message)
        except KeyError as e:
            print(f"无效消息格式: {str(e)}")

    # 更新用户列表
    def _update_user_list(self, users):
        self.user_list.clear()
        for user in users:
            item = QListWidgetItem(f"{user['nickname']} ({user['ip']})")
            self.user_list.addItem(item)

    def _show_received_message(self, message):
        if message.get("type") == "file":
            content = f"📁文件: {message['file_name']} ({message['file_size']}字节)"
        try:
            # 获取带默认值的字段
            sender_ip = message.get("sender_ip", "未知IP")
            nickname = message.get("nickname", "未知用户")
            timestamp = message.get(
                "timestamp", datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            )
            content = message.get("content", "空消息")
            # 处理网页用户显示
            if message.get("source") == "web":
                display_name = f"🌐{nickname.split('/')[-1]}"
            else:
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

    # 刷新用户列表按钮点击处理
    def _on_refresh_users_clicked(self):
        try:
            if hasattr(self, "network"):
                self.network.send_refresh_request()
                self._show_status_message("正在刷新用户列表...", "blue")
            else:
                self.append_message_signal.emit("[系统] 尚未连接到服务器")
        except Exception as e:
            print(f"刷新操作异常: {str(e)}")
            self.append_message_signal.emit("[系统] 刷新操作异常")

    def _show_status_message(self, text, color="red"):
        self.status_label.setText(text)
        self.status_label.setStyleSheet(f"color: {color};")

        # 3秒后恢复默认状态
        QtCore.QTimer.singleShot(
            3000, lambda: self.status_label.setText("状态：已连接")
        )

    def show_server_config_dialog(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("服务器配置")
        dialog.setFixedSize(300, 150)

        layout = QVBoxLayout(dialog)

        # 地址输入
        addr_layout = QHBoxLayout()
        addr_label = QLabel("服务器地址:")
        self.addr_input = QLineEdit("192.168.1.4")
        addr_layout.addWidget(addr_label)
        addr_layout.addWidget(self.addr_input)

        # 端口输入
        port_layout = QHBoxLayout()
        port_label = QLabel("端口号:")
        self.port_input = QLineEdit("8080")
        self.port_input.setValidator(QIntValidator(1, 65535))  # 限制端口范围
        port_layout.addWidget(port_label)
        port_layout.addWidget(self.port_input)

        # 确认按钮
        confirm_btn = QPushButton("确认连接")
        confirm_btn.clicked.connect(lambda: self.apply_server_config(dialog))

        layout.addLayout(addr_layout)
        layout.addLayout(port_layout)
        layout.addWidget(confirm_btn)

        dialog.exec_()

    def apply_server_config(self, dialog):
        new_host = self.addr_input.text()
        new_port = self.port_input.text()

        if not new_host or not new_port.isdigit():
            QMessageBox.warning(self, "错误", "请输入有效的地址和端口")
            return

        try:
            # 尝试连接新服务器
            self.network.reconnect_to_server(new_host, int(new_port))
            dialog.close()
            self.current_server_label.setText(f"当前服务器：{new_host}:{new_port}")
            self._show_status_message("连接成功", "green")
            self.connection_history.append(f"{new_host}:{new_port}")
        except Exception as e:
            self._show_status_message(f"连接失败: {str(e)}", "red")

    def reconnect_to_server(self, new_host, new_port, retry=3):
        for i in range(retry):
            if self.connect_to_server():
                return True
            time.sleep(1)
        raise ConnectionError(f"连接失败，已重试{retry}次")
