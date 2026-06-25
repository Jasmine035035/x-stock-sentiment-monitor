"""发送模块：把报告发到飞书群"""

import os
import requests
from dotenv import load_dotenv

load_dotenv()

FEISHU_WEBHOOK_URL = os.getenv("FEISHU_WEBHOOK_URL")


def post_to_feishu(message: str):
    """发送一段文字到飞书群"""
    if not FEISHU_WEBHOOK_URL:
        print("❌ 缺少飞书Webhook配置，请检查.env里的FEISHU_WEBHOOK_URL")
        return None

    payload = {
        "msg_type": "text",
        "content": {
            "text": message
        }
    }

    try:
        resp = requests.post(FEISHU_WEBHOOK_URL, json=payload)
        result = resp.json()
        if result.get("code") == 0:
            print("✅ 飞书发送成功")
        else:
            print(f"❌ 飞书发送失败: {result}")
        return result
    except Exception as e:
        print(f"❌ 发送时出错: {e}")
        return None