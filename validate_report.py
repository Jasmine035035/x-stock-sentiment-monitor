"""校验AI生成的个股推荐数据"""

from stock_validator import validate_ai_report, get_stock_realtime
import re
import json
from datetime import datetime


def validate_report_file(filepath: str):
    """读取AI报告文件，校验其中的个股数据"""
    
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    print("=" * 60)
    print("📊 个股数据校验报告")
    print(f"📄 文件: {filepath}")
    print("=" * 60)
    print()
    
    # 提取所有股票代码
    pattern = r'(\d{6})\.(SH|SZ|BJ)'
    matches = re.findall(pattern, content)
    
    if not matches:
        print("⚠️ 未在报告中找到A股股票代码")
        return
    
    print(f"🔍 发现 {len(matches)} 只股票，正在从东方财富获取真实数据...\n")
    
    for code, market in matches:
        code_full = f"{code}.{market}"
        real_data = get_stock_realtime(code_full)
        
        if "error" in real_data:
            print(f"❌ {code_full}: {real_data['error']}")
            continue
        
        # 尝试从报告中提取AI给出的市值
        ai_mc_match = re.search(
            rf'{code}\.{market}.*?当前市值[：:]\s*([0-9.]+)\s*亿元',
            content,
            re.DOTALL
        )
        ai_mc = float(ai_mc_match.group(1)) if ai_mc_match else None
        
        print(f"\n📌 {real_data.get('name', code)}({code_full})")
        print(f"   当前价格: {real_data.get('price', 'N/A')} 元")
        print(f"   总市值: {real_data.get('market_cap_str', '未知')}")
        print(f"   涨跌幅: {real_data.get('change_pct', 'N/A')}%")
        print(f"   市盈率: {real_data.get('pe', 'N/A')}")
        print(f"   市净率: {real_data.get('pb', 'N/A')}")
        print(f"   行业: {real_data.get('industry', 'N/A')}")
        print(f"   数据来源: {real_data.get('data_source', 'N/A')}")
        print(f"   更新时间: {real_data.get('updated_at', 'N/A')}")
        
        if ai_mc:
            real_mc = real_data.get('market_cap', 0)
            if real_mc > 0:
                diff = abs(ai_mc - real_mc)
                diff_pct = diff / real_mc * 100
                if diff_pct > 20:
                    print(f"   ⚠️ 市值偏差警告: AI说{ai_mc:.0f}亿，实际{real_mc:.0f}亿（偏差{diff_pct:.0f}%）")
                else:
                    print(f"   ✅ 市值匹配: AI说{ai_mc:.0f}亿，实际{real_mc:.0f}亿（偏差{diff_pct:.0f}%）")
        
        print("-" * 40)


if __name__ == "__main__":
    import sys
    import glob
    
    # 找最新的报告
    reports = glob.glob("reports/ai_analysis_*.txt")
    if not reports:
        print("❌ 未找到AI报告文件，请先运行 main.py")
        sys.exit(1)
    
    latest = max(reports, key=lambda x: x)
    print(f"📂 使用最新报告: {latest}\n")
    
    validate_report_file(latest)
