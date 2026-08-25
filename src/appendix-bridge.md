# 附录 C 理论卷（卷 VI）衔接与阅读路径

> 原独立仓库 `agent-infra-research` 已于 2026-08 **全量并入本书卷 VI**（`src/theory/`，T1–T7 + 附录 TA–TE），此后只需维护本仓库。理论卷不是源码卷的重写，而是其**概念底座**：两卷形成"理论 → 源码 → 实践"的闭环。

## 定位互补

| 维度 | 卷 VI 理论卷（T1–T7） | 本书源码卷（Ch1–14） |
|------|------------------------|---------------------------|
| 问题 | 为什么需要 Agent Infra（Why） | 各家怎么做的、如何选（How/Which） |
| 方法 | 论文+生态+岗位，5 角度×23 来源×92 主张→4 高置信 | 8 个代码仓 + Qwen-Agent 对照组精读，行号级锚点 |
| 产出 | 7 章综述 + 5 附录（Safety/Federated/多模态/端侧） | 14 章对比（五段式：历史→原理→对证→权衡→未来）+ 四阶段 Lab 路线 + 一页纸 |
| 读者 | 入门第一遍 | 进阶第二遍 + 查阅复习 |

## 章节对位

| 理论卷章节 | 源码卷对位 | 衔接说明 |
|--------------------|---------|---------|
| T1 全景 | Ch1 全景 + Ch2 公共模型 | 前者给六组件模型与五约束，后者给六件套心智模型与 200 行闭环 |
| T2 Memory | Ch6 Memory 深潜 | 前者讲 MemGPT/A-MEM/FadeMem 的"为什么"（含不可能三角、五问表），后者讲九家的"估算→预算→压缩→投影"怎么落地 |
| T3 Context | Ch5 Context 工程 | 前者讲 Token 经济学与摘要五类型，后者讲四层防线与 Prompt Caching 断点稳定 |
| T4 Runtime | Ch3 Loop + Ch4 Tools + Ch9 多 Agent | 前者讲 FSM vs while 与 ReAct/Plan-Execute/Multi-Agent 三模式，后者给七家三层嵌套与显式规划容器 |
| T5 Industry | Ch13 一页纸 + Ch12 路线 | 前者讲岗位信号与技能栈（ByteDance Memory Infra JD 逐句解读等独家内容），后者给可直接背诵的要点与实战路径 |
| T6 Ecosystem | Ch4 Tools(MCP) + Ch8 Model | 前者讲框架/向量/标准生态，后者讲 MCP/Skill 与多 provider 抽象 |
| T7 Roadmap | Ch12 路线 | 前者是理论驱动的 4 Phase，后者是源码驱动的四阶段实战（每周产出）；两份路线可并行使用 |

## 建议阅读顺序

```
1. T1（全景，10min） ─┐
2. T4（Runtime，20min）├─ 建立"为什么"
3. 本书 Ch2（公共模型，15min）     ─┘

4. T2/T3（Memory/Context）─┐
5. 本书 Ch5/Ch7（Context/Session）       ├─ 从理论到源码
6. 本书 Ch3/Ch4（Loop/Tools）            ─┘

7. 本书 Ch8/Ch9（Model/多Agent）── 扩展
8. T5（行业岗位）── 岗位信号
9. 本书 Ch13（一页纸）── 30min 快查
10. 本书 Ch12（学习路径）── 长期
```

## 理论到源码的 3 个"缝合点"

1. **MemGPT 的 OS 分页 → Claude 的四层防线**：论文的 `page fault/eviction` 在 `src/query.ts:219` 的 `snip/micro/collapse/autocompact` 上得到最完整的工程实现。
2. **A-MEM 的写入时代理 → Grok/DeepSeek 的 projection**：T2 的"代理权前移"在 `ChatState.estimate_item_tokens` 与 `RuntimeContextProjection.project()` 上落地为"写入时即决定如何投影"。
3. **`my-agent` 的按需检索 vs 固定检索 → ToolExposure**：T4 提出的 `ContextHygiene.sanitize_tool_output` 与 Codex 的 `ToolExposures{DIRECT/DEFERRED}` 同解"首轮 schema 预算"问题。

## 复用与引用

- 本书 Ch2 的六件套图与 Ch5 的"估算→预算→触发→压缩"链路，可作为 T1/T3 的配图补充
- 本书 Ch13 的一页纸可作为 T7 的 30 分钟快查卡
- 两卷现已同仓同构：同一 mdBook、同一 GitHub Pages、同一份审计日志（附录 D）——原独立仓库可归档
