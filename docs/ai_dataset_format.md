# AI 数据集导出格式（.cubx → AI-readable）

## 作用

把 Ubiqua `.cubx` 抓包转换为 AI 可直接消费的时序 + 节点交互数据。
解析复用 `backend/cubx_reader.py`（MAC/NWK/APS/ZCL 分层解析 + AES 解密），
导出层由 `scripts/export_ai_dataset.py` 完成。

## 用法

```bash
python scripts/export_ai_dataset.py "抓包文件.cubx" [--out 输出目录] [--target-pan 580C]
```

- 默认输出到 `exports/ai/<抓包名>_ai/`。
- 不指定 `--target-pan` 时，自动选择解密帧最多的 PAN。
- 解析用的密钥副本放在输出目录 `.keys/`，导出完成后自动删除。

## 输出文件

| 文件 | 内容 |
|---|---|
| `metadata.json` | 帧数、时长、PAN 统计、解密情况、密钥数量（不含密钥值） |
| `packets.jsonl` | 每帧完整解析字段，密钥值已脱敏 |
| `packets.csv` | Wireshark 风格 CSV：时间戳、MAC/NWK 地址、协议、帧类型、NWK/APS Frame Control、长度、Channel 等全部列 |
| `events.jsonl` | 紧凑语义事件，每帧一行，全 PAN |
| `events_target.jsonl` | 同上，只保留目标 PAN |
| `packets_target.csv` | 目标 PAN 的 Wireshark 风格 CSV |
| `interactions.json` | 按 `(PAN, 短地址)` 隔离的节点、EUI64 映射、按 `(PAN, 源, 目标)` 的交互边 |
| `timeline.md` | 全 PAN 时间线（相对毫秒 + 摘要） |
| `timeline_target.md` | 目标 PAN 时间线 |
| `digest.md` | 推荐 AI 直接阅读的摘要：节点表、交互表、关键时序事件 |

## 关键设计

- **时序**：每帧保留原始 `ts` 和相对 `dt_ms`，时间线按包序排列，APS Ack 通过 `ack_peer_seq` 回链到被确认帧。
- **节点交互**：短地址只在单个 PAN 内有效，因此节点/边都带 PAN 维度，避免不同网络地址复用互相污染；`eui_mappings` 记录 EUI64 ↔ 短地址 ↔ PAN 的历史映射（含入网/重入网导致的地址变化）。
- **解密**：`.cubx` 内嵌密钥 + 本机 `%APPDATA%\Wireshark\zigbee_pc_keys` 都会尝试；导出只写 `decrypted`、`sec_key_label`、`sec_key_type`，不导出密钥值，TransportKey/RequestKey/VerifyKey 载荷也会被移除。
- **未解密帧**：`sec.decrypted=false` 且 `sec.note=mic_fail/missing_key/parse_error`，时间线里标注 `Encrypted(...)`，不会被误当成功解密。
