# 附录 A 术语表

| 术语 | 定义 | 首次出现 |
|------|------|---------|
| **Agent Loop** | `采样→执行→回填`的闭合循环，七家均为三层嵌套（turn/retry/stream） | Ch2 |
| **Turn / Step** | Turn=一次用户输入到 end_turn；Step=Turn 内的一次采样+执行（DeepSeek `turn→step`, Codex `TurnContext/StepContext`） | Ch3 |
| **ToolSpec / ToolExecutor** | 工具的"规格"（LLM 可见 JSON）与"执行体"，同源绑定避免漂移 | Ch4 |
| **ToolExposure** | 工具可见性分级 `Direct/Deferred/Hidden`，首轮仅暴露 Direct | Ch4 |
| **Compaction** | 超预算时的压缩，含 snip/micro/collapse/摘要四层 | Ch5 |
| **Projection** | Session 保留全量，Context 是投影（Pi 术语） | Ch5 |
| **Prompt Caching** | `cache_control: ephemeral` 让前缀复用，断点需稳定（工具排序/prompt 冻结） | Ch5 |
| **Live vs Cumulative** | live=当前上下文 live 长度（驱动压缩），cumulative=累计用量（驱动计费），Grok `apply_terminal_event_overrides` 分离 | Ch6 |
| **Session** | `Vec<Message>` 的外部追加与重放，`append` 为唯一写路径 | Ch6 |
| **Trace** | 每 turn 的 token/工具/耗时记录（`tengu_*`/`codex-otel`/`EventV2Bridge`） | Ch6 |
| **PreparedLlmCall** | `LlmCallConfig` 经适配器剥除后的干净形态，供插件改写 | Ch7 |
| **Cordis** | DeepSeek Harness 的事件/服务框架，工具与能力均为插件 | Ch4/Ch8 |
| **Worktree 隔离** | 子 Agent 文件系统隔离（`createAgentWorktree`/`xai-fast-worktree btrfs/overlay`） | Ch8 |
| **Inbox** | DeepSeek 的精确打断语义，`next-turn` vs `next-step` + `wakeRequested` 闩锁 | Ch3 |
| **Hop** | Loop 的一轮采样+执行，Claude/Pi 上限 25 | Ch3 |
| **PTL** | `prompt_too_long`，触发 `reactiveCompact` | Ch5 |
| **MCP** | Model Context Protocol，工具扩展的事实标准 | Ch4 |
| **Skill / Plugin** | 第二层扩展（OpenCode `skill/`、DeepSeek `Cordis`、Grok `SkillInfo`） | Ch4/Ch8 |
| **ACI** | Agent-Computer Interface（SWE-agent 提出）：Agent 与执行环境的接口设计是独立变量，护栏内建在接口层 | Ch3 |
| **Verbal RL** | Reflexion 的"语言强化学习"：用自然语言复盘替代梯度更新，失败经验存入记忆缓冲供重试使用 | Ch3 |
| **Inception Prompting** | CAMEL 的手法：把对方角色职责与输出格式写进 system prompt，使对话自主涌现任务分解 | Ch9 |
| **DFSDT** | ToolLLM 的深度优先搜索式决策树：多条推理路径成树、走不通回溯，Loop 的轻量"试错-回退"外层 | Ch4 |
| **AST 匹配** | 工具调用评测法：解析生成文本为语法树后比对函数名与参数结构，比字面匹配更客观（BFCL 沿用） | Ch4 |
| **pass^k** | Tau-bench 指标：k 次独立运行全部通过才算过，暴露"平均分掩盖的不稳定性" | Ch10 |
| **PRM / ORM** | 过程奖励模型 / 结果奖励模型：逐步打分 vs 只看最终结果；PRM 在线化是自愈闭环的信号源 | Ch10 |
| **间接提示注入** | Greshake 等：网页/PDF/邮件等外部内容即攻击面——数据可变指令，只读工具也不安全 | Ch11 |
| **Confused Deputy** | 有权限的执行者被无权限者诱导（Hardy 1988）：权限必须按完整调用链评估的原因 | Ch11 |
| **Orchestrator-Worker / Swarm / Hierarchical** | 三类编排拓扑：主从汇总 / 对等群协作 / 树状委托；生产级以 O-W 为上限且禁嵌套 | Ch9 |
| **cache break** | 前缀字节级不一致导致缓存全 miss（工具顺序抖动/随机 ID 均可触发），Claude 以 `tengu_prompt_cache_break` 事件监控 | Ch5 |
