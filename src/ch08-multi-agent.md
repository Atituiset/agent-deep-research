# 第9章 多 Agent 与任务规划

> 单 Agent 解决"执行"，多 Agent 解决"分工"。七家的共识是：**任务规划是显式状态容器，子 Agent 是隔离的执行单元，plan 必须落盘为文件而非仅存于对话消息**。本章把"为什么需要多 Agent、怎么隔离、怎么通信、怎么规划"四问一次剖开。

**本章目标**：读完能（1）按时间轴复述多 Agent 与任务规划从 CAMEL 到多 Agent 实证之争的演进与每次跃迁的理由；（2）画出 Planner 的显式状态机与三类编排拓扑的时序图；（3）对照各家源码锚点解释"worktree 何时必要、何时禁止嵌套、plan 为何必须是 artifact"；（4）在单 Agent / Orchestrator-Worker / Swarm / Hierarchical 四选一时给出量化权衡；（5）对 Agent OS 与信用分配等五个前沿方向提出可验证假设。

**阅读方式**：配合 `appendix-sources.md` 锚点表，左侧开源码、右侧读本章；每节后 `> 反例` 与 `思考题` 用于自检。每家"隔离模型"差异是全书最高频追问点，建议重点对照 9.3.2 的逐行走读。


> 本章覆盖历史脉络：CAMEL 2023-03 (role-play) → MetaGPT 2023-08 (SOP) → AutoGen 2023-08 Microsoft → CrewAI 2023 → LangGraph 2024 → 多 Agent 实证之争 2024–2025；规划 lineage：ReAct → Plan-Execute → ReWOO → Voyager skill library；拓扑：Orchestrator-Worker vs Swarm vs Hierarchical；对证：Pi subagents 23；权衡：worktree 必要性、禁止嵌套、plan 落盘为文件


---

## 9.1 历史脉络与论文 lineage：从角色扮演到可调度系统

多 Agent 与任务规划是两条独立 lineage 的会合：**"多 Agent 协作"回答"谁来做"，"任务规划"回答"怎么做"**。二者在 2023–2024 年被 SWE-bench 类真实工程评测推向同一考场，又在 2025 年的 Anthropic vs Cognition 之争中被首次严肃清算性价比。

### 9.1.1 多 Agent Lineage：六次跃迁

```
2023-03  CAMEL (Li et al., arXiv:2303.17760)
           role-play：User ↔ Assistant 二元角色，inception prompting
           └── 首次证明"角色设定 + 对话式协作"可涌现任务分解，无显式 planner
                │
2023-08  MetaGPT (Hong et al., arXiv:2308.00352)
           SOP(Standardized Operating Procedure)：Product Manager → Architect → Engineer → QA
           └── 首次把"瀑布式 SOP"编码为 Agent 协作流程，产出 PRD/设计/代码三件套 artifact
                │  代价：SOP 硬编码，灵活性差
                │
2023-08  AutoGen (Wu et al., Microsoft, arXiv:2308.08155)
           ConversableAgent + GroupChat：可对话 Agent + 人机共编 + 代码执行器
           └── 首次把"多 Agent 对话"做成可编程框架，支持 human-in-the-loop
                │
2023-11  CrewAI (开源, 2023-10 首发, 2024 成熟)
           Role + Goal + Backstory + Task 声明式编排，Crew → Agent → Task 三级
           └── 把 AutoGen 的"对话式"收敛为"任务式"，降低使用门槛，代价是灵活性进一步下降
                │
2024-02  LangGraph (LangChain, 2024-02 发布, 2024-06 稳定)
           GraphState + Node + Edge：有状态图，支持 cycle / branch / checkpoint
           └── 首次把多 Agent 建模为"带持久化状态的有向图"，支持中断与恢复
                │  本质：把 CAMEL 的隐式对话流显式化为图结构
                │
2024–2025 多 Agent 实证之争
           More Agents (2024-02) 采样投票可扩展 → Anthropic 多 Agent 研究系统 (2025-06)
           └── 首次给出生产级量化：研究类任务提速 ~90%，代价 token ~15×；Cognition 同月唱反调
                │
2024–2026  七家生产实现（本书对象）
            Claude AgentTool(60+ 类型) / Codex collaboration-mode / Grok discovery + fast-worktree
            DeepSeek Cordis Scope / OpenCode task.ts / Pi subagents → "隔离模型"成为分水岭
```

| 年份 | 论文/系统 | 会议/载体 | 多 Agent 形态 | 一句话核心贡献 |
|------|-----------|-----------|---------------|----------------|
| 2023-03 | **CAMEL** | arXiv:2303.17760 | `User ↔ Assistant` 角色扮演，二元对话 | 首次证明"角色提示 + 自主对话"可涌现任务分解；规划隐式在对话中，无显式状态容器 |
| 2023-08 | **MetaGPT** | arXiv:2308.00352, ICLR 2024 | SOP 流水线：PM → Arch → Eng → QA，产出标准化文档 | 首次把"软件工程 SOP"编码为 Agent 协作协议，产出物（PRD/设计/代码）均为可审计 artifact |
| 2023-08 | **AutoGen** | Microsoft, arXiv:2308.08155 | `ConversableAgent` + `GroupChatManager` + `CodeExecutor` | 首次把多 Agent 做成可编程框架，支持人机共编与工具执行；`GroupChat` 引入 speaker selection 策略 |
| 2023-10 | **CrewAI** | 开源 (João Moura) | `Crew → Agent(role,goal,backstory) → Task` 声明式 | 把 AutoGen 的"图灵完备对话"收敛为"任务清单"，易用性最高，代价是难以表达复杂分支与回退 |
| 2024-02 | **LangGraph** | LangChain | `StateGraph{ nodes, edges, checkpoint }` 有状态图 | 首次把多 Agent 建模为"可持久化、可中断、可回放的状态图"，支持 `interrupt_before/after` 与时间旅行调试 |
| 2024-02 | **LangGraph** | LangChain | `StateGraph{ nodes, edges, checkpoint }` 有状态图 | 首次把多 Agent 建模为"可持久化、可中断、可回放的状态图"，支持 `interrupt_before/after` 与时间旅行调试 |
| 2024-2025 | **多 Agent 实证之争** | More Agents (arXiv:2402.05120)；Anthropic 工程博客 2025-06；Cognition 2025-06 | 采样投票扩展律 / Orchestrator-Worker 生产实测 / 反方檄文 | 首次给出量化答案：并行搜集类研究任务多 Agent 大幅领先（Anthropic：提速约 90%，代价 ~15× token）；强耦合编辑任务共享上下文优于分工（Cognition） |

> **演进主线**：`角色涌现（CAMEL）→ 流程固化（MetaGPT SOP）→ 可编程对话（AutoGen）→ 声明式任务（CrewAI）→ 状态图（LangGraph）→ 实证分水岭（More Agents / Anthropic vs Cognition）→ 生产隔离（七家）`。每一步都在回答：协作的"契约"应该写在哪里——prompt 里、SOP 文档里、代码里、还是状态图里。

### 9.1.2 逐篇精读：多 Agent 的五次形态变化与一次实证清算

时间轴是骨架，本节填血肉。多 Agent 这条线的独特之处在于：前五步是"怎么把协作表达出来"的框架竞赛，最后一步（2024–2025）才有人认真问"**这么做到底值不值**"——而答案比框架竞赛复杂得多。

#### CAMEL (2023)：什么都不给，只给角色——协作可以涌现

**困境**：让单个 LLM 分解复杂任务，质量不稳定。能不能让模型们互相把对方"逼出"完整的任务分解？

**机制**：CAMEL（Communicative Agents for "Mind" Exploration of Large Language Model Society）的做法极简到近乎行为艺术：一个 **task-setting 模型**把用户的一句模糊需求扩写成明确任务后，交给两个角色——**AI User**（扮演需求方）与 **AI Assistant**（扮演执行方）——自主对话直到产出结果。唯一的胶水是 **inception prompting**：给每个角色的 system prompt 里塞入对方的职责描述与输出格式约束，并规定 Assistant 每轮必须以"下一步要做什么"收尾，User 必须以具体指令回应。没有任何 planner 组件，规划完全在对话中涌现。

**证据**：论文的价值一半在成功案例，一半在失败观察。作者系统记录了两种失控：**role flipping**（两个角色互换身份，助手开始向用户下指令）与**无限客套**（双方反复说谢谢不干活）。这实际上是人类第一次大规模观察到"LLM 社会"的失稳模式——后来所有多 Agent 系统的终止条件、消息格式校验，都是在防这两件事。

**遗产**：证明"对话本身可以充当任务分解器"，但也暴露了无约束对话的低效与不可控。今天生产 Agent 里几乎找不到裸 role-play 了，但"用一段 prompt 定义子 Agent 的职责边界"这一基本手法，正是 inception prompting 的直系后代。

#### MetaGPT (2023)：给协作装上流水线——SOP 与 artifact

**困境**：CAMEL 式自由对话产出的代码没法用——需求漂移、接口对不上、没人写文档。MetaGPT 作者的洞察来自软件业百年教训：**混乱不是能力问题，是流程问题**。

**机制**：MetaGPT 把人类软件公司的 SOP（标准作业程序）直接编码为 Agent 流水线：产品经理产出 PRD、架构师画设计图（含 JSON 格式的 API 接口约定）、工程师按接口写代码、QA 写测试——每个角色只消费上游的标准化文档，只产出自己职责内的 artifact。关键机制是**结构化通信**：Agent 之间传的不是聊天记录，而是带 schema 的文档；上游改需求，下游按 diff 更新。这相当于把"对话式协作"降维成"装配线协作"。

**证据**：在小型项目生成上，MetaGPT 报告显著低于人类团队的 token 成本即可产出完整 PRD+设计+代码三件套，HumanEval 类基准上超过当时主流单 Agent 与对话式框架；更重要的是错误传播分析——自由对话的错误会级联放大，而 SOP 的 schema 校验能在接口处拦截。

**遗产**："plan 是 artifact 而非对话消息"由此成为工程共识——七家的 plan 文件落盘（Ch9.2.1 形态3）、PRD/设计文档先行，都是这条思路。局限同样明显：SOP 硬编码导致灵活性差，超出预设流程的任务就傻眼——这正是 AutoGen 要解放的。

#### AutoGen (2023)：把协作做成编程语言——Conversable Agent 与对话编程

**困境**：CAMEL 只有一种拓扑，MetaGPT 只有一条流水线。真实应用需要的组合千奇百怪：有的要人审批，有的要代码沙箱，有的要三个专家辩论。能不能有一个**可编程的多 Agent 运行时**，让开发者自由拼装？

**机制**：Microsoft 的 AutoGen 提出了 **Conversable Agent** 抽象——每个 Agent = LLM + 人 + 工具的可配置组合，彼此之间通过统一的消息传递协作；编排逻辑从硬编码拓扑变成"对话编程"（conversation programming）：开发者用计算图描述 Agent 间谁能跟谁说话、何时插入人类介入（human-in-the-loop）、何时触发代码执行器。`GroupChatManager` 用可插拔的 speaker selection 策略决定下一个发言者——这是第一次把"谁来说话"变成显式的策略选择而非固定轮转。

**证据**：论文以数学解题、检索增强问答、决策制定等六类应用展示同一套原语覆盖从双 Agent 到人机混合的广谱场景；后续社区生态（数百个示例应用）成为它影响力的更好证明。

**遗产**：七家生产实现里的"子 Agent 即配置对象"、工具注入、人工审批钩子，都能看到 Conversable Agent 的影子。代价是自由度过高——对话可能发散，调试困难，这个痛点由 CrewAI 和 LangGraph 从两个方向收敛。

#### CrewAI → LangGraph (2023–2024)：易用性与可控性的两极收敛

两者都是对 AutoGen 的收敛性反动，方向却相反。**CrewAI** 把自由对话压缩成声明式任务清单：`Crew → Agent(role, goal, backstory) → Task` 三级对象，顺序/层级执行，开发者像排班一样指派工作——上手十分钟，但复杂分支与回退难以表达。**LangGraph** 则反向加码可控性：放弃"对话即编排"，把整个多 Agent 系统**显式建模为状态图**（StateGraph：节点=Agent 或函数，边=转移条件），原生支持 cycle（迭代修正）、checkpoint（每步持久化）、`interrupt_before/after`（人在环中断点）与时间旅行调试（回放任意历史状态）。LangGraph 的 checkpoint 思想对本书尤其重要——它是 Ch7 Session 持久化与 Ch3 可恢复 Loop 在框架侧的同构物。两者的分化本质是一个问题的两面：**协作的控制流该藏在运行时里，还是该摊开成数据结构？**生产界的回答偏向后者——可观测、可恢复、可审计，这三样恰好是 Ch7/Ch10 的全部主题。

#### 多 Agent 值不值？(2024–2025)：从框架竞赛到实证清算

框架竞赛打了两年，一直没人认真回答性价比问题。2024 年起三份工作给出了互补的量化答案：

- **More Agents Is All You Need（Li et al., arXiv:2402.05120）**：最朴素的扩展律——多个 Agent 实例各自独立解题然后**多数投票**，性能随实例数单调上升（在 GSM8K 等基准上）。它证明"多 Agent"至少在无通信开销的退化形式下有真实收益，但也暗示收益来源主要是方差削减（类似 self-consistency），而非"分工智慧"。
- **Anthropic《How We Built Our Multi-Agent Research System》（2025-06）**：第一个生产级正方证词。Orchestrator-Worker 让研究类任务的评测表现较单 Agent 提升 **约 90%**——因为"先并行撒网搜集、再汇总"天然匹配多 Agent；但账单同样惊人：多 Agent 系统 token 消耗约为普通聊天的 **15×**、单 Agent 的 4×，且需要专门教 orchestrator 如何委派、如何防止 worker 重复劳动。
- **Cognition《Don't Build Multi-Agents》（同月）**：最锋利的反方檄文。两条原则——①**共享完整上下文**：分头行动的 Agent 各持残缺语境，必然做出互相冲突的隐含决策；②**行动携带隐含决策**：编辑 A 文件的方式已经暗含了对 B 文件的假设，而这些假设无法通过消息同步。结论：当前模型做不好真·多 Agent 编码，推荐单线程线性 Agent + 上下文压缩（Devin 的路线）。

三份合读的结论不是站队，而是**分界条件**：任务可并行且子任务弱耦合（搜索、调研、批量探索）→ 多 Agent 吃肉；任务强耦合、动作不可逆（编码、重构）→ 单线程保平安。这张判决书将在 9.1.4 的拓扑选型与 9.3 的源码对证中反复引用——七家"Orchestrator-Worker 为上限、禁嵌套、子代理继承父上下文投影"的三件套，就是同时吸收三方后的工程合成。

### 9.1.3 规划 Lineage：从隐式 ReAct 到显式 Skill 库

规划（Planning）是另一条独立演进线，与多 Agent 在 2024 年会合：

```
2022-10  ReAct (Yao et al., ICLR 2023)
           Thought → Act → Observe 交替，规划隐式在 prompt 的 Thought 中
           └── 无显式 plan 产物，失败靠下一轮 Thought 自愈
                │
2023-05  Plan-and-Execute (BabyAGI / AutoGPT 改进版, 2023-05)
           显式两阶段：Planner 产出 plan → Executor 按 plan 执行 → Replanner 修正
           └── 首次把规划做成"可 review 的中间产物"，plan 可被人类检查
                │  问题：plan 与执行分离后，执行偏离 plan 无自动纠偏
                │
2023-08  ReWOO (Xu et al., arXiv:2305.18323)
           Reason Without Observation：先产出完整 plan（含工具参数），再批量执行，最后整合
           └── 把"交替式 ReAct"改为"批处理式"：减少 LLM 调用次数，plan 可一次性审计
                │
2023-05  Voyager (Wang et al., NeurIPS 2023)
           Curriculum → CodeGen → Execute → Skill Library (向量化存储可复用技能)
           └── 首次把规划的产出物（skill）做成"可积累、可检索、可复用的库"
                │  Loop 从单任务变为终身学习：成功轨迹 → skill → 下次任务的 plan 素材
                │
2024–2026  七家生产规划
           TodoWrite / task.txt / Plan artifact / Workflow / Goal 四级
           └── 规划从"prompt 技巧"彻底变为"工具 + 文件 + 状态机"
```

| 年代 | 里程碑 | 核心贡献 | 对 Planner 设计的遗产 |
|------|--------|----------|----------------------|
| 2022-10 | **ReAct** | `Thought → Act → Observe` 交替，规划隐式 | 奠定"边想边动"范式；但规划不可审计、不可回滚 |
| 2023-05 | **Plan-Execute** | `Planner → Executor → Replanner` 两阶段，显式 plan | 首次把 plan 做成中间 artifact，人类可 review；成为后续所有显式规划的原型 |
| 2023-05 | **ReWOO** | 先产完整 plan（含参数），再批量执行，token 效率提升约数倍 | 证明"规划与执行解耦"可省 token；但执行期无法根据中间结果动态调整 |
| 2023-05 | **Voyager** | `Skill Library`：成功代码固化为可检索技能，自动课程驱动 | 首次把规划产出物"资产化"，plan 不再是一次性文本而是可复用知识 |

**从 ReAct 到 ReWOO：一次"先想完再做"的结构性反叛**。ReAct 的规划藏在每一步的 Thought 里（机制见 Ch3.1.2），优点是灵活、缺点是三重浪费：每步都要重新采样整个上下文（贵）、中间观察反复进 prompt（更贵）、且 plan 只存在于生成过程中——人类既不能提前审查，也不能事后审计。Plan-and-Solve 提示法与 BabyAGI 这类工程实现把方向倒过来：**先用一次强模型调用产出完整计划，再逐项执行**，计划成为可 review 的中间产物。ReWOO（Reason Without Observation）把这个思想推到极致并给出了量化论证：Planner 一次性产出**变量化的 DAG 计划**——`#E1 = Search[谁写了 X]`、`#E2 = Lookup[#E1 的国籍首都]`——后续步骤引用变量占位而非真实观察值；Worker 按拓扑序批量执行，Solver 最后整合。因为执行阶段不再把中间观察塞回大上下文，token 消耗较交替式下降约一个数量级内的数倍，且对观察噪声更鲁棒。代价同样明确：**计划在执行前就冻结了**，中途发现 #E1 的结果出乎意料也无法改道——这个"动态性 vs 效率"的两难，正是七家最终选择折中方案（TodoWrite 可增量更新 + hop 内仍走 ReAct）的直接原因。

> ** lineage 会合点**：ReWOO 的"批量规划" + Voyager 的"技能库"（机制精读见 Ch3.1.2）→ LangGraph 的"图状态" → 七家的"TodoWrite/task/plan 文件"三件套。**共识：plan 必须是可持久化、可 diff、可回滚的 artifact，而非对话消息**。

### 9.1.4 编排拓扑 lineage：三种范式的分化

```
Orchestrator-Worker (主从)
   主 Agent 负责分解与汇总，Worker 只读或隔离写
   代表：Claude AgentTool + TodoWrite, Codex collaboration-mode: orchestrator
   优点：主 Agent 拥有全局视图，易保证一致性
   缺点：主 Agent 成为瓶颈，Worker 间无法直接通信
        │
   vs
Swarm (去中心化群)
   多个对等 Agent 通过共享上下文或消息总线协作，无显式主从
   代表：Claude swarm/ + spawnTeammate(team_name), Codex swarm 模板
   优点：去中心化，扩展性好
   缺点：一致性需额外协议，易出现"谁说了算"冲突
        │
   vs
Hierarchical (分层)
   树状委托：Root → Sub-agent → Sub-sub-agent（但生产级禁止超过 1 层嵌套）
   代表：DeepSeek Workflow → Jobs, Grok SchedulerHandle 树
   优点：可表达复杂任务分解
   缺点：嵌套导致上下文爆炸与权限继承复杂，七家一致禁止嵌套 teammate
```

**多 Agent 是否值得：2024–2025 实证的工程归纳**。严格说，目前不存在一个权威基准系统性地回答"什么任务该用什么拓扑"——SWE-bench 测的是单 Agent 修复能力，多 Agent 的证据来自三份互相补充的工作（9.1.2 已精读：More Agents 扩展律、Anthropic 生产实测、Cognition 反方论证）。把它们的结论按任务类型归纳，得到下表——注意这是**工程经验归纳而非单一基准结果**，引用时请注明来源：

| 任务类型 | 单 Agent | Orchestrator-Worker | Swarm | 最优拓扑 | 依据 |
|----------|----------|---------------------|-------|----------|------|
| 单文件 bug 修复（≤10 步） | **最优**（开销最小） | 过度设计 | 过度设计 | 单 Agent | Cognition 原则①：强耦合编辑需共享完整上下文 |
| 跨 5+ 文件的探索/搜集 | 次优（串行慢） | **最优**（并行搜集） | 可选 | Orchestrator-Worker | Anthropic：研究类任务提速约 90%，代价 token ~15× |
| 大规模独立子问题批量求解 | 受限于方差 | **最优**（多数投票/分头尝试） | 过度设计 | Orchestrator-Worker（退化形式） | More Agents Is All You Need：采样投票单调增益 |
| 多角色协作（reviewer/tester/implementer） | 无法表达 | 可表达但主 Agent 瓶颈 | 理论最优、实践罕见 | Swarm（实验性） | 九家中无一生产化自由 Swarm（见 9.3） |
| 需严格 SOP 的企业流程 | 无法保证 | 可通过 plan 文件约束 | 难约束 | Hierarchical（1 层） | MetaGPT artifact 化遗产；嵌套超一层七家一致禁止 |

---

## 9.2 原理深潜：显式状态容器、隔离模型、通信与钩子

### 9.2.1 Planner：显式状态容器的三种形态

规划的本质是"**把未来要做的事从模型隐式记忆中抽出来，写到外部可观测、可修改、可持久化的状态容器中**"。七家给出三种容器，按"可审计性"递增：

```
形态1：Message（隐式，最弱）
   plan 仅存于对话消息中（assistant 的 Thought 或 text）
   └── 问题：不可 diff、不可回滚、压缩时可能丢失、无法被人类 pre-review
   └── 代表：早期 ReAct / Pi 默认（无 TodoWrite 时）

形态2：TodoWrite / Task 清单（显式，中等）
   plan 是工具调用产生的结构化清单，存于 ContextManager 或 task 文件
   └── 优点：可审计、可恢复、支持并发更新时的冲突检测
   └── 代表：Claude TodoWriteTool, OpenCode tool/task.ts, DeepSeek dsh-todo

形态3：Plan Artifact 文件（显式，最强）
   plan 是落盘文件（.agent/plans/*.md / .opencode/plans/*.md），人类可 review、可 diff、可回滚
   └── 优点：最强可审计，支持 plan 模式的权限隔离（plan 阶段禁止 edit）
   └── 代表：Claude Plan(isInPlanMode()), OpenCode plan_enter/plan_exit, DeepSeek dsh-plan-mode
```

#### 形式化：Planner 状态机

```ts
// 伪 TS，综合 Claude TodoWrite + OpenCode task.ts + DeepSeek dsh-plan-mode
type PlanItem = {
  id: string;
  content: string;          // 任务描述
  status: 'pending' | 'in_progress' | 'completed' | 'cancelled';
  priority: 'high' | 'medium' | 'low';
  assignee?: 'main' | string; // 分配给主 Agent 或某 subagent
};

type PlanState =
  | { kind: 'idle' }                                    // 无规划
  | { kind: 'planning'; items: PlanItem[]; mode: 'plan' } // plan 模式：只读探索，产出 plan 文件
  | { kind: 'executing'; items: PlanItem[]; mode: 'build' } // build 模式：按 plan 执行
  | { kind: 'reviewing'; items: PlanItem[]; diff: string }; // 产出 diff 供人类 review

// 状态迁移
const plannerTransitions = {
  'idle → planning':      '用户 /plan 或大任务自动触发 plan_enter',
  'planning → reviewing': 'Plan 文件落盘（.agent/plans/*.md），调 ask_user_question',
  'reviewing → executing':'用户确认 plan_exit',
  'executing → idle':     '所有 items completed 或用户取消',
  'executing → planning': '执行中发现 plan 缺陷，replan（ReWOO 式修正）',
};

// 不变量
// I1 plan 文件是唯一真源（single source of truth），TodoWrite 是其内存投影
// I2 plan 模式下所有 edit 工具被 deny（权限晶格保证），仅允许 read/grep/glob/explore subagent
// I3 每个 PlanItem 的 status 变更必须通过 TodoWrite 工具（可审计），不可直接改内存
```

#### ASCII：规划状态机图

```
                    /plan / plan_enter
             ┌─────────────────────────┐
             │                         ▼
        ┌────────┐  产出 .md 文件  ┌──────────┐  用户确认  ┌───────────┐
        │  idle  │ ──────────────► │ planning │ ─────────► │ reviewing │
        │        │                 │ (plan)   │            │           │
        └───┬────┘                 └──────────┘            └─────┬─────┘
            │  ▲                       │  ▲                     │
            │  │  全部完成             │  │ replan              │ plan_exit
            │  │                       │  │                     ▼
            │  │                  ┌──────────┐            ┌───────────┐
            └──┴──────────────────│executing │◄───────────│ executing │
                                 │ (build)  │  TodoWrite │ (build)   │
                                 └──────────┘   更新      └───────────┘
                                      │
                                 TodoWrite status:
                                   pending → in_progress → completed
                                      │
                                 若某 item 失败 → cancelled + 触发 replan
```

#### 三家 Planner 容器对比

| 家 | 规划工具 | 容器位置 | 粒度 | plan 模式隔离 |
|----|----------|----------|------|---------------|
| Claude | `TodoWriteTool` + `Task*Tool` + `Plan(isInPlanMode())` | 内存 TodoWrite + `.agent/plans/*.md` 文件 | 任务级（高/中/低优先级） | `isInPlanMode()` 时所有 edit 工具 deny，仅 `read/grep/glob/agent(explore)` 允许 |
| OpenCode | `tool/task.ts` + `task.txt` + `todo` + `plan_enter/plan_exit` | `task.txt` 文件 + `Session.fork()` 血缘 | 任务 + 会话级 | `build` 允许 `question/plan_enter`，`plan` 禁止所有 `edit` 仅允许 `.opencode/plans/*.md` |
| DeepSeek | `dsh-goal` → `dsh-plan-mode` → `dsh-todo` → `dsh-workflow` | `Goal → Plan → Todo → Workflow → Jobs` 四级 | 目标→计划→清单→工作流 | `dsh-plan-mode` 独立 package，plan 产出后经 `Inbox` 注入执行 |

> **原则**：`plan 是 artifact（文件），不是 message`。Claude 的 `Plan` 产出 `.agent/plans/*.md`，OpenCode 的 `plan_enter/plan_exit` 受限工具，都在保证"规划可 review、可 diff、可回滚"。Pi 无此机制是其作为教学实现的刻意简化。

#### TodoWrite 的并发语义（Claude 最精确）

```ts
// Claude: src/tools/TodoWriteTool (伪代码)
// 关键：TodoWrite 是"追加式"而非"覆盖式"，保证多 Agent 并发更新不丢
type TodoWriteInput = {
  todos: Array<{
    content: string;
    status: 'pending' | 'in_progress' | 'completed';
    priority: 'high' | 'medium' | 'low';
    // 注意：无 id，靠 content 去重；并发时以 content 为 key 合并
  }>;
};

// 调用示例：主 Agent 派发两个 explore subagent 后更新
// Hop 1: TodoWrite([{content:"探索 auth 模块", status:"in_progress", priority:"high"},
//                   {content:"探索 payment 模块", status:"pending", priority:"high"}])
// Hop 3: subagent-A 完成 → TodoWrite([{content:"探索 auth 模块", status:"completed", ...}])
// Hop 3: subagent-B 完成 → TodoWrite([{content:"探索 payment 模块", status:"completed", ...}])

// 失败案例：若 TodoWrite 是覆盖式而非合并式，两个 subagent 同时完成时会丢失对方的更新
// Claude 解法：TodoWrite 基于 content 的 upsert 语义 + Session.append 的追加式保证
```

### 9.2.2 子 Agent 隔离模型：worktree vs Actor vs Scope

隔离回答"**子 Agent 的副作用能否被关住、能否与主 Agent 并行而不互踩**"。七家给出三档隔离，按强度递增：

```
隔离强度递增 ──────────────────────────────────────────────►

同进程协程（最弱）          Scope 作用域（中等）            worktree/Actor（最强）
Pi / OpenCode fork         DeepSeek Cordis Scope          Claude worktree/remote
                                                          Grok btrfs/overlay
                                                          Grok ChatStateActor

成本递增 ──────────────────────────────────────────────────►
~0ms                      ~1ms (Scope 创建)                ~50-100ms (snapshot)
```

#### 三种隔离的形式化对比

| 维度 | 同进程协程 (Pi) | Scope 作用域 (DeepSeek) | worktree (Claude/Grok) | Actor (Grok) |
|------|----------------|------------------------|----------------------|--------------|
| **载体** | 同进程 `agentLoop()` 协程 | `Cordis Scope.createScope(loopCtx, this)` | `git worktree` + `btrfs snapshot` / `overlayfs` | `tokio::task` 单任务拥有 `ChatState` |
| **文件隔离** | 无（共享同一 worktree） | 无（共享文件，但 Scope 退出时收回句柄） | **强**：COW 分支，各写各的分支，完成后 merge | 无（状态隔离，文件仍共享） |
| **内存隔离** | 无（共享 `AgentContext.messages`） | **中**：Scope 内注册的服务随 Scope 退出自动 dispose | **强**：独立 `Session.fork()` + 独立 `ContextManager` | **强**：`ChatState` 仅单 task 可写，外部仅 `Command` |
| **权限隔离** | 无（继承主 Agent 权限） | **有**：`Scope` 可覆盖 `PermissionContext` | **有**：`subagent-permissions.ts` 独立规则 + `workerPermissionContext=acceptEdits` | **有**：`PromptContext{audience:Primary\|Subagent}` |
| **生命周期** | 随主循环结束 | 随 `Scope` 退出自动收回（`Scope.createScope` 的 RAII 语义） | 显式 `createAgentWorktree()` + `teleportToRemote()`，需手动清理 | 随 `ChatStateActor` task 结束 |
| **启动成本** | ~0ms | ~1ms | ~50-100ms | ~0ms（task 已存在） |
| **适用** | 只读 explore 子 Agent | 插件化工具隔离 | **并行写** subagent（避免 `write_file` 冲突） | 高并发状态隔离 |

#### 隔离对比的时序图（worktree 形态，Claude/Grok）

```
主 Agent                     Subagent-A (worktree-A)         Subagent-B (worktree-B)         FS
   │                              │                              │                          │
   │ createAgentWorktree()        │                              │                          │
   │─────────────────────────────────────────────────────────────────────────────────────►│
   │ btrfs snapshot / overlayfs   │                              │                          │
   │ worktree-A @ /tmp/wt-A       │                              │                          │
   │ worktree-B @ /tmp/wt-B       │                              │                          │
   │                              │                              │                          │
   │ spawn AgentTool              │                              │                          │
   │─────────────────────────────►│                              │                          │
   │                              │ read_file("src/auth.ts")     │                          │
   │                              │─────────────────────────────►│                          │
   │                              │◄─────────────────────────────│                          │
   │                              │ write_file("src/auth.ts")    │                          │
   │                              │──────────►│ (仅写 worktree-A) │                          │
   │                              │                              │ write_file("src/pay.ts")   │
   │                              │                              │──────────►│ (仅写 worktree-B)│
   │                              │                              │                          │
   │                              │◄─────────────────────────────│                          │
   │◄─────────────────────────────│                              │                          │
   │ finalizeAgentTool()          │                              │                          │
   │ 收集结果，merge 回主 worktree │                              │                          │
   │─────────────────────────────────────────────────────────────────────────────────────►│
   │ merge/conflict 检测          │                              │                          │
   │ 若冲突 → 人类介入或自动取主    │                              │                          │
```

> **为什么 worktree 必要**：若仅有 bwrap（进程级沙箱）而无 worktree（文件系统级），两个 subagent 并行 `write_file("src/a.ts")` 仍会写同一 inode，后写者覆盖前写者，丢失更新。Grok 的 `xai-fast-worktree` 与 Claude 的 `createAgentWorktree()` 正是为解决此问题——**bwrap 隔离单次执行，worktree 隔离整个会话的文件集，二者正交且互补**（见 Ch4.2.4）。

#### Scope 隔离的精髓（DeepSeek Cordis）

```ts
// DeepSeek: packages/core/agent-loop/src/agent.ts:64 + Cordis Scope
import { Scope } from 'cordis';

// 每个 Agent（含 subagent）拥有独立 Scope，Scope 退出时自动收回所有注册的服务
class ReactLoopAgent {
  constructor(private scope: Scope) {}

  spawnSubagent(task: string) {
    // 子 Agent 的 Scope 以主 Agent 的 Scope 为父，生命周期随主 Agent 退出而收回
    const subScope = this.scope.createScope(/* loopCtx */ {}, this);
    // 在 subScope 内注册子 Agent 专用工具（隔离）
    subScope.plugin(dshToolRead);
    subScope.plugin(dshToolWrite);
    // 子 Agent 结束时，subScope.dispose() 自动清理所有工具句柄，无泄漏
    return new ReactLoopAgent(subScope);
  }
}

// 关键不变量：
// 1. Scope 树 = Agent 树，Scope 退出 → Agent 退出 → 所有工具句柄收回
// 2. 子 Scope 可覆盖父 Scope 的 PermissionContext，实现"子 Agent 权限独立"
// 3. 轻量：Scope 创建仅 ~1ms，适合高频派发短任务
```

#### Actor 隔离的精髓（Grok ChatStateActor）

```rust
// Grok: crates/codegen/xai-chat-state/src/actor/mod.rs (伪 Rust)
pub struct ChatStateActor {
    state: ChatState, // conversation: Vec<ConversationItem> + UsageLedger + turn_capture
    rx: mpsc::Receiver<Command>,
}
pub enum Command {
    Append(Message),
    SpawnSubagent { task: String, reply: Oneshot<SubagentHandle> },
    GetState(Oneshot<ChatStateSnapshot>),
}

// ChatState 仅被单 tokio task 拥有，外部仅发 Command，无锁
// forkSubagent 时冻结 renderedSystemPrompt 保证 prompt cache 命中
impl ChatStateActor {
    async fn fork_subagent(&mut self, task: String) -> SubagentHandle {
        let snapshot = self.state.capture_from(self.state.turn_start_offset);
        // 子 Agent 继承冻结的 system prompt，cache 前缀一致
        SubagentHandle { snapshot, parent_scheduler: self.scheduler_handle.clone() }
    }
}
```

### 9.2.3 通信机制：Inbox vs InterAgentCommunication vs EventV2Bridge

通信回答"**子 Agent 的结果如何回到主 Agent，主 Agent 如何在中途 steer 子 Agent**"。七家给出三类机制：

#### 三类通信的对比

| 家 | 通信载体 | 粒度 | 方向 | 关键文件 |
|----|----------|------|------|----------|
| DeepSeek | `Inbox.splice(target)` + `Inbox.nextStep` | **最细**：`next-turn` vs `next-step` 区分 | 双向：主→子（`steer`）/ 子→主（`tool_result`） | `packages/core/agent/src/inbox.ts` |
| Codex | `InterAgentCommunication` (enum 变体) + `InputQueue` | 中：`TurnInput{UserInput\|InterAgentCommunication}` | 双向：`Agent → Agent` 消息 | `codex-rs/core/src/session/input_queue.rs:19` |
| Claude | `InterAgentCommunication` + `agentToolUtils.finalizeAgentTool/classifyHandoffIfNeeded` | 中：`agentToolUtils` 统一收敛 | 子→主为主，`spawnTeammate` 支持主→子 | `src/tools/AgentTool/` + `src/utils/teammate.ts` |
| OpenCode | `EventV2Bridge` | 粗：事件总线广播 | 广播式 | `packages/opencode/src/tool/task.ts` |
| Grok | `TurnInput contributors` + `SchedulerHandle` 树 | 中：`contributors` 列表 | 树状广播 | `xai-agent-lifecycle/local/{registry,contributors}` |
| Pi | `hooks-and-events` + `resources` | 粗：回调式注入 | 单向：子→主 | `packages/agent/src/types.ts` |

#### DeepSeek Inbox 的精确语义（七家最细）

```ts
// DeepSeek: packages/core/agent/src/inbox.ts (伪代码，见 Ch3.2.4.2)
type Target = 'next-turn' | 'next-step';
class Inbox {
  private queue: Message[] = [];
  private wake: { requested: boolean; afterAbort: boolean } = { requested: false, afterAbort: false };

  send(msg: Message)    { this.queue.push(msg); this.wake.requested = true; }
  steer(msg: Message)   { this.splice('next-step', msg); }   // 采样中打断，插入当前 step 末尾
  inject(msg: Message)  { this.splice('next-turn', msg); }   // 下一 turn 起点注入
  followup(msg: Message){ this.splice('next-turn', msg); }   // 模型结束后的跟进

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

// 主 Agent 派发 subagent 后的通信时序
// 主 Agent                    Subagent-A                  Inbox
//   │  spawnSubagent("探索 auth") │                          │
//   │──────────────────────────►│                          │
//   │                           │  read_file + grep ...     │
//   │                           │─────────────────────────►│
//   │                           │  完成，tool_result        │
//   │                           │◄─────────────────────────│
//   │  Inbox.drain(next-step)   │                          │
//   │◄──────────────────────────────────────────────────────│
//   │  将 subagent 结果拼到主 Agent 的 tool_results 后      │
//   │  重新 buildRequest（含 subagent 产出）                │
```

#### Codex InterAgentCommunication

```rust
// Codex: codex-rs/core/src/session/input_queue.rs:19
pub enum TurnInput {
    UserInput(UserInput),
    InterAgentCommunication(InterAgentCommunication),
}
pub struct InterAgentCommunication {
    pub from_agent: AgentId,
    pub to_agent: AgentId,
    pub payload: AgentMessage,
}
// 每 turn 起点 drain_pending_input() 统一排空 InputQueue
// 协作模式通过 AgentResolver 解析目标 Agent
```

#### OpenCode EventV2Bridge（最简）

```ts
// OpenCode: packages/opencode/src/tool/task.ts + EventV2Bridge
// 子 Agent 的产出通过事件总线广播，主 Agent 订阅
// 优点：解耦，任意 Agent 可监听
// 缺点：无精确的 next-step/next-turn 语义，时序靠事件顺序隐式保证
```

> **通信的时序保证**：DeepSeek 的 `Inbox.splice(next-step)` 是唯一能在"采样中"插入消息的机制（对应 Ch3 的 `wakingAfterAbort` 闩锁）。Codex 的 `InputQueue` 每 turn 起点排空，turn 内不抢占，时序保证较弱但实现简单。OpenCode 的 `EventV2Bridge` 最简，适合单机多 Agent，跨机需额外一致性协议。

### 9.2.4 钩子：waterfall vs before/after

钩子回答"**协作的生命周期事件由谁、以何种顺序拦截**"。七家分两派：

#### 两派钩子的对比

| 维度 | waterfall (DeepSeek Cordis) | before/after (Pi / Claude) |
|------|---------------------------|---------------------------|
| **模型** | `waterfall('agent/pre-step')` → 插件链依次改写，返回值向后传递 | `beforeToolCall` / `afterToolCall` 配对，独立调用 |
| **可组合性** | **强**：多个插件可串联改写同一事件（如权限插件 deny + 日志插件记录） | **弱**：每个钩子独立，无法感知其他钩子的改写 |
| **拦截能力** | 插件可 `return reject` 阻断后续（`decision{enter\|reject}`） | 仅 `before` 可阻断，`after` 仅通知 |
| **代表** | DeepSeek `waterfall('agent/pre-step'/'agent/request'/'agent/request-error'/'agent/turn-stopping')` | Pi `beforeToolCall/afterToolCall/prepareNextTurn/shouldStopAfterTurn`, Claude `PreCompact/PostCompact/SessionStart/Stop` |
| **复杂度** | 高：需理解 waterfall 的"瀑布传递"语义 | 低：直观的配对回调 |

#### DeepSeek Cordis waterfall 的全貌

```ts
// DeepSeek: packages/core/agent-loop/src/agent.ts:64 附近
// waterfall 是 Cordis 事件总线的核心原语：事件依次经过每个插件，插件可改写或阻断
import { waterfall } from 'cordis';

// 1. pre-step：权限决策（子 Agent 隔离的关键）
waterfall('agent/pre-step', async (ctx, next) => {
  const decision = await permissionPlugin.check(ctx.toolCalls);
  if (decision === 'reject') return { kind: 'blocked', reason: 'permission denied' };
  return next(); // 向后传递
});

// 2. request：LLM 调用改写（适配器剥除后插件看到干净的 LlmCallConfig）
waterfall('agent/request', async (req, next) => {
  const cleaned = stripAdapterDefaults(req); // 去除 adapterDefaults
  return next(cleaned);
});

// 3. request-error：失败归一与重试决策
waterfall('agent/request-error', async (err, next) => {
  const normalized = normalizeLlmFailure(err);
  if (normalized.retryable) return { kind: 'retry', afterMs: normalized.retryAfterMs };
  return next(err);
});

// 4. turn-stopping：协作回合何时结束
waterfall('agent/turn-stopping', async (ctx, next) => {
  if (ctx.inbox.nextStep.length === 0) return { kind: 'break' }; // 无待处理即结束
  if (ctx.turnEnds === 'max-tokens') return { kind: 'continue', sticky: true }; // 黏性保证
  return next();
});

// Grok 的对等：ReminderPolicy + PromptContext{audience:Primary|Subagent}
// Codex 的对等：ExtensionData/TurnInputContext/TurnInputEnvironment + agent/pre-step
// Pi 的对等：AgentLoopConfig{beforeToolCall/afterToolCall/prepareNextTurn/shouldStopAfterTurn}
```

#### Claude / Pi 的 before/after 钩子

```ts
// Pi: packages/agent/src/types.ts AgentLoopConfig
type AgentLoopConfig = {
  beforeToolCall?: (toolCall: ToolCall) => Promise<{ allow: boolean; reason?: string }>;
  afterToolCall?: (toolCall: ToolCall, result: ToolResult) => Promise<void>;
  prepareNextTurn?: (ctx: AgentContext) => Promise<void>;
  shouldStopAfterTurn?: (ctx: AgentContext) => Promise<boolean>;
};

// Claude: src/services/compact/compact.ts:387 compactConversation()
// PreCompact hooks → streamCompactSummary → PostCompact hooks → SessionStart hooks
// 钩子 waterfall vs before/after 的本质差异：
// - waterfall：事件在插件链中"流动"，每个插件看到前一个插件的改写结果
// - before/after：事件在固定点"触发"，插件间无流动，仅配对
```

> **选型口诀**：需"多插件串联改写同一事件"（如权限+审计+重试）→ `waterfall`；仅需"单点拦截"（如日志）→ `before/after`。DeepSeek 选前者因其 60+ 插件需串联，Pi 选后者因其教学定位追求直观。

---

## 9.3 对证分解：九家源码对证

### 9.3.1 总览对比表

| 家 | 子 Agent 载体 | 隔离模型 | 发现机制 | 通信 | 规划容器 | 钩子 | 嵌套 |
|----|--------------|---------|---------|------|---------|------|------|
| **Claude** | `src/tools/AgentTool/` 60+ 类型 (`builtInAgents.ts`) + `LocalAgentTask{registerAsyncAgent/registerAgentForeground}` + `spawnTeammate()` | `isolation: worktree\|remote` (`createAgentWorktree()` 临时 worktree, `teleportToRemote()` CCR), `runWithAgentContext(parentSessionId)` | `~/.claude/agents/` + `AgentTool.effectiveType` 缺省 `fork`（cache-identical 前缀） | `InterAgentCommunication` + `agentToolUtils.finalizeAgentTool/classifyHandoffIfNeeded` | `TodoWriteTool` + `Task*Tool` + `AskUserQuestionTool` + `Plan(isInPlanMode())` → `.agent/plans/*.md` | `PreCompact/PostCompact/SessionStart/Stop` | 禁止嵌套 teammate (`isTeammate()/isInProcessTeammate()`) |
| **Codex** | `codex-rs/agent/registry.rs/status.rs/control.rs/role.rs` + `tasks/regular.rs` vs `session/realtime_conversation.rs` | 无 worktree，`collaboration-mode-templates/` 模板隔离 | `AgentResolver` | `session/input_queue.rs:19 InterAgentCommunication` 变体 | `plugins/` + `hooks/hook_runtime.rs` + `ExtensionData` | `ExtensionData/TurnInputContext/TurnInputEnvironment` + `agent/pre-step` | 模板级隔离，无显式嵌套 |
| **Grok** | `xai-grok-agent/discovery.rs SubagentEntry{source}` + `xai-agent-lifecycle/local/{registry,contributors}` | `xai-grok-workspace SchedulerHandle` + `parent_scheduler_handle`, `xai-fast-worktree btrfs/overlay` | `AgentBuilder.parent_scheduler_handle` | `xai-agent-lifecycle` 的 `TurnInput contributors` | `xai-workflow` + `background_workflows_enabled` 闸控 `Workflow/GoalUpdate` 互斥 | `ReminderPolicy` + `PromptContext{audience:Primary\|Subagent}` | `SchedulerHandle` 树，1 层 |
| **DeepSeek** | `dsh-subagent` + `dsh-tool-subagent/subagent-control` | `Cordis Scope.createScope(loopCtx, this)` 生命周期随 Agent 退出收回 | `preset.yml` 决定子 agent 组合 | `Inbox.splice(next-step)` | `dsh-goal/goal-round-driver` → `dsh-plan-mode` → `dsh-todo` → `dsh-workflow/worker-thread` → `dsh-jobs-local` 四级 | `waterfall('agent/turn-stopping'/'agent/pre-step'/'agent/request')` | Scope 树，禁止 teammate 嵌套 |
| **OpenCode** | `packages/opencode/src/agent/agent.ts:35 Info{mode:subagent\|primary\|all}` + `tool/task.ts` | `Session.fork()` + `subagent-permissions.ts` 权限继承 | `skill` 发现 | `EventV2Bridge` | `tool/task.ts` + `task.txt` + `todo` + `plan_enter/plan_exit` 受限工具 | `EventV2Bridge` + `Agent.steps` | `Info.mode` 控制，1 层 |
| **Pi** | `docs/book/23-subagents.md AgentTool{subagent_type}` 触发子 `agentLoop()` | 同进程协程，无文件隔离 | `coding-agent` 主 + `explore` 只读子 | `hooks-and-events` + `resources` | 无显式规划容器（消息隐式） | `beforeToolCall/afterToolCall/prepareNextTurn/shouldStopAfterTurn` | 同进程，无嵌套 |
| **Claw** | 占位（规划中） | — | — | — | `compact_after_turns=12` 粗糙阈值 | — | — |

> 一句话区分：**Claude 求全（60+ 类型 + worktree/remote 双隔离）、Codex 求系统（模板 + InputQueue）、Grok 求隔离（btrfs + Actor）、DeepSeek 求插件（Scope + 四级规划）、OpenCode 求现代（Effect + task 文件）、Pi 求可读（同进程协程）、Claw 占位**。

### 9.3.2 分家精读（逐行走读要点）

#### Claude — `src/tools/AgentTool/` 60+ 类型 + worktree/remote 双隔离

```ts
// 骨架（TS 伪代码，对应 src/tools/AgentTool/ + builtInAgents.ts + LocalAgentTask）
// 1. 子 Agent 类型注册（60+ 类型，cache-identical 前缀保证 prompt cache 命中）
import { builtInAgents } from './builtInAgents';
type AgentType = 'explore' | 'plan' | 'code-reviewer' | 'test-runner' | /* 60+ */;
type Isolation = 'worktree' | 'remote';

// AgentTool 定义
export const agentTool = buildTool({
  name: 'agent',
  description: 'Spawn a sub-agent to handle complex tasks',
  parameters: z.object({
    agent_type: z.string().describe('Sub-agent type, e.g. explore/plan'),
    prompt: z.string().describe('Task description for sub-agent'),
    isolation: z.enum(['worktree', 'remote']).optional(), // 隔离级别
  }),
  isConcurrencySafe: false, // 默认串行，避免并发 worktree 冲突
  execute: async ({ agent_type, prompt, isolation }, ctx) => {
    // 2. 发现：effectiveType 缺省 fork（cache-identical 前缀）
    const effectiveType = agent_type ?? 'fork';
    // 3. 隔离：按需创建 worktree 或 teleport 到远端
    let worktree: string | null = null;
    if (isolation === 'worktree') {
      worktree = await createAgentWorktree(ctx.sessionId); // 临时 worktree，btrfs/overlay
    } else if (isolation === 'remote') {
      worktree = await teleportToRemote(ctx.sessionId); // CCR 远端执行
    }
    // 4. 上下文隔离：子 Agent 继承冻结的 system prompt，cache 前缀一致
    const subCtx = await runWithAgentContext(ctx.parentSessionId, { worktree });
    // 5. 派生：LocalAgentTask 管理生命周期
    const task = new LocalAgentTask({
      agentType: effectiveType,
      prompt,
      worktree,
      workerPermissionContext: 'acceptEdits', // 子 Agent 权限独立
    });
    // 6. 执行：同步 2s 后 BackgroundHint，120s autoBackground，避免阻塞主循环
    const result = await task.registerAgentForeground(); // 或 registerAsyncAgent()
    // 7. 收敛：finalizeAgentTool 收集结果，classifyHandoffIfNeeded 判定是否需 handoff
    return agentToolUtils.finalizeAgentTool(result);
  },
});

// LocalAgentTask 细节（src/tools/AgentTool/LocalAgentTask.ts 附近）
class LocalAgentTask {
  async registerAgentForeground() {
    // 同步执行，2s 后提示可 background，120s 自动 background
    const timer1 = setTimeout(() => this.emit('BackgroundHint'), 2000);
    const timer2 = setTimeout(() => this.autoBackground(), 120_000);
    return this.run();
  }
  async registerAsyncAgent() {
    // 异步执行，主循环不阻塞，通过 Inbox 回填
    return this.spawn();
  }
  isTeammate() { return this.agentType === 'teammate'; }
  isInProcessTeammate() { return this.isTeammate() && this.worktree === null; }
  // 禁止嵌套 teammate，防止递归风暴
  assertNotNested() {
    if (this.isTeammate() && this.parent?.isTeammate()) throw new Error('Nested teammate forbidden');
  }
}

// Swarm 形态：spawnTeammate(team_name + name)
// src/utils/teammate.ts + src/swarm/
export function spawnTeammate(teamName: string, name: string, task: string) {
  // team_name 决定共享上下文，name 决定角色
  return agentTool.execute({ agent_type: 'teammate', prompt: task, isolation: 'worktree' });
}
```

**精读点**：

- **`isolation: worktree|remote` 双轨**：`worktree` 本地 COW 分支（<100ms），`remote` 通过 CCR(Claude Code Remote) 远端执行，适合长任务不阻塞本地。`createAgentWorktree()` 与 Grok 的 `xai-fast-worktree` 同策不同实现。
- **60+ 类型的本质是"prompt 模板库"**：`builtInAgents.ts` 每种类型对应不同的 `systemPrompt` 前缀 + 工具白名单（如 `explore` 仅 `read/grep/glob`，`plan` 仅 `read + ask_user_question`）。`effectiveType` 缺省 `fork` 时复用主 Agent 的 `systemPrompt` 前缀，保证 cache 命中。
- **禁止嵌套 teammate**：`isTeammate()/isInProcessTeammate()` 双检查，防止 `teammate → teammate → teammate` 递归风暴。这是所有 Hierarchical 拓扑的共同约束（DeepSeek Scope 树亦同）。
- **2s BackgroundHint + 120s autoBackground**：长任务不阻塞主循环的精妙设计——短任务同步等待，长任务自动转后台，主 Agent 可继续处理其他事项，通过 `Inbox` 回填结果。

#### Codex — `codex-rs/agent/registry.rs` + `collaboration-mode` + `InterAgentCommunication`

```rust
// 骨架（Rust 伪代码，对应 codex-rs/agent/ + session/input_queue.rs:19）
// 1. Agent 注册表
// codex-rs/agent/registry.rs
pub struct AgentRegistry {
    agents: HashMap<AgentId, AgentInfo>,
    resolver: AgentResolver, // 解析 agent 名称 → ID
}
pub struct AgentInfo {
    pub role: AgentRole,     // role.rs: reviewer/tester/implementer
    pub status: AgentStatus, // status.rs: idle/running/done
    pub control: AgentControl, // control.rs: 协作控制
}

// 2. 协作模式模板（无 worktree，靠模板隔离）
// collaboration-mode-templates/
pub enum CollaborationMode {
    Orchestrator, // 主从：主 Agent 派发，子 Agent 只读
    Swarm,        // 去中心化：多 Agent 对等协作
    Pair,         // 双人：driver/navigator
}

// 3. 通信：InterAgentCommunication 作为 TurnInput 变体
// codex-rs/core/src/session/input_queue.rs:19
pub enum TurnInput {
    UserInput(UserInput),
    InterAgentCommunication(InterAgentCommunication),
}
pub struct InterAgentCommunication {
    pub from: AgentId,
    pub to: AgentId,
    pub payload: String, // AgentMessage 序列化
}
impl InputQueue {
    pub fn push_inter_agent(&mut self, msg: InterAgentCommunication) {
        self.queue.push(TurnInput::InterAgentCommunication(msg));
    }
    pub fn drain_pending_input(&mut self) -> Vec<TurnInput> {
        // 每 turn 起点排空，turn 内不抢占
        std::mem::take(&mut self.queue)
    }
}

// 4. 双轨任务：regular vs realtime
// tasks/regular.rs vs session/realtime_conversation.rs
pub enum TaskKind {
    Regular,   // 常规 turn，一次性采样
    Realtime,  // 实时对话，支持用户在采样期间 steer（类似 DeepSeek Inbox.next-step）
}
```

**精读点**：

- **无 worktree 的代价与补偿**：Codex 不做文件系统隔离（与 Claude/Grok 差异最大），依赖 `collaboration-mode-templates/` 的"模板隔离"——每个 Agent 的 `role` 决定可见工具集，`Orchestrator` 模式下子 Agent 仅 `read/grep`，天然避免写冲突。但多写 subagent 并行时仍有冲突风险，需上层 `write_file` 串行化。
- **`InterAgentCommunication` 作为 `TurnInput` 变体**：与 `UserInput` 同级，每 turn 起点统一 `drain_pending_input()`，保证"Agent 间消息"与"用户消息"在同一队列中公平调度。粒度不如 DeepSeek 的 `next-step/next-turn` 精细，但实现简单。
- **`AgentResolver` 的发现机制**：类似 Claude 的 `~/.claude/agents/`，但 Codex 通过 `AgentResolver` 动态解析，支持 `collaboration-mode-templates/` 的模板化 Agent 定义。

#### Grok — `xai-grok-agent/discovery.rs SubagentEntry` + `xai-fast-worktree btrfs/overlay`

```rust
// 骨架（Rust 伪代码，对应 xai-grok-agent/discovery.rs + xai-fast-worktree + xai-grok-workspace）
// 1. 子 Agent 发现
// xai-grok-agent/discovery.rs
pub struct SubagentEntry {
    pub source: SubagentSource, // 来源：内置 / 插件 / 远端
    pub prompt_template: String,
    pub tool_filter: Vec<ToolKind>,
}
pub enum SubagentSource {
    Builtin,           // 内置 subagent
    Plugin(SkillInfo), // 插件提供的 subagent（list_skills_with_plugins）
    Remote(String),    // 远端 subagent
}

// 2. 调度器句柄树（Hierarchical 的载体）
// xai-grok-workspace
pub struct SchedulerHandle {
    pub id: SchedulerId,
    pub parent: Option<Arc<SchedulerHandle>>, // parent_scheduler_handle 形成树
}
impl AgentBuilder {
    pub fn with_parent_scheduler(mut self, parent: Arc<SchedulerHandle>) -> Self {
        self.parent_scheduler_handle = Some(parent);
        self
    }
    pub fn spawn_subagent(&self, entry: SubagentEntry) -> SubagentHandle {
        let child_scheduler = SchedulerHandle::new(Some(self.parent_scheduler_handle.clone()));
        // 子 Agent 继承父调度器，但拥有独立 worktree
        SubagentHandle { scheduler: child_scheduler, entry }
    }
}

// 3. 快速 worktree（btrfs/overlay COW）
// xai-fast-worktree
pub enum WorktreeBackend {
    Btrfs,   // btrfs snapshot，<50ms
    Overlay, // overlayfs，<100ms，回退方案
}
pub fn create_fast_worktree(backend: WorktreeBackend, base: &Path) -> PathBuf {
    match backend {
        WorktreeBackend::Btrfs => btrfs_snapshot(base),   // 利用 btrfs COW
        WorktreeBackend::Overlay => overlay_mount(base),   // 利用 overlayfs
    }
}

// 4. 状态隔离：ChatStateActor 单 task 拥有状态
// xai-chat-state/src/actor/mod.rs
pub struct ChatStateActor {
    state: ChatState, // conversation + UsageLedger + turn_capture
    rx: mpsc::Receiver<Command>,
}
// forkSubagent 时冻结 renderedSystemPrompt 保证 cache 命中
impl ChatStateActor {
    pub fn fork_subagent_state(&self) -> ChatStateSnapshot {
        self.state.capture_from(self.state.turn_start_offset) // 批量投影，避免逐条克隆
    }
}
```

**精读点**：

- **`SubagentEntry{source}` 的可扩展性**：与 Claude 的 60+ 硬编码类型不同，Grok 的 `SubagentEntry` 支持 `Builtin/Plugin/Remote` 三来源，`list_skills_with_plugins` 动态发现，与 DeepSeek 的 `preset.yml` 同策不同实现。
- **`xai-fast-worktree` 的工程价值**：`btrfs snapshot` 在 <50ms 内完成 COW 分支，比 `git worktree` 快 5–10×，是云端高频派发 subagent 的关键。`overlayfs` 作为回退，保证非 btrfs 文件系统仍可用。
- **`SchedulerHandle` 树 = Agent 树**：`parent_scheduler_handle` 形成调度器树，与 DeepSeek 的 `Cordis Scope` 树同构，但 Grok 的树还承载 `UsageLedger` 的用量归因（每个 subagent 的 token 用量可独立追踪）。
- **Actor 的 cache 优化**：`forkSubagent` 时冻结 `renderedSystemPrompt`，保证子 Agent 与主 Agent 的 prompt 前缀一致，命中 server cache。这是 Grok 在 200K 上下文下保持性能的关键（与 Claude 的 `cache-identical 前缀` 同策）。

#### DeepSeek — `dsh-subagent` + `Cordis Scope` + `Goal/Plan/Workflow` 四级规划

```ts
// 骨架（TS 伪代码，对应 dsh-subagent + dsh-tool-subagent + Cordis Scope + 四级规划）
// 1. 四级规划栈（DeepSeek 最细）
// Goal（目标） → Plan（计划） → Todo（清单） → Workflow（工作流） → Jobs（后台任务）
// dsh-goal/goal-round-driver, dsh-plan-mode, dsh-todo, dsh-workflow/worker-thread, dsh-jobs-local

type Goal = { id: string; description: string; status: 'active' | 'achieved' | 'abandoned' };
type Plan = { goalId: string; steps: PlanStep[]; artifact: string }; // artifact = .md 文件
type Todo = { planStepId: string; items: TodoItem[] }; // TodoWrite 的对等
type Workflow = { todos: Todo[]; jobs: Job[] }; // Workflow 是 Todo 的执行图

// 2. 子 Agent 隔离：Cordis Scope
import { Scope } from 'cordis';

class SubagentControl {
  constructor(private parentScope: Scope) {}

  spawn(task: string, preset: string) {
    // preset.yml 决定子 agent 组合（类似 Grok SubagentEntry）
    const preset_config = loadPreset(preset); // code/standard/minimal/cordis
    const subScope = this.parentScope.createScope({ task, preset: preset_config }, this);
    // 子 Scope 内注册工具，生命周期随 Scope 退出收回
    for (const tool of preset_config.tools) {
      subScope.plugin(tool);
    }
    // Inbox 通信：子 Agent 结果通过 Inbox.splice(next-step) 回主 Agent
    const subAgent = new ReactLoopAgent(subScope);
    subAgent.onDone((result) => {
      this.parentScope.inbox.splice('next-step', result);
    });
    return subAgent;
  }
}

// 3. 通信：Inbox 的精确语义（见 9.2.3，已详述）
// 4. 钩子：Cordis waterfall（见 9.2.4，已详述）
// waterfall('agent/pre-step') → 权限决策
// waterfall('agent/request') → LLM 调用改写
// waterfall('agent/turn-stopping') → Inbox.nextStep 判空 → break
// 5. turnEnds 的黏性：completed 不覆盖 max-tokens，保证用量归因正确
```

**精读点**：

- **四级规划栈是"最细的规划分解"**：`Goal → Plan → Todo → Workflow → Jobs` 每级均有独立 package，可独立测试与复用。`Goal` 是用户意图，`Plan` 是可 review 的 artifact，`Todo` 是执行清单，`Workflow` 是带依赖的执行图，`Jobs` 是后台任务。七家中仅 DeepSeek 做到此粒度。
- **`Cordis Scope` 的 RAII 语义**：`Scope.createScope(loopCtx, this)` 的第二个参数 `this` 是"所有者"，Scope 随所有者退出自动 dispose，无泄漏。这是 DeepSeek 60+ 插件能安全高频派发 subagent 的基础。
- **`preset.yml` 的组合机制**：`preset.yml` 决定子 agent 的工具组合（`code/standard/minimal/cordis` 四档），与 Grok 的 `SubagentEntry{source}` 同策，但 DeepSeek 更声明式。
- **`Inbox.nextStep` 判空 → break**：`waterfall('agent/turn-stopping')` 中 `Inbox.nextStep` 为空即结束 turn，`turnEnds=max-tokens` 的黏性保证用量归因不被 `completed` 覆盖（见 Ch2 的适配器剥除）。

#### OpenCode — `packages/opencode/src/agent/agent.ts:35 Info{mode}` + `tool/task.ts` + `Session.fork()`

```ts
// 骨架（TS 伪代码，对应 agent.ts:90 + tool/task.ts + subagent-permissions.ts）
// 1. Agent 可见性分级
// packages/opencode/src/agent/agent.ts:35
type AgentInfo = {
  name: string;
  mode: 'subagent' | 'primary' | 'all'; // 可见性：仅子 Agent / 仅主 Agent / 全部
  native?: boolean;                       // native:true = 隐藏 agent（如 compaction）
  permission: PermissionV1.Ruleset;
  model?: string;                         // 子 Agent 可用不同模型（如 Haiku 做 explore）
};

// 内置 6 类 agent
const builtInAgents: AgentInfo[] = [
  { name: 'build', mode: 'primary', permission: allowAll },
  { name: 'plan', mode: 'primary', permission: denyEdit }, // plan 模式禁止 edit
  { name: 'explore', mode: 'subagent', permission: readOnly }, // 只读 explore
  { name: 'compaction', mode: 'all', native: true, permission: denyAll }, // 隐藏
];

// 2. 任务规划：tool/task.ts + task.txt
// packages/opencode/src/tool/task.ts
export const taskTool = buildTool({
  name: 'task',
  description: 'Create a sub-task for parallel execution',
  parameters: z.object({
    task: z.string(),
    agent: z.string().optional(), // 指定子 Agent 类型
  }),
  execute: async ({ task, agent }, ctx) => {
    // Session.fork() 创建子会话，血缘可追溯
    const subSessionId = await Session.fork(ctx.sessionId);
    // subagent-permissions.ts 权限继承与覆盖
    const subPermission = inheritPermission(ctx.permission, agent);
    // 派发子 Agent，通过 EventV2Bridge 通信
    const subAgent = spawnAgent(agent ?? 'explore', task, subSessionId, subPermission);
    return subAgent.result; // 通过 EventV2Bridge 回填
  },
});

// task.txt 是任务清单的落盘文件（类似 TodoWrite 的文件形态）
// .opencode/plans/*.md 是 plan artifact（类似 Claude .agent/plans/）

// 3. 隔离：Session.fork() + subagent-permissions.ts
// Session.fork() 复制当前 Session 的 parts 到新 Session，新 Session 独立追加
// subagent-permissions.ts 保证子 Agent 权限不高于主 Agent（权限继承的单调性）

// 4. 通信：EventV2Bridge 事件总线
// 子 Agent 完成 → EventV2Bridge 广播 → 主 Agent 订阅 → 拼到 tool_results
```

**精读点**：

- **`Info{mode:subagent|primary|all}` 的可见性分级**：与 Codex 的 `ToolExposure` 同策不同层——Codex 分级的是"工具"，OpenCode 分级的是"Agent"。`explore` 仅 `subagent` 可见，主 Agent 不直接暴露，避免主 Agent 误调只读工具做写操作。
- **`Session.fork()` 的血缘保证**：`fork()` 时 `structuredClone` 保证子 Session 的初始状态与主 Session 一致，且血缘可追溯（类似 Grok 的 `turn_start_offset` 批量投影）。但无 worktree 隔离，文件级仍共享。
- **`task.txt` + `.opencode/plans/*.md` 双文件**：`task.txt` 是执行清单（TodoWrite 对等），`.opencode/plans/*.md` 是 plan artifact（Plan 对等），与 Claude 的 `TodoWrite + .agent/plans/` 同策。
- **`subagent-permissions.ts` 的单调性**：子 Agent 权限 ≤ 主 Agent 权限，不可提权。这是所有多 Agent 系统的共同不变量，Claude 的 `workerPermissionContext=acceptEdits` 与 DeepSeek 的 `Scope` 覆盖亦保证此点。

#### Pi — `docs/book/23-subagents.md` 同进程协程（教学形态）

```ts
// 骨架（TS 伪代码，对应 docs/book/23-subagents.md + packages/agent/src/types.ts）
// Pi 的子 Agent 是"最简可运行"的教学实现，无隔离、无 worktree、无 Scope

type SubagentConfig = {
  subagent_type: 'explore' | 'coding-agent';
  prompt: string;
};

// AgentTool 触发子 agentLoop()
export const agentTool = buildTool({
  name: 'agent',
  description: 'Spawn a sub-agent',
  parameters: z.object({
    subagent_type: z.string(),
    prompt: z.string(),
  }),
  execute: async ({ subagent_type, prompt }, ctx) => {
    // 同进程协程：直接调 agentLoop()，共享同一 AgentContext
    const subContext: AgentContext = {
      ...ctx,
      messages: [...ctx.messages], // 浅拷贝消息，但文件系统仍共享
      systemPrompt: subagent_type === 'explore' ? explorePrompt : ctx.systemPrompt,
    };
    // 子 Agent 的工具集由 subagent_type 决定（explore 仅 read/grep/glob）
    const subTools = subagent_type === 'explore' ? readOnlyTools : allTools;
    const result = await agentLoop(subContext, subTools, ctx.signal);
    return result;
  },
});

// 主 Agent：coding-agent（全权限）
// 子 Agent：explore（只读），通过 hooks-and-events + resources 通信
// resources 是 Pi 的"资源"抽象，类似 DeepSeek 的 Scope 但更简
```

**精读点**：

- **教学价值**：Pi 的同进程协程是"200 行可运行的多 Agent 实验室"——无 worktree、无 Actor、无 Scope，所有隔离靠"工具白名单"保证。读者可在 50 行内改出"worktree 隔离"版本以体会差异。
- **局限**：无文件隔离，并行 `write_file` 必冲突；无 `Inbox` 精确语义，通信靠 `hooks-and-events` 回调；无 plan artifact，规划隐式在消息中。这正是 Pi 作为教学实现的刻意简化——**先让多 Agent 跑起来，再逐步加隔离**。
- **迁移路径**：Pi → OpenCode（加 `Session.fork()`）→ DeepSeek（加 `Scope`）→ Claude/Grok（加 `worktree`），是"隔离强度"的渐进路径。

#### Claw — 占位（规划中）

| 维度 | 现状 | 计划 |
|------|------|------|
| 子 Agent | 占位，无 `AgentTool` | 规划对标 Claude `AgentTool`，Rust 实现 |
| 隔离 | 无 | 规划 `worktree` 隔离（参考 Grok `xai-fast-worktree`） |
| 规划 | `compact_after_turns=12` 固定轮数 | 规划 `TodoWrite` 对等 |
| 价值 | 作为"TS→Rust 移植"的桥梁案例，见 `src/tools.py:96 load_tool_snapshot()` | 观察其如何把 Claude 的 TS 思想翻译为 Rust |

> **Claw 的反例价值**：`compact_after_turns=12` 的固定轮数触发 vs Claude `effectiveWindow-13K` / Grok `85%` 的 token 预算驱动，是"原型 vs 生产"的典型差距——固定轮数在长工具结果场景 12 轮前已 PTL，在短轮场景又过早压缩。

### 9.3.3 七家对证小结：一张"隔离与规划"的有无表

| 能力 | Claude | Codex | Pi | DeepSeek | Grok | OpenCode | Claw |
|------|--------|-------|----|----------|------|----------|------|
| **子 Agent 载体** | ✅ 60+ 类型 | ✅ registry | ✅ 协程 | ✅ Cordis | ✅ discovery | ✅ task.ts | ❌ 占位 |
| **worktree 隔离** | ✅ worktree/remote | ❌ 模板隔离 | ❌ | ❌ Scope | ✅ btrfs/overlay | ❌ fork | ❌ |
| **权限隔离** | ✅ workerPermission | ✅ role 模板 | △ 白名单 | ✅ Scope 覆盖 | ✅ PromptContext | ✅ subagent-permissions | ❌ |
| **禁止嵌套** | ✅ isTeammate | △ 模板级 | ❌ | ✅ Scope 树 | ✅ Scheduler 树 | ✅ Info.mode | — |
| **显式规划容器** | ✅ TodoWrite+Plan | △ plugins | ❌ | ✅ 四级 | ✅ Workflow | ✅ task.txt | ❌ |
| **plan 落盘文件** | ✅ .agent/plans/ | ❌ | ❌ | ✅ dsh-plan | ✅ xai-workflow | ✅ .opencode/plans/ | ❌ |
| **精确通信** | ✅ InterAgent | ✅ InputQueue | △ 回调 | ✅ Inbox | ✅ contributors | △ EventV2 | ❌ |
| **钩子** | ✅ Pre/PostCompact | ✅ ExtensionData | △ before/after | ✅ waterfall | ✅ ReminderPolicy | △ Event | ❌ |

> 结论：七家差异不在"有无多 Agent"，而在"隔离强度 × 规划显式度 × 通信精度"。Pi 只有"有"，Claude/Grok/DeepSeek 有"强"。

---

## 9.4 结论权衡：何时单 Agent vs Orchestrator-Worker vs Swarm

### 9.4.1 决策树：四选一

```
任务步数 ≤ 10 且单文件？
├─ 是 → 单 Agent（无多 Agent 开销，见 9.4.2 量化）
│        例：修一个函数的 bug、写一个 React 组件
│
└─ 否 → 需并行搜集/探索？
        ├─ 是 → 需多角色协作（reviewer/tester/implementer）？
        │        ├─ 是 → Swarm（spawnTeammate 去中心化）
        │        │        例：并行 review + test + implement 同一 PR
        │        │
        │        └─ 否 → Orchestrator-Worker（主从，最常用）
        │                 例：主 Agent 派 3 个 explore 子 Agent 并行搜集 5 个模块，主 Agent 汇总
        │                 代表：Claude AgentTool(explore) + TodoWrite
        │
        └─ 否 → 需严格 SOP / 树状分解？
                 ├─ 是 → Hierarchical（1 层，禁止嵌套）
                 │        例：DeepSeek Workflow → Jobs，企业级 SOP 流程
                 │
                 └─ 否 → 单 Agent + Plan 文件（大任务但可串行）
                          例：单 Agent 按 .agent/plans/*.md 逐步执行，用 TodoWrite 跟踪
```

### 9.4.2 量化权衡表

| 维度 | 单 Agent | Orchestrator-Worker | Swarm | Hierarchical (1 层) |
|------|----------|---------------------|-------|---------------------|
| **适用步数** | ≤10 步 | 10–50 步，需并行搜集 | 20+ 步，多角色 | 30+ 步，需 SOP |
| **并行度** | 无（串行） | 高（Worker 并行，见 9.4.3 时序） | 最高（去中心化并行） | 中（树状串行派发） |
| **一致性** | 强（单上下文） | 强（主 Agent 汇总） | 弱（需额外协议） | 强（SOP 约束） |
| **开销** | 最低（无 fork/worktree） | 中（worktree 50-100ms × N） | 高（多 Agent 上下文 × N） | 中（Scope 1ms × N） |
| **隔离需求** | 无 | **需 worktree**（并行写时） | **需 worktree** | Scope 即可 |
| **plan 必要性** | 可选（小任务无需） | **必须**（TodoWrite 跟踪 Worker 进度） | 必须（任务分配清单） | **必须**（Workflow 文件） |
| **代表** | Pi 默认 / Claude 单 turn | Claude explore + TodoWrite | Claude swarm + spawnTeammate | DeepSeek Workflow |

**实证归纳**（依据 9.1.2 的三份工作，非单一基准）：Anthropic 生产实测并行搜集类研究任务 Orchestrator-Worker 较单 Agent 提升约 90%，但 token 成本高约一个数量级（15× vs 普通聊天）；Cognition 论证强耦合编辑任务多 Agent 反而引入冲突；More Agents 证明无通信的采样投票才有单调扩展律。**结论：多 Agent 不是"越多人越好"，而是"并行搜集、子任务弱耦合时才值得"**。

### 9.4.3 编排时序图：Orchestrator-Worker（最常用）

```
时间 ─────────────────────────────────────────────────────────────►

主 Agent                 Worker-A (explore)      Worker-B (explore)      Worker-C (explore)
   │                           │                       │                       │
   │ TodoWrite(plan)           │                       │                       │
   │  "探索 auth/payment/db"   │                       │                       │
   │  pending × 3              │                       │                       │
   │                           │                       │                       │
   │ spawn AgentTool × 3 (并行) │                       │                       │
   │──────────────────────────►│                       │                       │
   │───────────────────────────┼──────────────────────►│                       │
   │───────────────────────────┼───────────────────────┼──────────────────────►│
   │                           │                       │                       │
   │ TodoWrite(in_progress ×3) │ read/grep/glob        │ read/grep/glob        │ read/grep/glob
   │                           │ (只读，无 worktree)    │                       │
   │                           │                       │                       │
   │                           │◄──────────────────────│                       │
   │                           │ 完成：auth 模块分析    │                       │
   │  Inbox.drain(next-step)   │                       │ 完成：payment 分析     │
   │◄──────────────────────────│                       │◄──────────────────────│
   │ TodoWrite(completed:auth) │                       │                       │ 完成：db 分析
   │                           │                       │                       │◄──────────────│
   │  Inbox.drain(next-step)   │                       │                       │
   │◄───────────────────────────────────────────────────│                       │
   │ TodoWrite(completed:pay)  │                       │                       │
   │                           │                       │                       │
   │  Inbox.drain(next-step)   │                       │                       │
   │◄───────────────────────────────────────────────────────────────────────────│
   │ TodoWrite(completed:db)   │                       │                       │
   │                           │                       │                       │
   │ 汇总：基于 3 个 Worker 的产出，生成最终方案                                │
   │  若需写文件 → 主 Agent 串行 write（避免并行写冲突）                        │
   │  若探索结果需写 → 需 worktree 隔离（见 9.4.4）                             │
```

> **关键**：explore Worker 是**只读**的，无需 worktree；若 Worker 需 `write_file`，则必须 worktree 隔离，否则并行写同一文件必冲突（见 9.4.4）。

### 9.4.4 隔离对比：何时必须 worktree

| 场景 | 是否需 worktree | 原因 | 代表 |
|------|----------------|------|------|
| Worker 只读探索（read/grep/glob） | ❌ 无需 | 无副作用，并行安全 | Claude explore, Pi explore |
| Worker 并行写不同文件 | ⚠️ 建议 | 虽不同文件但共享 worktree 时仍有 git 状态竞争 | Grok btrfs |
| Worker 并行写同一文件 | ✅ **必须** | 后写者覆盖前写者，丢失更新（见 Ch4.4.4 失败案例） | Claude worktree, Grok fast-worktree |
| 单 Agent 串行写 | ❌ 无需 | 串行无竞争 | 全部 |
| Hierarchical 多级写 | ✅ **必须** | 每级写操作需隔离，完成后 merge | DeepSeek Scope + worktree 双层 |

**失败案例 — 无 worktree 的并行写冲突**：

```
主 Agent 与两个 subagent 并行（无 worktree）：
  subagent-A: write_file("src/a.ts", "feature A")
  subagent-B: write_file("src/a.ts", "feature B")
  → bwrap 隔离了单次执行的文件可见性，但三个 agent 共享同一 worktree 的 src/a.ts
  → 后写者覆盖前写者，丢失更新

Grok/Claude 解法：每个 subagent 分配独立 worktree (btrfs snapshot)，
           完成后通过 merge/conflict 检测合并，而非直接写同一 inode。
```

### 9.4.5 三条铁律

#### 铁律 1：禁止嵌套 teammate（防递归风暴）

```ts
// Claude: src/tools/AgentTool/LocalAgentTask.ts
if (this.isTeammate() && this.parent?.isTeammate()) throw new Error('Nested teammate forbidden');
// DeepSeek: Cordis Scope 树亦禁止超过 1 层嵌套
// Grok: SchedulerHandle 树限制深度 1

// 原因：teammate → teammate → teammate 的递归派生会导致上下文指数爆炸
// 每层嵌套 token 成本 × N，3 层嵌套即 10× 成本，且权限继承链难以审计
// 例外：Orchestrator-Worker 的 Worker 不算 teammate，可 1 层 Hierarchical
```

#### 铁律 2：plan 必须落盘为文件（可审计性）

```
原则：plan 是 artifact（文件），不是 message
├── 审计：人类可 pre-review plan 文件，再决定是否执行（plan 模式的价值）
├── 持久：Session 恢复时 plan 文件仍在，message 可能被压缩丢失
├── 并发：多 Agent 可同时读 plan 文件，message 需通过 Inbox 转发
└── 回滚：plan 文件可 git diff / git revert，message 不可

Claude: .agent/plans/*.md + Plan(isInPlanMode())
OpenCode: .opencode/plans/*.md + plan_enter/plan_exit
DeepSeek: dsh-plan-mode 产出的 plan artifact
反例：Pi 无 plan 文件，规划隐式在消息中，无法被人类 pre-review
```

#### 铁律 3：子 Agent 权限单调性（不可提权）

```
子 Agent 权限 ≤ 主 Agent 权限（单调不增）
├── Claude: workerPermissionContext = acceptEdits（独立但不高于主）
├── DeepSeek: Scope 覆盖的 PermissionContext 不可提权
├── OpenCode: subagent-permissions.ts 继承 + 收紧
├── Grok: PromptContext{audience:Subagent} 的工具白名单 ≤ Primary
└── 原因：若子 Agent 可提权，恶意 prompt 可通过派生 subagent 绕过主 Agent 的 deny 规则
```

### 9.4.6 规划状态机 vs 工具编排的正交性

```
规划状态机（本章 9.2.1）          工具编排（Ch4.2.5）
     │                                │
     ├─ 决定"做什么"（任务分解）        ├─ 决定"怎么做"（工具调用顺序）
     ├─ 容器：TodoWrite/task/plan 文件 ├─ 容器：ToolOrchestrator + ToolRouter
     ├─ 粒度：任务级（高/中/低）        ├─ 粒度：工具调用级（read/write/bash）
     └─ 时序：plan → execute → review  └─ 时序：approval → sandbox → execute → hook
     │                                │
     └────────── 两者正交 ──────────────┘
               主 Agent 用规划状态机跟踪"任务进度"
               每个任务内的工具调用用 ToolOrchestrator 编排
               子 Agent 继承主 Agent 的规划上下文，但工具编排独立
```

---

## 9.5 未来：Agent OS、Skill 市场、Workflow DSL、跨 Agent Memory 与信用分配

> 本节对应要求的五个未来方向：Agent OS 调度器、Skill 市场、Workflow DSL、跨 Agent Memory 共享、评估与信用分配。

### 9.5.1 Agent OS 调度器：从 Loop 到 OS

今日的 Agent Loop 是"单进程单任务"，未来的 Agent OS 是"多进程多任务调度器"：

```
今日（Loop）：                          未来（Agent OS）：
┌─────────────────┐                    ┌──────────────────────────────────┐
│  Loop            │                    │  Agent OS Scheduler              │
│  while(hop<25)  │                    │  ┌──────────┐ ┌──────────┐      │
│   sample→tools  │                    │  │ Agent-A  │ │ Agent-B  │ ...  │
│   单任务串行     │                    │  │ (high)   │ │ (low)    │      │
│                  │                    │  └────┬─────┘ └────┬─────┘      │
└─────────────────┘                    │       │  调度  │               │
                                       │  ┌────▼────────▼────┐           │
                                       │  │ Priority Queue   │           │
                                       │  │ + Resource Quota │           │
                                       │  │ + Preemption     │           │
                                       │  └──────────────────┘           │
                                       │  ┌──────────────────┐           │
                                       │  │ Worktree Pool    │           │
                                       │  │ (btrfs 快照池)   │           │
                                       │  └──────────────────┘           │
                                       └──────────────────────────────────┘

关键能力：
1. 优先级调度：高优任务抢占低优任务的 worktree 与 token 预算
2. 资源配额：每 Agent 的 token/wall-time/worktree 数量上限
3. 抢占与恢复：被抢占的 Agent 状态 checkpoint 到 Session，恢复时重放
4. worktree 池化：预创建 btrfs 快照池，派发时 <10ms（vs 现场创建 50-100ms）
```

**七家现状与差距**：

| 家 | 调度能力 | 差距 |
|----|----------|------|
| Claude | `LocalAgentTask` 的 `autoBackground(120s)` 是雏形 | 无优先级、无配额、无 worktree 池 |
| DeepSeek | `Cordis Scope` 树 + `dsh-jobs-local` 后台任务 | 最接近 OS，但无抢占 |
| Grok | `SchedulerHandle` 树 + `xai-fast-worktree` | 有 worktree 但无统一调度器 |
| Codex | `collaboration-mode-templates` 静态模板 | 无动态调度 |

> **可验证假设**：Agent OS 调度器的首个可观测指标是"worktree 池命中率"——池化后 subagent 启动延迟应从 50-100ms 降至 <10ms，且 P99 稳定。

### 9.5.2 Skill 市场：从硬编码到可交易能力

```
今日（硬编码）：                        未来（Skill 市场）：
builtInAgents.ts 60+ 类型              ┌──────────────────────────────────┐
硬编码在源码中                          │  Skill Registry (市场)           │
更新需发版                              │  ┌──────────┐ ┌──────────┐      │
                                       │  │ Skill-A  │ │ Skill-B  │ ...  │
                                       │  │ (review) │ │ (test)   │      │
                                       │  │ ★4.8     │ │ ★4.5     │      │
                                       │  │ $0.01/use│ │ free     │      │
                                       │  └────┬─────┘ └────┬─────┘      │
                                       │       │  发现  │               │
                                       │  ┌────▼────────▼────┐           │
                                       │  │ Semantic Search  │           │
                                       │  │ + Reputation     │           │
                                       │  │ + Billing        │           │
                                       │  └──────────────────┘           │
                                       └──────────────────────────────────┘

Grok 的 SkillInfo + DeepSeek 的 dsh-skill + OpenCode 的 skill/ 已迈出第一步
下一跳：计费、评分、版本管理、依赖解析（类似 npm/pypi）
```

**关键设计**：

- **发现**：`Grok discovery.rs SubagentEntry{source}` + `DeepSeek preset.yml` + `OpenCode skill/` 三者的泛化——统一为 `Skill Registry` 的语义检索（Gorilla 思想的延续，见 Ch4.1.1）
- **计费**：按 `token 用量 × skill 复杂度` 计费，`UsageLedger`（Grok）已具备用量归因基础
- **信任**：`skill` 的 `prompt_template` 需沙箱审计，防止 prompt 注入提权（见 Ch11 安全）

### 9.5.3 Workflow DSL：从 TodoWrite 到可编排图

```
今日（TodoWrite 线性清单）：            未来（Workflow DSL 有向图）：
TodoWrite([                             Workflow DAG {
  {content:"任务A", status:"pending"},    nodes: [
  {content:"任务B", status:"pending"},      {id:"A", tool:"read_file", deps:[]},
])  线性，无依赖                          {id:"B", tool:"grep", deps:["A"]},
                                        {id:"C", tool:"write_file", deps:["A","B"]},
                                        {id:"D", tool:"bash", deps:["C"]},
                                       ],
                                       edges: ["A→B", "A→C", "B→C", "C→D"],
                                       parallelism: { "A,B": "parallel", "C,D": "sequential" }
                                       }

LangGraph 的 StateGraph 是雏形，DeepSeek 的 dsh-workflow/worker-thread 是另一雏形
下一跳：Workflow DSL 的类型化 + 静态检查（类似 GitHub Actions 的 workflow.yml）
```

**七家现状**：

| 家 | Workflow 能力 | DSL 形态 |
|----|--------------|----------|
| DeepSeek | `dsh-workflow/worker-thread` + `dsh-jobs-local` 最完整 | Cordis 插件组合，无显式 DSL |
| Grok | `xai-workflow` + `TemplateRenderer` | `${{ tools.by_kind.* }}` 模板 |
| LangGraph | `StateGraph{ nodes, edges, checkpoint }` | TS/Python 代码即 DSL |
| Claude | `TodoWrite` 线性，无 DAG | 无 |
| 未来 | Workflow DSL 文件（`.agent/workflows/*.yaml`） | 声明式，支持 `parallel/sequential/conditional` |

> **可验证假设**：Workflow DSL 的首个可观测收益是"并行度提升"——DAG 中无依赖的节点可并行执行，相比 TodoWrite 的串行，端到端延迟降低与 DAG 宽度成正比。

### 9.5.4 跨 Agent Memory 共享：从隔离到受控共享

```
今日（强隔离）：                        未来（受控共享）：
Agent-A worktree-A  ─┐                  ┌──────────────────────────────────┐
Agent-B worktree-B  ─┤ 完全隔离          │  Shared Memory Layer             │
Agent-C worktree-C  ─┘ 无共享            │  ┌──────────┐ ┌──────────┐      │
                                       │  │ Episodic │ │ Semantic │      │
                                       │  │ (共享)   │ │ (共享)   │      │
                                       │  └────┬─────┘ └────┬─────┘      │
                                       │       │  受控  │               │
                                       │  ┌────▼────────▼────┐           │
                                       │  │ Access Control   │           │
                                       │  │ + Conflict Merge │           │
                                       │  │ + Version Vector │           │
                                       │  └──────────────────┘           │
                                       │  ┌──────────────────┐           │
                                       │  │ Private Memory   │           │
                                       │  │ (每 Agent 独立)  │           │
                                       │  └──────────────────┘           │
                                       └──────────────────────────────────┘

今日七家均为"强隔离"，跨 Agent 共享靠"主 Agent 汇总"间接实现
未来：受控的共享 Memory 层，类似多进程的共享内存 + 信号量
```

**关键挑战**：

1. **一致性**：多 Agent 并发写共享 Memory 时的冲突合并（类似 CRDT 或 git merge）
2. **隐私**：哪些 Memory 可共享、哪些私有（`Private vs Shared` 分层）
3. **遗忘**：共享 Memory 的压缩与遗忘策略（FadeMem 的遗忘机制需扩展到多 Agent）

**与本书其他章的衔接**：

- Ch6 Memory 的 `MemGPT / A-MEM / FadeMem` 均假设单 Agent，跨 Agent 共享需新增"多租户 Memory"抽象
- Grok 的 `ChatStateActor` 单 task 拥有状态是"强隔离"的极致，未来需在 Actor 间加"受控共享"通道

### 9.5.5 评估与信用分配：谁的功劳

```
问题：多 Agent 协作完成后，如何评估每个 Agent 的贡献（信用分配）？

今日（无评估）：                        未来（信用分配）：
多 Agent 协作 → 主 Agent 汇总           多 Agent 协作 → 评估 → 信用分配
无法归因                               ┌──────────────────────────────────┐
                                       │  Evaluation                      │
                                       │  ┌──────────┐ ┌──────────┐      │
                                       │  │ Outcome  │ │ Process  │      │
                                       │  │ (结果)   │ │ (过程)   │      │
                                       │  │ pass/fail│ │ 轨迹质量 │      │
                                       │  └────┬─────┘ └────┬─────┘      │
                                       │       │         │               │
                                       │  ┌────▼─────────▼────┐           │
                                       │  │ Credit Assignment │           │
                                       │  │ Shapley Value     │           │
                                       │  │ / Attention-based │           │
                                       │  └────────┬──────────┘           │
                                       │            │                      │
                                       │  ┌─────────▼──────────┐           │
                                       │  │ Skill Rating Update│           │
                                       │  │ (市场评分联动)     │           │
                                       │  └──────────────────┘           │
                                       └──────────────────────────────────┘
```

**SWE-bench 的启示**：当前 SWE-bench 仅评估最终 `Outcome`（补丁是否通过测试），不评估 `Process`（每个 Agent 的轨迹质量）。未来需：

- **Outcome 评估**：`SWE-bench` 的 `pass/fail` 是基础，但需细化到"每个子任务的 pass/fail"（如 `auth 模块探索` 是否完整）
- **Process 评估**：`BFCL` 的 AST/可执行双轨评测可扩展到"多 Agent 协作轨迹"的评估
- **信用分配**：`Shapley Value`（博弈论）或 `Attention-based`（模型内归因）决定每个 Agent 对最终结果的贡献度，联动 Skill 市场的评分更新

> **可验证假设**：信用分配的首个可观测指标是"Skill 评分与实际贡献的相关系数"——高评分 Skill 的 Agent 在协作任务中的 Shapley Value 应显著高于低评分者，否则市场机制失效。

---

## 9.6 Lab：从单 Agent 到 Orchestrator-Worker 的渐进实现

> 本 Lab 在 `my-agent`（`src/loop.ts/context.ts/tools.ts`）基线上增量实现多 Agent 与规划能力，共 4 阶段，每阶段可 `git diff` 验收。

### Lab 0 — 前置：基线确认

```bash
npm test          # 12 个 ContextManager 单元测试通过
npm run typecheck # 类型检查通过
npm run dev -- --print "hello" # 单 Agent 基线可运行
```

### Lab 1 — TodoWrite 显式规划容器（30 分钟）

**目标**：实现 `TodoWrite` 工具，plan 存于内存 + 可选落盘。

**步骤**：

1. 在 `src/tools.ts` 新增 `TodoWriteTool`（参考 `src/Tool.ts:362` 的 `buildTool()` 形态）：
   ```ts
   export const todoWriteTool = buildTool({
     name: 'todo_write',
     description: 'Update task plan: pending/in_progress/completed',
     parameters: z.object({
       todos: z.array(z.object({
         content: z.string(),
         status: z.enum(['pending','in_progress','completed','cancelled']),
         priority: z.enum(['high','medium','low']),
       })),
     }),
     isReadOnly: false,
     isConcurrencySafe: false, // 规划更新必须串行
     execute: async ({ todos }, ctx) => {
       // upsert 语义：按 content 合并，而非覆盖
       ctx.planState = mergeTodos(ctx.planState, todos);
       // 可选：落盘 .agent/plans/<id>.md
       if (ctx.planFile) await writeFile(ctx.planFile, formatPlan(ctx.planState));
       return { todos: ctx.planState };
     },
   });
   ```
2. 在 `src/context.ts` 的 `ContextManager` 中新增 `planState: PlanItem[]` 字段，`push()` 时若检测到 `todo_write` 调用则更新 `planState`。
3. 在 `src/loop.ts` 的 `getMessagesForModel()` 中将 `planState` 注入 system prompt（类似 Claude 的 `TodoWrite` 状态容器）。

**验收**：

```bash
# 模型应能调用 todo_write，且后续 hop 的 system prompt 含最新 plan
npm run dev -- --print "用 TodoWrite 规划并执行：创建 a.ts 和 b.ts"
# 检查：trace 中应有 todo_write 调用，且 plan 状态正确流转
```

**常见坑**：TodoWrite 覆盖式而非合并式 → 并发更新丢状态；plan 未注入 system prompt → 模型看不到最新规划。

### Lab 2 — Plan Artifact 文件 + plan 模式权限隔离（45 分钟）

**目标**：plan 落盘为 `.agent/plans/*.md`，plan 模式下禁止 edit。

**步骤**：

1. 新增 `plan_enter` / `plan_exit` 工具（参考 OpenCode `plan_enter/plan_exit` 受限工具）：
   ```ts
   export const planEnterTool = buildTool({
     name: 'plan_enter',
     description: 'Enter plan mode: read-only exploration, produce plan file',
     parameters: z.object({ task: z.string() }),
     execute: async ({ task }, ctx) => {
       ctx.mode = 'plan';
       ctx.planFile = `.agent/plans/${Date.now()}.md`;
       // 切换权限：plan 模式下所有 write/edit/bash 被 deny
       ctx.permission = { ...ctx.permission, 'write': 'deny', 'bash(*)': 'deny' };
       return { mode: 'plan', planFile: ctx.planFile };
     },
   });
   ```
2. 在 `src/tools.ts` 的 `decidePermission()` 中检查 `ctx.mode === 'plan'` 时拒绝 `write_file/edit_file/bash`。
3. plan 文件产出后调 `ask_user_question`（或 `read_file` 供人类 review），确认后 `plan_exit` 切回 `build` 模式。

**验收**：

```bash
npm run dev -- --print "/plan 创建一个用户认证模块"
# 预期：模型进入 plan 模式，仅调 read/grep/glob + explore subagent，产出 .agent/plans/*.md
# 检查：plan 模式下尝试 write_file 应被 deny
```

### Lab 3 — Orchestrator-Worker 子 Agent（60 分钟）

**目标**：实现 `AgentTool` 的最小可用版本（同进程协程，无 worktree）。

**步骤**：

1. 新增 `AgentTool`（参考 Pi `docs/book/23-subagents.md` 的同进程形态）：
   ```ts
   export const agentTool = buildTool({
     name: 'agent',
     description: 'Spawn a sub-agent for exploration',
     parameters: z.object({
       subagent_type: z.enum(['explore']),
       prompt: z.string(),
     }),
     isConcurrencySafe: false,
     execute: async ({ subagent_type, prompt }, ctx) => {
       // 同进程协程：复用 ContextManager 但独立 hop 计数
       const subContext = ctx.fork({ maxHops: 10, tools: exploreTools });
       const result = await runLoop(subContext, prompt); // 子循环
       return { result, subagent_type };
     },
   });
   ```
2. `explore` 子 Agent 工具白名单：仅 `read_file/grep/glob/list_dir`（只读）。
3. 主 Agent 的 `TodoWrite` 跟踪 Worker 进度，`Inbox` 语义用简化版 `pendingMessages[]` 实现。

**验收**：

```bash
npm run dev -- --print "并行探索 src/ 下的 auth 和 payment 模块，然后汇总"
# 预期：主 Agent 派 2 个 explore 子 Agent 并行搜集，主 Agent 汇总
# 检查：trace 中应有 2 个 agent 调用，且子 Agent 仅调只读工具
```

**思考题**：若让 explore 子 Agent 并行 `write_file` 会怎样？（答：丢失更新，需 Lab 4 的 worktree 隔离）

### Lab 4 — worktree 隔离 + 禁止嵌套（60 分钟，可选进阶）

**目标**：为写操作的 subagent 添加 worktree 隔离，并禁止嵌套。

**步骤**：

1. 实现 `createAgentWorktree()`（简化版：`git worktree add /tmp/wt-<id>` 或 `cp -r`）：
   ```ts
   async function createAgentWorktree(sessionId: string): Promise<string> {
     const wt = `/tmp/wt-${sessionId}-${Date.now()}`;
     await bash(`git worktree add ${wt} HEAD`); // 或 cp -r
     return wt;
   }
   ```
2. `AgentTool` 的 `isolation` 参数：`explore` 用 `none`（只读无需），`coder` 用 `worktree`。
3. 禁止嵌套：`if (ctx.isSubagent && subagent_type === 'teammate') throw new Error('Nested teammate forbidden')`。
4. 完成后 `merge` 回主 worktree（`git diff` 检测冲突）。

**验收**：

```bash
npm run dev -- --print "并行让两个 subagent 分别写 src/a.ts 和 src/b.ts"
# 预期：两个 subagent 各在独立 worktree 中写，完成后 merge 无冲突
npm run dev -- --print "让 subagent 再派生 subagent"
# 预期：Nested teammate forbidden 错误
```

**完成标志**：`git diff` 显示 Lab 1–4 的增量即为"从单 Agent 到多 Agent"的完整实现路径，每阶段可独立回滚。

---

## 9.7 小结：何时用多 Agent（30 秒陈述）

> **单 Agent 足够**：≤10 步、单文件、单工具链（如修一个函数 bug），多 Agent 反而增加数倍 token 成本（Cognition 原则①）。
>
> **Orchestrator-Worker 必用**：需并行搜集（explore 只读子 Agent）或长任务不阻塞主循环（LocalAgentTask background），Anthropic 生产实测研究类任务提升约 90%（代价 token ~15×）。
>
> **Swarm 适用**：多角色协作（reviewer/tester/implementer），需 worktree 隔离，去中心化扩展性最好但一致性需额外协议。
>
> **三条铁律**：禁止嵌套 teammate（防递归风暴）、plan 必须落盘为文件（可审计）、子 Agent 权限单调不增（不可提权）。
>
> **一句话区分七家**：Claude 最全（60+ 类型 + worktree/remote）、Grok 最隔离（btrfs + Actor）、DeepSeek 最插件（Scope + 四级规划）、Codex 最系统（模板 + InputQueue）、OpenCode 最现代（Effect + task 文件）、Pi 最可读（同进程协程）、Claw 占位。

**下一章**：可观测性与评测（Ch10）——多 Agent 的轨迹如何被 Trace 记录、如何用 SWE-bench / BFCL 评估协作效果、以及 Agent OS 调度器的可观测指标。

---

> **源码锚点索引（本章）**
>
> | 家 | 锚点 | 说明 |
> |----|------|------|
> | Claude | `src/tools/AgentTool/` + `builtInAgents.ts` | 60+ 子 Agent 类型，cache-identical 前缀 |
> | Claude | `src/tools/AgentTool/LocalAgentTask` | `registerAsyncAgent/registerAgentForeground` + `BackgroundHint(2s)/autoBackground(120s)` |
> | Claude | `createAgentWorktree()/teleportToRemote()` | worktree/remote 双隔离 |
> | Claude | `src/utils/teammate.ts/swarm/` | `spawnTeammate(team_name+name)` 群协作 |
> | Claude | `agentToolUtils.finalizeAgentTool/classifyHandoffIfNeeded` | 子 Agent 结果收敛与 handoff 判定 |
> | Codex | `codex-rs/agent/registry.rs/status.rs/control.rs/role.rs` | Agent 注册与角色 |
> | Codex | `collaboration-mode-templates/` | 模板级隔离 |
> | Codex | `codex-rs/core/src/session/input_queue.rs:19` | `TurnInput{UserInput\|InterAgentCommunication}` |
> | Grok | `xai-grok-agent/discovery.rs SubagentEntry{source}` | 子 Agent 发现 |
> | Grok | `xai-fast-worktree btrfs/overlay` | COW 快速分支 |
> | Grok | `xai-grok-workspace SchedulerHandle` | `parent_scheduler_handle` 树 |
> | Grok | `xai-agent-lifecycle/local/{registry,contributors}` | 生命周期与贡献者 |
> | DeepSeek | `dsh-subagent` + `dsh-tool-subagent/subagent-control` | 子 Agent 载体 |
> | DeepSeek | `Cordis Scope.createScope(loopCtx, this)` | Scope 隔离 |
> | DeepSeek | `dsh-goal/goal-round-driver, dsh-plan-mode, dsh-workflow/worker-thread, dsh-todo, dsh-jobs-local` | 四级规划栈 |
> | DeepSeek | `packages/core/agent/src/inbox.ts Inbox` | `splice(next-turn/next-step)` 精确通信 |
> | OpenCode | `packages/opencode/src/agent/agent.ts:35 Info{mode}` | `mode:subagent\|primary\|all` 可见性 |
> | OpenCode | `packages/opencode/src/tool/task.ts` + `task.txt` | 任务规划与子 Agent 派生 |
> | OpenCode | `packages/opencode/src/session/session.ts:102 Session.fork()` | 会话血缘 |
> | OpenCode | `subagent-permissions.ts` + `EventV2Bridge` | 权限继承与事件通信 |
> | Pi | `docs/book/23-subagents.md AgentTool{subagent_type}` | 同进程协程子 Agent |
> | Pi | `packages/agent/src/types.ts AgentLoopConfig` | `beforeToolCall/afterToolCall` 钩子 |
> | Grok/DeepSeek | `waterfall('agent/turn-stopping')` + `Inbox.nextStep` 判空 | 协作回合结束判定 |
