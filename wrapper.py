#!/usr/bin/env python3
"""
NavClaw Wrapper - 调用 navclaw.py 并发送结果到聊天平台
默认行为：本地输出 + 发送到已配置的聊天平台
目前支持：Mattermost（更多平台陆续接入）

用法:
    python3 wrapper.py
    python3 wrapper.py --origin "起点地址" --dest "终点地址"
    python3 wrapper.py -o "北京南站" -d "广州南站" --send-mattermost
    python3 wrapper.py -o "石家庄" -d "南京" --no-send
    
支持OpenClaw，支持高德导航 / Motivated and Support OpenClaw  | First supported platform: Amap

需要 Slack、Discord、微信等其他平台？可以：

自行扩展 wrapper.py 代码
或者让你的 OpenClaw 阅读现有代码和文档，帮你适配新平台

Licensed under the Apache License, Version 2.0

作者小红书 @深度连接
"""

import sys
import argparse
import json
import requests
from pathlib import Path

# 导入 navclaw 的 RoutePlanner 和 PlannerConfig
sys.path.insert(0, str(Path(__file__).parent))
from navclaw import RoutePlanner, PlannerConfig

# Mattermost 配置 — 从 config.py 读取，fallback 到空值
try:
    import config as _cfg
    MM_BASEURL = getattr(_cfg, "MM_BASEURL", "")
    MM_BOT_TOKEN = getattr(_cfg, "MM_BOT_TOKEN", "")
    MM_CHANNEL_ID = getattr(_cfg, "MM_CHANNEL_ID", "")
except ImportError:
    MM_BASEURL = ""
    MM_BOT_TOKEN = ""
    MM_CHANNEL_ID = ""


def _mm_configured() -> bool:
    """检查 Mattermost 是否已配置"""
    return bool(MM_BASEURL and MM_BOT_TOKEN and MM_CHANNEL_ID)


def upload_file_to_mattermost(file_path: str) -> str:
    """上传文件到 Mattermost，返回 file_id"""
    try:
        with open(file_path, 'rb') as f:
            files = {'files': f}
            data = {'channel_id': MM_CHANNEL_ID}
            resp = requests.post(
                f"{MM_BASEURL}/api/v4/files",
                headers={"Authorization": f"Bearer {MM_BOT_TOKEN}"},
                files=files,
                data=data,
                timeout=10
            )
        if resp.status_code == 201:
            result = resp.json()
            return result['file_infos'][0]['id']
        else:
            print(f"⚠️ 文件上传失败: {resp.status_code} {resp.text[:200]}")
            return None
    except Exception as e:
        print(f"❌ 文件上传异常: {e}")
        return None


def send_mattermost_message(text: str, file_ids: list = None) -> bool:
    """发送消息到 Mattermost"""
    try:
        payload = {
            "channel_id": MM_CHANNEL_ID,
            "message": text
        }
        if file_ids:
            payload["file_ids"] = file_ids
        
        resp = requests.post(
            f"{MM_BASEURL}/api/v4/posts",
            headers={
                "Authorization": f"Bearer {MM_BOT_TOKEN}",
                "Content-Type": "application/json"
            },
            json=payload,
            timeout=10
        )
        if resp.status_code == 201:
            return True
        else:
            print(f"⚠️ 消息发送失败: {resp.status_code} {resp.text[:200]}")
            return False
    except Exception as e:
        print(f"❌ 消息发送异常: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(
        description="NavClaw Wrapper",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python3 wrapper.py                              # 默认起终点，本地输出 + 发送 Mattermost
  python3 wrapper.py -o "起点" -d "终点"
  python3 wrapper.py -o "石家庄" -d "南京" --no-send
  python3 wrapper.py --send-mattermost            # 显式指定发送 Mattermost
        """
    )
    
    # 基本参数（可选，默认从 config.py 读取）
    parser.add_argument("--origin", "-o", default=None, help="起点（默认从 config.py）")
    parser.add_argument("--dest", "-d", default=None, help="终点（默认从 config.py，'家'=默认终点）")
    
    # 可选路由规划参数
    parser.add_argument("--baselines", nargs="+", type=int, default=None,
                       help="基准策略列表 (默认: 32 36 38 39 35 1)")
    parser.add_argument("--bypass-strategies", nargs="+", type=int, default=None,
                       help="绕行策略列表")
    parser.add_argument("--top-y", type=int, default=None,
                       help="精筛选 Top Y (默认: 5)")
    parser.add_argument("--max-iter", type=int, default=None,
                       help="最大迭代次数 (默认: 0)")
    parser.add_argument("--anchor-count", type=int, default=None,
                       help="锚点数量 (默认: 10)")
    
    # 链接平台
    parser.add_argument("--no-android", action="store_true",
                       help="不生成 Android 链接")
    parser.add_argument("--no-ios", action="store_true",
                       help="不生成 iOS 链接")
    parser.add_argument("--web", action="store_true",
                       help="生成 Web 链接")
    
    # 聊天平台发送选项（默认发送到已配置的平台）
    parser.add_argument("--send-mattermost", action="store_true",
                       help="显式发送到 Mattermost（默认已开启，预留参数）")
    parser.add_argument("--no-send", action="store_true",
                       help="仅本地输出，不发送到任何聊天平台")
    parser.add_argument("--no-log-file", action="store_true",
                       help="不发送日志文件附件")
    
    args = parser.parse_args()
    
    # 构建配置
    cfg = PlannerConfig()
    if args.baselines:
        cfg.BASELINES = args.baselines
    if args.bypass_strategies:
        cfg.BYPASS_STRATEGIES = args.bypass_strategies
    if args.top_y:
        cfg.PHASE2_TOP_Y = args.top_y
    if args.max_iter is not None:
        cfg.MAX_ITER = args.max_iter
    if args.anchor_count:
        cfg.ANCHOR_COUNT = args.anchor_count
    if args.no_android:
        cfg.SEND_ANDROID = False
    if args.no_ios:
        cfg.SEND_IOS = False
    if args.web:
        cfg.SEND_WEB = True
    
    # origin/dest: 命令行 > config.py 默认值
    origin = args.origin
    dest = args.dest
    
    # 执行规划
    print(f"\n🎯 开始规划...")
    print(f"  起点: {origin or cfg.DEFAULT_ORIGIN or '(使用默认)'}")
    print(f"  终点: {dest or cfg.DEFAULT_DEST or '(使用默认)'}")
    
    planner = RoutePlanner(cfg)
    result = planner.run(origin=origin, dest=dest)
    
    messages = result.get("messages", [])
    log_path = result.get("log_path", "")
    
    if not messages:
        print("❌ 未获得规划结果")
        return 1
    
    # 本地输出
    print("\n" + "="*70)
    for i, msg in enumerate(messages, 1):
        print(f"\n{'─'*60}")
        print(f"📨 消息 {i}")
        print(f"{'─'*60}")
        print(msg)
    
    # 发送到聊天平台（默认发送，--no-send 跳过）
    if not args.no_send:
        print("\n" + "="*70)
        if not _mm_configured():
            print("⚠️ Mattermost 未配置（请在 config.py 设置 MM_BASEURL / MM_BOT_TOKEN / MM_CHANNEL_ID），消息未发送")
        else:
            print("📤 正在发送到 Mattermost...")
            for i, msg in enumerate(messages, 1):
                success = send_mattermost_message(msg)
                if success:
                    print(f"  ✅ 消息 {i} 发送成功")
                else:
                    print(f"  ❌ 消息 {i} 发送失败")
            
            # 发送日志文件
            if log_path and not args.no_log_file:
                if Path(log_path).exists():
                    print(f"\n  📎 上传日志文件: {log_path}")
                    file_id = upload_file_to_mattermost(log_path)
                    if file_id:
                        success = send_mattermost_message(
                            "📋 详细日志已生成（见附件）",
                            file_ids=[file_id]
                        )
                        if success:
                            print(f"  ✅ 日志文件发送成功")
                        else:
                            print(f"  ❌ 日志文件消息发送失败")
                    else:
                        print(f"  ❌ 日志文件上传失败")
                else:
                    print(f"  ⚠️ 日志文件不存在: {log_path}")
            
            print("\n✅ Mattermost 发送完成")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
