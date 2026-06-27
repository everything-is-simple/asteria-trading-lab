# Tachibana A 股结构资格理由码表 v0.1

## 版本定位

- 本文件承接 [Tachibana A 股结构资格判定记录模板 v0.1](./Tachibana-A股结构资格判定记录模板-v0.1.md)、[Tachibana A 股结构资格升级闸门检查清单 v0.1](./Tachibana-A股结构资格升级闸门检查清单-v0.1.md) 与 [Tachibana A 股结构资格判定记录 ASHARE-PENDING v0.1](./Tachibana-A股结构资格判定记录-ASHARE-PENDING-v0.1.md)。
- 它是 A 股结构资格判定的受控理由码表，不是交易信号，不是选股公式，不是 A 股制度规则。
- 它统一 `failed_contract_items / rule_match_reason / applicability_reason / boundary_warning / next_action` 的写法，避免未来真实样本各写各的理由。
- `rhythm_meaning` 的判定准则见 [MALF-立花结构状态到仓位节奏意义判定准则 v0.1](./MALF-立花结构状态到仓位节奏意义判定准则-v0.1.md)。
- `not_meaningful` 反例登记口径见 [MALF-立花 not_meaningful 反例登记表 v0.1](./MALF-立花not_meaningful反例登记表-v0.1.md)。
- `rhythm_meaning` 穿过 Data / Signal / Backtest 的接口接缝见 [Tachibana rhythm_meaning Data / Signal / Backtest 接口接缝补丁 v0.1](./Tachibana-rhythm_meaning-Data-Signal-Backtest-接口接缝补丁-v0.1.md)。
- 本文件不定义 T+1、涨跌停、停牌、整手、融资融券或任何执行约束。

## 命名规则

| 前缀 | 用途 | 示例 |
|---|---|---|
| `missing_*` | 接入包字段、文件或证据缺失。 | `missing_daily_window` |
| `blocked_by_*` | 当前阶段被某个缺口或争议阻断。 | `blocked_by_missing_malf_snapshot` |
| `no_*` | 前置过滤器或裁决理由中的否定事实。 | `no_ready_malf_snapshot` |
| `do_not_*` | 边界警告，防止越界解释。 | `do_not_upgrade_without_malf_snapshot` |
| `ready_*` | 通过型证据理由，仅表示可进入下一检查。 | `ready_daily_window` |
| `action:*` | `next_action` 的受控动作。 | `action:repair_data` |
| `NM-*` | `not_meaningful` 反例类型，不是交易排除规则。 | `NM-NO-STRUCTURE` |

理由码只说明结构资格证据状态，不表示买入、卖出、目标仓位或执行策略。

## 1. failed_contract_items

| reason_code | 含义 | 阻断层级 |
|---|---|---|
| `missing_candidate_universe` | 缺 `candidate-universe-v0.1.csv`。 | Gate 0 |
| `missing_ts_code` | 缺股票代码。 | Gate 0 |
| `missing_symbol_name` | 缺股票简称。 | Gate 0 |
| `missing_board_type` | 缺板块字段。 | Gate 0 |
| `missing_list_date` | 缺上市日期。 | Gate 0 |
| `missing_st_flag` | 缺 ST 标记。 | Gate 0 |
| `missing_new_stock_window` | 缺新股窗口标记。 | Gate 0 |
| `missing_source_ref` | 缺来源引用。 | Gate 0 |
| `missing_sw_industry_membership` | 缺申万行业标签文件。 | Gate 1 |
| `missing_industry_label` | 缺样本窗口有效行业标签。 | Gate 1 |
| `missing_daily_window` | 缺日线窗口。 | Gate 1 |
| `invalid_daily_ohlc` | 日线 OHLC 不合法。 | Gate 1 |
| `missing_quality_flags` | 缺数据质量标记。 | Gate 1 |
| `missing_malf_snapshot` | 缺 MALF 快照。 | Gate 2 |
| `malf_snapshot_not_ready` | MALF 快照不是 `ready`。 | Gate 2 |
| `malf_snapshot_window_mismatch` | MALF 快照窗口与日线窗口不一致。 | Gate 2 |
| `missing_qualification_rule_id` | 缺横向矩阵规则。 | Gate 2 |
| `missing_boundary_warning` | 缺必要边界警告。 | Gate 2 / Gate 3 |
| `missing_evidence_level` | 缺证据层级。 | Gate 3 |
| `forbidden_field_present` | 出现禁止字段。 | 任意阶段 |
| `duplicate_key_present` | 主键重复。 | 对应字段所在 Gate |
| `invalid_enum_value` | 枚举字段不在允许值内。 | 对应字段所在 Gate |
| `invalid_date_value` | 日期字段不符合 `YYYY-MM-DD` 或时间顺序不合法。 | 对应字段所在 Gate |
| `invalid_boolean_value` | 布尔字段不是 `true / false`。 | 对应字段所在 Gate |
| `invalid_numeric_value` | 数值字段不可解析或为负。 | Gate 1 |
| `source_disrupted` | 文件编码、JSON 或来源口径被破坏，无法可靠复核。 | 任意阶段 |

## 2. rule_match_reason

| reason_code | 含义 | 适用 |
|---|---|---|
| `blocked_by_missing_candidate_universe` | 缺候选元数据，无法识别真实股票。 | Gate 0 |
| `blocked_by_missing_universe_fields` | 元数据关键字段不完整。 | Gate 0 |
| `blocked_by_missing_industry_label` | 缺行业标签，无法进入结构样本。 | Gate 1 |
| `blocked_by_missing_daily_window` | 缺日线窗口，无法运行 MALF。 | Gate 1 |
| `blocked_by_invalid_daily_window` | 日线窗口质量不合格。 | Gate 1 |
| `blocked_by_missing_malf_snapshot` | 缺 MALF 快照，无法进入前置过滤器。 | Gate 2 |
| `blocked_by_malf_snapshot_not_ready` | MALF 快照未 ready。 | Gate 2 |
| `blocked_by_unknown_malf_background` | MALF 背景仍为 `unknown`。 | Gate 2 |
| `blocked_by_source_disruption` | 资料或口径扰动阻断判定。 | Gate 2 |
| `matched_q_alive_clean` | 匹配 `Q-ALIVE-CLEAN`。 | Gate 2 |
| `matched_q_alive_pm_mixed` | 匹配 `Q-ALIVE-PM-MIXED`。 | Gate 2 |
| `matched_q_pressure_adjust` | 匹配 `Q-PRESSURE-ADJUST`。 | Gate 2 |
| `matched_q_lock_candidate` | 匹配 `Q-LOCK-CANDIDATE`。 | Gate 2 |
| `matched_q_lock_wait` | 匹配 `Q-LOCK-WAIT`。 | Gate 2 |
| `matched_q_clear_reset` | 匹配 `Q-CLEAR-RESET`。 | Gate 2 |
| `matched_q_no_trade` | 匹配 `Q-NO-TRADE`。 | Gate 2 |
| `matched_q_seed_after_clear` | 匹配 `Q-SEED-AFTER-CLEAR`。 | Gate 2 |
| `matched_q_source_disrupted` | 匹配 `Q-SOURCE-DISRUPTED`。 | Gate 2 |
| `matched_nm_no_structure` | 匹配 `NM-NO-STRUCTURE` 反例类型。 | Gate 2 |

## 3. applicability_reason

| reason_code | 含义 | 对 `tachibana_applicability` 的影响 |
|---|---|---|
| `no_stock_metadata` | 缺股票元数据。 | `unknown` |
| `no_industry_label` | 缺行业标签。 | `unknown` |
| `no_daily_window` | 缺日线窗口。 | `unknown` |
| `no_ready_malf_snapshot` | 缺 ready MALF 快照。 | `unknown` |
| `no_qualification_rule` | 无横向矩阵规则支撑。 | `unknown` |
| `source_disrupted_keep_unknown` | 资料扰动，保持 unknown。 | `unknown` |
| `structure_clean_alive_wave` | 结构为清晰有向推进。 | `suitable` 候选 |
| `structure_alive_but_pm_required` | 结构有意义，但需要 PM 承接。 | `conditional` |
| `structure_lock_candidate_pm_required` | 双侧库存或锁单候选，需要 PM。 | `conditional` |
| `structure_clear_reset_pm_required` | 清零/重启段，需要 PM。 | `conditional` |
| `structure_no_trade_not_range` | 无交易不等于 range，需保守。 | `conditional / unknown` |
| `structure_unsuitable_for_tachibana_rhythm` | 明确不适合立花仓位节奏。 | `unsuitable` |
| `rhythm_meaning_meaningful` | 结构状态下仓位节奏有明确讨论意义。 | `suitable` 候选 |
| `rhythm_meaning_limited` | 结构状态有讨论价值但受 PM 或证据限制。 | `conditional` |
| `rhythm_meaning_not_meaningful` | 结构状态不适合立花仓位节奏。 | `unsuitable` |
| `rhythm_meaning_unknown` | 无法判断仓位节奏意义。 | `unknown` |
| `negative_type_nm_no_structure` | MALF ready 但无可讨论结构对象。 | `unsuitable` |
| `negative_type_nm_no_rhythm_object` | 有波动但无可复核仓位节奏对象。 | `unsuitable` |
| `negative_type_nm_noise_dominated` | 结构噪声主导且数据质量 ready。 | `unsuitable` |

## 4. boundary_warning

| reason_code | 含义 |
|---|---|
| `do_not_upgrade_without_malf_snapshot` | 没有 MALF 快照不得升级。 |
| `do_not_upgrade_ready_snapshot_without_front_filter` | ready MALF 快照仍不得绕过前置过滤器升级。 |
| `do_not_use_manual_stock_pick_as_structure_qualification` | 人工挑股不能替代结构资格。 |
| `do_not_treat_liquidity_as_structure` | 流动性不能替代结构。 |
| `do_not_use_industry_hot_score_as_structure_evidence` | 行业热度不能替代结构证据。 |
| `do_not_mix_board_constraints_with_structure_qualification` | 板块/制度约束不能混入结构资格。 |
| `do_not_mix_unit_change_ex_rights_and_structure_qualification` | 交易单位、除权或资料口径扰动不能混入结构资格。 |
| `do_not_infer_position_size_from_malf` | MALF 不输出手数。 |
| `do_not_call_mother_position_from_malf_only` | 母单/中心单不能只由 MALF 确认。 |
| `do_not_confirm_lock_from_dual_inventory_only` | 双侧库存不能直接确认为锁单。 |
| `do_not_net_dual_inventory_into_single_direction` | 双侧库存不得净额化为单方向。 |
| `do_not_merge_pressure_adjustment_into_clean_wave` | 压力调整不能升格成干净推进。 |
| `do_not_merge_new_seed_into_old_segment` | 清零后新试探不得并回旧段。 |
| `do_not_encode_clear_reason_in_malf` | 清仓原因不得写回 MALF。 |
| `do_not_infer_range_from_no_trade` | 无交易不等于 range。 |
| `do_not_treat_addon_scale_as_structure_strength` | 加码尺度不是结构强度。 |
| `do_not_convert_applicability_to_signal_accept` | `tachibana_applicability` 不是 Signal accept。 |
| `do_not_convert_rhythm_meaning_to_signal_accept` | `rhythm_meaning` 不是 Signal accept。 |
| `do_not_generate_trade_from_rhythm_meaning_only` | 不能只凭节奏意义生成买卖或回测成交。 |

## 5. next_action

| action_code | 含义 | 允许阶段 |
|---|---|---|
| `action:repair_data` | 回到数据接入修复。 | `unknown / universe_candidate` |
| `action:complete_industry_and_daily_window` | 补行业标签与日线窗口。 | `universe_candidate` |
| `action:run_malf_snapshot` | 运行或生成 MALF 快照。 | `structure_candidate` |
| `action:run_front_filter` | 运行 MALF-立花前置认知过滤器。 | `structure_candidate` |
| `action:rerun_malf` | 重新运行 MALF。 | `structure_candidate` |
| `action:fill_qualification_record` | 填写单窗口判定底稿。 | `structure_candidate / tachibana_candidate` |
| `action:fill_candidate_table` | 更新候选样本表。 | `tachibana_candidate` 或已通过低阶 Gate 的记录 |
| `action:method_pm_review` | 进入 Method / PM 讨论。 | `tachibana_candidate` |
| `action:research_audit_only` | 只保留研究审计。 | `unknown / unsuitable` |
| `action:keep_pending` | 保持待填。 | 任意阻断态 |

`next_action` 不能写成买入、卖出、加仓、减仓、清仓或制度执行动作。

## 6. 禁止理由码

| 禁止写法 | 原因 |
|---|---|
| `buy_signal_*` | 结构资格不是买卖信号。 |
| `sell_signal_*` | 结构资格不是买卖信号。 |
| `trade_accept_*` | 不能把适用性改写为 Signal。 |
| `trade_accept_from_rhythm_*` | 不能把 `rhythm_meaning` 改写为交易接受。 |
| `trade_reject_from_rhythm_*` | 不能把 `rhythm_meaning` 改写为交易拒绝。 |
| `signal_decision_from_rhythm_*` | 不能从节奏意义直接生成 Signal 决策。 |
| `backtest_execution_from_unknown_rhythm_*` | `unknown` 节奏意义只能进入审计或补证，不能进入成交回测。 |
| `target_position_*` | 目标仓位属于 PM / 执行层。 |
| `t1_action_*` | T+1 是制度执行约束，后置。 |
| `limit_up_strategy_*` | 涨跌停策略不是结构资格。 |
| `industry_hot_buy_*` | 行业热度不能生成结构资格。 |

## 当前 pending 记录覆盖

| sample_id | 已使用理由码 | 覆盖状态 |
|---|---|---|
| `ASHARE-PENDING-001` | `missing_candidate_universe`、`missing_sw_industry_membership`、`missing_daily_window`、`missing_malf_snapshot`、`blocked_by_missing_candidate_universe`、`blocked_by_missing_malf_snapshot`、`no_stock_metadata`、`no_industry_label`、`no_daily_window`、`no_ready_malf_snapshot`。 | 已覆盖。 |
| `ASHARE-PENDING-002` | `missing_daily_window`、`missing_malf_snapshot`、`blocked_by_missing_daily_window`、`blocked_by_missing_malf_snapshot`、`no_daily_window`、`no_ready_malf_snapshot`。 | 已覆盖。 |
| `ASHARE-PENDING-003` | `missing_board_type`、`missing_st_flag`、`missing_new_stock_window`、`missing_industry_label`、`blocked_by_missing_universe_fields`、`blocked_by_missing_industry_label`、`no_board_type`、`no_st_flag`、`no_new_stock_window`、`no_industry_label`。 | 已覆盖；`no_board_type/no_st_flag/no_new_stock_window` 作为补充兼容码保留。 |

## 补充兼容码

| reason_code | 含义 | 用途 |
|---|---|---|
| `no_board_type` | 缺板块字段。 | `applicability_reason` |
| `no_st_flag` | 缺 ST 标记。 | `applicability_reason` |
| `no_new_stock_window` | 缺新股窗口标记。 | `applicability_reason` |

## 当前结论

- 本理由码表统一 A 股结构资格判定记录的理由写法。
- 它只服务结构资格、证据链和前置过滤器，不服务交易执行。
- 后续真实 A 股样本必须优先使用本理由码表；新增理由码应先进入本表，再写入判定底稿。
