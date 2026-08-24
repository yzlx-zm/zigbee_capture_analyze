"""涂鸦 Zigbee 私有簇 0xEF00 解析 — DP 数据点协议 (U15, 2026-08-24)

依据: 涂鸦开发者平台公开 Zigbee 协议资料 (命令 0x00-0x1D 与 DP 结构);
载荷结构/方向以素材实证核对 (dimmer 素材 需求32533_simon_dimmer_涂鸦入网_ce5b.cubx)。

⚠️ 素材实证修正 (2026-08-24, dimmer):
- 0xEF00 帧 FCF 实测 0x09/0x01 (cluster-specific, 无 manufacturer-specific 位, 无 ms code)
- cmd 0x02 (S→C) 上报载荷 = [seq:2 大端][dp_id:1][dp_type:1][dp_len:2 **大端**][value]...
  seq 每帧递增 (0x005A→0x005D 素材实证)
- value 类型 0x02 实测 **4 字节大端** (素材: 00 00 02 2b = 555 亮度)
- 素材中 cmd 0x0B (C→S) ×22 帧 FCF=0x00 实为**全局命令 Default Response**
  (payload [02][00] = 响应命令 0x02 + SUCCESS), 并非涂鸦 0x0B 控制命令 —
  涂鸦 0x0B 下发控制命令结构待用户提供含控制操作的抓包验证

DP 数据结构 (涂鸦公开协议 + 素材实证; dp_len/value 均为大端):
  [dp_id:1][dp_type:1][dp_len:2 BE][dp_value:dp_len]
dp_type: 0x00 raw / 0x01 bool / 0x02 value(4B 大端) / 0x03 str / 0x04 enum(1B) / 0x05 bitmap(4B)
"""
from __future__ import annotations

# ── 涂鸦 0xEF00 命令名 (涂鸦公开协议; 方向标注素材实证结果) ──
TUYA_CMD_NAMES: dict[int, str] = {
    0x00: "查询设备 DP (Query DP)",
    0x01: "DP 上报 (Report DP, 设备→网关)",
    0x02: "查询 DP 响应/上报",   # 素材实证: dimmer ×20 S→C, 载荷 [seq][DP...]
    0x03: "定时上报 (Timed Report)",  # 素材实证: dimmer ×2 C→S 空载荷
    0x04: "预留",
    0x05: "查询 DP 上报规则",
    0x06: "查询 DP 数据",
    0x07: "查询设备状态",
    0x08: "设备状态响应",
    0x09: "预留",
    0x0A: "预留",
    0x0B: "下发 DP 控制命令 (网关→设备)",  # ⚠️ dimmer 素材未见真实 0x0B 控制帧 (22 帧为 Default Response)
    0x0C: "本地时间查询 (设备→网关)",
    0x0D: "本地时间响应 (网关→设备)",
    0x0E: "属性上报",
    0x0F: "下发命令",
    0x10: "属性查询",   # 素材实证: dimmer ×2 C→S 短载荷 (结构待验证)
    0x11: "属性响应",   # 素材实证: dimmer ×3 S→C 短载荷 (结构待验证)
    0x12: "场景查询",
    0x13: "场景响应",
    0x14: "场景保存",
    0x15: "场景保存响应",
    0x16: "时间同步",
    0x17: "心跳 (设备→网关)",
    0x18: "预留",
    0x19: "厂商命令",
    0x1A: "查询时间 (设备→网关)",
    0x1B: "时间响应 (网关→设备)",
    0x1C: "定时上报",
    0x1D: "预留",
}

DP_TYPE_NAMES: dict[int, str] = {
    0x00: "raw", 0x01: "bool", 0x02: "value", 0x03: "str",
    0x04: "enum", 0x05: "bitmap",
}

# DP 语义表: dp_id 含义按设备型号/产品品类定义 (涂鸦无全局统一表)。
# 已实证条目标注来源 (素材/型号); 未实证的留待素材 — 不臆造。
DP_SEMANTICS: dict[int, str] = {}


def get_tuya_command_name(cmd_id: int) -> str:
    return TUYA_CMD_NAMES.get(cmd_id, f"Cmd 0x{cmd_id:02X} (未定义)")


def _fmt_dp_value(dp_type: int, val: bytes) -> str:
    """DP 值格式化 (涂鸦公开协议类型定义; value 4B 大端 = 素材实证)."""
    if dp_type == 0x01:  # bool
        return "1 (true)" if val and val[0] else "0 (false)"
    if dp_type == 0x02:  # value: 4B 大端 (素材实证: 00 00 02 2b = 555)
        return str(int.from_bytes(val, "big", signed=True))
    if dp_type == 0x03:  # str
        try:
            return f"\"{val.decode('utf-8')}\""
        except UnicodeDecodeError:
            return f"hex:{val.hex()}"
    if dp_type == 0x04:  # enum: 1B
        return f"{val[0]} (0x{val[0]:02X})" if val else "(空)"
    if dp_type == 0x05:  # bitmap: 4B
        v = int.from_bytes(val[:4], "big") if val else 0
        return f"0x{v:08X} (bitmap)"
    return val.hex() if val else "(空)"  # 0x00 raw / 未知; 空值 DP 显式标注


def parse_tuya_dp(payload: bytes, max_dp: int = 32) -> tuple[list[dict], int]:
    """DP 序列解析 → (DP 记录列表, 未消费字节数).
    记录: {dp_id, dp_type, dp_type_name, value, hex}
    截断/长度不符 → 停在破损处, 剩余字节由调用方提示 (不臆造)."""
    dps: list[dict] = []
    off = 0
    while off + 4 <= len(payload) and len(dps) < max_dp:
        dp_id = payload[off]
        dp_type = payload[off + 1]
        # ⚠️ 素材实证 (dimmer): dp_len 大端 (00 01 = 1; 曾按 LE 误读为 256 致解析失败)
        dp_len = int.from_bytes(payload[off + 2:off + 4], "big")
        if off + 4 + dp_len > len(payload):
            break  # DP 长度越界 → 剩余为破损/非 DP 数据
        val = payload[off + 4:off + 4 + dp_len]
        dps.append({
            "dp_id": dp_id,
            "dp_type": dp_type,
            "dp_type_name": DP_TYPE_NAMES.get(dp_type, f"0x{dp_type:02X}"),
            "value": _fmt_dp_value(dp_type, val),
            "hex": val.hex(),
        })
        off += 4 + dp_len
    return dps, off


def parse_tuya_payload(cluster_id: int | None, cmd_id: int | None,
                       payload: bytes, direction: str | None = None) -> dict | None:
    """0xEF00 载荷解析 (注册进 zcl_defs.PAYLOAD_PARSERS 的解析器).

    ⚠️ 素材实证 (dimmer): cmd 0x02 上报载荷 = [seq:2 大端] + DP 序列;
    部分命令 (0x10/0x11 属性查询) 载荷无 DP 结构 → 尝试两种布局后仍无 DP → None 走兜底。

    返回 {"parser", "mode", "cmd_name", "fields", "hex"} — fields 为
    [{field, value, note}]; 一个 DP 都解析不出且载荷非空 → None (走字节兜底).
    """
    if cmd_id is None:
        return None
    cmd_name = get_tuya_command_name(cmd_id)
    fields: list[dict] = [{"field": "命令", "value": f"0x{cmd_id:02X} · {cmd_name}",
                           "note": "涂鸦 0xEF00 私有簇命令"}]
    if not payload:
        return {"parser": "涂鸦 0xEF00", "mode": "empty", "cmd_name": cmd_name,
                "fields": fields, "hex": ""}
    # 布局 1: [seq:2 大端] + DP 序列 (素材实证 cmd 0x02 上报)
    # 布局 2: 直接 DP 序列 (涂鸦公开协议描述)
    for skip in (2, 0):
        if skip and len(payload) <= skip:
            continue
        dps, off = parse_tuya_dp(payload[skip:])
        if dps:
            if skip:
                seq = int.from_bytes(payload[:skip], "big")
                fields.append({"field": "事务序号", "value": f"0x{seq:04X} ({seq})",
                               "note": "DP 上报序号, 每帧递增 (素材实证)"})
            for dp in dps:
                fields.append({
                    "field": f"DP {dp['dp_id']}",
                    "value": f"{dp['dp_type_name']} · {dp['value']}",
                    "note": "语义待素材 (按型号定义)" if dp["dp_id"] not in DP_SEMANTICS
                            else DP_SEMANTICS[dp["dp_id"]],
                })
            if off < len(payload) - skip:
                fields.append({"field": "⚠️ 剩余字节 (DP 解析中断)",
                               "value": payload[skip + off:].hex(),
                               "note": "长度与 DP 结构不符"})
            return {"parser": "涂鸦 0xEF00", "mode": "schema", "cmd_name": cmd_name,
                    "fields": fields, "hex": payload.hex()}
    return None  # 非 DP 结构 → 字节偏移兜底


def register(registry: dict) -> None:
    """注册 0xEF00 解析器进 zcl_defs.PAYLOAD_PARSERS (幂等)."""
    if 0xEF00 not in registry:
        registry[0xEF00] = parse_tuya_payload


if __name__ == "__main__":
    # 自检: 素材实证结构 [seq:2 BE][dp1:bool][dp2:value BE]
    payload = bytes([0x00, 0x5A,                    # seq 0x005A
                     0x01, 0x01, 0x01, 0x00, 0x01,   # dp1 bool=1
                     0x02, 0x02, 0x04, 0x00, 0x00, 0x00, 0x02, 0x2B])  # dp2 value=555 BE
    r = parse_tuya_payload(0xEF00, 0x02, payload, "Server→Client")
    for f in r["fields"]:
        print(f['field'], '=', f['value'])
