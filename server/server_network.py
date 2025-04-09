import socket
import json
import threading
from collections import defaultdict
from datetime import datetime
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs


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
        buffer = b""
        while True:
            try:
                data = client_socket.recv(4096)
                if not data:
                    break

                buffer += data

                # 处理文件元数据
                if b"<END_OF_JSON>" in buffer:
                    # 分离元数据和文件内容
                    meta_part, file_data = buffer.split(b"<END_OF_JSON>", 1)
                    meta = json.loads(meta_part.decode())

                    if meta["type"] == "file":
                        # 发送确认
                        client_socket.send(b"ACK")

                        # 准备接收文件
                        file_path = os.path.join("received_files", meta["file_name"])
                        os.makedirs("received_files", exist_ok=True)

                        received_size = 0
                        with open(file_path, "wb") as f:
                            f.write(file_data)
                            received_size += len(file_data)

                            # 继续接收剩余文件内容
                            while received_size < meta["file_size"]:
                                chunk = client_socket.recv(4096)
                                if not chunk:
                                    break
                                f.write(chunk)
                                received_size += len(chunk)

                        # 广播文件接收完成
                        notification = {
                            "type": "system",
                            "content": f"文件 {meta['file_name']} 已成功接收",
                            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        }
                        self.broadcast(notification, exclude=ip)

                        buffer = b""

                    else:
                        # 处理其他消息类型
                        self.handle_normal_message(client_socket, meta)
                        buffer = b""

            except Exception as e:
                print(f"处理客户端 {ip} 时出错: {str(e)}")
                break

    def route_message(self, message):
        # 添加字段验证
        required_fields = ["type", "sender_ip", "nickname", "timestamp", "content"]
        if message.get("type") != "message" or not all(
            field in message for field in required_fields
        ):
            print(f"丢弃无效消息: {message}")
            return

        # 将消息推送给网页端
        if hasattr(self, "push_web_message"):
            formatted_msg = json.dumps(
                {
                    "timestamp": message["timestamp"],
                    "nickname": message["nickname"],
                    "content": message["content"],
                    "source": "client",
                },
                ensure_ascii=False,
            )
            self.push_web_message(formatted_msg)

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


class WebHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/":
            self.send_response(200)
            self.send_header("Content-type", "text/html; charset=utf-8")
            self.end_headers()
            html_content = """
                <html>
                <head><title>杨鲲即时通讯网页聊天室</title></head>
                <body>
                    <div style="margin-bottom:10px;">
                        <input type="text" id="nickname" placeholder="输入昵称" style="width:200px;">
                        <button onclick="setNickname()">设置昵称</button>
                    </div>
                    <div id="messages" style="height:300px;overflow-y:scroll;border:1px solid #ccc;padding:10px;"></div>
                    <input type="text" id="message" style="width:70%;margin-top:10px;">
                    <button onclick="sendMessage()" style="width:25%;">发送</button>
                    <script>
                        let userNickname = '匿名用户';
                        
                        function setNickname() {
                            const input = document.getElementById('nickname');
                            userNickname = input.value || '匿名用户';
                            input.value = '';
                            alert('昵称已设置为: ' + userNickname);
                        }

                        function formatMessage(msgObj) {
                            const color = msgObj.source === 'web' ? 'blue' : 'green';
                            return `<span style="color:${color}">[${msgObj.timestamp}] ${msgObj.nickname}: ${msgObj.content}</span>`;
                        }

                        function updateMessages(msg) {
                            try {
                                const parsedMsg = JSON.parse(msg);
                                if (!parsedMsg.nickname.includes('/')) {
                                    parsedMsg.nickname = '系统消息';
                                }
                                const div = document.getElementById('messages');
                                const parsedMsg = JSON.parse(msg);
                                div.innerHTML += '<div>' + formatMessage(parsedMsg) + '</div>';
                                div.scrollTop = div.scrollHeight;
                            } catch(e) {
                                console.error('消息解析错误:', e);
                            }
                            
                        }
                        
                        function sendMessage() {
                            const input = document.getElementById('message');
                            const formData = new URLSearchParams({
                                message: input.value,
                                nickname: userNickname
                            });
                            
                            fetch('/send', {
                                method: 'POST',
                                body: formData
                            }).then(res => {
                                if(res.ok) input.value = '';
                            });
                        }
                        
                        // 实时消息推送
                        const eventSource = new EventSource('/stream');
                        eventSource.onmessage = function(e) {
                            updateMessages(e.data);
                        };
                    </script>
                </body>
                </html>
            """
            self.wfile.write(html_content.encode("utf-8"))

        elif self.path == "/stream":
            self.send_response(200)
            self.send_header("Content-type", "text/event-stream")
            self.send_header("Cache-Control", "no-cache")
            self.end_headers()
            # 添加消息队列监听
            while True:
                msg = self.server.network.get_web_message()
                if msg:
                    try:
                        self.wfile.write(f"data: {msg}\n\n".encode("utf-8"))
                        self.wfile.flush()
                    except BrokenPipeError:
                        break
        else:
            self.send_error(404)

    def do_POST(self):
        if self.path == "/send":
            content_length = int(self.headers["Content-Length"])
            post_data = parse_qs(self.rfile.read(content_length).decode())

            message = post_data.get("message", [""])[0]
            nickname = post_data.get("nickname", ["匿名用户"])[0]
            if message:
                # 生成网页消息格式
                web_message = {
                    "type": "message",
                    "sender_ip": "web_user",
                    "nickname": f"网页用户/{nickname}",
                    "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "content": message,
                    "receiver": "all",
                    "source": "web",  # 新增来源标识
                }
                # 通过服务器广播
                self.server.network.broadcast_message(web_message)

            self.send_response(200)
            self.end_headers()


class EnhancedServerNetwork(ServerNetwork):
    def __init__(self, *args):
        super().__init__(*args)
        self.web_message_queue = []
        self.web_message_lock = threading.Lock()
        # 启动HTTP服务器
        self.start_web_server(8081)  # 使用不同端口

    def start_web_server(self, port):
        def run_server():
            server = ThreadingHTTPServer(("0.0.0.0", port), WebHandler)
            server.network = self  # 绑定网络实例
            server.serve_forever()

        web_thread = threading.Thread(target=run_server, daemon=True)
        web_thread.start()

    # 线程安全的广播方法
    def broadcast_message(self, message):
        with threading.Lock():
            # 推送到网页消息队列
            if message.get("type") == "message":
                formatted_msg = json.dumps(
                    {
                        "timestamp": message["timestamp"],
                        "nickname": message["nickname"],
                        "content": message["content"],
                        "source": "client" if message.get("source") != "web" else "web",
                    },
                    ensure_ascii=False,
                )
                self.push_web_message(formatted_msg)

            # 客户端发送逻辑
            for ip, client in list(self.clients.items()):
                try:
                    data = json.dumps(message, ensure_ascii=False).encode("utf-8")
                    client["socket"].send(data)
                except Exception as e:
                    print(f"网页消息发送失败至 {ip}: {str(e)}")
                    del self.clients[ip]

    def push_web_message(self, msg):
        with self.web_message_lock:
            self.web_message_queue.append(msg)

    def get_web_message(self):
        with self.web_message_lock:
            return self.web_message_queue.pop(0) if self.web_message_queue else None
