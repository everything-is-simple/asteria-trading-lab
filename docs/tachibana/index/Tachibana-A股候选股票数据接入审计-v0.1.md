# Tachibana A 股候选股票数据接入审计 v0.1

## 版本定位

- 本文件承接 [Tachibana A 股候选股票结构资格样本表 v0.1](./Tachibana-A股候选股票结构资格样本表-v0.1.md)。
- 它审计当前仓库与正式数据目录中，是否已经具备填入真实 A 股结构资格样本的最低数据条件。
- 本文件不定义 A 股交易规则，不输出股票候选结论，不生成 `suitable / conditional`。
- 它只回答：现在能不能填真实 A 股候选样本；如果不能，缺什么。
- 最小接入包的正式字段、校验和禁止字段见 [Tachibana A 股最小接入包字段契约 v0.1](./Tachibana-A股最小接入包字段契约-v0.1.md)。
- 当前最小接入包验收结果见 [Tachibana A 股最小接入包验收报告 v0.1](./Tachibana-A股最小接入包验收报告-v0.1.md)。
- 数据到位后的复核顺序见 [Tachibana A 股最小接入包复核流程 v0.1](./Tachibana-A股最小接入包复核流程-v0.1.md)。

## 审计范围

| 路径 | 审计结果 | 说明 |
|---|---|---|
| `Z:\asteria-trading-labs-data` | 目录存在，但当前文件数为 `0`。 | 暂无正式 A 股数据文件可用。 |
| `Z:\asteria-trading-lab\data` | 仅发现 `pioneer-1975-1976`。 | 只有原始立花历史样本，没有 A 股候选数据。 |
| `docs/a-share/reference` | 有 A 股规则参考 Markdown。 | 可供制度规则后续使用，但不能替代个股元数据、日线数据或 MALF 快照。 |
| `docs/a-share/reference/README.md` | 明确申万分类原始表未纳入仓库。 | 申万个股行业标签当前缺失。 |
| `docs/tachibana/index` | 已有 A 股候选结构资格样本表。 | 只有字段契约与待填队列，没有真实个股结论。 |

## 最低数据条件

要把某只 A 股股票从 `universe_candidate` 升级到 `structure_candidate`，至少需要：

| 数据 | 必要字段 | 用途 |
|---|---|---|
| 股票元数据 | `ts_code / symbol_name / board_type / list_date / is_st / is_new_stock_window` | 判断是否是可审计对象，不做结构判断。 |
| 申万行业标签 | `ts_code / sw_l1_name / sw_l2_name / valid_from / valid_to` | 作为样本分层，不做买卖判断。 |
| 日线窗口 | `ts_code / trade_date / open / high / low / close / volume / amount / adj_factor_or_qfq_ref` | 供 MALF 生成结构快照。 |
| 数据质量标记 | `suspension_flag / missing_bar_flag / corporate_action_flag` | 判断样本能否进入结构审计。 |

要从 `structure_candidate` 升级到 `tachibana_candidate`，还需要：

| 数据 | 必要字段 | 用途 |
|---|---|---|
| MALF 快照 | `malf_snapshot_ref / malf_background / wave_range_break_fields / snapshot_window` | 结构资格判定的事实基础。 |
| 前置过滤器输出 | `tachibana_applicability / applicability_reason / boundary_warning / evidence_level` | 判断是否进入 Method / PM。 |
| 横向矩阵规则 | `qualification_rule_id / secondary_rule_ids` | 与历史样本规则对齐。 |

## 当前裁决

| 问题 | 裁决 |
|---|---|
| 是否可以填入真实 A 股 `tachibana_candidate`？ | 不可以。缺少 A 股 MALF 快照。 |
| 是否可以填入真实 A 股 `structure_candidate`？ | 不可以。缺少申万个股分类与 A 股日线窗口。 |
| 是否可以填入真实 A 股 `universe_candidate`？ | 暂不可以。正式数据目录没有股票元数据文件。 |
| 是否可以定义 T+1、涨跌停、停牌执行规则？ | 本轮不可以。原计划要求结构背景先行，制度约束后行。 |

## 禁止临时替代

| 禁止做法 | 原因 |
|---|---|
| 用行业指数代替个股行业分类。 | 行业指数不是个股样本元数据。 |
| 用流动性或成交额直接升级为 `tachibana_candidate`。 | 流动性不是结构资格。 |
| 用 A 股规则参考文档代替日线数据。 | 规则不是价格结构事实。 |
| 用人工挑选股票直接填 `suitable / conditional`。 | 没有 MALF 快照，无法复核。 |
| 先写 T+1 / 涨跌停适配。 | 会绕过“结构资格判定”主攻方向。 |

## 最小接入包

下一步最小数据接入不需要全市场，只需要一小批可复核样本。目录与文件口径由 [Tachibana A 股最小接入包字段契约 v0.1](./Tachibana-A股最小接入包字段契约-v0.1.md) 统一约束，概要如下：

```text
Z:\asteria-trading-labs-data\
  ashare\
    candidate-universe-v0.1.csv
    sw-industry-membership-v0.1.csv
    daily-window-v0.1\
      <ts_code>.csv
    malf-snapshots-v0.1\
      <ts_code>-<window>.json
```

| 文件 | 契约用途 |
|---|---|
| `candidate-universe-v0.1.csv` | 验收 A 股候选股票元数据，最多支持 `universe_candidate`。 |
| `sw-industry-membership-v0.1.csv` | 验收申万行业标签，只作为样本分层事实。 |
| `daily-window-v0.1/<ts_code>.csv` | 验收日线窗口是否可被 MALF 读取。 |
| `malf-snapshots-v0.1/<ts_code>-<window>.json` | 验收 MALF 结构事实快照，作为 `tachibana_candidate` 的必要证据。 |

## 待填样本占位

| ashare_sample_id | 当前阶段 | 缺失项 | 下一步 |
|---|---|---|---|
| `ASHARE-PENDING-001` | `blocked_by_missing_data` | 股票元数据、申万标签、日线窗口、MALF 快照。 | 导入最小接入包后再填。 |
| `ASHARE-PENDING-002` | `blocked_by_missing_data` | 日线窗口、MALF 快照。 | 先跑 MALF，不进入 Method / PM。 |
| `ASHARE-PENDING-003` | `blocked_by_missing_data` | board、ST、新股窗口、行业标签。 | 补 Data / Universe 事实。 |

## 当前结论

- 当前无法形成真实 A 股结构资格样本，因为正式数据目录为空，仓库内也没有 A 股日线窗口、申万个股分类或 MALF 快照。
- 这不是方法阻塞，而是数据接入前置条件未满足。
- 在数据接入前，A 股结构资格样本表只能保持待填状态；不得用经验、行业热度或流动性替代 MALF 快照。
- 当前验收报告已经将 `intake_package_status` 判为 `missing`，`contract_check_result` 判为 `fail`。
- 下一步应先按 [Tachibana A 股最小接入包字段契约 v0.1](./Tachibana-A股最小接入包字段契约-v0.1.md) 补数据，再按 [Tachibana A 股最小接入包复核流程 v0.1](./Tachibana-A股最小接入包复核流程-v0.1.md) 验收字段并生成 MALF 快照，不进入 T+1、涨跌停、停牌等制度规则改造。
