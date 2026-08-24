"""ZCL (Zigbee Cluster Library) 定义 — Cluster / Command / Attribute 名称映射"""
from __future__ import annotations

# ── Cluster 名称 ──
CLUSTER_NAMES: dict[int, str] = {
    0x0000: "Basic",
    0x0001: "Power Configuration",
    0x0002: "Device Temperature Configuration",
    0x0003: "Identify",
    0x0004: "Groups",
    0x0005: "Scenes",
    0x0006: "On/Off",
    0x0007: "On/Off Switch Configuration",
    0x0008: "Level Control",
    0x0009: "Alarms",
    0x000A: "Time",
    0x000F: "Binary Input (Basic)",
    0x0010: "Commissioning",
    0x0019: "OTA Upgrade",
    0x0020: "Poll Control",
    0x0021: "Green Power",
    0x0101: "Door Lock",
    0x0102: "Window Covering",
    0x0200: "Pump Config & Control",
    0x0201: "Thermostat",
    0x0202: "Fan Control",
    0x0203: "Dehumidification Control",
    0x0204: "Thermostat UI Config",
    0x0300: "Color Control",
    0x0400: "Illuminance Measurement",
    0x0401: "Illuminance Level Sensing",
    0x0402: "Temperature Measurement",
    0x0403: "Pressure Measurement",
    0x0404: "Flow Measurement",
    0x0405: "Humidity Measurement",
    0x0406: "Occupancy Sensing",
    0x0500: "IAS Zone",
    0x0501: "IAS ACE",
    0x0502: "IAS WD",
    0x0702: "Smart Energy Metering",
    0x0B05: "Diagnostics",
    0xFC00: "Manufacturer Specific",
}

# ── 全局 ZCL Command ──
GLOBAL_COMMANDS: dict[int, str] = {
    0x00: "Read Attributes",
    0x01: "Read Attributes Response",
    0x02: "Write Attributes",
    0x03: "Write Attributes Undivided",
    0x04: "Write Attributes Response",
    0x05: "Write Attributes No Response",
    0x06: "Configure Reporting",
    0x07: "Configure Reporting Response",
    0x08: "Read Reporting Configuration",
    0x09: "Read Reporting Configuration Response",
    0x0A: "Report Attributes",
    0x0B: "Default Response",
    0x0C: "Discover Attributes",
    0x0D: "Discover Attributes Response",
    0x0E: "Read Attributes Structured",
    0x0F: "Write Attributes Structured",
    0x10: "Write Attributes Structured Response",
    0x11: "Discover Commands Received",
    0x12: "Discover Commands Received Response",
    0x13: "Discover Commands Generated",
    0x14: "Discover Commands Generated Response",
    0x15: "Discover Attributes Extended",
    0x16: "Discover Attributes Extended Response",
}

# ── 特定 Cluster 的 Command ──
CLUSTER_COMMANDS: dict[int, dict[int, str]] = {
    # OTA Upgrade (0x0019)
    0x0019: {
        0x00: "Image Notify",
        0x01: "Query Next Image Request",
        0x02: "Query Next Image Response",
        0x03: "Image Block Request",
        0x04: "Image Page Request",
        0x05: "Image Block Response",
        0x06: "Upgrade End Request",
        0x07: "Upgrade End Response",
    },
    # Basic (0x0000)
    0x0000: {
        0x00: "Reset to Factory Defaults",
    },
    # Identify (0x0003)
    0x0003: {
        0x00: "Identify",
        0x01: "Identify Query",
        0x02: "Trigger Effect",
    },
    # Groups (0x0004)
    0x0004: {
        0x00: "Add Group",
        0x01: "View Group",
        0x02: "Get Group Membership",
        0x03: "Remove Group",
        0x04: "Remove All Groups",
        0x05: "Add Group If Identifying",
    },
    # Scenes (0x0005)
    0x0005: {
        0x00: "Add Scene",
        0x01: "View Scene",
        0x02: "Remove Scene",
        0x03: "Remove All Scenes",
        0x04: "Store Scene",
        0x05: "Recall Scene",
        0x06: "Get Scene Membership",
    },
    # On/Off (0x0006)
    0x0006: {
        0x00: "Off",
        0x01: "On",
        0x02: "Toggle",
        0x40: "Off with Effect",
        0x41: "On with Recall Global Scene",
        0x42: "On with Timed Off",
    },
    # Level Control (0x0008)
    0x0008: {
        0x00: "Move to Level",
        0x01: "Move",
        0x02: "Step",
        0x03: "Stop",
        0x04: "Move to Level (with On/Off)",
        0x05: "Move (with On/Off)",
        0x06: "Step (with On/Off)",
        0x07: "Stop (with On/Off)",
    },
    # Alarms (0x0009)
    0x0009: {
        0x00: "Reset Alarm",
        0x01: "Alarm",
        0x02: "Get Alarm",
        0x03: "Reset All Alarms",
        0x04: "Get Alarm Response",
    },
    # Door Lock (0x0101)
    0x0101: {
        0x00: "Lock Door",
        0x01: "Unlock Door",
        0x02: "Toggle",
    },
    # Window Covering (0x0102)
    0x0102: {
        0x00: "Up / Open",
        0x01: "Down / Close",
        0x02: "Stop",
        0x03: "Go to Lift Value",
        0x04: "Go to Tilt Value",
    },
    # Color Control (0x0300)
    0x0300: {
        0x00: "Move to Hue",
        0x01: "Move Hue",
        0x02: "Step Hue",
        0x03: "Move to Saturation",
        0x04: "Move Saturation",
        0x05: "Step Saturation",
        0x06: "Move to Hue & Saturation",
        0x07: "Move to Color",
        0x08: "Move Color",
        0x09: "Step Color",
        0x0A: "Move to Color Temperature",
        0x0B: "Enhanced Move to Hue",
        0x0C: "Enhanced Move Hue",
        0x0D: "Enhanced Step Hue",
        0x40: "Enhanced Move to Hue & Saturation",
        0x41: "Color Loop Set",
        0x42: "Stop Move Step",
        0x43: "Move Color Temperature",
        0x44: "Step Color Temperature",
    },
    # IAS Zone (0x0500)
    0x0500: {
        0x00: "Zone Status Change Notification",
        0x01: "Zone Enroll Request",
        0x02: "Zone Enroll Response",
    },
}


def get_cluster_name(cluster_id: int | None) -> str | None:
    """Cluster ID → 名称, 如 0x0019 → 'OTA Upgrade'"""
    if cluster_id is None:
        return None
    return CLUSTER_NAMES.get(cluster_id)


def get_command_name(cluster_id: int | None, cmd_id: int,
                     frame_type: int | None = None) -> str | None:
    """Command ID → 名称。frame_type 为 ZCL FCF bits0-1 (ZCL spec 2.3.1):
    0=Profile-wide (全局命令), 1=cluster-specific。
    同名冲突 (如 Basic 0x0000 的 cmd 0x00: 全局 Read Attributes vs cluster Reset to
    Factory Defaults) 必须靠 frame_type 区分, 否则全局命令被误标为 cluster 命令。

    frame_type=None/未知 (含厂商特定 0b10/0b11) → 保持历史回退逻辑 (先 cluster 后
    global), 兼容未提供 frame_type 的旧调用。"""
    if frame_type == 0:
        return GLOBAL_COMMANDS.get(cmd_id)
    if frame_type == 1:
        if cluster_id is not None and cluster_id in CLUSTER_COMMANDS:
            return CLUSTER_COMMANDS[cluster_id].get(cmd_id)
        return None
    if frame_type in (2, 3):
        # manufacturer specific (0b10/0b11): 厂商命令 ID 不得用全局表猜 (U15 严谨修正 —
        # 0xEF00 等私有簇 cmd 0x0B 曾被误标 Default Response), 仅查标准簇表
        if cluster_id is not None and cluster_id in CLUSTER_COMMANDS:
            return CLUSTER_COMMANDS[cluster_id].get(cmd_id)
        return None
    # None/未知: 现有回退逻辑
    if cluster_id is not None and cluster_id in CLUSTER_COMMANDS:
        if cmd_id in CLUSTER_COMMANDS[cluster_id]:
            return CLUSTER_COMMANDS[cluster_id][cmd_id]
    return GLOBAL_COMMANDS.get(cmd_id)


def get_cluster_commands(cluster_id: int) -> dict[int, str] | None:
    """获取特定 Cluster 的所有 Command 定义"""
    return CLUSTER_COMMANDS.get(cluster_id)


# ══════════════════════════════════════════════════════════════════════════
# U15: ZCL 命令载荷字段级解析 (ticket U15, 2026-08-24)
# 依据: Zigbee Cluster Library Spec 07-5123 (字段结构/枚举), 素材实证核对。
# 解析失败 (载荷长度不足等) 由 parse_zcl_payload 回退字节偏移兜底, 不臆造。
# ══════════════════════════════════════════════════════════════════════════

# 字段类型:
#   u8/u16/u24/u32/u40/u48/u64 — 无符号整数 (LE)
#   zstr — Zigbee char string ([len:u8][UTF-8 字符])
#   bytes:N — 固定 N 字节 (hex 显示)
#   raw — 剩余全部字节 (hex 显示)
#   repeat — 重复结构 (见下方 field["repeat"]), 循环解析至字节耗尽
#   attr_records — 属性记录重复: [attr_id:u16][data_type:u8][值] (Report/Write)
#   attr_records_rsp — 属性记录重复(带状态): [attr_id:u16][status:u8][data_type:u8][值] (Read Attr Rsp)
# 字段定义: {"name", "type", "enum"?, "note"?, "repeat"?}
_Field = dict

# ZCL data type 名称与宽度; None = 变长 (长度前缀)。
# ⚠️ 素材实证修正 (2026-08-24, dimmer Read Attr Rsp): 0x42 = 短字符串 (1B 长度前缀,
# 0x10=16 → "_TZE204_dayazmbk"), 0x41 同类 (U9 已验证); 0x43/0x44 = 长字符串 (2B LE)。
# 浮点 0x40-0x43 无素材实证 → 不列 (避免臆造; 未知类型按 hex 兜底)。
DATA_TYPE_NAMES: dict[int, str] = {
    0x00: "No data", 0x08: "8-bit data", 0x09: "16-bit data",
    0x0A: "24-bit data", 0x0B: "32-bit data", 0x0C: "40-bit data",
    0x0D: "48-bit data", 0x0E: "56-bit data", 0x0F: "64-bit data",
    0x10: "Boolean",
    0x18: "bitmap8", 0x19: "bitmap16", 0x1A: "bitmap24", 0x1B: "bitmap32",
    0x1C: "bitmap40", 0x1D: "bitmap48", 0x1E: "bitmap56", 0x1F: "bitmap64",
    0x20: "uint8", 0x21: "uint16", 0x22: "uint24", 0x23: "uint32",
    0x24: "uint40", 0x25: "uint48", 0x26: "uint56", 0x27: "uint64",
    0x28: "int8", 0x29: "int16", 0x2A: "int24", 0x2B: "int32",
    0x2C: "int40", 0x2D: "int48", 0x2E: "int56", 0x2F: "int64",
    0x30: "enum8", 0x31: "enum16",
    0x40: "octet string(8-bit len)", 0x41: "character string(8-bit len)",
    0x42: "character string(8-bit len)",   # 素材实证: 0x10=16 → "_TZE204_dayazmbk"
    0x43: "long character string(16-bit len)", 0x44: "long character string(16-bit len)",
    0x50: "array", 0x51: "struct",
    0xE0: "set", 0xE1: "bag", 0xE2: "time of day", 0xE3: "date", 0xE4: "UTC time",
    0xE5: "cluster ID", 0xE6: "attribute ID", 0xE7: "BACNet OID",
    0xE8: "IEEE address", 0xE9: "128-bit key", 0xEA: "unknown",
}
_DATA_TYPE_SIZES: dict[int, int | None] = {
    **{t: n for n, t in enumerate(range(0x08, 0x10), start=1)},   # 0x08-0x0F → 1-8B
    **{t: n for n, t in enumerate(range(0x18, 0x20), start=1)},   # bitmap8-64
    **{t: n for n, t in enumerate(range(0x20, 0x28), start=1)},   # uint8-64
    **{t: n for n, t in enumerate(range(0x28, 0x30), start=1)},   # int8-64
    0x10: 1, 0x30: 1, 0x31: 2,
    0x40: None, 0x41: None, 0x42: None, 0x43: None, 0x44: None,  # 字符串 (长度前缀)
    0xE2: 4, 0xE3: 4, 0xE4: 4, 0xE5: 2, 0xE6: 2, 0xE7: 4, 0xE8: 8, 0xE9: 16,
}
# 常用属性名 (ZCL spec 各簇属性表; 未列出者显示原始 0xXXXX — 名称不影响解析)
# ZCL 状态码名 (spec 2.4.3.1.1; L3-2 场景文档已实证 0x86/0xC3)
_ZCL_STATUS_NAMES: dict[int, str] = {
    0x00: "SUCCESS", 0x01: "FAILURE", 0x7E: "NOT_AUTHORIZED",
    0x80: "MALFORMED_COMMAND", 0x81: "UNSUP_CLUSTER_COMMAND", 0x82: "UNSUP_GENERAL_COMMAND",
    0x83: "UNSUP_MANUF_CLUSTER_COMMAND", 0x84: "UNSUP_MANUF_GENERAL_COMMAND",
    0x85: "INVALID_FIELD", 0x86: "UNSUPPORTED_ATTRIBUTE", 0x87: "INVALID_VALUE",
    0x88: "READ_ONLY", 0x89: "INSUFFICIENT_SPACE", 0x8A: "DUPLICATE_EXISTS",
    0x8B: "NOT_FOUND", 0x8C: "UNREPORTABLE_ATTRIBUTE", 0x8D: "INVALID_DATA_TYPE",
    0x8E: "INVALID_SELECTOR", 0x8F: "WRITE_ONLY", 0x90: "INCONSISTENT_STARTUP_STATE",
    0x91: "DEFINED_OUT_OF_BAND", 0x92: "INCONSISTENT", 0x93: "ACTION_DENIED",
    0x94: "TIMEOUT", 0x9C: "ABORT", 0x9D: "INVALID_IMAGE", 0x9E: "WAIT_FOR_DATA",
    0x9F: "NO_IMAGE_AVAILABLE", 0xA0: "REQUIRE_MORE_IMAGE", 0xA1: "NOTIFICATION_PENDING",
    0xC0: "HARDWARE_FAILURE", 0xC1: "SOFTWARE_FAILURE", 0xC2: "CALIBRATION_ERROR",
    0xC3: "UNSUPPORTED_CLUSTER",
}

_ATTR_NAMES: dict[int, dict[int, str]] = {
    0x0000: {0x0000: "ZCLVersion", 0x0001: "ApplicationVersion", 0x0002: "StackVersion",
             0x0004: "ManufacturerName", 0x0005: "ModelIdentifier", 0x0006: "DateCode",
             0x0007: "PowerSource", 0x0010: "LocationDescription"},
    0x0006: {0x0000: "OnOff"},
    0x0008: {0x0000: "CurrentLevel", 0x0011: "OnOffTransitionTime", 0x0012: "OnLevel",
             0x0013: "OnTransitionTime", 0x0014: "OffTransitionTime"},
    0x0300: {0x0000: "CurrentHue", 0x0001: "CurrentSaturation", 0x0002: "RemainingTime",
             0x0003: "CurrentX", 0x0004: "CurrentY", 0x0007: "ColorTemperatureMireds",
             0x0008: "ColorMode", 0x000F: "ColorCapabilities"},
    0x0102: {0x0000: "WindowCoveringType", 0x0001: "PhysicalClosedLimitLift",
             0x0003: "CurrentPositionLift", 0x0008: "CurrentPositionTilt",
             0x0010: "ConfigStatus", 0x001A: "CurrentPositionLiftPercentage",
             0x001B: "CurrentPositionTiltPercentage"},
}

# ── 标准控制簇命令载荷 schema (cluster → cmd → 方向 → [字段]) ──
# 方向: "C→S" = Client→Server (命令), "S→C" = Server→Client (响应);
# "*" = 两方向同结构。ZCL spec 07-5123 各簇命令定义。
CMD_PAYLOAD_SCHEMAS: dict[int, dict[int, dict[str, list[_Field]]]] = {
    # On/Off (0x0006) — spec §3.8
    0x0006: {
        0x00: {"C→S": []}, 0x01: {"C→S": []}, 0x02: {"C→S": []}, 0x41: {"C→S": []},
        0x40: {"C→S": [
            {"name": "EffectIdentifier", "type": "u8", "enum": {0: "Blink", 1: "Breathe", 2: "Okay"}},
            {"name": "EffectVariant", "type": "u8"}]},
        0x42: {"C→S": [
            {"name": "OnOffControl", "type": "u8"},
            {"name": "OnTime", "type": "u16"},
            {"name": "OffWaitTime", "type": "u16"}]},
    },
    # Level Control (0x0008) — spec §3.10
    0x0008: {
        0x00: {"C→S": [
            {"name": "Level", "type": "u8", "note": "目标亮度 (0-254)"},
            {"name": "TransitionTime", "type": "u16", "note": "过渡时间 0.1s 单位, 0xFFFF=立即"}]},
        0x01: {"C→S": [
            {"name": "MoveMode", "type": "u8", "enum": {0: "Up", 1: "Down"}},
            {"name": "Rate", "type": "u8", "note": "速率 (移动时长 0.1s 单位)"}]},
        0x02: {"C→S": [
            {"name": "StepMode", "type": "u8", "enum": {0: "Up", 1: "Down"}},
            {"name": "StepSize", "type": "u8"},
            {"name": "TransitionTime", "type": "u16"}]},
        0x03: {"C→S": []},
        0x04: {"C→S": [
            {"name": "Level", "type": "u8", "note": "目标亮度 (0-254)"},
            {"name": "TransitionTime", "type": "u16"}]},
        0x05: {"C→S": [
            {"name": "MoveMode", "type": "u8", "enum": {0: "Up", 1: "Down"}},
            {"name": "Rate", "type": "u8"}]},
        0x06: {"C→S": [
            {"name": "StepMode", "type": "u8", "enum": {0: "Up", 1: "Down"}},
            {"name": "StepSize", "type": "u8"},
            {"name": "TransitionTime", "type": "u16"}]},
        0x07: {"C→S": []},
    },
    # Identify (0x0003) — spec §3.5
    0x0003: {
        0x00: {"C→S": [{"name": "IdentifyTime", "type": "u16", "note": "秒, 0=停止"}]},
        0x01: {"C→S": []},
        0x02: {"C→S": [
            {"name": "EffectIdentifier", "type": "u8", "enum": {0: "Blink", 1: "Breathe", 2: "Okay"}},
            {"name": "EffectVariant", "type": "u8"}]},
    },
    # Groups (0x0004) — spec §3.6
    0x0004: {
        0x00: {"C→S": [
            {"name": "GroupID", "type": "u16"},
            {"name": "GroupName", "type": "zstr"}]},
        0x01: {"C→S": [{"name": "GroupID", "type": "u16"}]},
        0x02: {"C→S": [
            {"name": "GroupCount", "type": "u8"},
            {"name": "GroupList", "type": "repeat",
             "repeat": [{"name": "GroupID", "type": "u16"}]}]},
        0x03: {"C→S": [{"name": "GroupID", "type": "u16"}]},
        0x04: {"C→S": []},
        0x05: {"C→S": [
            {"name": "GroupID", "type": "u16"},
            {"name": "GroupName", "type": "zstr"}]},
        # 响应 (Server→Client)
        0x00: {"S→C": [
            {"name": "Status", "type": "u8", "enum": {0: "SUCCESS", 1: "FAILURE"}},
            {"name": "GroupID", "type": "u16"}]},
        0x01: {"S→C": [
            {"name": "Status", "type": "u8", "enum": {0: "SUCCESS", 1: "FAILURE"}},
            {"name": "GroupID", "type": "u16"},
            {"name": "GroupName", "type": "zstr"}]},
        0x02: {"S→C": [
            {"name": "Capacity", "type": "u8"},
            {"name": "GroupCount", "type": "u8"},
            {"name": "GroupList", "type": "repeat",
             "repeat": [{"name": "GroupID", "type": "u16"}]}]},
        0x03: {"S→C": [
            {"name": "Status", "type": "u8", "enum": {0: "SUCCESS", 1: "FAILURE"}},
            {"name": "GroupID", "type": "u16"}]},
    },
    # Scenes (0x0005) — spec §3.7
    0x0005: {
        0x00: {"C→S": [
            {"name": "GroupID", "type": "u16"},
            {"name": "SceneID", "type": "u8"},
            {"name": "TransitionTime", "type": "u16", "note": "0.1s 单位"},
            {"name": "SceneName", "type": "zstr"},
            {"name": "ExtensionFieldSets", "type": "raw", "note": "扩展字段 (簇/长度/值 序列)"}]},
        0x01: {"C→S": [
            {"name": "GroupID", "type": "u16"},
            {"name": "SceneID", "type": "u8"}]},
        0x02: {"C→S": [
            {"name": "GroupID", "type": "u16"},
            {"name": "SceneID", "type": "u8"}]},
        0x03: {"C→S": [{"name": "GroupID", "type": "u16"}]},
        0x04: {"C→S": [
            {"name": "GroupID", "type": "u16"},
            {"name": "SceneID", "type": "u8"}]},
        0x05: {"C→S": [
            {"name": "GroupID", "type": "u16"},
            {"name": "SceneID", "type": "u8"}]},
        0x06: {"C→S": [{"name": "GroupID", "type": "u16"}]},
        # 响应
        0x00: {"S→C": [
            {"name": "Status", "type": "u8", "enum": {0: "SUCCESS", 1: "FAILURE"}},
            {"name": "GroupID", "type": "u16"},
            {"name": "SceneID", "type": "u8"}]},
        0x01: {"S→C": [
            {"name": "Status", "type": "u8", "enum": {0: "SUCCESS", 1: "FAILURE"}},
            {"name": "GroupID", "type": "u16"},
            {"name": "SceneID", "type": "u8"},
            {"name": "TransitionTime", "type": "u16"},
            {"name": "SceneName", "type": "zstr"},
            {"name": "ExtensionFieldSets", "type": "raw"}]},
        0x02: {"S→C": [
            {"name": "Status", "type": "u8", "enum": {0: "SUCCESS", 1: "FAILURE"}},
            {"name": "GroupID", "type": "u16"},
            {"name": "SceneID", "type": "u8"}]},
        0x05: {"S→C": [
            {"name": "Status", "type": "u8", "enum": {0: "SUCCESS", 1: "FAILURE"}},
            {"name": "GroupID", "type": "u16"},
            {"name": "SceneID", "type": "u8"}]},
        0x06: {"S→C": [
            {"name": "GroupCount", "type": "u8"},
            {"name": "GroupList", "type": "repeat",
             "repeat": [{"name": "GroupID", "type": "u16"}]}]},
    },
    # Door Lock (0x0101) — spec §7.2 (PIN 码为可变长 Zigbee 字符串, 可空)
    0x0101: {
        0x00: {"C→S": [{"name": "PINCode", "type": "zstr", "note": "空载荷 = 无 PIN"}]},
        0x01: {"C→S": [{"name": "PINCode", "type": "zstr", "note": "空载荷 = 无 PIN"}]},
        0x02: {"C→S": [{"name": "PINCode", "type": "zstr", "note": "空载荷 = 无 PIN"}]},
    },
    # Window Covering (0x0102) — spec §8.4
    0x0102: {
        0x00: {"C→S": []}, 0x01: {"C→S": []}, 0x02: {"C→S": []},
        0x03: {"C→S": [{"name": "LiftValue", "type": "u16", "note": "百分位 0-10000 (0.01% 单位)"}]},
        0x04: {"C→S": [{"name": "TiltValue", "type": "u16", "note": "百分位 0-10000 (0.01% 单位)"}]},
    },
    # Color Control (0x0300) — spec §3.11
    0x0300: {
        0x00: {"C→S": [
            {"name": "Hue", "type": "u8"},
            {"name": "Direction", "type": "u8", "enum": {0: "最短路径", 1: "最长路径", 2: "向上", 3: "向下"}},
            {"name": "TransitionTime", "type": "u16"}]},
        0x01: {"C→S": [
            {"name": "MoveMode", "type": "u8", "enum": {0: "Up", 1: "Down"}},
            {"name": "Rate", "type": "u8"}]},
        0x02: {"C→S": [
            {"name": "StepMode", "type": "u8", "enum": {0: "Up", 1: "Down"}},
            {"name": "StepSize", "type": "u8"},
            {"name": "TransitionTime", "type": "u16"}]},
        0x03: {"C→S": [
            {"name": "Saturation", "type": "u8"},
            {"name": "TransitionTime", "type": "u16"}]},
        0x04: {"C→S": [
            {"name": "MoveMode", "type": "u8", "enum": {0: "Up", 1: "Down"}},
            {"name": "Rate", "type": "u8"}]},
        0x05: {"C→S": [
            {"name": "StepMode", "type": "u8", "enum": {0: "Up", 1: "Down"}},
            {"name": "StepSize", "type": "u8"},
            {"name": "TransitionTime", "type": "u16"}]},
        0x06: {"C→S": [
            {"name": "Hue", "type": "u8"},
            {"name": "Saturation", "type": "u8"},
            {"name": "TransitionTime", "type": "u16"}]},
        0x07: {"C→S": [
            {"name": "ColorX", "type": "u16"},
            {"name": "ColorY", "type": "u16"},
            {"name": "TransitionTime", "type": "u16"}]},
        0x08: {"C→S": [
            {"name": "RateX", "type": "u16"},
            {"name": "RateY", "type": "u16"}]},
        0x09: {"C→S": [
            {"name": "StepX", "type": "u16"},
            {"name": "StepY", "type": "u16"},
            {"name": "TransitionTime", "type": "u16"}]},
        0x0A: {"C→S": [
            {"name": "ColorTemperatureMireds", "type": "u16"},
            {"name": "TransitionTime", "type": "u16"}]},
        0x0B: {"C→S": [
            {"name": "MoveMode", "type": "u8", "enum": {0: "Up", 1: "Down"}},
            {"name": "Rate", "type": "u16"}]},
        0x0C: {"C→S": [
            {"name": "MoveMode", "type": "u8", "enum": {0: "Up", 1: "Down"}},
            {"name": "Rate", "type": "u16"}]},
        0x0D: {"C→S": [
            {"name": "StepMode", "type": "u8", "enum": {0: "Up", 1: "Down"}},
            {"name": "StepSize", "type": "u16"},
            {"name": "TransitionTime", "type": "u16"}]},
        0x40: {"C→S": [
            {"name": "EnhancedHue", "type": "u16"},
            {"name": "Saturation", "type": "u8"},
            {"name": "TransitionTime", "type": "u16"}]},
        0x41: {"C→S": [
            {"name": "UpdateFlags", "type": "u8", "note": "bit0=action, bit1=direction, bit2=time, bit3=start hue"},
            {"name": "Action", "type": "u8", "enum": {0: "Deactivate", 1: "从 ColorLoopStartEnhancedHue 激活", 2: "从 EnhancedCurrentHue 激活"}},
            {"name": "Direction", "type": "u8", "enum": {0: "Up", 1: "Down"}},
            {"name": "Time", "type": "u16"},
            {"name": "StartEnhancedHue", "type": "u16"}]},
        0x42: {"C→S": []},
        0x43: {"C→S": [
            {"name": "MoveMode", "type": "u8", "enum": {0: "Up", 1: "Down"}},
            {"name": "Rate", "type": "u16"},
            {"name": "ColorTemperatureMinimumMireds", "type": "u16"},
            {"name": "ColorTemperatureMaximumMireds", "type": "u16"}]},
        0x44: {"C→S": [
            {"name": "StepMode", "type": "u8", "enum": {0: "Up", 1: "Down"}},
            {"name": "StepSize", "type": "u16"},
            {"name": "TransitionTime", "type": "u16"},
            {"name": "ColorTemperatureMinimumMireds", "type": "u16"},
            {"name": "ColorTemperatureMaximumMireds", "type": "u16"}]},
    },
}

# ── 全局命令载荷 schema (frame type=0, ZCL spec 2.4.2) ──
GLOBAL_PAYLOAD_SCHEMAS: dict[int, list[_Field]] = {
    0x00: [{"name": "AttributeList", "type": "repeat",
            "repeat": [{"name": "AttributeID", "type": "u16"}]}],
    0x01: [{"name": "AttributeRecords", "type": "attr_records_rsp"}],
    0x02: [{"name": "AttributeRecords", "type": "attr_records"}],
    0x03: [{"name": "AttributeRecords", "type": "attr_records"}],
    0x04: [{"name": "AttributeStatusRecords", "type": "repeat",
            "repeat": [{"name": "AttributeID", "type": "u16"},
                       {"name": "Status", "type": "u8"}]}],
    0x05: [{"name": "AttributeRecords", "type": "attr_records"}],
    0x06: [{"name": "Direction", "type": "u8", "enum": {0: "上报配置 (带 delta)", 1: "默认值配置 (带 value)"}},
           {"name": "AttributeID", "type": "u16"},
           {"name": "DataType", "type": "u8"},
           {"name": "MinimumInterval", "type": "u16"},
           {"name": "MaximumInterval", "type": "u16"},
           {"name": "剩余 (delta/默认值)", "type": "raw", "note": "delta 或默认值长度按 DataType 定义"}],
    0x07: [{"name": "StatusRecords", "type": "repeat",
            "repeat": [{"name": "Status", "type": "u8"},
                       {"name": "Direction", "type": "u8"},
                       {"name": "AttributeID", "type": "u16"}]}],
    0x08: [{"name": "Records", "type": "repeat",
            "repeat": [{"name": "Direction", "type": "u8"},
                       {"name": "AttributeID", "type": "u16"}]}],
    0x09: [{"name": "ReadReportingConfigRecords", "type": "raw",
            "note": "[status][direction][attr_id][data_type][...] 变长结构"}],
    0x0A: [{"name": "AttributeReports", "type": "attr_records"}],
    0x0B: [{"name": "RespondedCommandID", "type": "u8"},
           {"name": "Status", "type": "u8"}],
    0x0C: [{"name": "StartAttributeID", "type": "u16"},
           {"name": "MaxAttributeIDs", "type": "u8"}],
    0x0D: [{"name": "Discriminator", "type": "u8"},
           {"name": "Complete", "type": "u8"},
           {"name": "AttributeRecords", "type": "raw",
            "note": "[attr_id][data_type] 记录序列"}],
}

# ── 私有簇解析器注册表 (扩展机制) ──
# 新私有协议: PAYLOAD_PARSERS[cluster_id] = fn(cluster_id, cmd_id, payload, direction) -> dict|None
# 注册方 (如 tuya_proto.py) 在模块底部注册; 返回 None = 无法解析 → 字节偏移兜底。
PAYLOAD_PARSERS: dict[int, "Callable"] = {}


def _fmt_int(v: int, width: int = 0) -> str:
    hx = f"0x{v:0{width}X}" if width else f"0x{v:X}"
    return f"{v} ({hx})"


def _schema_for(cluster_id: int, cmd_id: int, direction: str) -> list[_Field] | None:
    cmds = CMD_PAYLOAD_SCHEMAS.get(cluster_id)
    if not cmds:
        return None
    by_dir = cmds.get(cmd_id)
    if not by_dir:
        return None
    if direction in by_dir:
        return by_dir[direction]
    return by_dir.get("*")


def _parse_attr_value(data_type: int, buf: bytes, off: int) -> tuple[str, int]:
    """按 ZCL data type 解析属性值; 返回 (显示文本, 消耗字节数)."""
    name = DATA_TYPE_NAMES.get(data_type, f"0x{data_type:02X}")
    size = _DATA_TYPE_SIZES.get(data_type)
    if data_type == 0x10:  # bool
        return "1 (true)" if buf[off] else "0 (false)", 1
    if data_type in (0x40, 0x41, 0x42, 0x43, 0x44):  # 字符串 (素材实证: 0x42 短串 1B 前缀)
        len_b = 1 if data_type in (0x40, 0x41, 0x42) else 2
        if off + len_b > len(buf):
            return f"<截断 {name}>", len(buf) - off
        s_len = buf[off] if len_b == 1 else int.from_bytes(buf[off:off + 2], "little")
        end = off + len_b + s_len
        if end > len(buf):
            return f"<截断 {name}>", len(buf) - off
        raw = buf[off + len_b:end]
        try:
            return f"\"{raw.decode('utf-8')}\"", len_b + s_len
        except UnicodeDecodeError:
            return f"hex:{raw.hex()}", len_b + s_len
    if size is not None:  # 定长数值/位图
        if off + size > len(buf):
            return f"<截断 {name}>", len(buf) - off
        v = int.from_bytes(buf[off:off + size], "little")
        return _fmt_int(v, size * 2), size
    if data_type in (0x50, 0x51, 0xE0, 0xE1):  # array/struct/set/bag
        return f"<复杂类型 {name} 见 hex>", 0
    # 未知类型: 无法确定宽度 — 剩余全量 hex
    return f"<未知类型 0x{data_type:02X} hex:{buf[off:].hex()}>", len(buf) - off


def _parse_attr_records(buf: bytes, off: int, with_status: bool,
                        cluster_id: int | None = None) -> tuple[list[dict], int]:
    """解析属性记录序列: [attr_id:u16][(status:u8)] [data_type:u8][值].
    返回 (字段列表, 新偏移); 记录越界即停 (剩余交给上层).
    cluster_id 用于属性名表 (U15 修正: 曾硬编码 Basic 簇, On/Off attr 0x0000 误标
    ZCLVersion → 实为 OnOff)."""
    fields: list[dict] = []
    while off + 3 <= len(buf):
        attr_id = int.from_bytes(buf[off:off + 2], "little")
        off += 2
        st = None
        if with_status:
            st = buf[off]; off += 1
            if st != 0:
                # 非成功状态: 记录后无 data_type/value (0x86=属性不支持 素材实证:
                # Read Attr Rsp [attr 0xFFC0][0x86] 曾按值解析错位)
                nm = _ATTR_NAMES.get(cluster_id or 0, {}).get(attr_id, "")
                fields.append({"field": f"attr 0x{attr_id:04X}{(' ' + nm) if nm else ''}",
                               "value": f"status 0x{st:02X}",
                               "note": _ZCL_STATUS_NAMES.get(st, "非成功状态")})
                continue
        if off >= len(buf):
            break
        data_type = buf[off]; off += 1
        val, consumed = _parse_attr_value(data_type, buf, off)
        if consumed <= 0:
            break
        off += consumed
        nm = _ATTR_NAMES.get(cluster_id or 0, {}).get(attr_id, "")
        fields.append({"field": f"attr 0x{attr_id:04X}{(' ' + nm) if nm else ''}",
                       "value": val,
                       "note": DATA_TYPE_NAMES.get(data_type, f"type 0x{data_type:02X}")})
    return fields, off


def _parse_schema_fields(schema: list[_Field], payload: bytes,
                         cluster_id: int | None = None) -> tuple[list[dict], int]:
    """按 schema 解析 payload → (字段列表, 剩余未消费字节数).
    任一字段读取越界 → 停止 (剩余字节由上层以 hex 兜底展示, 不臆造)."""
    fields: list[dict] = []
    off = 0
    for fd in schema:
        ftype = fd["type"]
        fname = fd.get("name", ftype)
        if off >= len(payload) and ftype != "raw" and ftype != "zstr" and ftype != "attr_records" and ftype != "attr_records_rsp":
            # 无载荷但 schema 要求字段: 仅对空 schema 命令 (无字段) 正常
            break
        if ftype == "u8":
            if off + 1 > len(payload): break
            v = payload[off]; off += 1
            en = fd.get("enum")
            txt = f"{en.get(v, '')} ({v})" if en and v in en else _fmt_int(v, 2)
            fields.append({"field": fname, "value": txt, "note": fd.get("note", "")})
        elif ftype in ("u16", "u24", "u32", "u40", "u48", "u64"):
            n = int(ftype[1:]) // 8
            if off + n > len(payload): break
            v = int.from_bytes(payload[off:off + n], "little"); off += n
            en = fd.get("enum")
            txt = f"{en.get(v, '')} ({v})" if en and v in en else _fmt_int(v, n * 2)
            fields.append({"field": fname, "value": txt, "note": fd.get("note", "")})
        elif ftype == "zstr":
            if off + 1 > len(payload): break
            s_len = payload[off]; off += 1
            end = off + s_len
            if end > len(payload): break
            raw = payload[off:end]; off = end
            try:
                txt = f"\"{raw.decode('utf-8')}\"" if s_len else "(空)"
            except UnicodeDecodeError:
                txt = f"hex:{raw.hex()}"
            fields.append({"field": fname, "value": txt, "note": fd.get("note", "")})
        elif ftype.startswith("bytes:"):
            n = int(ftype.split(":")[1])
            if off + n > len(payload): break
            fields.append({"field": fname, "value": payload[off:off + n].hex(), "note": fd.get("note", "")})
            off += n
        elif ftype == "raw":
            rem = payload[off:]
            if rem:
                fields.append({"field": fname, "value": rem.hex(), "note": fd.get("note", "")})
            off = len(payload)
        elif ftype == "repeat":
            item_fields, new_off = _parse_repeat(fd.get("repeat", []), payload, off)
            if not item_fields:
                break  # 首轮即失败 → 上层兜底
            fields.append({"field": fname, "value": f"{len(item_fields)} 项", "note": ""})
            fields.extend(item_fields)
            off = new_off
        elif ftype in ("attr_records", "attr_records_rsp"):
            rec_fields, new_off = _parse_attr_records(
                payload, off, with_status=(ftype == "attr_records_rsp"),
                cluster_id=cluster_id)
            if rec_fields:
                fields.append({"field": fname, "value": f"{len(rec_fields)} 项", "note": ""})
                fields.extend(rec_fields)
                off = new_off
            else:
                break
        else:
            break  # 未知类型 — 不臆造
    return fields, off


def _parse_repeat(item_schema: list[_Field], payload: bytes, off: int) -> tuple[list[dict], int]:
    """repeat 结构: 循环解析 item_schema 直到字节耗尽或首轮越界."""
    fields: list[dict] = []
    idx = 1
    while off < len(payload):
        before = off
        for fd in item_schema:
            ftype = fd["type"]
            if ftype == "u8":
                if off + 1 > len(payload): return fields, off
                v = payload[off]; off += 1
                fields.append({"field": f"#{idx} {fd.get('name', '')}", "value": _fmt_int(v, 2),
                               "note": fd.get("note", "")})
            elif ftype == "u16":
                if off + 2 > len(payload): return fields, off
                v = int.from_bytes(payload[off:off + 2], "little"); off += 2
                fields.append({"field": f"#{idx} {fd.get('name', '')}", "value": _fmt_int(v, 4),
                               "note": fd.get("note", "")})
            else:
                return fields, off  # repeat 内仅支持定长字段
        if off == before:
            return fields, off  # 无进展保护
        idx += 1
    return fields, off


def parse_zcl_command_payload(cluster_id: int | None, cmd_id: int | None,
                              frame_type: int | None, payload: bytes,
                              direction: str | None = None) -> dict | None:
    """ZCL 命令载荷字段级解析 (标准 schema / 私有注册表)。

    返回 {"parser": 解析器名, "mode": "schema", "fields": [{field, value, note}], "hex": str}
    无匹配 schema / 首字段解析失败 → None (由 parse_zcl_payload 走字节偏移兜底).
    """
    if cmd_id is None or not payload:
        return None
    if frame_type == 0:
        schema = GLOBAL_PAYLOAD_SCHEMAS.get(cmd_id)
        parser = "全局命令"
    elif frame_type == 1:
        # 私有簇注册表优先 (涂鸦 0xEF00 等; 注册表内部可能返回 dict 或 None)
        if cluster_id is not None and cluster_id in PAYLOAD_PARSERS:
            try:
                r = PAYLOAD_PARSERS[cluster_id](cluster_id, cmd_id, payload, direction)
            except Exception:
                r = None
            if r is not None:
                return r
        schema = _schema_for(cluster_id, cmd_id, direction or "C→S")
        parser = f"{get_cluster_name(cluster_id) or f'0x{cluster_id:02X}'}"
    else:
        schema = None
        parser = ""
    if schema is None:
        return None
    fields, off = _parse_schema_fields(schema, payload, cluster_id)
    if not fields:
        return None
    if off < len(payload):
        fields.append({"field": "⚠️ 剩余字节 (schema 解析中断)",
                       "value": payload[off:].hex(), "note": "长度与规范不符, 余下按 hex 展示"})
    return {"parser": parser, "mode": "schema", "fields": fields, "hex": payload.hex()}


def fallback_byte_fields(payload: bytes, max_bytes: int = 256) -> list[dict]:
    """字节偏移兜底拆解 (Wireshark/Ubiqua 式, 用户示例 2026-08-24):
    整段载荷按 8 字节一组展示 (偏移 | hex 组 | 可打印字符), 不逐字节拆表 —
    一眼可见私有命令整体数据, 方便对接时自行对照结构.

    长载荷截断到 max_bytes (避免超大载荷刷屏), 剩余标提示; 完整 hex 仍在
    parse_zcl_payload 返回的 hex 字段 (详情面板下方)."""
    fields: list[dict] = []
    shown = min(len(payload), max_bytes)
    for i in range(0, shown, 8):
        chunk = payload[i:i + 8]
        hexs = " ".join(f"{b:02X}" for b in chunk)
        chars = "".join(chr(b) if 0x20 <= b < 0x7F else "·" for b in chunk)
        fields.append({"field": f"0x{i:04X}", "value": hexs, "note": chars})
    if len(payload) > shown:
        fields.append({"field": "…",
                       "value": f"剩余 {len(payload) - shown} 字节 (见下方完整 hex)",
                       "note": ""})
    return fields


def parse_zcl_payload(cluster_id: int | None, cmd_id: int | None,
                      frame_type: int | None, payload: bytes,
                      direction: str | None = None) -> dict:
    """主入口 (packet_detail/导出共用): 标准 schema → 私有注册表 → 字节偏移兜底.
    永不返回 None (兜底链总有输出); payload 为空时返回 None 由调用方跳过."""
    if not payload:
        return {"parser": "", "mode": "empty", "fields": [], "hex": ""}
    r = parse_zcl_command_payload(cluster_id, cmd_id, frame_type, payload, direction)
    if r is not None:
        return r
    return {"parser": "字节偏移兜底", "mode": "fallback",
            "fields": fallback_byte_fields(payload), "hex": payload.hex()}
