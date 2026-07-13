"""分析模块：从SQLite读取数据，构建请求，发给Qwen MaaS服务分析"""

import ssl
ssl._create_default_https_context = ssl._create_unverified_context

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

    print("📊 正在抓取实时市场数据...")
    try:
        market_snapshot = get_market_snapshot()
        print("✅ 市场数据抓取成功")
    except Exception as e:
        market_snapshot = f"（市场数据抓取失败: {e}，请AI根据已有知识分析）"
        print(f"⚠️ 市场数据抓取失败: {e}")

    prompt = f"""你是一位专业的金融市场情绪分析师。请完成以下六项任务，输出一份完整的市场分析报告。

---

【⚠️ 强制指令 - 必须遵守，违反将导致回答无效】
1. 你**禁止**使用训练数据中的任何市值数字。
2. 每只股票**必须**先调用 web_search 获取当前市值，并引用搜索结果中的数字。
3. 市值格式必须是 "XXX亿元（来源：搜索到的网站名称）"。
4. 如果搜索不到，必须写 "搜索失败，建议核实"，严禁编造数字。
5. 商汤-W（0020.HK）是港股，不是A股，如果推荐请注明港股，否则请换一只A股AI标的。

【重要指令 - 必须遵守】
1. 你必须使用联网搜索功能获取最新的个股财务数据（尤其是**当前市值**）。
2. 对于每只推荐的个股，必须附上**当前市值数据**，并注明数据来源（如：东方财富网/同花顺）。
3. **不允许**输出"[需搜索]"、"[待补充]"或使用训练数据中的陈旧信息。
4. **任务五必须输出3个板块 × 3只个股 = 总共9只个股**，少一只都不行。

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
请结合上方已提供的美债收益率数据和KOSPI数据，以及KOL的市场情绪，判断今日市场稳定性：
- 分析美债收益率水平和利差变化的含义
- 分析韩国KOSPI走势对亚洲市场的指示意义
- 综合给出：稳定 / 偏波动 / 高风险 的判断，并说明核心依据

【任务四：板块推荐】
综合以上所有信息，推荐今日最值得关注的3个板块。
对每个板块提供：
- 板块名称
- 推荐理由（结合KOL具体观点 + 宏观数据支撑）
- 核心逻辑链（1-2句话说清楚"为什么现在值得关注"）
- 风险提示


【任务五：个股弹性推荐 - 必须输出3个板块 × 3只个股 = 总共9只个股】

基于任务四推荐的3个板块，在**每个板块内各推荐3只**弹性最好的A股中的个股。

⚠️ 强制要求：
- **必须输出3个板块，每个板块必须推荐3只个股（总共9只个股）**
- 全部为A股（可包含科创板、创业板）

关于"弹性"的定义：
- 弹性好的个股通常具备以下特征：流通市值相对较小（50-500亿为佳）、业务与所在板块主题高度绑定

对每只个股提供：
- 股票名称及代码（必须含6位代码 + .SH/.SZ，如：兆易创新（603986.SH））
- 弹性逻辑
- 核心驱动
- 主要风险：1-2条

⚠️ 重要：**不要写市值数据**，市值将由系统后台自动补充，你只需输出股票代码即可。


【输出格式模板 - 严格按照此格式输出】：

▶ 板块一：[板块名称]
  板块核心逻辑（一句话回顾）：[从任务四中提炼]

  推荐个股：
  1. [股票名称]（[代码]，[市场]）
     当前市值：[XX亿元]（来源：[东方财富网/同花顺]）
     弹性逻辑：[...]
     核心驱动：[...]
     主要风险：[...]

  2. [股票名称]（[代码]，[市场]）
     当前市值：[XX亿元]（来源：[...]）
     弹性逻辑：[...]
     核心驱动：[...]
     主要风险：[...]

  3. [股票名称]（[代码]，[市场]）
     当前市值：[XX亿元]（来源：[...]）
     弹性逻辑：[...]
     核心驱动：[...]
     主要风险：[...]

▶ 板块二：[板块名称]
  ...（同上格式，3只个股）

▶ 板块三：[板块名称]
  ...（同上格式，3只个股）


【任务六：数据来源汇总】
请列出你在任务五中获取个股市值数据的来源链接或网站名称。

---

请用简洁专业的中文撰写。所有涉及"未来走势"和个股推荐的内容请注明"以下为推断性分析，不构成投资建议，个股推荐仅供参考，请结合自身判断"。
"""
    return prompt


def run_analysis(days: int = 7, model: str = "qwen-max") -> str:
    """主函数：读取SQLite数据 -> 构建prompt -> 调用Qwen（带网络搜索）-> 返回分析结果"""
    columns, rows = load_recent_tweets(days=days)
    if not rows:
        return "⚠️ 没有可分析的数据，请先运行抓取程序"

    formatted_data = format_data_for_prompt(columns, rows)
    prompt = build_analysis_prompt(formatted_data)

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
            tool_choice="auto",
            extra_body={
                "enable_search": True
            }
        )

        message = response.choices[0].message
        messages = [{"role": "user", "content": prompt}, message]

        while response.choices[0].finish_reason == "tool_calls":
            tool_calls = message.tool_calls
            for tool_call in tool_calls:
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
                tool_choice="auto",
                extra_body={
                    "enable_search": True
                }
            )
            message = response.choices[0].message
            messages.append(message)

        analysis_text = response.choices[0].message.content
        print(f"✅ {model} 分析完成")
        return analysis_text

    except Exception as e:
        print(f"❌ AI分析出错: {e}")
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