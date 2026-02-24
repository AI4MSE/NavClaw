#!/usr/bin/env python3
"""
NavClaw — 智能导航路线规划 / OpenSource Intelligent Route Planner for OpenClaw & More

🌐 https://navclaw.com (Reserved for Github Page)
📦 https://github.com/AI4MSE/NavClaw

所有用户可调参数集中于此，修改后无需改动任何 Python 代码。
All user-configurable parameters are here. No code changes needed.

支持OpenClaw，支持高德导航 / Motivated and Support OpenClaw  | First supported platform: Amap

Licensed under the Apache License, Version 2.0

作者小红书 @深度连接
"""

# ═══════════════════════════════════════════════════════════════════
# 🔑 通用参数 — NavClaw 核心配置
#    Common Parameters — NavClaw Core Config
# ═══════════════════════════════════════════════════════════════════

# 导航 API 密钥（首个支持 Amap）
# Navigation API key (first supported: Amap)
API_KEY = "your_amap_api_key_here"

# 默认起终点（不传参时使用）
# Default origin/destination (used when no args provided)
# ⚠️ 修改地址时如填写了坐标，务必同步更新，否则会不一致
# ⚠️ If you fill in coordinates, keep them in sync with the address
DEFAULT_ORIGIN = "北京南站"
DEFAULT_ORIGIN_COORD = ""     # 留空=每次geocode；填"lng,lat"可跳过 / Empty=geocode each time; "lng,lat"=skip
DEFAULT_DEST = "广州南站"
DEFAULT_DEST_COORD = ""       # 同上 / Same as above
HOME_KEYWORD = "家"            # 终点简写，输入"家"等同DEFAULT_DEST / Shortcut: "家" maps to DEFAULT_DEST

# ─── 策略配置 / Strategy Config ───
# 策略编号参考 / Strategy number reference (v5 API: 32-45, v3 API: 0-9):
#   32=默认推荐(default)     33=躲避拥堵(avoid congestion)  34=高速优先(highway first)
#   35=不走高速(no highway)  36=少收费(less toll)           37=大路优先(main roads)
#   38=速度最快(fastest)     39=避堵+高速(avoid+highway)
#   40=避堵+不走高速         41=避堵+少收费                  42=少收费+不走高速
#   43=避堵+少收费+不走高速  44=避堵+大路                    45=避堵+速度最快
#   v3: 0=速度优先(speed)  1=不走高速(no highway)  2=费用最少(least cost)  3=距离最短(shortest)
BASELINES = [32, 36, 38, 39, 35, 1]   # Phase 1 基准策略 / baseline strategies
BYPASS_STRATEGIES = [35, 33]            # Phase 3 绕行策略 / bypass strategies

# ─── 拥堵定义 / Congestion Definition ───
# TMC 状态 / TMC statuses: 畅通(clear) / 缓行(slow) / 拥堵(congested) / 严重拥堵(severely congested) / 未知(unknown)
CONGESTION_STATUSES = ("拥堵", "严重拥堵")  # 算作"堵"的状态 / statuses counted as "congested"
MIN_RED_LEN = 1000       # 单段最短拥堵(m) / min segment length to count as congestion
MERGE_GAP = 3000         # 高速合并间距(m) / highway: merge gap between segments
MERGE_GAP_NOHW = 1000   # 非高速合并间距(m) / non-highway: merge gap

# ─── 算法参数（一般无需修改）/ Algorithm Params (usually no need to change) ───
BASELINE_HW_STRAT = 39       # 高速基准策略 / highway baseline strategy
PHASE2_TOP_Y = 5              # Phase 2 精筛选保留数 / smart filter top N
NOHW_PROTECT = 1              # 非高速保护名额 / non-highway protected slots
SIMILAR_DUR_THRESHOLD = 300   # 相似路线时间阈值(秒) / similar route duration threshold (sec)
SIMILAR_RED_THRESHOLD = 3000  # 相似路线堵长阈值(米) / similar route congestion threshold (m)
MIN_RED_LEN_NOHW = 500       # 非高速单段最短拥堵(m) / non-highway min congestion segment
BYPASS_MERGE_GAP = 10000     # 二次合并间距(m) / secondary merge gap
MAX_BYPASS = 7                # 最多绕行聚合段数 / max bypass cluster count
BEFORE_OFF = 4000             # 绕行前偏移(m) / bypass offset before congestion
AFTER_OFF = 4000              # 绕行后偏移(m) / bypass offset after congestion
API_MAX_WP = 16               # API 最大途经点数 / max waypoints per API call
MAX_ITER = 0                  # Phase 4 迭代轮数(0=关闭) / iteration rounds (0=off)
ITER_CANDIDATES = 3           # 每轮迭代候选数 / candidates per iteration
ANCHOR_COUNT = 10             # Phase 5 固化锚点数 / route anchoring waypoint count

# ─── 输出与链接 / Output & Links ───
SEND_ANDROID = True   # 生成 Android 导航链接 / generate Android deep link
SEND_IOS = True       # 生成 iOS 导航链接 / generate iOS deep link
SEND_WEB = False      # 生成 Web 导航链接 / generate Web link
SEARCH_SEC = 90       # 导航搜索时间(秒) / nav search timeout (sec)

# ═══════════════════════════════════════════════════════════════════
# 📨 Mattermost 对接参数 — 仅 wrapper.py 使用
#    Mattermost Integration — used by wrapper.py only
# ═══════════════════════════════════════════════════════════════════

MM_BASEURL = ""
MM_BOT_TOKEN = ""
MM_CHANNEL_ID = ""
