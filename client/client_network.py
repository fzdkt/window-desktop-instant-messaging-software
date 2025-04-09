import socket
import json
import threading
from datetime import datetime
from PyQt5.QtWidgets import QMessageBox, QListWidgetItem, QInputDialog
import os


class ClientNetwork:
    def __init__(self, host, port, gui):
        self.host = host
        self.port = port
        self.gui = gui
        self.nickname = "未命名用户"
        self.current_mode = "public"
        self.target_user = None
        self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        # 连接服务器
        try:
            self.client_socket.connect((self.host, self.port))
            self.gui.status_label.setText("状态：已连接")
        except:
            QMessageBox.critical(self.gui, "错误", "无法连接服务器")
            return

        # 绑定事件
        self.gui.send_btn.clicked.connect(self.send_message)
        self.gui.file_btn.clicked.connect(self.send_file)
        self.gui.nickname_btn.clicked.connect(self.set_nickname)

        self.gui.msg_handler.network_message.connect(self.handle_message)

        # 启动接收线程
        self.receive_thread = threading.Thread(target=self.receive_data, daemon=True)
        self.receive_thread.start()

    def set_nickname(self):
        nickname, ok = QInputDialog.getText(self.gui, "设置昵称", "请输入昵称:")
        if ok and nickname:
            self.nickname = nickname
            update_data = {
                "type": "user_update",
                "nickname": nickname,
                "ip": self.host,  # 需要包含用户IP用于标识
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            }
            self.client_socket.send(json.dumps(update_data).encode())
            # self.send_system_message({"type": "user_update", "nickname": nickname})

    def send_message(self):
        message = self.gui.message_input.text()
        if not message:
            return

        message_data = {
            "type": "message",
            "sender_ip": self.host,
            "nickname": self.nickname,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "content": message,
            "receiver": "all" if self.current_mode == "public" else self.target_user,
        }
        # 本地立即显示逻辑
        self.show_local_message(message_data)

        self.client_socket.send(json.dumps(message_data).encode())
        self.gui.message_input.clear()

    # 立即显示自己发送的消息
    def show_local_message(self, message_data):
        display_text = f"[我] {message_data['timestamp']}\n{message_data['content']}\n"
        self.gui.messages_display.append(display_text)

    def send_file(self):
        file_path, _ = self.gui.file_dialog.getOpenFileName()
        if not file_path:
            return

        # 发送文件元数据
        file_data = {
            "type": "file",
            "sender_ip": self.host,
            "nickname": self.nickname,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "file_name": file_path.split("/")[-1],
            "file_size": os.path.getsize(file_path),
            "receiver": "all" if self.current_mode == "public" else self.target_user,
        }

        self.client_socket.send(json.dumps(file_data).encode())

        # 发送文件内容
        with open(file_path, "rb") as f:
            while True:
                chunk = f.read(1024)
                if not chunk:
                    break
                self.client_socket.send(chunk)

    def receive_data(self):
        while True:
            try:
                data = self.client_socket.recv(1024)
                if not data:
                    break

                # 处理不同类型的数据
                if data.startswith(b"{"):
                    message = json.loads(data.decode())
                    self.gui.msg_handler.network_message.emit(message)
                    # self.handle_message(message)
                else:
                    self.handle_file(data)

                # self.gui.msg_handler.network_message.emit(message)

            except Exception as e:
                # QMessageBox.critical(self.gui, "错误", f"连接错误: {str(e)}")
                # self.gui.append_message_signal.emit(f"[系统] 连接异常: {str(e)}")
                error_msg = f"连接错误: {str(e)}"
                self.gui.append_message_signal.emit(f"[系统] {error_msg}")
                break

    def handle_message(self, message):
        try:
            # 验证消息类型和必要字段
            if message.get("type") == "user_list":
                self._handle_user_list(message.get("users", []))

            elif message.get("type") == "message":
                self._handle_chat_message(message)

        except Exception as e:
            print(f"处理消息错误: {str(e)}")

    def _handle_user_list(self, users):
        """处理用户列表更新"""
        self.gui.user_list.clear()
        for user in users:
            item = QListWidgetItem(
                f"{user.get('nickname', '未知用户')} ({user.get('ip', '未知IP')})"
            )
            self.gui.user_list.addItem(item)

    def _handle_chat_message(self, message):
        """处理聊天消息"""
        required_fields = ["sender_ip", "content", "timestamp"]
        if not all(field in message for field in required_fields):
            raise ValueError("消息缺少必要字段")

        is_self = message["sender_ip"] == self.host
        display_name = "我" if is_self else message.get("nickname", "未知用户")

        display_text = (
            f"[{message['timestamp']}] {display_name}({message['sender_ip']})\n"
            f"{message['content']}\n"
            "------------------------"
        )
        self.gui.append_message_signal.emit(display_text)

        print(f"收到来自 {message['sender_ip']} 的消息: {message['content'][:20]}...")

    # def handle_message(self, message):
    #     if message["type"] == "user_list":
    #         self.gui.user_list.clear()
    #         for user in message["users"]:
    #             item = QListWidgetItem(f"{user['nickname']} ({user['ip']})")
    #             self.gui.user_list.addItem(item)

    #     elif message["type"] == "message":
    #         is_self = message["sender_ip"] == self.host
    #         display_name = "我" if is_self else message["nickname"]
    #         # 添加完整显示格式
    #         display_text = (
    #             f"[{message['timestamp']}] {display_name}({message['sender_ip']})\n"
    #             f"{message['content']}\n"
    #             "------------------------"
    #         )
    #         # sender_type = (
    #         #     "我" if message["sender_ip"] == self.host else message["nickname"]
    #         # )  # 添加消息来源
    #         # display_text = f"[{message['timestamp']}] {message['nickname']}({message['sender_ip']})\n{message['content']}\n"
    #         self.gui.messages_display.append(display_text)

    #     print(
    #         f"Received message from {message['sender_ip']}: {message['content'][:20]}..."
    #     )

    def handle_file(self, data):
        # 文件处理逻辑
        pass
