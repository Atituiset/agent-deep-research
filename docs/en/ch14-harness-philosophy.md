# Chapter 14 The Harness Philosophy: The Design Doctrines of the Nine

`Agent = Model + Harness`: Chapter 2 broke the Harness down into the six-piece set (Prompt / Loop / Tools / Context / Session / Model), and Chapters 3–11 verified "how each component is built" piece by piece. This chapter pulls the camera back to answer two higher-level questions — **why did the same six components grow into completely different shapes across the nine vendors? And how have these disagreements been debated in the industry's papers and blogs?** This is where the book's ideas converge.

**Chapter goals**: after reading, you should be able to (1) trace any Harness idea along the three-layer evidence chain of "paper → blog → source code"; (2) explain every morphological difference among the nine using five philosophical axes, and state the pricing logic behind each difference; (3) recap four public confrontations (complexity / multi-agent / the context manifestos / model-vendor absorption) and where the nine actually stood; (4) recite the five vocabulary bonds — append-only (只增不改), projection-over-mutation (投影而非改写), boundary set + retention set (边界集与保留集), failure boundary (故障边界), and minimal Harness tax (最小 Harness 税) — and point to their redemption anchors and failure boundaries in any one vendor's source tree.

**How to read**: 14.1–14.2 are the map (the evidence chain and the positioning matrix); 14.3–14.8 are the fault lines (the five axes and four confrontations); 14.9–14.10 are verdicts and action (predictions and a decision tree); 14.11 is the common denominator (the five vocabulary bonds) — you may pick sides on the disagreements, but the bonds must be honored. Sources for all file:line anchors are listed in [Appendix B](../appendix-sources.md) (zh).

## Chapter Map

```
Three schools         Metaphor          Representatives      One-line manifesto
─────────            ─────             ─────                ─────────
Systems school        OS/process        Claude·Codex·Grok    "An Agent is a machine that needs a kernel"
Framework school      library/composition Pi·Qwen-Agent      "An Agent is a set of composable functions"
Evolution school      organism          Hermes               "An Agent is an organism that grows itself"
(branch) Bus school   event bus         DeepSeek             "Every capability is a plugin"
        Engineering   modern-stack      OpenCode             "Do the right thing, properly"
        school        exemplar
        Mirror school port reference    Claw                 "Translation is audit"

Three-layer evidence chain   paper (origin of the idea) → tech blog (engineering translation) → source code (the final verdict)
Vocabulary bonds ×5          append-only · projection-over-mutation · boundary set + retention set · failure boundary · minimal Harness tax (redeemed one by one in 14.11)
```

## 14.1 The Evidence Chain: Paper → Tech Blog → Source Code

Every Harness idea can be traced back along a three-layer evidence chain. This table is the map of the chapter — and the methodology of the whole book:

| Idea | Paper layer (origin of the idea) | Blog layer (engineering translation) | Source layer (verified in this book) |
|------|--------------------------------|--------------------------------------|--------------------------------------|
| Looping agents | ReAct (arXiv:2210.03629); Reflexion (NeurIPS 2023) | Anthropic's *Building Effective Agents* (2024-12): distinguishes **workflow** (predefined paths) from **agent** (the model steers dynamically) | the nine main loops (Ch3) |
| Interface design first | SWE-agent (NeurIPS 2024): the ACI design space determines success rate | Anthropic's *Writing effective tools for agents*: write tool documentation for the model, not for humans | ToolExposures / defer_loading (Ch4) |
| Minimal complexity | Sutton's *The Bitter Lesson* (2019); Agentless (arXiv:2407.01489) | OpenAI's *A Practical Guide to Building Agents* (2025): single agent + breakpoints first, multi-agent only later | the minimal forms of Pi / Qwen-Agent |
| Memory and context | MemGPT (2310.08560); A-MEM (NeurIPS 2025) | Manus's *Context Engineering* (2025-07); Anthropic's *Effective Context Engineering* (2025) | four-layer compaction / ContextEngine ABC (Ch5/6) |
| Orchestration and delegation | CAMEL / MetaGPT / AutoGen (2023) | Anthropic's *How We Built Our Multi-Agent Research System* (2025-06); Cognition's *Don't Build Multi-Agents* (2025-06) — a **head-on clash** | AgentTool / Collaboration-mode (Ch9) |
| Reasoning and tool internalization | DeepSeek-R1 (arXiv:2501.12948): RL internalizes long-chain reasoning | OpenAI's *New Tools for Building Agents* (2025-03): the Responses API hosts tools | hosted tools / fncall_prompts (Ch8) |

> A note on methodology: papers tell you "what is possible", blogs tell you "what it costs", and source code tells you "the final trade-off". Read only papers and you overestimate complexity (the Agentless lesson); read only blogs and you underestimate depth (behind KV-cache lies the PagedAttention lineage); read only source and you know the *how* but not the *why*.

## 14.2 Five Philosophical Axes: The Positioning Matrix of the Nine

Every difference in the same set of components can be explained along five axes:

| Vendor | Axis 1: control | Axis 2: engineering org | Axis 3: capability view | Axis 4: constraint view | Axis 5: extension view |
|--------|----------------|------------------------|------------------------|------------------------|-----------------------|
| Claude Code | product fully managed | TS monorepo, single app | static set + defer_loading | paternalistic (tighten by default) | MCP first-mover + Skill catalog |
| Codex | product fully managed | Rust, 30+ crates (Bazel) | static + server-side hosted | tiered approval_policy | MCP + namespaces |
| Grok Build | product fully managed | Rust, 50+ crates (Actor boundaries) | static + ToolKind reverse lookup | secret redaction throughout | plugin_registry |
| DeepSeek | product fully managed | TS, 60+ packages (Cordis) | preset assembly | waterfall pre-interception | everything is a plugin |
| OpenCode | product fully managed | Bun monorepo (Effect) | six built-in agent types + skill packages | Ruleset merging | MCP + plugin packages |
| Pi | library hands control to the host | pnpm, 5 packages, minimal | callbacks inject everything | beforeToolCall hook | extension packages |
| Qwen-Agent | library hands control to the host | single-repo Python package | TOOL_REGISTRY registration | trusts the host (no sandbox, no permissions) | mcpServers plug-and-play |
| Claw | mirrors upstream | Python + Rust dual track | replicates upstream | inline authorize | none |
| Hermes | product fully managed (gateway) | Python monolith (9207 lines) | **self-generated skills** | approval-as-tool + environment-style | agentskills.io |

## 14.3 Axis 1 — Control: Workflow or Agent?

Anthropic's *Building Effective Agents* drew the widely cited line: **a workflow is a developer-pre-orchestrated chain of LLM calls (the five patterns: prompt chaining / routing / parallelization / orchestrator-workers / evaluator-optimizer), while an agent is a loop in which the model itself decides the path and the tool budget**. That line happens to cut the nine cleanly in two:

- **The library camp sells workflow primitives**: Qwen-Agent's router / group_chat, Pi's `getSteeringMessages` callback — control flow is handed back to the host;
- **The product camp sells the agent itself**: the main loops of all five products are "the model steers + the Harness enforces" — users supply a goal, never a flowchart;
- **The middle position in OpenAI's guide** (*A Practical Guide*): build a single agent with human breakpoints (human-in-the-loop) first, and upgrade to multi-agent only when proven necessary — which explains why all nine cap orchestration granularity at Orchestrator-Worker, and why Swarm remains scarce to this day.

> Axiom upgrade: "blank space is pricing" (the earlier conclusion of 14.2) should be sharpened to: **the library camp prices workflow freedom; the product camp prices agent reliability**. Under Anthropic's own definition, these are two different commodities entirely.

## 14.4 Axis 2 — Engineering Organization: Monolith vs Microkernel

```
Monolith camp     Hermes run_agent.py, 9207 lines — research iteration speed first
Microkernel camp  Codex (Bazel + 30 crates) · Grok (50+ crates) · DeepSeek (Cordis 60 packages) — team collaboration first
Layered middle    OpenCode (Effect Layer enforced injection) · Claude (TS monorepo directory conventions)
Minimalist camp   Pi (agent package < 3000 lines) — teaching first
```

Empirical observation: engineering organization correlates with team size, not with the quality of ideas. The 17-chapter mdBook shipped inside the Codex repo (`book/src/ch01-overview…ch17-engineering`) proves the microkernel camp must "trade documentation for cognition"; the Hermes monolith maintains discipline through `AGENTS.md` and its test directories instead. The lesson: **boundaries follow the organization — don't abstract ahead of need**.

## 14.5 Axis 3 — Capability: Static, Dynamic, Self-Evolving, and "Model-Side Absorption"

```
Static capability view    the tool set is fixed at release; runtime only grades visibility (the majority)
Dynamic composition view  preset/plugin assembly at startup (DeepSeek composition / OpenCode skill packages)
Self-evolution view       new capabilities generated and persisted at runtime (Hermes _create_skill = the only complete Voyager landing)
Model-side absorption     ← the fourth force after 2025
```

**Model-side absorption** is the newest variable on Axis 3, with three pieces of evidence:

1. The OpenAI Responses API turned `web_search / file_search / computer_use` into **server-side hosted tools** (2025-03): tool execution happens inside the model vendor's infrastructure and the Harness only receives results — Grok's `context_details` rewriting `total_tokens` in Ch8 exists precisely to digest this server-side loop;
2. Meta published its official system prompt directly in the open-source llama-models repo, and Llama 3.1 adopted a **pythonic tool-call format** (`[tool_call(...)]`) instead of JSON — proof that the "calling protocol" has been welded into the weights, and the Harness must adapt to the model's native dialect (Qwen-Agent's `fncall_prompts` text-protocol FC is the same story: backward compatibility for models without native FC);
3. DeepSeek-R1 used RL to internalize long-chain reasoning into `<think>`, demoting tool calls to a secondary role — hinting that "a reasoning model + a minimal tool set" may beat "an ordinary model + a heavy Harness".

> Implication for builders: **the Harness moat is precisely the four things models cannot do — hold state, hold execution authority, manage the environment, and attribute cost** (corresponding to Session / Tools / sandbox / Trace). Tools themselves are becoming a commodity of the model vendors.

## 14.6 Axis 4 — Constraints: Three Safety Postures and Layered Guardrails

Beyond paternalistic (Claude / Codex / Grok), laissez-faire (Qwen-Agent / Pi), and environment-style (Hermes's seven terminal backends), OpenAI's guide adds an engineering middleware idea: **layered guardrails** — input classifiers → tool-level approval → output filtering → human breakpoints, each layer independently testable. This can be stacked on top of Claude's cross-cutting permission lattice (deny > ask > allow) rather than being an either/or choice. See the four quadrants of the threat model in Ch11.

## 14.7 Axis 5 — Extension: Protocol, Bus, and Marketplace

The three routes — MCP (tool interoperability), the Cordis waterfall (aspect interception), and agentskills.io / Skill catalogs (skill distribution) — are covered in their respective chapters; the idea-level judgment is: **the protocol route wins on interoperability, the bus route wins on expressiveness, and the marketplace route wins on distribution**. The de facto convergence of 2026 is "MCP as the foundation + Skills for distribution", with the bus camp retreating to intra-enterprise scenarios.

## 14.8 Four Ideological Confrontations (Open Debates at the Blog Layer)

Every core controversy in Harness design has had a public confrontation. Here is each one, replayed, with its verdict as the field evolved:

### Clash A: Should You Build a Complex Harness? — The Bitter Lesson vs ACI Design

- **The "no" side**: Sutton's *Bitter Lesson* — general methods plus compute ultimately beat human priors; Agentless (2024-07) matched or beat complex agent frameworks of its day with a three-stage, agent-free "locate → fix → verify" pipeline, at a fraction of the cost.
- **The "yes" side**: SWE-agent (NeurIPS 2024) proved that **interface quality itself** (ACI) is an independent variable — the same model scores significantly higher with well-designed tool interfaces.
- **Verdict (looking back from 2026)**: both are right, but on different time scales. Stronger models depreciate "yesterday's complex Harness" (Agentless is right); yet "today's optimal interface" always needs design (SWE-agent is right). The evolution history of the nine is a continuous process of tearing down obsolete scaffolding and erecting new scaffolding — for example, Claude replaced its early large-manifest injection with `ToolSearch defer_loading` (an instance of honoring the minimal Harness tax bond, see 14.11.5).

### Clash B: Should You Build Multi-Agent at All? — Anthropic vs Cognition

The most famous public opposition of 2025:

- **Anthropic**, *How We Built Our Multi-Agent Research System* (2025-06): Orchestrator-Worker sped up research-type tasks **by roughly 90%**; but they candidly admitted the cost — a multi-agent system burns about **~15×** the tokens of a single chat, a single agent about **4×**; the practical lessons were "teach the orchestrator how to delegate, and tell subagents how to allocate effort".
- **Cognition**, *Don't Build Multi-Agents* (same period): two principles — ① **share the full context**; ② **actions carry implicit decisions, and conflicting implicit decisions inevitably produce bad results** — arguing that current models cannot do true multi-agent well, and recommending a single-threaded linear agent plus context compaction (exactly Devin's route).
- **Where the nine actually stood**: all implemented Orchestrator-Worker (Ch9); none productionized the "free Swarm" that Cognition argued against; Claude even absorbed both sides at once — `LocalAgentTask` backgrounding (Anthropic camp) plus subagents inheriting a summary of the parent's context instead of starting blank (a concession to Cognition's principle).
- **Verdict**: the disagreement is really **a fight over task topology** — parallelizable research tasks favor Anthropic's route, tightly coupled editing/coding tasks favor Cognition's. The nine took both ends at once with "subagent isolation + main-thread summarization".

### Clash C: The Three Context-Engineering Manifestos — Manus, Anthropic, Cognition

Three blog posts form the canon of the 2025 "Context Engineering" movement. Their views converge on three points; the disagreement is over means:

| Principle | Manus (2025-07) | Anthropic (2025) | Cognition (2025-06) |
|-----------|----------------|------------------|---------------------|
| Never rewrite history | **append-only** (never modify past actions; only append undos) | compaction preserves the segments before and after the boundary | single-threaded sequential progress |
| Externalize memory | **the filesystem is the ultimate context** (large outputs go to disk; references stay off the stack) | **structured notes** (NOTES.md / memory tools) | compressed summaries |
| Keep goals fresh | **todo.md recitation** (rewrite the goal at the tail of context every turn to fight lost-in-middle) | just-in-time retrieval (JIT context) replaces preloading | — |
| Unique contribution | KV-cache hit rate is the number-one metric (cached input is roughly an order of magnitude cheaper); **keep errors** as decision anchors; mask tools instead of removing them (logits masking prevents state-machine violations) | the attention-budget metaphor; engineering the compaction trigger threshold | action = implicit decision (the irreversibility argument) |

**How the nine map onto them**: Manus's todo.md ↔ each vendor's TodoWrite / plan-to-disk (Ch9); append-only ↔ the Session append-only iron law (Ch7 I1), i.e. the append-only bond (14.11.1); keeping errors ↔ Grok's repair, which backfills an error-result rather than deleting it (Ch11) — the corrective form of append-only under failure; masking tools ↔ Codex's ToolExposures=NONE (not registered, but schema validation retained, Ch4), i.e. the boundary set + retention set bond (14.11.3); KV-cache first ↔ Claude's cache-break detection events (Ch5.6). **All three manifestos have counterparts in all nine** — the hardest evidence that this is genuinely "common knowledge".

### Clash D: Will Model Vendors Swallow the Harness? — Redrawing the Moat

DeepSeek-R1 internalized reasoning, OpenAI hosts tools, and Meta welded the protocol into the weights (see 14.5). On the surface the Harness is being hollowed out; the actual redrawn map is:

```
What model vendors can absorb:   tool execution, part of reasoning, the calling protocol
What they cannot absorb:         cross-vendor state (Session), enterprise permissions (approval/audit),
                                 execution environment (sandbox/backends), cost attribution (billing),
                                 the evaluation loop
```

This is exactly the valuation logic of the five product-camp vendors among the nine, and it also explains why OpenAI itself shipped the Codex CLI — **a model vendor entering the Harness business is itself proof that this layer cannot be omitted**.

## 14.9 Convergence Predictions (Revised)

Based on the verdicts above:

1. **The product camp absorbs the evolution camp**: self-generated skills will become standard, with the precondition of "skill signatures + sandboxed dry runs" (Hermes has already validated the demand; safety mechanisms must come first);
2. **Protocols revive the library camp**: once a session-export standard (of the sessionwire kind) takes shape, Qwen-Agent / Pi can close their Session gap with import/export;
3. **Cognition's principles become the default constraint on multi-agent**: shared context turns from a virtue into an architectural requirement — subagents carry a projection of the parent context by default (Grok's `PromptContext.audience` is already an embryonic form), i.e. the extension of the projection-over-mutation bond (14.11.2) into multi-agent scenarios;
4. **The main battlefield of Harness competition shifts**: from "feature completeness" to "context economics" (KV-cache hit rate, attention-budget allocation) — a victory for the Manus manifesto.

## 14.10 A School-Selection Tree for Builders

```
Who are your users?
├─ end developers themselves ──► start with the systems school: build on Pi, then add Claude's gates one by one (the Ch12 route)
├─ app developers (you ship an SDK) ──► framework school: the Qwen-Agent form; leave Session/Memory blank but keep the interfaces,
│                                       and implement import/export per the 14.8C checklist, ready for the future
└─ unattended automation ──► evolution school + environment-style: model on Hermes; build tiered approval (14.6) before turning on self-evolution
                             ⚠ the order cannot be reversed: enabling self-evolution before mastering constraints = Excessive Agency made flesh
Universal first step (regardless of school): self-check against the Manus manifesto — append-only? goal recitation? error retention?
                                             stable cache breakpoints? (the Ch5.6 trio can be completed in a single day)
```

## 14.11 The Five Vocabulary Bonds: The Design Floor That All Nine Honor

The five axes and four clashes were about "disagreement"; this section is about the "common denominator". Throughout the book, five phrases recur in the source code of all nine vendors. They are not slogans but **vocabulary bonds** — once a term is issued into public discourse, every later line of implementation pays interest on it: redemption takes the form of file:line anchors, and default costs a concrete incident. Here they are, redeemed one by one.

### 14.11.1 append-only

**Definition**: the fact layer (Session / history / logs) only allows appends; correction happens by appending compensating entries, never by in-place modification; the view layer (compaction, summaries) may be rewritten, the fact layer never. Formalized, this is invariant I1 from Ch2 (`Session.append` is the only write path); at the manifesto layer, it is Manus's append-only.

**Anchors across the nine**:

| Vendor | Redemption anchor | How it is honored |
|--------|-------------------|-------------------|
| Claude Code | `src/QueryEngine.ts:184`, `src/utils/sessionStorage.ts:202` | transcript written before the model call (pre-write); JSONL line append + 100ms debounce (Ch7) |
| Codex | `codex-rs/core/src/context_manager/history.rs:93` | version anchors mark turn boundaries; history only grows |
| Grok Build | `xai-chat-state/src/actor/state.rs:119` | `repair_dangling_tool_calls` backfills a synthetic `tool_result` instead of deleting dangling calls (Ch7); error results are kept as decision anchors (Ch11) |
| DeepSeek | `packages/session/session-persistence-jsonl/` | append + zstd-compressed persistence backend |
| OpenCode | `packages/opencode/src/session/session.ts:669/751` | Effect event-stream create/touch; never modified in place |
| Pi | `packages/agent/src/harness/session/` (jsonl-repo) | JSONL repo append; SQLite is only a swappable backend |
| Qwen-Agent | — (no persistence layer) | the bond is **left blank for the host**: a layering choice of the library form, not an exemption |
| Claw | `rust/crates/runtime/src/session.rs` | `Session{version,messages}` replicates upstream semantics |
| Hermes | `agent/conversation_compression.py:469` | `CompressionCommitFence` keeps compaction writes from racing concurrent appends |

**Failure boundary / counterexamples**: compliance deletion (forgetting requests) is a legitimate exception, but it should append a tombstone event rather than physically deleting rows, or the replay chain breaks; if in-place editing of history were allowed, three layers would fall in a chain — KV-cache prefix breakage (Ch5.6), untrustworthy `--resume` replay (Ch7), and failure-attribution loss (Ch10). Compaction rewriting a view is not a default, provided the boundary is traceable (see 14.11.3).

### 14.11.2 projection-over-mutation

**Definition**: what is fed to the model is always a view, never the fact itself — `Context = project(Session)` (Ch2 I3). Compaction, truncation, modality stripping, and redaction all happen inside the projection function; the Session is preserved as-is.

**Anchors across the nine**:

| Vendor | Redemption anchor | How it is honored |
|--------|-------------------|-------------------|
| Codex | `codex-rs/core/src/context_manager/history.rs:206` | `for_prompt()` projection + `normalize.rs` stripping unsupported modalities |
| Pi | `packages/agent/src/types.ts` `transformContext`, `docs/book/src/12-memory-projection.md` | the origin of the projection terminology; the user injects the projection function, with zero built-in compaction layers |
| Hermes | `agent/context_engine.py:89/146` | projection strategy formalized as a pluggable `ContextEngine(ABC)` — the only one of the nine that is replaceable at runtime |
| Claude Code | `src/services/compact/compact.ts:387` | `compactConversation()` produces a summary view; the transcript is preserved as-is |
| Grok Build | `PromptContext.audience` (Ch9) | an embryonic parent-child context projection (evidence for prediction 3 in 14.9) |
| OpenCode | `packages/opencode/src/tool/truncate.ts`, `session.ts:693` | `Truncate.wrap()` projects on the output side; `fork()`'s idMap remapping is a session-level projection |
| DeepSeek | `packages/llm/llm/src/assembler.ts` | `BlockAssembler` streams the chunk→block projection |
| Qwen-Agent | `qwen_agent/agent.py:78` | `run()` entry `deepcopy` — the most primitive projection in library form: at least the caller's messages are not polluted |
| Claw | `src/query_engine.py:36` | turn-level view assembly mirroring upstream |

**Failure boundary / counterexamples**: the projection function must be deterministic (same input, same bytes), or cache breakpoints drift and traces become irreproducible (a Ch5 acceptance item); a projection that drops critical information (summary hallucination, lost-in-middle) is the biggest failure mode, and the cure is making the retention set explicit (14.11.3), not enlarging the window; the counterexample is mutating with `messages.splice()` directly — easy to write, but you can no longer audit "why was this dropped", and lineage breaks (see the projection-vs-rewrite comparison table in Ch5).

### 14.11.3 boundary set + retention set

**Definition**: any trim / compaction / offload operation must first explicitly declare two sets — the **boundary set** (structural anchors: turn boundaries, tool_call/tool_result pairs, compact boundaries) and the **retention set** (content that must be kept for semantic reasons); only what lies outside both sets may be dropped. It answers "what gets cut, what doesn't, and who decides".

**Anchors across the nine**:

| Vendor | Redemption anchor | How it is honored |
|--------|-------------------|-------------------|
| Claude Code | `compact.ts:350 boundary`, `autoCompact.ts:30` | compact boundary markers + `preservedSegment{head/tail/anchor}` re-linking (Ch7); the 20K summary output budget sizes the retention set |
| Codex | `codex-rs/tools/src/tool_spec.rs:22` | `ToolExposures=NONE` masks instead of removing — the schema goes into the retention set (validation still runs), not into the context (Ch4) |
| Grok Build | `xai-grok-agent/src/compaction.rs:9` | the `CompactionPolicy` 85% threshold draws the compaction boundary |
| OpenCode | `packages/opencode/src/agent/agent.ts:35` | hidden agents' `title/summary`: retained at runtime, invisible on the user surface |
| DeepSeek | Cordis presets (`code/standard/minimal`) | startup-time assembly is itself an explicit declaration of this run's boundary set |
| Pi | `transformContext` example `pruneOldMessages` | the simplest retention set: truncate by turn count, policy owned by the user |
| Qwen-Agent | `qwen_agent/agents/fncall_agent.py:73` | `MAX_LLM_CALL_PER_RUN=20` is a boundary set on the hop dimension |
| Claw | `src/query_engine.py:19` | `compact_after_turns=12` replicates upstream's turn-count boundary |
| Hermes | `StreamingContextScrubber` (:182) | streaming redaction: secrets are an "explicit removal set" — the inverse of the retention set must be declared too |

**Failure boundary / counterexamples**: cut the boundary between a tool_call and its tool_result → dangling calls, for which Grok pays the price of a full startup scan (Ch4/Ch7); leave the retention set to "the summary model's discretion" → summary hallucination, and Anthropic's fix is to keep the raw text before and after the boundary and summarize only the middle (14.8C); the counterexample is naive truncation with no boundary-set concept (drop the first N entries) — cache, pairing, and attribution all lost at once.

### 14.11.4 failure boundary

**Definition**: every failure class must have a single owning layer and an explicit disposition (retry-exp / fail-fast / withhold / escalate); failures must not pierce the boundary and pollute upstream. The theoretical counterparts are the DISPOSITION table of Ch11 and the Circuit Breaker / Bulkhead / Timeout trio from Nygard's *Release It!*.

**Anchors across the nine**:

| Vendor | Redemption anchor | How it is honored |
|--------|-------------------|-------------------|
| Claude Code | `autoCompact.ts:66`, `reactiveCompact.ts` | `MAX_CONSECUTIVE_AUTOCOMPACT_FAILURES=3` circuit breaker; PTL errors are withheld rather than thrown — compact first, then resend (withhold, Ch11) |
| DeepSeek | `packages/llm/llm/src/adapter-failure.ts` | `normalizeLlmFailure()` normalizes each provider's failures before uniform disposition |
| Grok Build | `state.rs` (`ChatState::new()`) | startup self-healing repair/dedup pays once at the session layer; the hot path scans zero times |
| Codex | `codex-rs/core/src/tools/context.rs:56` | cancellation_token threaded throughout; Ctrl-C interrupts a running tool |
| OpenCode | `wrapSSE` | dual header/read timeouts — the Timeout pattern landed |
| Qwen-Agent | `qwen_agent/agent.py:178` | exceptions backfilled as `error_message` (soft self-healing) vs `ToolServiceError` thrown upward — two tiers of disposition |
| Pi | `packages/agent/src/agent-loop.ts:155` | the hop cap of 25 is the simplest failure boundary: error loops cannot sample forever |
| Claw | `src/query_engine.py:36` | dual gates of `max_turns=8` and `max_budget_tokens=2000` |
| Hermes | `tools/terminal_tool.py:1517` | seven terminal backends isolate failures along the environment dimension; one backend crashing does not pollute the session |

**Failure boundary / counterexamples**: the most typical mistake is drawing the boundary at the wrong layer — permission checks written into every tool, rule-layer precedence inverted, no backfill after deny → the model retries the same action in a death loop (common pitfalls from Ch11); unbounded retries without jitter → thundering herd; the counterexample is treating an LLM failure as a tool failure (exponential retries on `prompt_too_long`) — misclassify the failure, and the boundary is decoration.

### 14.11.5 minimal Harness tax

**Definition**: every layer of Harness machinery must pay its way with "the incidents it prevents"; complexity that the model has internalized or a protocol has absorbed should be torn down immediately. This is the Bitter Lesson (Clash A in 14.8) restated in engineering terms at the Harness layer — the tax is not zero, but every penny needs an invoice.

**Anchors across the nine**:

| Vendor | Redemption anchor | How it is honored |
|--------|-------------------|-------------------|
| Pi | `packages/agent/src/agent-loop.ts:155` | a 792-line file carries all loop semantics; the agent package is under 3000 lines — the lowest tax rate of the nine |
| Claude Code | `src/utils/tokens.ts`, `src/tools.ts:346` | `chars/4` zero-dependency estimation — no tokenizer pulled in when "good enough" suffices; defer_loading tore down the large-manifest injection |
| Qwen-Agent | `qwen_agent/utils/tokenization_qwen.py` | a reverse anchor: the only one of the nine to pull in real tiktoken, paying a dependency tax for counting precision |
| DeepSeek | Cordis preset `minimal` | even the plugin set is trimmed per scenario to the smallest runnable form |
| OpenCode | `packages/opencode/src/provider/provider.ts:107` | 21 providers dynamically imported — no startup tax for protocols you don't use |
| Codex | `codex-rs/cli/src/main.rs:115` | MultitoolCli dispatches on demand; a single command doesn't load the full stack |
| Grok Build | `xai-grok-agent/src/builder.rs:42` | all 51 `with_*` defaults off — pay the tax only for the pieces you use |
| Hermes | `run_agent.py` | the negative reference: the 9207-line monolith has the highest tax rate, traded for research iteration speed; upstream had slimmed to 1555 lines by 2026-09 — the tax declines with maturity (drift note in Appendix B) |
| Claw | the whole repo | porting as auditing: parity_audit asks of every line, "where is the invoice for this tax?" |

**Failure boundary / counterexamples**: the boundary of cutting the tax too far = missing pieces of the six-piece set — Qwen-Agent lacks Session and permissions, and used for unattended automation that is Excessive Agency made flesh (the 14.10 warning); "minimal" is relative to task topology: Pi's form suffices for tasks within ~10 steps, but cutting the compaction layer for long-horizon coding is suicide; Agentless proved that "a heavy Harness gets depreciated by model progress", yet it is still a three-stage pipeline itself — "the tax can be zero" has never held; the floor is **the thinnest closed loop with none of the six pieces missing**.

> Read together, the five bonds are the constitution of the right-hand side of `Agent = Model + Harness`: the disagreements in 14.3–14.8 are each vendor's pricing freedom; 14.11 is the boundary of that freedom.

## Summary

After this chapter, you should be able to assert:

1. Every morphological difference among the nine can be located along the five philosophical axes, and each axis can be cross-checked against the three-layer "paper → blog → source" evidence chain — the differences are pricing choices, not questions of right and wrong.
2. The public confrontations of 2025 have converged in the source of the nine: Orchestrator-Worker became the maximum orchestration granularity (Anthropic's ~90% speedup and ~15× tokens, and Cognition's two shared-context principles, were absorbed simultaneously), and the three context-engineering manifestos' append-only / externalization / goal-freshness all have file:line counterparts.
3. Model vendors can absorb tool execution and reasoning; they cannot absorb cross-vendor state, enterprise permissions, the execution environment, or cost attribution — OpenAI personally entering the arena with the Codex CLI is itself proof that the Harness layer cannot be omitted.
4. The five vocabulary bonds — append-only, projection-over-mutation, boundary set + retention set, failure boundary, and minimal Harness tax — each have redemption anchors in the source of the nine; school routes are negotiable, but every bond default corresponds to a concrete incident.
5. Back to the master formula: the right-hand side of `Agent = Model + Harness` is not an appendage of the model, but the last-mile pricing device through which model capability reaches the user — which is exactly why this book dissects nine vendors' source code line by line.

## ★ Discussion Questions

1. Using the three documents Bitter Lesson / Agentless / SWE-agent, argue the true verdict of the complexity debate to a "heavy-framework believer" — on which time scale does your argument hold, and on which does it fail?
2. If Anthropic (~90% speedup, ~15× tokens) and Cognition (share the full context; actions are implicit decisions) are both right, how much of each side do the nine's "subagent isolation + main-thread summarization" capture? Design an experiment around Grok's `PromptContext.audience` to quantify these shares.
3. Pick one of the four convergence points of the three context-engineering manifestos, point to its file:line counterpart in the vendor you know best, and describe the concrete incident shape that vendor would suffer without it.
4. When append-only conflicts with a compliance forgetting request, why does the tombstone scheme satisfy both compliance and replayability? Does it break the `fork()` semantics of Ch7?
5. If the projection function is non-deterministic (two calls of `for_prompt()` on the same Session produce different bytes), which layers does the chain reaction break, in order? List them in the order Ch5 / Ch7 / Ch10, with one anchor each.
6. When adding a Session layer to Qwen-Agent, which bond should be redeemed first — minimal Harness tax or append-only? Why can't the order be reversed?
7. If DeepSeek-R1-style reasoning internalization goes one step further (the model decides compaction timing on its own), which of the five bonds in 14.11 matures first? What remains on the Harness side that cannot be internalized?
8. The 14.10 decision tree warns that "enabling self-evolution before mastering constraints = Excessive Agency" — restate it in the language of the five bonds: which bonds must the Hermes route redeem first, and what are their anchors?

> The components are done, and the ideas have converged. Return to [Ch12](../ch10-roadmap.md) (zh) to pick a route, or flip to [Ch13](./ch09-one-pager.md) to take the one-pager with you.
