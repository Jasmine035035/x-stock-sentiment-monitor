"""全局配置：博主列表、抓取参数"""

USERNAMES = [
    "DariusDale42", 
    "fundstrat", 
    "GerberKawasaki",
    "elonmusk", 
    "BillAckman", 
    "dylan522p", 
    "dnystedt", 
    "matthewherper",
    "jimcramer", 
    "aleabitoreddit", 
    "tengyanAI", 
    "xingpt",
    "bboczeng", 
    "jukan05"
]

# 抓取参数
FETCH_DAYS = 1          # 抓取最近几天的推文
MAX_RESULTS_PER_USER = 20  # 每人每次最多抓多少条
SLEEP_BETWEEN_USERS = 2    # 每个用户之间的间隔秒数，降低限流风险

# 存储路径
DATA_DIR = "data"
REPORT_DIR = "reports"