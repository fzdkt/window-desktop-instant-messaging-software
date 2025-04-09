import os
from datetime import datetime

def format_message(sender_ip, nickname, content):
    return f"[{datetime.now().strftime('%H:%M:%S')}] {nickname}({sender_ip}): {content}"

def format_user_entry(ip, nickname):
    return f"{nickname} ({ip})" if nickname else f"未命名用户 ({ip})"

def validate_ip(ip):
    parts = ip.split('.')
    if len(parts) != 4:
        return False
    for part in parts:
        if not part.isdigit() or not 0 <= int(part) <= 255:
            return False
    return True