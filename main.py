"""主流程：抓取 -> 存储 -> 生成报告"""

from config import (
    USERNAMES,
    FETCH_DAYS,
    MAX_RESULTS_PER_USER,
    SLEEP_BETWEEN_USERS,
    DATA_DIR,
    REPORT_DIR,
)
from fetch import fetch_all
from db import save_tweets
from report import generate_text_report, generate_summary_table, save_report
from send_feishu import post_to_feishu
from analyze import run_analysis


def run():
    print("=" * 50)
    print("开始抓取 X 博主观点数据")
    print("=" * 50)

    # 1. 抓取
    raw_data = fetch_all(
        usernames=USERNAMES,
        days=FETCH_DAYS,
        max_results=MAX_RESULTS_PER_USER,
        sleep_seconds=SLEEP_BETWEEN_USERS,
    )

    # 2. 存储
    save_tweets(raw_data)
    import pandas as pd
    df = pd.DataFrame(raw_data)

    if df.empty:
        print("⚠️ 本次未抓到任何数据，流程结束")
        return

    # 3. 展示
    text_report = generate_text_report(df, top_n=3)
    summary_df = generate_summary_table(df)

    print("\n" + text_report)
    print("\n汇总表：")
    print(summary_df.to_string(index=False))

    save_report(text_report, summary_df, report_dir=REPORT_DIR)

    # 4. AI分析（快照+趋势+展望）
    print("\n开始AI分析...")
    analysis_result = run_analysis(days=7)
    print("\n" + analysis_result)

    # 保存AI分析结果
    with open(f"{REPORT_DIR}/ai_analysis_{pd.Timestamp.now().date()}.txt", "w", encoding="utf-8") as f:
        f.write(analysis_result)

    # 5. 发送到飞书（这次发AI分析结果，而不是原始报告）
    post_to_feishu(analysis_result)

    print("\n✅ 流程结束")


if __name__ == "__main__":
    run()