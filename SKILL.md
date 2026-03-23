# MT4 Z-Score 异常成交量分析技能
## 基础信息
| 字段         | 取值                                                                 |
|--------------|----------------------------------------------------------------------|
| 技能ID       | mt4_zscore_analyzer                                                  |
| 名称         | MT4 Z-Score 异常成交量分析                                           |
| 版本         | 1.0.0                                                                |
| 适配平台     | OpenClaw 2026                                                        |
| 描述         | 通过 ZMQ 协议连接 MT4 交易平台，利用 Pandas-TA 计算价格/成交量 Z-Score，捕捉黄金（XAUUSD）、白银（XAGUSD）等品种的异常爆量信号 |
| 技能类型     | 命令执行型（Command）                                                |

## 执行配置
### 核心命令
```bash
python3 {{skillDir}}/mt4_zscore_skill.py --symbol {{symbol}} --length {{length}}