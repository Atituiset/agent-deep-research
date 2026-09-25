# Chapter 1 The Landscape and Its Positioning

> Four questions first: what Agent Infra is, where it came from (a 60-year lineage), why 2025–2026 became the inflection point, and where each of the nine implementations stands. This chapter is the map of the whole book — every later chapter returns to this map to locate itself.

The book's governing formula is: **Agent = Model + Harness**. The Model handles sampling and reasoning; the Harness handles everything else — scheduling, tools, memory, persistence, and guardrails. The Harness's internal structure is formalized in [Chapter 2](./ch02-common-model.md) as the **six-piece set**: Prompt, Loop, Tools, Context, Session, and the Model abstraction (the adaptation layer over the various underlying LLMs). The nine-implementation panorama in this chapter is positioned by the trade-offs each one makes across these six pieces.

## 1.1 The Layers of Agent Infra

![Three-layer architecture of Agent Infra: application layer, infrastructure layer, model layer](/figures/fig-1-1-agent-infra-layers.svg)

<p class="fig-caption">Figure 1-1 · The three layers of Agent Infra: the application layer calls downward and the model layer supports upward; the Agent Infrastructure sandwiched between them is the subject of this book</p>

The analogy between traditional software and Agent software is confirmed one by one in the nine codebases:

| Traditional component | Agent counterpart | Evidence in this book |
|---------|-----------|---------|
| Operating system | Runtime (scheduling the LLM + tools) | All 9 have a `loop/turn/_run/run_conversation` main loop |
| Memory management | Memory / Context | 8 have compaction/projection; Qwen-Agent substitutes RAG; Hermes makes the engine a pluggable ABC |
| File system | Tool System | All 9 separate the Tool registry from execution |
| Process/thread | Session / Turn | The 6 product-form implementations persist Sessions; the library-form ones (Qwen-Agent/Pi core) hand them back to the host; Hermes uses SQLite FTS5 for cross-session retrieval |
| System logs | Trace / Observability | All record token/latency/tool traces, at varying granularity |
> **Reading note | What are compaction and projection?** (see Ch5.5/Ch7 for details)
>
> MemGPT's OS analogy: the context window ≈ RAM, external history ≈ Disk. This lands as two actions —
>
> - **compaction**: when the window can no longer hold the full history, **summarize** the old turns into a few sentences (e.g. a 50KB file-read result → one line saying "already read X"), freeing up space. Claude's four-layer compaction (Ch5.4) is the most elaborate implementation.
> - **projection (i.e. "project, don't rewrite")**: the Session always keeps the full history (append-only), and each request sends the model only the "currently visible subset" — like a database VIEW: the underlying data never moves; the view changes with the query. Codex's `for_prompt()` and Pi's `transformContext` are both projection functions.
>
> How the two relate: **compaction is one means of producing a projection; projection is the discipline of "never rewriting history."** Two exceptional lines: Qwen-Agent stores no conversational memory at all and pages in ad-hoc RAG retrieval every turn (`memory/memory.py:32`); Hermes abstracts the entire strategy into a `ContextEngine(ABC)` that can be swapped at runtime (`context_engine.py:89`).

## 1.2 The Full History of Agents: From Capability Security to LLM Agents (1966–2026)

Agent Infra did not appear out of nowhere — it is the confluence of four independent lineages:

### Lineage 1: Systems and Sandboxing ("how to execute safely")

```
1966  Capability-Based Security (Dennis & Van Horn)   capability as authorization → tool allowlists
1979  chroot                                            the origin of filesystem-view isolation
2000s Linux namespaces/cgroups/seccomp                  the container foundation
2017  bubblewrap (bwrap)                                rootless sandboxing as a CLI → Codex linux-sandbox
2018  gVisor (Google) / Firecracker (AWS)               user-space kernel / micro-VM → strong cloud isolation
2024+ @anthropic-ai/sandbox-runtime / xai-grok-sandbox  sandboxing becomes standard Agent equipment
```

### Lineage 2: Planning and Reasoning ("how to decide the next step")

```
2022-10 ReAct (arXiv:2210.03629, ICLR 2023)   reason→act→observe loop → ancestor of every Loop
2023-03 Reflexion (NeurIPS 2023)              verbal self-reflection → prototype of stop-hooks/self-evaluation
2023-05 Voyager                               lifelong learning via a skill library → Skill systems (Ch9)
2024-02 CodeAct (ICML 2024)                   code as the action space → code_interpreter/bash as core tools
2024-05 SWE-agent (arXiv:2405.15793)          Agent-Computer Interface design space → tool ergonomics
> **Reading note | What is Voyager's "lifelong learning via a skill library"?** (see Ch9/Ch14 axis 3)
>
> Voyager (arXiv:2305.16291) demonstrated learning without training weights, inside Minecraft:
> every time it masters something, it writes the solution as reusable code with a description
> into a **skill library**; next time it retrieves and reuses first, explores only if nothing
> matches, and deposits new skills back into the library once learned.
> — "Learning" accumulates externally in the form of code (ReAct answers "how to act within a
>   single episode," Reflexion answers "how to fix a failure," Voyager answers "how not to
>   relearn next time what was learned this time").
>
> The 2026 productized counterparts: Hermes' `_create_skill()` autonomously creates skills after
> tasks and improves itself (the only complete closed loop); Codex `ToolExposures.DEFERRED` /
> Claude `defer_loading` = on-demand skill loading; the Claude Skill directory / agentskills.io
> standard = a skill-distribution marketplace.
```

### Lineage 3: Tool Calling ("how to connect to the outside world")

```
2023-02 Toolformer (arXiv:2302.04761)         self-supervised API calling → the tool-learning paradigm established
2023-06 OpenAI Function Calling               the first shot at protocol standardization
2023-05 Gorilla (arXiv:2305.15334)            retrieval-based tool selection + hallucination mitigation
2024-11 MCP (Anthropic)                       interoperability standard for the tool ecosystem → natively supported by eight of the nine
2024  BFCL (Berkeley Function Calling Leaderboard)  tool calling becomes benchmarkable
```

### Lineage 4: Memory and Context ("how to remember")

```
2017  Transformer self-attention              the physical limits of context start being discussed
2023-07 Lost in the Middle (arXiv:2307.03172) a long window ≠ good memory
2023-10 MemGPT (arXiv:2310.08560)             the OS paging analogy → the theoretical source of compaction
2023-12 RULER (arXiv:2404.06654→2024)         the real effective length of long context becomes measurable
2024-08 Prompt Caching (Anthropic)            prefix caching changes the cost structure → Ch5 cache-breakpoint design
2025  A-MEM (NeurIPS 2025)                    Zettelkasten-style agency at write time → memory organizes itself
2026  FadeMem/memorywire                      decay-based forgetting / a proposed memory-interop standard
```

**The confluence point**: in 2024–2025, SWE-bench compressed all four lineages into a single exam — a system that can fix GitHub issues must simultaneously solve safe execution (lineage 1), multi-step planning (lineage 2), tool integration (lineage 3), and long-task memory (lineage 4). Agent Infra was thus established as an independent engineering discipline.

## 1.3 Why 2025–2026 Is the Inflection Point

Four driving forces are clearly visible in this book's source-code comparisons:

1. **Academic convergence**: MemGPT → A-MEM → FadeMem → memorywire; ReAct → SWE-agent. Across the nine implementations, Claude's `snip/micro/collapse`, Grok's `two_pass`, and DeepSeek's `compaction-basic + tool-result-pruner` are different engineering answers to the same batch of papers.
2. **Industrial validation**: dedicated Memory Infra teams have appeared; 5 of the 9 have already split Memory/Context into standalone crates/packages (Grok `xai-grok-compaction/xai-grok-memory`, DeepSeek `compaction-*`, Codex `context_manager`, OpenCode's hidden compaction agent, Claude's compact service directory).
3. **Model-side shifts**: long context (200K–1M) and Prompt Caching make "full replay + server cache" (Codex `store:false`) a viable solution, and make "token-budget-driven compaction" a mandatory one.
4. **Ecosystem standardization**: MCP became the de facto standard (natively supported by all except Pi), with Skill/Plugin emerging as the second extension layer.

## 1.4 The Nine Implementations on One Map

Positioned by "**abstraction-layer thickness**" (horizontal axis) and "**engineering completeness**" (vertical axis):

```
Engineering completeness ↑
            │ Claude Code ●      Codex ●
            │ Grok Build ●
            │ DeepSeek ●     OpenCode ●
            │
            │        Pi ●        Qwen-Agent ●
            │   Claw (porting) ●
            └────────────────────────────→ abstraction-layer thickness (pluginization / multi-model / multi-Agent)
              library/framework ←──────────→ product/Harness
```

| Implementation | One-line positioning | Most worth borrowing | Deep-dive chapters |
|----|-----------|-----------|-------------|
| **Claude Code** | The most feature-complete product-grade Harness (TS + Bun) | four-layer compaction, stable cache breakpoints, cross-cutting permissions | Ch3/5/11 |
| **Codex** | The most systematic Rust engineering (Bazel + 30 crates) | the Turn/Step split, OTel, linux-sandbox | Ch3/8/11 |
| **Grok Build** | The reliability benchmark (Actor + Journal + worktree) | self-healing startup, key-prefix redaction, live/cumulative split accounting | Ch7/10/11 |
| **DeepSeek Harness** | Pluginization taken to the extreme (Cordis event bus) | Inbox interruption semantics, waterfall hooks, step-level retries | Ch3/9 |
| **OpenCode** | A model of the modern TS stack (Effect + Drizzle + AI SDK) | fork idMap, unified Truncate truncation, 10+ providers | Ch7/8 |
| **Pi** | A teaching-grade minimal closed loop (TS) | the 200-line runLoop, two-phase transformContext | Ch2/3/5 |
| **Qwen-Agent** | The only pure framework library (Python, Alibaba) | Memory-as-RAG-Agent composition, the fncall_prompts text-protocol FC, TOOL_REGISTRY | Ch4/6/11 (control group) |
| **Claw** | The porting bridge (Python snapshot + Rust runtime) | the parity_audit methodology, the "counterexample library" | counterexamples across chapters |
| **Hermes Agent** | A self-improving learning loop (Python monolith, Nous Research) | pluggable ContextEngine, 7 terminal backends, self-generated skills, trajectory compaction | Ch3/5/6/11 |

> Reading tip: treat **Qwen-Agent as the control group** — it leaves the Session/Trace/permissions layers blank, which happens to throw into relief what each of the five product-form implementations fills in (see the dedicated analyses in 7.3.2/10.3.2/11.3.2).

## 1.5 Five Design Patterns Running Through the Book (Vocabulary Bonds)

The nine implementations differ in details but share the same patterns. The following five design patterns recur throughout the later chapters and are named once here — **when later chapters claim instances, they always use the same names given here**, coining no new terms.

| Pattern | One-line definition | Source-code anchor |
|------|-----------|-------------|
| **append-only** | The Session only appends events and never rewrites history; crash recovery works by replay, not repair | Claude `src/QueryEngine.ts:184`: `submitMessage()` pre-writes the user message to the transcript before calling the model |
| **projection-over-mutation** | The Context sent to the model is a read-only projection of the Session's full history; compaction changes the view, never the ledger | Codex `codex-rs/core/src/context_manager/history.rs:206 for_prompt()` |
| **boundary set + retention set** | The context budget must carve out an untouchable "retention set" that triggers compaction before the boundary is crossed | Claude `src/services/compact/autoCompact.ts:62`: `AUTOCOMPACT_BUFFER_TOKENS=13_000`, reserving a buffer before the window runs out |
| **failure boundary** | Failures at each layer must be normalized at that layer, so upper layers never see the raw exception shapes of lower ones | DeepSeek `packages/llm/llm/src/adapter-failure.ts`: `normalizeLlmFailure()` unifies errors from all API backends into a single failure shape |
| **minimal Harness tax** | The overhead a Harness adds (abstraction layers, hooks, observability) should be spared wherever possible; the test is "if you delete it, does the minimal loop still run?" | Pi `packages/agent/src/agent-loop.ts:155 runLoop`: roughly 200 lines run the entire loop — the tax is nearly zero |

## 1.6 How to Read This Book: The Five-Part Structure

Chapters 3–11 each follow a fixed five-part structure: **① historical context and paper lineage → ② deep dive into principles → ③ evidence-based decomposition (source-code anchors) → ④ conclusions and trade-offs → ⑤ future directions**, accompanied by Labs and discussion questions. We recommend first building your coordinate system from this chapter's timeline, then entering the individual chapters along the four-phase route in Ch12 — each part can answer the question "which idea from which paper did this line of code land from?"

## 1.7 Summary

Returning to the opening formula **Agent = Model + Harness**: this chapter built the coordinate system for the Harness side — the layer diagram in §1.1 clarified the Harness's position sandwiched between applications and models, §1.2/§1.3 gave its origins and the inflection point, §1.4 positioned the nine implementations by their six-piece-set trade-offs, and §1.5 established the five design patterns that run through the book. Starting from Chapter 2, the six pieces on the right-hand side of the formula will be taken apart one by one.

> The next chapter formalizes the common knowledge that "no implementation can avoid" into the six-piece-set model, and gives a short evolutionary history of each piece.

Figures are currently annotated in Chinese.
