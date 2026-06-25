"""存储模块：保存抓取结果到CSV"""

import os
from datetime import date

import pandas as pd


def save_to_csv(data: list, data_dir: str = "data"):
    """将抓取结果存为当天的CSV文件"""
    os.makedirs(data_dir, exist_ok=True)

    df = pd.DataFrame(data)
    filepath = os.path.join(data_dir, f"tweets_{date.today()}.csv")

    if df.empty:
        print("⚠️ 没有数据可保存")
        return df, filepath

    df.to_csv(filepath, index=False, encoding="utf-8-sig")
    print(f"💾 已保存 {len(df)} 条记录到 {filepath}")
    return df, filepath


def load_csv(filepath: str) -> pd.DataFrame:
    """读取已保存的CSV"""
    if not os.path.exists(filepath):
        print(f"⚠️ 文件不存在: {filepath}")
        return pd.DataFrame()
    return pd.read_csv(filepath)