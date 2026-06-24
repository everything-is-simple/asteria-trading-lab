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
6. [docs/tachibana/index/Tachibana-Method-雏形.md](docs/tachibana/index/Tachibana-Method-%E9%9B%8F%E5%BD%A2.md)
7. [docs/tachibana/index/Tachibana-Position-Management-雏形.md](docs/tachibana/index/Tachibana-Position-Management-%E9%9B%8F%E5%BD%A2.md)
8. [docs/backtest-spec/original-tachibana-method-v0.1.md](docs/backtest-spec/original-tachibana-method-v0.1.md)
9. [docs/backtest-spec/original-tachibana-v0.1-statistics-report.md](docs/backtest-spec/original-tachibana-v0.1-statistics-report.md)
10. [docs/backtest-spec/original-tachibana-v0.1-performance-report.md](docs/backtest-spec/original-tachibana-v0.1-performance-report.md)
11. [docs/backtest-spec/original-tachibana-v0.1-major-trades-report.md](docs/backtest-spec/original-tachibana-v0.1-major-trades-report.md)
12. [docs/backtest-spec/original-tachibana-v0.1-source-data-audit.md](docs/backtest-spec/original-tachibana-v0.1-source-data-audit.md)
13. [docs/tachibana/index/Tachibana-A股适配版-雏形.md](docs/tachibana/index/Tachibana-A%E8%82%A1%E9%80%82%E9%85%8D%E7%89%88-%E9%9B%8F%E5%BD%A2.md)

## 当前状态

- `1975`：全年研究主线已较完整
- `1976`：全年事实骨架已建立，`1976-03/04/05/10/11/12` 已部分精读
- 近期目标：原始立花法回测规格
- 远期目标：A 股适配版与回测报告

## 目录说明

- `docs/tachibana/`：立花方法研究主线
- `docs/a-share/`：A 股规则与适配定义
- `docs/backtest-spec/`：回测规格与证据裁决
- `docs/malf/`：MALF 入口与后续承接
- `data/pioneer-1975-1976/`：月度 JSON 与 24 张交易谱截图
- `research/sources/`：未纳入仓库的大体量原始资料说明
- `src/`：后续回测代码与解析器实现
