# asteria-trading-lab

`asteria-trading-lab` 是一个面向“研究 + 定义 + 回测规格”的轻量仓库。

当前主线有三条：

- 原始立花义正波段交易法研究与回测规格
- MALF 结构语言与立花方法的映射
- 中国 A 股适配版立花义正波段交易法

## 推荐阅读顺序

1. [docs/tachibana/index/1975-总览.md](docs/tachibana/index/1975-%E6%80%BB%E8%A7%88.md)
2. [docs/tachibana/index/1976-总览.md](docs/tachibana/index/1976-%E6%80%BB%E8%A7%88.md)
3. [docs/tachibana/index/1976-补充完善清单.md](docs/tachibana/index/1976-%E8%A1%A5%E5%85%85%E5%AE%8C%E5%96%84%E6%B8%85%E5%8D%95.md)
4. [docs/tachibana/index/立花交易依据分类表.md](docs/tachibana/index/%E7%AB%8B%E8%8A%B1%E4%BA%A4%E6%98%93%E4%BE%9D%E6%8D%AE%E5%88%86%E7%B1%BB%E8%A1%A8.md)
5. [docs/tachibana/index/MALF-立花映射总表.md](docs/tachibana/index/MALF-%E7%AB%8B%E8%8A%B1%E6%98%A0%E5%B0%84%E6%80%BB%E8%A1%A8.md)
6. [docs/tachibana/index/MALF-立花前置认知过滤器攻坚总控矩阵-v0.1.md](docs/tachibana/index/MALF-%E7%AB%8B%E8%8A%B1%E5%89%8D%E7%BD%AE%E8%AE%A4%E7%9F%A5%E8%BF%87%E6%BB%A4%E5%99%A8%E6%94%BB%E5%9D%9A%E6%80%BB%E6%8E%A7%E7%9F%A9%E9%98%B5-v0.1.md)
7. [docs/tachibana/index/MALF-立花前置认知过滤器-v0.1.md](docs/tachibana/index/MALF-%E7%AB%8B%E8%8A%B1%E5%89%8D%E7%BD%AE%E8%AE%A4%E7%9F%A5%E8%BF%87%E6%BB%A4%E5%99%A8-v0.1.md)
8. [docs/tachibana/index/MALF-立花结构资格样本表-v0.1.md](docs/tachibana/index/MALF-%E7%AB%8B%E8%8A%B1%E7%BB%93%E6%9E%84%E8%B5%84%E6%A0%BC%E6%A0%B7%E6%9C%AC%E8%A1%A8-v0.1.md)
9. [docs/tachibana/index/MALF-立花结构资格横向判读矩阵-v0.1.md](docs/tachibana/index/MALF-%E7%AB%8B%E8%8A%B1%E7%BB%93%E6%9E%84%E8%B5%84%E6%A0%BC%E6%A8%AA%E5%90%91%E5%88%A4%E8%AF%BB%E7%9F%A9%E9%98%B5-v0.1.md)
10. [docs/tachibana/index/MALF-立花结构状态到仓位节奏意义判定准则-v0.1.md](docs/tachibana/index/MALF-%E7%AB%8B%E8%8A%B1%E7%BB%93%E6%9E%84%E7%8A%B6%E6%80%81%E5%88%B0%E4%BB%93%E4%BD%8D%E8%8A%82%E5%A5%8F%E6%84%8F%E4%B9%89%E5%88%A4%E5%AE%9A%E5%87%86%E5%88%99-v0.1.md)
11. [docs/tachibana/index/MALF-立花rhythm_meaning历史样本回填审计-v0.1.md](docs/tachibana/index/MALF-%E7%AB%8B%E8%8A%B1rhythm_meaning%E5%8E%86%E5%8F%B2%E6%A0%B7%E6%9C%AC%E5%9B%9E%E5%A1%AB%E5%AE%A1%E8%AE%A1-v0.1.md)
12. [docs/tachibana/index/MALF-立花not_meaningful反例登记表-v0.1.md](docs/tachibana/index/MALF-%E7%AB%8B%E8%8A%B1not_meaningful%E5%8F%8D%E4%BE%8B%E7%99%BB%E8%AE%B0%E8%A1%A8-v0.1.md)
13. [docs/tachibana/index/MALF-立花样本升级门槛-v0.1.md](docs/tachibana/index/MALF-%E7%AB%8B%E8%8A%B1%E6%A0%B7%E6%9C%AC%E5%8D%87%E7%BA%A7%E9%97%A8%E6%A7%9B-v0.1.md)
14. [docs/tachibana/index/MALF-立花1975-06交易段结构资格审计-v0.1.md](docs/tachibana/index/MALF-%E7%AB%8B%E8%8A%B11975-06%E4%BA%A4%E6%98%93%E6%AE%B5%E7%BB%93%E6%9E%84%E8%B5%84%E6%A0%BC%E5%AE%A1%E8%AE%A1-v0.1.md)
15. [docs/tachibana/index/MALF-立花1976-01至02样本升级审计-v0.1.md](docs/tachibana/index/MALF-%E7%AB%8B%E8%8A%B11976-01%E8%87%B302%E6%A0%B7%E6%9C%AC%E5%8D%87%E7%BA%A7%E5%AE%A1%E8%AE%A1-v0.1.md)
16. [docs/tachibana/index/MALF-立花1976-03与07交易段结构资格审计-v0.1.md](docs/tachibana/index/MALF-%E7%AB%8B%E8%8A%B11976-03%E4%B8%8E07%E4%BA%A4%E6%98%93%E6%AE%B5%E7%BB%93%E6%9E%84%E8%B5%84%E6%A0%BC%E5%AE%A1%E8%AE%A1-v0.1.md)
17. [docs/tachibana/index/MALF-立花1976-04至05交易段结构资格审计-v0.1.md](docs/tachibana/index/MALF-%E7%AB%8B%E8%8A%B11976-04%E8%87%B305%E4%BA%A4%E6%98%93%E6%AE%B5%E7%BB%93%E6%9E%84%E8%B5%84%E6%A0%BC%E5%AE%A1%E8%AE%A1-v0.1.md)
18. [docs/tachibana/index/MALF-立花1976-06至09样本升级审计-v0.1.md](docs/tachibana/index/MALF-%E7%AB%8B%E8%8A%B11976-06%E8%87%B309%E6%A0%B7%E6%9C%AC%E5%8D%87%E7%BA%A7%E5%AE%A1%E8%AE%A1-v0.1.md)
19. [docs/tachibana/index/MALF-立花1976-09制度资料口径审计-v0.1.md](docs/tachibana/index/MALF-%E7%AB%8B%E8%8A%B11976-09%E5%88%B6%E5%BA%A6%E8%B5%84%E6%96%99%E5%8F%A3%E5%BE%84%E5%AE%A1%E8%AE%A1-v0.1.md)
20. [docs/tachibana/index/MALF-立花1976-11交易段结构资格审计-v0.1.md](docs/tachibana/index/MALF-%E7%AB%8B%E8%8A%B11976-11%E4%BA%A4%E6%98%93%E6%AE%B5%E7%BB%93%E6%9E%84%E8%B5%84%E6%A0%BC%E5%AE%A1%E8%AE%A1-v0.1.md)
21. [docs/tachibana/index/MALF-立花1976-12交易段结构资格审计-v0.1.md](docs/tachibana/index/MALF-%E7%AB%8B%E8%8A%B11976-12%E4%BA%A4%E6%98%93%E6%AE%B5%E7%BB%93%E6%9E%84%E8%B5%84%E6%A0%BC%E5%AE%A1%E8%AE%A1-v0.1.md)
22. [docs/tachibana/index/Tachibana-分层边界审计-v0.1.md](docs/tachibana/index/Tachibana-%E5%88%86%E5%B1%82%E8%BE%B9%E7%95%8C%E5%AE%A1%E8%AE%A1-v0.1.md)
23. [docs/tachibana/index/Tachibana-Data-Signal-Backtest-接口边界审计-v0.1.md](docs/tachibana/index/Tachibana-Data-Signal-Backtest-%E6%8E%A5%E5%8F%A3%E8%BE%B9%E7%95%8C%E5%AE%A1%E8%AE%A1-v0.1.md)
24. [docs/tachibana/index/Tachibana-rhythm_meaning-Data-Signal-Backtest-接口接缝补丁-v0.1.md](docs/tachibana/index/Tachibana-rhythm_meaning-Data-Signal-Backtest-%E6%8E%A5%E5%8F%A3%E6%8E%A5%E7%BC%9D%E8%A1%A5%E4%B8%81-v0.1.md)
25. [docs/tachibana/index/Tachibana-Method-雏形.md](docs/tachibana/index/Tachibana-Method-%E9%9B%8F%E5%BD%A2.md)
26. [docs/tachibana/index/Tachibana-Position-Management-雏形.md](docs/tachibana/index/Tachibana-Position-Management-%E9%9B%8F%E5%BD%A2.md)
27. [docs/tachibana/index/Tachibana-Backtest-Input-适配层草案-v0.1.md](docs/tachibana/index/Tachibana-Backtest-Input-%E9%80%82%E9%85%8D%E5%B1%82%E8%8D%89%E6%A1%88-v0.1.md)
28. [docs/tachibana/index/TachibanaBacktestInput-1976段级样本试填审计-v0.1.md](docs/tachibana/index/TachibanaBacktestInput-1976%E6%AE%B5%E7%BA%A7%E6%A0%B7%E6%9C%AC%E8%AF%95%E5%A1%AB%E5%AE%A1%E8%AE%A1-v0.1.md)
29. [docs/tachibana/index/TachibanaBacktestInput-1975-06段级样本试填审计-v0.1.md](docs/tachibana/index/TachibanaBacktestInput-1975-06%E6%AE%B5%E7%BA%A7%E6%A0%B7%E6%9C%AC%E8%AF%95%E5%A1%AB%E5%AE%A1%E8%AE%A1-v0.1.md)
30. [docs/backtest-spec/tachibana-part1-3-detail-calibration.md](docs/backtest-spec/tachibana-part1-3-detail-calibration.md)
31. [docs/backtest-spec/tachibana-part4-pm-annotations-v0.1.md](docs/backtest-spec/tachibana-part4-pm-annotations-v0.1.md)
32. [docs/backtest-spec/tachibana-final-source-calibration-1975-1976.md](docs/backtest-spec/tachibana-final-source-calibration-1975-1976.md)
33. [docs/backtest-spec/original-tachibana-method-v0.1.md](docs/backtest-spec/original-tachibana-method-v0.1.md)
34. [docs/backtest-spec/original-tachibana-v0.1-statistics-report.md](docs/backtest-spec/original-tachibana-v0.1-statistics-report.md)
35. [docs/backtest-spec/original-tachibana-v0.1-performance-report.md](docs/backtest-spec/original-tachibana-v0.1-performance-report.md)
36. [docs/backtest-spec/original-tachibana-v0.1-major-trades-report.md](docs/backtest-spec/original-tachibana-v0.1-major-trades-report.md)
37. [docs/backtest-spec/original-tachibana-v0.1-quant-report.md](docs/backtest-spec/original-tachibana-v0.1-quant-report.md)
38. [docs/backtest-spec/original-tachibana-v0.1-source-data-audit.md](docs/backtest-spec/original-tachibana-v0.1-source-data-audit.md)
39. [docs/tachibana/index/Tachibana-A股候选股票结构资格样本表-v0.1.md](docs/tachibana/index/Tachibana-A%E8%82%A1%E5%80%99%E9%80%89%E8%82%A1%E7%A5%A8%E7%BB%93%E6%9E%84%E8%B5%84%E6%A0%BC%E6%A0%B7%E6%9C%AC%E8%A1%A8-v0.1.md)
40. [docs/tachibana/index/Tachibana-A股候选股票数据接入审计-v0.1.md](docs/tachibana/index/Tachibana-A%E8%82%A1%E5%80%99%E9%80%89%E8%82%A1%E7%A5%A8%E6%95%B0%E6%8D%AE%E6%8E%A5%E5%85%A5%E5%AE%A1%E8%AE%A1-v0.1.md)
41. [docs/tachibana/index/Tachibana-A股最小接入包字段契约-v0.1.md](docs/tachibana/index/Tachibana-A%E8%82%A1%E6%9C%80%E5%B0%8F%E6%8E%A5%E5%85%A5%E5%8C%85%E5%AD%97%E6%AE%B5%E5%A5%91%E7%BA%A6-v0.1.md)
42. [docs/tachibana/index/Tachibana-A股最小接入包落盘准备清单-v0.1.md](docs/tachibana/index/Tachibana-A%E8%82%A1%E6%9C%80%E5%B0%8F%E6%8E%A5%E5%85%A5%E5%8C%85%E8%90%BD%E7%9B%98%E5%87%86%E5%A4%87%E6%B8%85%E5%8D%95-v0.1.md)
43. [docs/tachibana/index/Tachibana-A股最小接入包验收报告-v0.1.md](docs/tachibana/index/Tachibana-A%E8%82%A1%E6%9C%80%E5%B0%8F%E6%8E%A5%E5%85%A5%E5%8C%85%E9%AA%8C%E6%94%B6%E6%8A%A5%E5%91%8A-v0.1.md)
44. [docs/tachibana/index/Tachibana-A股最小接入包复核流程-v0.1.md](docs/tachibana/index/Tachibana-A%E8%82%A1%E6%9C%80%E5%B0%8F%E6%8E%A5%E5%85%A5%E5%8C%85%E5%A4%8D%E6%A0%B8%E6%B5%81%E7%A8%8B-v0.1.md)
45. [docs/tachibana/index/Tachibana-A股结构资格判定记录模板-v0.1.md](docs/tachibana/index/Tachibana-A%E8%82%A1%E7%BB%93%E6%9E%84%E8%B5%84%E6%A0%BC%E5%88%A4%E5%AE%9A%E8%AE%B0%E5%BD%95%E6%A8%A1%E6%9D%BF-v0.1.md)
46. [docs/tachibana/index/Tachibana-A股结构资格判定记录-ASHARE-PENDING-v0.1.md](docs/tachibana/index/Tachibana-A%E8%82%A1%E7%BB%93%E6%9E%84%E8%B5%84%E6%A0%BC%E5%88%A4%E5%AE%9A%E8%AE%B0%E5%BD%95-ASHARE-PENDING-v0.1.md)
47. [docs/tachibana/index/Tachibana-A股结构资格升级闸门检查清单-v0.1.md](docs/tachibana/index/Tachibana-A%E8%82%A1%E7%BB%93%E6%9E%84%E8%B5%84%E6%A0%BC%E5%8D%87%E7%BA%A7%E9%97%B8%E9%97%A8%E6%A3%80%E6%9F%A5%E6%B8%85%E5%8D%95-v0.1.md)
48. [docs/tachibana/index/Tachibana-A股结构资格理由码表-v0.1.md](docs/tachibana/index/Tachibana-A%E8%82%A1%E7%BB%93%E6%9E%84%E8%B5%84%E6%A0%BC%E7%90%86%E7%94%B1%E7%A0%81%E8%A1%A8-v0.1.md)
49. [docs/tachibana/index/Tachibana-A股制度改造启动闸门-v0.1.md](docs/tachibana/index/Tachibana-A%E8%82%A1%E5%88%B6%E5%BA%A6%E6%94%B9%E9%80%A0%E5%90%AF%E5%8A%A8%E9%97%B8%E9%97%A8-v0.1.md)
50. [docs/tachibana/index/Tachibana-A股适配版-雏形.md](docs/tachibana/index/Tachibana-A%E8%82%A1%E9%80%82%E9%85%8D%E7%89%88-%E9%9B%8F%E5%BD%A2.md)

## 当前状态

- `1975`：全年研究主线已较完整
- `1976`：全年事实骨架已建立，`1976-03/04/05/10/11/12` 已部分精读
- 近期目标：当前主攻不是修改交易规则，而是把 MALF 做成立花法的前置认知过滤器。机器链路已经按 `A 股接入包复核 -> MALF snapshot -> rhythm_meaning -> candidate_table_gate -> Method/PM bridge -> Backtest Input -> cognitive_pipeline_gate` 收束；只有总闸门通过后，才允许进入 A 股制度约束审计。
- 远期目标：A 股适配版与回测报告
- 当前项目口径：`PAS` 已明确搁置，不纳入当前施工主线与进度估算。

## 当前闸门纪律

- MALF 只判断结构事实与结构资格，不输出买卖信号、仓位规模、中心单或锁单结论。
- Tachibana Method / Position Management 承接交易动作、仓位节奏与复盘解释，不反向改写 MALF 定义。
- Data / Signal / Backtest 只承接已成型的结构结果；不得把交易判断前置到数据层或信号层。
- A 股适配只处理制度约束，例如 T+1、涨跌停、停牌和可交易性；它不是方法本体，必须在 `cognitive_pipeline_gate=pass` 之后再启动。

## 目录说明

- `docs/tachibana/`：立花方法研究主线
- `docs/a-share/`：A 股规则与适配定义
- `docs/backtest-spec/`：回测规格与证据裁决
- `docs/malf/`：MALF 入口与后续承接
- `data/pioneer-1975-1976/`：月度 JSON 与 24 张交易谱截图
- `research/sources/`：未纳入仓库的大体量原始资料说明
- `src/`：后续回测代码与解析器实现
