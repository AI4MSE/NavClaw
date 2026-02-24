---
name: navclaw
description: 个人AI导航助手 — 极限搜索避堵方案，实测智能绕行可能比官方方案更优。一键跳转手机导航APP（iOS/Android）。附加工具箱：天气查询、周边地点搜索、地理编码、行政区划查询等。目前支持高德，后续扩展。 Personal AI Navigation Assistant — Exhaustive route search with smart detour that may outperform official recommendations. One-tap deep links for iOS/Android. Bonus toolbox like weather, POI search, geocoding, district query, etc. Currently supports Amap, more platforms coming
version: 0.1.2
icon: 🦀
---

# NavClaw 🦀 - 个人AI导航助手

导航平台：目前支持高德，后续扩展更多平台。

**⚠️ 前置条件**：需要高德 Web 服务 API Key（免费申请）。获取优先级：
1. 从记忆中查找用户是否已提供过高德 API Key
2. 如果没有，询问用户是否有高德 API Key
3. 如果用户没有，引导获取：[高德开放平台](https://lbs.amap.com/) → 控制台 → 创建应用 → 添加 Key（Web 服务）

拿到 Key 后填入 `config.py` 的 `API_KEY` 字段：
```python
API_KEY = "你的高德API Key"
```

和设置为环境变量（双保险）：
```bash
export API_KEY="你的高德API Key"
```

**触发方式**：用户说"从 [起点] 到 [终点] 导航"、"导航从 [起点] 到 [终点]"或"navigate from [A] to [B]"即可自动执行。说"到家"时自动替换为 `config.py` 中的 `DEFAULT_DEST`。

**工作流程**：调用 `wrapper.py --origin "起点" --dest "终点"`，经过五阶段规划（广撒网 → 精筛选 → 深加工 → 迭代优化 → 路线固化），生成大量路线方案（含绕行优化），自动发送 3 条消息到聊天平台 + 日志附件：消息 1 完整对比表格，消息 2 快速导航链接，消息 3 最终推荐 + iOS/Android 一键深度链接。

**输出格式**：

- **其他聊天工具（通用方法，推荐优先使用）**：运行 `wrapper.py --origin "起点" --dest "终点" --no-send`，结果输出到 stdout，OpenClaw 读取后转发给用户即可。stdout 格式如下：
- **Mattermost（原生支持）**：需要先在 `config.py` 中配置 `MM_BASEURL`、`MM_BOT_TOKEN`、`MM_CHANNEL_ID`，然后直接运行 `wrapper.py --origin "起点" --dest "终点"`，自动发送 3 条消息 + 日志附件。

**强烈建议先用通用方法（`--no-send`）**，确认结果正确后再配置特定平台。stdout 格式如下：

```
────────────────────────────────────────────────────────────
📨 消息 1
────────────────────────────────────────────────────────────
（完整对比表格：所有基准 + 绕行方案，含时间/里程/拥堵%/收费等）

────────────────────────────────────────────────────────────
📨 消息 2
────────────────────────────────────────────────────────────
（快速导航链接：最快绕行 + 最少拥堵 + Android/iOS deep link）

────────────────────────────────────────────────────────────
📨 消息 3
────────────────────────────────────────────────────────────
（最终推荐：综合时间榜 / 拥堵最少榜 / 官方基准榜 + 一键导航链接）
```

OpenClaw 可读取 stdout 按 `📨 消息 1/2/3` 分段转发给用户。日志文件路径在末尾 `📝 日志: log/navclaw/...` 行中。

**安装配置**：`pip install requests` → `cp config_example.py config.py` → 编辑填入高德 API Key、默认终点、Mattermost 配置（可选）。

**文件位置**：调用入口 `wrapper.py`，核心引擎 `navclaw.py`，配置 `config.py`（需用户创建），模板 `config_example.py`，日志 `log/`。

**聊天平台**：目前内置支持 Mattermost（通过 `wrapper.py`），其他聊天工具 OpenClaw 帮我转发。最简单的办法是直接聊天告诉 OpenClaw 运行并读取结果发送给你，支持任何聊天平台，稳定性和上下文长度取决于你的大模型 API。如果想节约 token、防止上下文截断、加快响应速度，可以自行扩展 `wrapper.py` 或让 OpenClaw AI 阅读现有 Mattermost 代码帮你适配新平台。

**性能参考**：短途无拥堵（迭代=0）约 6 秒、15 次 API、10 条路线；长途有拥堵（迭代=1）约 30 秒、150 次 API、40 条路线。首次使用建议 `MAX_ITER = 0` 验证配置正确，`MAX_ITER = 1` 深度优化可能找到比官方更快的路线。

**依赖**：Python 3.8+、`requests`（唯一第三方依赖）、高德 Web 服务 API Key。

---

## 附加功能：地图 API 工具箱

除了核心驾车规划外，NavClaw 的 API Key 同样可以调用高德全套位置服务。以下功能均通过 curl 直接调用，无需额外依赖。

**何时使用**：当用户提到天气查询、地点搜索、地址转坐标、坐标转地址、行政区划等需求时，可直接使用以下接口。

### 1. 天气查询

获取某城市当前天气或未来预报。需要城市 `adcode`，不确定时先用下方行政区划查询获取。

```bash
# 实时天气（例：北京 adcode=110000）
curl "https://restapi.amap.com/v3/weather/weatherInfo?key=$API_KEY&city=[adcode]&extensions=base"

# 未来几天预报
curl "https://restapi.amap.com/v3/weather/weatherInfo?key=$API_KEY&city=[adcode]&extensions=all"
```

### 2. 周边地点搜索（POI）

按关键词在指定城市范围内检索兴趣点。

```bash
# 示例：在杭州搜索"咖啡馆"
curl "https://restapi.amap.com/v3/place/text?key=$API_KEY&keywords=[关键词]&city=[城市名称]"
```

### 3. 地理编码（地址 → 经纬度）

把文字地址解析为经纬度坐标，驾车规划等接口需要坐标作为输入。

```bash
curl "https://restapi.amap.com/v3/geocode/geo?key=$API_KEY&address=[地址文本]"
```

### 4. 逆地理编码（经纬度 → 地址）

将坐标反查为可读的地址描述。

```bash
# 坐标格式：经度,纬度
curl "https://restapi.amap.com/v3/geocode/regeo?key=$API_KEY&location=[经度,纬度]"
```

### 5. 行政区划查询（获取 adcode）

查询省市区街道的行政编码及边界，天气查询等接口依赖 adcode。

```bash
# 示例：查"北京市"的 adcode
curl "https://restapi.amap.com/v3/config/district?key=$API_KEY&keywords=[城市或区域名]&subdistrict=0"
```

---

**作者**：小红书 @深度连接

**更多信息**：[GitHub](https://github.com/AI4MSE/NavClaw) · [技术文档](docs/technical_CN.md) · 🌐 [NavClaw.com](https://navclaw.com) · 📧 NavClaw@NavClaw.com（纯自娱自乐）
