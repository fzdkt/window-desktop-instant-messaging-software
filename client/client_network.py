import socket
import json
import threading
from datetime import datetime
from PyQt5.QtWidgets import QMessageBox, QListWidgetItem, QInputDialog
import os


class ClientNetwork:
    def __init__(self, host, port, gui):

        self.gui = gui
        self.host = host
        self.port = port
        self.nickname = "未命名用户"
        self.current_mode = "public"
        self.target_user = None
        self.client_socket = None
        # self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

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

        self.connect_to_server()

    # 通用连接方法
    def connect_to_server(self):
        try:
            if self.client_socket:
                # 关闭旧连接
                try:
                    self.client_socket.shutdown(socket.SHUT_RDWR)
                    self.client_socket.close()
                except:
                    pass
            # 创建新连接
            self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.client_socket.settimeout(10)
            self.client_socket.connect((self._host, self._port))

            # 发送初始握手包
            self.client_socket.send(b"HELO")
            ack = self.client_socket.recv(4)
            if ack != b"ACK":
                raise ConnectionError("握手失败")

            # 重启接收线程
            if hasattr(self, "receive_thread"):
                self.receive_thread.join(0.1)
            self.receive_thread = threading.Thread(
                target=self.receive_data, daemon=True
            )
            self.receive_thread.start()

            self.gui.status_label.setText("状态：已连接")
            return True
        except Exception as e:
            self.gui.append_message_signal.emit(f"[错误] 连接失败: {str(e)}")
            return False

    def reconnect_to_server(self, new_host, new_port):
        """重新连接到新服务器"""
        self._host = new_host
        self._port = new_port

        # 保存旧socket引用
        old_socket = self.client_socket

        # 尝试连接新服务器
        if self.connect_to_server():
            # 关闭旧连接
            if old_socket:
                try:
                    old_socket.shutdown(socket.SHUT_RDWR)
                    old_socket.close()
                except:
                    pass
            # 发送用户更新信息
            self.send_user_update()
        else:
            raise ConnectionError("无法连接到新服务器")

    def send_user_update(self):
        """连接成功后更新用户信息"""
        update_data = {
            "type": "user_update",
            "nickname": self.nickname,
            "ip": self.host,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }
        self.client_socket.send(json.dumps(update_data).encode())

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
        message = self.gui.message_input.text().strip()
        if not message:
            # self.gui.append_message_signal.emit("[系统] 消息内容不能为空！")
            # self.gui.message_input.clear()
            self.gui._show_status_message("⚠️ 消息内容不能为空！")  # 使用状态栏提示
            self.gui.message_input.clear()
            return
        if not self.client_socket or not self._is_connected():
            self.gui.append_message_signal.emit("[系统] 正在尝试重新连接...")
            self.connect_to_server()
        try:

            message_data = {
                "type": "message",
                "sender_ip": self.host,
                "nickname": self.nickname,
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "content": message,
                "receiver": (
                    "all" if self.current_mode == "public" else self.target_user
                ),
            }
            # 本地立即显示逻辑
            self.show_local_message(message_data)

            self.client_socket.send(json.dumps(message_data).encode("utf-8"))
        except Exception as e:
            self.gui.append_message_signal.emit(f"[错误] 发送失败: {str(e)}")
            self.reconnect_server()
        self.gui.message_input.clear()

    # 添加连接状态的判断
    def _is_connected(self):
        try:
            # 发送空数据测试连接状态
            self.client_socket.send(b"")
            return True
        except (OSError, AttributeError):
            return False

    # 立即显示自己发送的消息
    def show_local_message(self, message_data):
        display_text = (
            f"[{message_data['timestamp']}] 我({self.host})\n"
            f"{message_data['content']}\n"
            "------------------------"
        )
        self.gui.append_message_signal.emit(display_text)

    def send_file(self):
        try:
            file_path, _ = self.gui.file_dialog.getOpenFileName()
            if not file_path:
                return

            # 发送文件元数据
            file_data = {
                "type": "file",
                "sender_ip": self.host,
                "nickname": self.nickname,
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "file_name": os.path.basename(file_path),
                "file_size": os.path.getsize(file_path),
                "receiver": (
                    "all" if self.current_mode == "public" else self.target_user
                ),
            }

            # 添加结束标记
            meta_data = json.dumps(file_data) + "<END_OF_JSON>"
            self.client_socket.send(meta_data.encode())

            # 等待服务器确认
            ack = self.client_socket.recv(3)  # 接收简单的ACK确认
            if ack != b"ACK":
                raise Exception("服务器未确认接收")

            # 发送文件内容（分块发送）
            with open(file_path, "rb") as f:
                total_sent = 0
                while total_sent < file_data["file_size"]:
                    chunk = f.read(4096)  # 增大块大小到4KB
                    if not chunk:
                        break
                    self.client_socket.sendall(chunk)  # 使用sendall确保完整发送
                    total_sent += len(chunk)
                    # 更新发送进度（可选）
                    progress = int((total_sent / file_data["file_size"]) * 100)
                    self.gui.append_message_signal.emit(f"[进度] 已发送 {progress}%")

            self.gui.append_message_signal.emit(
                f"[成功] 文件 {file_data['file_name']} 已发送"
            )
        except Exception as e:
            print(f"文件发送失败: {str(e)}")
            self.gui.append_message_signal.emit(f"[错误] 文件发送失败: {str(e)}")
            # 重建连接
            self.reconnect_server()

    # 重新连接服务器
    def reconnect_server(self):
        try:
            self.client_socket.close()
            self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.client_socket.connect((self.host, self.port))
            self.gui.status_label.setText("状态：已重新连接")
        except Exception as e:
            self.gui.append_message_signal.emit(
                f"[严重错误] 无法重新连接服务器: {str(e)}"
            )

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

    # 处理用户列表更新
    def _handle_user_list(self, users):
        self.gui.user_list.clear()
        for user in users:
            item = QListWidgetItem(
                f"{user.get('nickname', '未知用户')} ({user.get('ip', '未知IP')})"
            )
            self.gui.user_list.addItem(item)

    # 处理聊天消息
    def _handle_chat_message(self, message):
        required_fields = ["sender_ip", "content", "timestamp"]
        if not all(field in message for field in required_fields):
            raise ValueError("消息缺少必要字段")

        is_self = message["sender_ip"] == self.host
        display_name = (
            message["sender_ip"] if is_self else message.get("nickname", "未知用户")
        )

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

    # 发送刷新用户列表请求
    def send_refresh_request(self):
        request = {
            "type": "get_user_list",
            "sender_ip": self.host,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }
        try:
            self.client_socket.send(json.dumps(request).encode())
            print("[DEBUG] 已发送用户列表刷新请求")
        except Exception as e:
            print(f"发送刷新请求失败: {str(e)}")
            self.gui.append_message_signal.emit("[系统] 刷新用户列表失败")
