"""I 项预研对账: 轻量 PAN 提取 (只读 Raw 头) vs _raw_to_dict 权威解析 — 逐行比对.

按 DB 行逐行解析 (不依赖 parse_cubx 的过滤后顺序), 同素材逐帧比对 pan_dst/pan_src.
"""
import sys, os, sqlite3, time
sys.path.insert(0, os.path.abspath('.'))
sys.path.insert(0, os.path.join(os.path.abspath('.'), '.scratch', 'verification', 'u20-import'))
from pan_scan_probe import light_pan
from backend import cubx_reader


def main(path):
    db = sqlite3.connect(f'file:{path}?mode=ro', uri=True)
    rows = db.execute('SELECT Id, Raw, Timestamp, Channel, LQI, RSSI FROM Packets ORDER BY Id').fetchall()
    db.close()
    n = len(rows)
    mism = []
    light_pans, auth_pans = {}, {}
    t0 = time.time()
    for (pid, raw, ts, ch, lqi, rssi) in rows:
        raw = bytes(raw)
        d, s = light_pan(raw)
        p = cubx_reader._raw_to_dict(raw, int(pid), float(ts or 0), int(ch or 0),
                                     int(lqi or 0), int(rssi or 0), [], [])
        pd, ps = p.get('pan_dst'), p.get('pan_src')
        for pan in (d, s):
            if pan is not None:
                light_pans[pan] = light_pans.get(pan, 0) + 1
        for pan in (pd, ps):
            if pan is not None:
                auth_pans[pan] = auth_pans.get(pan, 0) + 1
        if d != pd or s != ps:
            if len(mism) < 8:
                mism.append(dict(id=pid, light=(d, s), auth=(pd, ps), raw=raw[:16].hex(),
                                 fcf=p.get('mac_fcf'), ft=p.get('mac_frame_type')))
    dt = time.time() - t0
    print(f'== {os.path.basename(path)}: {n} 帧, 逐行解析 {dt:.1f}s')
    print(f'   不匹配帧数: {len(mism) if len(mism)<8 else ">=8"} (样本 {len(mism)})')
    for m in mism:
        print('   ', m)
    # 全量不匹配计数 (mism 已截断 → 重扫一次计数)
    cnt = 0
    for (pid, raw, ts, ch, lqi, rssi) in rows:
        raw = bytes(raw)
        d, s = light_pan(raw)
        p = cubx_reader._raw_to_dict(raw, int(pid), float(ts or 0), int(ch or 0),
                                     int(lqi or 0), int(rssi or 0), [], [])
        if (d, s) != (p.get('pan_dst'), p.get('pan_src')):
            cnt += 1
    print(f'   不匹配合计: {cnt}/{n} ({cnt/n*100:.2f}%)')
    diff = {k: (light_pans.get(k, 0), auth_pans.get(k, 0))
            for k in set(light_pans) | set(auth_pans)
            if light_pans.get(k, 0) != auth_pans.get(k, 0)}
    print(f'   轻量分布 top8:', ', '.join(f'0x{k:04X}:{v}' for k, v in sorted(light_pans.items(), key=lambda x: -x[1])[:8]))
    print(f'   权威分布 top8:', ', '.join(f'0x{k:04X}:{v}' for k, v in sorted(auth_pans.items(), key=lambda x: -x[1])[:8]))
    print(f'   分布差异 {len(diff)} 个 PAN: ' + ', '.join(f'0x{k:04X}(轻{v[0]}/权{v[1]})' for k, v in list(diff.items())[:10]))


if __name__ == '__main__':
    for p in sys.argv[1:]:
        main(p)
