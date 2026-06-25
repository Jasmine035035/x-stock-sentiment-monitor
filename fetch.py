"""抓取模块：从X API拉取指定用户的最近推文"""

import os
import time
from datetime import datetime, timedelta, timezone

import tweepy
from dotenv import load_dotenv

load_dotenv()
BEARER_TOKEN = os.getenv("X_BEARER_TOKEN")

if not BEARER_TOKEN:
    raise RuntimeError("未找到 X_BEARER_TOKEN，请检查 .env 文件")

client = tweepy.Client(bearer_token=BEARER_TOKEN, wait_on_rate_limit=True)

_user_id_cache = {}


def get_user_id(username: str):
    """根据用户名查user_id，带缓存，减少API调用次数"""
    if username in _user_id_cache:
        return _user_id_cache[username]

    try:
        user = client.get_user(username=username)
    except Exception as e:
        print(f"❌ 查询用户 {username} 失败: {e}")
        return None

    uid = user.data.id if user.data else None
    if uid is None:
        print(f"⚠️ 找不到用户: {username}（可能改名/账号不存在）")
    _user_id_cache[username] = uid
    return uid


def fetch_recent_tweets(username: str, days: int = 1, max_results: int = 20):
    """抓取某用户最近N天的原创推文（排除转发和回复）"""
    user_id = get_user_id(username)
    if not user_id:
        return []

    start_time = (datetime.now(timezone.utc) - timedelta(days=days)).strftime(
        "%Y-%m-%dT%H:%M:%SZ"
    )

    try:
        tweets = client.get_users_tweets(
            id=user_id,
            max_results=max_results,
            start_time=start_time,
            tweet_fields=["created_at", "public_metrics", "lang"],
            exclude=["retweets", "replies"],
        )
    except tweepy.TooManyRequests:
        print(f"⏳ 触发限流，等待15分钟后重试 ({username}) ...")
        time.sleep(900)
        return fetch_recent_tweets(username, days, max_results)
    except Exception as e:
        print(f"❌ 抓取 {username} 出错: {e}")
        return []

    results = []
    if tweets.data:
        for t in tweets.data:
            results.append({
                "username": username,
                "tweet_id": str(t.id),
                "text": t.text,
                "created_at": t.created_at,
                "likes": t.public_metrics.get("like_count", 0),
                "retweets": t.public_metrics.get("retweet_count", 0),
                "replies": t.public_metrics.get("reply_count", 0),
                "url": f"https://x.com/{username}/status/{t.id}",
                # 预留字段，下周接情绪分析
                "sentiment": None,
                "topic": None,
            })
    print(f"✅ {username}: 抓到 {len(results)} 条")
    return results


def fetch_all(usernames, days=1, max_results=20, sleep_seconds=2):
    """批量抓取所有用户"""
    all_data = []
    for i, u in enumerate(usernames, 1):
        print(f"[{i}/{len(usernames)}] 抓取 {u} ...")
        data = fetch_recent_tweets(u, days=days, max_results=max_results)
        all_data.extend(data)
        if i < len(usernames):
            time.sleep(sleep_seconds)
    return all_data