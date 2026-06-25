"""展示模块：把原始抓取数据整理成可读报告"""

import os
from datetime import date

import pandas as pd


def generate_text_report(df: pd.DataFrame, top_n: int = 3) -> str:
    """生成纯文本报告：按博主分组，展示互动最高的几条"""
    if df.empty:
        return "今日无新数据可展示。"

    lines = [f"📊 X博主观点速览 — {date.today()}", "=" * 40]

    total_tweets = len(df)
    active_users = df["username"].nunique()
    lines.append(f"本次共抓取 {total_tweets} 条推文，覆盖 {active_users} 位博主\n")

    for username in df["username"].unique():
        sub = df[df["username"] == username].copy()
        sub = sub.sort_values("likes", ascending=False)

        lines.append(f"👤 @{username}（{len(sub)}条）")

        if sub.empty:
            lines.append("  （本周期内无新推文）\n")
            continue

        for _, row in sub.head(top_n).iterrows():
            text_short = str(row["text"]).replace("\n", " ").strip()
            if len(text_short) > 100:
                text_short = text_short[:100] + "..."
            lines.append(
                f"  • {text_short}\n"
                f"    👍{row['likes']} 🔁{row['retweets']} 💬{row['replies']}  "
                f"({row['created_at']})\n"
                f"    {row['url']}"
            )
        lines.append("")  # 空行分隔

    return "\n".join(lines)


def generate_summary_table(df: pd.DataFrame) -> pd.DataFrame:
    """生成汇总表：每位博主的发推数、平均互动量"""
    if df.empty:
        return pd.DataFrame()

    summary = (
        df.groupby("username")
        .agg(
            推文数=("tweet_id", "count"),
            总点赞=("likes", "sum"),
            总转发=("retweets", "sum"),
            平均点赞=("likes", "mean"),
        )
        .round(1)
        .sort_values("总点赞", ascending=False)
        .reset_index()
    )
    return summary


def save_report(text_report: str, summary_df: pd.DataFrame, report_dir: str = "reports"):
    """保存文本报告和汇总表到本地文件"""
    os.makedirs(report_dir, exist_ok=True)
    today = date.today()

    txt_path = os.path.join(report_dir, f"report_{today}.txt")
    with open(txt_path, "w", encoding="utf-8") as f:
        f.write(text_report)
    print(f"📄 文本报告已保存: {txt_path}")

    if not summary_df.empty:
        xlsx_path = os.path.join(report_dir, f"summary_{today}.xlsx")
        summary_df.to_excel(xlsx_path, index=False)
        print(f"📊 汇总表已保存: {xlsx_path}")
        return txt_path, xlsx_path

    return txt_path, None
