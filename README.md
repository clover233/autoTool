# autoTool

iOS / 鸿蒙 性能内存数据采集与解析工具集。

## 文件说明

| 文件 | 作用 | 需自定义 |
|------|------|----------|
| `mem/memcollct.sh` | SSH连接iOS设备并采集内存日志 | `PASSWORD` `IP` `PORT` `USER`、scp本地路径 |
| `mem/run.sh` | iOS设备端循环采集footprint/zprint | 采集间隔 `sleep 10`、触发方式(read/sleep) |
| `parse_harmonymem.py` | 解析鸿蒙hidumper内存输出为CSV | 命令行参数传入文件路径、`self.processes` 进程列表 |
| `parse_jsonfootprint.py` | 解析footprint JSON为Excel | 脚本同目录放 `footprint_*.json` 文件 |
| `parse_txtfootprint.py` | 解析footprint文本为Excel | `steps` 步骤列表、`ios_file_path` 数据目录、输出文件名 |
| `parse_zprint.py` | 解析zprint计算内核/驱动占用 | 脚本同目录放 `zprint_*` 文件 |
| `xc/analyze-memall.py` | 批量导出xctrace activity-monitor XML | `BASE_PATH` trace文件目录 |
| `xc/hitch.py` | 解析xctrace hitches卡顿数据为CSV | `run()` 参数：trace文件目录 |
| `xc/xc.py` | xctrace内存按步骤汇总(需log) | `case_folder` 用例目录路径 |
| `xc/xcnolog.py` | xctrace XML直接解析输出Excel | `case_folder` 用例目录路径 |
