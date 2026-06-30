# 06_Roadmap_TodoList — 后续路线图与待办

**版本**: v0.4
**日期**: 2026-06-30
**当前基线**: `candidate_table_update_audit_package_prepared`
**文档性质**: 未来待办、路线图与优先级安排

## 1. 当前基线

本路线图从以下已发生状态开始：

- 资格记录审计链路已推进到 `formal_record_ready_for_persistence`。
- 已准备 `qualification_record_persistence_package`。
- 尚未执行真实持久化写入。
- 已完成 M1：`prepare_candidate_table_update_audit_when_explicitly_requested`。
- 已生成 candidate table update audit package。
- 尚未真实更新 candidate table。
- 尚未开放 trading layer。
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

待办：

- [ ] 设计真实持久化写入入口。
- [ ] 设计 candidate table 更新入口。
- [ ] 先在临时目录验证真实文件 IO。
- [ ] 再讨论是否写入正式 `data_root`。

## 7. P5：制度规则定义

启动条件：

- P3 制度研究准备层已收口。
- P4 持久化与候选表写入路径已稳定。

待办：

- [ ] 起草涨跌停规则草案。
- [ ] 起草停复牌规则草案。
- [ ] 起草 T+1 相关约束草案。
- [ ] 明确规则层与 MALF 层的边界。

## 8. P6：信号与回测

启动条件：

- 制度规则定义完成。
- trading layer read 通过独立审计。
- signal generation gate 经过显式开放审计。

待办：

- [ ] MALF 信号生成器。
- [ ] A 股完整回测引擎。
- [ ] Pioneer v0.2 回测。
- [ ] 15 笔交易段重跑与对照。

## 9. 暂不做事项

- [ ] 不启用 `--fast-research`。
- [ ] 不合并审计步骤。
- [ ] 不跳过 candidate table update audit。
- [ ] 不提前开放 trading layer read。
- [ ] 不提前实现 signal generation。
- [ ] 不提前执行 backtest。

## 10. 进度估算口径

Mistral Large 的估算可以作为路线图参考，但采用以下校准口径：

- 当前审计链路骨架：约 85% 到 90%。
- 资格记录进入候选表之前的主线：约 60% 到 70%。
- 完整可回测系统：约 40% 到 50%。

后续每完成一个 P 阶段，应同步更新本文件的勾选状态，并在 `04_施工计划_当前进度版.md` 中只记录已经真实发生的结果。
