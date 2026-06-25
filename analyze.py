"""分析模块：从SQLite读取数据，构建请求，发给Qwen MaaS服务分析"""

import os
from openai import OpenAI
from dotenv import load_dotenv

from db import load_recent_tweets

load_dotenv()

client = OpenAI(
    api_key=os.getenv("DASHSCOPE_API_KEY"),
    base_url="https://dashscope.aliyuncs.com/compatible-mode/v1"
)

TOPIC_CATEGORIES = [
    "大盘/宏观", "半导体", "商业航天", "生物医药",
    "AI/科技", "新能源", "其他"
]


def format_data_for_prompt(columns, rows, max_chars: int = 12000) -> str:
    """把SQLite读出来的数据整理成给AI看的清晰文本，按日期分组"""
    if not rows:
        return "（无数据）"

    grouped = {}
    for row in rows:
        record = dict(zip(columns, row))
        fetch_date = record["fetch_date"]
        username = record["username"]
        grouped.setdefault(fetch_date, {}).setdefault(username, []).append(record)

    lines = []
    for fetch_date in sorted(grouped.keys()):
        lines.append(f"\n=== 日期: {fetch_date} ===")
        for username, records in grouped[fetch_date].items():
            lines.append(f"\n【@{username}】（{len(records)}条）")
            for r in records:
                text = str(r["text"]).replace("\n", " ")
                lines.append(f"- {text} (👍{r['likes']} 🔁{r['retweets']})")

    full_text = "\n".join(lines)
    if len(full_text) > max_chars:
        full_text = "（注：数据量较大，已截取最近部分）\n" + full_text[-max_chars:]
    return full_text


def build_analysis_prompt(formatted_data: str) -> str:
    topics_str = "、".join(TOPIC_CATEGORIES)

    prompt = f"""你是一位专业的金融市场情绪分析师，正在分析一批知名股票投资类KOL在X(Twitter)上的近期发言。

以下是按日期和博主整理的原始推文数据：

{formatted_data}

请基于以上数据，输出一份结构化的分析报告，包含以下四个部分：

## 1. 今日快照
总结最新一天的数据：整体市场情绪倾向（看多/看空/中性，并简要说明依据）、各位博主提到的关键话题和观点。请按以下话题分类组织：{topics_str}。对每个有相关讨论的分类，简要说明该分类下博主们的主要观点和立场。

## 2. 逐人观点摘要
对每位博主，用1-2句话总结他/她最近的核心观点和情绪倾向（看多/看空/中性）。

## 3. 趋势变化
如果数据覆盖了多天，请分析：相比更早的几天，整体情绪/观点是否有明显转变？哪些话题的讨论热度或态度发生了变化？如果数据只有一天，请说明"目前数据量不足以判断趋势，需要积累更多天数据"。

## 4. 推断性展望
基于以上讨论内容，给出一段简短的推断性展望——市场参与者目前关注的焦点可能预示着什么。请务必在这部分开头注明："以下为基于近期社交媒体讨论内容的推断性总结，不构成投资建议，仅供参考"。

请用简洁、专业、客观的中文撰写，避免使用过于绝对的措辞（如"一定会""肯定"），适当体现不确定性。
"""
    return prompt


def run_analysis(days: int = 7, model: str = "qwen3.5-plus") -> str:
    """主函数：读取SQLite数据 -> 构建prompt -> 调用Qwen -> 返回分析结果"""
    columns, rows = load_recent_tweets(days=days)
    if not rows:
        return "⚠️ 没有可分析的数据"

    formatted_data = format_data_for_prompt(columns, rows)
    prompt = build_analysis_prompt(formatted_data)

    try:
        response = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=2000,
        )
        analysis_text = response.choices[0].message.content
        print(f"✅ {model} 分析完成")
        return analysis_text
    except Exception as e:
        print(f"❌ AI分析出错: {e}")
        return f"分析失败: {e}"