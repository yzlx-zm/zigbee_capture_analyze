# -*- coding: utf-8 -*-
"""ZAP XML → zcl_defs 标准数据生成器 (S4 2026-08-27, 用户对齐: 标准文档自动化).

数据源: gecko_sdk_v4.3.2/app/zcl/*.xml (Silicon Labs 官方 ZAP ZCL 定义, 与
Zigbee Cluster Library spec 一致, 机器可读 — 替代人工逐个簇核对 Ubiqua)。

输出: backend/zcl_defs_std.py — 含:
  CLUSTER_COMMANDS_STD: {cluster_code: {cmd_code: "命令名"}}   (全部簇命令)
  CMD_PAYLOAD_SCHEMAS_STD: {cluster: {cmd: {方向: [字段]}}}    (字段级载荷)
  CLUSTER_ATTRIBUTES_STD: {cluster_code: {attr_code: "属性名"}} (属性 ID → 名, Read Attributes 显示用)
  ENUMS_STD: {枚举类型名: {value: "item 名"}}                  (枚举表)

类型映射 (ZAP → 本工具 schema 类型):
  INT8U/ENUM8/BOOLEAN → u8        INT16U/ENUM16 → u16
  INT24U → u24                     INT32U → u32
  INT40U → u40                     INT48U → u48
  INT64U → u64
  CHAR_STRING/OCTET_STRING → zstr  (Zigbee 字符串: 1B 长度前缀)
  枚举类型名 → u8/u16 + enum 查找 types.xml
  其他/未知 → bytes:4 (原始 hex 展示, 不臆造)

用法: python scripts/zap_xml_extract.py [zcl_xml_dir] [out_path]
默认: C:/Users/Administrator/SimplicityStudio/SDKs/gecko_sdk_v4.3.2/app/zcl
      → backend/zcl_defs_std.py
"""
from __future__ import annotations

import os
import re
import sys
from pathlib import Path

# ── 簇 XML 文件 (全部应用 profile; types.xml 是类型/枚举定义) ──
CLUSTER_FILES = [
    "general.xml", "ha.xml", "green-power.xml", "zll.xml",
    "wwah-silabs.xml", "ami.xml", "cba.xml", "hc.xml",
    "lo.xml", "ta.xml", "relay-control.xml", "sleeping-mesh.xml",
    "zigbee-direct.xml", "sample-extensions.xml", "silabs.xml",
]

# ZAP 类型 → 本工具 schema 类型
_TYPE_MAP = {
    "INT8U": "u8", "ENUM8": "u8", "BOOLEAN": "u8",
    "INT16U": "u16", "ENUM16": "u16",
    "INT24U": "u24",
    "INT32U": "u32",
    "INT40U": "u40",
    "INT48U": "u48",
    "INT64U": "u64",
    "CHAR_STRING": "zstr", "OCTET_STRING": "zstr",
}


def _camel_to_words(name: str) -> str:
    """OperationEventNotification → Operation Event Notification"""
    return re.sub(r'(?<=[a-z0-9])(?=[A-Z])|(?<=[A-Z])(?=[A-Z][a-z])', ' ', name)


def parse_enums(xml: str) -> dict[str, dict[int, str]]:
    """types.xml 枚举: <enum name="X"> <item name value/> </enum>"""
    enums: dict[str, dict[int, str]] = {}
    for m in re.finditer(r'<enum\s+name="(\w+)"[^>]*>(.*?)</enum>', xml, re.S):
        name, body = m.group(1), m.group(2)
        items: dict[int, str] = {}
        for it in re.finditer(r'<item\s+name="([^"]+)"\s+value="(0x[0-9A-Fa-f]+|\d+)"', body):
            try:
                v = int(it.group(2), 16) if it.group(2).startswith("0x") else int(it.group(2))
            except ValueError:
                continue
            items[v] = _camel_to_words(it.group(1))
        enums[name] = items
    return enums


def parse_clusters(xml: str, enums: dict) -> dict:
    """簇定义: <cluster><name/><code/>...<command/>...</cluster> → 数据"""
    clusters: dict[int, dict] = {}
    for m in re.finditer(r'<cluster\b[^>]*>(.*?)</cluster>', xml, re.S):
        body = m.group(1)
        code_m = re.search(r'<code>(0x[0-9A-Fa-f]+)</code>', body)
        name_m = re.search(r'<name>([^<]+)</name>', body)
        if not code_m or not name_m:
            continue
        code = int(code_m.group(1), 16)
        clusters[code] = {"name": name_m.group(1).strip(), "cmds": {}, "attrs": {}}
        # 属性定义 (Read Attributes 属性 ID → 名, 对齐 Ubiqua 显示)
        for am in re.finditer(r'<attribute\b([^>]*)>([^<]*)</attribute>', body):
            aa = dict(re.findall(r'(\w+)="([^"]*)"', am.group(1)))
            try:
                acode = int(aa["code"], 16)
            except (KeyError, ValueError):
                continue
            aname = am.group(2).strip() or _camel_to_words(aa.get("define", ""))
            if acode not in clusters[code]["attrs"]:
                clusters[code]["attrs"][acode] = aname
        for cm in re.finditer(
                r'<command\b([^>]*)>(.*?)</command>', body, re.S):
            attrs, cbody = cm.group(1), cm.group(2)
            ca = dict(re.findall(r'(\w+)="([^"]*)"', attrs))
            cname = ca.get("name", "")
            try:
                ccode = int(ca["code"], 16)
            except (KeyError, ValueError):
                continue
            source = ca.get("source", ca.get("side", ""))  # client/server/both
            dirs = []
            if source in ("client", "both", ""):
                dirs.append("C→S")
            if source in ("server", "both", ""):
                dirs.append("S→C")
            fields = []
            for am in re.finditer(r'<arg\b([^>]*)/?>', cbody):
                aa = dict(re.findall(r'(\w+)="([^"]*)"', am.group(1)))
                fname = _camel_to_words(aa.get("name", ""))
                ftype = aa.get("type", "")
                note = aa.get("introducedIn", "")
                st = _field_schema(ftype, fname, enums)
                if st:
                    if note:
                        st["note"] = f"({note})"
                    fields.append(st)
            # 同 code 命令 (C→S 命令 + S→C 响应同 code, 如 Groups 0x00 Add Group
            # 与 Add Group Response) — 合并方向/字段, 名称去重 "A / B"
            if ccode in clusters[code]["cmds"]:
                cur = clusters[code]["cmds"][ccode]
                names = [cur["name"], _camel_to_words(cname)]
                cur["name"] = " / ".join(dict.fromkeys(names))
                for d in dirs:
                    if d not in cur["dirs"]:
                        cur["dirs"].append(d)
                cur["fields"][d] = fields  # 方向 → 字段 (同方向覆盖: 后定义优先)
            else:
                clusters[code]["cmds"][ccode] = {
                    "name": _camel_to_words(cname), "dirs": dirs,
                    "fields": {d: fields for d in dirs}}
    return clusters


def _field_schema(zap_type: str, fname: str, enums: dict) -> dict | None:
    """ZAP 类型 → schema 字段; 枚举类型查 types.xml; 未知 → bytes:4 不臆造"""
    if zap_type in _TYPE_MAP:
        t = _TYPE_MAP[zap_type]
        return {"name": fname, "type": t}
    if zap_type in enums:
        items = enums[zap_type]
        # 枚举值范围判断 u8/u16
        t = "u16" if max(items) > 0xFF else "u8"
        return {"name": fname, "type": t, "enum": items}
    # 未知类型 (复合结构) — 不臆造, 按字节展示
    return {"name": fname, "type": "bytes:4"}


def main() -> None:
    zcl_dir = sys.argv[1] if len(sys.argv) > 1 else \
        r"C:/Users/Administrator/SimplicityStudio/SDKs/gecko_sdk_v4.3.2/app/zcl"
    out_path = sys.argv[2] if len(sys.argv) > 2 else \
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "backend",
                     "zcl_defs_std.py")
    zcl_dir = Path(zcl_dir)
    enums: dict = {}
    clusters: dict[int, dict] = {}
    src_map: dict[int, str] = {}  # cluster → 源文件 (审计)
    for fn in CLUSTER_FILES:
        p = zcl_dir / fn
        if not p.exists():
            print(f"⚠️ 跳过缺失文件: {fn}")
            continue
        xml = p.read_text(encoding="utf-8")
        if fn == "types.xml":
            continue
        enums.update(parse_enums((zcl_dir / "types.xml").read_text(encoding="utf-8")))
        cs = parse_clusters(xml, enums)
        for code, c in cs.items():
            if code not in clusters:
                clusters[code] = c
                src_map[code] = fn
            else:
                # 同簇多文件 (silabs 扩展) — 合并命令/属性 (已有优先)
                for cc, cmd in c["cmds"].items():
                    clusters[code]["cmds"].setdefault(cc, cmd)
                for ac, an in c["attrs"].items():
                    clusters[code]["attrs"].setdefault(ac, an)

    # ── 生成 Python 数据文件 ──
    lines = []
    lines.append('# -*- coding: utf-8 -*-')
    lines.append('"""标准 ZCL 数据 — 由 scripts/zap_xml_extract.py 从 gecko_sdk ZAP XML')
    lines.append('(Silicon Labs 官方, 与 Zigbee Cluster Library spec 一致) 自动生成.')
    lines.append('勿手改 — 重新生成: python scripts/zap_xml_extract.py')
    lines.append('"""')
    lines.append('')
    lines.append('CLUSTER_COMMANDS_STD: dict[int, dict[int, str]] = {')
    for code in sorted(clusters):
        cmds = clusters[code]["cmds"]
        lines.append(f'    # {clusters[code]["name"]} (0x{code:04X}) [{src_map[code]}]')
        lines.append(f'    0x{code:04X}: {{')
        for cc in sorted(cmds):
            lines.append(f'        {cc}: {cmds[cc]["name"]!r},')
        lines.append('    },')
    lines.append('}')
    lines.append('')
    lines.append('CMD_PAYLOAD_SCHEMAS_STD: dict[int, dict[int, dict[str, list]]] = {')
    for code in sorted(clusters):
        cmds = clusters[code]["cmds"]
        with_fields = {cc: c for cc, c in cmds.items() if c["fields"]}
        if not with_fields:
            continue
        lines.append(f'    # {clusters[code]["name"]} (0x{code:04X}) [{src_map[code]}]')
        lines.append(f'    0x{code:04X}: {{')
        for cc in sorted(with_fields):
            c = with_fields[cc]
            # 同 code 多方向 (C→S 命令 + S→C 响应) 合并进同一条目 — 拆行输出
            # 否则生成重复 dict 键 (后者覆盖前者, Groups 0x00 C→S 丢失实锤)
            lines.append(f'        {cc}: {{')
            for d in c["dirs"]:
                fields = c["fields"].get(d, [])
                lines.append(f'            "{d}": [')
                for f in fields:
                    parts = [f"\"name\": {f['name']!r}", f"\"type\": {f['type']!r}"]
                    if "enum" in f:
                        en = ", ".join(f"{k}: {v!r}" for k, v in sorted(f["enum"].items()))
                        parts.append(f"\"enum\": {{{en}}}")
                    if "note" in f:
                        parts.append(f"\"note\": {f['note']!r}")
                    lines.append(f'                {{{", ".join(parts)}}},')
                lines.append('            ],')
            lines.append('        },')
        lines.append('    },')
    lines.append('}')
    lines.append('')
    lines.append('CLUSTER_ATTRIBUTES_STD: dict[int, dict[int, str]] = {')
    for code in sorted(clusters):
        attrs = clusters[code]["attrs"]
        if not attrs:
            continue
        lines.append(f'    # {clusters[code]["name"]} (0x{code:04X}) [{src_map[code]}]')
        lines.append(f'    0x{code:04X}: {{')
        for ac in sorted(attrs):
            lines.append(f'        {ac}: {attrs[ac]!r},')
        lines.append('    },')
    lines.append('}')
    lines.append('')
    lines.append('ENUMS_STD: dict[str, dict[int, str]] = {')
    for name in sorted(enums):
        items = ", ".join(f"{k}: {v!r}" for k, v in sorted(enums[name].items()))
        lines.append(f'    {name!r}: {{{items}}},')
    lines.append('}')
    out = Path(out_path).resolve()
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"✅ 生成 {out}")
    print(f"   簇: {len(clusters)} | 命令: {sum(len(c['cmds']) for c in clusters.values())}"
          f" | 枚举类型: {len(enums)}")
    print(f"   源文件: {[f for f in CLUSTER_FILES if (zcl_dir/f).exists()]}")


if __name__ == "__main__":
    main()
