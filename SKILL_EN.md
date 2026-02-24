---
name: navclaw
description: Personal AI Navigation Assistant — Exhaustive route search with smart detour that may outperform official recommendations. One-tap deep links for iOS/Android. Bonus toolbox like weather, POI search, geocoding, district query, etc. Currently supports Amap, more platforms coming 
version: 0.1.2
icon: 🦀
---

# NavClaw 🦀 - Personal AI Navigation Assistant

Navigation platform: Currently supports Amap (Gaode), more platforms coming.

**⚠️ Prerequisite**: Requires an Amap Web Service API Key (free). Priority:
1. Check memory for user's existing Amap API Key
2. If not found, ask the user
3. If they don't have one, guide them: [Amap Open Platform](https://lbs.amap.com/) → Console → Create App → Add Key (Web Service)

Once obtained, write to `config.py`:
```python
API_KEY = "your_amap_api_key"
```

And set as environment variable (dual insurance):
```bash
export API_KEY="your_amap_api_key"
```

**Trigger**: User says "navigate from [A] to [B]", or similar. Saying "home" auto-replaces with `DEFAULT_DEST` in `config.py`.

**Workflow**: Runs `wrapper.py --origin "A" --dest "B"` through a 5-phase pipeline (broad search → filter → congestion analysis → iterative optimization → route anchoring), generating many route candidates with bypass optimization, then outputs 3 messages: msg 1 full comparison table, msg 2 quick navigation links, msg 3 top recommendations + iOS/Android one-tap deep links.

**Output format**:

- **Universal method (recommended first)**: Run `wrapper.py --origin "A" --dest "B" --no-send`, results output to stdout. OpenClaw reads and forwards to user. stdout format:
- **Mattermost (built-in)**: Configure `MM_BASEURL`, `MM_BOT_TOKEN`, `MM_CHANNEL_ID` in `config.py`, then run `wrapper.py --origin "A" --dest "B"` to auto-send 3 messages + log attachment.

**Strongly recommended to use universal method (`--no-send`) first**, verify results, then configure specific platforms. stdout format:

```
────────────────────────────────────────────────────────────
📨 Message 1
────────────────────────────────────────────────────────────
(Full comparison table: all baselines + bypass routes, with time/distance/congestion%/toll)

────────────────────────────────────────────────────────────
📨 Message 2
────────────────────────────────────────────────────────────
(Quick navigation links: fastest bypass + least congestion + Android/iOS deep links)

────────────────────────────────────────────────────────────
📨 Message 3
────────────────────────────────────────────────────────────
(Top recommendations: time ranking / congestion ranking / official baseline + one-tap navigation links)
```

OpenClaw can read stdout and forward by splitting on `📨 Message 1/2/3`. Log file path appears at the end of stdout, look for the line containing `log/navclaw/`.

**Installation**: `pip install requests` → `cp config_example.py config.py` → edit with Amap API Key, default destination, Mattermost config (optional).

**File locations**: Entry point `wrapper.py`, core engine `navclaw.py`, config `config.py` (user-created), template `config_example.py`, logs `log/`.

**Chat platforms**: Built-in Mattermost support via `wrapper.py`. For other platforms, OpenClaw reads results and forwards to user. Simplest approach: tell OpenClaw to run the script and send results back. For lower token usage and faster response, extend `wrapper.py` or let OpenClaw AI read existing Mattermost code to adapt for Slack, Discord, WeChat, etc.

**Performance**: Short trip no congestion (iter=0): ~6s, 15 API calls, 10 routes. Long trip with congestion (iter=1): ~30s, 150 API calls, 40 routes. Start with `MAX_ITER = 0` to verify config, `MAX_ITER = 1` for deep optimization that may find faster routes than official recommendations.

**Dependencies**: Python 3.8+, `requests` (only third-party dependency), Amap Web Service API Key.

---

## Bonus: Amap API Toolbox

Beyond driving route planning, NavClaw's API Key unlocks the full suite of Amap location services. All functions below use curl directly — no extra dependencies.

**When to use**: When the user asks about weather, nearby places, address lookup, coordinate conversion, or administrative region info.

### 1. Weather Lookup

Retrieve current conditions or multi-day forecast for a city. Requires the city's `adcode` — use the District Query below if unknown.

```bash
# Current weather (e.g. Beijing adcode=110000)
curl "https://restapi.amap.com/v3/weather/weatherInfo?key=$API_KEY&city=[adcode]&extensions=base"

# Multi-day forecast
curl "https://restapi.amap.com/v3/weather/weatherInfo?key=$API_KEY&city=[adcode]&extensions=all"
```

### 2. Place Search (POI)

Find points of interest by keyword within a given city.

```bash
# Example: search "coffee shop" in Hangzhou
curl "https://restapi.amap.com/v3/place/text?key=$API_KEY&keywords=[keyword]&city=[city_name]"
```

### 3. Geocoding (Address → Coordinates)

Resolve a text address into latitude/longitude. Required as input for driving and other coordinate-based APIs.

```bash
curl "https://restapi.amap.com/v3/geocode/geo?key=$API_KEY&address=[address_text]"
```

### 4. Reverse Geocoding (Coordinates → Address)

Convert a coordinate pair back to a human-readable address.

```bash
# Format: longitude,latitude
curl "https://restapi.amap.com/v3/geocode/regeo?key=$API_KEY&location=[lng,lat]"
```

### 5. District Query (Get adcode)

Look up administrative region codes and boundaries. Weather and other APIs depend on adcode.

```bash
# Example: look up "Beijing" adcode
curl "https://restapi.amap.com/v3/config/district?key=$API_KEY&keywords=[city_or_region]&subdistrict=0"
```

---

**Author**: @DeepJoint

**More info**: [GitHub](https://github.com/AI4MSE/NavClaw) · [Technical docs](docs/technical_EN.md) · 🌐 [NavClaw.com](https://navclaw.com) · 📧 NavClaw@NavClaw.com (just for fun)
