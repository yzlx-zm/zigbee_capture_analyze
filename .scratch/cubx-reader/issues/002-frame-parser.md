# 7b — cubx 帧解析器 + pkt_type 判别

**要构建的内容**：`cubx_reader.py` 中 `_raw_to_dict()` + `_pkt_type()` + `_load_cubx_keys()` + `parse_cubx()`。单帧解析：Dot15d4FCS→NWK→APS→ZCL/ZDP→dict。Link Status 邻居和 Route Record relay 列表提取。

**阻塞于**：#7a (解密原语)

**需要硬件**：无

**验证方式**：
```python
from backend.cubx_reader import parse_cubx
pkts, _, _ = parse_cubx(r'C:\Users\Administrator\Desktop\test2-ubiqua-export.cubx')
assert len(pkts) == 9341  # 和 tshark 解析 test2-export.pcap 帧数一致

# 对比 pkt_type 分布
from collections import Counter
types = Counter(p['pkt_type'] for p in pkts)
print('Route Record:', types.get('Route Record',0), '(expect ~207)')
print('Link Status:', types.get('Link Status',0), '(expect ~1724)')
print('Decrypted:', sum(1 for p in pkts if p.get('decrypted')))
```

**状态**：ready

- [ ] `_load_cubx_keys(db)` — Keys 表读取 → (network_keys, link_keys)
- [ ] `_raw_to_dict(raw, id, ts, ch, lqi, rssi, nwk_keys, link_keys)` — 单帧完整解析
- [ ] MAC 层解析 (FCF, addressing mode, src/dst/pan, seq)
- [ ] NWK 层解析 (FCF, src/dst, radius, seq, security header)
- [ ] NWK 命令提取 (Link Status neighbors, Route Record relays, Route Request, Leave, etc.)
- [ ] APS 层解析 (FCF, cluster, profile, counter, src_ep, dst_ep)
- [ ] ZCL/ZDP 命令判别
- [ ] `_pkt_type(mac_ft, nwk, aps, decrypted)` — 包类型判别 (与 tshark._pkt_type 对齐)
- [ ] `parse_cubx(path)` — 顶层接口: 读文件→解析→返回(包列表, key新增, key总数)
- [ ] 对 test2.cubx 验证: 帧数/类型分布/解密数与 pcap+tshark 一致
