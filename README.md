# Zigbee Capture Analyzer

本地 Zigbee 抓包离线分析工具：导入 .cubx / .pcap 抓包 → 自动诊断网络问题 →
拓扑 / 报文 / 节点 / AI 侧边栏多页面分析。Python 后端 + 浏览器界面，
可打包为免安装目录包分发（双击 exe 即用）。

## 功能

- **抓包导入**: .cubx（Ubiqua 原生，内嵌密钥）/ .pcap / .pcapng，多文件合并
- **大包处理**: 30MB+ 自动预扫 + 时间窗拆分导入（573 万帧 prescan 秒级）
- **协议解析**: MAC / NWK / APS / ZDO / ZCL 全层解析器（cubx 自解析 + tshark 双路径）
- **解密**: 导入 Network Key，NWK AES-CCM* 解密；解密失败原因可观测（缺 key / MIC 不匹配）
- **网络诊断**（诊断页）: 13 个场景检测器（L1 入网 / L2 在线维持 / L3 运营期 / L6 SED），
  白话结论 + 规则码 + 证据帧跳报文页；多 PAN 网络可切换诊断
- **拓扑分析**: poll / AssocResp / Route Record / 源路由四来源链路证据，
  30s 证据窗 + 时刻游标 + 聚焦链路历史
- **报文页**: 全量帧查看，字段点选过滤、未解密折叠、APS 事务链
- **节点页**: 设备身份（厂商/型号）+ 控制命令统计 + 画像导出（JSON/MD）
- **AI 侧边栏**: 知识检索（芯科官方文档库，免配置）+ 对话式范围分析（需 API key）

## 快速开始（打包分发版）

1. 解压 `ZigbeeAnalyzer-<版本>.zip` 到任意目录
2. 双击 `ZigbeeAnalyzer.exe` → 自动打开浏览器
3. 导入抓包 → 分析

> 详细使用说明见 **[DIST_README.md](DIST_README.md)**（含数据目录 / 更新 / 卸载 / 常见问题）。

## 开发运行

```bash
pip install -r requirements.txt
python -m backend                # 启动后自动打开浏览器（端口自动）
python -m backend --port 8765 --no-browser   # 指定端口/不开浏览器
```

开发模式数据目录 = 工程根（ai_config.json / logs/），与打包版隔离。

## 打包分发

```bash
python build.py                    # 版本自动（git describe + 日期）
python build.py --version 1.0.0    # 指定版本
```

产物：`dist/ZigbeeAnalyzer/`（目录包）+ `dist/ZigbeeAnalyzer-<版本>.zip`。
打包要点（见 [build.spec](build.spec)）：frontend 静态文件打进 `_internal/`；
数据分层 —— AI key 等敏感配置存 `%APPDATA%\zigbee-analyzer\`（更新覆盖不丢）；
单实例锁防双开；大包导入依赖 multiprocessing（launcher 已 freeze_support）。

## 架构

```
backend/           FastAPI 后端
  api/             端点（files 导入 / topology 拓扑 / diag 诊断 / ai / keys / ubiqua）
  detectors/       L1/L2/L3/L6 场景检测器（诊断页数据源）
  cubx_reader.py   .cubx 自解析（scapy + AES-CCM*）
  tshark.py        pcap 解析（tshark JSON 权威字段）
  route_events.py  路由事件时间线（拓扑推导）
frontend/          原生 ES6 前端（无构建工具，版本号 ?v= 缓存控制）
launcher.py        PyInstaller 入口（打包用）
build.py/spec      打包脚本
docs/              设计文档 + 场景拆解（L1-L7, 55 场景 taxonomy）
```

## 测试

```bash
# 回归套件（解析器契约/素材指纹）
python .scratch/verification/zcl_fcf_regression.py
python .scratch/verification/p1-contract/p1_regression.py
python .scratch/verification/p2_regression.py
```

## 里程碑

| 阶段 | 内容 |
|---|---|
| M1-M3 | pcap 解析 / 解密 / 拓扑 / 时间线 |
| M4 | .cubx 导入 + 打包 |
| M5 | AI 助手 |
| S0-S7 | 打包前界面稳定化（导入/诊断/拓扑/报文已闭环） |
| T2 | 主工具打包分发（目录包 + 数据分层 + 单实例） |
