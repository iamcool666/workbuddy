# -*- coding: utf-8 -*-
import os
import urllib.request
import urllib.parse

def send(title, content):
    """
    通用 Server 酱/ Bark 推送接口（如果在 Secrets 中配置了 SERVERCHAN_KEY）
    """
    sckey = os.getenv("SERVERCHAN_KEY")
    if not sckey:
        return
        
    url = f"https://sctapi.ftqq.com/{sckey}.send"
    data = urllib.parse.urlencode({"title": title, "desp": content}).encode("utf-8")
    req = urllib.request.Request(url, data=data, method="POST")
    try:
        urllib.request.urlopen(req, timeout=10)
        print("📱 消息已成功推送至 Server 酱")
    except Exception as e:
        print(f"⚠️ 消息推送失败: {e}")
