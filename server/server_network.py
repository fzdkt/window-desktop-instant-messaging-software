import socket
import json
import threading
from collections import defaultdict


class ServerNetwork:
    def __init__(self, host, port, gui):
        self.host = host
        self.port = port
        self.gui = gui
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.clients = defaultdict(dict)  # {ip: {"socket": obj, "nickname": str}}

        # 绑定服务器
        self.server_socket.bind((self.host, self.port))
        self.server_socket.listen(5)

        # 启动接受连接线程
        self.accept_thread = threading.Thread(
            target=self.accept_connections, daemon=True
        )
        self.accept_thread.start()

    def accept_connections(self):
        while True:
            client_socket, addr = self.server_socket.accept()
            ip = addr[0]
            self.clients[ip]["socket"] = client_socket
            self.clients[ip]["nickname"] = "新用户"

            # 启动客户端处理线程
            client_thread = threading.Thread(
                target=self.handle_client, args=(client_socket, ip), daemon=True
            )
            client_thread.start()

            # 更新用户列表
            self.broadcast_user_list()

    def validate_message(self, message):
        type_map = {
            "message": ["sender_ip", "nickname", "timestamp", "content"],
            "file": ["file_name", "file_size"],
            "user_update": ["nickname", "ip"],
        }
        if message.get("type") not in type_map:
            return False
        return all(field in message for field in type_map[message["type"]])

    def handle_client(self, client_socket, ip):

        while True:
            try:
                data = client_socket.recv(1024)
                if not data:
                    break

                try:
                    message = json.loads(data.decode())
                    if not self.validate_message(message):
                        continue
                    if message["type"] == "user_update":
                        self.clients[ip]["nickname"] = message["nickname"]
                        self.broadcast_user_list()

                    elif message["type"] == "message":
                        self.route_message(message)

                    elif message["type"] == "file":
                        self.handle_file(message, client_socket)
                except json.JSONDecodeError:
                    print(f"无效JSON数据: {data[:50]}...")

            except:
                break

        # 客户端断开处理
        del self.clients[ip]
        self.broadcast_user_list()
        client_socket.close()

    def route_message(self, message):
        # 添加字段验证
        required_fields = ["type", "sender_ip", "nickname", "timestamp", "content"]
        if message.get("type") != "message" or not all(
            field in message for field in required_fields
        ):
            print(f"丢弃无效消息: {message}")
            return

        # 广播给所有客户端（含发送者）
        for ip, client in list(self.clients.items()):  # 使用list避免字典改变
            try:
                client["socket"].send(json.dumps(message).encode())
                print(f"成功发送至 {ip}")
            except Exception as e:
                print(f"发送失败至 {ip}，错误：{str(e)}")
                del self.clients[ip]

    # def route_message(self, message):
    #     if message["type"] not in ["message", "file", "user_update"]:
    #         return
    #     self.message_history.append(message)
    #     if message["receiver"] == "all":
    #         for client in self.clients.items():
    #             try:
    #                 client["socket"].send(json.dumps(message).encode())
    #             except:
    #                 self.remove_disconnected_client(client)
    #             # if ip != message["sender_ip"]:
    #             # client["socket"].send(json.dumps(message).encode())
    #     else:
    #         target_ip = next(
    #             (
    #                 ip
    #                 for ip, info in self.clients.items()
    #                 if info["nickname"] == message["receiver"]
    #             ),
    #             None,
    #         )
    #         if target_ip:
    #             self.clients[target_ip]["socket"].send(json.dumps(message).encode())

    #     # 日志信息
    #     print(
    #         f"Broadcasting to {len(self.clients)} clients: {message['content'][:20]}..."
    #     )

    # 处理断开连接的客户端
    def remove_disconnected_client(self, client):
        for ip, info in list(self.clients.items()):
            if info["socket"] == client["socket"]:
                del self.clients[ip]
                self.broadcast_user_list()
                break

    def broadcast_user_list(self):
        user_list = [
            {"ip": ip, "nickname": info["nickname"]}
            for ip, info in self.clients.items()
        ]
        message = {"type": "user_list", "users": user_list}
        for client in self.clients.values():
            client["socket"].send(json.dumps(message).encode())
