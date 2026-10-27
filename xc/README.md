# iOS 性能数据处理工具

从 Xcode Instruments 的 `.trace` 录制包导出 XML，分析进程内存、步骤内存、卡顿记录以及 `vmstats.log`。

## 文件命名与功能

入口统一使用 `snake_case` 命名，按“动作 + 数据对象”区分职责。

| 当前文件 | 功能 | 原文件/功能来源 |
| --- | --- | --- |
| `export_activity_monitor.py` | 批量将 `.trace` 导出为进程内存 XML | `analyze-memall.py` |
| `parse_trace_xml.py` | 将原始进程 XML 转成 Excel，不需要步骤日志 | `xc.py` / `xcnolog.py` 的默认执行功能 |
| `analyze_memory.py` | 根据步骤日志生成一个用例的内存分类 Excel | `xc.py` / `xcnolog.py` 的内存分析类 |
| `summarize_memory.py` | 按录制时间汇总各 trace 的第 2 个采样点 | 同名原文件 |
| `summarize_hitches.py` | 导出卡顿 XML，合并卡顿记录到 CSV | `hitch.py` |
| `parse_vmstats.py` | 将 vmstats JSON 日志转换成分组表头 Excel | 同名原文件 |

原来的 `xc.py` 和 `xcnolog.py` 基本相同，现按功能拆分为两个入口，共享实现放在 `xctrace_tools`。旧文件名已替换，调用旧命令的外部脚本需要按上表更新。历史类名 `XCTraceXMLParser`、`MemoryAnalyse`、`MemoryAnalyseNew` 保留在 `xctrace_tools.memory` 中供 Python 调用。

## 环境与安装

- Python 3.9 或更新版本。上层 `autoTool` 项目若使用其 `pyproject.toml` 管理环境，遵循该项目的 Python 版本要求。
- Excel 导出依赖 `pandas` 和 `openpyxl`。
- 从 `.trace` 导出 XML 需要 macOS、完整 Xcode 以及可用的 `xcrun xctrace`。只处理已导出的 XML/日志时不需要调用 Xcode。

在本目录执行：

```bash
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -r requirements.txt
```

所有路径均可通过命令行传入，路径含空格或括号时使用引号。省略输入路径时沿用原脚本的个人目录默认值；在其他机器上请显式传入路径，或修改 `xctrace_tools/config.py` 中的默认配置。卡顿入口的历史默认目录是 `/Users/clover/Desktop/Basic1`。

## 输入目录约定

推荐目录结构：

```text
result1/
├── vmstats.log
└── PerformanceDynamic_demo/
    └── Traces/
        ├── PerformanceDynamic_demo-step_4-200022-20260929_200026(4s).trace/
        ├── PerformanceDynamic_demo-step_4-200022-20260929_200026(4s).xml
        └── PerformanceDynamic_demo-step_4-200022-20260929_200026(4s).log
```

扫描会递归查找文件，并跳过 `.trace` 包内部内容。内存 XML 的批量扫描匹配 `PerformanceDynamic_*.xml`，自动排除 `_hitches_summary.xml`。XML 和步骤日志必须在同一目录且同名，仅扩展名不同。

步骤日志格式：

```text
0.123456789 : [微信][打开首页]
3.0 : [微信][滑动列表]
```

时间单位为相对录制开始的秒；内部以整数纳秒处理。完整日志保留所有有效记录，并按时间排序。

## 常用流程

### 1. 导出进程内存 XML

```bash
python3 export_activity_monitor.py --result-dir "/path/to/result1"
```

每个 `.trace` 旁生成同名 `.xml`，导出 schema 为 `activity-monitor-process-live`，run 为 1。

默认跳过可解析的已有 XML；使用 `--force` 重新导出。导出最多尝试 3 次，先写入临时目录并验证 XML，再原子替换目标；失败时保留已有文件。某个 trace 失败后继续处理其余 trace，并在结束时报告成功、跳过、失败数。

默认沿用环境变量 `DEVELOPER_DIR` 或系统 Xcode 选择。需要指定 Xcode 时：

```bash
python3 export_activity_monitor.py -r "/path/to/result1" \
  --developer-dir "/Applications/Xcode.app/Contents/Developer" --force
```

### 2. 汇总第 2 个采样点

```bash
python3 summarize_memory.py --result-dir "/path/to/result1"
python3 summarize_memory.py -r "/path/to/result1" --check-only
python3 summarize_memory.py -r "/path/to/result1" -o "/path/to/reports/memory.xlsx"
```

默认输出 `result1/physical_memory_summary.xlsx`，包含：

- `trace内存汇总`：录制时间、步骤、各类内存、进程数和前台匹配状态。
- `第2采样点进程明细`：进程名、PID、类别、原始字节和 MiB。
- `分类规则`：进程映射和取样规则。
- `解析失败`：仅在有失败输入时生成，记录来源和原因。

取样及分类规则：

- 对所有 `start` 数值去重后排序，选择第 2 个时间戳的全部进程；首个时间戳必须为 0。采样不足或数据异常时记录失败。
- 仅统计 `memory-physical-footprint`；`MiB = bytes / 1048576`。
- 通过文件名 `-step_编号-开始HHMMSS-结束YYYYMMDD_HHMMSS` 提取录制开始时间，支持跨午夜，并按录制时间排序。
- 日志中选择采样时间之前或同一时刻的最后一条步骤。若采样早于首条步骤，则以首条步骤标注前台；缺少日志时标记“前台未知”。
- `APPS` 中与前台应用同名的进程归 `ForegroundAPP`，其余普通应用归 `BackgroudAPP`；`LOAD_APPS` 始终归 `BackgroudLoad`；其余进程归 `SystemService`。
- 保留历史字段拼写 `BackgroudAPP` / `BackgroudLoad`。未知或未配置前台的前台内存显示 `n.a.`，总计仍包含所有进程。
- Excel 中的 MiB、类别汇总和总计使用公式，Excel/WPS 打开时重算。`openpyxl` 不计算公式，刚生成文件的公式缓存可能为空；`--check-only` 直接校验原始数值，不依赖缓存。

### 3. 按步骤分析一个用例

每一步对应一个 XML/log 文件对时：

```bash
python3 analyze_memory.py --result-dir "/path/to/PerformanceDynamic_demo/Traces" --mode steps
```

默认输出到用例目录的 `用例名.xlsx`，sheet 为 `用例内存数据`。每个 XML 选第 2 个不同采样时间戳；每个日志必须只有一条有效步骤；步骤 ID 使用文件名中的原始编号。输入目录只能包含一个用例、一次运行，重复步骤编号会报错。

一个 XML/log 覆盖整个用例时：

```bash
python3 analyze_memory.py --result-dir "/path/to/single_case" --mode single
python3 analyze_memory.py -r "/path/to/single_case" --mode single \
  --last-step-seconds 1 -o "/path/to/reports/case.xlsx"
```

`single` 模式要求且仅允许一个同名文件对。普通步骤选择下一步开始前 1 秒处、或之前最近的采样点；最后一步默认取本步骤开始后 5 秒，可通过 `--last-step-seconds` 调整。原 `xc.py` 使用 5 秒，原 `xcnolog.py` 使用 1 秒。查询早于/晚于录制范围时分别取首/末采样点，精确命中时取该点。

此报表保留原有细分类口径：普通应用与负载应用均计入“应用内存”；自动化服务 `WebDriverAgentRunner-Runner`、`DTServiceHub` 不计入“系统服务内存”；图形、大桌面、输入法是系统服务的子集。各列以 MiB 展示，保留 1 位小数。“内核+驱动”和“预留”仍为空。这个口径与上一节四类互斥分类不同，比较报表时应注意。

### 4. 查看 XML 的原始进程明细

```bash
python3 parse_trace_xml.py "/path/to/result1"
python3 parse_trace_xml.py "/path/to/one.xml"
python3 parse_trace_xml.py "/path/to/one.xml" \
  --columns start process memory-physical-footprint memory-compressed
```

每个 XML 旁生成 `原文件名_res.xlsx`，sheet 为 `xctrace数据`，保留原始索引列。无需步骤日志。`--columns` 使用 XML schema 的 mnemonic 名称；未知列会报错。内存与时间列保留原始字节、纳秒数值。

### 5. 汇总卡顿

```bash
python3 summarize_hitches.py --result-dir "/path/to/result1" -o "/path/to/reports/hitches.csv"
python3 summarize_hitches.py -r "/path/to/result1" --export-only
```

导出 schema 为 `hitches`，XML 命名为 `原trace名_hitches_summary.xml`。支持 `--force` 和 `--developer-dir`，默认复用可解析的 XML。`--export-only` 只生成 XML，不写 CSV。

CSV 默认写到当前目录 `summary.csv`，保留原字段 `start-time`、`process`、`process_name`、`hitches_timeduration`；起始时间及耗时沿用 xctrace 的 `fmt` 显示值。无卡顿记录时生成只有表头的 CSV；部分 trace 失败时输出其余可解析记录并返回失败状态。

### 6. 转换 vmstats 日志

```bash
python3 parse_vmstats.py "/path/to/result1/vmstats.log"
python3 parse_vmstats.py "/path/to/vmstats.log" -o "/path/to/reports/vmstats.xlsx"
```

输入格式为每行一个时间戳和 JSON：

```text
[2026-09-29 20:00:00] {"sessionId":"demo","value":{"memory":{"used":123,"free":456}}}
```

默认输出同目录、同名 `.xlsx`，sheet 为 `vmstats`。嵌套字段展开为路径，列表保留为 JSON 文本；忽略顶层 `sessionId`。按所有记录的字段合集生成两行分组表头，缺失值留空，重复时间保留为独立记录。异常输入报告原日志行号，输出不允许覆盖源日志。

## 代码结构与配置

```text
xctrace_tools/
├── config.py    # 默认目录、应用/负载进程映射、分类规则、单位
├── export.py    # xctrace 命令、重试、缓存、原子替换
├── files.py     # 目录扫描、trace 包剪枝、XML/log 配对
├── logs.py      # 日志解析、纳秒时间、前台匹配
├── memory.py    # XML 转表、步骤内存统计
└── xmlio.py     # schema、行校验、链式 id/ref 解析
tests/
└── test_tools.py
```

新增或调整应用请修改 `xctrace_tools/config.py` 的 `APPS`、`LOAD_APPS`，名称按大小写精确匹配。两者合并为旧步骤分析所用的 `IOS_PACKAGES_MAP`，避免多份清单产生偏差。

共用 XML 解析支持链式引用，缺失引用、循环引用、列数不一致等异常会明确报错。导入模块不会执行扫描、写报表或修改根日志配置。需要保留历史报表时，先备份或用 `-o` 指定新路径；Excel/CSV 的同名输出会替换已有结果。

## 测试与退出状态

```bash
python3 -m unittest discover -s tests -v
```

测试使用临时目录和构造数据，覆盖采样排序、XML 引用、步骤匹配、内存分类、报表结构、导出重试及失败后保留原文件。Xcode 导出调用使用模拟实现；真实 `.trace` 的兼容性需要在装有 Xcode 的机器上用实际录制数据验证。

可对任意入口执行 `python3 文件名.py --help` 查看参数。处理成功返回 0；数据或导出失败返回非零，批处理遇到部分失败也返回非零。`argparse` 参数错误返回 2。`summarize_memory.py --check-only` 不生成文件，存在解析失败记录时仍返回 1。
