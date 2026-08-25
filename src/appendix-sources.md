# 附录 B 源码索引与锚点

> 本书所有结论均可回溯到以下锚点。快照时间 2026-08-22。

## Claude Code (`claude-code-haha`, `999.0.0-local`)

| 锚点 | 说明 |
|------|------|
| `src/query.ts:219 query()` | turn 外层循环，四层压缩触发点 |
| `src/QueryEngine.ts:184 QueryEngine` | SDK/headless 封装，`submitMessage()` + `recordTranscript` 预写 |
| `src/Tool.ts:362 Tool` | 工具类型与 `buildTool()` 默认 `isConcurrencySafe=false` |
| `src/tools.ts:194 getAllBaseTools()` | 30+ 工具注册，`assembleToolPool()` 分区排序 |
| `src/context.ts:116 getSystemContext()/getUserContext()` | System/User 上下文，`memoize` 缓存 |
| `src/utils/tokens.ts` / `src/services/tokenEstimation.ts` | `chars/4` 估算 |
| `src/services/compact/autoCompact.ts:62` | `AUTOCOMPACT_BUFFER=13K`, `MAX_OUTPUT_TOKENS_FOR_SUMMARY=20K` |
| `src/services/compact/compact.ts:387 compactConversation()` | 摘要执行：`PreCompact → streamCompactSummary → boundary` |
| `src/utils/sessionStorage.ts` | `getTranscriptPath() → ~/.claude/projects/<hash>/session.jsonl` |
| `src/services/api/claude.ts:606 getCacheControl()` | `cache_control: ephemeral` |
| `src/tools/AgentTool/` | 60+ 子 Agent 类型，`isolation:worktree\|remote` |

## Claw (`claw-code-main`)

| 锚点 | 说明 |
|------|------|
| `src/query_engine.py:193 QueryEnginePort` | Python 镜像，`compact_after_turns=12` |
| `src/tools.py:96 load_tool_snapshot()` | 工具快照加载 |
| `rust/crates/runtime/src/conversation.rs:117 ConversationRuntime` | 真实 Rust 循环 |
| `rust/crates/runtime/src/session.rs` | `Session{version,messages}` |
| `rust/crates/runtime/src/compact.rs` | `should_compact/format_compact_summary` |

## Codex (`codex`)

| 锚点 | 说明 |
|------|------|
| `codex-rs/core/src/session/turn.rs:153 run_turn()` | 三层嵌套主循环 |
| `codex-rs/core/src/context_manager/history.rs:93 ContextManager` | `for_prompt()` 投影 |
| `codex-rs/tools/src/tool_spec.rs:20 ToolSpec` | `ToolSpec{Function/Namespace/ToolSearch}` |
| `codex-rs/tools/src/tool_executor.rs:106 ToolExecutor` | `spec()+handle()` 同源 |
| `codex-rs/core/src/tools/spec_plan.rs:117 build_tool_router()` | 每 StepContext 重建 |
| `codex-rs/config/src/config_toml.rs:152 ConfigToml` | 两级配置模型 |
| `codex-rs/cli/src/main.rs:100 MultitoolCli` | 入口分发 |
| `book/src/ch07-agent-loop.md` | 逐函数走读 |

## OpenCode (`opencode`)

| 锚点 | 说明 |
|------|------|
| `packages/opencode/src/session/session.ts:224 Info Schema` | Effect Session，`create/fork/touch/list` |
| `packages/opencode/src/tool/tool.ts:55 Def` | `Tool.Def{parameters,execute:Effect}` |
| `packages/opencode/src/agent/agent.ts:35 Info` | `build/plan/general/explore/compaction` 6 类原生 agent |
| `packages/opencode/src/provider/provider.ts:100` | `BundledSDK` 10+ provider |
| `packages/opencode/src/tool/truncate.ts` | `Truncate.wrap()` 统一截断 |
| `tool/truncate.ts` + `agent/prompt/compaction.txt` | 隐藏 compaction agent |

## Pi (`pi`)

| 锚点 | 说明 |
|------|------|
| `packages/agent/src/types.ts:28 StreamFn` | `Model<Api> → Context → Stream` |
| `packages/agent/src/agent-loop.ts:155 runLoop` | 200 行最小闭环 |
| `packages/storage/src/` | `session-tree/session-storage/sqlite-backend` |
| `docs/book/src/12-memory-projection.md` | 投影术语 |
| `docs/book/src/23-subagents.md` | 子 Agent |

## DeepSeek Harness (`deepseek-harness`)

| 锚点 | 说明 |
|------|------|
| `packages/core/agent-loop/src/agent.ts:64 ReactLoopAgent` | `Phase{idle\|maintenance\|running}` 状态机 |
| `packages/core/agent/src/inbox.ts Inbox` | `splice(next-turn vs next-step)` 精确打断 |
| `packages/llm/llm/src/assembler.ts BlockAssembler` | `chunk → block-start/delta/block-end` |
| `packages/llm/llm/src/adapter-failure.ts` | `normalizeLlmFailure()` 归一 |
| `packages/session/session-persistence/src/` | `jsonl/sqlite` 双后端 |

## Grok Build (`grok-build`)

| 锚点 | 说明 |
|------|------|
| `crates/codegen/xai-chat-state/src/actor/state.rs:1 ChatState` | `conversation + UsageLedger + turn_capture` |
| `crates/codegen/xai-chat-state/src/actor/mod.rs ChatStateActor` | 单 task 拥有状态，`Command + Oneshot` |
| `crates/codegen/xai-grok-sampler/src/lib.rs SamplingClient` | 三后端×六端点，`GrokRequestHeaders` |
| `crates/codegen/xai-grok-tools/src/bridge.rs ToolBridge` | `ToolRegistry + ToolKind + TemplateRenderer` |
| `crates/codegen/xai-grok-agent/src/compaction.rs CompactionPolicy` | `auto_compact_threshold_percent:85` |
| `crates/codegen/xai-grok-agent/src/agent.rs AgentBuilder` | 30+ 流式配置 |
| `crates/codegen/xai-fast-worktree` | `btrfs/overlay` 快速分支 |

## 理论卷（`src/theory/`，原 agent-infra-research，2026-08 并入）

| 锚点 | 说明 |
|------|------|
| `src/theory/chapter-01-landscape.md` | 六组件模型 + 五约束 |
| `src/theory/chapter-02-memory.md` | MemGPT/A-MEM/FadeMem + 写入时代理 + 不可能三角 |
| `src/theory/chapter-03-context.md` | Token 经济学 + Prompt Caching + 摘要五类型 |
| `src/theory/chapter-04-runtime.md` | FSM vs while + `my-agent` 基线 |
| `src/theory/chapter-05-industry.md` | 行业岗位信号（ByteDance Memory Infra JD 解读） |
| `src/theory/chapter-06-ecosystem.md` | 框架/向量库/标准化生态图谱 |
| `src/theory/appendix-b.md` | **被否决的观点及原因**（负知识，源码卷无对位） |
| `src/theory/appendix-d.md` / `appendix-e.md` | Safety/Federated Memory；多模态 Memory 与端侧推理 |

---

> 需函数级时序图或与 `my-agent`（`src/loop.ts/context.ts/tools.ts`）逐行对齐表，可在上述锚点上继续深入。完整调研日志见 [附录 D](./appendix-research-log.md)。

## Qwen-Agent (`Qwen-Agent`, 阿里通义, Python 纯框架库)

| 锚点 | 说明 |
|------|------|
| `qwen_agent/agent.py:31 Agent(ABC)` | 抽象基类：run() 归一化消息/deepcopy/lang 检测，_run() 由子类定义工作流 |
| `qwen_agent/agent.py:78 run()` | 公共入口：copy.deepcopy + system_message 插入 + 中英文自动检测 |
| `qwen_agent/agent.py:178 _call_tool()` | 工具执行：异常捕获转 error_message 字符串回填（软自愈）；ToolServiceError 上抛 |
| `qwen_agent/agent.py:239 _detect_tool()` | function_call 格式检测 |
| `qwen_agent/agents/fncall_agent.py:73 _run()` | 主循环：`while num_llm_calls_available > 0` 计数器式 hop 上限（MAX_LLM_CALL_PER_RUN=20, settings.py:24）|
| `qwen_agent/memory/memory.py:32 Memory(Agent)` | **Memory 即 Agent**：RAG 式记忆（retrieval+doc_parser+keygen_strategies，max_ref_token=4000）|
| `qwen_agent/multi_agent_hub.py:22 MultiAgentHub` | 多 Agent 组合器（_agents 列表）；agents/router.py 路由、group_chat.py 群聊 |
| `qwen_agent/llm/base.py:61 BaseChatModel` | 模型注册表工厂 get_chat_model；`llm/function_calling.py` + `fncall_prompts/` 文本协议模拟 FC（非原生 FC 模型可用）|
| `qwen_agent/tools/base.py:24 TOOL_REGISTRY` | 全局工具注册表 + register_tool 装饰器；MCPManager 支持 mcpServers |
| `qwen_agent/utils/tokenization_qwen.py` | 真 tiktoken 计数（qwen.tiktoken），八家中唯一非 chars/4 |

> Qwen-Agent 的对照价值：Session/Trace/权限三层留白给宿主——与产品形态五家形成"库 vs 产品"分水岭，专节分析见 7.3.2 / 10.3.2 / 11.3.2。


## Hermes Agent (`hermes-agent`, Nous Research, Python 单体+网关)

| 锚点 | 说明 |
|------|------|
| `agent/conversation_loop.py:1766 run_conversation()` | 主循环入口：工具调用直到完成；流式回调供 TTS 提前合成 |
| `run_agent.py`（9215 行） | 单体式 Agent 核心（与 Codex 的 Bazel 多 crate 成两极） |
| `agent/context_engine.py:89 class ContextEngine(ABC)` | **可插拔上下文引擎**：`:146 should_compress()` 抽象——九家中唯一把压缩策略做成运行时可替换 |
| `agent/conversation_compression.py:469 CompressionCommitFence` | 压缩提交栅栏：解决"压缩落盘与并发写历史"的竞态（独特工程件） |
| `tools/terminal_tool.py:1517 _CONTAINER_BACKENDS={docker,singularity,modal,daytona,vercel_sandbox}` | **七种终端后端**（+local/ssh）：执行环境即插件，serverless 休眠唤醒 |
| `tools/skill_manager_tool.py:908 _create_skill()` | 自改进闭环：任务完成后自主创建技能，使用中自我改进（Voyager 谱系产品化） |
| `agent/memory_manager.py` + `memory_provider.py` | Agent 自策展记忆 + 周期性 nudge；`StreamingContextScrubber`(:182) 流式脱敏 |
| `trajectory_compressor.py`（1598 行） | 轨迹压缩生成训练数据——"research-ready"定位的独有件 |
| 多 Provider 适配 | `agent/{anthropic,bedrock,codex_responses}_adapter.py`；网关单进程接 Telegram/Discord/Slack 等 |

> 对照价值：①把 Ch6 记忆三范式补齐为四范式（compaction / RAG / Zettelkasten / **自策展+跨会话 FTS5**）；②把 Ch11 执行隔离从"沙箱选型"扩展为"环境即后端"；③Ch5 的"投影策略"被它形式化为 ContextEngine ABC。
