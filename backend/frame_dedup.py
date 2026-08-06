"""帧去重公共能力 — P1 产出 (2026-08-05).

背景: cubx 抓包器 (Ubiqua 多接收器/冗余采集) 会把同一空中帧重复捕获多次。
素材实证: 2-群控压测问题包.cubx 54,403 帧中 37% 为重复捕获 (同一帧 2-3 次,
mac_seq/nwk_seq 完全相同, 时间戳几乎相同)。不先去重, 投递率/失败率等
计数类分析必然失真 (如群控投递率首轮计数因重复帧翻倍)。

设计要点:
- 帧身份仅依赖 MAC 层 (mac_src/mac_dst/mac_seq) — cubx/tshark 双路径都有这些字段
- MAC seq 8 位回绕: 1s 窗口内同设备最多 ~100 帧 (250kbps), 同 seq 复用不可能
- APS 应用层重传 (mac_seq 重新封装) 不去重 — 重传是独立事件, 应计入
- MAC 层重传 (同 mac_seq 多次出现) 会被去重 — 对"投递/到达"类计数合理 (同一帧)
- 去重仅用于统计类分析; 原始列表保留给 UI (时间线/帧详情需逐条展示)
"""
from __future__ import annotations


def dedup_packets(packets: list[dict], window_s: float = 1.0) -> list[dict]:
    """按帧身份去重, 保留首次出现。

    键 = (mac_src, mac_dst, mac_seq) — 同跳去重 (素材实证, 群控包 Unlock 634→461):
      - 物理重复捕获 (抓包器同帧多录): 全同 → 去重 ✓
      - MAC 层重传 (同帧重发, mac_seq 不变): 去重 ✓ (对"到达/投递"计数合理)
      - ⚠️ 不能用 NWK 事务键 (nwk_src/dst/seq): 同一事务的"发送帧"与"投递帧"
         (中继转发段, mac_src/mac_dst 不同) 会被误去重 → 投递率分析失真
        (2026-08-06 回归实测: NWK 键使 54995 投递率 15/24 误报 0/24).
      - 上层 (APS) 重传重新封装 → nwk_seq 递增 → 不去重 (独立事务, 分析层自判)
      - 无地址帧 (Beacon 广播): 不参与去重, 原样保留

    事务级合并 (如"发送尝试数"= 唯一 (nwk_dst, nwk_seq)) 是分析层语义,
    由检测器自行按需处理 — 本模块只保证同跳物理去重.
    """
    seen: dict[tuple, float] = {}
    out: list[dict] = []
    for p in packets:
        key = (p.get("mac_src"), p.get("mac_dst"), p.get("mac_seq"))
        if any(v is None for v in key):
            out.append(p)
            continue
        t = p["ts"]
        prev = seen.get(key)
        if prev is not None and abs(t - prev) < window_s:
            continue  # 重复捕获 / 同帧 MAC 重传
        seen[key] = t
        out.append(p)
    return out


def dedup_stats(packets: list[dict], window_s: float = 1.0) -> dict:
    """去重统计报告: 原始数 / 去重后数 / 重复率 (诊断页与回归测试用)."""
    deduped = dedup_packets(packets, window_s)
    total = len(packets)
    dup = total - len(deduped)
    return {
        "original": total,
        "deduped": len(deduped),
        "duplicates": dup,
        "dup_ratio": round(dup / total, 3) if total else 0.0,
        "window_s": window_s,
    }
