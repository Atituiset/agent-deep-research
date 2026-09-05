# 第3章 Agent Loop 精读

> Loop 是 Agent 的"心脏"，也是各家分歧最大的组件。所有可靠性增强——重试、限流、打断、压缩、预算——最终都要落到"采样→执行→回填"这一闭合上如何编排。看懂 Loop，就看懂了 Agent 的并发模型与失败模型。

**本章目标**：读完能（1）按时间轴说清 Loop 范式从 ReAct 到 CodeAct 的五次跃迁；（2）手写三层嵌套的形式化定义与 FSM 迁移表；（3）对照各家源码锚点逐行解释"为什么这样写，不这样写会怎样"；（4）在 while / FSM / Actor 三选一时给出权衡与代价；（5）对 Speculative Loop 等四个前沿方向提出可验证的取舍假设。

**阅读方式**：配合 `appendix-sources.md` 的锚点表，建议左侧开源码、右侧读本章；每节后的 `> 反例` 与 `思考题` 用于自检是否"真懂"。

---

## 3.1 历史脉络与论文 lineage：Loop 范式如何演进

Loop 并非一开始就是"状态机"。它的演进是一条"从 Prompt 技巧 → 单体循环 → 可中断系统"的工程化路径，学术论文与开源系统交替推动。

### 3.1.1 时间轴与一句贡献

| 年份 | 论文/系统 | 会议/载体 | Loop 形态 | 一句话核心贡献 |
|------|-----------|-----------|-----------|----------------|
| 2022.10 | **ReAct** (Yao et al.) | arXiv 2210.03629 → **ICLR 2023** | `Thought → Act → Observe` 交替的纯 Prompt 循环，无工具重试与取消 | 首次把 **Reason + Act 交替**形式化为可被 LLM 执行的轨迹（trajectory），证明"边想边动"优于纯 CoT；Loop 退化为"采样一次、解析一次 `Action:`" |
| 2023.03 | **Reflexion** (Shinn et al.) | **NeurIPS 2023** | `Act → Eval → Reflect → Retry` 外层加"语言级梯度" | 用**语言自反思（verbal reflection）**作跨 trial 的记忆，Loop 从单轨迹变为`trial loop × step loop`二层嵌套；首次显式讨论"失败回填如何进下一次 prompt" |
| 2023.05 | **Voyager** (Wang et al.) | arXiv 2305.16291 → **NeurIPS 2023** | `Curriculum → CodeGen → Execute → SkillLib` 终身循环 | 把 Loop **拉长到数百步的终身学习**：自动课程（curriculum）驱动任务生成，执行失败进 Skill 库迭代；Loop 不再"一问一答"，而是持续自演进的 `open-ended loop` |
| 2023.03–04 | **AutoGPT / BabyAGI** | 开源系统（无正式会议） | `while(true){ plan → tool → memory }` 无限自主循环 | 工程上首次暴露 Loop 的**失控问题**：无 hop 上限、无取消、无预算闸，用户只能 `Ctrl-C`；反向推动后续系统补全"熔断与打断" |
| 2024.05 | **SWE-agent** (Yang et al., arXiv:2405.15793) | **NeurIPS 2024** | `Thought → Action(单一 command) → Observation` 窄 Loop + ACI | 提出 **Agent-Computer Interface (ACI)**：把"可执行动作空间"收敛到`bash + editor`，证明 Loop 的**工具集设计比模型更影响成功率**；Loop 内不做并行工具调用 |
| 2024.03 | **OpenHands** (原 OpenDevin, Xingyao Wang et al.) | arXiv 2407.16741, **ICLR 2025** submission | `EventStream(controller) → AgentDelegate → MicroAgent` 事件驱动 | 把 Loop **事件化**：所有输入均抽象为 `Event{source, message, timestamp}` 流，`Controller` 统一调度 `Agent/Tool`；首次系统化支持**多 Agent 委托**与人机共编 |
| 2024.02 | **CodeAct** (Wang et al.) | **ICML 2024** | `Code as Action`：`think → exec(python) → observe` 单一代码执行 Loop | 统一动作空间为**可执行 Python**，Loop 的工具调用从"多 JSON schema"坍缩为"单一 `exec`"，大幅降低 schema 漂移与解析失败；启发后续 Claude Code / Codex 的"代码即工具"分支 |
| 2024–2026 | **Claude Code / Codex / Grok / DeepSeek Harness / OpenCode / Pi / Claw** | 工业实现（本书七码） | 三层嵌套（见 3.2）+ 状态机/Actor + 取消语义 | 把学术 Loop **生产化**：叠加`采样重试 × 流式装配 × 预算闸 × 打断（steer/inbox）× 观测（trace/otel）`五类"闸" |

> **演进主线**：`Prompt 技巧（ReAct）→ 跨试次记忆（Reflexion）→ 终身技能库（Voyager）→ 可控执行（SWE-agent ACI / CodeAct 统一动作）→ 事件化与委托（OpenHands）→ 生产化三层嵌套 + 取消语义（各家 Harness）`。每一次跃迁都在回答：Loop 的边界往哪里扩、失败往哪里回填、谁有权在中途打断它。

### 3.1.2 逐篇精读：每篇论文如何"长出"一种 Loop 形态

上表是地图，本节是徒步。我们逐篇回答四个问题——**它反对什么（当时的困境）、它的机制怎么运作、证据是什么、给今天的 Loop 留下了什么**。读完你会发现：今天任何一家 `agent-loop.ts` 里的每一行，都能在这些论文里找到原型。

#### ReAct (2022)：Loop 的"创世纪"——边想边动

**困境**：ReAct 之前有两条路线。纯 CoT（Chain-of-Thought）让模型"先想后答"，但推理悬浮在参数记忆里——一步幻觉，步步幻觉，没有现实来纠错；纯 Act（直接生成动作）能触碰环境，但缺少推理的中间步骤，模型常常"手比脑快"，在错误的方向上一路执行到底。

**机制**：ReAct 的洞见是把两者交织成 `Thought → Action → Observation` 的循环：Thought 是模型的自我陈述（"我应该先查 X 的出生地"），Action 是对外部世界的调用（`Search[X]`），Observation 是环境返回的真实事实。整个循环用 **few-shot 示例**写进 prompt，模型本身完全冻结——不训练任何权重。所谓"Loop"，此时只是"采样一次 → 用正则解析出 `Action:` 行 → 执行 → 把 Observation 拼回 prompt → 再采样一次"的文本协议。

**证据**：论文在四类任务上验证。最直观的是 ALFWorld 文字游戏（做家务）：ReAct 成功率 71%，而纯动作基线只有 45%——差距几乎全部来自"先想再动"避免了无效操作。更重要的是错误分析：CoT 的主要失败模式是**幻觉**（编造事实且无法自纠），而 ReAct 把这类错误压到了零头——因为 Observation 提供了外部接地，错了会被环境打脸。

**遗产与局限**：今天所有 Agent 的 `messages[]` 里 `assistant(tool_call) / user(tool_result)` 的交替结构，就是 Thought-Act-Observation 的直系后代。但 ReAct 也留下了一个直到 Function Calling 出现才解决的问题：**文本协议太脆**。`Action:` 行靠正则解析，模型少个引号、多个换行就解析失败——这个痛点直接催生了 Ch4 的结构化工具调用。另外 ReAct 的 Loop 没有任何熔断：任务失败只能整条轨迹重来。

#### Reflexion (2023)：给 Loop 加"外层"——失败如何变成下一次的输入

**困境**：权重冻结的 LLM 无法从经验中学习。强化学习当然可以，但它需要奖励信号、梯度更新和海量 trial——对只买得起 API token 的开发者遥不可及。问题是：能不能只用语言，就模拟出"吃一堑长一智"？

**机制**：Reflexion 给出了被作者称为"verbal RL"的方案。它在 ReAct 的单轨迹外面套了一层 **trial 循环**，并配三个角色：**Actor**（照常执行任务，产出轨迹）、**Evaluator**（给轨迹打分——环境有奖励就用环境，没有就让 LLM 当裁判）、**Self-Reflect**（失败后生成一段自然语言的"复盘"："上次因为没先看测试文件就改代码导致编译失败，下次应该先跑 `make test`"）。这段复盘被存进一个**情景记忆缓冲区**，重试时拼进 prompt——于是第二次尝试时，模型"带着上次的经验"上场。

**证据**：在 HumanEval 上，GPT-4 基线 pass@1 约 80%，加 Reflexion 后达 91%；ALFWorld 上 134 个任务成功 130 个（约 97%）。消融实验显示去掉 Self-Reflect（只保留重试）收益大半消失——**起作用的不是重复尝试，而是失败被语言化后进入了下一次的上下文**。

**遗产与局限**：这是 Loop 从单层变两层嵌套的起源（trial loop × step loop），也是"失败要原文回填而非丢弃"这一工程铁律的学理依据——你在 Claude `src/query.ts:219` 里看到的 error tool_result 回填、stop-hook 自评，都是 Reflexion 思想的产品化。局限在于：记忆缓冲有窗口上限，反思质量依赖 Evaluator 的打分可靠性（LLM 裁判会误判），而且跨 trial 的学习无法沉淀为技能——这正是 Voyager 要解决的。

#### Voyager (2023)：把 Loop 拉成"终身"——成功也要回填

**困境**：Reflexion 解决了"失败怎么进下一轮"，但成功的经验同样被丢弃：每次任务结束，一切归零重来。开放世界（如 Minecraft）需要的是终身学习——越玩越强，而不是每个新世界从零开始。

**机制**：Voyager 用三件套把 Loop 改造成自演进的闭环。①**自动课程**：GPT-4 根据智能体当前状态（背包、位置、已解锁科技）动态提出"下一个该学的任务"，代替人工关卡；②**技能库**：每学会一件事，就把解法写成带 docstring 的可执行代码存入向量库——下次遇到类似目标，先按语义检索复用，没有才探索，学会再入库；③**迭代提示**：程序执行报错或自验证不过，就把错误信息喂回去重新生成——这本质上是把"环境反馈"细化到了代码级。关键在于技能可组合：学过"合成木镐"和"挖矿"之后，"下矿洞生存"可以直接调用两个旧技能拼接。

**证据**：同样的 GPT-4，Voyager 解锁的独特物品数是此前最强方法（ReActXtra/AutoGPT 类）的 **3.3×**，移动距离 2.3×；并且能泛化到从未见过的世界实例与新任务——说明学到的是技能而非背题。

**遗产与局限**：技能库是今天一切 "Skill 目录 / agentskills.io / defer_loading 工具"（Ch4 可见性分级、Ch9 技能系统）的思想源头——"能力以代码形式在外部累积"。局限：写入技能库的成本当时无人关心（Minecraft 不在乎 token），放到生产 Agent 里就必须回答"什么时候值得为一次使用写一个技能"，这个问题至今没有标准答案。

#### AutoGPT / BabyAGI (2023)：工程上的反面教材——失控的 while(true)

严格说这两者不是论文，而是 2023 年春引爆 GitHub 的开源项目，但它们对 Loop 工程史的贡献不可替代：它们把 ReAct 式 prompt 循环直接接上 `while(true)`，让模型自主设定子目标、无限执行——然后**当众展示了失控长什么样**。没有 hop 上限，模型陷入循环烧钱；没有取消语义，用户唯一的停止手段是 Ctrl-C 杀进程；没有预算闸，一夜烧穿 API key 的帖子层出不穷。它们的价值恰恰是**负面的**：此后所有生产实现（本书七码）里的 MAX_HOPS=25、预算闸、打断语义，都是对这个教训的直接回应。"Agent 需要的不是更聪明的模型，而是一个能踩刹车的 Harness"——这句话就是 AutoGPT 用真金白银换来的。

#### SWE-agent (2024)：接口即变量——ACI 设计学

**困境**：2024 年初，各家都发现同一个怪现象：同样的 GPT-4，换个 Agent 框架，SWE-bench 成功率差好几倍。差异从哪来？SWE-agent 团队的答案是：**Agent 与计算机之间的接口（ACI）是一个独立变量**，其重要性堪比 HCI 之于人机交互。

**机制**：SWE-agent 把动作空间收敛到 `bash + editor` 两类命令，然后在接口层内建**护栏**，而不是指望模型自律。两个代表性设计：①编辑命令要求提供"待修改文本的唯一精确匹配"，若匹配到多处则拒绝执行并报错——防止模型凭模糊印象覆盖代码；②文件查看器一次最多显示 100 行，超长截断——防止几千行日志挤爆上下文。这些护栏的共同哲学是：**让错误的动作"快速失败并得到解释性反馈"，而不是默默成功或灾难性失败**。

**证据**：发布时以 12.47% 刷新 SWE-bench 全测试集纪录。更有说服力的是消融：仅移除编辑护栏一项，成功率就掉好几个点；接口措辞的微调也能带来可观的波动——证明"成功率里相当一部分是接口设计挣来的，不是模型"。

**遗产与局限**：这是"为模型而非人写工具文档"（Anthropic 工具写作指南）的学术源头，Claude/Codex 的 edit 工具至今保留"唯一精确匹配否则报错"的护栏，就是 ACI 论文的直接落地。局限：ACI 实验基于当时的 GPT-4，模型变强后部分脚手架贬值（Ch14 交锋 A 的"Bitter Lesson vs ACI"之争）——但"接口是需要设计的独立变量"这一命题本身已被永久确立。

#### CodeAct (2024)：动作空间坍缩——万物皆可 exec

**困境**：Function Calling 之后，Agent 的动作空间是一堆 JSON schema：读文件一个 schema、搜索一个 schema……schema 一多就漂移（Ch4 的同源困境），模型要在几十种格式间切换，出错率随之上升；且工具之间传递中间结果必须经过上下文中转，多步计算笨拙。

**机制**：CodeAct 的做法激进而简单：**把全部动作坍缩为一种——可执行的 Python 代码**。想读文件？`read(path)`；想批量处理？写个 for 循环。附带一个此前没人认真利用的红利：**解释器状态跨步保留**——第一步定义的变量第二步还在内存里，中间结果无需塞回上下文。训练侧构造 CodeActInstruct 数据集微调出 CodeActAgent，评测覆盖 MINT 与 VQA/表格数学等任务。

**证据**：论文报告 CodeAct 在 MINT 任务成功率上相对传统 text/JSON 动作空间最高提升约 17%，VQA 与表格数学最高约 12%；即便不微调、纯 prompt 切换到 code action，多数场景也不劣于 JSON。工程体感更明显：解析失败率从一类常见错误趋近于零。

**遗产与局限**：这是 Claude Code "Bash-first"、Codex 统一 exec、以及各家 code mode 的思想源头——工具数量爆炸时，与其管理 N 个 schema，不如给一个图灵完备的动作空间。局限同样清晰：自由代码意味着更大的破坏半径，沙箱与超时从"可选"变成"必选"（Ch4/Ch11 的沙箱线因此被加速）；且并非所有动作都适合代码表达（审批粒度变粗了）。

#### OpenHands (2024)：Loop 的"事件化"——从拥有者变为消费者

前几篇都在改进 Loop 内部，OpenHands（原 OpenDevin）动的是 Loop 的**形态本身**。它把 Agent 运行时的全部输入——用户消息、工具结果、环境事件、代理委派——统一抽象为带时间戳的 `Event` 流，`EventStream` 作为单一事实源，`Controller` 消费事件驱动 Agent 执行，运行环境强制 Docker 沙箱。这一抽象带来三个此前难以实现的特性：**任意时刻可暂停/恢复**（状态即事件流的 fold）、**多 Agent 委托成为一等公民**（委托本身就是一条事件）、**评测平台化**（同一套 EventStream 对接 SWE-bench/AgentBench 多种 harness）。DeepSeek 的 Phase 状态机（3.2.3）与各家的 Inbox 设计，都能看到"Loop 是事件的消费者而非拥有者"这条思想的影子——当用户 steer、压缩、取消都被建模为事件时，"采样中打断"才第一次有了干净的实现路径。

### 3.1.3 三次范式位移

```
ReAct (2022)
  "怎么让模型在一步内既推理又行动"
        │
        ▼
Reflexion / Voyager (2023)
  "怎么让多步/多试次的失败变成下一次输入"
        │
        ▼
SWE-agent / CodeAct / OpenHands (2024)
  "怎么约束动作空间，让 Loop 可执行、可复现、可中断"
        │
        ▼
生产级 Loop（2024–2026，本书七码）
  "怎么在保持可中断的同时，保证流式、重试、预算、观测都不丢"
```

**位移 1 — 从"一次性采样"到"跨步记忆"**：ReAct 的 `trajectory` 仍是单次采样的副产物；Reflexion 引入 `self-reflection` 文本作为跨 `trial` 的显式状态，Voyager 进一步把"成功轨迹"固化为可复用的 `skill`。Loop 的状态 `State_t` 从`当前 prompt` 扩展为`prompt + 记忆库`。

**位移 2 — 从"自然语言动作"到"代码即动作"**：SWE-agent 用 ACI 约束 `Action ∈ {bash, edit}`，CodeAct 更激进地令 `Action = Python`。效果是**解析失败从一类错误变为几乎消失**，但要求执行侧提供沙箱与超时——这直接催生了本章后续 3.4 的"工具编排必须串行/显式并发"讨论。

**位移 3 — 从"循环体"到"调度器"**：OpenHands 的 `EventStream` 与 DeepSeek 的 `Phase` 状态机把 Loop 从`while(true)`语法提升为**可被外部事件驱动的状态机**。`user_input / tool_result / steer / cancel` 均是事件，Loop 成为事件的消费者而非拥有者。这解释了为何各产品实现最终收敛为三类形态（见 3.4.1）。

### 3.1.4 为什么要按此脉络读源码

- 读 Claude `src/query.ts:219` 的 `while(true)` 时，问自己：若无 Reflexion 的"失败回填"思想，`tool_result` 里的 `error` 为何要原文回填而非丢弃？
- 读 CodeAct 影响下的 Codex `codex-rs/core/src/tools/` 时，注意`spec() 与 handle() 同 trait`如何消解 CodeAct 之前"多 schema 漂移"的问题。
- 读 DeepSeek `packages/core/agent-loop/src/agent.ts:70` 的 `Phase`（type Phase :39） 时，对照 OpenHands 的 `EventStream`：为什么 DeepSeek 需要`maintenance`相而 Pi 不需要？答案在 3.2.3。

---

## 3.2 原理深潜：形式化、状态机与取消语义

### 3.2.1 Loop 的形式化定义

最小 Loop 是一个**带预算与取消的 Kleisli 循环**（`Message → M Message` 的重复绑定）：

```ts
// 数学形态（伪 TS，忽略错误归一）
type State = {
  session: Message[];          // 全量事实，仅 append（I1）
  context: ProjectedContext;   // 本次请求可见投影（I3）
  pending: UserInput[];        // 未消费输入（Inbox/InputQueue）
  budget: { window: number; reserve: number; used: number };
  phase: Phase;                // 见 3.2.3
};

type StepResult =
  | { kind: 'tool_calls'; calls: ToolCall[]; text: string }
  | { kind: 'text'; text: string }
  | { kind: 'blocked'; reason: string }   // 审批/沙箱拦截
  | { kind: 'error'; error: LlmError };   // 可重试/不可重试

// Loop 不变量（对应 Ch2 的 I1–I4，重述为 Loop 视角）
 // I1 Session.append 是唯一写路径 → 可重放
 // I2 Prompt 与 ToolSpecs 同快照 → 无悬垂工具调用
 // I3 Context = project(Session) → 压缩不丢血缘
 // I4 |Context| ≤ window - reserve → 否则触发 compaction 或 reactiveCompact
```

单步（`step`）与整轮（`turn`）的区分是七家的最大共识：

```
turn  := 用户一次输入 → 直到模型不再产生 tool_calls（或被打断/熔断）
step  := turn 内一次"采样→（可选）执行→回填"的原子单元
hop   := step 的别名（Claude/Pi 称 hop，DeepSeek 称 step）
```

形式化：

```
Loop(s0) =
  let s = s0
  for hop in 0..MAX_HOPS-1:
    if needsCompaction(s): s = compact(s)          // 闸1：预算
    if s.pending.nonEmpty && s.phase.canPreempt:
      s = drainPending(s)                           // 闸2：打断（steer）
    chunkStream = sampleWithRetry(s)                // 中层+内层（见 3.2.2）
    result = assemble(chunkStream)                  // BlockAssembler / StreamingToolExecutor
    match result:
      | {tool_calls} -> s = execAndRefill(s, result) // 工具编排（Ch4）
      | {text}       -> return s.withOutput(result.text)
      | {blocked}    -> s = refillBlocked(s, result); continue
      | {error}      -> if retryable(error) then continue else throw
  throw HopLimitExceeded
```

> 直觉：Loop 的"本质"是`采样→执行→回填`的闭合；"工程"是闭合上叠加的五类闸——**预算闸、重试闸、流装配闸、打断闸、观测闸**（trace/otel）。

### 3.2.2 三层嵌套：为何不是一层或两层

七家对照后可提炼为**三层**（与 `src/ch03-loop.md` 原版一致，此处形式化）：

```
┌─────────────────────────────────────────────────────────┐
│ L1 turn loop（外层，业务语义）                          │
│   职责：hop 计数、结束判定、预算检查、pending 排空      │
│   拥有：Session / Context / Inbox / Trace               │
│   熔断：MAX_HOPS(25) / shouldStopAfterTurn / needs_follow_up │
│   │                                                      │
│   ├─ L2 sampling retry loop（中层，可靠性）             │
│   │     职责：网络/限流/PTL 的整轮采样重试 + 模型降级   │
│   │     拥有：RetryPolicy / FallbackModel / LlmError 归一│
│   │     退避：指数退避 + jitter，区分 retryable vs fatal│
│   │     │                                                │
│   │     └─ L3 stream consume loop（内层，协议）         │
│   │           职责：逐块消费 SSE/Responses/ChatComp 事件 │
│   │           拥有：BlockAssembler / in_flight 累积器    │
│   │           产出：text delta / tool_use delta / completed│
│   │                                                      │
│   └─ 工具编排（横切，与 L2/L3 正交）                     │
│         approval → sandbox → execute → hook → 回填      │
└─────────────────────────────────────────────────────────┘
```

**为何必须三层**（反证法）：

- 若只有 L1（Pi 的教学形态可近似）：`fetch once → parse once`，网络抖动即整 turn 失败；流式中途取消无法以块为粒度中断；只能"全量重试"，无法做`chunk → block`的增量装配。
- 若只有 L1+L2（无 L3 装配器）：`tool_use delta` 会以不完整的 JSON 碎片进执行器，导致`InvalidArgumentsError`批量失败。Claude 的 `StreamingToolExecutor.addTool()` 与 DeepSeek 的 `BlockAssembler.push(chunk)` 正是为解决此问题。
- 若 L2 与 L3 合并：重试策略无法区分"采样前失败"（可整体重试）与"流中失败"（需按已收 `chunkSeqs` 决定是否重放或截断）。DeepSeek 的 `sourceEventSeqs` 回溯与 Claude 的 `withheld` 扣留即依赖此分层。

#### L2 的重试契约（七家归一后）

```ts
type LlmError = {
  code: 'rate_limited' | 'overloaded' | 'prompt_too_long' | 'network' | 'auth' | 'unknown';
  status?: number;
  retryAfterMs?: number;
  requestId?: string;
  retryable: boolean;
};

function normalizeLlmFailure(raw: unknown): LlmError {
  // DeepSeek: normalizeLlmFailure() 归一
  // Grok: Auth401AttributionCallback{record_401(SamplingConsumer, bearer_prefix)}
  // Codex: responses_retry.rs 指数退避 + 模型降级
  // 共识：先归一形状，再决策重试
}

async function sampleWithRetry(s: State, policy: RetryPolicy): Promise<ChunkStream> {
  for (let attempt = 0; attempt < policy.maxAttempts; attempt++) {
    try {
      return await streamOnce(s); // L3
    } catch (e) {
      const err = normalizeLlmFailure(e);
      if (!err.retryable || attempt === policy.maxAttempts - 1) throw err;
      await sleep(backoff(attempt, err.retryAfterMs));
      if (err.code === 'overloaded' && policy.fallbackModel) s = s.withModel(policy.fallbackModel);
      if (err.code === 'prompt_too_long') { await reactiveCompact(s); } // Claude reactiveCompact.ts
    }
  }
  throw new Unreachable();
}
```

#### L3 的流装配契约

```ts
// DeepSeek: packages/llm/llm/src/assembler.ts BlockAssembler
// Codex: ResponseEvent{OutputItemAdded, ToolCallInputDelta, Done}
// Claude: for await (msg of deps.callModel()) + StreamingToolExecutor
type Chunk = { seq: number; type: 'text'|'tool_use'|'reasoning'; delta: string; id?: string };
type Block = { id: string; kind: 'text'|'tool'; state: 'start'|'delta'|'end'; content: string };

class BlockAssembler {
  private inFlight = new Map<string, string>(); // id → accumulated JSON
  private seqs: number[] = [];                  // sourceEventSeqs 供回溯
  push(chunk: Chunk): Block[] {
    this.seqs.push(chunk.seq);
    if (chunk.type === 'tool_use') {
      const cur = (this.inFlight.get(chunk.id!) ?? '') + chunk.delta;
      this.inFlight.set(chunk.id!, cur);
      if (isCompleteJson(cur)) return [{ id: chunk.id!, kind: 'tool', state: 'end', content: cur }];
      return [{ id: chunk.id!, kind: 'tool', state: 'delta', content: chunk.delta }];
    }
    return [{ id: 'text', kind: 'text', state: 'delta', content: chunk.delta }];
  }
}
```

> 生产教训（Claw 的反例）：Claw `ApiClient::stream() → Vec<AssistantEvent>` 的**批量流**一次性返回整批事件，代码最短，但在 20+ hop 长链路上无法做到"边收边执行"与"中途取消"。因此七家生产级几乎一致选**增量流 + 装配器**。

### 3.2.3 状态机定义：从 `while(true)` 到 `Phase`

最简 Loop 用 `while(true)` 足够（Pi、Claude `src/query.ts:219` 的外层）；一旦需要**可中断、可恢复、可并发**，`while` 的隐式状态（`pc` 在循环体内）不足以表达"当前是否可被 steer 打断"，必须显式状态机。

#### FSM 形式化

```ts
// DeepSeek: packages/core/agent-loop/src/agent.ts:70 ReactLoopAgent（type Phase :39）
type Phase =
  | { kind: 'idle' }                                    // 无 turn 运行，可接受新输入
  | { kind: 'running'; turn: TurnState; step: StepState } // 正在 turn 内
  | { kind: 'maintenance' };                             // 压缩/初始化，不可被普通输入打断

type TurnState = { id: string; hop: number; startOffset: number };
type StepState = {
  seq: number;
  abort: AbortController;     // step 级取消令牌
  wake: { requested: boolean; afterAbort: boolean }; // 对应 wakingAfterAbort 防重入
};

// 迁移表（精简，完整版见 DeepSeek agent.ts:50 附近）
const transitions: Record<string, Phase['kind'][]> = {
  'idle → running':        ['kick() / turn() 被调用'],
  'running → maintenance': ['needsCompaction() / cancel(keepInbox=false)'],
  'maintenance → idle':    ['compact 完成 / abort 完成'],
  'running → idle':        ['turn 正常结束 / HopLimitExceeded / fatal error'],
  // 非法迁移：idle → maintenance（无 turn 何来维护）、maintenance → running（需经 idle）
};
```

#### ASCII 状态机图

```
                 kick() / turn()
          ┌─────────────────────────┐
          │                         ▼
     ┌────────┐  compact/cancel  ┌──────────┐  done/fatal  ┌────────┐
     │  idle  │ ───────────────► │maintenance│ ───────────► │  idle  │
     │        │ ◄─────────────── │          │              │        │
     └────────┘   compactDone    └──────────┘              └────────┘
        │  ▲                         │  ▲
        │  │  turnEnds               │  │ abortDone
        │  │  (completed)            │  │
        ▼  │                         ▼  │
     ┌──────────┐  step() loop   ┌──────────┐
     │ running  │ ─────────────► │ running  │
     │ turn{step}│  next-step/    │ turn{next}│
     │          │  next-turn     │          │
     └──────────┘   (Inbox.splice) └──────────┘

  子状态（running 内部）：
     step: idle → streaming(L3) → executing(tools) → refilling → next step
           │           │                │                  │
           └───────────┴────────────────┴──────────────────┘
                         任意时刻可被 Inbox.splice 打断
```

**不变量（DeepSeek 精髓）**：

- `wakingAfterAbort`：若 `abort` 后紧接着 `wakeRequested`，则该 wake 是"abort 的副作用"，不应被归类为新的 `next-turn`，否则会凭空多起一轮 turn。
- `turn_start_offset`（Grok `turn_capture.turn_start_offset`）：`idle → running` 时记录 `session.length`，`maintenance` 期间的所有追加均不计入当前 turn，便于崩溃后按 offset 重放而非逐条克隆。
- `history_version`（Codex `context_manager/history.rs:93`）：每次 `Session.append` 递增，`for_prompt()` 消费时校验，确保"压缩不丢血缘"（3.5 节的投影语义）。

#### 为何 Pi/Claude 仍用 `while`

| 场景 | 推荐形态 | 理由 |
|------|----------|------|
| 教学手写练习（200 行） | `while(true)` + `hop ≤ 25` | 心智负担最低，易验证 |
| 单 turn 无打断（批量任务） | `while(true)` + `AsyncGenerator` | 无需 `maintenance` 相 |
| 需"采样中打断"（steer） | `Phase FSM`（DeepSeek）或 `Actor`（Grok） | `while` 的 `pc` 无法表达"可抢占点" |
| 需跨进程/崩溃自愈 | `Actor`（Grok `ChatStateActor`） | 单 task 拥有状态，无锁，崩溃自愈 |

> 选型口诀：**"三问定形态"**——（1）需要采样中打断吗？（2）需要 `maintenance` 不可打断吗？（3）需要崩溃自愈吗？三问皆否则 `while`，任一是则 `FSM`，第三问是则 `Actor`。

### 3.2.4 取消语义（Cancellation）：最难的并发问题

用户在模型采样期间敲键盘输入，是 Loop 最难的并发问题。七家给出三档精度：

#### 3.2.4.1 取消的两种语义

- **协作式取消（Cooperative）**：`AbortSignal / cancellation_token` 仅在"可抢占点"检查（`stream.next()` / `tool.execute` 起点）。优点是状态一致，缺点是"正在执行的 `bash` 无法瞬间杀死"。
- **抢占式取消（Preemptive）**：`AbortController.abort()` + `sandbox kill`。优点是响应快，缺点是需处理"半写入文件"与"半累积的 `in_flight` JSON"。

生产级均为**协作 + 抢占混合**：流消费协作检查，工具执行抢占 kill（`codex-rs/core/src/tools/context.rs:56 ToolInvocation{cancellation_token, tracker}`）。

#### 3.2.4.2 Inbox / InputQueue 的精确语义（DeepSeek 最精确）

```ts
// DeepSeek: packages/core/agent/src/inbox.ts
type Target = 'next-turn' | 'next-step';
class Inbox {
  private queue: Message[] = [];
  private wake: { requested: boolean; afterAbort: boolean } = { requested: false, afterAbort: false };

  send(msg: Message)   { this.queue.push(msg); this.wake.requested = true; } // 普通输入
  steer(msg: Message)  { this.splice('next-step', msg); }  // 采样中打断，插入当前 step 末尾
  inject(msg: Message) { this.splice('next-turn', msg); } // 下一 turn 起点注入
  followup(msg: Message){ this.splice('next-turn', msg); } // 模型结束后的跟进

  splice(target: Target, ...msgs: Message[]) {
    // next-step: 追加到当前 step 的 tool_results 之后，当前 step 结束后立即消费
    // next-turn: 排到队列尾，当前 turn 结束后消费
    // 同时置位 wake.requested，供 Phase 迁移时判断
  }

  cancel(keepInbox=false) {
    if (!keepInbox) this.queue = [];
    this.abortCurrentStep(); // abort + 置 wakingAfterAbort
  }

  drain(target: Target): Message[] { /* 按 target 排空 */ }
}
```

| 家 | 机制 | 精度 | 关键文件 |
|----|------|------|----------|
| DeepSeek | `Inbox.splice(target)` + `wakeRequested / wakingAfterAbort` 闩锁 | **最高**：区分 `next-turn` vs `next-step`，防重入误分类 | `packages/core/agent/src/inbox.ts` |
| Codex | `InputQueue` + `TurnInput{UserInput\|InterAgentCommunication}` + `drain_pending_input()` | 中：每 turn 起点排空，turn 内不抢占 | `codex-rs/core/src/session/input_queue.rs:21` |
| Pi | `AgentLoopConfig.getSteeringMessages()/getFollowUpMessages()` 回调式 | 低：回调注入，无队列语义 | `packages/agent/src/agent-loop.ts:155 runLoop` |
| Claude | `withheld` 扣留 + `StreamingToolExecutor.getCompletedResults()` 并行回吐 | 中高：工具结果与 steer 合并回填，`withheld` 保证不丢 | `src/query.ts:219` + `src/services/tools/` |
| Grok | `ChatStateActor` 单 task 串行消费 `Command` | 高：Actor 串行天然无竞态，`Oneshot` 回执 | `crates/codegen/xai-chat-state/src/actor/mod.rs` |

#### 3.2.4.3 取消的时序图（DeepSeek 语义，ASCII）

```
时间 ─────────────────────────────────────────────────────────►

用户线程                Loop 线程 (running/step streaming)          工具线程
  │                              │                                    │
  ├─ type "stop" ───────────────►│                                      │
  │                              │ Inbox.steer("stop")                  │
  │                              │ splice(next-step, "stop")            │
  │                              │ wake.requested = true                │
  │                              │                                      │
  │                              ├─ stream.next() 检查 wake? ──────────►│
  │                              │  若 wake 且可抢占: abort streaming   │
  │                              │  BlockAssembler 保留已收 seqs        │
  │                              │                                      │
  │                              │  step 结束，drain(next-step)         │
  │                              │  将 "stop" 拼到 tool_results 后      │
  │                              │  重新 buildRequest（含 steer）       │
  │                              │                                      │
  │                              ├─ 下一 step 采样 ────────────────────►│
  │                              │  模型看到 steer 指令                 │
  │                              │                                      │
  │  ── 若此时再次输入 ─────────►│  wakingAfterAbort = true             │
  │                              │  该 wake 不触发新 turn               │
  │                              │  避免"abort 副作用被误判为新输入"    │
```

> 为什么需要 `wakingAfterAbort`：`cancel(keepInbox=false)` 会 `abort` 当前 step，`abort` 本身会触发一次 `wake`。若不标记`afterAbort`，Loop 会误以为用户又发了一次新消息而多起一轮 turn。DeepSeek 的`wakingAfterAbort`闩锁即为此边界而设。

#### 3.2.4.4 工具执行的取消

```rust
// Codex: codex-rs/core/src/tools/context.rs:56
pub struct ToolInvocation {
    pub cancellation_token: CancellationToken, // tokio_util::sync::CancellationToken
    pub tracker: Arc<ToolTracker>,            // 上报 is_completed / is_running
}
// 执行侧伪代码
async fn execute_tool(inv: ToolInvocation, cmd: &str) -> ToolResult {
    tokio::select! {
        res = run_bash(cmd) => res,
        _ = inv.cancellation_token.cancelled() => {
            kill_child_process().await;
            ToolResult::cancelled("steered by user")
        }
    }
}
```

Claude 的 `StreamingToolExecutor` 进一步做到"工具边收边执行"：`addTool()` 时即为每个 `tool_use` 分配 `cancellation_token`，`getCompletedResults()` 仅回吐已完成的，其余在下一次 `step` 起点以 `withheld` 扣留，避免"部分工具结果丢失"。

---

## 3.3 对证分解：九家源码对证

### 3.3.1 总览对比表

| 家 | 外层 turn loop | 中层 sampling retry | 内层 stream consume | 工具编排 | 结束判定 | 形态标签 |
|----|---------------|---------------------|---------------------|----------|----------|----------|
| **Claude** | `src/query.ts:219 query()` 的 `while(true)` + `hop≤25` | `attemptWithFallback()` 指数退避 + 模型降级 | `for await (message of deps.callModel())` + `StreamingToolExecutor.addTool()` 边收边执行 | `ToolOrchestrator: approval → sandbox → execute → hook → 回填` + `withheld` 扣留 | `handleStopHooks / toolUseSummary / max_output_tokens / shouldStopAfterTurn` | **生产 while + 增量流** |
| **Codex** | `codex-rs/core/src/session/turn.rs:153 run_turn()` | `run_sampling_request()` + `responses_retry.rs` | `try_run_sampling_request()` 内 `stream.next()` + `ResponseEvent{OutputItemAdded/Done, ToolCallInputDelta}` 累积 `in_flight` | `ToolExecutor<Invocation>{spec(),handle()}` + `ToolCallRuntime(RwLock)` 并行门闸 + `sandboxing.rs` | `needs_follow_up` / `HopLimit` | **FSM 二分 Context** |
| **Pi** | `packages/agent/src/agent-loop.ts:155 runLoop` 外层 `while(true)` + 内层 `while(hasMore)` | `streamAssistantResponse()` 内重试（可注入） | `streamFn` 事件流 → `message.content.filter(isToolCall)` | `AgentTool{id,parameters,execute}` + `ToolExecutionMode{sequential\|parallel}` | `shouldStopAfterTurn / getFollowUpMessages / getSteeringMessages` | **教学 while（最小闭环）** |
| **DeepSeek** | `packages/core/agent-loop/src/agent.ts:70 kick()→turn()→step()` + `Phase{idle\|maintenance\|running}` | `step(){ while(true){buildRequest→stream; if(error) normalizeLlmFailure→continue } }` | `BlockAssembler.push(chunk)` → `block-start/delta/block-end` + `chunkSeqs → sourceEventSeqs` | `Cordis` 插件化 `dsh-tool-*` + `executeToolCalls()` 批量串行注入 | `completed vs blocked vs null` + `turnEnds=max-tokens` 黏性 | **状态机 FSM（最精确）** |
| **Grok** | `xai-chat-state` Actor + `xai-agent-lifecycle` | `SamplingClient` 三后端×六端点 + `deserialize_response_event()` | `ChatStateActor` 单 task 串行消费 `Command`，`turn_capture.turn_start_offset` | `ToolBridge + xai-tool-runtime ToolRegistry{ToolKind→vendorName}` + `merge_tool_params` | `TurnCaptureState` + `CompactionPolicy.should_auto_compact(85%)` | **Actor 隔离** |
| **OpenCode** | `packages/opencode/src/session/session.ts:224 Info Schema` (Effect) | `tool/registry` 驱动 + `BundledSDK.languageModel` | `tool/tool.ts:50 execute(ctx: Effect)` | `Tool.Def{parameters,jsonSchema,execute:Effect}` + `PermissionV1.Ruleset` + `Truncate.wrap()` | `Agent.steps` + `agent/prompt/compaction.txt` 隐藏 agent | **Effect + 隐藏 agent** |
| **Claw** | `rust/crates/runtime/src/conversation.rs:91 ConversationRuntime`（`run_turn()` :153） | `ApiClient::stream` | `build_assistant_message(events)` | `rust/crates/tools/src/lib.rs ToolPool` | `max_iterations` | **批量流（反例）** |
| Hermes | `agent/conversation_loop.py:1766 run_conversation()`（单体式主循环；网关进程缓存 agent 实现跨 turn 复用；MoA/子代理经 async_delegation 并行） |

> 一句话区分：**最小闭环（Pi）只有外层与"工具后回填"；生产级（Claude/Codex/DeepSeek/Grok）在中/内层叠加了重试、流式工具累积、预算闸与取消语义**。

### 3.3.2 分家精读（逐行走读要点）

#### Claude — `src/query.ts:219 query()`

```ts
// 骨架（已删减，仅示意图）
export async function* query(
  deps: QueryDeps, // { callModel, tools, context, session, trace }
  init: QueryInit
) {
  let hop = 0;
  while (true) {
    if (hop++ >= 25) break; // 熔断（与 Pi 同值，见 Ch2）
    // 闸1：四层压缩（snip → micro → collapse → autocompact）
    await snipCompactIfNeeded(deps);
    await microcompact(deps);
    await contextCollapse.applyCollapsesIfNeeded(deps);
    await autocompactIfNeeded(deps); // Haiku 摘要，失败回退到截断

    // 闸2：Prompt Caching 断点（system / tools / history）
    const cacheControl = getCacheControl({ querySource: init.source });

    // L2+L3：采样重试 + 流式消费（边收边执行）
    const stream = deps.callModel({ cacheControl, signal: deps.abortSignal });
    const executor = new StreamingToolExecutor(deps.tools);
    for await (const message of stream) {
      if (message.tool_use) executor.addTool(message.tool_use); // 边收边起执行
      yield message; // 增量回显
    }

    const toolCalls = executor.getToolCalls();
    if (toolCalls.length === 0) {
      // 结束判定：handleStopHooks / toolUseSummary / max_output_tokens
      const stop = await handleStopHooks(deps, toolCalls);
      if (stop.shouldStop) break;
      yield* handleTextResponse(deps, toolCalls);
      break;
    }

    // 工具编排：approval → sandbox → execute → hook
    // withheld：若本轮被 steer 打断，未完成的 tool_results 扣留到下一 step
    const { completed, withheld } = await executor.getCompletedResults();
    deps.session.append({ tool_results: completed });
    if (withheld.length) deps.session.withhold(withheld); // 下一 hop 起点合并回填
    deps.trace.record({ hop, toolCalls, tokenUsage, compactionEvent });
  }
}
```

**精读点**：

- `StreamingToolExecutor.addTool()` 的"边收边执行"是增量流的核心——`tool_use` 的 `input` 尚未收全时即可预创建 `cancellation_token`，与 DeepSeek 的 `BlockAssembler` 异曲同工。
- `withheld` 扣留解决"steer 到来时部分工具已完成、部分未完成"的**部分结果问题**：已完成的立即回填，未完成的扣留到下一 hop 起点与新 `steer` 消息合并，避免"丢 tool_result 导致下一轮采样因缺 `tool_result` 而 PTL"。
- `attemptWithFallback`（中层）在 `query()` 外层包裹，`overloaded` 时自动降级模型（如 `opus → sonnet`），与 Codex `responses_retry.rs` 同策。

#### Codex — `codex-rs/core/src/session/turn.rs:153 run_turn()`

```rust
// 骨架（Rust 伪代码）
pub async fn run_turn(ctx: TurnContext, mut stepCtx: StepContext) -> TurnResult {
    // TurnContext vs StepContext 二分（见 3.4.1 权衡）
    let mut hop = 0;
    loop {
        if hop >= MAX_HOPS { break; }
        // 闸：history_version 检查 + should_compact
        if ctx.context_manager.should_compact() {
            ctx.context_manager.compact().await; // core/src/compact.rs
        }
        // L2：采样重试
        let events = run_sampling_request(&ctx, &stepCtx).await?;
        // L3：流消费（try_run_sampling_request 内）
        //   ResponseEvent::OutputItemAdded / ToolCallInputDelta 累积 in_flight
        //   ToolCallRuntime(RwLock) 控制并行度
        let toolCalls = drain_in_flight(events);

        if toolCalls.is_empty() {
            if !needs_follow_up(&ctx) { break; }
            continue;
        }

        // 工具编排：build_tool_router() 每 step 重建（spec_plan.rs:117）
        //   add_core_tool_sources() + append_mcp → finalize_tool_router()
        //   保证 model_visible_specs 与本次快照一致（I2）
        let router = build_tool_router(&stepCtx);
        let results = execute_tools_parallel_if_safe(router, toolCalls, &stepCtx).await;
        ctx.session.append(results); // history_version 递增
        hop += 1;
        if let Some(pending) = ctx.input_queue.drain_pending_input() {
            ctx.session.append(pending); // InputQueue 每 turn 起点排空
        }
    }
    Ok(TurnResult::Done)
}
```

**精读点**：

- **`TurnContext` vs `StepContext` 二分**是 Codex 最值得抄的设计：`TurnContext` 持有`稳定`的 `session / config / model`，`StepContext` 持有`快照`的 `tool_router / approval_policy / sandbox`。回合中途切模型或卸载工具时，不影响已开始的 step，避免"悬垂工具调用"。
- `ToolCallRuntime(RwLock)` 并行门闸：`isConcurrencySafe=true` 的工具可并行，`preflight`（审批+沙箱决策）仍串行，前置决策不并发是正确性保证。
- `responses_retry.rs` 的指数退避与模型降级与 Claude `attemptWithFallback` 同策，但 Codex 额外在 `LlmError` 中保留 `requestId` 供 `codex-otel` 归因。

#### Pi — `packages/agent/src/agent-loop.ts:155 runLoop`

```ts
// 最小闭环（200 行心智模型，见 Ch2.4，此处补全取消与预算）
export async function runLoop(
  context: AgentContext, // { systemPrompt, messages: AgentMessage[] }
  config: AgentLoopConfig, // { getSteeringMessages, getFollowUpMessages, shouldStopAfterTurn, toolExecution }
  signal: AbortSignal,
  emit: EmitFn,
  streamFn: StreamFn
) {
  while (true) { // outer: followUp loop（L1）
    let hasMore = true;
    while (hasMore) { // inner: hop loop（L1 内层）
      if (await needsCompaction(context)) await compact(context); // 闸1（用户注入）
      // L2+L3 合一：streamAssistantResponse 内含重试 + 事件流消费
      const message = await streamAssistantResponse(context, config, signal, emit, streamFn);
      const toolCalls = message.content.filter(isToolCall);
      if (toolCalls.length === 0) {
        hasMore = false;
        break;
      }
      // 工具编排：preflight 串行 → execute 可并行（由 ToolExecutionMode 决定）
      const toolResults = await executeToolCalls(toolCalls, config); // 含 cancellation
      context.messages.push(message, ...toolResults); // 回填（无 Session 持久化，仅内存）
      // 结束判定
      if (await config.shouldStopAfterTurn?.(context)) { hasMore = false; break; }
      // 打断：steering（协作式）
      const steering = await config.getSteeringMessages?.();
      if (steering?.length) context.messages.push(...steering);
    }
    const followUp = await config.getFollowUpMessages?.();
    if (!followUp?.length) break;
    context.messages.push(...followUp);
  }
}
```

**精读点**：

- **为何适合教学**：`runLoop` 无 `Session` 持久化、无 `BlockAssembler`、无 `Inbox` 队列，所有"闸"均通过 `AgentLoopConfig` 回调注入，读者可逐个替换实现以观察效果，是"200 行可运行的 Loop 实验室"。
- **局限**：无 `TurnContext/StepContext` 二分，`tool_router` 在循环内不变，若回合中途切模型需重启整个 `runLoop`；无 `TurnCaptureState`，崩溃无法按 offset 重放。
- **一句话陈述**："我能手写 Pi 的 `runLoop`，并指出生产级需在其上加的 5 个闸：预算、重试、装配、取消、观测。"

#### DeepSeek — `packages/core/agent-loop/src/agent.ts:70 ReactLoopAgent（type Phase :39）`

```ts
// 状态机形态（TS 伪代码，对应 Rust 侧 Phase 枚举）
type Phase = 'idle' | 'maintenance' | 'running';

class ReactLoopAgent {
  private phase: Phase = 'idle';
  private inbox = new Inbox(); // splice(next-turn/next-step)
  private turn: { id: string; hop: number } | null = null;

  kick(input: Message) { // idle → running
    this.phase = 'running';
    this.turn = { id: uid(), hop: 0 };
    this.turnLoop(input);
  }

  private async turnLoop(initial: Message) {
    this.session.append({ type: 'turn/start', turnId: this.turn!.id });
    let pending: Message[] = [initial];
    while (this.phase === 'running') {
      if (this.turn!.hop >= 25) break;
      // maintenance 相：压缩/取消期间不可被普通输入打断
      if (needsCompaction(this.session)) {
        this.phase = 'maintenance';
        await this.compact(); // compaction-basic + tool-result-pruner
        this.phase = 'running';
        if (this.inbox.wakeRequested && !this.inbox.wakingAfterAbort) {
          pending.push(...this.inbox.drain('next-turn'));
        }
      }
      const stepResult = await this.step(pending); // L2+L3
      pending = [];
      if (stepResult.kind === 'completed') break;
      if (stepResult.kind === 'blocked') { pending = stepResult.followup; continue; }
      // 工具结果已在 step 内 append，此处仅处理 Inbox
      const spliced = this.inbox.drain(stepResult.kind === 'completed' ? 'next-turn' : 'next-step');
      if (spliced.length) pending.push(...spliced);
      this.turn!.hop++;
    }
    this.phase = 'idle';
    this.session.append({ type: 'turn/end', turnId: this.turn!.id });
  }

  private async step(messages: Message[]): Promise<StepResult> {
    // L2：采样重试（可不跨 turn 重试）
    while (true) {
      try {
        const req = this.buildRequest(messages); // joinContextSections 控制 cache 前缀
        const stream = this.llm.stream(req); // ChunkStream
        const assembler = new BlockAssembler();
        for await (const chunk of stream) {
          const blocks = assembler.push(chunk);
          for (const b of blocks) this.session.append({ type: 'assistant/chunk', block: b });
          if (this.inbox.wakeRequested) { /* 可抢占检查 */ }
        }
        const toolCalls = assembler.getToolCalls();
        if (toolCalls.length === 0) return { kind: 'completed' };
        const results = await executeToolCalls(toolCalls); // Cordis 插件化
        this.session.append({ type: 'step/end', results });
        return { kind: 'completed' } as StepResult; // 简化，实际区分 blocked/completed
      } catch (e) {
        const err = normalizeLlmFailure(e); // adapter-failure.ts 归一
        if (!err.retryable) throw e;
        await sleep(backoff(err.retryAfterMs));
        continue; // 单 step 内重试，不跨 turn
      }
    }
  }
}
```

**精读点**：

- **`Phase` 三态是本书最精确的中断语义**：`idle` 可接受 `kick()`，`running` 可被 `steer(next-step)` 抢占，`maintenance` 仅可被 `cancel(keepInbox=false)` 打断。`wakingAfterAbort` 防重入是正确性关键（见 3.2.4.2 时序图）。
- **`BlockAssembler` + `sourceEventSeqs`**：`chunkSeqs` 供 `turn/start` 回溯，若流中失败可按已收 seqs 决定重放或截断，是"流的可重放性"保证。
- **`turnEnds=max-tokens` 的黏性**：`completed` 不覆盖 `max-tokens`，保证用量归因正确（`total_tokens` 重写为 live 长度，见 Ch2 的适配器剥除）。

#### Grok — `xai-chat-state` Actor

```rust
// 骨架（Rust 伪代码，对应 crates/codegen/xai-chat-state/src/actor/mod.rs）
pub enum Command {
    Append(Message),
    Steer(Message),
    GetState(Oneshot<Sender<ChatStateSnapshot>>),
    TurnCapture { offset: usize, oneshot: Oneshot<TurnCaptureState> },
}

pub struct ChatStateActor {
    state: ChatState, // conversation: Vec<ConversationItem> + UsageLedger + turn_capture
    rx: mpsc::Receiver<Command>,
}

impl ChatStateActor {
    pub async fn run(mut self) {
        while let Some(cmd) = self.rx.recv().await {
            match cmd {
                Command::Append(msg) => {
                    self.state.conversation.push(msg.into());
                    self.state.usage.add(msg.tokens);
                }
                Command::Steer(msg) => {
                    // 单 task 拥有状态，无锁；steer 直接 push，无需 Inbox 队列
                    self.state.conversation.push(msg.into());
                }
                Command::GetState(tx) => { let _ = tx.send(self.state.snapshot()); }
                Command::TurnCapture { offset, oneshot } => {
                    // turn_start_offset 避免逐条克隆，批量投影
                    let capture = self.state.capture_from(offset);
                    let _ = oneshot.send(capture);
                }
            }
        }
    }
}

// ChatState 侧（state.rs:1）
impl ChatState {
    pub fn new(items: Vec<ConversationItem>) -> Self {
        // 自愈：dedup_duplicate_tool_results + repair_dangling_tool_calls
        let items = Self::dedup_duplicate_tool_results(items);
        let items = Self::repair_dangling_tool_calls(items);
        Self { conversation: items, usage: UsageLedger::new(), turn_capture: TurnCaptureState::new() }
    }
    pub fn estimate_item_tokens(item: &ConversationItem) -> usize {
        // chars/4 + IMAGE_TOKEN_ESTIMATE + tool_calls.arguments.len()
        (item.bytes() / 4) + item.tool_args_len() + IMAGE_TOKEN_ESTIMATE
    }
}
```

**精读点**：

- **Actor 的本质是"串行化并发"**：`ChatState` 仅被单 `tokio::task` 拥有，外部仅发 `Command`，无需 `RwLock`，天然无数据竞争；代价是跨 task 查询需 `Oneshot`（`GetState`）。
- **`turn_capture.turn_start_offset` 的批量投影**：`capture_from(offset)` 返回 `offset..` 的切片，避免每条消息克隆，是 Grok 在 200K 上下文下保持性能的关键。
- **自愈（`ChatState::new()`）**：`dedup_duplicate_tool_results` 去重崩溃前重复写入的 `tool_result`，`repair_dangling_tool_calls` 为无 `tool_result` 的 `tool_call` 补 `error` 占位，避免下一轮采样因缺 `tool_result` 而 PTL。

#### OpenCode — `packages/opencode/src/session/session.ts:224 Info Schema` + `tool/tool.ts:55 Def`

```ts
// Session.Service（Effect 形态）
export class SessionService extends Effect.Service<SessionService>()("SessionService", {
  effect: Effect.gen(function* () {
    const db = yield* Database; // Drizzle + SQLite
    return {
      create: (init) => Effect.gen(function* () {
        const id = uid();
        yield* db.insert(PartTable).values({ sessionId: id, message: init });
        return id;
      }),
      fork: (sessionId) => Effect.gen(function* () {
        const parts = yield* db.select().from(PartTable).where(eq(PartTable.sessionId, sessionId));
        const newId = uid();
        yield* db.insert(PartTable).values(parts.map(p => ({ ...p, sessionId: newId })));
        // structuredClone 保证血缘可追溯
        return newId;
      }),
      append: (sessionId, part) => db.insert(PartTable).values({ sessionId, part }),
    };
  }),
}) {}

// Tool.Def（tool.ts:30）
export type Def = {
  id: string;
  parameters: z.ZodSchema;
  jsonSchema: JSONSchema;
  execute: (ctx: { sessionId: string; args: unknown; signal: AbortSignal }) => Effect.Effect<ToolResult, ToolError>;
  exposure?: 'direct' | 'deferred' | 'hidden'; // 可见性分级（与 Codex 同策）
};

// Truncate（tool/truncate.ts）
export const Truncate = {
  wrap: (result: ToolResult, agent: AgentInfo) =>
    truncate.output(result.output, { whitelistedDirs: agent.whitelistedDirs }, agent),
};
```

**精读点**：

- **Effect 的价值**：`Tool.Def.execute` 返回 `Effect`，`Session.Service` 亦为 `Effect`，两者在 `Effect.gen` 中组合时，`AbortSignal` 与错误归一自动传播，无需手写 `try/catch + abort` 样板。
- **隐藏 compaction agent**（`agent/agent.ts:35 Info{mode:hidden, permission:* deny}`）：压缩由专用子 agent 执行（`compaction/title/summary` 三类，见 `agent/prompt/compaction.txt`），权限`* deny`保证不触文件，是"压缩即子 Agent"的干净隔离。
- **统一截断**：`Truncate.wrap()` 在工具层统一做，而非散落在各工具内部，避免某工具绕过截断导致 context 爆炸（与 Claude `src/services/tools/toolOrchestration.ts` 末端截断同策，但 OpenCode 更彻底）。

#### Claw — `rust/crates/runtime/src/conversation.rs:91 ConversationRuntime`（`run_turn()` :153）

```rust
// 骨架（Rust 伪代码）
pub struct ConversationRuntime {
    session: Session, // Session{version, messages}
    client: ApiClient,
    tools: ToolPool,
}

impl ConversationRuntime {
    pub async fn run_turn(&mut self, input: &str) -> Result<TurnResult> {
        self.session.messages.push(Message::user(input));
        for hop in 0..self.config.max_iterations {
            if self.should_compact() { self.compact().await; } // compact_after_turns=12
            // 批量流：一次性返回 Vec<AssistantEvent>
            let events: Vec<AssistantEvent> = self.client.stream(self.session.for_prompt()).await?;
            let assistant = build_assistant_message(events); // 组装
            self.session.messages.push(assistant.clone());
            let toolCalls = assistant.tool_calls();
            if toolCalls.is_empty() { return Ok(TurnResult::Text(assistant.text())); }
            let results = self.tools.execute_all(toolCalls).await; // 无 preflight 串行
            self.session.messages.extend(results);
        }
        Ok(TurnResult::HopLimit)
    }
}
```

**精读点（反例价值）**：

- **批量流的代价**：`ApiClient::stream() → Vec<AssistantEvent>` 一次性返回整批事件，代码最短，但在 20+ hop 长链路上无法做"边收边执行"与"中途取消"。`build_assistant_message(events)` 需等待整批事件收全后才起工具执行，首个工具的启动延迟 = 整轮采样延迟。
- **`compact_after_turns=12` 的粗糙**：固定轮数触发压缩，而非 token 预算驱动（Claude `effectiveWindow-13k` / Grok `85%`）。在"单轮输出 30K token 的长工具结果"场景，12 轮前已 PTL；在"短轮 20 turn"场景又过早压缩，浪费可缓存前缀。
- **移植价值**：`claw-code-main/src/tools.py:24 load_tool_snapshot()` 展示如何把 TS 的 `Tool.Def` 翻译为 Rust 的 `ToolPool`，是"TS→Rust 移植"的桥梁案例。

### 3.3.3 七家对证小结：一张"闸"的有无表

| 闸 | Claude | Codex | Pi | DeepSeek | Grok | OpenCode | Claw |
|----|--------|-------|----|----------|------|----------|------|
| **hop 上限** | ✅ 25 | ✅ `MAX_HOPS` | ✅ 25 | ✅ 25 | ✅ `max_iterations` | ✅ `Agent.steps` | ✅ `max_iterations` |
| **采样重试+降级** | ✅ `attemptWithFallback` | ✅ `responses_retry.rs` | △ 可注入 | ✅ `normalizeLlmFailure` | ✅ `SamplingClient` | △ `BundledSDK` | ❌ |
| **流装配器** | ✅ `StreamingToolExecutor` | ✅ `in_flight` | ❌ | ✅ `BlockAssembler` | ✅ `deserialize_response_event` | △ `Effect` 流 | ❌ 批量流 |
| **预算闸** | ✅ 四层防线 | ✅ `history_version` | △ 用户注入 | ✅ `dsh-token-meter` | ✅ `85%` | ✅ 隐藏 agent | △ 固定轮数 |
| **取消/打断** | ✅ `withheld` | ✅ `InputQueue` | △ 回调式 | ✅ `Inbox.splice` | ✅ `Actor` | △ `AbortSignal` | ❌ |
| **观测** | ✅ `tengu_*` + `Trace` | ✅ `codex-otel` | △ 内存 | ✅ `EventV2Bridge` | ✅ `UsageLedger` | ✅ `Drizzle PartTable` | △ `Session.version` |

> 结论：七家差异不在"有无 Loop"，而在"在 Loop 上装了几道闸、每道闸的精度"。Pi 只有 1 道（hop），Claw 2 道，生产级 5 道全装。

---

## 3.4 结论与权衡

### 3.4.1 when while vs FSM vs Actor

| 风格 | 代表 | 形态 | 优点 | 代价 | 适用场景 |
|------|------|------|------|------|----------|
| **简单 while** | Claude `src/query.ts:219 query()`, Pi `packages/agent/src/agent-loop.ts:155 runLoop` | `while(true){ llm→tools→push }` + `hop≤25` | 直观、易读、易测试；`AsyncGenerator` 直接 `yield` 增量 | 打断/恢复需额外状态（`withheld`）；`maintenance` 不可打断难表达 | 教学演示、手写练习、单 turn 批量任务、无需采样中打断 |
| **状态机 FSM** | DeepSeek `packages/core/agent-loop/src/agent.ts:70 Phase{idle\|maintenance\|running}` | `idle→running{turn{step}}→idle` + `maintenance` | 天然支持暂停/恢复/并发；`splice(next-turn vs next-step)` 精度最高 | 代码量大、状态迁移易遗漏；需`wakingAfterAbort`等闩锁防重入 | 需"采样中打断"且`maintenance`不可打断的生产 Agent |
| **Actor 隔离** | Grok `crates/codegen/xai-chat-state/src/actor/mod.rs ChatStateActor` | 单 `tokio::task` 拥有 `ChatState`，外部仅发 `Command` | 无锁、崩溃自愈（`dedup+repair`）、批量投影（`turn_start_offset`） | 跨 task 查询需 `Oneshot`，链路多一跳；`Command` 枚举膨胀 | 高并发、多租户、需崩溃自愈的云端 Agent |
| **二分 Context** | Codex `TurnContext` vs `StepContext` (`session/step_context.rs:17`) | Turn 稳定、Step 快照；`build_tool_router()` 每步重建 | 回合中途切模型/工具清单稳定；`I2`（同快照）天然满足 | 概念负担；`StepContext` 需逐 step 克隆部分状态 | 工具集/模型在 turn 内可变（MCP 动态装卸、模型降级） |

**决策树（简化）**：

```
需要采样中打断（steer）吗？
├─ 否 → 需要崩溃自愈吗？
│        ├─ 否 → while (Pi/Claude 形态，200–400 行)
│        └─ 是 → Actor（Grok），但可先用 while + Journal 折中
└─ 是 → maintenance 需不可打断吗？
         ├─ 否 → while + InputQueue（Codex 简化版）
         └─ 是 → FSM（DeepSeek Phase），或 Actor（Grok）
                  └─ 需要跨进程/多租户无锁吗？ → Actor
```

**真实教训**：

- Claude 选择 `while` 而非 `FSM`，代价是用 `withheld` 扣留与 `StreamingToolExecutor` 的复杂度换取可读性——但团队规模大时，`withheld`的隐式状态成为新人坑位。
- DeepSeek 选择 `FSM`，收益是`Inbox`语义精确，代价是`Phase`迁移表需 exhaustive test（`agent.ts:50` 附近有 20+ `expect(phase).toBe(...)`）。
- Grok 选择 `Actor`，收益是`ChatState`无锁且可`forkSubagent`时冻结 `renderedSystemPrompt` 保证 cache 命中，代价是每个 `Command` 需定义 `Oneshot` 回执类型，`ToolBridge` 的 `merge_tool_params` 需跨 task 同步。

### 3.4.2 批量流 vs 增量流：生产教训

| 维度 | 批量流（Claw `Vec<AssistantEvent>`） | 增量流 + 装配器（Claude/Codex/DeepSeek） |
|------|----------------------------------------|-------------------------------------------|
| **首工具启动延迟** | = 整轮采样延迟（需等全部 events） | = 首个 `tool_use delta` 到达延迟（边收边起） |
| **中途取消** | 无法以块为粒度取消，只能等整批返回后 `abort` | `stream.next()` 每次检查 `wakeRequested`，可块级取消 |
| **部分失败** | 整批失败即整轮重采，无 `sourceEventSeqs` 回溯 | `chunkSeqs` 保留已收块，可按 offset 重放或截断 |
| **代码复杂度** | 最低（`await stream → Vec`） | 高（`BlockAssembler` + `in_flight` + `withheld`） |
| **适用** | 原型、离线评测（无需交互） | 生产、交互式 CLI（需 steer 与边收边执行） |

> **教训**：**不要用批量流做长链路**（>5 hop 或 >30s 采样）。Claw 的批量流在 12 轮原型中可接受，但在 25 hop 生产链路上，首工具延迟与取消缺失会直接转化为用户可感知的"卡顿"与"无法打断"。

### 3.4.3 其他权衡

| 权衡 | 选项 A | 选项 B | 建议 |
|------|--------|--------|------|
| **工具并行** | 默认串行（Claude）`isConcurrencySafe=true`才并行 | 默认并行（Codex）`supports_parallel_tool_calls`显式声明 | 默认串行，仅对`isReadOnly && isConcurrencySafe`的工具并行；`preflight`仍串行 |
| **预算触发** | 固定轮数（Claw `12`） | Token 预算（Claude `window-13k` / Grok `85%` / Codex `history_version`） | 生产必选 token 预算；轮数仅作原型兜底 |
| **错误归一** | 各处 `if (e.status===429)` | 先 `normalizeLlmFailure()` 再决策（DeepSeek/Grok） | 先归一形状（`LlmError{code,status,retryAfterMs,requestId}`），再定重试策略；`SENT_BEARER_PREFIX_LEN=12`截断防日志泄密 |
| **hop 上限** | 无上限（AutoGPT 教训） | `25` 熔断（Claude/Pi/DeepSeek） | 必设 `25` 熔断；`turnEnds=max-tokens` 时黏性保留 `max-tokens` 归因 |
| **结束判定** | 单一 `tool_calls.isEmpty()` | `shouldStopAfterTurn / needs_follow_up / handleStopHooks` 三闸 | 至少两闸：`tool_calls.isEmpty()` + `shouldStopAfterTurn`（预算/外部信号） |

---

## 3.5 未来方向

### 3.5.1 Speculative Loop（推测执行）

**问题**：当前 Loop 是`采样→执行→回填`的串行依赖，模型等待工具执行时 GPU 空闲，工具等待模型采样时 CPU/IO 空闲。

**思路**：借鉴 CPU 分支预测与 LLM 推测解码（Speculative Decoding），在`tool_result`尚未返回时即**推测其内容**并提前发起下一轮采样。

```
当前（串行）：
  llm₁ ──► exec(tool₁) ──► llm₂ ──► exec(tool₂) ──► llm₃

推测（并行）：
  llm₁ ──► exec(tool₁) ─┬─► llm₂(speculative: "file not found") ──► exec(tool₂)（若猜错则丢弃）
                         └─► llm₂(actual: tool₁ result) ──────────► exec(tool₂)（若猜中则已提前）
```

**关键挑战**：

- 推测策略：对`read_file`可推测"文件存在/不存在"各起一 speculative branch（类似 Grok 的 `forkSubagent` 冻结 `renderedSystemPrompt` 保证 cache 命中，推测分支亦可共享前缀 cache）。
- 回滚代价：`Session.append` 为唯一写路径（I1），推测分支需写 `speculative: true` 的暂态事件，确认后 `commit` 或 `rollback`。DeepSeek 的 `turn_start_offset` 与 Grok 的 `Journal` 为此提供基础——offset 之前的共享前缀无需回滚。
- 适用场景：`read_file / list_dir` 等只读工具推测收益高；`write_file / bash` 等有副作用工具不可推测（需 `isConcurrencySafe` 判定）。

**验收**：在 10 hop 链路上，推测命中率>60% 时端到端延迟下降>20%，且回滚正确性 100%（无推测污染进 `Session` 全量）。

### 3.5.2 Human-in-the-Loop Steer（人在环驾驶）

**现状**：DeepSeek 的 `Inbox.steer(next-step)` 与 Pi 的 `getSteeringMessages()` 已支持"采样中打断"，但语义仍是"文本注入"。

**演进**：

| 层级 | 形态 | 例子 | Loop 改动 |
|------|------|------|-----------|
| L1 文本 steer | 用户追加消息 | "stop, change direction" | `Inbox.splice(next-step)`（已实现） |
| L2 结构化 steer | 用户改工具参数/审批决策 | 拖拽调整 `write_file` 的目标路径 | `ToolCall` 级别的 `steer({toolCallId, newArgs})`，需 `BlockAssembler` 支持按 `id` 定向更新 `in_flight` |
| L3 策略 steer | 用户改 Loop 策略 | "从现在起所有 `bash` 需审批" | `Phase.maintenance` 内热更新 `approval_policy`（Codex `StepContext` 每步重建已支持，需扩展为 steer 触发） |
| L4 目标 steer | 用户改任务目标 | "放弃当前重构，改为写测试" | `turn/fork`：当前 turn `cancel(keepInbox=false)` 并以新目标起新 `turn`，旧 turn 归档为 `abandoned`（OpenHands `EventStream` 已有雏形） |

**设计原则**：steer 的**粒度与 Loop 的抢占点一一对应**——`next-step` 粒度对应 L2，`next-turn` 粒度对应 L1，策略/目标 steer 对应 `maintenance` 相。DeepSeek 的 `Inbox` 四方法（`send/steer/inject/followup`）已为此分层打下基础，缺的是"结构化 steer"的 `toolCallId` 定向能力。

### 3.5.3 Adaptive Hop Budget（自适应预算）

**现状**：七家均为固定 `MAX_HOPS=25`（Claude/Pi/DeepSeek）或 `max_iterations`（Grok/Claw）。固定值在"简单问答 3 hop 即结束"时浪费判定开销，在"复杂重构需 40 hop"时过早熔断。

**思路**：把 `hop budget` 从常量变为**基于任务复杂度与历史成功率的动态值**。

```ts
type HopBudget = {
  base: number;           // 25（默认）
  byTask: (task: Task) => number; // 任务分类：qa→10, refactor→40, explore→15
  byHistory: (history: Session) => number; // 若近 5 hop 工具成功率>80%则 +5，否则 -5
  byToken: (used: number, window: number) => number; // window 剩余<20%时强制收敛
  hardCap: number;        // 50（绝对上限，防无限循环）
};

function getHopBudget(state: State, task: Task): number {
  const base = 25;
  const taskBonus = task.kind === 'refactor' ? 15 : task.kind === 'qa' ? -10 : 0;
  const historyBonus = recentSuccessRate(state.session) > 0.8 ? 5 : -5;
  const tokenPenalty = state.budget.used / state.budget.window > 0.8 ? -10 : 0;
  return clamp(base + taskBonus + historyBonus + tokenPenalty, 5, 50);
}
```

**与现有机制的衔接**：

- `shouldStopAfterTurn`（Pi）与 `handleStopHooks`（Claude）已是"结束判定的扩展点"，自适应预算可作为其一实现。
- `TurnState.hop` 计数与 `needsCompaction()` 预算闸需联动：hop 预算增加时，`effectiveWindow - reserve` 的阈值需同步收紧，避免"hop 多但 context 已爆"。
- Grok 的 `CompactionPolicy{wall_clock_budget_secs:300}` 已引入**时间预算**，hop 预算是其"步数维度"的对偶。

**风险**：自适应若基于模型自评复杂度，易被"过度自信"误导；需以**工具成功率**与**token 剩余**等客观信号为主，模型自评仅作辅助。

### 3.5.4 结构化 Loop DSL（可编排、可验证的 Loop）

**问题**：当前 Loop 均以**宿主语言**（TS/Rust/Python）的`while/FSM/Actor`手写，难以静态分析"是否存在不可达状态"、"取消是否覆盖所有 `await` 点"、"hop 预算是否在所有路径上递减"。

**思路**：引入**结构化 Loop DSL**，将 Loop 描述为可被`lint/inspect`的声明式配置，类似 `Temporal` 的 Workflow 定义或 `XState` 的状态图。

```yaml
# 伪 DSL（受 XState 与 DeepSeek Phase 启发）
loop:
  phases: [idle, running, maintenance]
  transitions:
    - from: idle
      on: kick
      to: running
      actions: [recordTurnStart, resetHop]
    - from: running
      on: [steer, cancel]
      to: running
      guard: isNextStep
      actions: [inboxSpliceNextStep, abortStep]
    - from: running
      on: needsCompaction
      to: maintenance
      actions: [compact]
    - from: maintenance
      on: compactDone
      to: running
      guard: notWakingAfterAbort

  step:
    sampling:
      retry: { maxAttempts: 3, backoff: exponential, fallbackModel: sonnet }
      stream: { assembler: blockAssembler, chunkSeqs: sourceEventSeqs }
    execution:
      preflight: sequential        # 审批+沙箱串行
      execute: { mode: conditionalParallel, when: isConcurrencySafe }
    refill: { strategy: withheld } # Claude 语义

  budget:
    hop: { base: 25, adaptive: true, hardCap: 50 }
    token: { window: 200k, reserve: 8k, threshold: window-13k }
    wallClock: 300s

  observability:
    trace: [hop, toolCalls, tokenUsage, compactionEvent]
    otel: { span: turn, metrics: [hopCount, retryCount, steerCount] }
```

**收益**：

- **可验证**：`lint` 可检查"是否存在 `running → idle` 的未定义迁移"、"`maintenance` 是否可被 `steer` 误打断"。
- **可视化**：`inspect` 可渲染状态机图（Mermaid/XState Viz），`3.2.3` 的 ASCII 图自动生成。
- **可移植**：`packages/opencode` 的 `Effect` 与 `grok-build` 的 `Actor` 可共享同一 DSL，仅 `runtime` 不同（类似 `hyperframes` 的"同一 DSL 多 runtime"思想）。

**先例**：DeepSeek 的 `Cordis` 插件化已将`tool`声明为可配置单元；Grok 的 `AgentBuilder{30+ 流式配置}` 已接近 DSL；本方向是将其**从工具层提升到 Loop 层**。

---

## 3.6 小结：Loop 的五道闸与一张选型卡

```
用户输入
  │
  ▼
┌──────────────────────────────────────────────┐
│  Loop（采样→执行→回填的闭合）                │
│  ┌──────────────────────────────────────┐    │
│  │ L1 turn loop：hop 计数 / 结束判定    │    │
│  │ L2 sampling retry：重试+降级         │    │
│  │ L3 stream consume：装配+增量         │    │
│  │ 横切：工具编排（审批→沙箱→执行→Hook）│    │
│  └──────────────────────────────────────┘    │
│  五道闸：                                    │
│  ① hop 熔断（25）                            │
│  ② 预算闸（window-13k / 85% / history_version）│
│  ③ 重试闸（normalizeLlmFailure + backoff）   │
│  ④ 装配闸（BlockAssembler / in_flight）      │
│  ⑤ 取消闸（Inbox.splice / withheld / Actor） │
│  一条观测：Trace/otel/UsageLedger            │
└──────────────────────────────────────────────┘
  │
  ▼
Session.append（唯一写路径，可重放）
```

**选型卡（30 秒陈述）**：

> "Loop 的本质是`采样→执行→回填`的闭合，工程是在闭合上加五道闸。教学用 Pi 的 200 行 `while` 能跑；生产需三层嵌套——外层 turn 控 hop 与结束判定，中层采样重试归一 `LlmError` 后指数退避，内层流消费用 `BlockAssembler/in_flight` 装配。`while / FSM / Actor` 三选一取决于是否需采样中打断与崩溃自愈：三问皆否则 `while`，需打断则 `FSM`（DeepSeek `Phase`），需自愈则 `Actor`（Grok `ChatStateActor`）。批量流（Claw `Vec<AssistantEvent>`）易写但不可取消与边收边执行，生产必选增量流。"

---

## 思考题

1. **取消的正确性**：DeepSeek 的 `wakingAfterAbort` 闩锁若去掉，会在何种输入时序下导致"多起一轮空 turn"？请画出 `cancel(keepInbox=false)` → `wake` → `drain(next-turn)` 的时序并指出误分类点。（提示：`abort` 本身会触发 `wake`。）
2. **二分 Context 的必要性**：Codex 为何要将 `TurnContext`（稳定）与 `StepContext`（快照）分离？若改为单 `Context` 且在 `run_turn` 内直接 `build_tool_router()`，会在哪种场景产生悬垂工具调用？（提示：`StepContext` 快照包含 `ToolRouter`，而 `TurnContext` 不变。）
3. **批量流的边界**：Claw 的 `Vec<AssistantEvent>` 在何种 hop 数与采样时长下，其"首工具延迟 = 整轮采样延迟"的代价会超过增量流的 `BlockAssembler` 复杂度？请给出量化估算（假设平均采样 2s/hop，工具执行 1s，10 hop）。
4. **预算驱动 vs 轮数驱动**：`compact_after_turns=12`（Claw）与 `effectiveWindow-13k`（Claude）在"单轮 `tool_result` 30K token"与"20 轮短轮"两种负载下，分别会发生什么？哪种会先 PTL，哪种会过早压缩？
5. **推测执行的回滚**：Speculative Loop 中，若推测分支的 `Session.append({speculative:true})` 未正确 `rollback`，会对 `Session.fork()` 与 `history_version` 产生何种污染？应如何设计 `commit/rollback` 与 `turn_start_offset` 的协同？

## Lab 3：从 200 行到生产 Loop

**目标**：在 Pi 的 `runLoop` 上逐步加闸，最终得到与 Claude/Codex 对等的可中断 Loop。

**前置**：`my-agent/src/loop.ts`（已实现 `while + hop≤25 + ContextManager`）与 `packages/agent/src/agent-loop.ts:155 runLoop` 源码。

**步骤**：

1. **L3 装配器**：将 `streamFn` 的 `Vec<AssistantEvent>` 改为增量 `AsyncGenerator<Chunk>`，实现 `BlockAssembler.push(chunk)`（`chunk → block-start/delta/block-end`），并验证`tool_use`的 JSON 碎片可被正确累积与 `isCompleteJson` 判定。
2. **L2 重试**：实现 `normalizeLlmFailure()`（`LlmError{code,status,retryAfterMs,requestId,retryable}`）与指数退避（`backoff(attempt, retryAfterMs)`），并在 `step()` 内 `while(true) buildRequest→stream`，区分 `retryable` 与 `fatal`。
3. **取消语义**：实现 `Inbox`（`send/steer/inject/followup + splice(next-turn/next-step) + wakeRequested/wakingAfterAbort`），在 `stream.next()` 与 `executeToolCalls` 起点检查 `AbortSignal`，并验证"采样中输入 `stop`"可被 `next-step` 抢占而非等整轮结束。
4. **预算闸**：将 `compact_after_turns` 改为 `effectiveWindow-13k` 的 token 预算驱动（`chars/4` 估算），并在 `turn` 起点 `needsCompaction()` 时触发 `compact()`（可先用截断实现，再替换为 Haiku 摘要）。
5. **观测**：每 hop 记录 `Trace{hop, assistantText, toolCalls, tokenUsage, compactionEvent}` 到 `~/.my-agent/traces/<id>.json`，并验证 `hop=25` 熔断与 `max-tokens` 黏性归因。

**验收**：

- [ ] `npm test` 中新增 `loop.cancel.test.ts`：在采样 1s 后 `inbox.steer("stop")`，断言 Loop 在 ≤200ms 内进入下一 step 且 `tool_result` 无丢失（`withheld` 正确回填）
- [ ] `npm run typecheck` 通过，且 `git diff` 显示 Loop 文件行数从 ~200 行增至 ~400 行，但 `while` 仍为外层（未过早引入 FSM）
- [ ] 构造"30K `tool_result` × 10 hop"负载，验证固定轮数压缩会 PTL 而预算驱动不会
- [ ] `Trace` 文件中每条 `hop` 均含 `tokenUsage{input, output, cached}` 且 `compactionEvent` 可回溯

**常见坑**：

- `BlockAssembler` 的 `in_flight` 未按 `tool_call_id` 隔离→ 多工具并发时 JSON 碎片串扰。
- `Inbox.splice` 的 `next-step` 与 `next-turn` 混用→ `steer` 被延迟到下一 turn，用户感知"打断不生效"。
- `wakingAfterAbort` 未置位→ `cancel(keepInbox=false)` 后多起一轮空 turn，`Trace` 中出现 `hop` 空洞。

---

> 下一章将把 Loop 体内的"工具编排"——审批、沙箱、可见性、并行与 MCP——逐行拆开。七家在此的分野比 Loop 更细：同一 `read_file`，在 Claude/Codex/OpenCode 中的权限判定路径完全不同。



## 3.8 技术审计实证注记（2026-08-23 校准）

以下锚点与机制均已对照本地源码逐条验证：

| 声明 | 实证锚点 | 验证结果 |
|------|---------|---------|
| Codex `run_turn` 三层嵌套入口 | `codex-rs/core/src/session/turn.rs:153 pub(crate) async fn run_turn` | ✅（初稿误写 2791，已修正） |
| Codex 每 StepContext 重建工具清单 | `codex-rs/core/src/tools/spec_plan.rs:117 pub(crate) fn build_tool_router` | ✅（初稿误写 1381） |
| Codex 工具可见性 | `codex-rs/tools/src/tool_executor.rs:17 ToolExposures` bitflags：`NONE/DIRECT/DEFERRED/CODE_MODE/ALL`（CODE_MODE=嵌套 Code Mode 可调，非"Hidden"） | ✅ 变体名已修正 |
| DeepSeek `ReactLoopAgent` 与 Phase 状态机 | `packages/core/agent-loop/src/agent.ts:38 type Phase`、`:64 export class ReactLoopAgent` | ✅ |
| Pi 最小循环 | `packages/agent/src/agent-loop.ts:155 async function runLoop`（注意：不在 agent.ts；`agent.ts:171` 是 class Agent 包装层） | ✅ 路径已修正 |
| Pi steering 语义 | `agent-loop.ts:167` 循环起点即取 `getSteeringMessages()`——"等待期间输入"被显式建模 | ✅ 补充实证 |
