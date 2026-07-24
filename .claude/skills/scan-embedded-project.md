# 扫描嵌入式工程

深度扫描嵌入式工程的源码树，生成 `PROJECT-KNOWLEDGE-GRAPH.md`（项目知识图谱）文件到仓库根目录。

这是**深度扫描**——每个维度每次都完整执行。输出是所有其他技能（需求锐化、术语定义、硬件调试、代码审查、深度文档）的单一事实来源。

## 扫描维度

### 1. 构建系统

识别主构建系统并提取：

- **类型**：CMake / Make / IAR (.ewp) / Keil (.uvprojx) / SCons / Meson / Bazel / PlatformIO / shell 脚本
- **入口点**：顶层构建文件路径
- **编译器**：GCC / ARMClang / IAR ICC / MSVC — 版本、目标三元组（如 `arm-none-eabi-`）
- **链接脚本**：`.ld` 或 `.icf` 文件路径
- **构建变体**：debug / release / production — 差异（优化级别、宏定义）
- **关键宏定义**：`-D` 标志和配置头文件中的 `#define`，尤其是平台选择宏（`CONFIG_PLATFORM_*`、`BOARD_*`）

查找这些文件：`CMakeLists.txt`、`Makefile`、`*.ewp`、`*.uvprojx`、`build.gradle`、`platformio.ini`、`Kconfig`、`defconfig`、`prj.conf`

### 2. MCU / SoC 架构

找到目标芯片并提取：

- **MCU 系列**：如 EFR32MG21、STM32F407、nRF52840、ESP32-C6、TLSR8258
- **CPU 内核**：Cortex-M0+/M3/M4/M33/M7/M55、RISC-V RV32IMC、Xtensa LX7 等
- **最高主频**：从数据手册或时钟配置中获取
- **Flash 大小 / RAM 大小**：从链接脚本或芯片头文件中获取
- **关键硬件特性**：FPU（单/双精度）、MPU/MMU、DSP 扩展、TrustZone、加密加速器
- **芯片版本 / errata 参考**（如果代码库中存在）

查找这些文件：`startup_*.s`、`startup_*.c`、`system_*.c`、芯片头文件（`stm32f4xx.h`、`em_device.h`）、`sdk_config.h`、链接脚本中的 `MEMORY` 块

### 3. RTOS 配置

如果存在 RTOS，提取：

- **类型**：FreeRTOS / Zephyr / ThreadX / μC/OS / RT-Thread / 裸机
- **版本**：从 `FreeRTOS.h`、`zephyr/version.h` 等获取
- **关键配置**：tick 频率、最大优先级、栈大小、堆策略、空闲钩子
- **任务清单**：任务名、优先级、栈大小（从 `xTaskCreate` 调用或 `.conf` 文件中获取）
- **使用的 IPC 机制**：队列、信号量、互斥锁、事件组、消息缓冲区
- **内存管理**：heap_N.c 变体、静态 vs 动态分配的偏好

查找这些文件：`FreeRTOSConfig.h`、`prj.conf`、`Kconfig`、`syscfg`、任务创建调用

### 4. 外设清单

枚举工程使用的每个外设。对每个外设记录：

| 字段 | 示例 |
|------|------|
| 外设 | USART1 |
| 功能 | NCP 主机通信 |
| 基地址 | 0x40011000 |
| IRQ 号 | 37 |
| DMA 通道 | TX: DMA1_Ch4, RX: DMA1_Ch5 |
| 引脚映射 | TX=PA9(AF7), RX=PA10(AF7), CTS=PA11, RTS=PA12 |
| 时钟源 | PCLK2 (APB2) |
| 配置文件 | `src/hal/uart_config.c` |

同时注意：
- **共享总线**：哪些外设共享同一 I2C/SPI 总线 → 潜在竞争
- **未使用的外设**：启动代码中初始化但从未引用的外设
- **GPIO 清单**：每个 `gpio_set`、`GPIO_PinConfig`、`nrf_gpio_cfg` 调用按端口分组

查找这些文件：HAL 初始化调用、外设句柄声明、引脚配置数组、Device Tree 节点（Zephyr/Linux）、`board.c`/`board.h`

### 5. 中断向量表

提取完整的中断配置：

- **向量表位置**：从启动文件或链接脚本中获取
- **直接 ISR**：向量表中列出的函数
- **间接处理函数**：运行时通过 HAL 回调注册的 ISR
- **优先级分配**：每个已启用 IRQ 的 NVIC 优先级
- **嵌套关系**：哪些 ISR 可以抢占哪些其他 ISR（根据优先级级别）
- **共享中断线**：EXTI 线、GPIO 端口——哪些源共享同一条 IRQ
- **故障处理函数**：HardFault / MemManage / BusFault / UsageFault — 是否已定义？

查找这些文件：`startup_*.s` 中的向量表、`NVIC_SetPriority()`、`__NVIC_EnableIRQ()`、`irq_enable()`

### 6. 内存布局

重构内存映射：

- **Flash 布局**：bootloader / app / storage / OTA 镜像槽 — 大小和基地址
- **RAM 布局**：.data / .bss / heap / stack / noinit — 大小和边界
- **特殊段**：校准数据、序列号、密钥、NVRAM
- **栈位置**：MSP vs PSP，栈底/栈顶，保护区域
- **堆配置**：`configTOTAL_HEAP_SIZE`（FreeRTOS）或 `malloc` 堆大小
- **外部存储器**：外部 Flash（QSPI）、外部 RAM、EEPROM — 如果存在

查找这些文件：`.ld` 链接脚本、`.icf` IAR 链接配置、`partitions.csv`/`pm.yml`（Zephyr）、flash map 头文件

### 7. 协议栈

对于无线/有线协议栈：

- **协议**：Zigbee（EmberZNet / ZBOSS / Z-Stack）、BLE（SoftDevice / NimBLE / Zephyr BT）、Thread（OpenThread）、Matter、LoRaWAN、CAN、Modbus、自定义 RF
- **协议栈版本**：SDK 版本、协议规范版本
- **协议栈层集成**：哪些层在哪里运行（host vs NCP vs SoC 模式）
- **配置**：网络参数、安全密钥、发射功率、信道掩码
- **回调和钩子**：协议栈与应用的集成接口
- **缓冲区模型**：协议栈如何管理数据包缓冲区、池大小、与应用共享

查找这些文件：`stack/`、`protocol/`、`zb_*.h`、`ble_*.h`、`app_ble.cfg`、SDK 配置头文件

### 8. 模块依赖图

映射软件架构：

- **顶层模块**：列出 `src/`、`app/`、`lib/` 下的每个目录及其声明用途
- **依赖方向**：哪些模块 `#include` 了哪些其他模块
- **循环依赖**：检测任何 `A → B → A` 路径
- **HAL 接口**：硬件相关代码和硬件无关代码之间的边界
- **第三方组件**：库、中间件、厂商 SDK 代码 — 带版本号

生成文本树形图：

```
src/
├── hal/          ← 硬件抽象（依赖：厂商 SDK）
├── driver/       ← 设备驱动（依赖：hal/）
├── protocol/     ← 无线协议栈集成（依赖：hal/, driver/）
├── app/          ← 应用逻辑（依赖：protocol/, driver/）
└── util/         ← 共享工具（依赖：无）
```

### 9. 已有文档

清点已存在的文档：

- `CONTEXT.md`、`CLAUDE.md`、`README.md`
- `docs/` 目录内容
- 架构图
- 注释中引用的数据手册/参考手册
- 已有的 ADR 目录

## 输出

将 `PROJECT-KNOWLEDGE-GRAPH.md` 写入仓库根目录，结构如下：

```markdown
# 项目知识图谱：<项目名>

> 由 scan-embedded-project 自动生成。上次扫描：<日期>

## 1. 构建系统
## 2. MCU / SoC 架构
## 3. RTOS 配置
## 4. 外设清单
## 5. 中断向量表
## 6. 内存布局
## 7. 协议栈
## 8. 模块依赖图
## 9. 已有文档
```

每个章节包含表格和结构化列表中的提取数据——不要写成散文，不要推测。如果某个维度确实没有内容（如裸机系统无 RTOS），写"无 —— 裸机系统"，而不是省略该章节。

## 重新扫描

此技能是幂等的——再次运行会用新的扫描结果覆盖 `PROJECT-KNOWLEDGE-GRAPH.md`。始终从源码树的当前状态扫描；永远不要与之前的图谱合并或做差异对比。
