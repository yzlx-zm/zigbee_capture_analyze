# 深探针: 解析 Basic cluster Read Attr Req/Rsp 的属性 ID 和值 (manu_name/model_id 载体)
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.path.insert(0, '.')
from backend.cubx_reader import parse_cubx

path = r"C:/Users/Administrator/Desktop/zigbee_capture/设备控制分析-训练素材/需求32533_simon_dimmer_涂鸦入网_ce5b.cubx"
ret = parse_cubx(path)
pkts = []
def flat(x):
    if isinstance(x, dict): pkts.append(x)
    elif isinstance(x, (list, tuple)):
        for i in x: flat(i)
flat(ret)

ATTR = {0x0000:'ZCL Version',0x0004:'ManufacturerName',0x0005:'ModelIdentifier',0x0007:'PowerSource'}
TYPE = {0x42:'str',0x20:'u8',0x21:'u16',0x10:'bool'}

def locate_zcl(p):
    # 复用 cubx_reader 的偏移逻辑
    plain = p.get('aps_plain')
    sec = p.get('decrypted')  # 加密帧?
    if not plain: return None
    base = 6 if p.get('_has_sec_hdr') else 0
    return base

def zcl_off_from(p):
    plain = p.get('aps_plain')
    # 从结果字段推断: 若有 zcl_seq 且知道它的位置不可直接得; 用保守法: fcf 定位
    # 加密帧 aps_plain 从 profile 起 → ZCL 头偏移 6; 非加密偏移 0
    base = 6 if p.get('_has_sec_hdr') else 0
    return base

cnt = 0
for p in pkts:
    if p.get('aps_cluster') != 0x0000: continue
    cid = p.get('zcl_cmd_id')
    if cid not in (0x00, 0x01): continue
    plain = p.get('aps_plain')
    if not isinstance(plain, (bytes, bytearray)): continue
    # 找 ZCL 头: 加密帧偏移 6; 无 sec 头偏移 0 (与 reader 逻辑一致)
    base = 6 if p.get('_has_sec_hdr') else 0
    if len(plain) < base + 4: continue
    fcf = plain[base]
    off = base + 1
    if fcf & 0x04: off += 2
    if len(plain) < off + 2: continue
    payload = plain[off + 2:]
    if cid == 0x00:  # Read Attr Req: [attr_id:2] xN
        ids = []
        for i in range(0, len(payload) - 1, 2):
            a = int.from_bytes(payload[i:i+2], 'little')
            ids.append(f"{a:04X}" + (f"({ATTR.get(a,'')})" if a in ATTR else ""))
        if ids:
            cnt += 1
            if cnt <= 8: print(f"[Req] src={p.get('nwk_src')} ep={p.get('aps_src_ep')} attrs={ids}")
    elif cid == 0x01:  # Read Attr Rsp: [attr_id:2][status:1][type:1][value..]
        i = 0; out = []
        while i + 4 <= len(payload):
            a = int.from_bytes(payload[i:i+2], 'little')
            st = payload[i+2]
            if st != 0:  # 0x00 SUCCESS
                out.append(f"{a:04X}=status{st}")
                i += 3
                continue
            ty = payload[i+3]
            i += 4
            if ty == 0x42:  # string
                ln = payload[i]; val = payload[i+1:i+1+ln]
                try: vtxt = val.decode('utf-8', errors='replace')
                except: vtxt = repr(val)
                out.append(f"{a:04X}({ATTR.get(a,'?')})={vtxt}")
                i += 1 + ln
            elif ty in (0x20, 0x10):
                out.append(f"{a:04X}({ATTR.get(a,'?')})={payload[i]}")
                i += 1
            elif ty == 0x21:
                out.append(f"{a:04X}({ATTR.get(a,'?')})={int.from_bytes(payload[i:i+2],'little')}")
                i += 2
            else:
                out.append(f"{a:04X}({ATTR.get(a,'?')})ty{ty:02X}")
                i += 2
        if out:
            print(f"[Rsp] src={p.get('nwk_src')} ep={p.get('aps_src_ep')} -> {out}")
print("\ndone")
