"""分析模块：从SQLite读取数据，构建请求，发给Qwen MaaS服务分析"""

import os
import json
from openai import OpenAI
from dotenv import load_dotenv
from db import load_recent_tweets
from market_data import get_market_snapshot

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

    # 抓取实时市场数据（在调用AI之前先拿到真实数据）
    print("📊 正在抓取实时市场数据...")
    try:
        market_snapshot = get_market_snapshot()
        print("✅ 市场数据抓取成功")
    except Exception as e:
        market_snapshot = f"（市场数据抓取失败: {e}，请AI根据已有知识分析）"
        print(f"⚠️ 市场数据抓取失败: {e}")

    prompt = f"""你是一位专业的金融市场情绪分析师。请完成以下四项任务，输出一份完整的市场分析报告。

---

【实时市场数据（已由程序抓取，数据真实可信，请直接使用）】

{market_snapshot}

---

【KOL推文数据（最近7天）】

{formatted_data}

---

【任务一：今日快照】
基于以上KOL推文数据，总结今日整体市场情绪倾向（看多/看空/中性），按话题分类（{topics_str}）整理各方观点。

【任务二：逐人观点摘要】
对每位博主用1-2句话总结其近期核心观点和情绪倾向。

【任务三：市场稳定性分析】
请结合上方已提供的美债收益率数据和KOSPI数据（不需要再搜索，数据已在上方），以及KOL的市场情绪，判断今日市场稳定性：
- 分析美债收益率水平和利差变化的含义
- 分析韩国KOSPI走势对亚洲市场的指示意义
- 综合给出：稳定 / 偏波动 / 高风险 的判断，并说明核心依据

【任务四：板块推荐】
综合以上所有信息（KOL观点 + 美债数据 + KOSPI情况），推荐今日最值得关注的3个板块。
对每个板块提供：
- 板块名称
- 推荐理由（结合KOL具体观点 + 宏观数据支撑）
- 核心逻辑链（1-2句话说清楚"为什么现在值得关注"）
- 风险提示

---

请用简洁专业的中文撰写。所有涉及"未来走势"的判断请注明"以下为推断性分析，不构成投资建议"。
"""
    return prompt


def run_analysis(days: int = 7, model: str = "qwen3.5-plus") -> str:
    """主函数：读取SQLite数据 -> 构建prompt -> 调用Qwen（带网络搜索）-> 返回分析结果"""
    columns, rows = load_recent_tweets(days=days)
    if not rows:
        return "⚠️ 没有可分析的数据，请先运行抓取程序"

    formatted_data = format_data_for_prompt(columns, rows)
    prompt = build_analysis_prompt(formatted_data)

    # 定义网络搜索工具（Qwen支持的内置工具）
    tools = [
        {
            "type": "function",
            "function": {
                "name": "web_search",
                "description": "搜索互联网获取实时信息，如股市数据、新闻等",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "搜索关键词"
                        }
                    },
                    "required": ["query"]
                }
            }
        }
    ]

    try:
        response = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=3000,
            tools=tools,
            tool_choice="auto"
        )

        # 处理可能的多轮工具调用（Qwen可能先调用搜索，再生成最终回答）
        message = response.choices[0].message
        messages = [{"role": "user", "content": prompt}, message]

        # 如果模型调用了搜索工具，继续处理
        while response.choices[0].finish_reason == "tool_calls":
            tool_calls = message.tool_calls
            for tool_call in tool_calls:
                # 这里Qwen会自己执行搜索并返回结果，我们只需把结果回传
                tool_result = {
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": "搜索已执行，请基于你的知识和搜索结果继续分析"
                }
                messages.append(tool_result)

            response = client.chat.completions.create(
                model=model,
                messages=messages,
                max_tokens=3000,
                tools=tools,
                tool_choice="auto"
            )
            message = response.choices[0].message
            messages.append(message)

        analysis_text = response.choices[0].message.content
        print(f"✅ {model} 分析完成")
        return analysis_text

    except Exception as e:
        print(f"❌ AI分析出错: {e}")
        # 如果工具调用出错，降级为无工具版本
        try:
            print("⚠️ 尝试降级为无工具模式...")
            response = client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=3000,
            )
            return response.choices[0].message.content
        except Exception as e2:
            return f"分析失败: {e2}"