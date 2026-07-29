# Zigbee 解密管线 — 方案与验证

## 概述

Zigbee 抓包文件（pcap）中的数据帧（Data Frame）默认经过 NWK 层 AES-128-CCM* 加密。
要解析 APS/ZCL 内容，必须在 tshark 中加载正确的 Network Key。

本文档记录了已验证的解密方案、密钥配置流程，以及工具集成架构。

---

## 核心难题：为什么不自己实现解密

Zigbee NWK 层使用 **AES-CCM\*** 加密（IEEE 802.15.4 定义）。
- 标准库 `cryptography.hazmat.primitives.ciphers.aead.AESCCM` 只支持标准 CCM，不完全兼容 CCM\*
- CCM\* 支持加密-only / 认证-only 模式，标准 CCM 不支持
- 自行实现需要手动 AES-CTR + CBC-MAC（~200 行），调试周期长、风险高

**结论：借助 tshark 的解密引擎，零代码成本获取解密数据。**

---

## 已确认的关键参数（2026-07-22 验证）

| 参数 | 值 | 来源 |
|------|-----|------|
| 安全等级 | AES-128 + 32-bit MIC（Level 5） | Ubiqua 截图确认 |
| NWK Key 数量 | 57 个（测试环境历史密钥） | Ubiqua 导出 |
| 有效 Key | **Key2**: `FF:21:4D:7A:31:ED:4B:76:55:03:CC:9D:B1:2D:A6:2B` | Wireshark GUI 帧 302 验证 |
| TC Link Key | `5A:69:67:42:65:65:41:6C:6C:69:61:6E:63:65:30:39`（ZigBeeAlliance09） | Zigbee 规范默认 |
| 测试文件 | `test2-export.pcap`（13245 帧，PAN 0xFEED） | Ubiqua 导出 |

### 验证结果（帧 302）

```
帧 302 — Wireshark GUI 和 tshark 结果一致：

NWK Layer:
   Frame Control: 0x0208 (Data, Security)
   Source: 0x0000, Destination: 0x2bd6
   Security: Key Id=Network Key, Extended Nonce, Key Seq=0
   [Key: ff214d7a31ed4b765503cc9db12da62b]  ← Key2 命中

APS Layer:
   Frame Control: 0x40 (Data)
   Cluster: 0x0019 (OTA Upgrade)
   Profile: 0x0104 (Home Automation)
   Endpoint: 1 → 1, Counter: 178

ZCL Layer:
   Frame Type: Cluster-specific (0x01)
   Direction: Server → Client
   Command: Query Next Image Response (0x02)
   Status: Ota No Image Available (0x98)
```

**解密统计（全量 13245 帧）：**

| 解密帧数 | Cluster | 说明 |
|----------|---------|------|
| 378 | 0x0000 Basic | 设备基础属性读写 |
| 316 | 0x0019 OTA Upgrade | 固件升级查询 |
| 69 | 0xFCFA Private Cluster | 私有扩展 Cluster |
| ~319 | (空) | NWK 命令帧（Link Status/Route Request 等，无需解密）|

---

## 工程师完整工作流

```
┌──────────────┐     ┌──────────────────┐     ┌─────────────────┐
│ 1. Ubiqua    │────→│ 2. File → Export │────→│ 3. 我们的工具    │
│ 抓包 + 解密   │     │    保存为 pcap    │     │ 导入 + 分析      │
└──────────────┘     └──────────────────┘     └─────────────────┘
                                                      │
                           ┌──────────────────────────┘
                           │
                    ┌──────▼──────┐
                    │ 4. tshark    │
                    │ JSON 全解析  │
                    │ MAC/NWK/APS  │
                    │ /ZCL 四层    │
                    └──────────────┘
```

### 步骤 1: Ubiqua 抓包

- 硬件：CC2531 USB Dongle（或兼容 sniffer）
- 信道：与目标网关一致（常用 Ch.20 2.450GHz）
- 密钥：在 Ubiqua 中配置 `Tools → Options → Security → Network Key`

### 步骤 2: 导出 pcap

- Ubiqua → File → Export → 选择 pcap 格式
- 注意：Ubiqua 导出的 pcap **携带原始加密数据**，KEY 不嵌入文件
- 文件大小参考：~1MB / 每分钟（滚动分片）

### 步骤 3: 导入工具

- 工具端不需要了解密钥，直接导入 pcap
- `POST /api/import/pcap` → tshark 批量 JSON 解析 → 内存存储

### 步骤 4: tshark 解密

- tshark 读取 `zigbee_pc_keys` 文件中的 Network Key 列表
- 对每帧尝试所有 Key，找到匹配的自动解密
- 输出 JSON：每帧包含 `frame` / `wpan` / `zbee_nwk` / `zbee_aps` / `zbee_zcl` 五层

---

## zigbee_pc_keys 配置

### 文件位置

```
Windows: %APPDATA%\Wireshark\zigbee_pc_keys
```

### 文件格式

```csv
"<32位hex密钥>","<Normal|Reverse>","<标签>"
```

每行一个 Key，3 个字段（CSV 格式，用逗号分隔，**不带空格**）：

```
"FC90D2638CF7E1C27309CECBD4116F9D","Normal","Key0"
"E265F2835FC046023DD4BE14C2409CB9","Normal","Key1"
"FF214D7A31ED4B765503CC9DB12DA62B","Normal","Key2"
"579B5DFD78737A8BA9B5B48DE9A1FFE8","Normal","Key3"
"A744D01B3DC7E1A51F7B4DA0666FB369","Normal","Key4"
"266536B373A010302226CE5EF9BA0554","Normal","Key5"
...
```

**格式要求：**
- 字段 1：16 字节密钥的 32 位 hex 字符串，**无分隔符**，用双引号包裹
- 字段 2：`Normal` 或 `Reverse`（字节序）
- 字段 3：任意标签（用于调试，Wireshark 中显示为 `[Key Label: xxx]`）
- **注意**：NOT 空格分隔、NOT 冒号分隔、NOT 不带引号

### 验证密钥是否生效

```bash
# 查看帧 302 的解密结果
tshark -r test2.pcap -Y "frame.number == 302" -T json | python -c "
import sys,json
data=json.loads(sys.stdin.read())
layers=data[0]['_source']['layers']
print('APS' if 'zbee_aps' in layers else 'NO APS')
print(layers.get('zbee_aps',{}).get('zbee_aps.cluster','N/A'))
"

# 统计解密帧数
tshark -r test2.pcap -Y "zbee_aps" -T fields -e frame.number | wc -l
```

---

## 已验证的 tshark 命令

### 基础解密查询

```bash
# 导出单帧完整 JSON（含所有协议层）
tshark -r <pcap文件> -Y "frame.number == N" -T json

# 查询 APS 层字段
tshark -r <pcap文件> -Y "zbee_aps" -T fields \
  -e frame.number -e zbee_nwk.security \
  -e zbee_aps.cluster -e zbee_aps.counter -e zbee_zcl.cmd.id

# 统计 Cluster 分布
tshark -r <pcap文件> -Y "zbee_aps" -T fields -e zbee_aps.cluster | sort | uniq -c | sort -rn
```

### 可用的 zbee 字段（关键）

| 层 | 关键字段 |
|----|---------|
| MAC | `wpan.src16`, `wpan.dst16`, `wpan.fcf`, `wpan.seq_no` |
| NWK | `zbee_nwk.src`, `zbee_nwk.dst`, `zbee_nwk.security`, `zbee_nwk.src64`, `zbee_nwk.radius` |
| 安全 | `zbee.sec.counter`, `zbee.sec.key`, `zbee.sec.mic`, `zbee.sec.decryption_key` |
| APS | `zbee_aps.cluster`, `zbee_aps.profile`, `zbee_aps.counter`, `zbee_aps.src`, `zbee_aps.dst` |
| ZCL | `zbee_zcl.cmd.id`, `zbee_zcl.cmd.tsn`, ZCL payload fields |

---

## 常见问题排查

### Q: tshark 不返回 APS 数据（或 NWK 层完全没有）

**第 0 步（最易被忽略）：检查 FCS。** 某些抓包工具导出的 pcap，每帧 FCS 字段是占位值 `0xffff`（Bad FCS）。tshark 默认偏好 `wpan.802154_fcs_ok: TRUE`——**FCS 校验不过就跳过 NWK 解析**，导致所有帧只显示 `wpan:data`，连 `zbee_nwk` 层都不出现，此时再多 key 也没用。

诊断：
```bash
# 看帧的协议栈里有没有 zbee_nwk
tshark -r <pcap> -T fields -e frame.number -e frame.protocols | head
# 若全是 "wpan:data" 而无 "wpan:zbee_nwk:..." → FCS 问题
# 确认: -V 看单帧, "Bad FCS" + "Security Enabled: False" 但实际是加密帧
tshark -r <pcap> -V -c 1 | grep -i "fcs\|protocols"
```

修复：给所有 tshark 调用加 `-o "wpan.802154_fcs_ok:FALSE"`。**本项目有两个地方调用 tshark，都要加**：
- `backend/tshark.py`（主解析 + relay 提取，2 处）
- `backend/verify.py`（基准校验，9 处）——漏改这里会导致 verify 全红、拓扑/时间线被锁

> ⚠️ Wireshark **GUI** 默认不卡 FCS，所以"GUI 能显示但 tshark 不能"是 FCS 问题的典型症状。

1. 检查 `zigbee_pc_keys` 格式 — **必须**是 `"hex","Normal","label"`（引号 hex，无分隔符）
2. 确认文件在 `%APPDATA%/Wireshark/` 目录下
3. 用 Wireshark GUI 打开同一个 pcap 验证 Key 是否有效
4. 在 Wireshark GUI 中查看 `[Key: xxx]` 和 `[Key Label: xxx]` 确认 Key 被匹配

### Q: 部分帧能解密，部分不能
- 多 PAN 场景：不同 PAN 可能使用不同的 Key
- Key 轮换：测试环境中 Key 可能随时间变化 — 需要导入所有历史 Key
- 帧类型：Link Status / Route Request 等 NWK 命令帧不需要解密，APS 层为空

### Q: Wireshark GUI 能解密但 tshark 不能
- tshark 版本问题：2026-07-22 在 tshark 4.6.2 上验证通过
- `-o` 参数格式在 Windows 上容易出错，建议使用文件方式配置 Key

---

## 集成到工具

### 后端设计要点

```python
# 1. 导入 pcap 时写入密钥文件
def write_keys_to_wireshark(keys: list[str], labels: list[str]):
    """将 Network Key 列表写入 zigbee_pc_keys"""
    config_dir = os.path.expandvars(r"%APPDATA%\Wireshark")
    key_file = os.path.join(config_dir, "zigbee_pc_keys")
    with open(key_file, "w") as f:
        for key_hex, label in zip(keys, labels):
            # 去掉冒号，保持 32 位 hex
            clean = key_hex.replace(":", "").replace(" ", "").upper()
            f.write(f'"{clean}","Normal","{label}"\n')

# 2. 调用 tshark 批量解析
def parse_pcap(pcap_path: str) -> list[dict]:
    """tshark JSON 解析, 返回包列表"""
    result = subprocess.run([
        "tshark", "-r", pcap_path,
        "-Y", "zbee_nwk",   # 只取 Zigbee NWK 帧
        "-T", "json"
    ], capture_output=True, text=True)
    return json.loads(result.stdout)
```

### API 设计

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/import/pcap` | POST | 上传 pcap 文件，写入 Key → tshark 解析 → 存储 |
| `/api/keys` | GET | 查看当前已配置的 Key 列表 |
| `/api/keys` | POST | 添加/更新 Key（写入 zigbee_pc_keys） |
| `/api/packets/{id}` | GET | 返回单帧完整协议树 JSON（含 MAC/NWK/APS/ZCL 所有字段） |
| `/api/packets/{id}/raw` | GET | 返回单帧原始 hex 字节 |

### 前端交互

```
[密钥管理页]
  ┌─ 已配置 Key 列表 ─────────────────┐
  │ Key0: FC90D2...  [状态: 未命中]    │
  │ Key2: FF214D...  [状态: ✓ 命中]    │  ← 绿色 = 有帧成功解密
  │ Key3: 579B5D...  [状态: 未命中]    │
  │ [+ 添加 Key] [从 Ubiqua 导入]      │
  └───────────────────────────────────┘
```

---

## 依赖记录

| 组件 | 版本 | 路径/安装 |
|------|------|----------|
| tshark | 4.6.2 | `D:\work_tool\Wireshark\tshark.exe` |
| Wireshark GUI | 4.6.2 | `D:\work_tool\Wireshark\Wireshark.exe` |
| Python | 3.13 | 系统 PATH |
| cryptography | latest | `pip install cryptography`（仅用于验证，生产用 tshark） |
