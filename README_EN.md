# NavClaw 🦀 - Personal AI Navigation Assistant

[![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](LICENSE)
[![Python 3.8+](https://img.shields.io/badge/Python-3.8+-green.svg)](https://www.python.org/)
[![ClawHub](https://img.shields.io/badge/ClawHub-navclaw-orange)](https://clawhub.ai/AI4MSE/navclaw)

**Intelligent route planner** — standalone or powered by OpenClaw. Congestion avoidance, exhaustive route optimization, iOS & Android deep links that open your navigation app in one tap.Bonus toolbox like weather, POI search, geocoding, district query, etc. Currently supports Amap, more platforms coming

First supported navigation platform: **Amap** · More coming soon

[📖 中文](README.md) · [GitHub](https://github.com/AI4MSE/NavClaw) · [Technical Doc (CN)](docs/technical_CN.md)· [Technical Doc (EN)](docs/technical_EN.md)

## Highlights

- 🔍 **Exhaustive search** — queries multiple routing strategies, generates dozens of bypass combinations
- 🚧 **Smart congestion avoidance** — detects traffic jams via TMC data, auto-generates detour routes
- 📱 **One-tap navigation** — deep links for iOS & Android, opens directly in your nav app
- 🤖 **OpenClaw-native** — designed as an AI agent skill; just say *"navigate from Beijing to Guangzhou"*
- 🔌 **Chat integration** — sends results to Mattermost; extensible to other platforms via code or AI collaboration
- ⚡ **Fast** — returns results in seconds (with iteration=0), 40+ routes evaluated

## Quick Start

### With OpenClaw (recommended)

NavClaw is designed primarily as an OpenClaw skill. Dependencies (`requests`) are auto-installed.

1. Clone NavClaw into your OpenClaw project directory, or place it anywhere on your OpenClaw server
2. Copy `config_example.py` → `config.py`, fill in your Amap API key
3. Update OpenClaw's long-term memory or create a skill
4. Just say: *"Navigate from Beijing South Station to Guangzhou South Station"*

### Standalone

```bash
git clone https://github.com/AI4MSE/NavClaw.git
cd NavClaw
pip install -r requirements.txt
cp config_example.py config.py     # fill in your Amap API key
```

Get your API key: [Amap Open Platform](https://lbs.amap.com/) → Console → Create App → Add Key (Web Service).

```bash
python3 navclaw.py                                       # use defaults from config.py
python3 navclaw.py -o "Beijing South Station" -d "Guangzhou South Station"
python3 wrapper.py                                       # with Mattermost push (default)
python3 wrapper.py --no-send                             # local output only
```

## How It Works

NavClaw runs a **5-phase pipeline** to discover routes navigation apps won't show you:

```
Phase 1: 🟢 Broad Search      → Query 6+ routing strategies in parallel
Phase 2: 🟡 Smart Filter      → Deduplicate, select diverse seed routes
Phase 3: 🔴 Deep Optimization  → Detect congestion clusters, generate bypass combos
Phase 4: 🔄 Iteration         → Re-optimize best candidates
Phase 5: ⚓ Route Anchoring    → Lock routes with waypoints for reproducible navigation
```

## OpenClaw Integration

NavClaw's primary use case is as an OpenClaw AI agent skill.

### Option 1: Update long-term memory

Paste the following into OpenClaw's long-term memory (adapt paths and addresses to your setup):

> Memory file: `~/.openclaw/MEMORY.md` (or your workspace `MEMORY.md`). Append to the end of the file. You can also tell OpenClaw in chat: "please remember the following" to update.

```markdown
### 🗺️ NavClaw — Intelligent Route Planner

**Trigger**: User says "navigate from [A] to [B]" or "从[A]到[B]导航"

**Special rules**:
- "到家" / "home" → auto-replaces with DEFAULT_DEST in config.py
- Example: "从北京南站到家" → routes to the address configured in config.py

**Workflow**:
1. Run: /path/to/NavClaw/wrapper.py --origin "A" --dest "B" --no-send
2. wrapper.py loads config.py, calls navclaw.py for 5-phase planning
3. Generates many route candidates including bypass optimization
4. stdout outputs 3 messages, delimited by `📨 消息 1/2/3`:
   - msg1: Full comparison table (all baselines + bypass routes)
   - msg2: Quick navigation links (fastest/least congestion)
   - msg3: Top recommendations with one-tap deep links (iOS/Android)
5. Read stdout results and forward the 3 messages to the user
6. Log file path is in the `📝 日志:` line at the end (optional to send)

**Note**:
- Default uses `--no-send` (universal mode), OpenClaw reads results and forwards to user
- If user is on Mattermost, remove `--no-send` to auto-send to the Mattermost channel. Requires additional config in config.py:
  - `MM_BASEURL`: Mattermost server URL (e.g. `https://mm.example.com`)
  - `MM_BOT_TOKEN`: Bot token
  - `MM_CHANNEL_ID`: Target channel ID

**File locations**:
- Entry point: /path/to/NavClaw/wrapper.py
- Core engine: /path/to/NavClaw/navclaw.py
- Config: /path/to/NavClaw/config.py
- Logs: /path/to/NavClaw/log/

**API Key (important)**:
- Before first use, check memory for user's Amap API Key
- If not found, ask the user if they have one
- If they don't, guide them: Amap Open Platform https://lbs.amap.com/ → Console → Create App → Add Key (Web Service)
- Write the key to config.py API_KEY field
```

### Option 2: Install as OpenClaw skill

NavClaw includes a standard `SKILL.md` manifest. Install via:

**ClawHub (official marketplace)**:

```bash
clawhub install navclaw
```

**OpenClaw CN community (clawd.org.cn)**:

```bash
claw skill install navclaw
```

**Manual install**:

```bash
cp -r /path/to/NavClaw ~/.openclaw/workspace/skills/navclaw
```

> ⚠️ The skill may not yet be published or is pending review. Use **Option 1 (long-term memory)** as a temporary alternative — works identically.

### Option 3: Send a message to OpenClaw directly (easiest)

Copy and send the following message to your OpenClaw:

```
Please install the NavClaw navigation skill:

1. Go to https://github.com/AI4MSE/NavClaw, read the README docs, and download the necessary files
2. Use the long-term memory approach for now (see the memory template in the repo README, append to MEMORY.md)
3. Copy config_example.py to config.py, set API_KEY = xxx (replace with real key)
4. Chat platform: if I'm on Mattermost, look for MM_BASEURL, MM_BOT_TOKEN, MM_CHANNEL_ID in memory or config first — ask me only if not found. If sending fails or you're unsure of my chat platform, use universal mode (--no-send) and forward results to me yourself
5. Run a quick test to verify after installation
```

> 💡 Replace `API_KEY = xxx` with your real Amap API Key. If you don't have one, let OpenClaw guide you to https://lbs.amap.com/ to apply.

### Chat platform support

Currently supported: **Mattermost** (built-in via `wrapper.py`).

Want Slack, Discord, WeChat, or other platforms? You can:
- Extend `wrapper.py` yourself
- Ask your OpenClaw AI to read the existing Mattermost code and adapt it for your platform

## Real Example: Beijing South → Guangzhou South

> Run date: 2026-02-24 · NavClaw v0.1 · 2,147 km highway route

### Performance

| Metric | Value |
|--------|-------|
| API calls | 147 |
| Total time | ~30s |
| Routes evaluated | 41 (10 baseline + 31 bypass) |
| Congestion clusters detected | 6 (63.7 km total) |
| Bypass success rate | 126/130 |

### Result: 22 minutes saved vs default

| Ranking | Route | Time | Distance | Congestion | Toll |
|---------|-------|------|----------|------------|------|
| 🏆 Overall fastest | Bypass cluster 5/5 | **22h46m** | 2,148 km | 3% | ¥1,060 |
| 🛡️ Baseline best | Default (anchored) | 23h08m | 2,147 km | 3% | ¥1,073 |
| 🚗 Least congestion | No-highway (anchored) | 45h20m | 2,373 km | 0% | ¥36 |

### Pipeline breakdown

```
Phase 1: 🟢  6 API,   5.9s → 10 raw routes from 6 strategies
Phase 2: 🟡  0 API,   0.0s → dedup & filter → 5 seeds
Phase 3: 🔴 124 API, 49.3s → 6 congestion clusters → 126 bypass routes
Phase 4: 🔄  6 API,  16.8s → 2 iterated improvements
Phase 5: ⚓  9 API,  23.7s → 9 baselines anchored (10 waypoints each)
```

### Sample output — msg3 (final recommendations)

```
🎯 最终推荐

🏆 综合时间榜（全场最快）
   [混合] 绕行堵5/5[s33-39-10-iter0]
   ⏱ 22h46m | 2148km | 拥堵3%
   📱 Android: amapuri://route/plan/?slat=39.867679&slon=116.378059&sname=北京南站&dlat=22.989125&dlon=113.277732&dname=广州南站&...
   📱 iOS: iosamap://route/plan/?slat=39.867679&slon=116.378059&sname=北京南站&dlat=22.989125&dlon=113.277732&dname=广州南站&...

🚗 拥堵最少榜（最省心路线）
   [基准] 不走高速(固化)[s35-1-fix]
   ⏱ 45h20m | 2373km | 拥堵0%

🛡️ 官方基准榜（导航原始推荐）
   [基准] 默认推荐(固化)[s32-1-fix]
   ⏱ 23h08m | 2147km | 拥堵3%
```

### Sample output — msg1 (comparison table, top 10 of 41)

```
| 高亮 | 标签 | 方案 | 时间 | 里程 | 高速% | 堵% | 收费 | 途经 |
|------|------|------|------|------|-------|-----|------|------|
| 🏆全局最快 | s33-39-10-iter0 | 绕行堵5/5 | 22h46m | 2148km | 97% | 3% | ¥1060 | 2 |
| - | s33-39-8-iter0 | 绕行堵4/5 | 22h53m | 2148km | 96% | 3% | ¥1046 | 2 |
| ⏱基准最快 | s32-1-fix | 默认推荐(固化) | 23h08m | 2147km | 99% | 3% | ¥1073 | 10 |
| - | s33-39-6-iter0 | 绕行堵3/5 | 23h15m | 2192km | 98% | 3% | ¥1085 | 2 |
| - | s33-39-28-iter0 | 绕行堵3、5/5 | 23h40m | 2194km | 96% | 3% | ¥1072 | 4 |
| - | s33-39-18-iter0 | 绕行堵1、5/5 | 23h46m | 2212km | 96% | 2% | ¥1073 | 4 |
| - | s33-39-12-iter0 | 绕行堵1、2/5 | 23h48m | 2207km | 94% | 2% | ¥1046 | 4 |
| - | s33-32-4-iter0 | 绕行堵2/5 | 23h53m | 2203km | 97% | 2% | ¥1069 | 2 |
| - | s33-32-2-iter0 | 绕行堵1/5 | 24h03m | 2211km | 98% | 2% | ¥1086 | 2 |
| - | s33-39-30-iter0 | 绕行堵4、5/5 | 24h10m | 2156km | 95% | 2% | ¥1030 | 4 |
| ... | ... | ... (31 more routes) | ... | ... | ... | ... | ... | ... |
```

<details>
<summary>📋 Full log file (click to expand)</summary>

```markdown
# NavClaw日志 v0.1
## 元数据
- 起点：北京南站 (116.378059,39.867679)
- 终点：广州南站 (113.277732,22.989125)
- 时间：2026-02-24 13:13:41
- 版本：0.1
- BASELINES: [32, 36, 38, 39, 35, 1]
- BYPASS_STRATEGIES: [35, 33]
- PHASE2_TOP_Y: 5 / NOHW_PROTECT: 1
- MIN_RED_LEN: 1000m / MERGE_GAP: 3000m
- CONGESTION_STATUSES: ('拥堵', '严重拥堵')
- ANCHOR_COUNT: 10

## 总体统计
- API 查询次数：147
- 总耗时：99.8s
- 基准路线：10 条
- 种子路线：5 条
- 拥堵聚合段：6 个
- 绕行方案：成功 126/130

### 各阶段明细
- Phase 1: 6 次 API, 5.9s
- Phase 2: 0 次 API, 0.0s
- Phase 3: 124 次 API, 49.3s
- Phase 4: 6 次 API, 16.8s
  - 迭代1: 6 次 API, 16.8s, 新增 2 条
- Phase 5: 9 次 API, 23.7s

### 固化前后对比
| 标签 | 原时间 | 固时间 | Δ时间 | 原里程 | 固里程 | 原堵% | 固堵% | 原收费 | 固收费 |
|------|--------|--------|-------|--------|--------|-------|-------|--------|--------|
| s32-1 | 23h04m | 23h08m | +3m | 2147km | 2147km | 3% | 3% | ¥1073 | ¥1073 |
| s36-1 | 45h13m | 45h12m | -2m | 2384km | 2384km | 0% | 0% | ¥10 | ¥10 |
| s36-2 | 45h37m | 45h36m | -1m | 2390km | 2390km | 0% | 0% | ¥10 | ¥10 |
| s36-3 | 45h54m | 45h53m | -2m | 2320km | 2320km | 1% | 1% | 免费 | 免费 |
| s39-1 | 22h18m | 23h13m | +54m | 2147km | 2147km | 3% | 3% | ¥1073 | ¥1073 |
| s35-1 | 45h21m | 45h20m | -2m | 2373km | 2373km | 0% | 0% | ¥36 | ¥36 |
| s35-2 | 45h50m | 45h49m | -1m | 2322km | 2322km | 1% | 1% | ¥22 | ¥22 |
| s35-3 | 45h12m | 45h11m | -1m | 2404km | 2404km | 0% | 0% | ¥31 | ¥31 |
| s1-1 | 46h07m | 46h06m | -2m | 2340km | 2340km | 1% | 1% | 免费 | 免费 |

## 运行日志

🟢 Phase 1: 广撒网 — 10 条原始路线, 6 次 API, 5.9s
  s32-1 | 23h04m | 2147km | 高速 99% | 拥堵  3% | ¥1073
  s39-1 | 22h18m | 2147km | 高速 99% | 拥堵  3% | ¥1073
  s36-1 | 45h13m | 2384km | 高速  0% | 拥堵  0% | ¥10
  s35-1 | 45h21m | 2373km | 高速  0% | 拥堵  0% | ¥36
  ... (6 more)

🟡 Phase 2: 精筛选 — 10 → 5 seeds
  去重: s38-1 = s32-1
  相似剔除: s36-1 ≈ s35-3, s36-3 ≈ s35-2

🔴 Phase 3: 深加工 — 6 congestion clusters on s39-1:
  堵1: 1268~1289km, 20.4km | 堵2: 1331~1337km, 6.4km
  堵3: 1653~1665km, 12.0km | 堵4: 1877~1894km, 16.7km
  堵5: 2024~2034km, 9.7km  | 堵6: 2065~2066km, 1.1km
  → 124 bypass queries, 126/130 success

🔄 Phase 4: 迭代优化 — 6 API, 2 new routes

⚓ Phase 5: 路线固化 — 9 baselines anchored (10 waypoints each)

## 全部路线 (41 routes)
- s33-39-10-iter0 | 22h46m | 2148km | 97% | 3% | ¥1060 | WP=2 🏆全局最快
- s33-39-8-iter0  | 22h53m | 2148km | 96% | 3% | ¥1046 | WP=2
- s32-1-fix       | 23h08m | 2147km | 99% | 3% | ¥1073 | WP=10
- s33-39-6-iter0  | 23h15m | 2192km | 98% | 3% | ¥1085 | WP=2
- ... (37 more routes)
```

</details>

## Project Structure

```
NavClaw/
├── navclaw.py          # Core engine (standalone or importable)
├── wrapper.py          # Chat platform integration layer
├── config.py           # Your config (gitignored)
├── config_example.py   # Config template with comments
├── SKILL.md            # OpenClaw skill marketplace manifest
├── .clawignore         # Skill publish exclusion rules
├── requirements.txt    # Python dependencies (requests)
├── .gitignore
├── LICENSE             # Apache 2.0
├── README.md           # 中文 (bilingual header)
├── README_EN.md        # English
└── docs/
    └── technical_CN.md # Technical documentation
```

## Requirements

- Python 3.8+
- `requests` library (auto-installed with OpenClaw; or `pip install -r requirements.txt`)
- Amap Web Service API key

## License

[Apache License 2.0](LICENSE)
🌐 [NavClaw.com](https://navclaw.com)  Reserved for Github Page
🦀 [ClawHub: navclaw](https://clawhub.ai/AI4MSE/navclaw)

Email:NavClaw@NavClaw.com (FUN only. I may not have time to reply)
