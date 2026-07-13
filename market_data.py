"""实时市场数据抓取模块：通过 FRED API 获取美债收益率"""

import ssl
ssl._create_default_https_context = ssl._create_unverified_context

import os
from datetime import datetime
from dotenv import load_dotenv
from fredapi import Fred

load_dotenv()

FRED_API_KEY = os.getenv("FRED_API_KEY")


def get_us_treasury_yields():
    """
    通过 FRED API 获取美国国债收益率
    使用 DGS2MO(2个月)、DGS5(5年)、DGS10(10年)、DGS30(30年)
    """
    if not FRED_API_KEY:
        return {"error": "FRED_API_KEY 未设置，请在 .env 中配置"}

    try:
        fred = Fred(api_key=FRED_API_KEY)

        # 美债收益率系列ID
        tickers = {
            "2个月": "DGS2MO",
            "5年期": "DGS5",
            "10年期": "DGS10",
            "30年期": "DGS30"
        }

        results = {}
        for name, series_id in tickers.items():
            try:
                data = fred.get_series(series_id)
                if not data.empty:
                    latest = data.iloc[-1]
                    prev = data.iloc[-2] if len(data) >= 2 else latest
                    change = latest - prev
                    results[name] = {
                        "yield": round(latest, 4),
                        "change": round(change, 4),
                        "direction": "↑" if change > 0 else "↓" if change < 0 else "→"
                    }
                else:
                    results[name] = {"error": "无数据"}
            except Exception as e:
                results[name] = {"error": f"获取失败: {str(e)}"}

        # 计算10年-2个月利差
        try:
            y10 = results.get("10年期", {}).get("yield")
            y2m = results.get("2个月", {}).get("yield")
            if y10 and y2m:
                spread = round(y10 - y2m, 4)
                results["10Y-2M利差"] = {
                    "spread": spread,
                    "interpretation": "曲线倒挂（衰退信号）" if spread < 0 else "曲线正常（斜率为正）"
                }
        except Exception:
            pass

        return results

    except Exception as e:
        return {"error": f"FRED API 连接失败: {str(e)}"}


def get_kospi():
    """获取韩国KOSPI指数（继续用 yfinance）"""
    import yfinance as yf

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
    except Exception as e:
        return {"error": f"KOSPI数据获取失败: {e}"}

    return {"error": "无数据返回"}


def get_market_snapshot() -> str:
    """获取完整市场快照"""
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    lines = [f"【实时市场数据】（抓取时间：{now}）\n"]

    # 美债（从 FRED 获取）
    lines.append("▶ 美国国债收益率（来源：FRED）：")
    yields = get_us_treasury_yields()
    if "error" in yields:
        lines.append(f"  {yields['error']}")
    else:
        for name, data in yields.items():
            if "error" in data:
                lines.append(f"  {name}: {data['error']}")
            elif "spread" in data:
                lines.append(f"  {name}: {data['spread']}% （{data['interpretation']}）")
            else:
                lines.append(
                    f"  {name}: {data['yield']}% {data['direction']}"
                    f"（较前日变动 {data['change']:+.4f}%）"
                )

    lines.append("")

    # KOSPI（继续用 yfinance）
    lines.append("▶ 韩国KOSPI指数：")
    kospi = get_kospi()
    if "error" in kospi:
        lines.append(f"  {kospi['error']}")
    else:
        lines.append(f"  点位：{kospi['收盘点位']} {kospi['方向']}")
        lines.append(f"  涨跌幅：{kospi['涨跌幅']}")
        lines.append(f"  日内区间：{kospi['日内区间']}")

    return "\n".join(lines)


if __name__ == "__main__":
    print(get_market_snapshot())