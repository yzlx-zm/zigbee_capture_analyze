# 7a — AES-CCM* 解密原语 (参考 akubela)

**要构建的内容**：`cubx_reader.py` 中的密码学基础函数。移植 akubela `_capture_probe.py` 的解密逻辑：`_zigbee_hash()` (AES-MMO), `_zigbee_key_hash()` (keyed hash for transport/load keys), `_decrypt_nwk()`, `_decrypt_aps()`, `_security_candidates()`。

**阻塞于**：无——可立即开始

**需要硬件**：无

**验证方式**：
```python
from backend.cubx_reader import _zigbee_hash, _zigbee_key_hash
# 用 Zigbee spec 已知测试向量验证
# 用 test2.cubx 的 key 解密已知帧, 和 tshark 结果对比
```

**状态**：ready

- [ ] `_zigbee_hash(value: bytes) -> bytes` — AES-MMO (spec B.1.3/B.6)
- [ ] `_zigbee_key_hash(key, selector) -> bytes` — keyed hash (transport=0x00, load=0x02)
- [ ] `_security_candidates(key_type, nwk_keys, link_keys)` — key selection
- [ ] `_decrypt_security_blob(prefix, sec_bytes, ...)` — ENC-MIC-32 解密核心
- [ ] `_decrypt_nwk(nwk, nwk_keys)` — NWK 层解密
- [ ] `_decrypt_aps(aps, nwk_keys, link_keys)` — APS 层解密 (含 link key 派生)
- [ ] 用 test2.cubx 验证: 密钥匹配, 解密成功
