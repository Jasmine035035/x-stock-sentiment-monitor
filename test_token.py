import os
import tweepy
from dotenv import load_dotenv

load_dotenv()
token = os.getenv("X_BEARER_TOKEN")

print("读取到的token前10位:", token[:10] if token else "没有读到token")

client = tweepy.Client(bearer_token=token)

try:
    user = client.get_user(username="jimcramer")
    print("✅ Token有效，查询到用户:", user.data)
except Exception as e:
    print("❌ Token无效或权限不足:", e)