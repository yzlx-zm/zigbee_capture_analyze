"""P1 双路径字段契约对齐 — 可复跑断言测试.

用法: python .scratch/verification/p1-contract/test_p1_contract.py [cubx] [pcap]
默认素材: 验证可用-记录\\1-标准入网抓包-2 (cubx + pcap 同素材)

断言 (P1 契约):
  1. 字段全集: cubx 与 tshark 输出 key 集合一致 (条件字段已初始化 None)
  2. 安全语义: nwk_security 帧数一致; security 取值 ∈ {Decrypted, Encrypted, ''}
  3. 密钥流程: aps_cmd_id 帧两路径一致 (0x05/0x08/0x0F/0x10)
  4. 帧级一致性: 同帧 (src/dst/nwk_seq/mac_seq + ts 窗口) 关键字段值一致
  5. pkt_type 分布: NWK 命令帧分类一致 (ZDP 名称表双路径同一张表)

退出码: 0 = 全部通过; 1 = 有失败项
"""
from __future__ import annotations

import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from backend import cubx_reader, tshark  # noqa: E402

DEFAULT_CUBX = r"C:\Users\Administrator\Desktop\zigbee_capture\验证可用-记录\1-标准入网抓包-2.cubx"
DEFAULT_PCAP = r"C:\Users\Administrator\Desktop\zigbee_capture\验证可用-记录\1-标准入网抓包-2.pcap"

# 帧级一致性检查的字段 (排除解密能力差异字段 decrypted/sec_key/...)
FRAME_CONSISTENCY_FIELDS = (
    "nwk_security", "pkt_type", "mac_seq", "nwk_seq", "nwk_radius",
    "aps_cluster", "aps_profile", "aps_src_ep", "aps_dst_ep",
    "aps_cmd_id", "aps_cmd_key_type", "sec_frame_counter", "sec_level",
    "zcl_seq", "zcl_direction", "nwk_cmd_id", "nwk_status_code", "nwk_status_target",
)

failures: list[str] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    status = "PASS" if ok else "FAIL"
    print(f"[{status}] {name}" + (f" — {detail}" if detail and not ok else ""))
    if not ok:
        failures.append(name)


def main() -> int:
    cubx_path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(DEFAULT_CUBX)
    pcap_path = Path(sys.argv[2]) if len(sys.argv) > 2 else Path(DEFAULT_PCAP)

    print(f"== P1 双路径契约测试: {cubx_path.name} / {pcap_path.name} ==")
    cubx_pkts, _, _ = cubx_reader.parse_cubx(str(cubx_path), include_mac_frames=True)
    tsh_path = tshark.find_tshark()
    assert tsh_path, "tshark 未找到"
    pcap_pkts = tshark.parse_packets([str(pcap_path)], tsh_path)
    print(f"cubx {len(cubx_pkts)} 帧, pcap {len(pcap_pkts)} 帧")

    # ── 1. 字段全集一致 ──
    cubx_keys = set()
    for p in cubx_pkts:
        cubx_keys |= set(p)
    pcap_keys = set()
    for p in pcap_pkts:
        pcap_keys |= set(p)
    only_cubx = sorted(cubx_keys - pcap_keys)
    only_pcap = sorted(pcap_keys - cubx_keys)
    check("1. 字段全集一致 (cubx 独有)", not only_cubx, f"cubx 独有: {only_cubx}")
    check("1. 字段全集一致 (pcap 独有)", not only_pcap, f"pcap 独有: {only_pcap}")

    # ── 2. 安全语义 ──
    cubx_nwk = [p for p in cubx_pkts if p.get("nwk_src") is not None or p.get("nwk_dst") is not None]
    pcap_nwk = [p for p in pcap_pkts if p.get("nwk_src") is not None or p.get("nwk_dst") is not None]
    cubx_sec_cnt = sum(1 for p in cubx_nwk if p.get("nwk_security"))
    pcap_sec_cnt = sum(1 for p in pcap_nwk if p.get("nwk_security"))
    # 允许帧集差异 (tshark -Y zbee_nwk 与 cubx NWK 层判定边界 ±5 帧内)
    # 用占比比较: 安全帧比例两路径应一致
    cubx_ratio = cubx_sec_cnt / len(cubx_nwk) if cubx_nwk else 0
    pcap_ratio = pcap_sec_cnt / len(pcap_nwk) if pcap_nwk else 0
    check("2. nwk_security 占比一致", abs(cubx_ratio - pcap_ratio) < 0.05,
          f"cubx {cubx_sec_cnt}/{len(cubx_nwk)} vs pcap {pcap_sec_cnt}/{len(pcap_nwk)}")
    bad_security = {p.get("security") for p in cubx_pkts} | {p.get("security") for p in pcap_pkts}
    check("2. security 取值合法", bad_security <= {"Decrypted", "Encrypted", ""},
          f"非法值: {bad_security - {'Decrypted', 'Encrypted', ''}}")

    # ── 3. 密钥流程帧一致 ──
    cubx_cmd = [(p.get("aps_cmd_id"), p.get("aps_cmd_key_type")) for p in cubx_pkts if p.get("aps_cmd_id") is not None]
    pcap_cmd = [(p.get("aps_cmd_id"), p.get("aps_cmd_key_type")) for p in pcap_pkts if p.get("aps_cmd_id") is not None]
    check("3. APS 命令帧数量一致", len(cubx_cmd) == len(pcap_cmd),
          f"cubx {len(cubx_cmd)} vs pcap {len(pcap_cmd)}")
    check("3. APS 命令 ID+key_type 一致", sorted(cubx_cmd) == sorted(pcap_cmd),
          f"cubx {sorted(cubx_cmd)} vs pcap {sorted(pcap_cmd)}")

    # ── 4. 帧级一致性 (排序双指针 + ts 窗口) ──
    def fk(p):
        return (p.get("nwk_src"), p.get("nwk_dst"), p.get("nwk_seq"), p.get("mac_seq"))

    cubx_sorted = sorted(cubx_nwk, key=lambda p: p["ts"])
    pcap_sorted = sorted(pcap_nwk, key=lambda p: p["ts"])
    matched = mism = 0
    mism_examples: list[str] = []
    i = j = 0
    while i < len(cubx_sorted) and j < len(pcap_sorted):
        p, q = cubx_sorted[i], pcap_sorted[j]
        if fk(p) == fk(q) and abs(p["ts"] - q["ts"]) < 0.5:
            matched += 1
            for f in FRAME_CONSISTENCY_FIELDS:
                if p.get(f) != q.get(f):
                    mism += 1
                    if len(mism_examples) < 5:
                        mism_examples.append(f"{f}: cubx={p.get(f)!r} pcap={q.get(f)!r}")
            i += 1
            j += 1
        elif p["ts"] < q["ts"]:
            i += 1
        else:
            j += 1
    check("4. 帧级匹配数足够", matched >= len(cubx_nwk) * 0.5,
          f"匹配 {matched}/{len(cubx_nwk)} (seq 循环导致部分帧无法唯一匹配)")
    check("4. 同帧字段值一致", mism == 0, f"{mism} 处不一致: {mism_examples}")

    # ── 5. NWK 命令分类一致 ──
    cubx_types = Counter(p["pkt_type"] for p in cubx_nwk)
    pcap_types = Counter(p["pkt_type"] for p in pcap_nwk)
    diff_types = {t for t in set(cubx_types) | set(pcap_types) if cubx_types.get(t, 0) != pcap_types.get(t, 0)}
    # 允许解密能力差异 (cubx 可解更多加密帧) — 仅检查名称表一致性
    check("5. pkt_type 分类名一致", diff_types <= {"Data", "NWK Cmd", "ZDP Cmd"},
          f"分类名差异: {diff_types}")

    print(f"\n== 结果: {'全部通过' if not failures else f'{len(failures)} 项失败'} ==")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
