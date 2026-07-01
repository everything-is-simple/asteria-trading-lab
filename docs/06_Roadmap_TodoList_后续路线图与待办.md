# 06_Roadmap_TodoList — 后续路线图与待办

**版本**: v0.8
**日期**: 2026-07-01
**当前基线**: `candidate_table_trading_layer_readiness_audit_passed`
**文档性质**: 未来待办、路线图与优先级安排

## 1. 当前基线

本路线图从以下已发生状态开始：

- 资格记录审计链路已推进到 `formal_record_ready_for_persistence`。
- 已准备 `qualification_record_persistence_package`。
- 已完成 P4a：在临时/staging 目录验证资格记录真实文件 IO。
- 已完成 M1：`prepare_candidate_table_update_audit_when_explicitly_requested`。
- 已生成 candidate table update audit package。
- 已生成 staging qualification record manifest 与 records。
- 已生成 staging candidate table draft JSONL 与 manifest。
- 已实现 P4c formal data root candidate table 写入入口，并在临时 formal data root 验证 backup 与 rollback。
- 已实现 P5 formal candidate table trading layer readiness audit。
- formal candidate table 已准备进入未来 trading layer read gate contract review。
- 真实生产路径 `Z:\asteria-trading-labs-data` 尚未执行人工确认写入。
- 尚未开放真实 trading layer read。
- 尚未开放 signal generation 或 backtest execution。

事实进度记录见：

[04_施工计划_当前进度版.md](./04_施工计划_当前进度版.md)

## 2. P0：立即修正文档分层

- [x] 保持 `04_施工计划_当前进度版.md` 只记录已经发生的进度、当前系统位置和已确认边界。
- [x] 使用本文件承接未来路线图、TodoList、急需任务和后续阶段安排。
- [x] 后续更新时，避免把“计划要做”写成“已经完成”。

## 3. M1：candidate table update audit

目标：新增显式触发入口，只做候选表更新前审计，不做真实写入。

入口：

`prepare_candidate_table_update_audit_when_explicitly_requested`

边界要求：

- [x] 输入必须来自已准备好的 `qualification_record_persistence_package`。
- [x] 输出只能是 candidate table update audit package。
- [x] 不得直接写 candidate table。
- [x] 不得开放 trading layer。
- [x] 不得产生买卖信号。
- [x] 不得执行回测。

测试要求：

- [x] pass case
- [x] blocked case
- [x] 禁用字段校验
- [x] 三道硬闸继续为 false
- [x] 不允许混入交易信号、仓位、回测字段

验证命令：

```powershell
$env:PYTHONPATH='src'
python -m unittest tests.test_tdx_local_first_batch -v
python -m unittest discover -s tests
```

## 4. P2：样本扩充

目标：继续执行 post-label 窗口重筛，补齐四类样本覆盖。

- [x] `meaningful` 样本覆盖达标。
- [x] `limited` 样本覆盖达标。
- [x] `unknown` 样本覆盖达标。
- [x] `not_meaningful` 样本覆盖达标。
- [x] 复核行业标签时间对齐，避免未来标签污染历史窗口。

当前机器审计要求四类 `rhythm_meaning` 至少各保留 2 条样本，并输出
`sample_count_by_rhythm_meaning / missing_rhythm_meanings /
undercovered_rhythm_meanings`，防止后续样本目录退化为只覆盖理由码、不覆盖四类语义。
对带有 `sample_window_end / current_industry_valid_from` 的样本行，机器审计会阻断
`current_industry_valid_from > sample_window_end` 的未来行业标签污染。

边界：

- 样本扩充仍属于研究审计。
- 样本扩充不等于交易许可。
- 样本扩充不开放回测。

## 5. P3：制度研究准备层收口

目标：整理 `execution_policy_research_agenda` 的制度研究素材。

- [x] 整理 `t1` 研究材料。
- [x] 整理 `price_limit` 研究材料。
- [x] 整理 `suspension_resume` 研究材料。
- [x] 输出制度研究收口报告。

收口报告：

[Tachibana-A股制度研究准备层收口报告-v0.1.md](./tachibana/index/Tachibana-A股制度研究准备层收口报告-v0.1.md)

边界：

- 该阶段仍是研究准备。
- 该阶段不定义交易规则。
- 该阶段不生成交易信号。

## 6. P4：真实持久化与候选表写入

启动条件：

- P1 candidate table update audit 已通过。
- persistence package 与真实写入语义已经完全分离。
- 目标写入路径、临时目录、原子替换策略明确。

设计规格：

[2026-06-30-p4-persistence-and-candidate-table-design.md](./superpowers/specs/2026-06-30-p4-persistence-and-candidate-table-design.md)

[2026-06-30-p4b-candidate-table-update-design.md](./superpowers/specs/2026-06-30-p4b-candidate-table-update-design.md)

[2026-06-30-p4c-formal-candidate-table-write-design.md](./superpowers/specs/2026-06-30-p4c-formal-candidate-table-write-design.md)

待办：

- [x] 设计真实持久化写入入口。
- [x] 设计 candidate table 更新入口。
- [x] 先在临时目录验证真实文件 IO。
- [x] 再讨论是否写入正式 `data_root`（P4c 设计规格已完成）。
- [x] 实现 explicit formal data root candidate table writer，并用临时 formal data root 验证 backup / rollback。

P4c 已完成项：

- 入口：`write_candidate_table_to_formal_data_root_when_explicitly_confirmed`
- 正式路径：`Z:\asteria-trading-labs-data\ashare\candidate-table-v0.1\candidate-table.jsonl` + `manifest.json`
- 格式：JSONL
- 人工 gate：`confirm_formal_write=True` 必须显式传入；否则立即 block
- Rollback：完整回滚，不留残件；旧正式目录写入前自动备份到 `candidate-table-v0.1.backup.<ISO8601>/`
- Trading layer：P4c 完成后仍关闭；另走 P5 独立审计才能开放
- 验证：`tests.test_tdx_local_first_batch` 覆盖 pass / blocked-no-confirm / blocked-bad-manifest / forbidden-field / rollback。
- 边界：本轮未对真实生产路径 `Z:\asteria-trading-labs-data` 执行人工确认写入。

P4a 已完成项：

- 入口：`write_qualification_records_to_staging_when_explicitly_requested`
- 输出：`qualification-records-v0.1/records/<qualification_record_id>.json`
- 输出：`qualification-records-v0.1/manifest.json`
- 边界：只写调用方传入的 staging root，不写正式 `data_root`。
- 边界：`candidate_table_update_performed=False`，`candidate_table_update_allowed=False`，trading layer、signal、backtest 继续关闭。

P4b 已完成设计：

- 入口：`update_candidate_table_from_staged_qualification_records_when_explicitly_requested`
- 推荐格式：`candidate-table-draft.jsonl` + `manifest.json`
- 推荐路径：调用方传入的 candidate table staging root。
- merge key：`qualification_record_id`
- 重复处理：同一 manifest 内重复 key 阻断；既有 staging 表同 key 不一致时阻断。
- rollback：先写临时目录，完成后替换，manifest 最后可见。
- 边界：P4b staging 实现已完成，尚未真实更新正式 `data_root` candidate table。
- 验证：`tests.test_tdx_local_first_batch` 覆盖 pass / blocked manifest / forbidden field / duplicate key / idempotent rewrite。

## 7. P5：trading layer readiness audit

启动条件：

- P3 制度研究准备层已收口。
- P4 持久化与候选表写入路径已稳定。
- P4c formal candidate table writer 已完成；trading layer 仍需独立审计后才能读取。

已完成：

- [x] 设计 `audit_trading_layer_readiness_for_candidate_table_when_explicitly_requested`。
- [x] 审计 formal candidate table manifest 与 JSONL 内容。
- [x] 验证 missing manifest / missing JSONL / malformed JSONL / forbidden fields / downstream gates。
- [x] 确认 institution rule definition readiness 仍未开放时，继续 block trading layer read。
- [x] 明确 P5 pass 只表示 `ready_for_trading_layer_read_gate_review`。
- [x] 明确 P5 不生成 signal、不生成仓位、不运行 backtest、不定义正式制度规则。

规格与计划：

[2026-07-01-p5-trading-layer-readiness-audit-design.md](./superpowers/specs/2026-07-01-p5-trading-layer-readiness-audit-design.md)

[2026-07-01-p5-trading-layer-readiness-audit.md](./superpowers/plans/2026-07-01-p5-trading-layer-readiness-audit.md)

当前边界：

- `institution_rule_definition_allowed=False`
- `trading_layer_read_allowed=False`
- `signal_generation_allowed=False`
- `backtest_execution_allowed=False`

## 8. P6：trading layer read gate / consumer contract

启动条件：

- P5 trading layer readiness audit 已通过。
- formal candidate table manifest / JSONL 已证明结构可读。
- Method/PM、Backtest Input、execution constraint / verdict 的只读消费边界需要先设计清楚。

待办：

- [ ] 设计 P6 read gate contract 规格。
- [ ] 明确 trading layer read gate 可以读取哪些 artifact。
- [ ] 明确缺 Method/PM plan 时如何 blocked。
- [ ] 明确缺 Backtest Input gate 时如何 blocked。
- [ ] 明确 execution constraint snapshot 与 execution feasibility verdict 如何作为只读输入。
- [ ] 明确 candidate table readiness audit 如何作为前置证明。
- [ ] 明确 P6 第一版是否仍保持 `trading_layer_read_allowed=false`，只推进到下一 review gate。
- [ ] 保持 signal generation 与 backtest execution 关闭。

建议规格：

[2026-07-01-p6-trading-layer-read-gate-contract-design.md](./superpowers/specs/2026-07-01-p6-trading-layer-read-gate-contract-design.md)

## 9. P7：制度规则定义

启动条件：

- P6 read gate contract 已完成规格设计。
- Method/PM 与 execution constraint/verdict 之间的只读消费关系已明确。
- 制度事实仍不被误当成交易规则。

待办：

- [ ] 起草涨跌停规则草案。
- [ ] 起草停复牌规则草案。
- [ ] 起草 T+1 相关约束草案。
- [ ] 明确规则层与 MALF 层的边界。
- [ ] 新增 pass / blocked / 禁用字段校验测试。
- [ ] 继续保持 signal 与 backtest 关闭。

## 10. P8：信号与回测

启动条件：

- 制度规则定义完成。
- trading layer read 通过独立审计。
- signal generation gate 经过显式开放审计。

待办：

- [ ] MALF 信号生成器。
- [ ] A 股完整回测引擎。
- [ ] Pioneer v0.2 回测。
- [ ] 15 笔交易段重跑与对照。

## 11. 暂不做事项

- [ ] 不启用 `--fast-research`。
- [ ] 不合并审计步骤。
- [ ] 不跳过 candidate table update audit。
- [ ] 不提前开放 trading layer read。
- [ ] 不把 P5 pass 解释成真实 trading layer read 已发生。
- [ ] 不提前实现 signal generation。
- [ ] 不提前执行 backtest。

## 12. 进度估算口径

Mistral Large 的估算可以作为路线图参考，但采用以下校准口径：

- 当前审计链路骨架：约 85% 到 90%。
- 资格记录进入候选表之前的主线：约 60% 到 70%。
- 完整可回测系统：约 40% 到 50%。

后续每完成一个 P 阶段，应同步更新本文件的勾选状态，并在 `04_施工计划_当前进度版.md` 中只记录已经真实发生的结果。
