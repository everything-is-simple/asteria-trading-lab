# Planned-Event Price Limit Relation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` (recommended) or `superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 把 `price_limit_event_relation_*` 以最小改动路径挂到现有 `price_limit_event_evidence_*` 附近，让 `open_center` 与 `add_on` 使用统一的 planned-event relation schema，并保持规则后置、CSV 契约不扩张。

**Architecture:** 延续 `src/ashare_intake_validator.py` 当前 `execution constraint snapshot -> execution policy candidate` 的只读审计链路，在 snapshot 层新增 relation facts，在 candidate 层优先消费 relation status。保留现有 `price_limit_event_evidence_*` 作为粗粒度前置事实层，不新建独立制度主表，不回写 `institution_facts-v0.1`。

**Tech Stack:** PowerShell, Python 3.11, `unittest`, 现有 `ashare_intake_validator.py` CLI 与只读审计约束。

---

## 文件结构

**需要修改**
- `src/ashare_intake_validator.py`
- `tests/test_ashare_intake_validator.py`
- `docs/daily-status/2026-06-28.md`
- `docs/tachibana/execution-feasibility-verdicts/first-batch-v0.1/README.md`
- `docs/tachibana/execution-policy-research-agenda/first-batch-v0.1/README.md`

**已存在、作为设计输入**
- `docs/tachibana/index/Tachibana-A股-price_limit-研究问题拆解清单-v0.1.md`
- `docs/tachibana/index/Tachibana-A股-planned-event-price_limit-关系事实最小草案-v0.1.md`

## 输出契约

### Snapshot 层新增字段

```python
{
    "price_limit_event_relation_status": "relation_clear",
    "price_limit_event_fill_blocking_status": "no_explicit_fill_blocking_fact",
    "price_limit_event_limit_proximity": "not_applicable",
    "price_limit_event_relation_reason": [
        "planned_event_has_no_explicit_price_limit_blocking_fact"
    ],
    "price_limit_event_relation_ref": [
        "ASHARE-CONSTRAINT-000001.SZ-2026-04-03-v0.1"
    ],
}
```

### 枚举固定值

```python
RELATION_STATUSES = {
    "relation_clear",
    "relation_constrained",
    "relation_blocked",
    "relation_unknown",
}

FILL_BLOCKING_STATUSES = {
    "no_explicit_fill_blocking_fact",
    "explicit_fill_blocking_fact",
    "fill_blocking_unknown",
    "not_applicable",
}

LIMIT_PROXIMITY_STATUSES = {
    "not_near_limit",
    "near_limit",
    "at_limit",
    "proximity_unknown",
    "not_applicable",
}
```

### Candidate 层 price_limit 口径

```python
if relation_status in {"relation_clear", "relation_constrained"}:
    candidate_status = "review_required"
else:
    candidate_status = "evidence_incomplete"
```

## 执行清单

- [ ] Task 1: 写 relation 层失败测试
- [ ] Task 2: 在 snapshot 层新增 relation helper
- [ ] Task 3: 让 candidate 层优先消费 relation status
- [ ] Task 4: 做最小文档同步
- [ ] 总验证通过
- [ ] 提交与推送

## 完成判定

- [ ] `price_limit_event_relation_*` 已挂到现有 `price_limit_event_evidence_*` 附近，而不是新建独立制度主表。
- [ ] `open_center` 与 `add_on` 使用同一组字段表达差异。
- [ ] `price_limit` candidate 已优先消费 relation status。
- [ ] `close_limit_status / touched_limit_status` 仍未进入最小字段集，只保留为升级条件。
- [ ] 文档、测试、代码三处口径一致。
