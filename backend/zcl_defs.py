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
    # None/未知: 现有回退逻辑
    if cluster_id is not None and cluster_id in CLUSTER_COMMANDS:
        if cmd_id in CLUSTER_COMMANDS[cluster_id]:
            return CLUSTER_COMMANDS[cluster_id][cmd_id]
    return GLOBAL_COMMANDS.get(cmd_id)


def get_cluster_commands(cluster_id: int) -> dict[int, str] | None:
    """获取特定 Cluster 的所有 Command 定义"""
    return CLUSTER_COMMANDS.get(cluster_id)
