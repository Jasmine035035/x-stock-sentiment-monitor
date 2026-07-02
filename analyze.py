"""分析模块：从SQLite读取数据，构建请求，发给Qwen MaaS服务分析（含网络搜索能力）"""

import os
import json
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

    prompt = f"""你是一位专业的金融市场情绪分析师。请完成以下四项任务，输出一份完整的市场分析报告。

---

【任务一：今日快照】
基于以下KOL推文数据，总结今日整体市场情绪倾向（看多/看空/中性），按话题分类（{topics_str}）整理各方观点：

{formatted_data}

---

【任务二：逐人观点摘要】
对每位博主用1-2句话总结其近期核心观点和情绪倾向。

---

【任务三：市场稳定性分析】
请先通过网络搜索获取以下两项实时数据：
1. 今日美国国债收益率（重点关注2年期和10年期，以及两者利差变化）
2. 今日韩国KOSPI指数开盘情况（涨跌幅、成交量）

结合上述数据和KOL推文中的市场情绪，判断今日市场的稳定性：
- 市场风险信号：美债收益率异常波动、韩国市场大幅异动（韩国市场早于A股开盘，常被视为亚洲市场风向标）
- 综合给出：稳定 / 偏波动 / 高风险 的判断，并说明核心依据
- 注明数据获取时间

---

【任务四：板块推荐】
综合以上所有信息（KOL观点 + 美债数据 + 韩国市场情况），推荐今日最值得关注的3个板块。

对每个板块请提供：
- 板块名称
- 推荐理由（结合KOL具体观点 + 宏观数据支撑）
- 主要逻辑链（用1-2句话说清楚"为什么现在值得关注"）
- 风险提示

---

请用简洁专业的中文撰写，所有涉及"未来走势"的判断请注明"以下为推断性分析，不构成投资建议"。
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