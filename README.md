# autoTool
鸿蒙/iOS 性能内存数据采集与解析工具集。

## 目录结构

- `/mem`：采集 footprint 和 zprint（以及 vmstat、sysctl）的 shell 脚本
- `/openharmony`：解析 openharmony 内核及驱动的脚本
- `/xc`：解析非越狱手机 Instrument 采集到的 trace，内存大小（beta）
- 根目录：iOS 内存数据解析脚本集合

## 环境要求

```bash
pip install openpyxl pandas
```

---

## iOS 内存解析工具

### 1. arse_zprint.py
**功能**：解析 iOS zprint 内存数据，计算内核和驱动占用

**输入**：
- 目录中的 `zprint_*` 文件（无扩展名）
- 修改脚本中的 `BASE_DIR` 变量指定文件目录

**输出**：
- `ios_zprint.xlsx`：包含内核占用、驱动占用及详细内存分类

**计算公式**：
- 内核占用 = (wired memory 中的所有 VM_KERN_* + zones) - VM_KERN_COUNT_BOOT_STOLEN + VM_KERN_COUNT_WIRED_残余
- 驱动占用 = sum(wired memory 中的 com.apple.*) - com.apple.iokit.IOSurface - com.apple.filesystems.apfs

**使用**：
```bash
python arse_zprint.py
```

---

### 2. arse_vmstat.py
**功能**：解析 vmstat 虚拟内存统计数据

**输入**：
- 目录中的 `vmstatlog_*` 文件
- 修改脚本中的 `BASE_DIR` 变量

**输出**：
- `vmstat.xlsx`：包含所有虚拟内存统计字段（Pages free、Translation faults 等）

**使用**：
```bash
python arse_vmstat.py
```

---

### 3. arse_sysctl.py
**功能**：解析 sysctl 系统参数数据

**输入**：
- 目录中的 `sysctllog_*` 文件
- 修改脚本中的 `BASE_DIR` 变量

**输出**：
- `sysctl.xlsx`：包含所有 vm.* 系统参数

**使用**：
```bash
python arse_sysctl.py
```

---

### 4. arse_json.py
**功能**：解析 footprint JSON 数据，提取进程内存信息

**输入**：
- 目录中的 `footprint_*.json` 文件
- 修改脚本中的 `BASE_DIR` 变量

**输出**：
- Excel 文件，包含每个进程的 footprint、Dirty、Swapped、Clean、Reclaimable、wired 等指标（单位：MB）

**使用**：
```bash
python arse_json.py
```

---

### 5. arse_log.py
**功能**：解析测试日志，匹配进程名和应用名

**输入**：
- 目录中的日志文件
- 修改脚本中的 `BASE_DIR` 变量
- 内置进程名映射字典（BackgroundLoad、ForegroundAPP 等）

**输出**：
- Excel 文件，包含进程名到应用名的映射关系

**使用**：
```bash
python arse_log.py
```

---

### 6. arse_compressor.py
**功能**：解析 compressor 压缩器数据

**输入**：
- compressor 文件（如 `compressor5`）
- 修改脚本中的 `COMPRESSOR_FILE` 和 `OUTPUT_DIR` 变量

**输出**：
- `compressor*.xlsx`：包含时间戳、compact awakens、compress size、pool size、pool actual size、minor frag、major frag 等指标

**使用**：
```bash
python arse_compressor.py
```

---

### 7. parse_comratio.py
**功能**：计算压缩比（Compression Ratio）

**输入**：
- 目录中的 `vmstatlog_*` 文件
- 修改脚本中的 `BASE_DIR` 变量

**输出**：
- `ComRatio.xlsx`：包含 Stored、Occupied、Ratio（压缩比）及平均值

**计算公式**：
- Ratio = Pages stored in compressor / Pages occupied by compressor

**使用**：
```bash
python parse_comratio.py
```

---

### 8. footprint_jsonperpid.py
**功能**：按进程解析 footprint JSON 数据，生成格式化的 Excel 报告

**输入**：
- footprint JSON 文件（通过命令行参数指定）

**输出**：
- Excel 文件，每个进程一个独立的数据块，包含 Dirty、Swapped、Clean、Reclaimable、Wired、Regions 六个指标的详细分类

**使用**：
```bash
python footprint_jsonperpid.py <footprint.json>
```

---

### 9. parse_txtfootprint.py
**功能**：解析文本格式的 footprint 数据

**输入**：
- 文本格式的 footprint 文件
- 内置 iOS 应用进程名映射字典

**输出**：
- Excel 文件，包含进程名到应用名的映射及内存数据

**使用**：
```bash
python parse_txtfootprint.py
```

---

### 10. match_step.py
**功能**：将 footprint、sysctl、vmstat 数据按时间戳匹配到测试步骤

**输入**：
- `footprint_step.xlsx`：包含测试步骤和时间戳的 footprint 数据
- `sysctl/sysctl.xlsx`：sysctl 数据
- `vmstat/vmstat.xlsx`：vmstat 数据
- 修改脚本中的 `BASE_DIR` 变量

**输出**：
- `sysctl/sysctl_step.xlsx`：带步骤信息的 sysctl 数据
- `vmstat/vmstat_step.xlsx`：带步骤信息的 vmstat 数据

**匹配规则**：
- 根据时间戳匹配（允许最大 10 秒时间差）

**使用**：
```bash
python match_step.py
```

---

### 11. align_steps.py
**功能**：将测试日志中的步骤标记按时间对齐到 zprint 报告

**输入**：
- `all_log.txt`：测试日志文件
- `ios_zprint_report.xlsx`：zprint 报告

**输出**：
- `ios_zprint_report_with_steps.xlsx`：带步骤标记的 zprint 报告

**使用**：
```bash
python align_steps.py
```

---

### 12. app_info.py
**功能**：应用信息管理（具体功能需查看完整代码）

**输入**：
- 修改脚本中的 `BASE_DIR` 变量

**输出**：
- 应用相关信息的 Excel 文件

**使用**：
```bash
python app_info.py
```

---

## 使用流程示例

1. **采集数据**：使用 `/mem` 目录下的 shell 脚本采集 zprint、vmstat、sysctl、footprint 数据
2. **解析基础数据**：
   ```bash
   python arse_zprint.py    # 解析 zprint
   python arse_vmstat.py    # 解析 vmstat
   python arse_sysctl.py    # 解析 sysctl
   python arse_json.py      # 解析 footprint JSON
   ```
3. **计算压缩比**：
   ```bash
   python parse_comratio.py
   ```
4. **匹配测试步骤**：
   ```bash
   python match_step.py     # 将数据匹配到测试步骤
   python align_steps.py    # 对齐日志步骤
   ```

## 注意事项

1. 所有脚本都需要修改 `BASE_DIR` 变量指定数据文件目录
2. 输入文件命名格式必须符合脚本要求（如 `zprint_*`、`vmstatlog_*` 等）
3. 确保已安装所需的 Python 依赖库
4. 输出的 Excel 文件会保存在输入文件所在目录或脚本指定的输出目录



update
