"""构造"单 PAN + >1MB"合成素材 (U20-I 面板分支验证用).

真实单 PAN 素材 (水沁传感器问题入网.cubx, 435 帧 / 0.4MB) 小于前端预扫面板阈值
(>1MB), 无法触发面板 → 复制 Packets 行 13 份 (时间戳各 +1 分钟) 使其 >1MB,
用于验证"单 PAN 素材面板不显示选择器"分支。合成件仅为 UI 分支测试用, 不入库。
"""
from __future__ import annotations

import glob
import os
import shutil
import sqlite3

BASE = r"C:\Users\Administrator\Desktop\zigbee_capture"
DST = r"D:\tmp\u20\one_pan_big.cubx"

src = None
for p in glob.glob(os.path.join(BASE, "**", "*.cubx"), recursive=True):
    name = os.path.basename(p)
    if name.startswith("\u6c34\u6c81") and "\u5165\u7f51" in name:   # 水沁…入网
        src = p
        break
if src is None:
    raise SystemExit("未找到水沁传感器入网素材")
shutil.copy(src, DST)
db = sqlite3.connect(DST)
rows = db.execute("SELECT Id, Raw, Stack, Channel, Timestamp, TimeDelta, LQI, RSSI, Comment"
                  " FROM Packets ORDER BY Id").fetchall()
base_id = rows[0][0]
max_id = max(r[0] for r in rows)
n = 0
for k in range(1, 31):
    for r in rows:
        db.execute("INSERT INTO Packets (Id, Raw, Stack, Channel, Timestamp, TimeDelta,"
                   " LQI, RSSI, Comment) VALUES (?,?,?,?,?,?,?,?,?)",
                   (max_id + (k - 1) * len(rows) + (r[0] - base_id) + 1, r[1], r[2], r[3],
                    r[4] + k * 60, r[5], r[6], r[7], r[8]))
        n += 1
db.execute("UPDATE sqlite_sequence SET seq=(SELECT MAX(Id) FROM Packets) WHERE name='Packets'")
db.commit()
total = db.execute("SELECT COUNT(*) FROM Packets").fetchone()[0]
db.close()
print(f"源: {os.path.basename(src)} → {DST}")
print(f"新增 {n} 行 / 合计 {total} 帧 / {os.path.getsize(DST)/1048576:.2f} MB")
