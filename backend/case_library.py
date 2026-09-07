"""案例库 — 诊断页学习机制 (U12, 2026-09-07)

场景 tab = 学习容器: 导入问题包 + 标注 → 案例入库 → 场景案例积累 →
结论由案例支撑越来越准 → 导出传播到其他设备。

存储设计 (grilling 对齐 v2):
- 目录: <config.APP_DATA_DIR>/cases/ (开发模式 = 项目根/cases, 打包后
  %APPDATA%/zigbee-analyzer/cases — T2 数据分层, 用户数据不随更新覆盖)
- 每案例一个 JSON: cases/<id>.json; 素材副本 cases/materials/<id>.cubx
- 案例不含密钥 (导出时 _redact 同思路 — 案例 JSON 本身不存密钥字段)

相似检索 (find_similar): 简单可迭代 — 场景集合 Jaccard + 根因/现象关键词
+ PAN/设备地址, 不引入向量化 (ticket 明确边界)。
"""
from __future__ import annotations

import json
import os
import re
import shutil
import time
import uuid
import zipfile
from pathlib import Path

from . import config

# ── 55 场景全表 (docs/network_problems_taxonomy.md v1.0, ADR-0001) ──
# (编号, 白话名) — 检测器覆盖的 13 个标 covered=True (S2 实测 13/55)
SCENARIOS: dict[str, dict] = {}
def _reg(sid: str, name: str, covered: bool = False) -> None:
    SCENARIOS[sid] = {"id": sid, "name": name, "covered": covered}

# L1 网络形成与入网 (7)
_reg("L1-1", "设备找不到网络", True)
_reg("L1-2", "设备入网失败或被拒", True)
_reg("L1-3", "密钥分发或验证出问题", True)
_reg("L1-4", "设备被网关拒绝或踢出", True)
_reg("L1-5", "大网络多跳入网失败")
_reg("L1-6", "并发入网风暴")
_reg("L1-7", "误入错误网络")
# L2 设备在线维持 (6)
_reg("L2-1", "终端频繁离线", True)
_reg("L2-2", "父节点子设备表老化")
_reg("L2-3", "孤儿重入网循环")
_reg("L2-4", "路由器掉线连锁离线")
_reg("L2-5", "设备移动后失联")
_reg("L2-6", "设备静默失联", True)
# L3 运营期核心 (20)
_reg("L3-1", "命令收不到确认", True)
_reg("L3-2", "命令送达但未执行", True)
_reg("L3-3", "状态上报滞后", True)
_reg("L3-4", "绑定/组播命令未达")
_reg("L3-5", "设备收不到网关下发 (源路由失效)", True)
_reg("L3-6", "路由校验失败")
_reg("L3-7", "路由路径震荡")
_reg("L3-8", "目标不可达/地址未分配")
_reg("L3-9", "链路质量不对称", True)
_reg("L3-10", "路由表溢出")
_reg("L3-11", "命令反复重发", True)
_reg("L3-12", "端到端延迟过大")
_reg("L3-13", "广播中继失败")
_reg("L3-14", "消息队列满")
_reg("L3-15", "路由表抖动")
_reg("L3-16", "TC Link Key 更新失败")
_reg("L3-17", "信任中心更换异常")
_reg("L3-18", "未知命令")
_reg("L3-19", "低电量路由失败")
_reg("L3-20", "密钥不同步/轮换失败")
# L4 网络级维护 (5)
_reg("L4-1", "信道切换未跟随")
_reg("L4-2", "信道干扰")
_reg("L4-3", "PAN ID 变更/冲突")
_reg("L4-4", "广播风暴/限速")
_reg("L4-5", "网络规模超限")
# L5 应用/功能层 (4)
_reg("L5-1", "OTA 升级中断")
_reg("L5-2", "OTA 镜像请求失败")
_reg("L5-3", "Touchlink 加入失败")
_reg("L5-4", "ZCL 命令超时")
# L6 SED 专项 (5)
_reg("L6-S1", "父节点间接队列满")
_reg("L6-S2", "轮询间隔超时丢消息")
_reg("L6-S3", "SED 消息收不到 (间接事务过期)", True)
_reg("L6-S4", "SED 假阳性在线")
_reg("L6-S5", "Poll Control 集群故障")
# L7 MAC/物理层 (4)
_reg("L7-1", "MAC 无确认")
_reg("L7-2", "信道接入失败")
_reg("L7-3", "MAC 重传风暴")
_reg("L7-4", "帧校验失败")
# L8 设备硬件/固件 (3)
_reg("L8-1", "设备硬件故障")
_reg("L8-2", "设备软件故障")
_reg("L8-3", "堆栈/硬件不匹配")

SCENARIO_TOTAL = len(SCENARIOS)  # = 54 (taxonomy §"完整场景清单" 逐条计数; 文档标题
# 写 "~55" 为约数 — L1 7+L2 6+L3 20+L4 5+L5 4+L6 5+L7 4+L8 3 = 54, 实际以本表为准)

# 检测器 key → 场景号 (检测命中集合提取用; L6 端点 key l6_3 对应场景 L6-S3)
_DETECTOR_SCENARIO = {
    "l1_1": "L1-1", "l1_2": "L1-2", "l1_3": "L1-3", "l1_4": "L1-4",
    "l2_1": "L2-1", "l2_6": "L2-6",
    "l3_1": "L3-1", "l3_2": "L3-2", "l3_3": "L3-3", "l3_5": "L3-5",
    "l3_9": "L3-9", "l3_11": "L3-11",
    "l6_3": "L6-S3",
}

# 根因建议列表 (标注表单下拉; 来自已验证素材根因, 可迭代)
ROOT_CAUSE_SUGGESTIONS = [
    "源路由/MTORR 路由失效 (L3-5)",
    "中继/父节点下行链路断 (非对称)",
    "设备被网关踢出 (TC deny / 白名单)",
    "密钥分发失败 (TC link key 缺失)",
    "设备固件不回独立 APS Ack (以 ZCL 响应确认)",
    "父节点间接队列满/过期 (SED)",
    "设备静默失联 (无 Leave 帧)",
    "抓包器盲区/漏帧 (非设备问题)",
    "网关不支持该命令 (Default Response 拒绝)",
    "现场环境干扰 (同频/距离)",
    "其他 (手填)",
]

SEVERITY_LEVELS = ["high", "medium", "low"]


def cases_dir() -> Path:
    """案例库根目录 (惰性创建)."""
    d = Path(config.APP_DATA_DIR) / "cases"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _materials_dir() -> Path:
    d = cases_dir() / "materials"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _case_path(case_id: str) -> Path:
    return cases_dir() / f"{case_id}.json"


# ── 案例读写 ──

def add_case(annotation: dict, detection: dict, meta: dict,
             source_path: str | None = None, copy_material: bool = True) -> dict:
    """案例入库.

    - annotation: {phenomenon, root_cause, severity, environment} (phenomenon 必填)
    - detection: {scenario_hits: [...], verdicts: {...}} — 自动检测命中
      (scenarios_verdicts: {场景号: verdict} 全量, 入库时算好供差距报告)
    - meta: {pan, device_addr, time_range: [t0, t1], frames, source_file}
    - source_path: 素材原路径; copy_material=True 复制到 cases/materials/<id>.cubx
    """
    phenomenon = (annotation.get("phenomenon") or "").strip()
    if not phenomenon:
        raise ValueError("现象 (phenomenon) 必填")
    case_id = time.strftime("%Y%m%d") + "-" + uuid.uuid4().hex[:8]
    # 归属场景: 自动命中 ∪ 人工确认 (去重保序)
    auto_hits = [h for h in (detection.get("scenario_hits") or [])
                 if h in SCENARIOS]
    manual = [m for m in (detection.get("manual_scenarios") or [])
              if m in SCENARIOS]
    scenarios = list(dict.fromkeys(auto_hits + manual))
    if not scenarios:
        raise ValueError("场景归属为空 (自动命中与人工确认均无)")

    case = {
        "id": case_id,
        "ts": time.time(),
        "source_file": meta.get("source_file") or (
            os.path.basename(source_path) if source_path else ""),
        "material_copy": None,
        "pan": meta.get("pan"),
        "device_addr": meta.get("device_addr"),
        "time_range": meta.get("time_range"),  # [t0, t1] epoch
        "frames": meta.get("frames"),
        "annotation": {
            "phenomenon": phenomenon,
            "root_cause": (annotation.get("root_cause") or "").strip() or None,
            "severity": annotation.get("severity") if annotation.get("severity")
            in SEVERITY_LEVELS else "medium",
            "environment": (annotation.get("environment") or "").strip() or None,
        },
        "scenarios": scenarios,               # 案例归属 (自动 ∪ 人工)
        "detection": {
            "auto_hits": auto_hits,           # 检测器自动命中
            "manual_only": [s for s in scenarios if s not in auto_hits],
            "verdicts": detection.get("verdicts") or {},  # {场景号: verdict} 快照
        },
        "status": "new",                      # new / reviewed / closed
    }
    # 素材副本 (导出传播自带素材; 默认复制可关闭 — 磁盘占用控制)
    if copy_material and source_path and os.path.isfile(source_path):
        dst = _materials_dir() / f"{case_id}{Path(source_path).suffix.lower()}"
        try:
            shutil.copy2(source_path, dst)
            case["material_copy"] = str(dst)
        except OSError:
            case["material_copy"] = None  # 复制失败不阻断入库 (诚实: 无副本)
    _case_path(case_id).write_text(
        json.dumps(case, ensure_ascii=False, indent=2), encoding="utf-8")
    return case


def list_cases(scenario: str | None = None) -> list[dict]:
    """案例列表 (ts 降序); scenario 过滤 = 归属含该场景."""
    out: list[dict] = []
    for f in cases_dir().glob("*.json"):
        try:
            c = json.loads(f.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue
        if scenario and scenario not in (c.get("scenarios") or []):
            continue
        out.append(c)
    out.sort(key=lambda c: c.get("ts") or 0, reverse=True)
    return out


def get_case(case_id: str) -> dict | None:
    p = _case_path(case_id)
    if not p.is_file():
        return None
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None


def update_case(case_id: str, fields: dict) -> dict | None:
    """更新案例字段 (status / annotation / scenarios); 不动 id/ts/素材."""
    c = get_case(case_id)
    if not c:
        return None
    for k in ("status", "annotation", "scenarios"):
        if k in fields:
            c[k] = fields[k]
    _case_path(case_id).write_text(
        json.dumps(c, ensure_ascii=False, indent=2), encoding="utf-8")
    return c


def delete_case(case_id: str) -> bool:
    """删除案例 + 素材副本."""
    p = _case_path(case_id)
    if not p.is_file():
        return False
    c = get_case(case_id)
    p.unlink()
    if c and c.get("material_copy") and os.path.isfile(c["material_copy"]):
        # 素材副本在 cases/materials/ 内才删 (防 case JSON 被篡改后误删任意文件)
        try:
            if Path(c["material_copy"]).resolve().parent == _materials_dir().resolve():
                os.unlink(c["material_copy"])
        except OSError:
            pass
    return True


# ── 场景学习状态 ──

def scenario_stats() -> dict:
    """54 场景学习进度: 每场景案例数 + 已学场景数 (案例 ≥1 = 已学).

    ⚠️ case_total = 实际案例条数 (list_cases 长度) — 曾按归属求和 (一案例
    归属多场景重复计), 前端"案例库 N 条"显示虚高 (1 案例 8 场景曾显示 8)."""
    all_cases = list_cases()
    counts: dict[str, int] = {}
    for c in all_cases:
        for s in c.get("scenarios") or []:
            counts[s] = counts.get(s, 0) + 1
    out = {sid: {"name": info["name"], "covered": info["covered"],
                 "case_count": counts.get(sid, 0)}
           for sid, info in SCENARIOS.items()}
    learned = sum(1 for v in out.values() if v["case_count"] > 0)
    return {"total": SCENARIO_TOTAL, "learned": learned,
            "scenarios": out, "case_total": len(all_cases)}


# ── 相似案例检索 (简单可迭代: 关键词 + 场景集合, 不引入向量化) ──

# 根因同义词表 (Root Cause 同义词, ticket §2 — 匹配打分用; 可迭代扩充)
_RC_SYNONYMS = [
    ("源路由", ("源路由", "source route", "0x0b", "mtorr", "0x0c", "路由失效")),
    ("中继", ("中继", "relay", "父节点", "父链路", "下行链路")),
    ("踢出", ("踢", "deny", "白名单", "remove device", "踢出", "移除")),
    ("密钥", ("密钥", "key", "解密", "tc link")),
    ("ack", ("ack", "确认", "无响应", "无回应")),
    ("队列", ("队列", "queue", "间接", "indirect", "过期", "expir")),
    ("静默失联", ("静默", "失联", "silent", "消失", "离线")),
    ("干扰", ("干扰", "wifi", "ble", "同频", "环境", "距离")),
    ("固件", ("固件", "firmware", "不支持", "default response", "拒绝")),
    ("抓包", ("抓包", "漏帧", "盲区", "捕获率", "抓包器")),
]


def _tokens(text: str) -> set[str]:
    """轻量分词: 英文/数字词 + 中文 2-gram (关键词重叠打分用, 不引入分词库)."""
    t = (text or "").lower()
    words = set(re.findall(r"[a-z0-9]+", t))
    han = re.findall(r"[一-鿿]+", t)
    for seg in han:
        for i in range(len(seg) - 1):
            words.add(seg[i:i + 2])
        if seg:
            words.add(seg)
    return words


def find_similar(probe: dict, k: int = 5) -> list[dict]:
    """相似案例检索.

    probe: {scenarios: [...], phenomenon, root_cause, pan, device_addr}
    打分 = 场景集合 Jaccard×3 + 根因同义词命中×2 + 现象关键词重叠 (Jaccard)
    + PAN 相同×1 + 设备地址相同×1; 0 分不返回。
    """
    p_scen = set(s for s in (probe.get("scenarios") or []) if s in SCENARIOS)
    p_rc = (probe.get("root_cause") or "").lower()
    p_tok = _tokens((probe.get("phenomenon") or ""))
    scored: list[tuple[float, dict]] = []
    for c in list_cases():
        c_scen = set(c.get("scenarios") or [])
        score = 0.0
        # ① 场景集合 Jaccard
        if p_scen or c_scen:
            union = p_scen | c_scen
            inter = p_scen & c_scen
            score += 3.0 * (len(inter) / len(union) if union else 0.0)
        # ② 根因同义词命中 (probe 根因 ↔ 案例根因 同组即命中)
        c_rc = ((c.get("annotation") or {}).get("root_cause") or "").lower()
        if p_rc and c_rc:
            for _grp, syns in _RC_SYNONYMS:
                p_hit = any(s in p_rc for s in syns)
                c_hit = any(s in c_rc for s in syns)
                if p_hit and c_hit:
                    score += 2.0
                    break
        # ③ 现象关键词重叠 (token Jaccard; 双方都有内容才计)
        c_tok = _tokens((c.get("annotation") or {}).get("phenomenon") or "")
        if p_tok and c_tok:
            inter = p_tok & c_tok
            union = p_tok | c_tok
            score += (len(inter) / len(union)) if union else 0.0
        # ④ PAN / 设备地址
        if probe.get("pan") is not None and probe.get("pan") == c.get("pan"):
            score += 1.0
        if (probe.get("device_addr") is not None
                and probe.get("device_addr") == c.get("device_addr")):
            score += 1.0
        if score > 0.05:
            scored.append((round(score, 3), _case_brief(c)))
    scored.sort(key=lambda x: -x[0])
    return [dict(s, score=sc) for sc, s in scored[:k]]


def _case_brief(c: dict) -> dict:
    """案例摘要 (列表/检索输出 — 不带 evidence 大数组, 控制响应体积)."""
    ann = c.get("annotation") or {}
    return {
        "id": c.get("id"), "ts": c.get("ts"),
        "source_file": c.get("source_file"), "pan": c.get("pan"),
        "device_addr": c.get("device_addr"),
        "phenomenon": ann.get("phenomenon"), "root_cause": ann.get("root_cause"),
        "severity": ann.get("severity"), "environment": ann.get("environment"),
        "scenarios": c.get("scenarios"), "status": c.get("status"),
        "has_material": bool(c.get("material_copy")),
        "material_path": c.get("material_copy") if c.get("material_copy") else None,
    }


# ── 差距报告 (检测命中 vs 案例标注对比 → 待完善清单) ──

def gap_report() -> dict:
    """所有案例的检测 vs 标注未对齐项, 场景维度聚合 (检测器改进优先级).

    未对齐类型:
    - missed: 案例归属某场景但检测器未命中 (manual_only) → 检测器漏报线索
    - false_positive: 检测器命中但案例未归属 (自动命中不在最终 scenarios —
      人工否决了) → 检测器误报线索
    - verdict_snapshot: 命中场景的 verdict 快照 (供人工核对非 HIT 却归属)
    """
    gaps: list[dict] = []
    for c in list_cases():
        det = c.get("detection") or {}
        auto = set(det.get("auto_hits") or [])
        final = set(c.get("scenarios") or [])
        cid = c.get("id")
        src = c.get("source_file") or ""
        for s in sorted(final - auto):
            gaps.append({"case_id": cid, "source_file": src, "scenario": s,
                         "type": "missed",
                         "note": "人工归属但检测未命中 (漏报线索)"})
        for s in sorted(auto - final):
            gaps.append({"case_id": cid, "source_file": src, "scenario": s,
                         "type": "false_positive",
                         "note": "检测命中但人工未归属 (误报线索)"})
    # 场景维度聚合: 哪些场景不符最多 → 检测器改进优先级
    by_scenario: dict[str, dict] = {}
    for g in gaps:
        agg = by_scenario.setdefault(g["scenario"],
                                     {"scenario": g["scenario"],
                                      "missed": 0, "false_positive": 0})
        agg[g["type"]] += 1
    priority = sorted(by_scenario.values(),
                      key=lambda a: -(a["missed"] + a["false_positive"]))
    return {"gap_count": len(gaps), "gaps": gaps,
            "by_scenario": priority}


# ── 导出/导入传播 ──

# 案例 JSON 的密钥敏感字段 (导出前剥离; 案例本身不存密钥, 此为双保险 —
# 与 export_ai_dataset._redact 同思路)
_SENSITIVE_KEYS = {"sec_key", "aps_payload_hex", "mac_cmd_payload"}


def _sanitize(obj):
    """递归剥敏感字段 (导出安全; bytes → hex)。"""
    if isinstance(obj, dict):
        return {k: _sanitize(v) for k, v in obj.items() if k not in _SENSITIVE_KEYS}
    if isinstance(obj, list):
        return [_sanitize(x) for x in obj]
    if isinstance(obj, bytes):
        return obj.hex()
    return obj


def export_cases(out_path: str | None = None, case_ids: list[str] | None = None) -> str:
    """案例库导出为 zip: cases.json (全案例元数据) + materials/ (素材副本).

    规则不随包导出 — 检测器规则是代码, 代码随工具版本分发 (grilling 决策)。
    """
    cases = [c for c in list_cases()
             if not case_ids or c.get("id") in case_ids]
    if not out_path:
        stamp = time.strftime("%Y%m%d_%H%M%S")
        out_path = str(cases_dir() / f"case_export_{stamp}.zip")
    with zipfile.ZipFile(out_path, "w", zipfile.ZIP_DEFLATED) as zf:
        n_mat = 0
        mat_entries: list[tuple[str, str]] = []
        for c in cases:
            mc = c.get("material_copy")
            if mc and os.path.isfile(mc):
                try:
                    arc = f"materials/{c['id']}{Path(mc).suffix.lower()}"
                    zf.write(mc, arc)
                    mat_entries.append((c["id"], arc))
                    n_mat += 1
                except OSError:
                    pass
        payload = {"exported_at": time.time(),
                   "scenario_total": SCENARIO_TOTAL,
                   "case_count": len(cases),
                   "materials_included": n_mat,
                   "cases": [_sanitize(c) for c in cases]}
        zf.writestr("cases.json", json.dumps(payload, ensure_ascii=False, indent=2))
    return out_path


def import_cases(zip_path: str, merge: bool = True) -> dict:
    """导入案例 zip → 案例入库 + 素材副本恢复.

    - merge=True: 同 id 案例跳过保留本地 (场景案例同步积累);
      merge=False: 同 id 覆盖
    - 素材副本恢复到 cases/materials/ (material_copy 路径重指本地)
    """
    if not os.path.isfile(zip_path):
        raise FileNotFoundError(f"文件不存在: {zip_path}")
    added, skipped = [], []
    with zipfile.ZipFile(zip_path) as zf:
        names = zf.namelist()
        if "cases.json" not in names:
            raise ValueError("非法案例包 (缺 cases.json)")
        payload = json.loads(zf.read("cases.json").decode("utf-8"))
        mat_dir = _materials_dir()
        for c in payload.get("cases") or []:
            cid = c.get("id")
            if not cid or not re.fullmatch(r"[0-9a-f\-]+", cid):
                continue  # id 非法跳过 (防路径注入)
            existing = get_case(cid)
            if existing and merge:
                skipped.append(cid)
                continue
            # 素材副本恢复
            mat_name = f"materials/{cid}.cubx"
            c = dict(c)
            if mat_name in names:
                dst = mat_dir / f"{cid}.cubx"
                dst.write_bytes(zf.read(mat_name))
                c["material_copy"] = str(dst)
            else:
                c["material_copy"] = None
            _case_path(cid).write_text(
                json.dumps(_sanitize(c), ensure_ascii=False, indent=2),
                encoding="utf-8")
            added.append(cid)
    return {"added": added, "skipped": skipped,
            "total": len(payload.get("cases") or [])}


# ── 检测结果 → 案例字段提取 (API 层调用) ──

def extract_detection(diag_results: dict) -> dict:
    """诊断端点结果 (l1/l2/l3/l6 各 detect() 输出) → 案例检测字段.

    - scenario_hits: verdict 含 _HIT 的场景 (自动命中)
    - verdicts: {场景号: verdict} 全量快照
    """
    hits: list[str] = []
    verdicts: dict[str, str] = {}
    for key, sid in _DETECTOR_SCENARIO.items():
        r = (diag_results or {}).get(key) or {}
        v = r.get("verdict") or ""
        verdicts[sid] = v or "INCONCLUSIVE"
        if "_HIT" in v:
            hits.append(sid)
    return {"scenario_hits": hits, "verdicts": verdicts}
