"""主流程：抓取 -> 存储 -> 生成报告"""

from config import (
    USERNAMES,
    FETCH_DAYS,
    MAX_RESULTS_PER_USER,
    SLEEP_BETWEEN_USERS,
    REPORT_DIR,
)
from fetch import fetch_all
from db import save_tweets
from report import generate_text_report, generate_summary_table, save_report
from analyze import run_analysis
from stock_validator import auto_fill_market_cap
import pandas as pd


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

    # 4. AI分析
    print("\n开始AI分析...")
    analysis_result = run_analysis(days=7)

    # 5. 保存原始报告
    today = pd.Timestamp.now().date()
    raw_path = f"{REPORT_DIR}/ai_analysis_{today}.txt"
    with open(raw_path, "w", encoding="utf-8") as f:
        f.write(analysis_result)

    # 6. 自动填充市值，生成最终版
    print("\n📊 正在自动填充市值数据...")
    final_path = auto_fill_market_cap(raw_path)

        # 7. 读取最终版内容，打印到终端
    with open(final_path, 'r', encoding='utf-8') as f:
        final_content = f.read()

    print("\n" + "=" * 50)
    print("📊 最终分析报告（市值已自动填充）")
    print("=" * 50)
    print(final_content)

    # 8. 发送到飞书（发送最终版，含真实市值）
    print("\n📤 正在发送到飞书...")
    post_to_feishu(final_content)

    print(f"\n✅ 报告已保存：{final_path}")
    print("✅ 流程结束")


if __name__ == "__main__":
    run()
