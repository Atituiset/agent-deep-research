# 第12章 精深学习路径：四阶段动手路线

> 这不是"速成打卡计划"，而是一条**论文 × 源码 × 实现**三位一体的精深路线。每个 Lab 都能在本书对应章节找到骨架与验收标准；每个源码锚点都真实可跳转。走完约 12–14 周，产出是一个可演示的 Agent + 一套自己的技术判断力。

## 本章图谱

```
Stage A 奠基(2周)      Stage B 核心组件(4周)     Stage C 生产化(4周)      Stage D 前沿与产出(持续)
─────────────         ────────────────         ────────────────        ──────────────
Transformer/BPE       ReAct→Reflexion→          Event Sourcing/Dapper    CAMEL→AutoGen→
成本模型              SWE-agent lineage         Prompt Injection/OWASP   LangGraph lineage
最小闭环 Lab1-2       Toolformer→Gorilla→MCP    SWE-bench/Tau-bench      memorywire/PRM
读 Pi+Qwen-Agent      MemGPT/A-MEM/FadeMem      读 Claude/Codex/Grok     Capstone: 自建
源码                  读 Claude/Codex 源码      深度                     Agent+写书评
Lab3-6               Lab7/10/11                多Agent/评测前沿
```

## 12.1 学习原则

1. **三位一体**：每学一个组件，必须同时完成——读 1–2 篇源头论文、走读 ≥2 家实现、动手改自己的 Lab 代码。三者缺一，知识就是悬空的。
2. **从最简到最强**：先读懂 Pi 的 200 行 `runLoop` 与 Qwen-Agent 的库形态（`agent.py:31`），再看 Claude/Codex 的生产增强——知道"哪些复杂度是本质的，哪些是工程债"。
3. **以反例驱动**：每章的 `> 反例` 与失败案例优先于成功路径。能说清"为什么不行"才算懂了"为什么行"。
4. **产出可验收**：每个 Stage 结束有硬性 checklist；不达标不进入下一阶段。
5. **写作即学习**：Stage D 要求输出公开文章或书评——把七家对比讲给别人听，是检验理解的唯一标准。

## 12.2 Stage A：奠基期（约 2 周）

**目标**：跑通最小闭环；建立 token 成本直觉；能用两套代码风格（TS 库 / Python 框架）写出 hello-world Agent。

| 维度 | 内容 |
|------|------|
| 论文 | Attention Is All You Need (arXiv:1706.03762)；BPE/SentencePiece 原理；ReAct (arXiv:2210.03629) 只读 abstract+图1 建立 Loop 直觉 |
| 源码 | Pi `packages/agent/src/{types,agent}.ts` 全读（≤300 行）；Qwen-Agent `qwen_agent/agent.py` 全读（269 行）——两种语言的最简形态 |
| Lab | **Lab 1**：200 行 TS 最小闭环（Ch2.4 骨架，hop≤25，read/write/bash 三工具）；**Lab 2**：chars/4 vs tiktoken 误差表 + 20 轮对话成本模型（Ch5.2 数据可对照） |
| 验收 | [ ] 能白板手写 runLoop 并指出 3 个闸的位置；[ ] 能解释 Qwen-Agent 为何 deepcopy messages（`agent.py:91`）；[ ] 成本模型误差 <20% |

**常见坑**：直接上 Claude/Codex 源码会被三层嵌套劝退——务必先吃透两个"教学级"实现。

## 12.3 Stage B：核心组件期（约 4 周）

**目标**：Loop/Tools/Context/Memory 四大件的论文脉络与生产实现全部打通，完成对应 Lab。

### Week 3–4: Loop 与 Tools

| 维度 | 内容 |
|------|------|
| 论文 | Reflexion (arXiv:2303.11366)；CodeAct (ICML 2024)；Toolformer (arXiv:2302.04761)；Gorilla (arXiv:2305.15334)；Function Calling 技术报告（OpenAI 2023-06 / Anthropic 2024）；MCP 规范（2024-11）。**先读本书逐篇精读建立框架**：Ch3 §3.1.2（Loop 六篇）、Ch4 §4.1.2（工具六篇），再回原文对照 |
| 源码 | Claude `src/query.ts:219`（只看三层嵌套骨架）+ `src/Tool.ts:362`；Codex `turn.rs:153` 骨架 + `spec_plan.rs:117` build_tool_router；DeepSeek `inbox.ts` 打断语义；Qwen-Agent `fncall_agent.py:73` 计数器循环（对照组） |
| Lab | **Lab 3**（Ch3）：while→FSM 改造 + Inbox.splice 打断；**Lab 4**（Ch4）：ToolExposure{Direct,Deferred} 分级 + 横切权限 |
| 验收 | [ ] 能画 DeepSeek Phase 状态机并说出 wakingAfterAbort 解决什么；(2) 能解释 Codex 每 StepContext 重建 ToolRouter 的动机；(3) Lab4 首轮 schema tokens 下降 >50% |

### Week 5–6: Context 与 Memory

| 维度 | 内容 |
|------|------|
| 论文 | Lost in the Middle (arXiv:2307.03172)；RULER (arXiv:2404.06654)；MemGPT (arXiv:2310.08560)；A-MEM (NeurIPS 2025)；FadeMem (2026)；Prompt Caching 技术博客（Anthropic 2024-08）。精读入口：Ch5 §5.1.3、Ch6 §6.1.3（含 MemGPT/A-MEM 核心图复述） |
| 源码 | Claude `autoCompact.ts:62` + `compact.ts:387` 四层防线全读；Grok `compaction.rs` CompactionPolicy + two_pass；Codex `context_manager/history.rs:93` for_prompt 投影；Qwen-Agent `memory/memory.py:32` RAG-as-Memory（对照范式） |
| Lab | **Lab 5**（Ch5）：chars/4 + window-13K 触发 + 结构化摘要；**Lab M**（Ch6）：120 行最小 Zettelkasten（Note/Link/Evolution/Retrieve 四阶段 + 衰减函数） |
| 验收 | [ ] 能推导 T=W-R-B 并算出 Opus 200K 的三档阈值；(2) 能复述四层压缩各自删什么、为什么顺序不可换；(3) Zettelkasten demo 能演示"写入时建链"与检索增益 |

**常见坑**：Memory 章的论文容易读成综述笔记——强制自己给每个范式写一句"它在八家里对应的代码在哪"，对不上就说明没懂。

## 12.4 Stage C：生产化期（约 4 周）

**目标**：Session/Trace/安全三大工程件达到"能给团队做技术分享"的水平。

### Week 7–8: Session 与持久化

| 维度 | 内容 |
|------|------|
| 论文/经典 | Event Sourcing (Fowler 2005)；Dapper (2010)；设计数据密集型应用 Ch3/Ch7（WAL/CRDT 选读）；Redux 时间旅行调试思想 |
| 源码 | Grok `xai-chat-state/src/persistence.rs` + journal 双轨；Claude `sessionStorage.ts` 预写+防抖+逆序读；OpenCode `session.ts:693` fork idMap；Pi storage 包 branch/navigation |
| Lab | **Lab 7**（Ch7）：append-only Session + kill -9 恢复 + repair + fork |
| 验收 | [ ] 三种 turn 边界方案能各自说一个失效场景；(2) Lab7 通过全部三项验收含崩溃恢复 |

### Week 9: 可观测与评测

| 维度 | 内容 |
|------|------|
| 论文 | SWE-bench (arXiv:2310.06770)；Tau-bench (arXiv:2406.12045)；MT-Bench LLM-as-Judge (arXiv:2306.05685)；Process Reward (Math-Shepherd arXiv:2312.08935)。精读入口：Ch10 §10.1（Dapper 三招 + 五大基准逐篇） |
| 源码 | Codex e2e/benchmark 目录结构；Claude promptCacheBreakDetection 思路；Grok UsageLedger live/cumulative 分账 |
| Lab | **Lab 10**（Ch10）：三层 Trace + 成本分账 + cache_break 告警 |
| 验收 | [ ] 能列出 trace 最小完备集并各配一个事故模式；(2) 成本突增排查路径演练通过 |

### Week 10: 安全与自愈

| 维度 | 内容 |
|------|------|
| 论文/标准 | Ignore Previous Prompt (arXiv:2211.09527)；Indirect PI (arXiv:2302.12173)；OWASP LLM Top10 v2(2024-11)；《Release It!》熔断器章节。精读入口：Ch11 §11.1（沙箱五十年 + 注入四篇逐篇） |
| 源码 | Codex linux-sandbox + arg0 分发；Grok SENT_BEARER_PREFIX_LEN=12 全链路；Claude 反调试细节；Claw conversation.rs 内联 authorize（反面对照）；Qwen-Agent `_call_tool` 异常转消息（软自愈） |
| Lab | **Lab 11**（Ch11）：Gatekeeper 权限层 + DISPOSITION 处置表 + 启动自愈 |
| 验收 | [ ] 注入测试用例：webfetch 恶意页面 → deny 且有审计事件；(2) 429 重试间隔符合 retryAfterMs |

## 12.5 Stage D：前沿与产出期（持续）

**目标**：形成自己的技术观点并公开输出；跟踪三个前沿信号。

1. **多 Agent 实战**（Week 11+）：读 CAMEL/MetaGPT/AutoGen lineage（逐篇精读见 Ch9 §9.1.2，实证清算与拓扑选型见 Ch9 §9.1.2 末节 + §9.1.4）→ 完成 **Lab 9**（Ch9.6）：TodoWrite + 单子 Agent → Orchestrator-Worker → worktree 并行写验证无冲突；
2. **Capstone 二选一**：
   - **工程向**：把 Lab1–11 整合为一个开源 mini-agent（目标 2000 行内），README 里用本书的六件套模型讲解设计；
   - **研究向**：选一个未来方向（Ch5b.5 Federated Memory / Ch11.5 Policy-as-code），写一篇带实验的深度文章；
3. **跟踪信号清单**（每月 30 分钟）：memorywire 标准进展、OTel GenAI 语义约定、各家 release notes 中 compact/subagent 相关变更；
4. **验收**：[ ] 公开输出 ≥1 篇长文并获得有效反馈；(2) mini-agent 或研究文章可被陌生人独立跑通/读完。

## 12.6 全书 Lab 地图

| Lab | 章节 | 依赖 | 核心能力 |
|-----|------|------|---------|
| Lab 1 最小闭环 | Ch2.4 | — | 六件套体感 |
| Lab 2 成本模型 | Ch5.2 | Lab1 | token 经济学 |
| Lab 3 FSM+Inbox | Ch3 | Lab1 | 循环与打断 |
| Lab 4 工具分级 | Ch4 | Lab1 | schema 预算/权限横切 |
| Lab 5 压缩管线 | Ch5 | Lab2 | 四层防线 |
| Lab M Zettelkasten | Ch6 | Lab5 | 写入时代理记忆 |
| Lab 7 Session | Ch7 | Lab1 | 可重放/自愈/fork |
| Lab 9 Orchestrator | Ch9 | Lab3/4 | 多 Agent 编排 |
| Lab 10 Trace 分账 | Ch10 | Lab7 | 可观测/成本归因 |
| Lab 11 安全三件套 | Ch11 | Lab4/7 | 权限/归一/自愈 |

依赖关系决定了推荐顺序：A(Lab1-2) → B(Lab3→4→5→M) → C(Lab7→10→11) → D(Lab9→Capstone)。

## 12.7 能力自评雷达与每周节奏

```
            精深(5)                    入门(1)
Loop 设计      ●━━━━━━━ 能手写 FSM+打断语义 ━━━ 只会 while
Tools 系统     ●━━━━━━━ 能做 exposure 分级 ━━━ 只会注册表
Context 工程   ●━━━━━━━ 能调四层压缩参数   ━━━ 只会截断
Memory 架构    ●━━━━━━━ 能选范式并落地     ━━━ 只知道向量库
Session/Trace  ●━━━━━━━ 能设计分账与恢复   ━━━ 只存 json 数组
安全纵深       ●━━━━━━━ 能写策略+沙箱选型  ━━━ 无权限层
多 Agent       ●━━━━━━━ 能编排+隔离        ━━━ 单 agent
```

**每周节奏建议**：工作日每天 45 分钟（论文 2 天 + 源码 2 天 + Lab 1 天），周末 3 小时整块（Lab 冲刺 + 笔记）。每个 Stage 结束写一篇 500 字小结发在个人笔记/博客——三个月后回看，进步曲线本身就是最好的激励。

> 学完本章路线，你收获的不只是"会用 Agent"，而是**能设计 Agent Infra 的判断力**——这正是各家仓库最值钱的部分。
