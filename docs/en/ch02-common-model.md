# Chapter 2 The Common Model: The Six Pieces

> The nine implementations look wildly different on the surface, but peel them open and they are all the same set of "six pieces" deformed under different constraints. This chapter first **formalizes** that model, then uses counterexamples to show "what happens when one piece is missing," laying down a coordinate system for the close readings that follow.

The book's governing formula is **Agent = Model + Harness** — the "six pieces" of this chapter are precisely the **internal structure of the Harness**. Note that the sixth piece, "Model," does not mean the LLM itself, but the **model abstraction/adaptation layer** on the Harness side; the Model (LLM) on the right-hand side of the formula is an external dependency that these six pieces surround, schedule, and constrain.

## 2.1 One-Sentence Definition and Formalization

**Agent = Prompt + Loop + Tools + Context + Session + Model** — all six are indispensable. Formalized as a state machine:

```
State = (Prompt, Context, Session, PendingInput)
Loop  : State -> Model -> (ToolCalls | Text) -> Tools -> State'
         └─ budget gate / cancellation / retry may intervene at every step

Invariants:
  I1 Session.append is the only write path (replayable)
  I2 Prompt and ToolSpecs share one snapshot (StepContext is atomic)
  I3 Context = project(Session) (projection, not rewriting)
  I4 every Model call is bounded by a Token budget
```

```
user input ──► Loop (scheduling, see Ch3)
                ├─► Model (sampling, see Ch8)
                ├─► Tools (execution, see Ch4)
                ├─► Context (memory/compaction/caching, see Ch5/Ch6)
                ├─► Session (persistence/replay, see Ch7)
                └─► Prompt (system prompt assembly)
                      ▲
                      └─ observability (Trace/Metrics, see Ch10)
```

### Why six pieces, not four or eight

- Merge `Prompt` and `Context`? No. `Prompt` is **instructions** (System + tool descriptions), `Context` is **memory** (message history + compaction artifacts); the two behave differently under caching (`cache_control`) and compaction (`for_prompt`) ([Ch5 (zh)](../ch05-context.md)).
- Merge `Session` and `Context`? No. `Session` is the **full record of facts** (an append-only log), `Context` is a **projection** (the subset visible to this request); the semantics of `Session.fork()` and `Context.for_prompt()` are orthogonal ([Ch7 (zh)](../ch06-session.md) vs [Ch5 (zh)](../ch05-context.md)).
- Split `Memory` out as a seventh piece? This book treats `Memory` as the **long-term extension** of `Context` and the **index layer** of `Session` ([Ch6 (zh)](../ch05b-memory.md)) — it gets its own chapter but not top-level-piece status, to avoid blurring `Context`'s responsibilities.

## 2.1b A Short Evolutionary History of the Six Pieces (Aligned with the Papers)

The six pieces were not born at the same time — each has its own paper lineage and its own engineering inflection point. As you read later chapters, you can always come back to this "piece × paper" table to locate yourself:

| Piece | Source paper / event | Key idea | Engineering inflection point |
|-------|----------------------|----------|------------------------------|
| **Prompt** | GPT-3 few-shot (arXiv:2005.14165, 2020); CoT (arXiv:2201.11903, 2022) | Instructions as programs; in-context learning | 2023: the System Prompt becomes a core product asset (ChatGPT Custom Instructions) |
| **Loop** | ReAct (arXiv:2210.03629, 2022); Reflexion (NeurIPS 2023) | reason→act→observe; linguistic self-reflection | 2023-03: AutoGPT ignites "looping Agents"; 2024: SWE-agent establishes the HCI design space |
| **Tools** | Toolformer (arXiv:2302.04761, 2023); Gorilla (arXiv:2305.15334) | Self-supervised call learning; retrieval-based tool selection | 2023-06: Function Calling becomes a protocol → 2024-11: MCP standardizes the ecosystem |
| **Context/Memory** | Lost in the Middle (arXiv:2307.03172, 2023); MemGPT (arXiv:2310.08560) | Long window ≠ good memory; the OS paging analogy | 2024-08: Prompt Caching ships → compaction shifts from "saving tokens" to "preserving cache + preserving key information" |
| **Session** | Event Sourcing (Fowler 2005); Dapper (2010) | Store events, not state; end-to-end tracing | 2024: product-grade `--resume`/fork becomes standard CLI equipment |
| **Model abstraction** | LangChain (2022) → AI SDK (Vercel 2023) | A unified Provider interface | 2024: multi-protocol divergence (Messages/Responses) → the adapter-stripping pattern |

Three evolutionary laws run through the whole book:

1. **Every piece went through the same three-stage arc: "paper proves feasibility → protocol standardization → defense-in-depth engineering."** Tools is the canonical case — Toolformer proved feasibility (2023-02), Function Calling completed protocolization (2023-06), MCP completed ecosystem-ization (2024-11); after that, all competition moved to defense-in-depth engineering around permissions/sandboxes/visibility.
2. **Complexity migrated from the model side to the Harness side**: in 2023 an Agent's complexity lived in its prompts (AutoGPT was all prompt); in 2026 the complexity lives in the Harness (the nine products' system prompts have actually grown more restrained) — which is exactly why this book exists.
3. **The library/product divide widens as the piece count grows**: Qwen-Agent implements only four of the six pieces (no Session/Trace, weak safety), Pi does five and a half; the five product-form entrants implement all six with mutual coupling. **Every additional piece you take on raises the bar for engineering completeness non-linearly.**

## 2.2 The Six Pieces in Detail (with Counterexamples)

### 1) Prompt — the only programmable "OS kernel"

- The **System Prompt** is the Agent's "kernel mode": it defines the role, the capability boundary, and the rules of tool use
- **User Context** (`getSystemContext/getUserContext` in `claude-code-haha/src/context.ts:116`) injects `git status / CLAUDE.md / OS`, cached via `memoize`
- **Dynamic assembly** (`TemplateRenderer.render_with_extra` in `grok-build/crates/codegen/xai-grok-tools/src/bridge.rs`, `AgentBuilder.finalize_prompt()`) keeps the tool list and the prompt sourced from the same origin

> Common law: **the prompt and the tool list must come from the same snapshot**. Codex rebuilds the `ToolRouter` inside `StepContext` at every step (`codex-rs/core/src/tools/spec_plan.rs:117`); Grok's `finalize_prompt()` re-renders after the tool set is finalized — both exist to prevent "the model calling a tool that was unloaded in a previous turn."

> Counterexample: if `Prompt` is rewritten mid-`Loop` while `ToolSpecs` is not rebuilt, the model can emit a **dangling tool call**. Grok added `repair_dangling_tool_calls` self-healing in `ChatState::new()` for exactly this, at the cost of a full scan at startup.

**Close-reading pointer**: compare the `memoize + parallel git` of `claude-code-haha/src/context.ts:116 getSystemContext()` with the one-shot build of `claw-code-main/rust/crates/runtime/src/prompt.rs SystemPromptBuilder::with_project_context`, and think through the "cache vs freshness" trade-off.

### 2) Loop — a state machine, not a simple loop

The minimal form (Pi `packages/agent/src/agent-loop.ts:155 runLoop`):

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

The production form (Claude `src/query.ts:219` / Codex `codex-rs/core/src/session/turn.rs:153` / DeepSeek `packages/core/agent-loop/src/agent.ts:70 ReactLoopAgent`) layers on top of this:

- Three nested levels: `turn loop → sampling retry loop → stream consume loop`
- Interruption semantics: `Inbox.splice(next-turn vs next-step)` / `InputQueue.steer`
- Budget gates: `needsCompaction / should_auto_compact / history_version`

> Common law: **the essence of the Loop is the closure of "sample → execute → write back"**; every reliability enhancement (retry, compaction, cancellation) is a "gate" bolted onto this closure. See the close reading in [Ch3 (zh)](../ch03-loop.md).

> Counterexample: if the Loop has no `hop` cap (Claude/Pi use `25`), the model will **sample forever** inside a tool-error cycle; if there is no `cancellation_token` (`codex-rs/core/src/tools/context.rs:56`), the user's `Ctrl-C` cannot interrupt a running `bash`.

### 3) Tools — spec and execution from one source, permission as a cross-cutting concern

The common shape (highly consistent across 8 of the 9, with Claw as the exception — see the counterexample at the end of this section and cross-check with [Ch4 (zh)](../ch04-tools.md)):

```
ToolSpec (serializable into LLM-visible JSON)  ←→  ToolExecutor (executable)
        │                                              │
        └──────────── same object / same registry ─────┘
                              │
                       ToolRouter / ToolRegistry
                              │
                  approval → sandbox → execute → Hook → write back
```

- **One source**: Claude `Tool<Input,Output>` (`src/Tool.ts:362`), Codex `ToolExecutor<Invocation>{spec(),handle()}` (`codex-rs/tools/src/tool_executor.rs:106`), OpenCode `Tool.Def` (`packages/opencode/src/tool/tool.ts:55`), Pi `AgentTool` — all of them "weld spec and execution together"
- **Tiered visibility**: Codex `ToolExposures bitflags{NONE/DIRECT/DEFERRED/CODE_MODE/ALL}`, Claude `ToolSearch defer_loading`, OpenCode's hidden agents with `native:true` — all are answers to the "first-turn schema budget" problem
- **Permission is cross-cutting**: not `if (allowed)` inside every tool, but unified interception in the orchestrator (Claude `ToolPermissionContext`, Codex `AskForApproval`, OpenCode `PermissionV1.Ruleset`)

> Counterexample: if spec and execution are separated (as in early Claw, where `src/tools.py:24 load_tool_snapshot()` only filtered by name), you get **schema drift** — the model passes arguments per the old `parameters` while the execution side has already changed its validation, producing a batch of `InvalidArgumentsError`. Codex welding `spec()` onto the same trait as `handle()` is precisely the fix for this.

See [Ch4 (zh)](../ch04-tools.md) for details.

### 4) Context / Memory — budget-driven, projection not rewriting

```
Token budget ──► estimation (chars/4 or tiktoken) ──► trigger threshold ──► compaction strategy
                                                          ├─ summarization (Abstractive, Haiku/small model)
                                                          ├─ truncation (Truncation, drop old turns)
                                                          ├─ extraction (Extractive, keep key tool_results)
                                                          └─ collapsing (Collapse, fine-grained per-segment)
```

- **Estimation**: almost everyone except Qwen-Agent uses `chars/4` (`claude-code-haha/src/utils/tokens.ts`, Grok `xai-chat-state/src/actor/state.rs:estimate_item_tokens`), explicitly giving up `tiktoken` in exchange for zero dependencies and speed
- **Triggering**: all production-grade systems are **token-budget-driven** (Claude `effectiveWindow-13k`, Grok `85%`, Codex `history_version`); only prototypes are turn-count-driven (Claw `compact_after_turns=12`)
- **Projection**: `Session` keeps the full record; `for_prompt()` / `transformContext` / `RuntimeContextProjection.project()` produces the LLM-visible subset (Pi `docs/book/src/12-memory-projection.md`)

> Counterexample: if Context rewrites the Session directly (instead of projecting), `--resume` and `Session.fork()` lose their lineage; Pi's two-stage `transformContext → convertToLlm` exists precisely so that compaction happens at the `AgentMessage` layer without polluting the `Message` persistence layer.

See [Ch5 (zh)](../ch05-context.md) (Context engineering) and [Ch6 (zh)](../ch05b-memory.md) (Memory deep dive).

### 5) Session / Trace — replayable beats recoverable

```
user message ──► Session.append(event) ──► persistence (jsonl/sqlite/journal)
                  │
                  ├─► Trace (per-turn tokens/tools/latency)
                  ├─► branching (fork/branch/navigation)
                  └─► replay (resume / turn_capture offset / history_version)
```

- **Appending beats overwriting**: Claude's `recordTranscript` pre-writes the user message before the API response, Codex's `history_version` increments monotonically, Grok's `turn_capture.turn_start_offset` avoids cloning entry by entry
- **Events are the log**: DeepSeek's `Session.append(eventType)` is the only write path; `turn/start, step/start/end, assistant/chunk` are all events
- **Built-in observability**: `tengu_*` (Claude), `codex-otel` (Codex), `EventV2Bridge` (OpenCode), `UsageLedger` (Grok)

> Counterexample: if the Session only writes in batch at the end of a turn (instead of `Session.append` per event), a crash loses the whole turn; this is why Claude **writes the user message before calling the model** in `QueryEngine.submitMessage()`, guaranteeing that `--resume` can recover.

See [Ch7 (zh)](../ch06-session.md) and [Ch10 (zh)](../ch09-observability.md).

### 6) Model — from SDK wrapper to adapter stripping

```
Provider (Anthropic/OpenAI/DeepSeek/xAI/local)
   │
Adapter (SSE/Responses/ChatCompletions unified into StreamChunk)
   │
PreparedLlmCall (a clean LlmCallConfig that plugins can rewrite)
   │
Retry/Attribution (retry + 401 attribution + billing separation)
```

- **Early days**: a single SDK wired directly (Claude `@anthropic-ai/sdk`)
- **Middle period**: AI SDK unification (OpenCode `BundledSDK.languageModel`, 10+ providers)
- **Recent**: adapter stripping (DeepSeek's removal of `adapterDefaults`, Grok's `apply_terminal_event_overrides` rewriting `total_tokens` to the live length via `context_details`)

> Counterexample: if the adapter injects `reasoningEffort/maxTokens` directly into `LlmCallConfig` without stripping them, the plugin layer sees a "contaminated config" and cannot do a clean `waterfall 'agent/request'` rewrite (the motivation behind DeepSeek `packages/llm/llm/src/adapter-failure.ts`).

See [Ch8 (zh)](../ch07-model.md).

## 2.3 The Five Constraints (Formalized)

The five problems Agent Infra must solve simultaneously (the framework from [Theory volume T1 (zh)](../theory/chapter-01-landscape.md), and all nine head-to-head comparisons in this book hit every one of them):

| Constraint | Formalization | Typical solutions | Failure symptom |
|------------|---------------|-------------------|-----------------|
| State | The LLM is stateless; `State_{t+1}=f(State_t, ToolResult_t)` must live outside it | `Session extends Vec<Message>` + event appending | Lost state = no `resume`; the whole history must be replayed |
| Resources | `|Context| ≤ Window - Reserve`, `Cost = Σ input×p_in + output×p_out` | Budgets + compaction + caching + truncation | Over the window = PTL; over budget = silent failure |
| Reliability | `P(single-step failure) ≈ 1-(1-p_llm)(1-p_tool)^n`, approaching 1 as n grows | Retry + interception + degradation + self-healing | A single point of failure cascades into a whole-turn failure |
| Composability | The Cartesian product `Tools × Agents × Envs` | Registries + namespaces + isolation | Tool-name collisions, concurrent file-write conflicts |
| Cost | `Cost_turn = cached×p_cached + uncached×p_uncached + output×p_out` | Caching + summarization + smart retrieval | Without caching, 20-turn cost grows exponentially |

**A cost example** (the token economics of [Theory volume T3 (zh)](../theory/chapter-03-context.md)):

```
Model Opus 200K, $15/$75 per 1M
20-turn conversation, no caching: Σ_{i=1}^{20} i×avg_tokens ≈ 210×avg ≈ $X
With Prompt Caching (80% prefix reuse): Cost ≈ 0.2×X + 0.8×X×0.1 (cached price) ≈ 0.28X
→ the savings from summarization (32%) and caching (58%) do not stack linearly;
  compute them separately as "cacheable prefix / non-cacheable increment"
```

## 2.4 The Minimal Working Loop (a 200-Line Mental Model)

Using Pi's shape to present "the smallest Agent that actually runs" — every production enhancement later in the book is a "gate" added onto this loop:

```ts
// Pseudocode, corresponding to pi/packages/agent/src/agent-loop.ts:155 runLoop + my-agent/src/loop.ts
async function agentLoop(userInput, ctx, model, tools) {
  ctx.messages.push({ role: 'user', content: userInput });
  for (let hop = 0; hop < 25; hop++) {
    if (needsCompaction(ctx)) await compact(ctx);          // gate 1: budget
    const res = await model.stream(ctx.forPrompt());       // sample
    if (res.toolCalls.length === 0) return res.text;       // done
    const results = await runTools(res.toolCalls, tools);  // execute
    ctx.messages.push(res.message, ...results);             // write back
  }
}
```

> Memorize this loop. Every comparison in the chapters ahead answers the same question: **on top of "sample → execute → write back," which gates did each implementation add, why, and at what cost.**

**Exercises**:
1. What happens if the `needsCompaction` check comes *after* `model.stream`? (Hint: the cost of PTL interception and `reactiveCompact`)
2. If `runTools` executes two `write_file` calls to the same path in parallel, is the result deterministic? (Hint: why `isConcurrencySafe` is necessary)
3. If `ctx.forPrompt()` returned `ctx.messages` directly instead of a projection, what would happen to `Session.fork()`? (Hint: `structuredClone` and `history_version`)

## 2.5 Summary: The Common-Knowledge Checklist

- [ ] Can draw the six-piece architecture diagram and state each piece's responsibility, interactions, and invariants I1–I4
- [ ] Can explain why "prompt and tool list from the same snapshot" matters, and give the dangling tool call counterexample
- [ ] Can articulate the difference between "projection vs rewriting" and "replayable vs recoverable," with acceptance criteria
- [ ] Can describe Context in the five steps "budget → estimation → trigger → compaction → caching," and compute the 20-turn cost
- [ ] Can explain why a Tool's "spec" and "execution" must share one source, and name the symptoms of schema drift
- [ ] Can hand-write the 200-line minimal loop and point out where the 3 "gates" sit

---

> The next chapter takes the first class of "gates" — **Loop scheduling and cancellation** ([Ch3 (zh)](../ch03-loop.md)) — apart line by line.
