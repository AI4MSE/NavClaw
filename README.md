# NavClaw 🦀

**智能导航路线规划** — 支持 OpenClaw 集成，也可独立使用。避堵规划 · 极限搜索优化方案 · 兼容 iOS 和 Android · 链接一键跳转导航 APP。

**Intelligent route planner** — standalone or powered by OpenClaw. Congestion avoidance, exhaustive route optimization, iOS & Android deep links that open your navigation app in one tap.

首个支持导航平台 / First supported platform: **Amap 高德** · 你可以贡献来使它更多平台支持 / More coming soon & Wecome your contribution.

 [📖 English](README_EN.md) · [GitHub](https://github.com/AI4MSE/NavClaw) · [技术文档](docs/technical_CN.md)

## 核心特性 / Highlights

- 🔍 **极限搜索** — 多策略并发查询，可以短时间拿到***官方所有推荐进行对比**，并生成数十种绕行组合， / Exhaustive search with dozens of bypass combinations
- 🚧 **智能避堵** — 基于 TMC 数据识别拥堵段，自动生成绕行方案，可能可以***比官方推荐的更省时*** （参考下面实际案例） / Smart congestion detection & auto-detour
- 📱 **一键导航** — iOS / Android 深度链接，点击直接跳转导航 APP / One-tap deep links for iOS & Android
- 🤖 **OpenClaw 原生** — AI Agent 技能，说"从北京到广州导航"即可 / Say *"navigate from A to B"* and it runs
- 🔌 **聊天平台** — 内置 Mattermost，可扩展更多平台 / Mattermost built-in, extensible to other platforms
- ⚡ **高性能** — 可几秒内返回结果（如果迭代=0），40+ 条路线 / Returns in seconds, 40+ routes evaluated

## 快速开始 / Quick Start

### 通过 OpenClaw 使用（推荐）/ With OpenClaw (recommended)

NavClaw 主要面向 OpenClaw 用户设计，依赖（`requests`）会自动安装。
Designed primarily as an OpenClaw skill. Dependencies auto-installed.

1. 将 NavClaw 克隆到 OpenClaw 项目目录，或直接放到 OpenClaw 服务器上的任意位置
   Clone into your OpenClaw project dir, or place anywhere on your OpenClaw server
3. 复制 `config_example.py` → `config.py`，填入 Amap API Key
   Copy `config_example.py` → `config.py`, fill in your Amap API key
4. 更新 OpenClaw 的长期记忆或制作技能
   Update OpenClaw's long-term memory or create a skill
5. 直接说 / Just say: *"从北京南站到广州南站导航"*

### 独立使用 / Standalone

```bash
git clone https://github.com/AI4MSE/NavClaw.git
cd NavClaw
pip install -r requirements.txt
cp config_example.py config.py     # 填入 Amap 高德 API Key / fill in your Amap API key
```

API Key 获取 / Get your key: [高德开放平台 / Amap Open Platform](https://lbs.amap.com/) → 控制台 → 创建应用 → 添加 Key（Web 服务）

```bash
python3 navclaw.py                                        # 使用 config.py 默认起终点
python3 navclaw.py -o "北京南站" -d "广州南站"
python3 navclaw.py -o "上海虹桥站" -d "家"                 # "家" = config.py 中的默认终点
python3 wrapper.py                                        # 带 Mattermost 推送（默认）
python3 wrapper.py --no-send                              # 仅本地输出
```

---

## 工作原理

导航 APP 通常只返回 2-3 条路线。NavClaw 通过**五阶段流水线**探索更多可能：

```
Phase 1: 🟢 广撒网    → 并发查询 6+ 种路线策略
Phase 2: 🟡 精筛选    → 去重 + 选出多样化种子路线
Phase 3: 🔴 深加工    → 识别拥堵聚合段，生成绕行组合
Phase 4: 🔄 迭代优化  → 对最佳候选方案再次优化
Phase 5: ⚓ 路线固化   → 用途经点锁定路线，确保导航可复现
```

## OpenClaw 集成

NavClaw 的最大用户群是 OpenClaw AI Agent。

### 方式一：更新长期记忆

将以下内容贴入 OpenClaw 的长期记忆（路径和地址按你的环境修改）：

```markdown
### 🗺️ NavClaw — 智能导航路线规划技能

**触发方式**：用户说"从 [起点] 到 [终点] 导航"即可自动执行

**特殊规则**：
- 说"到家"时，自动替换为 config.py 中的 DEFAULT_DEST
- 示例："从北京南站到家" → 路线目的地为 config.py 配置的默认终点

**工作流程**：
1. 调用 /path/to/NavClaw/wrapper.py --origin "起点" --dest "终点"
2. wrapper.py 加载 config.py，调用 navclaw.py 执行 Phase 1-5 规划
3. 生成 40+ 条路线方案（含绕行优化）
4. 自动发送 3 条 Mattermost 消息 + 日志附件：
   - 📨 消息 1 — 完整对比表格（所有基准 + 绕行方案）
   - 📨 消息 2 — 快速导航链接（最快绕行 + 最少拥堵）
   - 📨 消息 3 — 最终推荐（时间榜 / 拥堵榜 / 基准榜）+ 一键深度链接

**文件位置**：
- 调用入口：/path/to/NavClaw/wrapper.py
- 核心引擎：/path/to/NavClaw/navclaw.py
- 配置文件：/path/to/NavClaw/config.py
- 日志目录：/path/to/NavClaw/log/
```

### 方式二：制作 OpenClaw 技能

也可以为 NavClaw 创建专属技能文件，参考 OpenClaw 的技能文档格式。

### 聊天平台支持

目前内置支持：**Mattermost**（通过 `wrapper.py`）。

- 当然**最简单**的办法就是聊天告诉Openclaw 自己运行和读取结果发送给你，支持任何聊天平台扩展，稳定性和支持上下文长度取决于你的大模型API
- 如果想节约token并防止上下文截断、加快响应速度，那么你可以让AI帮你开发一个接口，比如需要 Slack、Discord、微信等其他平台？可以：
    - 自行扩展 `wrapper.py` 代码
    - 让你的 OpenClaw AI 阅读现有 Mattermost 代码，帮你适配新平台

## 实测某超长距离复杂迭代案例：北京南站 → 广州南站 （自驾） - 比官方默认各种推荐省时

> 运行时间：2026-02-24 · NavClaw v0.1 · 高速路线 2,147 km

### 性能指标

| 指标 | 数值 |
|------|------|
| API 调用 | 147 次 |
| 总耗时 | -秒 可并行加速 |
| 评估路线数 | 41 条（10 基准 + 31 绕行） |
| 检测拥堵聚合段 | 6 段（共 63.7 km） |
| 绕行成功率 | 126/130 |

### 结果：比官方默认推荐快 22 分钟

| 榜单 | 方案 | 时间 | 里程 | 拥堵 | 收费 |
|------|------|------|------|------|------|
| 🏆 全场最快 | 绕行堵5/5 | **22h46m** | 2,148 km | 3% | ¥1,060 |
| 🛡️ 基准最快 | 默认推荐(固化) | 23h08m | 2,147 km | 3% | ¥1,073 |
| 🚗 拥堵最少 | 不走高速(固化) | 45h20m | 2,373 km | 0% | ¥36 |

### 各阶段耗时

```
Phase 1: 🟢   6 次 API,   5.9s → 6 种策略查询 10 条原始路线
Phase 2: 🟡   0 次 API,   0.0s → 去重过滤 → 5 条种子路线
Phase 3: 🔴 124 次 API,  49.3s → 6 个拥堵聚合段 → 126 条绕行方案
Phase 4: 🔄   6 次 API,  16.8s → 迭代优化 2 条新路线
Phase 5: ⚓   9 次 API,  23.7s → 9 条基准路线固化（各 10 个锚点）
```

### 输出示例 — 消息 3（最终推荐）

```
🎯 最终推荐

🏆 综合时间榜（全场最快）
   [混合] 绕行堵5/5[s33-39-10-iter0] **本工具推荐，比官方省时**
   ⏱ 22h46m | 2148km | 拥堵3%
   📱 Android: amapuri://route/plan/?slat=39.867679&slon=116.378059&sname=北京南站&dlat=22.989125&dlon=113.277732&dname=广州南站&...
   📱 iOS: iosamap://route/plan/?slat=39.867679&slon=116.378059&sname=北京南站&dlat=22.989125&dlon=113.277732&dname=广州南站&...

🚗 拥堵最少榜（最省心路线）
   [基准] 不走高速(固化)[s35-1-fix]
   ⏱ 45h20m | 2373km | 拥堵0%

🛡️ 官方基准榜（Amap官方导航原始推荐）
   [基准] 默认推荐(固化)[s32-1-fix]
   ⏱ 23h08m | 2147km | 拥堵3%
```

### 输出示例 — 消息 1（路线对比表，取前 10 条 / 共 41 条）

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
| ... | ... | ... 还有 31 条路线 | ... | ... | ... | ... | ... | ... |
```

<details>
<summary>📋 完整日志文件（点击展开）</summary>

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

🔴 Phase 3: 深加工 — s39-1 上检测到 6 个拥堵聚合段:
  堵1: 1268~1289km, 20.4km | 堵2: 1331~1337km, 6.4km
  堵3: 1653~1665km, 12.0km | 堵4: 1877~1894km, 16.7km
  堵5: 2024~2034km, 9.7km  | 堵6: 2065~2066km, 1.1km
  → 124 次绕行查询, 126/130 成功

🔄 Phase 4: 迭代优化 — 6 次 API, 新增 2 条路线

⚓ Phase 5: 路线固化 — 9 条基准路线锚定（各 10 个途经点）

## 全部路线 (41 条)
- s33-39-10-iter0 | 22h46m | 2148km | 97% | 3% | ¥1060 | WP=2 🏆全局最快
- s33-39-8-iter0  | 22h53m | 2148km | 96% | 3% | ¥1046 | WP=2
- s32-1-fix       | 23h08m | 2147km | 99% | 3% | ¥1073 | WP=10
- s33-39-6-iter0  | 23h15m | 2192km | 98% | 3% | ¥1085 | WP=2
- ... (37 more routes)
```

</details>

## 项目结构

```
NavClaw/
├── navclaw.py          # 核心引擎（可独立运行或被 import）
├── wrapper.py          # 聊天平台对接层
├── config.py           # 你的配置文件（已 gitignore）
├── config_example.py   # 配置模板（含注释）
├── requirements.txt    # Python 依赖（requests）
├── .gitignore
├── LICENSE             # Apache 2.0
├── README.md           # 中文（双语头部）
├── README_EN.md        # English
└── docs/
    └── technical_CN.md # 技术文档
```

## 运行环境要求

- Python 3.8+
- 唯一的第三方依赖就是 requests，其余全是标准库
  - `requests` 库（OpenClaw 环境自动安装；或 `pip install -r requirements.txt`）
- Amap高德API Key

## 许可证

[Apache License 2.0](LICENSE)
🌐 [NavClaw.com](https://navclaw.com) (Reserved Only for NavClaw GitHub Page 备用链接跳转Github，非商用目的，仅跳转)

