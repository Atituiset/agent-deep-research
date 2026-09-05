# 第2章 公共模型：六件套

> 九家实现表面差异很大，但剥开后都是同一套"六件套"在不同约束下的变形。本章先把这套模型**形式化**，再用反例说明"缺一件会怎样"，为后续精读打下坐标系。

## 2.1 一句话定义与形式化

**Agent = Prompt + Loop + Tools + Context + Session + Model**，六者缺一不可。形式化为状态机：

```
State = (Prompt, Context, Session, PendingInput)
Loop  : State -> Model -> (ToolCalls | Text) -> Tools -> State'
         └─ 预算闸 / 取消 / 重试 在每一步可介入

不变量：
  I1 Session.append 为唯一写路径（可重放）
  I2 Prompt 与 ToolSpecs 同快照（StepContext 原子）
  I3 Context = project(Session)（投影，非重写）
  I4 每次 Model 调用受 Token 预算约束
```

```
用户输入 ──► Loop（调度，见 Ch3）
              ├─► Model（采样，见 Ch8）
              ├─► Tools（执行，见 Ch4）
              ├─► Context（记忆/压缩/缓存，见 Ch5/Ch6）
              ├─► Session（持久化/重放，见 Ch7）
              └─► Prompt（系统提示词组装）
                    ▲
                    └─ 观测（Trace/Metrics，见 Ch10）
```

### 为什么是六件，而不是四件或八件

- 合并 `Prompt` 与 `Context`？不行。`Prompt` 是**指令**（System + 工具描述），`Context` 是**记忆**（历史消息 + 压缩产物），两者在缓存（`cache_control`）与压缩（`for_prompt`）上行为不同（Ch5）。
- 合并 `Session` 与 `Context`？不行。`Session` 是**全量事实**（追加日志），`Context` 是**投影**（本次请求可见子集），`Session.fork()` 与 `Context.for_prompt()` 的语义正交（Ch7 vs Ch5）。
- 拆出 `Memory` 为第七件？本书将 `Memory` 视为 `Context` 的**长期延伸**与 `Session` 的**索引层**（Ch6），单独立章但不单列为顶层件，避免与 `Context` 职责混淆。

## 2.1b 六件套演化小史（论文对齐）

六件不是同时诞生的——每一件都有自己的论文源头与工程化时间点。读后续章节时，可随时回到这张"组件 × 论文"对照表定位：

| 件 | 源头论文/事件 | 关键思想 | 工程化拐点 |
|----|--------------|---------|-----------|
| **Prompt** | GPT-3 few-shot (arXiv:2005.14165, 2020)；CoT (arXiv:2201.11903, 2022) | 指令即程序；上下文学习 | 2023 System Prompt 成为产品核心资产（ChatGPT Custom Instructions） |
| **Loop** | ReAct (arXiv:2210.03629, 2022)；Reflexion (NeurIPS 2023) | reason→act→observe；语言自反思 | 2023-03 AutoGPT 引爆"循环 Agent"；2024 SWE-agent 确立 HCI 设计空间 |
| **Tools** | Toolformer (arXiv:2302.04761, 2023)；Gorilla (arXiv:2305.15334) | 自监督学调用；检索式选工具 | 2023-06 Function Calling 协议化 → 2024-11 MCP 生态标准化 |
| **Context/Memory** | Lost in the Middle (arXiv:2307.03172, 2023)；MemGPT (arXiv:2310.08560) | 长窗≠好记忆；OS 分页类比 | 2024-08 Prompt Caching 上线 → 压缩从"省 token"变为"保缓存+保关键信息" |
| **Session** | Event Sourcing (Fowler 2005)；Dapper (2010) | 存事件不存状态；全链路追踪 | 2024 产品级 `--resume`/fork 成为 CLI 标配 |
| **Model 抽象** | LangChain (2022)→AI SDK (Vercel 2023) | Provider 统一接口 | 2024 多协议分化（Messages/Responses）→ 适配器剥除模式 |

三条演化规律，贯穿全书：

1. **每件都经历了"论文证明可行 → 协议标准化 → 工程纵深防御"三段式**：Tools 最典型——Toolformer 证明可行性（2023-02），Function Calling 完成协议化（2023-06），MCP 完成生态化（2024-11），之后各家的竞争全部转向权限/沙箱/可见性等纵深工程。
2. **复杂度从模型侧向 Harness 侧转移**：2023 年的 Agent 复杂度在 prompt 里（AutoGPT 全靠提示词）；2026 年的复杂度在 Harness 里（八家的 system prompt 反而更克制）——这正是本书存在的理由。
3. **库与产品的分野随件数增加而扩大**：Qwen-Agent 六件只做四件（无 Session/Trace、弱安全），Pi 做五件半；产品形态五家六件全做且互相耦合。**每多承担一件，工程完备度的要求非线性上升**。

## 2.2 六件套详解（附反例）

### 1) Prompt — 唯一可编程的"操作系统内核"

- **System Prompt** 是 Agent 的"内核态"：决定角色、能力边界、工具使用规范
- **User Context**（`getSystemContext/getUserContext` in `claude-code-haha/src/context.ts:116`）把 `git status / CLAUDE.md / OS` 注入，`memoize` 缓存
- **动态组装**（`TemplateRenderer.render_with_extra` in `grok-build/crates/codegen/xai-grok-tools/src/bridge.rs`、`AgentBuilder.finalize_prompt()`）让工具清单与提示词同源

> 公共规律：**提示词与工具清单必须同一次快照**。Codex 的 `StepContext` 每步重建 `ToolRouter`（`codex-rs/core/src/tools/spec_plan.rs:117`）、Grok 的 `finalize_prompt()` 在工具定版后重渲染，都是为了避免"模型调了上一轮已卸载的工具"。

> 反例：若 `Prompt` 在 `Loop` 中途被改写而 `ToolSpecs` 未重建，模型会产生**悬垂工具调用**（dangling tool call），Grok 为此在 `ChatState::new()` 增加 `repair_dangling_tool_calls` 自愈，代价是启动时全量扫描。

**精读指引**：对比 `claude-code-haha/src/context.ts:116 getSystemContext()` 的 `memoize + 并行 git` 与 `claw-code-main/rust/crates/runtime/src/prompt.rs SystemPromptBuilder::with_project_context` 的一次性构建，思考"缓存 vs 实时性"的权衡。

### 2) Loop — 状态机而非简单循环

最简形态（Pi `packages/agent/src/agent-loop.ts:155 runLoop`）：

```ts
while (true) { // outer: followUp
  while (hasMoreToolCalls || pendingMessages.length) {
    message = await streamAssistantResponse(context, config, signal, emit, streamFn);
    toolCalls = message.content.filter(isToolCall);
    toolResults = await executeToolCalls(toolCalls, config);
    context.messages.push(message, ...toolResults);
    if (await shouldStopAfterTurn(...)) break;
  }
  if (!(followUp = await getFollowUpMessages())) break;
}
```

生产形态（Claude `src/query.ts:219` / Codex `codex-rs/core/src/session/turn.rs:153` / DeepSeek `packages/core/agent-loop/src/agent.ts:70 ReactLoopAgent`）在此基础上叠加：

- 三层嵌套：`turn loop → sampling retry loop → stream consume loop`
- 中断语义：`Inbox.splice(next-turn vs next-step)` / `InputQueue.steer`
- 预算闸：`needsCompaction / should_auto_compact / history_version`

> 公共规律：**Loop 的本质是"采样→执行→回填"的闭合**，所有可靠性增强（重试、压缩、取消）都是在这个闭合上加"闸"。详见 Ch3 精读。

> 反例：若 Loop 无 `hop` 上限（Claude/Pi 的 `25`），模型在工具错误循环中会**无限采样**；若无 `cancellation_token`（`codex-rs/core/src/tools/context.rs:56`），用户 `Ctrl-C` 无法中断正在执行的 `bash`。

### 3) Tools — 规格与执行同源、权限是横切面

公共形态（跨 8 家高度一致）：

```
ToolSpec（可序列化为 LLM 可见的 JSON）  ←→  ToolExecutor（可执行）
        │                                        │
        └────────── 同一对象/同一注册表 ──────────┘
                         │
                    ToolRouter / ToolRegistry
                         │
                审批 → 沙箱 → 执行 → Hook → 回填
```

- **同源**：Claude `Tool<Input,Output>`（`src/Tool.ts:362`）、Codex `ToolExecutor<Invocation>{spec(),handle()}`（`codex-rs/tools/src/tool_executor.rs:106`）、OpenCode `Tool.Def`（`packages/opencode/src/tool/tool.ts:55`）、Pi `AgentTool` 都是"规格与执行焊在一起"
- **可见性分级**：Codex `ToolExposures bitflags{NONE/DIRECT/DEFERRED/CODE_MODE/ALL}`、Claude `ToolSearch defer_loading`、OpenCode `native:true` 的隐藏 agent——都在解"首轮 schema 预算"这道题
- **权限是横切面**：不在每个工具里 `if (allowed)`，而在编排器统一拦截（Claude `ToolPermissionContext`、Codex `AskForApproval`、OpenCode `PermissionV1.Ruleset`）

> 反例：若规格与执行分离（如早期 Claw `src/tools.py:24 load_tool_snapshot()` 仅做名字过滤），会出现**schema 漂移**——模型按旧 `parameters` 传参，执行侧已改校验，导致批量 `InvalidArgumentsError`。Codex 将 `spec()` 焊在 `handle()` 同一 trait 上即为对此的修正。

详见 Ch4。

### 4) Context / Memory — 预算驱动、投影而非重写

```
Token 预算 ──► 估算（chars/4 或 tiktoken）──► 触发阈值 ──► 压缩策略
                                                        ├─ 摘要（Abstractive, Haiku/小模型）
                                                        ├─ 截断（Truncation, 丢弃旧轮）
                                                        ├─ 抽取（Extractive, 保留关键 tool_result）
                                                        └─ 折叠（Collapse, 细粒度按段折叠）
```

- **估算**：除 Qwen-Agent 外几乎都用 `chars/4`（`claude-code-haha/src/utils/tokens.ts`、Grok `xai-chat-state/src/actor/state.rs:estimate_item_tokens`），显式放弃 `tiktoken` 以换取零依赖与速度
- **触发**：生产级均为 **token 预算驱动**（Claude `effectiveWindow-13k`、Grok `85%`、Codex `history_version`），仅原型用轮数驱动（Claw `compact_after_turns=12`）
- **投影**：`Session` 保留全量，`for_prompt()` / `transformContext` / `RuntimeContextProjection.project()` 产出 LLM 可见子集（Pi `docs/book/src/12-memory-projection.md`）

> 反例：若 Context 直接重写 Session（而非投影），`--resume` 与 `Session.fork()` 会丢失血缘；Pi 的两阶段 `transformContext → convertToLlm` 正是为了让压缩发生在 `AgentMessage` 层，不污染 `Message` 持久化层。

详见 Ch5（Context 工程）与 Ch6（Memory 深潜）。

### 5) Session / Trace — 可重放优于可恢复

```
用户消息 ──► Session.append(event) ──► 持久化（jsonl/sqlite/journal）
                │
                ├─► Trace（每 turn 的 token/工具/耗时）
                ├─► 分支（fork/branch/navigation）
                └─► 重放（resume / turn_capture offset / history_version）
```

- **追加优于覆盖**：Claude `recordTranscript` 在 API 响应前预写 user 消息、Codex `history_version` 递增、Grok `turn_capture.turn_start_offset` 避免逐条克隆
- **事件即日志**：DeepSeek `Session.append(eventType)` 为唯一写路径，`turn/start, step/start/end, assistant/chunk` 均为事件
- **可观测内建**：`tengu_*`（Claude）、`codex-otel`（Codex）、`EventV2Bridge`（OpenCode）、`UsageLedger`（Grok）

> 反例：若 Session 仅在 turn 结束时批量写（而非 `Session.append` 逐事件），崩溃会丢整 turn；Claude 为此在 `QueryEngine.submitMessage()` 中**先写 user 消息再调模型**，保证 `--resume` 可恢复。

详见 Ch7 与 Ch10。

### 6) Model — 从 SDK 封装到适配器剥除

```
Provider（Anthropic/OpenAI/DeepSeek/xAI/本地）
   │
Adapter（SSE/Responses/ChatCompletions 归一为 StreamChunk）
   │
PreparedLlmCall（干净的 LlmCallConfig，供插件改写）
   │
Retry/Attribution（重试 + 401 归因 + 计费分离）
```

- **早期**：单 SDK 直连（Claude `@anthropic-ai/sdk`）
- **中期**：AI SDK 统一（OpenCode `BundledSDK.languageModel` 10+ provider）
- **近期**：适配器剥除（DeepSeek `adapterDefaults` 去除、`Grok apply_terminal_event_overrides` 以 `context_details` 重写 `total_tokens` 为 live 长度）

> 反例：若适配器将 `reasoningEffort/maxTokens` 直接注入 `LlmCallConfig` 且不剥除，插件层看到的是"被污染的配置"，无法做干净的 `waterfall 'agent/request'` 改写（DeepSeek `packages/llm/llm/src/adapter-failure.ts` 的动机）。

详见 Ch8。

## 2.3 五大约束（形式化）

Agent Infra 要同时解的五道题（[理论卷 T1](./theory/chapter-01-landscape.md) 的框架，在本书七码一书对照中全部命中）：

| 约束 | 形式化 | 典型解法 | 失效症状 |
|------|--------|---------|---------|
| 状态 | LLM 无状态，`State_{t+1}=f(State_t, ToolResult_t)` 必须外置 | `Session extends Vec<Message>` + 事件追加 | 状态丢=无法 `resume`，需重放整段历史 |
| 资源 | `|Context| ≤ Window - Reserve`，`Cost = Σ input×p_in + output×p_out` | 预算 + 压缩 + 缓存 + 截断 | 超窗=PTL，超预算=静默失败 |
| 可靠性 | `P(单步失败) ≈ 1-(1-p_llm)(1-p_tool)^n`，n 增大时接近 1 | 重试 + 扣留 + 降级 + 自愈 | 单点失败级联为整 turn 失败 |
| 可组合 | `Tools × Agents × Envs` 笛卡尔积 | 注册表 + 命名空间 + 隔离 | 工具名冲突、文件并发写冲突 |
| 成本 | `Cost_turn = cached×p_cached + uncached×p_uncached + output×p_out` | Caching + 摘要 + 智能检索 | 无缓存时 20 轮成本指数增长 |

**成本算例**（[理论卷 T3](./theory/chapter-03-context.md) 的 Token 经济学）：

```
模型 Opus 200K, $15/$75 per 1M
20 轮对话，无缓存：Σ_{i=1}^{20} i×avg_tokens ≈ 210×avg ≈ $X
有 Prompt Caching（前缀复用 80%）：Cost ≈ 0.2×X + 0.8×X×0.1（cached 价）≈ 0.28X
→ 摘要 32% + Cache 58% 的节省并非线性叠加，需按"可缓存前缀/不可缓存增量"分项计算
```

## 2.4 最小可用闭环（200 行心智模型）

用 Pi 的形态给出"跑得起来的最小 Agent"——后续所有生产增强都是在这个闭环上加"闸"：

```ts
// 伪代码，对应 pi/packages/agent/src/agent-loop.ts:155 runLoop + my-agent/src/loop.ts
async function agentLoop(userInput, ctx, model, tools) {
  ctx.messages.push({ role: 'user', content: userInput });
  for (let hop = 0; hop < 25; hop++) {
    if (needsCompaction(ctx)) await compact(ctx);          // 闸1：预算
    const res = await model.stream(ctx.forPrompt());       // 采样
    if (res.toolCalls.length === 0) return res.text;       // 结束
    const results = await runTools(res.toolCalls, tools);  // 执行
    ctx.messages.push(res.message, ...results);             // 回填
  }
}
```

> 记住这个闭环，后续每章的对比都是在回答：**在"采样→执行→回填"上，各家加了哪些闸、为什么加、代价是什么。**

**思考题**：
1. 若 `needsCompaction` 判断在 `model.stream` 之后，会发生什么？（提示：PTL 扣留与 `reactiveCompact` 的代价）
2. 若 `runTools` 并行执行两个 `write_file` 到同一路径，结果是否确定？（提示：`isConcurrencySafe` 的必要性）
3. 若 `ctx.forPrompt()` 直接返回 `ctx.messages` 而非投影，`Session.fork()` 会怎样？（提示：`structuredClone` 与 `history_version`）

## 2.5 小结：公共知识清单

- [ ] 能画出六件套架构图并说清每件的职责、交互与不变量 I1–I4
- [ ] 能解释"提示词与工具清单同快照"为什么重要，并举出 dangling tool call 反例
- [ ] 能说清"投影 vs 重写"与"可重放 vs 可恢复"的区别与验收条件
- [ ] 能用"预算→估算→触发→压缩→缓存"五步描述 Context，并算清 20 轮成本
- [ ] 能区分 Tool 的"规格"与"执行"为何要同源，并说出 schema 漂移的症状
- [ ] 能手写 200 行最小闭环并指出 3 个"闸"的位置

---

> 下一章将把"闸"的第一类——**Loop 的调度与取消**——逐行拆开。
