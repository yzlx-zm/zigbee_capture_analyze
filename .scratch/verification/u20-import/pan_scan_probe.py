"""I 项预研: 轻量 PAN 提取 (只读 Raw 头, 不跑协议栈) — v2 对齐权威语义."""


def light_pan(raw):
    """Raw 头 → (dst_pan, src_pan); 语义对齐 cubx_reader._raw_to_dict.

    - 保留帧类型 4-7 (reserved) / 2 (ACK) → 无寻址字段 (scapy 解析为 Raw / 无地址)
    - 尾部 2 字节 FCS 不计入寻址 (Dot15d4FCS)
    - 寻址块长度不足 → 无法判定 (None), 不越界臆测
    - pan_src 兜底 = pan_dst (对齐 cubx_reader.py:520 `src_panid or dest_panid`)
    """
    if not raw or len(raw) < 5:
        return None, None
    fcf = raw[0] | (raw[1] << 8)
    ftype = fcf & 0x07
    if ftype >= 4 or ftype == 2:
        return None, None
    if (fcf >> 10) & 3 == 1 or (fcf >> 14) & 3 == 1:
        return None, None   # 保留寻址模式 (scapy 无法寻址)
    pan_comp = (fcf >> 6) & 1
    dst_mode = (fcf >> 10) & 0x03
    src_mode = (fcf >> 14) & 0x03
    body = len(raw) - 2          # 扣 FCS
    off = 3                      # FCF(2) + seq(1)
    dst_pan = src_pan = None
    if ftype == 0:               # Beacon: 仅 SrcPAN + SrcAddr (规范无 dst 地址)
        if src_mode == 0 or dst_mode != 0:
            return None, None
        if body < off + 2 + (8 if src_mode == 3 else 2):
            return None, None
        src_pan = raw[off] | (raw[off + 1] << 8)
        return None, src_pan
    if dst_mode:
        if body < off + 2 + (8 if dst_mode == 3 else 2):
            return None, None
        dst_pan = raw[off] | (raw[off + 1] << 8)
        off += 2 + (8 if dst_mode == 3 else 2)
    if src_mode:
        if pan_comp and dst_mode:
            src_pan = dst_pan
        elif body >= off + 2:
            src_pan = raw[off] | (raw[off + 1] << 8)
        else:
            return None, None
    if src_pan is None:
        src_pan = dst_pan
    return dst_pan, src_pan
