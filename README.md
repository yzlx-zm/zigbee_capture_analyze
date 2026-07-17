# zigbee_capture_analyze

本地 Zigbee 抓包分析工具 — Python 后端 + 浏览器界面,最终打包为单个 exe 分发。

## 功能

- **离线 pcap 分析**: 支持 802.15.4 (DLT 195) pcap/pcapng,多文件按时间自动合并
- **协议解析**: MAC / NWK / APS / ZDO / ZCL 全层手写解析器
- **组合过滤**: 地址 / 帧类型 / Cluster / 时间范围 AND/OR 组合过滤
- **解密** (M2): 导入 Network Key,NWK 层 AES-CCM* 解密查看 APS/ZCL 内容
- **拓扑分析** (M2): 从 Link Status / Mgmt_Lqi_rsp / 源路由帧构建网络拓扑 + LQI 矩阵
- **时间线** (M3): 图形化整体时序,时间切片联动过滤
- **节点视图** (M3): 独立查看单节点全部交互会话
- **AI 助手** (M5): 内嵌 AI 分析,支持配置 API Key

## 开发运行

```bash
pip install -r requirements.txt
python -m backend            # 启动后自动打开浏览器
python -m backend --port 8765 --no-browser   # 指定端口/不开浏览器
```

## 打包

```bash
build\build.bat              # 输出 dist/ZigbeeAnalyzer.exe
```

## 里程碑

| 阶段 | 内容 |
|---|---|
| M1 | pcap 解析 + 包列表 + 组合过滤 |
| M2 | Network Key 解密 + 拓扑图 + LQI 矩阵 |
| M3 | 时间线 + 单节点会话视图 |
| M4 | Ubiqua .cubx 导入 + exe 打包 |
| M5 | AI 分析助手 |
