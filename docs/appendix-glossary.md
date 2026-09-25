# 附录 A 术语表

按主题分组：总纲 / Loop / Context / Tools / Memory / Session / Model / 多 Agent / 可靠性 / 评估。"出处"列为该术语定义所在的章节文件。

## 总纲

| 术语 | 定义 | 出处 |
|------|------|------|
| **Agent = Model + Harness** | 全书统摄公式：模型之外让 Agent 可运行的全部工程外壳即 Harness | [Ch2](./ch02-common-model.md) |
| **Harness 六件套** | Harness 的内部结构：`Prompt + Loop + Tools + Context + Session + Model`，形式化为状态机 | [Ch2](./ch02-common-model.md) |
| **Agent Infra** | Agent 基础设施层：介于模型能力与终端应用之间的工程栈，本书九家的解剖对象 | [Ch1](./ch01-landscape.md) |
| **「只增不改」** | Session 的写纪律：append 为唯一写路径，全量事件永不覆盖（append-only） | [Ch1](./ch01-landscape.md) / [Ch7](./ch06-session.md) |
| **「投影而非改写」** | Session 保留全量，发给模型的上下文是投影函数产出的视图，如数据库 VIEW | [Ch1](./ch01-landscape.md) / [Ch5](./ch05-context.md) |
| **「边界集与保留集」** | 上下文预算必须拆出一块不可动用的"保留集"，在越界之前先触发压缩 | [Ch1 §1.5](./ch01-landscape.md#_1-5-五个贯穿全书的设计模式-词汇债券) / [Ch5](./ch05-context.md) |
| **「故障边界」** | 每层的失败必须在本层归一化，不让上层看到下层的原始异常形态 | [Ch1 §1.5](./ch01-landscape.md#_1-5-五个贯穿全书的设计模式-词汇债券) / [Ch11](./ch10-reliability.md) |
| **「最小 Harness 税」** | Harness 加收的开销（抽象层、钩子、观测）能省则省；判据是"删掉它最小闭环还能不能跑" | [Ch1 §1.5](./ch01-landscape.md#_1-5-五个贯穿全书的设计模式-词汇债券) / [Ch3](./ch03-loop.md) |

## Loop

| 术语 | 定义 | 出处 |
|------|------|------|
| **Agent Loop** | `采样→执行→回填`的闭合循环，九家均为三层嵌套（turn/retry/stream） | [Ch2](./ch02-common-model.md) / [Ch3](./ch03-loop.md) |
| **Turn / Step** | Turn=一次用户输入到 end_turn；Step=Turn 内的一次采样+执行（DeepSeek `turn→step`, Codex `TurnContext/StepContext`） | [Ch3](./ch03-loop.md) |
| **Hop** | Loop 的一轮采样+执行，Claude/Pi 上限 25 | [Ch3](./ch03-loop.md) |
| **ReAct** | `Thought → Action → Observation` 交织的纯 Prompt 循环（Yao et al. 2022），Loop 范式的"创世纪" | [Ch3](./ch03-loop.md) |
| **CodeAct** | 把动作空间统一为可执行 Python（`think → exec → observe`），工具调用从多 JSON schema 坍缩为单一 `exec` | [Ch3](./ch03-loop.md) |
| **EventStream（OpenHands）** | 把用户消息、工具结果、环境事件、委派统一抽象为带时间戳的 `Event` 流；Loop 是事件的消费者而非拥有者 | [Ch3](./ch03-loop.md) |
| **五道闸** | 生产 Loop 在闭合上加的五类闸：hop 熔断、预算闸、重试闸、装配闸、取消闸 | [Ch3](./ch03-loop.md) |
| **Inbox** | DeepSeek 的精确打断语义，`next-turn` vs `next-step` + `wakeRequested` 闩锁 | [Ch3](./ch03-loop.md) |
| **Steer** | 采样中打断：`Inbox.steer(msg)` 以 `next-step` 粒度把用户消息插入当前 step 末尾，无需等整轮结束 | [Ch3](./ch03-loop.md) |
| **withheld 扣留** | steer 到来时已完成的 tool_result 立即回填、未完成的扣留到下一 hop 与新消息合并，解决部分结果问题 | [Ch3](./ch03-loop.md) |
| **Phase 状态机** | DeepSeek 的 `idle / running / maintenance` 三态 FSM，本书最精确的中断语义；`wakingAfterAbort` 闩锁防重入 | [Ch3](./ch03-loop.md) |
| **Actor 模型** | Grok `ChatStateActor`：单 task 独占 `ChatState`，steer 直接 push 无需锁与 Inbox 队列 | [Ch3](./ch03-loop.md) |
| **followUp** | Pi 外层循环的追问机制：turn 结束后取 `getFollowUpMessages()` 决定是否再跑一轮 | [Ch2](./ch02-common-model.md) |
| **BlockAssembler** | 流式装配闸：把 SSE chunk 按 `id` 分桶累积为完整 Block（`in_flight`），支撑边收边执行 | [Ch3](./ch03-loop.md) / [Ch8](./ch07-model.md) |
| **ACI** | Agent-Computer Interface（SWE-agent 提出）：Agent 与执行环境的接口设计是独立变量，护栏内建在接口层 | [Ch3](./ch03-loop.md) |
| **Verbal RL** | Reflexion 的"语言强化学习"：用自然语言复盘替代梯度更新，失败经验存入记忆缓冲供重试使用 | [Ch3](./ch03-loop.md) |
| **Speculative Loop** | 推测执行：分支写 `speculative: true` 暂态事件，确认后 `commit` 或 `rollback`，依赖 `turn_start_offset` 对齐共享前缀 | [Ch3](./ch03-loop.md) |

## Context

| 术语 | 定义 | 出处 |
|------|------|------|
| **Context Engineering** | 2024–2025 从 Prompt Engineering 独立成科：对进入窗口的一切信息做估算、预算、压缩与摆位 | [Ch5](./ch05-context.md) |
| **Compaction** | 超预算时的压缩，含 snip/micro/collapse/摘要四层 | [Ch5](./ch05-context.md) |
| **四层压缩** | `snip`（turn 级粗删）→ `microcompact`（tool_result 级细删）→ `collapse`（按段折叠）→ 摘要（小模型重写），cheap 先行、失败回退 | [Ch5](./ch05-context.md) |
| **Projection** | Session 保留全量，Context 是投影（Pi 术语），`for_prompt() / transformContext` 产出 LLM 可见子集 | [Ch5](./ch05-context.md) |
| **chars/4 估算** | 用字符数÷4 估 token：英文/代码约 -10% 误差、中文约 -60%，需 buffer 对冲；`bytes/4` 更稳 | [Ch5](./ch05-context.md) |
| **预算三档水位** | `T = W − R − B`（绝对值）或 `T = W × p`（百分比，Grok 85%），混合策略 `min(W×85%, W−13K)` | [Ch5](./ch05-context.md) |
| **PTL** | `prompt_too_long`，触发 `reactiveCompact` | [Ch5](./ch05-context.md) |
| **autoCompact / reactiveCompact** | 主动压缩（达阈值线即压）与被动兜底（PTL 后才压，多一次重试与延迟） | [Ch5](./ch05-context.md) |
| **Prompt Caching** | `cache_control: ephemeral` 让前缀复用，断点需稳定（工具排序/prompt 冻结） | [Ch5](./ch05-context.md) |
| **cache break** | 前缀字节级不一致导致缓存全 miss（工具顺序抖动/随机 ID 均可触发），Claude 以 `tengu_prompt_cache_break` 事件监控 | [Ch5](./ch05-context.md) |
| **Live vs Cumulative** | live=当前上下文 live 长度（驱动压缩），cumulative=累计用量（驱动计费），Grok `apply_terminal_event_overrides` 分离 | [Ch5](./ch05-context.md) / [Ch8](./ch07-model.md) |
| **Lost in the Middle** | Liu et al. 2024：关键信息埋在上下文中段时性能显著塌陷（U 型曲线），压缩要保头保尾、牺牲中段 | [Ch5](./ch05-context.md) |
| **RULER / Needle in a Haystack** | 长上下文有效长度评测：标称 128K 的模型常在 32K–64K 失守——"不要把 200K 当 200K 用" | [Ch5](./ch05-context.md) |

## Tools

| 术语 | 定义 | 出处 |
|------|------|------|
| **ToolSpec / ToolExecutor** | 工具的"规格"（LLM 可见 JSON）与"执行体"，同源绑定避免漂移 | [Ch4](./ch04-tools.md) |
| **Schema 漂移** | LLM 可见 schema 与执行侧校验分离演进导致的幻觉参数/幽灵工具/类型截断三类故障 | [Ch4](./ch04-tools.md) |
| **悬垂工具调用（dangling tool call）** | Prompt 中途改写而 ToolSpecs 未重建，模型调用已卸载工具；Grok 以 `repair_dangling_tool_calls` 启动自愈兜底 | [Ch2](./ch02-common-model.md) / [Ch11](./ch10-reliability.md) |
| **ToolRouter / ToolRegistry** | 工具注册与路由中枢；Codex 每个 `StepContext` 重建 `build_tool_router()` 保证工具清单与 prompt 同一快照 | [Ch4](./ch04-tools.md) |
| **ToolExposure** | 工具可见性分级 `Direct/Deferred/Hidden`，首轮仅暴露 Direct | [Ch4](./ch04-tools.md) |
| **defer_loading / ToolSearch** | 延迟加载：首轮只给"目录"，模型按需检索加载工具"正文"，把首轮 schema 预算压到 1/5 | [Ch4](./ch04-tools.md) |
| **权限晶格（Permission Lattice）** | 权限合并序 `Deny > Ask > Allow`，同级细粒度覆盖通配 | [Ch4](./ch04-tools.md) |
| **bwrap（bubblewrap）** | 进程级沙箱：mount/net/pid/user namespace 隔离，Codex 每次 `bash` fork 出带 `execpolicy` 的沙箱子进程 | [Ch4](./ch04-tools.md) |
| **isConcurrencySafe** | 工具是否可并行执行的声明位，默认 false；三段式并行= preflight 串行 + 执行分桶 + 顺序回填 | [Ch4](./ch04-tools.md) |
| **Toolformer** | Meta 2023：自监督让 LM 学会插入 `[API_CALL]`，证明"何时调工具"可被预训练学会 | [Ch4](./ch04-tools.md) |
| **Gorilla** | Berkeley 2023：检索缩小候选 API 集 + AST 评测，预示今天的 Tool Search 与 `defer_loading` | [Ch4](./ch04-tools.md) |
| **Function Calling** | OpenAI 2023-06：`tools` + `tool_calls` + `tool` role 进入协议，统一了此后所有 Agent 的工具调用线形 | [Ch4](./ch04-tools.md) |
| **MCP** | Model Context Protocol，工具扩展的事实标准 | [Ch4](./ch04-tools.md) |
| **Skill / Plugin** | 第二层扩展（OpenCode `skill/`、DeepSeek `Cordis`、Grok `SkillInfo`） | [Ch4](./ch04-tools.md) / [Ch9](./ch08-multi-agent.md) |
| **Cordis** | DeepSeek Harness 的事件/服务框架，工具与能力均为插件（"一切皆插件"） | [Ch4](./ch04-tools.md) / [Ch9](./ch08-multi-agent.md) |
| **DFSDT** | ToolLLM 的深度优先搜索式决策树：多条推理路径成树、走不通回溯，Loop 的轻量"试错-回退"外层 | [Ch4](./ch04-tools.md) |

## Memory

| 术语 | 定义 | 出处 |
|------|------|------|
| **Working Memory** | 单次 Task 内的中间推理状态，驻留 Context Window，可由 LLM 自主编辑（MemGPT 自编辑机制） | [T2](./theory/chapter-02-memory.md) / [Ch6](./ch05b-memory.md) |
| **MemGPT** | 2023：OS 分页类比的 Agent Memory 奠基之作——主存/外存分页 + 换页函数，回答"怎么不爆窗" | [Ch6](./ch05b-memory.md) |
| **A-MEM** | 2025（NeurIPS）：Zettelkasten 笔记盒 + Note/Link/Evolution/Retrieval 四阶段，把最重的智能放在写入时 | [Ch6](./ch05b-memory.md) |
| **代理权前移** | Memory 智能从检索时（RAG）迁移到写入时（A-MEM）：写入即决定"连到哪、如何改写旧记忆" | [Ch6](./ch05b-memory.md) |
| **五维分类** | 《Memory in the LLM Era》综述框架：时间 × 信息类型 × 组织 × 代理权 × 演化，任意 Memory 系统可在此打点选型 | [Ch6](./ch05b-memory.md) |
| **Episodic / Semantic / Procedural** | 信息类型三分：情景=某次对话事实，语义=偏好/知识，程序=技能/工作流（Voyager 技能库即 procedural） | [Ch6](./ch05b-memory.md) |
| **Memory Pipeline 五步** | `Ingestion → Storage → Indexing → Retrieval → Forgetting`，每步都有"便宜但笨 vs 贵但准"的权衡 | [Ch6](./ch05b-memory.md) |
| **RAG** | 检索增强生成：智能放在检索时；在 Memory 视角下是"检索时代理权"的代表，与 A-MEM 互为镜像 | [Ch6](./ch05b-memory.md) |
| **Voyager 技能库** | NVIDIA 2023：自动课程 + Skill Library + 迭代提示的终身学习，OpenCode `skill/` 与 `ToolExposure.Deferred` 的思想源头 | [Ch1](./ch01-landscape.md) / [Ch6](./ch05b-memory.md) |
| **Generative Agents** | Stanford 2023：记忆流 + 重要性评分 + 反思（Reflection）的小镇模拟，首次做完整"检索-反思-规划"闭环 | [Ch6](./ch05b-memory.md) |
| **FadeMem / 衰减曲线** | 2026：艾宾浩斯遗忘曲线 + 强化回放 + 重要性门控，让"自然遗忘"有可微公式；回答"怎么忘" | [Ch6](./ch05b-memory.md) |
| **Zettelkasten** | 卡片盒笔记法：原子笔记 + 显式链接 + 持续演化，A-MEM 四阶段的直接思想来源 | [Ch6](./ch05b-memory.md) |

## Session

| 术语 | 定义 | 出处 |
|------|------|------|
| **Session** | `Vec<Message>` 的外部追加与重放，`append` 为唯一写路径 | [Ch7](./ch06-session.md) |
| **Event Sourcing** | Fowler 2005：不存"当前状态"，存"导致状态的所有事件"；状态是事件 fold 的结果 | [Ch7](./ch06-session.md) |
| **WAL** | Write-Ahead Log（ARIES 1992）：先写日志再改数据；Session 的 `append` 即 WAL 的 `write`，`turn/start` 即 checkpoint | [Ch7](./ch06-session.md) |
| **预写（pre-write）** | user 消息在 `callModel()` 前落盘（Claude `recordTranscript`），崩溃时"用户说过什么"永不丢 | [Ch7](./ch06-session.md) |
| **Journal** | Grok `xai-sqlite-journal`：SQLite 冷恢复 + 内存 `Vec<ConversationItem>` 热路径的"两级 log"，启动时 `dedup + repair` 自愈 | [Ch7](./ch06-session.md) |
| **rollout.jsonl** | Codex 的会话持久化文件：jsonl 追加 + thread-manager 多线程恢复（`ResumeSource`） | [Ch7](./ch06-session.md) |
| **history_version** | Codex 的 turn 边界方案：版本号递增检测过期视图，兼顾预算闸与血缘 | [Ch7](./ch06-session.md) |
| **turn_capture / turn_start_offset** | Grok 的 turn 边界方案：偏移量 bulk 切片 `conversation[off..]`，O(1) 定位且共享前缀无需回滚 | [Ch7](./ch06-session.md) |
| **fork / resume** | Session 的分支与重放：`--resume` 可信、`fork` 可分支是"可重放优于可恢复"的落地 | [Ch7](./ch06-session.md) |
| **compact_boundary.preservedSegment** | Claude 压缩边界的重链接结构 `{head/tail/anchor}`，保证压缩后 `--resume` 血缘不断 | [Ch7](./ch06-session.md) |
| **Trace** | 每 turn 的 token/工具/耗时记录（`tengu_*`/`codex-otel`/`EventV2Bridge`） | [Ch7](./ch06-session.md) / [Ch10](./ch09-observability.md) |

## Model

| 术语 | 定义 | 出处 |
|------|------|------|
| **Provider / Adapter** | 模型抽象的头两层：Provider 直连各厂商端点，Adapter 把 SSE/Responses/ChatCompletions 归一为统一流 | [Ch8](./ch07-model.md) |
| **StreamChunk** | Adapter 归一的输出形态：`text + reasoning + tool_use` 三通道交织为单一 `type` 枚举 | [Ch8](./ch07-model.md) |
| **PreparedLlmCall** | `LlmCallConfig` 经适配器剥除后的干净形态，供插件改写 | [Ch8](./ch07-model.md) |
| **适配器剥除（adapterDefaults）** | 2026 新不变量：适配器注入的默认参数显式剥离，插件层只见"干净的业务意图" | [Ch8](./ch07-model.md) |
| **waterfall 插件链** | DeepSeek Cordis 的改写管线：`'agent/request'` 与 `'agent/request-error'` 钩子让插件逐层改写请求与重试决策 | [Ch8](./ch07-model.md) |
| **Model Router** | 从"配置选型"到"智能选型"：按任务在 reasoning 与成本间做 Pareto 路由，模型抽象的未来方向 | [Ch8](./ch07-model.md) |

## 多 Agent

| 术语 | 定义 | 出处 |
|------|------|------|
| **Orchestrator-Worker / Swarm / Hierarchical** | 三类编排拓扑：主从汇总 / 对等群协作 / 树状委托；生产级以 O-W 为上限且禁嵌套 | [Ch9](./ch08-multi-agent.md) |
| **Inception Prompting** | CAMEL 的手法：把对方角色职责与输出格式写进 system prompt，使对话自主涌现任务分解 | [Ch9](./ch08-multi-agent.md) |
| **显式状态容器** | 任务规划必须落盘为显式状态（plan 文件/状态机）而非仅存于对话消息，Planner 与 Worker 共享的事实源 | [Ch9](./ch08-multi-agent.md) |
| **Worktree 隔离** | 子 Agent 文件系统隔离（`createAgentWorktree`/`xai-fast-worktree btrfs/overlay`） | [Ch9](./ch08-multi-agent.md) |

## 可靠性

| 术语 | 定义 | 出处 |
|------|------|------|
| **间接提示注入** | Greshake 等：网页/PDF/邮件等外部内容即攻击面——数据可变指令，只读工具也不安全 | [Ch11](./ch10-reliability.md) |
| **Confused Deputy** | 有权限的执行者被无权限者诱导（Hardy 1988）：权限必须按完整调用链评估的原因 | [Ch11](./ch10-reliability.md) |
| **威胁模型四象限** | 按"内容来源 × 工具权限"分象限定防线：只读内容也要过闸 | [Ch11](./ch10-reliability.md) |
| **LlmError / normalizeLlmFailure** | 失败归一：各家错误先归一为 `LlmError{retryable, retryAfterMs, requestId}` 再重试，无归一则重试逻辑散落腐化 | [Ch8](./ch07-model.md) / [Ch11](./ch10-reliability.md) |
| **DISPOSITION 处置表** | 错误类别 → 处置动作（重试/降级/熔断/上报）的显式映射表，每类错误配真实锚点 | [Ch11](./ch10-reliability.md) |
| **Circuit Breaker / Bulkhead / Timeout** | Nygard《Release It!》三模式：快速失败 / 舱壁隔离 / 所有远程调用必有截止时间 | [Ch11](./ch10-reliability.md) |
| **自愈三层** | L1 重试、L2 会话级修复（`repair_dangling_tool_calls`）、L3 启动自愈；自愈尽量在启动时做 | [Ch11](./ch10-reliability.md) |
| **12 字符原则** | `SENT_BEARER_PREFIX_LEN=12`：日志/回调中的凭证只留前 12 字符前缀，可辨认（哪把钥匙）+ 不可复原 | [Ch11](./ch10-reliability.md) |
| **异常即消息** | Qwen-Agent 的最小自愈：错误作为 FUNCTION 结果回填，模型下一轮自己修正参数，零基础设施成本 | [Ch11](./ch10-reliability.md) |
| **信任边界（库 vs 产品）** | 库形态把权限/沙箱推给宿主（Qwen-Agent），产品形态默认收紧兜底（Claude/Codex）；选型先问威胁模型属于哪边 | [Ch11](./ch10-reliability.md) |

## 评估

| 术语 | 定义 | 出处 |
|------|------|------|
| **AST 匹配** | 工具调用评测法：解析生成文本为语法树后比对函数名与参数结构，比字面匹配更客观（BFCL 沿用） | [Ch4](./ch04-tools.md) |
| **BFCL** | Berkeley Function Calling Leaderboard：AST/可执行性双轨，v2 起在真实环境跑调用校验状态变化——AST 合法 ≠ 可执行 ≠ 应被执行 | [Ch4](./ch04-tools.md) |
| **SWE-bench** | 真实 GitHub issue 修复 + F2P/P2P 测试判分，完全客观但只看最终 patch 不看过程 | [Ch10](./ch09-observability.md) |
| **SWE-bench Verified** | OpenAI 2024-08 人工过滤的 500 题干净子集——基准本身也是需要审计的 artifact | [Ch10](./ch09-observability.md) |
| **AgentBench** | 8 类环境统一评测 Agent 能力（Liu et al. 2023），环境真实性有限 | [Ch10](./ch09-observability.md) |
| **WebArena** | 自托管真实网站的长 horizon 任务评测，部署重 | [Ch10](./ch09-observability.md) |
| **Tau-bench** | 用户模拟 + 工具 + 策略符合度的双重评测（航空/零售域），pass^k 指标的出处 | [Ch10](./ch09-observability.md) |
| **pass^k** | Tau-bench 指标：k 次独立运行全部通过才算过，暴露"平均分掩盖的不稳定性" | [Ch10](./ch09-observability.md) |
| **LLM-as-Judge** | 用 LLM 当裁判的过程/质量评分，需控三类偏置；与结果判分（SWE-bench 式）互补 | [Ch10](./ch09-observability.md) |
| **PRM / ORM** | 过程奖励模型 / 结果奖励模型：逐步打分 vs 只看最终结果；PRM 在线化是自愈闭环的信号源 | [Ch10](./ch09-observability.md) |
