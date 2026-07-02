"""实时市场数据抓取模块：美债收益率 + 韩国KOSPI"""

import yfinance as yf
from datetime import datetime, timedelta
import traceback


def get_us_treasury_yields():
    """
    获取美国国债收益率
    ^IRX = 13周（短端）
    ^FVX = 5年期
    ^TNX = 10年期
    ^TYX = 30年期
    2年期用 BIL 或者直接用 FRED，这里用^IRX作为短端代理
    """
    tickers = {
        "2年期(代理)": "^IRX",
        "5年期": "^FVX",
        "10年期": "^TNX",
        "30年期": "^TYX"
    }

    results = {}
    for name, ticker in tickers.items():
        try:
            data = yf.Ticker(ticker)
            hist = data.history(period="2d")
            if not hist.empty:
                latest = hist["Close"].iloc[-1]
                prev = hist["Close"].iloc[-2] if len(hist) >= 2 else latest
                change = latest - prev
                results[name] = {
                    "yield": round(latest, 3),
                    "change": round(change, 3),
                    "direction": "↑" if change > 0 else "↓" if change < 0 else "→"
                }
        except Exception:
            results[name] = {"error": "获取失败"}

    # 计算10年-2年利差（长短端利差，衡量收益率曲线形态）
    try:
        y10 = results.get("10年期", {}).get("yield")
        y2 = results.get("2年期(代理)", {}).get("yield")
        if y10 and y2:
            spread = round(y10 - y2, 3)
            results["10Y-2Y利差"] = {
                "spread": spread,
                "interpretation": "曲线倒挂（衰退信号）" if spread < 0 else "曲线正常（斜率为正）"
            }
    except Exception:
        pass

    return results


def get_kospi():
    """获取韩国KOSPI指数最新数据"""
    try:
        kospi = yf.Ticker("^KS11")
        hist = kospi.history(period="2d")
        if not hist.empty:
            latest_close = hist["Close"].iloc[-1]
            latest_open = hist["Open"].iloc[-1]
            prev_close = hist["Close"].iloc[-2] if len(hist) >= 2 else latest_open

            pct_change = (latest_close - prev_close) / prev_close * 100
            day_range = f"{round(hist['Low'].iloc[-1], 2)} - {round(hist['High'].iloc[-1], 2)}"

            return {
                "收盘点位": round(latest_close, 2),
                "涨跌幅": f"{round(pct_change, 2)}%",
                "日内区间": day_range,
                "成交量": int(hist["Volume"].iloc[-1]),
                "方向": "↑" if pct_change > 0 else "↓"
            }
    except Exception:
        return {"error": "KOSPI数据获取失败", "detail": traceback.format_exc()}

    return {"error": "无数据返回"}


def get_market_snapshot() -> str:
    """
    获取完整市场快照，格式化成可直接插入prompt的文字
    """
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    lines = [f"【实时市场数据】（抓取时间：{now}，数据来源：Yahoo Finance）\n"]

    # 美债
    lines.append("▶ 美国国债收益率：")
    try:
        yields = get_us_treasury_yields()
        for name, data in yields.items():
            if "error" in data:
                lines.append(f"  {name}: 获取失败")
            elif "spread" in data:
                lines.append(f"  {name}: {data['spread']}% （{data['interpretation']}）")
            else:
                lines.append(
                    f"  {name}: {data['yield']}% {data['direction']}"
                    f"（较前日变动 {data['change']:+.3f}%）"
                )
    except Exception as e:
        lines.append(f"  美债数据获取出错: {e}")

    lines.append("")

    # KOSPI
    lines.append("▶ 韩国KOSPI指数：")
    try:
        kospi = get_kospi()
        if "error" in kospi:
            lines.append(f"  获取失败: {kospi['error']}")
        else:
            lines.append(f"  点位：{kospi['收盘点位']} {kospi['方向']}")
            lines.append(f"  涨跌幅：{kospi['涨跌幅']}")
            lines.append(f"  日内区间：{kospi['日内区间']}")
    except Exception as e:
        lines.append(f"  KOSPI数据获取出错: {e}")

    return "\n".join(lines)


if __name__ == "__main__":
    print(get_market_snapshot())