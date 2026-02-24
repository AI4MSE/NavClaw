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

"""
NavClaw — 智能导航规划（支持OpenClaw，可以单独使用 | 避堵 | 极限搜索优化方案 | 兼容IOS和安卓 | 链接一键跳转导航APP）
目前支持导航平台：Amap高德

用法:
    python3 navclaw.py                          # 使用 config.py 默认起终点
    python3 navclaw.py -o "北京南站" -d "广州南站"
    python3 navclaw.py -o "上海" -d "家"        # "家" = config.py 中的默认终点

五阶段流水线:
  Phase 1: 🟢 广撒网 → Phase 2: 🟡 精筛选 → Phase 3: 🔴 深加工
  → Phase 4: 🔄 迭代优化 → Phase 5: ⚓ 路线固化
"""

import os, sys, re, json, time, hashlib, math, urllib.parse
from datetime import datetime, timezone, timedelta
from itertools import combinations
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field

# 强制中国时区 (UTC+8)
CN_TZ = timezone(timedelta(hours=8))
from typing import Optional
import requests

# ═══════════════════════════════════════════════════════════════════
# §2  全局配置参数 (USER CONFIG) — 所有参数都有默认值，可通过构造函数覆盖
# 加载共享配置（config.py 不存在时使用内置默认值）
try:
    import config as _cfg
except ImportError:
    _cfg = None

def _c(attr, default):
    """从 config.py 读取，不存在则用默认值"""
    return getattr(_cfg, attr, default)

# ═══════════════════════════════════════════════════════════════════

@dataclass
class PlannerConfig:
    """所有可调参数集中于此。优先读取 config.py，fallback 到内置默认值。"""
    # §2.1 版本
    VERSION: str = "0.1"
    API_KEY: str = field(default_factory=lambda: _c("API_KEY", ""))

    # §2.2 Phase 1 广撒网
    BASELINES: list = field(default_factory=lambda: _c("BASELINES", [32, 36, 38, 39, 35, 1]))
    BASELINE_HW_STRAT: int = field(default_factory=lambda: _c("BASELINE_HW_STRAT", 39))

    # §2.3 Phase 2 精筛选
    PHASE2_TOP_Y: int = field(default_factory=lambda: _c("PHASE2_TOP_Y", 5))
    NOHW_PROTECT: int = field(default_factory=lambda: _c("NOHW_PROTECT", 1))
    SIMILAR_DUR_THRESHOLD: int = field(default_factory=lambda: _c("SIMILAR_DUR_THRESHOLD", 300))
    SIMILAR_RED_THRESHOLD: int = field(default_factory=lambda: _c("SIMILAR_RED_THRESHOLD", 3000))

    # §2.4 Phase 3 深加工 — 拥堵识别
    # TMC 状态: 畅通 / 缓行 / 拥堵 / 严重拥堵 / 未知
    CONGESTION_STATUSES: tuple = field(default_factory=lambda: _c("CONGESTION_STATUSES", ("拥堵", "严重拥堵")))
    MIN_RED_LEN: int = field(default_factory=lambda: _c("MIN_RED_LEN", 1000))
    MERGE_GAP: int = field(default_factory=lambda: _c("MERGE_GAP", 3000))
    MIN_RED_LEN_NOHW: int = field(default_factory=lambda: _c("MIN_RED_LEN_NOHW", 500))
    MERGE_GAP_NOHW: int = field(default_factory=lambda: _c("MERGE_GAP_NOHW", 1000))
    BYPASS_MERGE_GAP: int = field(default_factory=lambda: _c("BYPASS_MERGE_GAP", 10000))
    MAX_BYPASS: int = field(default_factory=lambda: _c("MAX_BYPASS", 7))

    # §2.4 Phase 3 深加工 — 绕行
    BYPASS_STRATEGIES: list = field(default_factory=lambda: _c("BYPASS_STRATEGIES", [35, 33]))
    BEFORE_OFF: int = field(default_factory=lambda: _c("BEFORE_OFF", 4000))
    AFTER_OFF: int = field(default_factory=lambda: _c("AFTER_OFF", 4000))
    API_MAX_WP: int = field(default_factory=lambda: _c("API_MAX_WP", 16))

    # §2.5 Phase 4 迭代优化
    MAX_ITER: int = field(default_factory=lambda: _c("MAX_ITER", 0))
    ITER_CANDIDATES: int = field(default_factory=lambda: _c("ITER_CANDIDATES", 3))

    # §2.6 Phase 5 路线固化
    ANCHOR_COUNT: int = field(default_factory=lambda: _c("ANCHOR_COUNT", 10))

    # §2.7 输出与链接
    SEND_ANDROID: bool = field(default_factory=lambda: _c("SEND_ANDROID", True))
    SEND_IOS: bool = field(default_factory=lambda: _c("SEND_IOS", True))
    SEND_WEB: bool = field(default_factory=lambda: _c("SEND_WEB", False))
    SEARCH_SEC: int = field(default_factory=lambda: _c("SEARCH_SEC", 90))

    # 默认起终点
    DEFAULT_ORIGIN: str = field(default_factory=lambda: _c("DEFAULT_ORIGIN", ""))
    DEFAULT_ORIGIN_COORD: str = field(default_factory=lambda: _c("DEFAULT_ORIGIN_COORD", ""))
    DEFAULT_DEST: str = field(default_factory=lambda: _c("DEFAULT_DEST", ""))
    DEFAULT_DEST_COORD: str = field(default_factory=lambda: _c("DEFAULT_DEST_COORD", ""))
    HOME_KEYWORD: str = field(default_factory=lambda: _c("HOME_KEYWORD", "家"))

    @property
    def link_count(self):
        return int(self.SEND_ANDROID) + int(self.SEND_IOS) + int(self.SEND_WEB)


# ═══════════════════════════════════════════════════════════════════
# §4.1  策略名称映射
# ═══════════════════════════════════════════════════════════════════

STRATEGY_NAMES = {
    # v5 API (32-45) — 全部策略
    32: "默认推荐",     33: "躲避拥堵",     34: "高速优先",     35: "不走高速",
    36: "少收费",       37: "大路优先",     38: "速度最快",     39: "避堵+高速",
    40: "避堵+不走高速", 41: "避堵+少收费",  42: "少收费+不走高速",
    43: "避堵+少收费+不走高速", 44: "避堵+大路", 45: "避堵+速度最快",
    # v3 API (0-9) — 兼容旧策略
    0: "速度优先(v3)", 1: "不走高速(v3)", 2: "费用最少(v3)", 3: "距离最短(v3)",
    4: "多策略(v3)", 5: "不走快速路(v3)", 6: "大路优先(v3)", 7: "高速优先(v3)",
    8: "避免收费(v3)", 9: "躲避拥堵(v3)",
    # v3 多结果策略 (10-20)
    10: "默认多结果(v3)", 11: "时短距短避堵(v3)", 12: "避堵多(v3)",
    13: "不走高速多(v3)", 14: "避收费多(v3)", 15: "避堵+不走高速(v3)",
    16: "避收费+不走高速(v3)", 17: "避堵+避收费(v3)",
    18: "避堵+避收费+不走高速(v3)", 19: "高速优先多(v3)", 20: "避堵+高速(v3)",
}


def strategy_name(s: int) -> str:
    """获取策略名称，未知策略也不报错"""
    return STRATEGY_NAMES.get(s, f"策略{s}")


def strategy_brief(s: int) -> str:
    """获取策略简介（用于消息输出），未知策略也不报错"""
    brief_map = {32: "同APP默认", 39: "避堵+高速"}
    return brief_map.get(s, strategy_name(s))

# ═══════════════════════════════════════════════════════════════════
# §12 节假日高速免费期 (2026-2036)
# ═══════════════════════════════════════════════════════════════════
# 四大免费节日：春节、清明、劳动节、国庆
# 春节：除夕 00:00 至 初七 24:00（8天）
# 清明/劳动/国庆：按国务院假日办公告
# 首日和末日标记为"可能免费"，以实际为准
# 注：未来年份为预估，实际以政府公告为准
# ═══════════════════════════════════════════════════════════════════

# 农历春节（正月初一）日期表 2026-2036
_CNY_DATES = {
    2026: (2, 17), 2027: (2, 6),  2028: (1, 26), 2029: (2, 13), 2030: (2, 3),
    2031: (1, 23), 2032: (2, 11), 2033: (1, 31), 2034: (2, 19), 2035: (2, 8),
    2036: (1, 28),
}

def _generate_toll_free_periods() -> list:
    """生成 2026-2036 年全部高速免费时段（预估）"""
    from datetime import timedelta
    periods = []
    for year in range(2026, 2037):
        # 春节：除夕(初一-1天) 00:00 至 初七(初一+6天) 24:00 = 8天
        cny = _CNY_DATES.get(year)
        if cny:
            cny_dt = datetime(year, cny[0], cny[1])
            periods.append((cny_dt - timedelta(days=1), cny_dt + timedelta(days=7)))

        # 清明：通常 4月4日或4月5日，3天假期
        # 保守取 4月3日-4月7日 覆盖
        periods.append((datetime(year, 4, 3, 0, 0), datetime(year, 4, 7, 0, 0)))

        # 劳动节：5月1日-5月5日（5天）
        periods.append((datetime(year, 5, 1, 0, 0), datetime(year, 5, 6, 0, 0)))

        # 国庆节：10月1日-10月7日（7天），近年常扩至10月8日
        periods.append((datetime(year, 10, 1, 0, 0), datetime(year, 10, 8, 0, 0)))
    return periods

TOLL_FREE_PERIODS = _generate_toll_free_periods()


def is_toll_free(dt: datetime = None) -> str:
    """判断指定时间是否在高速免费期内。
    返回值:
      "free"       — 确定免费（免费期中间日）
      "maybe_free" — 首日或末日（0点分界不可靠，以实际为准）
      "paid"       — 收费 / 超出覆盖年份
    """
    dt = dt or datetime.now(CN_TZ)
    # 去掉时区信息用于比较（TOLL_FREE_PERIODS 是 naive datetime）
    dt_naive = dt.replace(tzinfo=None)
    for s, e in TOLL_FREE_PERIODS:
        if s <= dt_naive < e:
            # 首日 = s.date()，末日 = (e - timedelta(seconds=1)).date()
            first_day = s.date()
            last_day = (e - timedelta(seconds=1)).date()
            if dt_naive.date() == first_day or dt_naive.date() == last_day:
                return "maybe_free"
            return "free"
    return "paid"


# ═══════════════════════════════════════════════════════════════════
# 辅助工具
# ═══════════════════════════════════════════════════════════════════

def fmt_dur(sec: int) -> str:
    h, m = divmod(int(sec), 3600)
    m = m // 60
    return f"{h}h{m:02d}m"

def fmt_dist(m: float) -> str:
    return f"{m/1000:.0f}km"

def fmt_pct(ratio: float) -> str:
    return f"{ratio*100:.0f}%"

def fmt_cost(cost: int, toll_state: str = "paid") -> str:
    """格式化收费。以 API 返回金额为准，内置免费日历仅做提示。
    toll_state: "free" / "maybe_free" / "paid"
    """
    if cost == 0:
        return "免费"
    if toll_state == "free":
        return f"¥{cost}(免费期)"
    if toll_state == "maybe_free":
        return f"¥{cost}(可能免费)"
    return f"¥{cost}"

def parse_polyline(poly_str: str) -> list:
    if not poly_str:
        return []
    pts = []
    for seg in poly_str.split(";"):
        parts = seg.split(",")
        if len(parts) == 2:
            try:
                pts.append((float(parts[0]), float(parts[1])))
            except ValueError:
                pass
    return pts

def polyline_cumulative_dist(pts: list) -> list:
    dists = [0.0]
    for i in range(1, len(pts)):
        d = haversine(pts[i-1], pts[i])
        dists.append(dists[-1] + d)
    return dists

def haversine(p1: tuple, p2: tuple) -> float:
    R = 6371000
    lng1, lat1 = math.radians(p1[0]), math.radians(p1[1])
    lng2, lat2 = math.radians(p2[0]), math.radians(p2[1])
    dlat = lat2 - lat1
    dlng = lng2 - lng1
    a = math.sin(dlat/2)**2 + math.cos(lat1)*math.cos(lat2)*math.sin(dlng/2)**2
    return R * 2 * math.asin(math.sqrt(a))

def wp_fingerprint(waypoints: list, origin: str, dest: str) -> str:
    raw = f"{origin}|{dest}|" + "|".join(f"{w[0]:.6f},{w[1]:.6f}" for w in waypoints)
    return hashlib.md5(raw.encode()).hexdigest()[:12]

def point_at_fraction(pts: list, cum_dists: list, fraction: float) -> tuple:
    target = cum_dists[-1] * max(0.0, min(1.0, fraction))
    for i in range(1, len(cum_dists)):
        if cum_dists[i] >= target:
            seg_len = cum_dists[i] - cum_dists[i-1]
            if seg_len < 1e-6:
                return pts[i]
            t = (target - cum_dists[i-1]) / seg_len
            lng = pts[i-1][0] + t * (pts[i][0] - pts[i-1][0])
            lat = pts[i-1][1] + t * (pts[i][1] - pts[i-1][1])
            return (lng, lat)
    return pts[-1]


# ═══════════════════════════════════════════════════════════════════
# §4.4  导航 API 封装 (当前: Amap)
# ═══════════════════════════════════════════════════════════════════

class AmapAPI:
    BASE_GEO = "https://restapi.amap.com/v3/geocode/geo"
    BASE_DRIVE = "https://restapi.amap.com/v5/direction/driving"

    def __init__(self, api_key: str):
        self.key = api_key
        self.session = requests.Session()
        self.api_call_count = 0

    def geocode(self, address: str, city: str = "") -> Optional[str]:
        variants = [address]
        # 去掉括号但保留内容: "XX店(某某市)" → "XX店某某市"
        stripped = re.sub(r'[（()]', '', re.sub(r'[）)]', '', address)).strip()
        if stripped and stripped != address:
            variants.append(stripped)
        # 去掉括号内容: "XX店(某某市)" → "XX店"
        no_paren = re.sub(r'[（(][^）)]*[）)]', '', address).strip()
        if no_paren and no_paren != address and no_paren != stripped:
            variants.append(no_paren)
        m = re.search(r'([\u4e00-\u9fff]{2,3}(?:市|县|区|州))', address)
        city_hint = m.group(1) if m else city
        for v in variants:
            coord = self._try_geocode(v, city_hint)
            if coord:
                return coord
        return None

    def _try_geocode(self, address: str, city: str = "") -> Optional[str]:
        params = {"key": self.key, "address": address}
        if city:
            params["city"] = city
        try:
            self.api_call_count += 1
            r = self.session.get(self.BASE_GEO, params=params, timeout=10)
            data = r.json()
            if data.get("status") == "1" and data.get("geocodes"):
                loc = data["geocodes"][0].get("location", "")
                if loc:
                    return loc
        except Exception as e:
            print(f"  ⚠️ geocode 异常: {e}")
        return None

    def drive_route(self, origin: str, dest: str, strategy: int = 39,
                    waypoints: list = None,
                    show_fields: str = "cost,tmcs,polyline") -> dict:
        params = {
            "key": self.key,
            "origin": origin,
            "destination": dest,
            "strategy": str(strategy),
            "show_fields": show_fields,
        }
        if waypoints:
            wp_str = ";".join(f"{w[0]:.6f},{w[1]:.6f}" for w in waypoints)
            params["waypoints"] = wp_str
        try:
            self.api_call_count += 1
            r = self.session.get(self.BASE_DRIVE, params=params, timeout=15)
            return r.json()
        except Exception as e:
            print(f"  ⚠️ drive_route 异常 (s{strategy}): {e}")
            return {}


# ═══════════════════════════════════════════════════════════════════
# 数据结构
# ═══════════════════════════════════════════════════════════════════

@dataclass
class RouteInfo:
    label: str
    strategy: int
    route_type: str       # '基准' or '绕行'
    desc: str
    duration: int = 0
    distance: int = 0
    toll_distance: int = 0
    toll_cost: int = 0
    red_len: int = 0
    polyline_str: str = ""
    tmcs: list = field(default_factory=list)
    waypoints: list = field(default_factory=list)
    fingerprint: str = ""
    bypassed_indices: list = field(default_factory=list)
    tags: list = field(default_factory=list)

    @property
    def hw_pct(self) -> float:
        return self.toll_distance / max(self.distance, 1)

    @property
    def red_pct(self) -> float:
        return self.red_len / max(self.distance, 1)

    @property
    def is_nohw(self) -> bool:
        return self.hw_pct < 0.1


@dataclass
class CongestionCluster:
    idx: int
    start_dist: float
    end_dist: float
    total_red: float
    segments: list = field(default_factory=list)

    @property
    def length(self) -> float:
        return self.end_dist - self.start_dist


# ═══════════════════════════════════════════════════════════════════
# §8  导航链接
# ═══════════════════════════════════════════════════════════════════

def build_nav_links(origin_coord: str, origin_name: str,
                    dest_coord: str, dest_name: str,
                    waypoints: list = None, cfg: PlannerConfig = None) -> list:
    cfg = cfg or PlannerConfig()
    links = []
    olng, olat = origin_coord.split(",")
    dlng, dlat = dest_coord.split(",")

    wp_params_app = ""
    wp_params_web = ""
    if waypoints:
        n = len(waypoints)
        lons = "|".join(f"{w[0]:.6f}" for w in waypoints)
        lats = "|".join(f"{w[1]:.6f}" for w in waypoints)
        names = "|".join(f"途经{i+1}" for i in range(n))
        wp_params_app = f"&vian={n}&vialons={lons}&vialats={lats}&vianames={names}"
        via_parts = "|".join(f"{w[0]:.6f},{w[1]:.6f},途经{i+1}" for i, w in enumerate(waypoints))
        wp_params_web = f"&via={via_parts}"

    base_app = (f"slat={olat}&slon={olng}&sname={urllib.parse.quote(origin_name)}"
                f"&dlat={dlat}&dlon={dlng}&dname={urllib.parse.quote(dest_name)}"
                f"&dev=0&t=0&m=4&sourceApplication=NavClaw{wp_params_app}")

    if cfg.SEND_ANDROID:
        links.append(("Android", f"amapuri://route/plan/?{base_app}"))
    if cfg.SEND_IOS:
        links.append(("iOS", f"iosamap://route/plan/?{base_app}"))
    if cfg.SEND_WEB:
        web_url = (f"https://uri.amap.com/navigation?"
                   f"from={olng},{olat},{urllib.parse.quote(origin_name)}"
                   f"&to={dlng},{dlat},{urllib.parse.quote(dest_name)}"
                   f"{wp_params_web}&mode=car&callnative=0")
        links.append(("Web", web_url))
    return links


# ═══════════════════════════════════════════════════════════════════
# 核心引擎
# ═══════════════════════════════════════════════════════════════════

class RoutePlanner:

    def __init__(self, cfg: PlannerConfig = None):
        self.cfg = cfg or PlannerConfig()
        self.api = AmapAPI(self.cfg.API_KEY)
        self.toll_free = is_toll_free()
        self.start_time = 0.0

        self.baselines: list[RouteInfo] = []
        self.seeds: list[RouteInfo] = []
        self.bypass_routes: list[RouteInfo] = []
        self.all_routes: list[RouteInfo] = []

        self.origin_coord = ""
        self.origin_name = ""
        self.dest_coord = ""
        self.dest_name = ""

        self.s1_polyline: list = []
        self.s1_cum_dists: list = []
        self.s1_total_dist: float = 0.0

        self.bypass_success = 0
        self.bypass_total = 0
        self.total_clusters = 0
        self.log_lines: list[str] = []
        self.phase_stats: dict = {}  # phase → {api_calls, elapsed, detail}
        self.fixation_comparison: list = []  # [(orig, fixed), ...]

    def _log(self, msg: str):
        print(msg)
        self.log_lines.append(msg)

    # ─────── 入口 ───────
    def run(self, origin: str = None, dest: str = None) -> dict:
        self.start_time = time.time()
        origin = origin or self.cfg.DEFAULT_ORIGIN
        dest = dest or self.cfg.DEFAULT_DEST
        # "家" → 使用预设坐标跳过 geocode；其他地址一律 geocode
        use_cached_dest = dest.strip() == self.cfg.HOME_KEYWORD
        use_cached_origin = False  # origin 无快捷词，暂不缓存
        if use_cached_dest:
            dest = self.cfg.DEFAULT_DEST

        self._log(f"🎯 NavClaw v{self.cfg.VERSION} 启动")
        self._log(f"  起点: {origin}")
        self._log(f"  终点: {dest}")

        self.origin_name = origin
        self.dest_name = dest

        def _valid_coord(s: str) -> bool:
            return bool(s and re.match(r'^\d+\.\d+,\d+\.\d+$', s.strip()))

        if use_cached_origin and _valid_coord(self.cfg.DEFAULT_ORIGIN_COORD):
            self.origin_coord = self.cfg.DEFAULT_ORIGIN_COORD.strip()
            self._log(f"  起点坐标(缓存): {self.origin_coord}")
        else:
            self.origin_coord = self._resolve_coord(origin)
        if use_cached_dest and _valid_coord(self.cfg.DEFAULT_DEST_COORD):
            self.dest_coord = self.cfg.DEFAULT_DEST_COORD.strip()
            self._log(f"  终点坐标(缓存): {self.dest_coord}")
        else:
            self.dest_coord = self._resolve_coord(dest)

        if not self.origin_coord or not self.dest_coord:
            self._log("❌ 无法解析起终点坐标，终止。")
            return {"messages": ["❌ 无法解析起终点坐标"], "log_path": ""}

        self._log(f"  起点坐标: {self.origin_coord}")
        self._log(f"  终点坐标: {self.dest_coord}")
        toll_label = {"free": "是(免费期)", "maybe_free": "可能(首/末日)", "paid": "否"}
        self._log(f"  高速免费(内置日历): {toll_label.get(self.toll_free, '未知')}  ← 实际以API返回金额为准")
        self._log("")

        self._phase1_broad_search()
        self._phase2_smart_filter()
        self._phase3_deep_optimize()
        self._phase4_iteration()
        self._phase5_fixation()

        elapsed = time.time() - self.start_time
        messages = self._build_messages(elapsed)
        log_path = self._save_log(elapsed)
        return {"messages": messages, "log_path": log_path}

    def _resolve_coord(self, name_or_coord: str) -> str:
        if re.match(r'^\d+\.\d+,\d+\.\d+$', name_or_coord.strip()):
            return name_or_coord.strip()
        coord = self.api.geocode(name_or_coord)
        if coord:
            return coord
        self._log(f"  ⚠️ 地理编码失败: {name_or_coord}")
        return ""

    # ═══════════════════════ Phase 1 ═══════════════════════
    def _phase1_broad_search(self):
        self._log("═" * 60)
        self._log("🟢 Phase 1: 广撒网 (Broad Search)")
        self._log("═" * 60)
        t0 = time.time()
        results = {}

        with ThreadPoolExecutor(max_workers=5) as pool:
            futures = {}
            for strat in self.cfg.BASELINES:
                f = pool.submit(self.api.drive_route,
                                self.origin_coord, self.dest_coord, strat)
                futures[f] = strat
            for f in as_completed(futures):
                strat = futures[f]
                try:
                    results[strat] = f.result()
                except Exception as e:
                    self._log(f"  ⚠️ s{strat} 查询异常: {e}")

        for strat in self.cfg.BASELINES:
            data = results.get(strat, {})
            if data.get("status") != "1" or not data.get("route", {}).get("paths"):
                self._log(f"  ⚠️ s{strat} 无有效结果")
                continue
            paths = data["route"]["paths"]
            for idx, path in enumerate(paths, 1):
                label = f"s{strat}-{idx}"
                route = self._parse_path(path, label, strat)
                self.baselines.append(route)
                # 非高速 polyline 优先从 s35 获取（v5原生，2条），fallback s1
                if strat == 35 and idx == 1 and not self.s1_polyline:
                    self.s1_polyline = parse_polyline(route.polyline_str)
                    if self.s1_polyline:
                        self.s1_cum_dists = polyline_cumulative_dist(self.s1_polyline)
                        self.s1_total_dist = self.s1_cum_dists[-1] if self.s1_cum_dists else 0
                if strat == 1 and idx == 1 and not self.s1_polyline:
                    self.s1_polyline = parse_polyline(route.polyline_str)
                    if self.s1_polyline:
                        self.s1_cum_dists = polyline_cumulative_dist(self.s1_polyline)
                        self.s1_total_dist = self.s1_cum_dists[-1] if self.s1_cum_dists else 0

        elapsed_p1 = time.time() - t0
        api_p1 = len(self.cfg.BASELINES)
        self.phase_stats["Phase 1"] = {"api_calls": api_p1, "elapsed": elapsed_p1}
        self._log(f"\n  📊 Phase 1: {len(self.baselines)} 条原始路线, "
                  f"{api_p1} 次 API, {elapsed_p1:.1f}s")
        for r in self.baselines:
            cost_str = fmt_cost(r.toll_cost, self.toll_free)
            self._log(f"    {r.label:8s} | {fmt_dur(r.duration):>7s} | {fmt_dist(r.distance):>6s} "
                      f"| 高速{fmt_pct(r.hw_pct):>4s} | 拥堵{fmt_pct(r.red_pct):>4s} | {cost_str}")

        # ── 基准多样性分析 ──
        self._log("\n  ── 基准多样性分析 ──")
        by_strat = {}
        for r in self.baselines:
            by_strat.setdefault(r.strategy, []).append(r)
        for s, routes in by_strat.items():
            self._log(f"    s{s}({strategy_name(s)}): 返回 {len(routes)} 条")

        # 用 (distance, duration, toll_distance) 近似判断路线是否实质相同
        def route_sig(r):
            return (round(r.distance / 1000), round(r.duration / 60), round(r.toll_distance / 1000))
        sig_map = {}  # sig → [labels]
        for r in self.baselines:
            sig = route_sig(r)
            sig_map.setdefault(sig, []).append(r.label)
        unique_sigs = len(sig_map)
        dup_groups = [(sig, labels) for sig, labels in sig_map.items() if len(labels) > 1]
        self._log(f"\n    独立路线: {unique_sigs} 条（基于 距离/时间/高速里程 判断）")
        if dup_groups:
            self._log(f"    重复组:")
            for sig, labels in dup_groups:
                dist_km, dur_min, hw_km = sig
                self._log(f"      {dist_km}km/{dur_min}min/高速{hw_km}km → "
                          f"{' = '.join(labels)}")
        else:
            self._log(f"    无重复路线 ✅")

    def _parse_path(self, path: dict, label: str, strategy: int,
                    route_type: str = "基准", desc: str = "",
                    waypoints: list = None, bypassed: list = None) -> RouteInfo:
        # v5 API: distance 在顶层(字符串), duration 在 cost 里
        distance = int(path.get("distance", 0))
        cost_info = path.get("cost", {})
        duration = int(cost_info.get("duration", 0)) if cost_info else 0
        toll_cost = int(cost_info.get("tolls", 0)) if cost_info else 0
        toll_distance = int(cost_info.get("toll_distance", 0)) if cost_info else 0

        tmcs = []
        red_len = 0
        all_polylines = []
        for step in path.get("steps", []):
            step_poly = step.get("polyline", "")
            if step_poly:
                all_polylines.append(step_poly)
            for tmc in step.get("tmcs", []):
                tmc_status = tmc.get("tmc_status", "")
                tmc_dist = int(tmc.get("tmc_distance", 0))
                tmcs.append({"status": tmc_status, "distance": tmc_dist,
                             "polyline": tmc.get("tmc_polyline", "")})
                if tmc_status in self.cfg.CONGESTION_STATUSES:
                    red_len += tmc_dist

        full_polyline = ";".join(all_polylines)
        wps = waypoints or []

        # 指纹：有途经点用途经点hash；无途经点（基准）用 距离+耗时+高速占比 区分
        if wps:
            fp = wp_fingerprint(wps, self.origin_coord, self.dest_coord)
        else:
            raw = f"{self.origin_coord}|{self.dest_coord}|{distance}|{duration}|{toll_distance}"
            fp = hashlib.md5(raw.encode()).hexdigest()[:12]

        return RouteInfo(
            label=label, strategy=strategy, route_type=route_type,
            desc=desc or strategy_name(strategy),
            duration=duration, distance=distance,
            toll_distance=toll_distance,
            toll_cost=toll_cost,
            red_len=red_len, polyline_str=full_polyline,
            tmcs=tmcs, waypoints=wps, fingerprint=fp,
            bypassed_indices=bypassed or [],
        )

    # ═══════════════════════ Phase 2 ═══════════════════════
    def _phase2_smart_filter(self):
        self._log(f"\n{'═'*60}")
        self._log("🟡 Phase 2: 精筛选 (Smart Filter)")
        self._log("═" * 60)
        t0 = time.time()
        if not self.baselines:
            self._log("  ⚠️ 无基准路线，跳过")
            return

        count_orig = len(self.baselines)

        # Step 1: 指纹去重
        seen_fp = {}
        deduped = []
        for r in self.baselines:
            if r.fingerprint not in seen_fp:
                seen_fp[r.fingerprint] = r
                deduped.append(r)
            else:
                self._log(f"  去重: {r.label} 与 {seen_fp[r.fingerprint].label} 重复")
        count_dedup = len(deduped)

        # Step 2: 相似度剔除
        deduped.sort(key=lambda r: r.duration)
        filtered = []
        for r in deduped:
            is_similar = False
            for kept in filtered:
                dur_diff = abs(r.duration - kept.duration)
                red_diff = abs(r.red_len - kept.red_len)
                if dur_diff < self.cfg.SIMILAR_DUR_THRESHOLD and red_diff < self.cfg.SIMILAR_RED_THRESHOLD:
                    is_similar = True
                    self._log(f"  相似剔除: {r.label} ≈ {kept.label}")
                    break
            if not is_similar:
                filtered.append(r)
        count_filtered = len(filtered)

        # Step 3: Top Y 选拔
        nohw_routes = sorted([r for r in filtered if r.is_nohw], key=lambda r: r.duration)
        protected = nohw_routes[:self.cfg.NOHW_PROTECT]
        protected_fps = {r.fingerprint for r in protected}
        remaining = sorted([r for r in filtered if r.fingerprint not in protected_fps],
                           key=lambda r: r.duration)
        seats_left = self.cfg.PHASE2_TOP_Y - len(protected)
        self.seeds = protected + remaining[:max(0, seats_left)]

        self._log(f"\n  📊 Phase 2: {count_orig} 条 → 去重 {count_dedup} → "
                  f"过滤 {count_filtered} → 种子 {len(self.seeds)}")
        self.phase_stats["Phase 2"] = {"api_calls": 0, "elapsed": time.time() - t0}
        for r in self.seeds:
            tag = " [非高速保护]" if r.fingerprint in protected_fps else ""
            self._log(f"    {r.label:8s} | {fmt_dur(r.duration):>7s} | "
                      f"高速{fmt_pct(r.hw_pct):>4s} | 拥堵{fmt_pct(r.red_pct):>4s}{tag}")

    # ═══════════════════════ Phase 3 ═══════════════════════
    def _phase3_deep_optimize(self):
        self._log(f"\n{'═'*60}")
        self._log("🔴 Phase 3: 深加工 (Deep Optimization)")
        self._log("═" * 60)
        t0 = time.time()
        api_before = self.api.api_call_count
        if not self.seeds:
            self._log("  ⚠️ 无种子路线，跳过")
            return
        if not self.s1_polyline:
            self._log("  ⚠️ 无 s1 polyline，无法生成绕行途经点，跳过")
            return

        all_clusters_by_seed = {}
        for seed in self.seeds:
            is_hw = not seed.is_nohw
            min_red = self.cfg.MIN_RED_LEN if is_hw else self.cfg.MIN_RED_LEN_NOHW
            merge_gap = self.cfg.MERGE_GAP if is_hw else self.cfg.MERGE_GAP_NOHW
            clusters, summary = self._identify_congestion(seed, min_red, merge_gap)

            self._log(f"\n  {seed.label} ({'高速' if is_hw else '非高速'}, "
                      f"{fmt_dist(seed.distance)}):")
            self._log(f"    TMC拥堵总长: {summary['total_tmc_red']/1000:.1f}km "
                      f"(原始{summary['raw_segments']}段, "
                      f"达标{summary['qualified_segments']}段, "
                      f"过小忽略{summary['small_ignored']}段)")
            if summary['raw_details']:
                for i, (s, e, l, st) in enumerate(summary['raw_details'], 1):
                    self._log(f"      原始段{i}: {s/1000:.1f}~{e/1000:.1f}km, "
                              f"长{l/1000:.1f}km [{st}]")
            if summary['merge1_count'] > 0:
                self._log(f"    一次合并: {summary['merge1_count']}次 "
                          f"(间距<{merge_gap/1000:.0f}km)")
            if summary['merge2_count'] > 0:
                self._log(f"    二次合并: {summary['merge2_count']}次 "
                          f"(间距<{self.cfg.BYPASS_MERGE_GAP/1000:.0f}km)")
            if clusters:
                all_clusters_by_seed[seed.label] = (seed, clusters)
                self._log(f"    → 最终 {len(clusters)} 个拥堵聚合段:")
                for c in clusters:
                    self._log(f"      堵{c.idx}: {c.start_dist/1000:.1f}~"
                              f"{c.end_dist/1000:.1f}km, 覆盖{c.total_red/1000:.1f}km")
            else:
                self._log(f"    → 无拥堵段")

        if not all_clusters_by_seed:
            self._log("\n  ℹ️ 所有种子均无拥堵，跳过绕行")
            return

        # 只对高速路线种子生成绕行方案（非高速种子的拥堵不适合高速绕行逻辑）
        for seed_label, (seed, clusters) in all_clusters_by_seed.items():
            if seed.is_nohw:
                self._log(f"  {seed.label}: 非高速路线，跳过绕行生成（拥堵在非高速段）")
                continue
            self.total_clusters = max(self.total_clusters, len(clusters))
            self._generate_bypass_routes(seed, clusters)

        api_p3 = self.api.api_call_count - api_before
        self.phase_stats["Phase 3"] = {"api_calls": api_p3, "elapsed": time.time() - t0}
        self._log(f"\n  📊 Phase 3: 绕行成功 {self.bypass_success}/{self.bypass_total}, "
                  f"{api_p3} 次 API, {time.time()-t0:.1f}s")

    def _identify_congestion(self, route: RouteInfo, min_red_len: int,
                             merge_gap: int) -> tuple:
        """返回 (clusters, summary_dict)"""
        red_segments = []
        cum_dist = 0
        total_tmc_red = 0  # 所有拥堵TMC的总长（含不达标的）
        small_ignored = 0  # 被 min_red_len 过滤掉的小段数
        for tmc in route.tmcs:
            dist = tmc["distance"]
            if tmc["status"] in self.cfg.CONGESTION_STATUSES:
                total_tmc_red += dist
                if dist >= min_red_len:
                    red_segments.append({"start": cum_dist, "end": cum_dist + dist,
                                         "length": dist, "status": tmc["status"]})
                else:
                    small_ignored += 1
            cum_dist += dist

        summary = {
            "total_tmc_red": total_tmc_red,
            "raw_segments": len(red_segments) + small_ignored,
            "qualified_segments": len(red_segments),
            "small_ignored": small_ignored,
            "merge1_count": 0,
            "merge2_count": 0,
            "raw_details": [(s["start"], s["end"], s["length"], s.get("status", ""))
                            for s in red_segments],
        }
        if not red_segments:
            return [], summary

        # 一次合并
        merged = [red_segments[0].copy()]
        merge1_ops = 0
        for seg in red_segments[1:]:
            if seg["start"] - merged[-1]["end"] < merge_gap:
                merged[-1]["end"] = seg["end"]
                merged[-1]["length"] = merged[-1]["end"] - merged[-1]["start"]
                merge1_ops += 1
            else:
                merged.append(seg.copy())
        summary["merge1_count"] = merge1_ops

        # 二次合并
        second = [merged[0].copy()]
        merge2_ops = 0
        for seg in merged[1:]:
            if seg["start"] - second[-1]["end"] < self.cfg.BYPASS_MERGE_GAP:
                second[-1]["end"] = seg["end"]
                second[-1]["length"] = second[-1]["end"] - second[-1]["start"]
                merge2_ops += 1
            else:
                second.append(seg.copy())
        summary["merge2_count"] = merge2_ops

        # 裁剪
        if len(second) > self.cfg.MAX_BYPASS:
            second.sort(key=lambda s: s["length"], reverse=True)
            second = second[:self.cfg.MAX_BYPASS]
            second.sort(key=lambda s: s["start"])

        clusters = [CongestionCluster(idx=i+1, start_dist=s["start"],
                                      end_dist=s["end"], total_red=s["length"])
                    for i, s in enumerate(second)]
        return clusters, summary

    def _generate_bypass_routes(self, seed: RouteInfo, clusters: list):
        total_seed_dist = seed.distance
        cluster_wps = {}
        for c in clusters:
            r_start = c.start_dist / max(total_seed_dist, 1)
            r_end = c.end_dist / max(total_seed_dist, 1)
            span = r_end - r_start
            if span < 0.001:
                continue
            mid1 = point_at_fraction(self.s1_polyline, self.s1_cum_dists,
                                     r_start + span * 0.33)
            mid2 = point_at_fraction(self.s1_polyline, self.s1_cum_dists,
                                     r_start + span * 0.67)
            cluster_wps[c.idx] = [mid1, mid2]
        if not cluster_wps:
            return

        cluster_indices = sorted(cluster_wps.keys())
        n = len(cluster_indices)
        combos = []
        for r in range(1, n + 1):
            for combo in combinations(cluster_indices, r):
                total_wps = sum(len(cluster_wps[i]) for i in combo)
                if total_wps <= self.cfg.API_MAX_WP:
                    combos.append(combo)

        self._log(f"\n  {seed.label}: {len(combos)} 组合 × "
                  f"{len(self.cfg.BYPASS_STRATEGIES)} 策略 = "
                  f"{len(combos)*len(self.cfg.BYPASS_STRATEGIES)} 查询")

        bypass_k = [0]
        with ThreadPoolExecutor(max_workers=8) as pool:
            futures = {}
            for combo in combos:
                wps = []
                for idx in combo:
                    wps.extend(cluster_wps[idx])
                for strat in self.cfg.BYPASS_STRATEGIES:
                    bypass_k[0] += 1
                    self.bypass_total += 1
                    f = pool.submit(self.api.drive_route,
                                    self.origin_coord, self.dest_coord, strat, wps)
                    futures[f] = (combo, strat, list(wps), bypass_k[0])

            for f in as_completed(futures):
                combo, strat, wps, k = futures[f]
                try:
                    data = f.result()
                    if data.get("status") == "1" and data.get("route", {}).get("paths"):
                        path = data["route"]["paths"][0]
                        combo_desc = self._combo_desc(combo, n)
                        label = f"s{strat}-{seed.label.split('-')[0][1:]}-{k}"
                        route = self._parse_path(
                            path, label, strat, route_type="绕行",
                            desc=combo_desc, waypoints=wps, bypassed=list(combo))
                        self.bypass_routes.append(route)
                        self.bypass_success += 1
                except Exception as e:
                    self._log(f"    ⚠️ 绕行异常: {e}")

    def _combo_desc(self, combo: tuple, total: int) -> str:
        parts = "、".join(str(i) for i in combo)
        return f"绕行堵{parts}/{total}"

    # ═══════════════════════ Phase 4 ═══════════════════════
    def _phase4_iteration(self):
        if self.cfg.MAX_ITER <= 0:
            self._log(f"\n{'═'*60}")
            self._log("🔄 Phase 4: 迭代优化 — 已跳过 (MAX_ITER=0)")
            self._log("═" * 60)
            self.phase_stats["Phase 4"] = {"api_calls": 0, "elapsed": 0, "iterations": []}
            return

        self._log(f"\n{'═'*60}")
        self._log("🔄 Phase 4: 迭代优化 (Iteration)")
        self._log("═" * 60)
        t0_total = time.time()
        api_before_total = self.api.api_call_count
        iter_stats = []

        if not self.bypass_routes:
            self._log("  ⚠️ 无绕行方案，跳过")
            self.phase_stats["Phase 4"] = {"api_calls": 0, "elapsed": 0, "iterations": []}
            return

        # 给 Phase 3 的绕行方案加 iter0 后缀
        for r in self.bypass_routes:
            if not r.label.endswith("-iter0"):
                r.label = r.label + "-iter0"

        for it in range(self.cfg.MAX_ITER):
            self._log(f"\n  ── 迭代 {it+1}/{self.cfg.MAX_ITER} ──")
            t0_iter = time.time()
            api_before_iter = self.api.api_call_count
            iter_new = 0

            candidates = sorted(self.bypass_routes, key=lambda r: r.duration)
            candidates = candidates[:self.cfg.ITER_CANDIDATES]
            for cand in candidates:
                clusters, _summary = self._identify_congestion(
                    cand, self.cfg.MIN_RED_LEN_NOHW, self.cfg.MERGE_GAP_NOHW)
                if not clusters:
                    continue
                existing_wps = list(cand.waypoints)
                new_wps = []
                for c in clusters:
                    r_s = c.start_dist / max(cand.distance, 1)
                    r_e = c.end_dist / max(cand.distance, 1)
                    span = r_e - r_s
                    if span < 0.001:
                        continue
                    new_wps.append(point_at_fraction(
                        self.s1_polyline, self.s1_cum_dists, r_s + span * 0.33))
                    new_wps.append(point_at_fraction(
                        self.s1_polyline, self.s1_cum_dists, r_s + span * 0.67))
                merged_wps = (existing_wps + new_wps)[:self.cfg.API_MAX_WP]
                for strat in self.cfg.BYPASS_STRATEGIES:
                    self.bypass_total += 1
                    data = self.api.drive_route(
                        self.origin_coord, self.dest_coord, strat, merged_wps)
                    if data.get("status") == "1" and data.get("route", {}).get("paths"):
                        path = data["route"]["paths"][0]
                        label = f"{cand.label.replace('-iter0','')}-iter{it+1}"
                        route = self._parse_path(
                            path, label, strat, route_type="绕行",
                            desc=f"迭代{it+1}", waypoints=merged_wps)
                        if self.s1_total_dist > 0 and route.distance > 1.5 * self.s1_total_dist:
                            continue
                        if any(r.fingerprint == route.fingerprint for r in self.bypass_routes):
                            continue
                        self.bypass_routes.append(route)
                        self.bypass_success += 1
                        iter_new += 1
                        self._log(f"    新增 {label}: {fmt_dur(route.duration)}")

            api_iter = self.api.api_call_count - api_before_iter
            elapsed_iter = time.time() - t0_iter
            iter_stats.append({"iter": it+1, "api_calls": api_iter,
                               "elapsed": elapsed_iter, "new_routes": iter_new})
            self._log(f"\n  📊 迭代{it+1}: {api_iter} 次 API, {elapsed_iter:.1f}s, "
                      f"新增 {iter_new} 条")

        api_p4 = self.api.api_call_count - api_before_total
        elapsed_p4 = time.time() - t0_total
        self.phase_stats["Phase 4"] = {"api_calls": api_p4, "elapsed": elapsed_p4,
                                        "iterations": iter_stats}
        self._log(f"\n  📊 Phase 4 合计: {api_p4} 次 API, {elapsed_p4:.1f}s")

    # ═══════════════════════ Phase 5 ═══════════════════════
    def _phase5_fixation(self):
        self._log(f"\n{'═'*60}")
        self._log("⚓ Phase 5: 路线固化与交付 (Fixation)")
        self._log("═" * 60)
        t0 = time.time()
        api_before = self.api.api_call_count

        # 锚点生成 — 先去重（避免重复fixate浪费API+策略漂移）
        self._log("\n  ── 锚点生成 ──")
        seen_fp = {}
        unique_baselines = []
        for r in self.baselines:
            if r.fingerprint not in seen_fp:
                seen_fp[r.fingerprint] = r
                unique_baselines.append(r)
        self._log(f"    基准去重: {len(self.baselines)} → {len(unique_baselines)} 条")

        anchored = []
        for r in unique_baselines:
            poly = parse_polyline(r.polyline_str)
            if not poly or len(poly) < 3:
                continue
            cum_dists = polyline_cumulative_dist(poly)
            n_anchors = min(self.cfg.ANCHOR_COUNT, self.cfg.API_MAX_WP)
            ancs = []
            for i in range(1, n_anchors + 1):
                frac = i / (n_anchors + 1)
                ancs.append(point_at_fraction(poly, cum_dists, frac))

            data = self.api.drive_route(
                self.origin_coord, self.dest_coord, r.strategy, ancs)
            if data.get("status") == "1" and data.get("route", {}).get("paths"):
                path = data["route"]["paths"][0]
                fixed = self._parse_path(
                    path, r.label + "-fix", r.strategy,
                    route_type="基准", desc=f"{r.desc}(固化)", waypoints=ancs)
                anchored.append(fixed)
                self.fixation_comparison.append((r, fixed))
                self._log(f"    {r.label} → 固化 OK ({n_anchors}锚点)")
            else:
                self._log(f"    {r.label} → 固化失败")

        # 固化前后对比日志
        if self.fixation_comparison:
            self._log("\n  ── 固化前后对比 ──")
            self._log(f"  {'标签':12s} | {'原时间':>7s} → {'固时间':>7s} | "
                      f"{'原里程':>6s} → {'固里程':>6s} | "
                      f"{'原堵%':>5s} → {'固堵%':>5s} | "
                      f"{'原收费':>6s} → {'固收费':>6s}")
            self._log(f"  {'-'*12}-+-{'-'*17}-+-{'-'*15}-+-{'-'*13}-+-{'-'*15}")
            for orig, fixed in self.fixation_comparison:
                self._log(
                    f"  {orig.label:12s} | {fmt_dur(orig.duration):>7s} → {fmt_dur(fixed.duration):>7s} | "
                    f"{fmt_dist(orig.distance):>6s} → {fmt_dist(fixed.distance):>6s} | "
                    f"{fmt_pct(orig.red_pct):>5s} → {fmt_pct(fixed.red_pct):>5s} | "
                    f"{fmt_cost(orig.toll_cost, self.toll_free):>6s} → "
                    f"{fmt_cost(fixed.toll_cost, self.toll_free):>6s}")

        # 用固化版替换原始基准（不同时保留两者）
        anchored_map = {}
        for a in anchored:
            orig_label = a.label.replace("-fix", "")
            anchored_map[orig_label] = a

        replaced_baselines = []
        for r in unique_baselines:
            if r.label in anchored_map:
                replaced_baselines.append(anchored_map[r.label])
            else:
                replaced_baselines.append(r)

        self.all_routes = replaced_baselines + self.bypass_routes
        # 去重
        seen = {}
        unique = []
        for r in self.all_routes:
            if r.fingerprint not in seen:
                seen[r.fingerprint] = r
                unique.append(r)
            elif r.duration < seen[r.fingerprint].duration:
                unique = [r if x.fingerprint == r.fingerprint else x for x in unique]
                seen[r.fingerprint] = r
        self.all_routes = unique
        self._assign_tags()

        api_p5 = self.api.api_call_count - api_before
        elapsed_p5 = time.time() - t0
        self.phase_stats["Phase 5"] = {"api_calls": api_p5, "elapsed": elapsed_p5}
        self._log(f"\n  📊 Phase 5: 全部方案 {len(self.all_routes)} 条, "
                  f"{api_p5} 次 API, {elapsed_p5:.1f}s")

    def _assign_tags(self):
        baselines = [r for r in self.all_routes if r.route_type == "基准"]
        bypasses = [r for r in self.all_routes if r.route_type == "绕行"]
        def tag_min(routes, key, tag):
            if routes:
                best = min(routes, key=key)
                best.tags.append(tag)
        tag_min(self.all_routes, lambda r: r.duration, "🏆全局最快")
        tag_min(baselines, lambda r: r.duration, "⏱基准最快")
        tag_min(bypasses, lambda r: r.duration, "⏱绕行最快")
        tag_min(self.all_routes, lambda r: r.red_len, "⚡全局少堵")
        tag_min(baselines, lambda r: r.red_len, "⚡基准少堵")
        tag_min(bypasses, lambda r: r.red_len, "⚡绕行少堵")

    # ═══════════════════════ 消息构建 ═══════════════════════
    def _build_messages(self, elapsed: float) -> list:
        return [self._build_msg1(elapsed), self._build_msg2(), self._build_msg3()]

    def _build_msg1(self, elapsed: float) -> str:
        strat_str = "/".join(f"s{s}" for s in self.cfg.BASELINES)
        bypass_str = "/".join(f"s{s}" for s in self.cfg.BYPASS_STRATEGIES)
        base_detail = ", ".join(
            f"s{s}={strategy_brief(s)}" for s in self.cfg.BASELINES)
        bypass_detail = ", ".join(
            f"s{s}={strategy_brief(s)}" for s in self.cfg.BYPASS_STRATEGIES)

        # Per-phase breakdown
        phase_lines = []
        for phase_name in ["Phase 1", "Phase 2", "Phase 3", "Phase 4", "Phase 5"]:
            ps = self.phase_stats.get(phase_name, {})
            api_c = ps.get("api_calls", 0)
            el = ps.get("elapsed", 0)
            line = f"    {phase_name}: {api_c} 次 API, {el:.1f}s"
            if phase_name == "Phase 4" and ps.get("iterations"):
                for ist in ps["iterations"]:
                    line += f"\n      迭代{ist['iter']}: {ist['api_calls']} 次 API, " \
                            f"{ist['elapsed']:.1f}s, 新增 {ist['new_routes']} 条"
            phase_lines.append(line)

        # Congestion definition
        cong_str = "/".join(self.cfg.CONGESTION_STATUSES)
        toll_label = {"free": "免费期", "maybe_free": "可能免费(首/末日)", "paid": "收费"}

        header = (
            f"🎯 NavClaw v{self.cfg.VERSION} 已启动\n\n"
            f"📊 查询参数\n"
            f"  起点：{self.origin_name}\n"
            f"  终点：{self.dest_name}\n"
            f"  高速收费：{toll_label.get(self.toll_free, '未知')}（以API实际金额为准）\n"
            f"  基准策略：{len(self.cfg.BASELINES)} 种 ({strat_str})\n"
            f"    {base_detail}\n"
            f"  绕行策略：{len(self.cfg.BYPASS_STRATEGIES)} 种 ({bypass_str})\n"
            f"    {bypass_detail}\n"
            f"  拥堵定义：TMC状态为[{cong_str}]且单段≥{self.cfg.MIN_RED_LEN}m\n"
            f"    合并间距：高速{self.cfg.MERGE_GAP}m / 非高速{self.cfg.MERGE_GAP_NOHW}m\n\n"
            f"📈 查询结果\n"
            f"  API 查询：{self.api.api_call_count} 次（总计）\n"
            f"  耗时：{elapsed:.1f}s（总计）\n"
            f"  各阶段明细：\n" + "\n".join(phase_lines) + "\n\n"
            f"✅ 基准路线 {len(self.baselines)} 条 · "
            f"种子路线 {len(self.seeds)} 条 · "
            f"绕行成功 {self.bypass_success}/{self.bypass_total}\n\n"
        )
        return header + self._build_table()

    def _build_table(self) -> str:
        baselines = sorted([r for r in self.all_routes if r.route_type == "基准"],
                           key=lambda r: (r.duration, r.red_len))
        bypasses = sorted([r for r in self.all_routes if r.route_type == "绕行"],
                          key=lambda r: (r.duration, r.red_len))
        all_sorted = baselines + bypasses
        if not all_sorted:
            return "(无路线数据)\n"
        fastest_dur = min(r.duration for r in all_sorted)

        hdr = "| 高亮 | 标签 | 方案 | 类型 | 时间 | +时间 | 里程 | 高速% | 堵% | 收费 | 途经 |"
        sep = "|------|------|------|------|------|-------|------|-------|-----|------|------|"
        rows = [hdr, sep]

        def mk_row(r):
            tag_str = ", ".join(r.tags) if r.tags else "-"
            plus_min = (r.duration - fastest_dur) // 60
            bold = "🏆全局最快" in r.tags
            cols = [tag_str, r.label, r.desc[:20], r.route_type,
                    fmt_dur(r.duration), str(int(plus_min)),
                    fmt_dist(r.distance), fmt_pct(r.hw_pct),
                    fmt_pct(r.red_pct), fmt_cost(r.toll_cost, self.toll_free),
                    str(len(r.waypoints))]
            if bold:
                cols = [f"**{c}**" for c in cols]
            return "| " + " | ".join(cols) + " |"

        for r in baselines:
            rows.append(mk_row(r))
        if bypasses:
            rows.append("| ────── " * 11 + "|")
            for r in bypasses:
                rows.append(mk_row(r))
        return "\n".join(rows) + "\n"

    def _build_msg2(self) -> str:
        if not self.bypass_routes:
            return "🚗 绕行方案快速导航\n\n  (无拥堵 / 无绕行方案)\n"

        bypasses_sorted = sorted(self.bypass_routes, key=lambda r: r.duration)
        fastest_all = min(r.duration for r in self.all_routes) if self.all_routes else 0
        fastest_bypass = bypasses_sorted[0]
        all_bypass = None
        if self.total_clusters > 0:
            full = [r for r in bypasses_sorted if len(r.bypassed_indices) >= self.total_clusters]
            all_bypass = full[0] if full else None
        least_red = min(bypasses_sorted, key=lambda r: r.red_len)

        picks = [("最快绕", fastest_bypass), ("全部绕", all_bypass), ("最少堵", least_red)]
        lines = ["🚗 绕行方案快速导航\n"]
        seen_fps = {}
        for i, (name, route) in enumerate(picks, 1):
            if route is None:
                lines.append(f"{i}️⃣ [{name}] - {'全部失败' if name=='全部绕' else '无'}\n")
                continue
            if route.fingerprint in seen_fps:
                lines.append(f"{i}️⃣ [{name}] 同[{seen_fps[route.fingerprint]}]\n")
                continue
            seen_fps[route.fingerprint] = name
            plus = (route.duration - fastest_all) // 60
            lines.append(f"{i}️⃣ [{name}] {route.desc}[{route.label}]")
            lines.append(f"   ⏱ {fmt_dur(route.duration)}（+{plus}分钟）")
            for p, url in build_nav_links(
                    self.origin_coord, self.origin_name,
                    self.dest_coord, self.dest_name, route.waypoints, self.cfg):
                lines.append(f"   📱 {p}: {url}")
            lines.append("")
        lines.append("更多详细信息见附件日志文件")
        return "\n".join(lines)

    def _build_msg3(self) -> str:
        if not self.all_routes:
            return "🎯 最终推荐\n\n  (无路线数据)\n"
        best_time = min(self.all_routes, key=lambda r: r.duration)
        best_red = min(self.all_routes, key=lambda r: r.red_len)
        # 官方基准榜：all_routes 中的基准已全部是固化版
        baselines = [r for r in self.all_routes if r.route_type == "基准"]
        best_base = min(baselines, key=lambda r: r.duration) if baselines else best_time

        picks = [
            ("🏆", "综合时间榜（全场最快）", best_time),
            ("🚗", "拥堵最少榜（最省心路线）", best_red),
            ("🛡️", "官方基准榜（导航原始推荐）", best_base),
        ]
        lines = ["🎯 最终推荐\n"]
        seen_fps = {}
        for icon, title, route in picks:
            if route.fingerprint in seen_fps:
                lines.append(f"{icon} {title}")
                lines.append(f"   同{seen_fps[route.fingerprint]}\n")
                continue
            seen_fps[route.fingerprint] = title
            t = "混合" if route.route_type == "绕行" else "基准"
            lines.append(f"{icon} {title}")
            lines.append(f"   [{t}] {route.desc}[{route.label}]")
            lines.append(f"   ⏱ {fmt_dur(route.duration)} | "
                         f"{fmt_dist(route.distance)} | 拥堵{fmt_pct(route.red_pct)}")
            for p, url in build_nav_links(
                    self.origin_coord, self.origin_name,
                    self.dest_coord, self.dest_name, route.waypoints, self.cfg):
                lines.append(f"   📱 {p}: {url}")
            lines.append("")
        return "\n".join(lines)

    # ═══════════════════════ 日志 ═══════════════════════
    def _save_log(self, elapsed: float) -> str:
        now = datetime.now(CN_TZ)
        ts = now.strftime("%Y%m%d_%H%M%S")
        log_dir = f"log/navclaw/{ts}"
        os.makedirs(log_dir, exist_ok=True)
        log_path = f"{log_dir}/navclaw_{ts}.md"

        c = self.cfg
        content = [
            f"# NavClaw日志 v{c.VERSION}",
            f"## 元数据",
            f"- 起点：{self.origin_name} ({self.origin_coord})",
            f"- 终点：{self.dest_name} ({self.dest_coord})",
            f"- 时间：{now.strftime('%Y-%m-%d %H:%M:%S')}",
            f"- 版本：{c.VERSION}",
            f"- BASELINES: {c.BASELINES}",
            f"- BYPASS_STRATEGIES: {c.BYPASS_STRATEGIES}",
            f"- PHASE2_TOP_Y: {c.PHASE2_TOP_Y} / NOHW_PROTECT: {c.NOHW_PROTECT}",
            f"- MIN_RED_LEN: {c.MIN_RED_LEN}m / MERGE_GAP: {c.MERGE_GAP}m",
            f"- CONGESTION_STATUSES: {c.CONGESTION_STATUSES}",
            f"- 拥堵定义: TMC状态为[{'/'.join(c.CONGESTION_STATUSES)}]且单段≥{c.MIN_RED_LEN}m",
            f"- ANCHOR_COUNT: {c.ANCHOR_COUNT}",
            f"- 高速收费: {self.toll_free}（以API实际金额为准，内置日历仅供参考）", "",
            f"## 总体统计",
            f"- API 查询次数：{self.api.api_call_count}",
            f"- 总耗时：{elapsed:.1f}s",
            f"- 基准路线：{len(self.baselines)} 条",
            f"- 种子路线：{len(self.seeds)} 条",
            f"- 拥堵聚合段：{self.total_clusters} 个",
            f"- 绕行方案：成功 {self.bypass_success}/{self.bypass_total}", "",
            "### 各阶段明细",
        ]
        for phase_name in ["Phase 1", "Phase 2", "Phase 3", "Phase 4", "Phase 5"]:
            ps = self.phase_stats.get(phase_name, {})
            content.append(f"- {phase_name}: {ps.get('api_calls',0)} 次 API, "
                           f"{ps.get('elapsed',0):.1f}s")
            if phase_name == "Phase 4" and ps.get("iterations"):
                for ist in ps["iterations"]:
                    content.append(f"  - 迭代{ist['iter']}: {ist['api_calls']} 次 API, "
                                   f"{ist['elapsed']:.1f}s, 新增 {ist['new_routes']} 条")
        content.append("")

        # 固化前后对比表
        if self.fixation_comparison:
            content.append("### 固化前后对比")
            content.append(f"| 标签 | 原时间 | 固时间 | Δ时间 | 原里程 | 固里程 | 原堵% | 固堵% | 原收费 | 固收费 |")
            content.append(f"|------|--------|--------|-------|--------|--------|-------|-------|--------|--------|")
            for orig, fixed in self.fixation_comparison:
                delta = fixed.duration - orig.duration
                delta_str = f"+{delta//60}m" if delta >= 0 else f"{delta//60}m"
                content.append(
                    f"| {orig.label} | {fmt_dur(orig.duration)} | {fmt_dur(fixed.duration)} | "
                    f"{delta_str} | {fmt_dist(orig.distance)} | {fmt_dist(fixed.distance)} | "
                    f"{fmt_pct(orig.red_pct)} | {fmt_pct(fixed.red_pct)} | "
                    f"{fmt_cost(orig.toll_cost, self.toll_free)} | "
                    f"{fmt_cost(fixed.toll_cost, self.toll_free)} |")
            content.append("")

        content.append("## 运行日志")
        content.extend(self.log_lines)
        content.append("\n## 全部路线详情")
        for r in self.all_routes:
            tags_str = " ".join(r.tags) if r.tags else ""
            content.append(
                f"- {r.label} [{r.route_type}] {r.desc} | "
                f"{fmt_dur(r.duration)} | {fmt_dist(r.distance)} | "
                f"高速{fmt_pct(r.hw_pct)} | 拥堵{fmt_pct(r.red_pct)} | "
                f"{fmt_cost(r.toll_cost, self.toll_free)} | WP={len(r.waypoints)} {tags_str}")

        with open(log_path, "w", encoding="utf-8") as f:
            f.write("\n".join(content))
        self._log(f"\n📝 日志: {log_path}")
        return log_path


# ═══════════════════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════════════════

def main():
    import argparse
    parser = argparse.ArgumentParser(description="NavClaw - AI智能导航助手")
    parser.add_argument("--origin", "-o", default=None)
    parser.add_argument("--dest", "-d", default=None)
    parser.add_argument("--baselines", nargs="+", type=int, default=None)
    parser.add_argument("--bypass-strategies", nargs="+", type=int, default=None)
    parser.add_argument("--top-y", type=int, default=None)
    parser.add_argument("--max-iter", type=int, default=None)
    parser.add_argument("--anchor-count", type=int, default=None)
    parser.add_argument("--no-android", action="store_true")
    parser.add_argument("--no-ios", action="store_true")
    parser.add_argument("--web", action="store_true")
    args = parser.parse_args()

    cfg = PlannerConfig()
    if args.baselines: cfg.BASELINES = args.baselines
    if args.bypass_strategies: cfg.BYPASS_STRATEGIES = args.bypass_strategies
    if args.top_y: cfg.PHASE2_TOP_Y = args.top_y
    if args.max_iter is not None: cfg.MAX_ITER = args.max_iter
    if args.anchor_count: cfg.ANCHOR_COUNT = args.anchor_count
    if args.no_android: cfg.SEND_ANDROID = False
    if args.no_ios: cfg.SEND_IOS = False
    if args.web: cfg.SEND_WEB = True

    planner = RoutePlanner(cfg)
    result = planner.run(origin=args.origin, dest=args.dest)

    print("\n" + "=" * 70)
    for i, msg in enumerate(result["messages"], 1):
        print(f"\n{'─'*60}")
        print(f"📨 消息 {i}")
        print(f"{'─'*60}")
        print(msg)
    return result


if __name__ == "__main__":
    main()
