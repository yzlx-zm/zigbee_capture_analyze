"""AI 对话式分析: 范围解析 + 取数摘要 (U17 阶段二).

- parse_scope: 自然语言 → 结构化范围 {ts_start, ts_end, addr, pan}
  (时间窗 HH:MM:SS~ / 相对时间"前 N 分钟" / 短地址 0x838D / PAN 0x1234;
   解析失败 → 引导重述, 不臆测 — 铁律)
- build_scope_summary: 按范围取数 → 精简摘要 (统计 + 关键事件 + 检测 verdict 精简)
  (复用 scripts/export_ai_dataset.packet_summary 事件文本 + 各检测器 detect)
"""
from __future__ import annotations

import re

from .api.files import _parse_clock_time

# ── 范围信号 (正则) ──
_TIME_WINDOW_RE = re.compile(
    r"(?P<t1>\d{1,2}:\d{2}(?::\d{2})?)\s*[-~至到]\s*(?P<t2>\d{1,2}:\d{2}(?::\d{2})?)")
_REL_TIME_RE = re.compile(r"(?:最近|前|过去)\s*(?P<n>\d+)\s*(?P<u>秒|分钟|分|小时)")
# 短地址: 0x 前缀 3-4 位, 或**无前缀 4 位含字母** ("838d"; 排除纯数字如 "1234" 防误判计数)
_ADDR_RE = re.compile(r"0x(?P<a>[0-9A-Fa-f]{3,4})\b|(?<![0-9A-Fa-f])(?=[0-9A-Fa-f]*[A-Fa-f])(?P<a2>[0-9A-Fa-f]{4})(?![0-9A-Fa-f])")
_PAN_RE = re.compile(r"(?:PAN|pan)\s*0x(?P<p>[0-9A-Fa-f]{4})\b")
_AFTER_RE = re.compile(r"(?P<t>\d{1,2}:\d{2}(?::\d{2})?)\s*(?:之后|以后|开始|以来)")
_UNTIL_RE = re.compile(r"(?P<t>\d{1,2}:\d{2}(?::\d{2})?)\s*(?:之前|以前|为止|结束)")

_UNIT_SEC = {"秒": 1, "分钟": 60, "分": 60, "小时": 3600}


def parse_scope(message: str, packets: list[dict], prev: dict | None = None) -> dict:
    """自然语言 → 结构化范围. 返回:
    {ok: True, scope: {ts_start, ts_end, addr, addr_text, pan, pan_text, text, inherit}}
    或 {ok: False, error: 引导提示}

    追问继承: 无任何显式范围信号 + prev 非空 → 继承 prev (inherit=True);
    显式新范围覆盖. 解析失败不臆测, 引导重述.
    """
    m = message.strip()
    if not packets:
        return {"ok": False, "error": "当前没有导入的抓包数据 — 请先导入 .cubx 素材再分析"}
    scope: dict = {}
    signals: list[str] = []

    # PAN (0x1234 4 位, PAN 前缀强信号)
    pm = _PAN_RE.search(m)
    if pm:
        scope["pan"] = int(pm.group("p"), 16)
        scope["pan_text"] = f"0x{scope['pan']:04X}"
        signals.append(f"PAN {scope['pan_text']}")

    # 短地址 (0x838D 或裸 4 位 hex 含字母 "838d"; 排除广播 ≥0xFFF0)
    am = _ADDR_RE.search(m)
    if am:
        a = int(am.group("a") or am.group("a2"), 16)
        if a < 0xFFF0:
            scope["addr"] = a
            scope["addr_text"] = f"0x{a:04X}"
            signals.append(f"节点 {scope['addr_text']}")

    # 时间窗 (10:00-10:30 / 10:00~10:30 / 10:00 至 10:30)
    base_ts = packets[0]["ts"]
    last_ts = packets[-1]["ts"]
    tw = _TIME_WINDOW_RE.search(m)
    if tw:
        t1 = _parse_clock_time(tw.group("t1"), base_ts)
        t2 = _parse_clock_time(tw.group("t2"), base_ts)
        if t1 is not None and t2 is not None:
            if t2 <= t1:
                t2 += 86400  # 跨午夜
            scope["ts_start"], scope["ts_end"] = t1, t2
            signals.append(f"时间窗 {tw.group('t1')}~{tw.group('t2')}")

    # 相对时间 (最近 5 分钟 / 前 30 秒) → 相对抓包末尾
    rt = _REL_TIME_RE.search(m)
    if rt and "ts_start" not in scope:
        n, u = int(rt.group("n")), rt.group("u")
        span = n * _UNIT_SEC.get(u, 60)
        scope["ts_start"], scope["ts_end"] = last_ts - span, last_ts
        signals.append(f"最近 {n}{u}")

    # 单时间点 (10:00 之后 / 之前)
    if "ts_start" not in scope and "ts_end" not in scope:
        af = _AFTER_RE.search(m)
        if af:
            t = _parse_clock_time(af.group("t"), base_ts)
            if t is not None:
                scope["ts_start"], scope["ts_end"] = t, last_ts
                signals.append(f"{af.group('t')} 之后")
        else:
            un = _UNTIL_RE.search(m)
            if un:
                t = _parse_clock_time(un.group("t"), base_ts)
                if t is not None:
                    scope["ts_start"], scope["ts_end"] = base_ts, t + 0.999
                    signals.append(f"{un.group('t')} 之前")

    # 追问继承 (无显式范围信号 + 上轮范围)
    if not signals:
        if prev and any(prev.get(k) is not None for k in
                        ("ts_start", "ts_end", "addr", "pan")):
            scope = {k: v for k, v in prev.items()
                     if k in ("ts_start", "ts_end", "addr", "addr_text", "pan", "pan_text")}
            scope["inherit"] = True
            scope["text"] = _scope_text(scope)
            return {"ok": True, "scope": scope}
        return {"ok": False, "error": "没听懂分析范围 😅 请补充，例如："
                                     "「分析 10:00-10:30 的 0x838D」或「看看最近 5 分钟的 PAN 0x1234」"}

    # 边界钳制: 时间窗与抓包范围对齐
    if "ts_start" in scope:
        scope["ts_start"] = max(scope["ts_start"], base_ts)
    if "ts_end" in scope:
        scope["ts_end"] = min(scope["ts_end"], last_ts)

    scope["inherit"] = False
    scope["text"] = _scope_text(scope)
    return {"ok": True, "scope": scope}


def _scope_text(scope: dict) -> str:
    parts = []
    if "ts_start" in scope and "ts_end" in scope:
        def _hms(ts: float) -> str:
            import datetime
            d = datetime.datetime.fromtimestamp(ts)
            return f"{d.hour:02d}:{d.minute:02d}:{d.second:02d}"
        parts.append(f"时间 {_hms(scope['ts_start'])}~{_hms(scope['ts_end'])}")
    if scope.get("addr_text"):
        parts.append(f"节点 {scope['addr_text']}")
    if scope.get("pan_text"):
        parts.append(f"PAN {scope['pan_text']}")
    return " · ".join(parts) or "全部范围"


def filter_packets(packets: list[dict], scope: dict) -> list[dict]:
    """按范围过滤 (时间/节点/PAN 与 /api/packets 同口径)."""
    out = []
    ts0, ts1 = scope.get("ts_start"), scope.get("ts_end")
    addr, pan = scope.get("addr"), scope.get("pan")
    for p in packets:
        if ts0 is not None and p["ts"] < ts0:
            continue
        if ts1 is not None and p["ts"] > ts1:
            continue
        if addr is not None and not (p["nwk_src"] == addr or p["nwk_dst"] == addr
                                     or p["mac_src"] == addr or p["mac_dst"] == addr):
            continue
        if pan is not None and not (p["pan_src"] == pan or p["pan_dst"] == pan):
            continue
        out.append(p)
    return out


# 事件帧类型 (pkt_type 兜底: 加密 NWK 命令帧 nwk_cmd_id 为 None, 须按类型识别)
_EVENT_TYPES = {"NWK Cmd", "Link Status", "Route Request", "Route Reply", "Route Record",
                "Network Status", "Leave", "Rejoin Request", "Rejoin Response",
                "APS Cmd", "ZDP Cmd"}
# 关键事件类型 (截断时保底保留 — 08-26 修复: 838D Leave #6929 曾被前 40 帧截断遗漏)
_KEY_EVENT_MARK = ("Leave", "Network Status", "Rejoin", "TransportKey", "Remove Device",
                   "Update Device", "Device Announce", "Assoc", "Default Response")


def _event_lines(pkts: list[dict], limit: int = 80) -> list[str]:
    """关键事件文本: **全量扫描** (曾只扫前 40 帧 → 尾部关键帧如 Leave 被遗漏,
    用户实证: 0x838D 入网后 Leave #6929 未入摘要 → LLM 误判"入网完全成功").

    超上限时关键事件类型 (Leave/NS/密钥管理/Announce) 保底保留, 其余按时间填满.
    """
    try:
        from scripts.export_ai_dataset import packet_summary
    except Exception:
        packet_summary = None

    rows: list[tuple[int, str, bool]] = []   # (packet_id, line, is_key)
    for i, p in enumerate(pkts):
        pkt_id = p.get("packet_id") if p.get("packet_id") is not None else i
        has_ev = (p.get("nwk_cmd_id") is not None or p.get("aps_cmd_id") is not None
                  or p.get("aps_cluster") == 0x0013
                  or p.get("mac_cmd_id") in (1, 2)
                  or p.get("nwk_status_code") is not None
                  or p.get("pkt_type") in _EVENT_TYPES)
        if not has_ev:
            continue
        if packet_summary:
            text = packet_summary(p)
        else:
            text = (p.get("pkt_type") or "Unknown")
        src = p.get("nwk_src") or p.get("mac_src")
        dst = p.get("nwk_dst") or p.get("mac_dst")
        line = (f"- 帧#{pkt_id} {p.get('pkt_type') or 'Unknown'} "
                f"{f'0x{src:04X}' if src is not None else '-'} → "
                f"{f'0x{dst:04X}' if dst is not None else '-'}: {text}")
        is_key = any(k in text for k in _KEY_EVENT_MARK)
        rows.append((pkt_id, line, is_key))

    if len(rows) <= limit:
        return [r[1] for r in rows]
    # 超限: 关键事件保底 + 其余按时间填满
    keys = [r for r in rows if r[2]]
    rest = [r for r in rows if not r[2]]
    out = keys[:limit]
    if len(out) < limit:
        out.extend(rest[:limit - len(out)])
    out.sort(key=lambda r: r[0])   # 保持时间序
    return [r[1] for r in out]


def _detector_verdicts(pkts: list[dict]) -> list[str]:
    """范围内检测精简 (verdict 级, 异常降级跳过 — 摘要不因检测器失败而崩)."""
    if not pkts:
        return []
    out: list[str] = []
    try:
        from ..detectors import l1, l2, l3, l6
        for mod, label in ((l1, "L1 入网"), (l2, "L2 在线维持"), (l3, "L3 路由/传输"), (l6, "L6 SED")):
            try:
                r = mod.detect(pkts)
            except Exception:
                continue
            for det_name, det in (r.get("detections") or {}).items() if isinstance(r, dict) else ():
                v = det.get("verdict") if isinstance(det, dict) else None
                if v:
                    out.append(f"- {label} {det_name}: {v}")
    except Exception:
        pass
    return out


def build_scope_summary(packets: list[dict], scope: dict) -> str:
    """范围摘要 (markdown): 概览统计 + 关键事件 + 检测 verdict 精简. 供 LLM 上下文 + 前端预览."""
    pkts = filter_packets(packets, scope)
    if not pkts:
        return f"范围内无帧 (范围: {scope.get('text', '全部')})"
    from collections import Counter
    types = Counter(p.get("pkt_type") or "Unknown" for p in pkts)
    addrs = {a for p in pkts for a in (p.get("nwk_src"), p.get("nwk_dst"))
             if isinstance(a, int) and a < 0xFFF0}
    dec = sum(1 for p in pkts if p.get("decrypted"))
    enc = sum(1 for p in pkts if p.get("security") == "Encrypted")
    span = pkts[-1]["ts"] - pkts[0]["ts"]
    lines = [
        f"### 范围摘要 (范围: {scope.get('text', '全部')})",
        f"- 帧数: {len(pkts)} | 时长: {span:.1f}s | 节点数: {len(addrs)} "
        f"| 解密: {dec}/{len(pkts)} ({dec * 100 // max(len(pkts), 1)}%) 加密未解密: {enc}",
        "- 类型分布: " + ", ".join(f"{k}:{v}" for k, v in types.most_common(8)),
    ]
    evs = _event_lines(pkts)
    if evs:
        lines.append("### 关键事件")
        lines.extend(evs)   # 全量事件 (曾 [:30] 截断 — 尾部 Leave #6929 被漏, 08-26 用户实证)
    else:
        lines.append("### 关键事件: (范围内无命令/状态事件)")
    vd = _detector_verdicts(pkts)
    if vd:
        lines.append("### 检测")
        lines.extend(vd[:8])
    return "\n".join(lines)
