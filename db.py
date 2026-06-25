"""SQLite存储模块"""

import os
import sqlite3
from datetime import date, timedelta

DB_PATH = "data/tweets.db"


def init_db(db_path: str = DB_PATH):
    """初始化数据库表结构"""
    # 确保 data 目录存在
    db_dir = os.path.dirname(db_path)
    if db_dir and not os.path.exists(db_dir):
        os.makedirs(db_dir, exist_ok=True)
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS tweets (
            tweet_id TEXT PRIMARY KEY,
            username TEXT,
            text TEXT,
            created_at TEXT,
            likes INTEGER,
            retweets INTEGER,
            replies INTEGER,
            url TEXT,
            fetch_date TEXT
        )
    """)
    conn.commit()
    conn.close()


def save_tweets(data: list, db_path: str = DB_PATH):
    """把抓取结果存入SQLite，重复tweet_id会被忽略（去重）"""
    if not data:
        print("⚠️ 没有数据可保存")
        return 0

    init_db(db_path)
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    today = str(date.today())
    inserted = 0
    for row in data:
        try:
            cursor.execute("""
                INSERT OR IGNORE INTO tweets
                (tweet_id, username, text, created_at, likes, retweets, replies, url, fetch_date)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                row["tweet_id"], row["username"], row["text"],
                str(row["created_at"]), row["likes"], row["retweets"],
                row["replies"], row["url"], today
            ))
            if cursor.rowcount > 0:
                inserted += 1
        except Exception as e:
            print(f"❌ 写入失败: {e}")

    conn.commit()
    conn.close()
    print(f"💾 已写入 {inserted} 条新记录到 SQLite（{db_path}）")
    return inserted


def load_recent_tweets(days: int = 7, db_path: str = DB_PATH):
    """读取最近N天的推文，返回 (列名列表, 行数据列表)"""
    init_db(db_path)
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cutoff = str(date.today() - timedelta(days=days))
    cursor.execute("""
        SELECT username, text, created_at, likes, retweets, replies, url, fetch_date
        FROM tweets
        WHERE fetch_date >= ?
        ORDER BY fetch_date, username
    """, (cutoff,))

    rows = cursor.fetchall()
    columns = ["username", "text", "created_at", "likes", "retweets", "replies", "url", "fetch_date"]
    conn.close()
    return columns, rows