"""zigbee_pc_keys 文件管理 — 读/写/统计"""
from __future__ import annotations

import os

# zigbee_pc_keys 文件路径
WIRESHARK_CONFIG_DIR = os.path.expandvars(r"%APPDATA%\Wireshark")
KEYS_FILE = os.path.join(WIRESHARK_CONFIG_DIR, "zigbee_pc_keys")

# 预设密钥 (TC Link Key)
PRESET_KEYS: dict[str, str] = {
    "ZigBeeAlliance09": "5A6967426565416C6C69616E63653039",
}


def _ensure_dir() -> None:
    os.makedirs(WIRESHARK_CONFIG_DIR, exist_ok=True)


def normalize_hex(raw: str) -> str:
    """将各种格式的 hex key 统一为 32 位大写无分隔符"""
    clean = raw.replace(":", "").replace(" ", "").replace("-", "").upper().strip()
    if len(clean) != 32:
        raise ValueError(f"Key 必须是 16 字节 (32 位 hex), 当前: {len(clean)} 位")
    return clean


def read_all_keys() -> list[dict]:
    """读取 zigbee_pc_keys 中所有 Key, 返回 [{hex, label, is_preset}]"""
    if not os.path.exists(KEYS_FILE):
        # 自动创建并写入预设 Key
        _ensure_dir()
        write_all_keys([])
        return _with_presets([])

    keys = []
    with open(KEYS_FILE, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            # 格式: "hex","Normal","label"
            parts = line.split(",")
            if len(parts) >= 1:
                hex_val = parts[0].strip().strip('"')
                label = parts[2].strip().strip('"') if len(parts) >= 3 else ""
                keys.append({"hex": hex_val, "label": label})

    return _with_presets(keys)


def _with_presets(custom_keys: list[dict]) -> list[dict]:
    """合并预设 Key 和自定义 Key"""
    result = []
    preset_labels = {k["label"] for k in custom_keys if k.get("is_preset")}
    for label, hex_val in PRESET_KEYS.items():
        result.append({"hex": hex_val, "label": label, "is_preset": True})
    for k in custom_keys:
        k["is_preset"] = k.get("is_preset", False)
        result.append(k)
    return result


def write_all_keys(custom_keys: list[dict]) -> None:
    """写入全部自定义 Key (预设 Key 也一起写入, 确保 tshark 可见)"""
    _ensure_dir()
    all_keys = []
    # 先加预设
    for label, hex_val in PRESET_KEYS.items():
        all_keys.append({"hex": hex_val, "label": label})
    # 再加自定义
    for k in custom_keys:
        all_keys.append({"hex": k["hex"], "label": k["label"]})

    with open(KEYS_FILE, "w", encoding="utf-8") as f:
        for k in all_keys:
            f.write(f'"{k["hex"]}","Normal","{k["label"]}"\n')


def add_key(hex_raw: str, label: str) -> dict:
    """添加一个 Key, 返回 {hex, label}"""
    clean = normalize_hex(hex_raw)
    existing = read_all_keys()
    # 检查是否重复
    for k in existing:
        if k.get("is_preset"):
            continue
        if k["hex"] == clean:
            raise ValueError(f"Key {clean[:8]}... 已存在 (标签: {k['label']})")
        if k["label"] == label and label:
            raise ValueError(f"标签 '{label}' 已存在")

    custom = [k for k in existing if not k.get("is_preset")]
    custom.append({"hex": clean, "label": label})
    write_all_keys(custom)
    return {"hex": clean, "label": label}


def remove_key(label: str) -> bool:
    """删除一个自定义 Key (预设 Key 不可删除)"""
    if label in PRESET_KEYS:
        raise ValueError(f"预设 Key '{label}' 不可删除")
    existing = read_all_keys()
    custom = [k for k in existing if not k.get("is_preset") and k["label"] != label]
    if len(custom) == len([k for k in existing if not k.get("is_preset")]):
        return False  # 没找到
    write_all_keys(custom)
    return True


def get_match_stats(packets: list[dict]) -> dict:
    """统计 Key 命中情况: 哪些 Key 解密了多少帧"""
    key_counts: dict[str, int] = {}
    total_data = 0
    decrypted = 0
    cluster_counts: dict[int, int] = {}

    for p in packets:
        if p.get("pkt_type") == "Data":
            total_data += 1
        if p.get("decrypted"):
            decrypted += 1
            label = p.get("sec_key_label", "")
            if label:
                key_counts[label] = key_counts.get(label, 0) + 1
            cid = p.get("aps_cluster")
            if cid is not None:
                cluster_counts[cid] = cluster_counts.get(cid, 0) + 1

    all_keys = read_all_keys()
    matched_keys = []
    unmatched_keys = []
    for k in all_keys:
        count = key_counts.get(k["label"], 0)
        if count > 0:
            matched_keys.append({**k, "frame_count": count})
        elif not k.get("is_preset"):
            unmatched_keys.append(k)

    return {
        "total_data_frames": total_data,
        "decrypted": decrypted,
        "encrypted": total_data - decrypted,
        "decrypt_rate": round(decrypted / total_data, 3) if total_data else 0,
        "by_cluster": {f"0x{k:04X}": v for k, v in sorted(cluster_counts.items())},
        "matched_keys": matched_keys,
        "unmatched_keys": unmatched_keys,
    }
