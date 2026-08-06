"""定位密钥流程 5 帧 (mac_seq 45/53/55/205/206) 在 tshark 侧的状态."""
import json
import subprocess
import sys

sys.path.insert(0, r"D:\ai_agent\zigbee_capture_analyze")
from backend import tshark  # noqa: E402

PCAP = r"C:\Users\Administrator\Desktop\zigbee_capture\验证可用-记录\1-标准入网抓包-2.pcap"
tsh_path = tshark.find_tshark()
target_seqs = {45, 53, 55, 205, 206}

for filt in ["", "zbee_nwk"]:
    cmd = [tsh_path, "-r", PCAP, "-o", "wpan.802154_fcs_ok:FALSE"]
    if filt:
        cmd += ["-Y", filt]
    cmd += ["-T", "json"]
    r = subprocess.run(cmd, capture_output=True, text=True)
    arr = json.loads(r.stdout) if r.stdout.strip() else []
    hits = []
    for tf in arr:
        layers = tf["_source"]["layers"]
        wpan = layers.get("wpan", {})
        seq_raw = wpan.get("wpan.seq_no", "")
        seq = int(seq_raw, 16) if seq_raw else None
        if seq in target_seqs:
            nwk = layers.get("zbee_nwk", {})
            aps = layers.get("zbee_aps", {})
            sec_tree = nwk.get("zbee_nwk.fcf_tree", {})
            hits.append(
                f"  seq={seq} nwk={'Y' if nwk else 'N'} aps={'Y' if aps else 'N'} "
                f"fcs_ok={wpan.get('wpan.fcs_ok')} sec={sec_tree.get('zbee_nwk.security')}"
            )
    print(f"filter={filt or '(无)'}: 总帧 {len(arr)}, 命中 {len(hits)}")
    for h in hits:
        print(h)
