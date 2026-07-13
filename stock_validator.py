"""个股数据校验模块：通过yfinance获取A股实时数据，自动填充市值"""

import yfinance as yf
import time
import re
from datetime import datetime

_stock_cache = {}


def get_stock_realtime(code: str) -> dict:
    """
    获取A股个股实时数据
    code: 股票代码，如 '603986.SH' 或 '603986'
    """
    code_clean = code.replace('.SH', '').replace('.SZ', '').replace('.BJ', '').strip()
    
    # 检查缓存
    if code_clean in _stock_cache:
        cache_time, data = _stock_cache[code_clean]
        if (datetime.now() - cache_time).seconds < 300:
            return data
    
    # 转换成yfinance格式
    if len(code_clean) == 6:
        if code_clean.startswith('6') or code_clean.startswith('5'):
            ticker = f"{code_clean}.SS"
        else:
            ticker = f"{code_clean}.SZ"
    else:
        ticker = code
    
    try:
        stock = yf.Ticker(ticker)
        info = stock.info
        
        market_cap = info.get('marketCap', 0)
        if market_cap:
            market_cap = market_cap / 100000000
        
        result = {
            "code": code_clean,
            "name": info.get('longName', info.get('shortName', code_clean)),
            "price": info.get('regularMarketPrice', info.get('currentPrice', 0)),
            "change_pct": info.get('regularMarketChangePercent', 0),
            "market_cap": market_cap,
            "market_cap_str": f"{market_cap:.0f}亿元" if market_cap and market_cap > 0 else "未知",
            "pe": info.get('trailingPE', None),
            "pb": info.get('priceToBook', None),
            "industry": info.get('industry', info.get('sector', '')),
            "data_source": "Yahoo Finance",
            "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        
        _stock_cache[code_clean] = (datetime.now(), result)
        return result
        
    except Exception as e:
        return {"error": f"获取数据失败: {str(e)}"}


def auto_fill_market_cap(input_path: str, output_path: str = None):
    """
    读取AI报告，找到所有A股股票代码，自动填充真实市值
    """
    if output_path is None:
        output_path = input_path.replace('.txt', '_最终版.txt')
    
    with open(input_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 找所有 6位代码.SH 或 6位代码.SZ
    pattern = r'(\d{6})\.(SH|SZ)'
    matches = re.findall(pattern, content)
    
    if not matches:
        print("⚠️ 未找到A股股票代码，无需填充")
        # 直接复制原文件
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(content)
        return output_path
    
    print(f"📊 发现 {len(matches)} 只股票，正在获取实时市值...")
    
    # 先收集所有真实数据
    real_data_map = {}
    for code, market in matches:
        code_full = f"{code}.{market}"
        print(f"  🔍 获取 {code_full} ...")
        data = get_stock_realtime(code_full)
        if "error" not in data and data.get('market_cap'):
            real_data_map[code_full] = data
        time.sleep(0.3)
    
    if not real_data_map:
        print("⚠️ 未能获取任何股票的市值数据，请检查网络")
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(content)
        return output_path
    
    # 逐条替换：找到 "当前市值" 行并替换
    for code_full, data in real_data_map.items():
        mc = data['market_cap']
        mc_str = f"{mc:.0f}亿元"
        name = data.get('name', code_full)
        
        # 替换已有的市值行
        # 匹配 "当前市值：xxx亿元" 或 "当前市值：搜索失败"
        old_pattern = rf'({re.escape(code_full)}.*?)(当前市值[：:][^\n]*)'
        
        def replace_func(match):
            prefix = match.group(1)
            return f"{prefix}当前市值：{mc_str}（来源：Yahoo Finance，自动补充）"
        
        new_content = re.sub(old_pattern, replace_func, content, flags=re.DOTALL)
        
        # 如果没替换成功（说明没有"当前市值"行），就在代码后面插入一行
        if new_content == content:
            new_content = re.sub(
                rf'({re.escape(code_full)}.*?)(\n)',
                rf'\1\n  当前市值：{mc_str}（来源：Yahoo Finance，自动补充）\2',
                content,
                flags=re.DOTALL
            )
        
        content = new_content
        print(f"  ✅ {name}({code_full}) 市值：{mc_str}")
    
    # 保存最终版
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print(f"\n✅ 市值已自动填充，保存至：{output_path}")
    return output_path


def validate_ai_report(analysis_text: str) -> str:
    """从AI报告中提取股票代码，获取真实数据（仅校验，不修改文件）"""
    pattern = r'(\d{6})\.(SH|SZ)'
    codes = re.findall(pattern, analysis_text)
    
    if not codes:
        return "⚠️ 未在报告中找到A股股票代码"
    
    print(f"\n📊 找到 {len(codes)} 只股票，正在获取真实数据...")
    print("=" * 50)
    
    results = []
    for code, market in codes:
        code_full = f"{code}.{market}"
        data = get_stock_realtime(code_full)
        
        if "error" in data:
            results.append(f"❌ {code_full}: {data['error']}")
        else:
            mc = data.get('market_cap', 0)
            mc_str = f"{mc:.0f}亿" if mc > 0 else "未知"
            results.append(
                f"✅ {data.get('name', code)}({code_full}) "
                f"市值: {mc_str} | "
                f"价格: {data.get('price', 'N/A')} | "
                f"涨跌幅: {data.get('change_pct', 'N/A')}%"
            )
        
        time.sleep(0.5)
    
    return "\n".join(results)


if __name__ == "__main__":
    import sys
    import glob
    
    reports = glob.glob("reports/ai_analysis_*.txt")
    if not reports:
        print("❌ 未找到AI报告")
        sys.exit(1)
    
    latest = max(reports)
    print(f"📂 使用最新报告: {latest}\n")
    print("【校验模式】仅显示真实数据，不修改文件")
    print("=" * 50)
    
    with open(latest, 'r', encoding='utf-8') as f:
        content = f.read()
    
    print(validate_ai_report(content))
    
    print("\n" + "=" * 50)
    print("【自动填充模式】生成最终版报告")
    auto_fill_market_cap(latest)
