# Tachibana A-Share Adaptation v0 定义草案

## 版本定位

- 本文件是 `Tachibana A-Share Adaptation` 的第一份草稿，用于把立花义正日线波段交易法适配到中国 A 股市场。
- 本文件不替代 [Tachibana Method v1 定义草案](./Tachibana-Method-雏形.md)，也不修改 [Tachibana Position Management v1 定义草案](./Tachibana-Position-Management-雏形.md)。
- 原始立花法必须先独立回测；A 股适配版只能在原始法复刻完成之后，再作为“中国市场改造版”进入回测。
- 本文件仍是定义草稿，不是交易建议，不是实盘规则，不是 PAS 触发器。
- 分层边界见 [Tachibana 分层边界审计 v0.1](./Tachibana-分层边界审计-v0.1.md)；A 股适配只处理制度、候选池和执行约束，不反向修改 MALF / Method / PM 主定义。
- A 股候选股票的结构资格样本表见 [Tachibana A 股候选股票结构资格样本表 v0.1](./Tachibana-A股候选股票结构资格样本表-v0.1.md)；该表先判结构资格，不定义 T+1、涨跌停或停牌执行规则。
- A 股候选股票的数据接入状态见 [Tachibana A 股候选股票数据接入审计 v0.1](./Tachibana-A股候选股票数据接入审计-v0.1.md)。
- A 股最小接入包的字段验收口径见 [Tachibana A 股最小接入包字段契约 v0.1](./Tachibana-A股最小接入包字段契约-v0.1.md)。
- A 股最小接入包的当前验收结果见 [Tachibana A 股最小接入包验收报告 v0.1](./Tachibana-A股最小接入包验收报告-v0.1.md)。
- A 股最小接入包的数据到位复核顺序见 [Tachibana A 股最小接入包复核流程 v0.1](./Tachibana-A股最小接入包复核流程-v0.1.md)。
- A 股制度规则正式改造前必须先通过 [Tachibana A 股制度改造启动闸门 v0.1](./Tachibana-A股制度改造启动闸门-v0.1.md)；本文件中 T+1、涨跌停、停牌等内容在通过该闸门前均为候选约束草案。

## 当前冻结裁决

本文件早于“结构资格优先”攻坚链路形成，因此包含若干 A 股制度候选规则。自 [Tachibana A 股制度改造启动闸门 v0.1](./Tachibana-A股制度改造启动闸门-v0.1.md) 建立后，以下裁决优先生效：

| 内容 | 当前状态 | 说明 |
|---|---|---|
| T+1、涨跌停、停牌、板块差异 | 候选执行约束。 | 只有真实样本通过结构资格、Method / PM 与 Backtest Input 闸门后，才能转为正式执行约束。 |
| A 股选股池、申万行业、流动性过滤 | 候选样本分层工具。 | 不得替代 MALF 结构资格与 `rhythm_meaning`。 |
| 仓位尺度改造 | 候选 PM 执行折扣。 | 不得反向修改 Tachibana PM 主定义。 |
| 回测口径 | 候选执行层口径。 | 不得把制度回测结果反写为结构资格裁决。 |

因此，阅读本文件时应先把它理解为候选池，而不是当前可执行的 A 股正式规则。

## 双轨纪律

| 轨道 | 用途 | 是否引入 A 股规则 | 是否允许改造立花原意 | 输出 |
|---|---|---:|---:|---|
| `Tachibana Original` | 复刻书中立花义正交易法，验证原始方法的结构和绩效。 | 否 | 否 | 原始方法回测、原始动作解释 |
| `Tachibana A-Share Adaptation` | 在原始法理解完成后，适配中国 A 股交易制度和选股环境。 | 是 | 是，但必须显式标注 | A 股版方法定义、A 股版选股与回测约束 |

硬纪律：

- 不允许用 A 股制度反向解释 1975 年先锋电子交易谱。
- 不允许在原始立花回测中加入 T+1、涨跌停、申万行业筛选。
- 不允许把 A 股适配后的规则伪装成书中原意。
- 所有适配项必须标注为 `A股制度约束`、`A股市场结构改造` 或 `我们的抽象解释`。

## 本地参考资料

| 来源类别 | 文件入口 | 用途 |
|---|---|---|
| A 股交易制度 | [A股市场交易规则-tushare版.md](../../a-share/reference/A股市场交易规则-tushare版.md) | T+1、交易时段、板块差异、交易日历约束 |
| 涨跌停制度 | [A股涨跌停板制度-tushare版.md](../../a-share/reference/A股涨跌停板制度-tushare版.md) | 主板、科创板、创业板、北交所、ST、新股涨跌停差异 |
| 申万行业指数 | [A股申万行业指数-tushare版.md](../../a-share/reference/A股申万行业指数-tushare版.md) | 行业轮动、行业情绪、行业过滤 |
| 申万个股分类 | `首轮未纳入仓库；见 ../../a-share/reference/README.md` | 个股所属行业、一级/二级/三级行业映射、选股池构造 |

正式进入实现前，仍需以交易所最新规则和本地数据版本做一次最终校验。本文件现在只根据已给本地资料起草结构。

## A 股适配的核心问题

立花方法原始语境里，核心是日线节奏、分批、中心单、加码单、锁单、均价和利润保护。进入 A 股后，以下制度会改变“同一方法”的可执行形态。

| A 股特征 | 对立花方法的影响 | 适配归属 |
|---|---|---|
| T+1 | 当日买入不能当日卖出，试仓与认错必须承受隔夜风险。 | `execution_constraint` |
| 涨跌停 | 价格可能被制度性封住，波段推进、退出、锁单都会受到流动性约束。 | `limit_constraint` |
| 板块差异 | 主板、科创板、创业板、北交所、ST 的波动边界不同，不能使用同一仓位尺度。 | `board_constraint` |
| 新股特殊规则 | 新股早期波动和涨跌停约束不同，不适合直接套用普通波段节奏。 | `universe_filter` |
| 停牌/复牌 | 连续日线节奏可能中断，MALF wave 和仓位风险都要单独标记。 | `data_and_execution_constraint` |
| 申万行业结构 | A 股个股选择必须考虑行业属性、行业轮动和行业拥挤度。 | `stock_selection_layer` |
| 散户与情绪特征 | 涨跌停、连板、题材、行业热度可能放大短期波动。 | `market_microstructure_adjustment` |

## 定义范围

`Tachibana A-Share Adaptation` 负责四件事：

| 模块 | 职责 | 不做什么 |
|---|---|---|
| 交易制度约束 | 把 T+1、涨跌停、交易日历、板块规则写成方法外部约束。 | 不改变 MALF 主定义 |
| A 股选股池 | 用申万行业、板块、流动性、风险标签构造可交易候选池。 | 不把选股结果当成交易信号 |
| 仓位尺度改造 | 根据板块波动、涨跌停、ST/新股风险调整中心单和加码单尺度。 | 不否定原始分批原则 |
| 回测口径 | 区分原始回测和 A 股适配回测，确保结果可比较。 | 不把适配回测冒充书中方法绩效 |

## A 股制度约束定义

| 约束代码 | 定义 | 来源 | 对 Method 的影响 | 对 Position Management 的影响 |
|---|---|---|---|---|
| `ashare_t1_constraint` | 买入后最早下一个交易日才能卖出。 | [A股市场交易规则-tushare版.md](../../a-share/reference/A股市场交易规则-tushare版.md) | `exit_on_rhythm_failure` 不能默认当日完成。 | 试仓必须更小，隔夜风险必须进入仓位预算。 |
| `ashare_price_limit_constraint` | 涨跌停会限制价格连续波动和成交可能性。 | [A股涨跌停板制度-tushare版.md](../../a-share/reference/A股涨跌停板制度-tushare版.md) | `distribution_reduce` 和 `reversal_flip` 可能无法按计划成交。 | 锁单、减仓、清仓需要考虑封板和流动性失败。 |
| `ashare_board_volatility_constraint` | 不同板块涨跌停幅度不同，波动尺度不可混用。 | [A股涨跌停板制度-tushare版.md](../../a-share/reference/A股涨跌停板制度-tushare版.md) | 同样的 wave/progress 在不同板块意义不同。 | 中心单、加码单手数要按板块风险缩放。 |
| `ashare_st_constraint` | ST 股票涨跌停、退市风险、流动性特征特殊。 | [A股涨跌停板制度-tushare版.md](../../a-share/reference/A股涨跌停板制度-tushare版.md) | 默认不进入普通立花 A 股选股池。 | 如纳入，必须单独定义极端仓位上限。 |
| `ashare_ipo_constraint` | 新股上市初期规则与波动特殊。 | [A股涨跌停板制度-tushare版.md](../../a-share/reference/A股涨跌停板制度-tushare版.md) | 默认不用于普通波段训练样本。 | 新股仓位规则需独立定义，暂不纳入。 |
| `ashare_trading_calendar_constraint` | 节假日、停牌、复牌会打断日线节奏。 | [A股市场交易规则-tushare版.md](../../a-share/reference/A股市场交易规则-tushare版.md) | MALF 和 Method 必须知道不可交易日。 | 持仓风险要按实际不可交易天数计算。 |

## A 股选股层草案

立花方法的一个关键现实问题是：选出适合日线波段、分批、中心单和加码的股票。A 股适配版必须新增 `Tachibana A-Share Stock Selection`，但本阶段先放在本文件内作为草稿。

### 选股目标

选股不是预测哪只股票马上涨，而是寻找适合立花式训练和交易的对象：

- 日线节奏清楚，价格有可观察的推进、回撤、盘整。
- 流动性足够，分批进出不会被成交困难严重扭曲。
- 行业属性明确，能放入申万行业框架观察。
- 不频繁停牌，不处于明显制度异常状态。
- 适合反复记录、复盘、训练，而不是追逐一次性题材。

### 候选池过滤

| 过滤层 | 规则草案 | 处理结果 |
|---|---|---|
| `market_scope` | 先限定 A 股普通股票；北交所、新股、ST 默认排除。 | 降低制度异常干扰 |
| `board_scope` | 第一版优先主板、创业板、科创板；不同板块分开回测。 | 避免波动尺度混池 |
| `industry_scope` | 使用申万一级/二级行业归类，行业缺失者暂不纳入。 | 支持行业对照 |
| `liquidity_scope` | 需要后续定义成交额、换手、停牌率等最低门槛。 | 保证分批可执行 |
| `limit_behavior_scope` | 记录涨跌停、炸板、连续涨跌停，但不直接作为买卖信号。 | 作为情绪和流动性风险 |
| `malf_suitability_scope` | 能否产生稳定 wave/range 样本。 | 用于 MALF 适配验证 |

## 申万行业与立花选股

申万行业在 A 股适配版中不是预测器，而是“对象分类器”和“环境过滤器”。

| 用法 | 定义 | 禁止用法 |
|---|---|---|
| 行业归属 | 给每只股票贴上申万一级/二级/三级行业标签。 | 不因为行业热门就直接买入 |
| 行业背景 | 判断个股节奏是否与行业共振或背离。 | 不把行业涨幅当作立花交易依据 |
| 样本分层 | 回测时按行业拆分表现，避免把行业周期误认为方法优势。 | 不把全市场样本粗暴混在一起 |
| 选股池维护 | 剔除行业分类缺失、行业变更未同步的标的。 | 不使用来源不明的行业标签 |

候选股票的第一版结构资格字段已独立为 [Tachibana A 股候选股票结构资格样本表 v0.1](./Tachibana-A股候选股票结构资格样本表-v0.1.md)。它不是完整选股池定义，而是 A 股进入 Method / PM 前的结构资格闸门。

## A 股版动作适配

| 原始 Method 动作 | A 股适配问题 | A 股版解释 |
|---|---|---|
| `trend_probe_entry` | T+1 导致试仓当天不能纠错卖出。 | 试仓手数必须更克制，且默认承担隔夜风险。 |
| `trend_confirmation_add` | 涨停附近加码可能成交困难，且隔日回撤不可当日退出。 | 加码必须避开纯封板冲动，更多依赖回撤后的可成交节奏。 |
| `pullback_entry` | 跌停或接近跌停时，回撤可能不是机会而是流动性风险。 | 回撤入口必须区分自然回撤与制度性跌停压力。 |
| `pullback_add` | T+1 和板块波动会放大加码后的不可逆风险。 | 加码单需要板块风险折扣和当日涨跌停距离检查。 |
| `distribution_reduce` | 涨停想卖、跌停想卖都可能有成交偏差。 | 减仓规则要记录计划成交与实际成交差异。 |
| `exit_on_rhythm_failure` | 节奏失败当天可能无法卖出，尤其跌停。 | 必须定义 `exit_blocked_by_limit` 状态。 |
| `reversal_flip` | A 股股票不能日内回转卖出已买入仓位。 | 反手在 A 股中需要拆成“退出原仓”和“建立新仓”两个阶段。 |
| `inventory_rebalance` | 双向锁单在普通股票实操中受工具约束，不能照搬期货/信用语境。 | 需区分普通账户、融资融券、股指/ETF 工具；第一版暂不默认支持。 |
| `wait_no_action` | A 股情绪噪声和题材诱惑强。 | 等待要成为显式动作，尤其在涨跌停密集或行业过热时。 |

## 仓位管理适配

| PM 概念 | A 股改造 | 草案规则 |
|---|---|---|
| 中心单 | 仍保留，但初始中心单不应过大。 | 中心单规模受板块、涨跌停距离、流动性约束。 |
| 加码单 | 仍保留，但更强调可成交回撤。 | 不在连续涨停、极端高开或流动性异常时机械加码。 |
| 均价 | 更重要，因为 T+1 会放大隔夜压力。 | 每次加减仓都必须记录均价变化。 |
| 锁单 | 不能照搬原始语境。 | 普通股票第一版不默认启用锁单；如用融资融券或 ETF 对冲，另起定义。 |
| 利润保护 | 更重要，因为跌停可能阻断退出。 | 分批减仓要早于“必须卖”的时刻。 |
| 清仓 | 可能受涨跌停和停牌影响。 | 需要记录 `planned_exit_date` 与 `actual_exit_date`。 |

## 与 MALF 的关系

| MALF 观察项 | A 股适配方式 | 边界 |
|---|---|---|
| `wave / progress` | 仍用于描述日线波段推进。 | 涨跌停造成的跳跃推进要单独标注，不等同自然波段。 |
| `range` | 仍用于描述震荡或无推进。 | 一字板、停牌、缩量封板不是普通 range。 |
| `break / birth_type` | 仍可描述结构转换。 | 受制度限制无法成交时，break 不等于可执行反手。 |
| `lifespan` | 可比较不同股票/行业的波段寿命。 | 板块涨跌停幅度不同，样本不能不加区分地混池。 |
| `probability` | 可作为结构辅助。 | 不替代 T+1、涨跌停、行业和流动性约束。 |

结论：A 股适配不要求修改 MALF 主定义，但需要在 MALF 输出之外增加 `AShareMarketConstraintSnapshot`。

## 建议新增数据快照

### `AShareMarketConstraintSnapshot`

| 字段 | 类型 | 含义 |
|---|---|---|
| `trade_date` | date | 交易日 |
| `ts_code` | string | 股票代码 |
| `board_type` | enum | `main / star / gem / bse / st / unknown` |
| `is_st` | boolean | 是否 ST 或 *ST |
| `is_new_stock_window` | boolean | 是否处于新股特殊窗口 |
| `is_suspended` | boolean | 是否停牌 |
| `limit_up_price` | number/null | 涨停价 |
| `limit_down_price` | number/null | 跌停价 |
| `close_limit_status` | enum | `none / limit_up / limit_down / near_limit_up / near_limit_down` |
| `touched_limit_status` | enum | `none / touched_up / touched_down / both` |
| `t1_sellable_shares` | number | 当日可卖股数 |
| `newly_bought_shares` | number | 当日买入、尚不可卖股数 |
| `sw_l1_code` | string/null | 申万一级行业代码 |
| `sw_l1_name` | string/null | 申万一级行业名称 |
| `sw_l2_code` | string/null | 申万二级行业代码 |
| `sw_l2_name` | string/null | 申万二级行业名称 |
| `constraint_reason_codes` | list | 约束原因，如 `t1_blocked`、`limit_down_exit_blocked` |

### `AshareAdaptedTachibanaDecisionContext`

| 字段 | 类型 | 含义 |
|---|---|---|
| `method_action_original` | enum | 原始立花动作分类 |
| `method_action_ashare` | enum | A 股适配后的动作分类 |
| `adaptation_reason` | list | 适配原因 |
| `malf_snapshot_ref` | string | 对应 MALF 快照 |
| `market_constraint_ref` | string | 对应 A 股制度约束快照 |
| `stock_selection_ref` | string | 对应选股池/行业过滤记录 |
| `pm_adjustment` | list | 仓位层调整 |
| `is_original_comparable` | boolean | 是否仍可与原始立花动作比较 |

## 回测分层

| 回测层 | 名称 | 用途 | 数据约束 |
|---|---|---|---|
| `BT-0` | 原始立花复刻回测 | 验证书中方法，不引入 A 股制度。 | 先锋电子 1975-1976、原始月表 |
| `BT-1` | MALF + 原始立花法 | 验证 MALF 是否能解释原始动作。 | 不引入 A 股制度 |
| `BT-2` | MALF + A 股制度约束 | 验证结构语言在 A 股是否可用。 | 加入 T+1、涨跌停、停牌、交易日历 |
| `BT-3` | MALF + A 股选股 + 立花 PM | 验证 A 股改造版完整框架。 | 加入申万行业、选股池、仓位缩放 |

验收纪律：

- `BT-0` 与 `BT-1` 不允许引用本文件规则。
- `BT-2` 开始才允许使用 A 股制度约束。
- `BT-3` 才允许使用申万行业选股层。
- 每个回测结果必须标明使用的是 `Original` 还是 `A-Share Adapted`。

## 当前暂不定义

- 不定义具体买卖信号。
- 不定义 A 股最终选股公式。
- 不定义行业轮动打分。
- 不定义融资融券、ETF 对冲、期货替代锁单。
- 不定义实盘执行系统。
- 不修订 MALF 主定义。
- 不解冻 PAS。

## 下一版要补

- 按 [Tachibana A 股最小接入包字段契约 v0.1](./Tachibana-A股最小接入包字段契约-v0.1.md) 建立最小接入包，并按 [Tachibana A 股最小接入包复核流程 v0.1](./Tachibana-A股最小接入包复核流程-v0.1.md) 输出 `intake_package_status` 与 `contract_check_result`。
- 从申万行业分类 Excel 中抽取字段口径，填充 [Tachibana A 股候选股票结构资格样本表 v0.1](./Tachibana-A股候选股票结构资格样本表-v0.1.md)。
- 跑出第一批 A 股候选窗口的 MALF 快照，生成 `malf_snapshot_ref`。
- 把 A 股交易规则压缩为可回测的 `reason_code` 枚举。
- 为 `exit_blocked_by_limit`、`t1_blocked`、`suspended_gap` 建立明确状态定义。
- 单独起草完整 `Tachibana-A股选股池定义.md`，但必须承接结构资格样本表。
- 单独起草 `Tachibana-A股回测口径.md`。
- 在完成原始立花回测后，再把本文件升级为 v1。
