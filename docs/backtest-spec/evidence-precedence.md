# 回测事实裁决顺序

为了保证立花法回测的事实底座稳定，仓库内统一采用以下证据优先级：

1. `data/pioneer-1975-1976/source-images/` 下的 24 张月度交易谱截图
2. 原始月度交易谱 PDF
3. `data/pioneer-1975-1976/json/` 下的重建 JSON
4. 用户挑出的规则页组：`Z:\market-life-cycle\立花义正交易法-part1-3`
5. part4 交易谱说明页组：`Z:\market-life-cycle\立花义正交易法-part4`
6. 章节原文 PDF / 图片页
7. OCR 文本，仅作检索辅助

## 使用原则

- 月报中的逐笔交易事实，以月度截图为最高依据。
- 记录方式、下单纪律、早期交易单位、分批、锁单、母单等规则定义，以用户挑出的 part1-3 页组和章节原文页为优先依据。
- part4 交易谱说明页组用于解释 1975-1976 实战段的 `lock_purpose / mother_position / add_on / reverse_probe`，以及 1976-09-21 后 PIONEER 交易单位改为 100 股的资金口径修正。
- JSON 是结构化载体，不高于截图与月度 PDF。
- 当截图、PDF 与 JSON 不一致时，优先修正 JSON 与月报解释，不反向修改截图结论。
- OCR 文本不能单独作为规则定义或交易事实依据。
- 对 `trade_raw`、`position_raw` 的方向解释，只能标为“我们的抽象解释”，不能冒充原文。
