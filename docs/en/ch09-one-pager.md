# Chapter 13 The One-Pager

> The entire book compressed into a single sheet, plus a 5-minute talk framework and a table of answers to the most common follow-up questions. When you need a quick refresher, read only this chapter; the rest of the time, use it as a bookmark.
>
> The governing formula is still **Agent = Model + Harness** — this sheet compresses every cross-implementation finding about the Harness-side six-piece set ([Ch2](./ch02-common-model.md)) across the nine codebases.

## 13.1 The One-Pager (Printable)

```
Agent Infra One-Pager (nine-codebase comparison, 2026-08)

[Positioning] Agent Infra = the operating system on top of the LLM:
        the six-piece set Prompt+Loop+Tools+Context+Session+Model
[History]   ReAct(2022)→Reflexion/Voyager(2023)→SWE-agent/CodeAct(2024);
        Toolformer→function calling(2023-06)→MCP(2024-11);
        MemGPT(2023)→A-MEM(2025 NeurIPS, agentic write)→FadeMem(2026, decay);
        CAMEL/MetaGPT/AutoGen(2023)→LangGraph(2024)→multi-Agent reckoning(2024-25)

[Loop: three layers] turn loop → sampling retry loop → stream consume loop
  Form spectrum: while (Claude/Pi) vs FSM (DeepSeek Phase{idle|maintenance|running})
            vs Actor (Grok ChatStateActor)
            vs library-form counter (Qwen-Agent MAX_LLM_CALL_PER_RUN=20)
  Interrupt semantics: Inbox.splice(next-turn|next-step) is the most precise;
            steer callback is the simplest

[Tools: four watersheds] same-source (spec+handle welded together to prevent
        schema drift) / visibility tiers (ToolExposure Direct→Hidden)
  Cross-cutting permissions (deny>ask>allow, decided once, only in the orchestrator)
        / sandbox (bwrap<gVisor<worktree file isolation)
  Parallelism: serial by default; parallel only when isConcurrencySafe;
        preflight is always serial

[Context: four lines of defense] estimation (chars/4; Qwen-Agent using real tiktoken
        is the exception) → budget (window-buffer or 85%)
  compression (snip coarse delete → micro fine delete → collapse → summarize;
        order is not interchangeable) → cache (stable cache_control breakpoints:
        tool ordering / localeCompare / contentHash; disabling the prefix in
        experiments = 98% miss)

[Session: three bottom lines] append as the only write path + never lose the
        turn/start boundary (pre-write Claude / version Codex / offset Grok)
  startup self-healing (repair_dangling_tool_calls). Library forms
        (Qwen-Agent/Pi core) may leave blanks for the host — a layering choice,
        not a defect

[Model: three stages] single-SDK direct connect → AI SDK unification (10+ providers)
        → adapter stripping (adapterDefaults stripping + context_details rewriting
        total to live). live drives compaction, cumulative drives billing;
        never mix the two

[Security: four quadrants] large side effects → sandbox + approval;
        suspicious input (web) → read-only is dangerous too!
        Injection = data becoming instructions (arXiv:2302.12173)
  Normalize failures first, then handle them (Network retry-exp /
        RateLimit retry-after / PTL withhold / 401 truncated to 12 chars)
  Key redaction SENT_BEARER_PREFIX_LEN=12 across the whole pipeline

[Multi-Agent: two principles] planning is an explicit state container
        (plan persisted as a file, diffable and rollback-able)
  sub-Agent is an isolated execution unit (worktree/Actor/Cordis Scope);
        forbid nested teammates to prevent recursive storms
  Decision boundary: parallel gathering / loose coupling → O-W ~90% speedup
        but token ~15× (Anthropic 2025-06); tightly coupled edits / irreversible
        actions → single thread with shared context (Cognition, same month)

[Evaluation: two layers] outcome metrics (SWE-bench pass@k) set the bar +
        process metrics (trace step analysis / PRM) locate the bottleneck
```

## 13.2 The Nine in One Sentence Each (for "Which Ones Did You Study?")

| Implementation | Keywords |
|----|--------|
| Claude Code | Four-layer compression defense, stable cache breakpoints, cross-cutting permissions — king of production-grade detail |
| Codex | Turn/Step split, rebuilding ToolRouter every step, native OTel — king of systematic design |
| Grok Build | Lock-free Actor, startup self-healing, 12-character key prefix — king of reliability |
| DeepSeek | Cordis waterfall plugin interception, Inbox next-turn/next-step — king of extensibility |
| OpenCode | Effect+Drizzle, fork idMap remapping — model example of the modern TS stack |
| Pi | 200-line runLoop, transformContext projection — teaching-grade starting point |
| Qwen-Agent | Memory=RAG Agent, fncall_prompts text-protocol function calling, library form missing three of the six pieces — the control group |
| Claw | parity_audit porting methodology — cautionary tale and translation bridge |
| Hermes | Pluggable ContextEngine + self-generated skill learning loop + 7 terminal backends — representative of the self-evolving route |

## 13.3 The 5-Minute Talk Framework (Overview → Breakdown → Evidence → Choice)

**① Overview**: "Agent Infra is the operating system on top of the LLM. I did a close reading of nine implementations — five production-grade Harnesses (Claude/Codex/Grok/DeepSeek/OpenCode), two teaching and framework forms (Pi/Qwen-Agent), one porting control (Claw), and one representative of the self-evolving route (Hermes). Strip them open and they are all the same six pieces: Prompt+Loop+Tools+Context+Session+Model, each with a clear evolution line from its paper origins to engineering depth."

**② Breakdown**: "The watersheds are in four places. On Loop, while is easy to read but hard to interrupt — production systems choose FSM or Actor. On Tools, visibility tiers matter more than tool count, and permissions must be cross-cutting. On Context, chars/4 estimation is the consensus (Qwen-Agent using real tiktoken is the sole exception), and compression must be layered. On Session, replayability beats recoverability, and the turn/start boundary must have an anchor."

**③ Evidence**: "Three details impressed me most: Codex rebuilds the ToolRouter for every StepContext, eliminating dangling tool calls; Grok runs repair_dangling_tool_calls at startup to heal poisoned history; DeepSeek's Inbox splits interrupts into next-turn and next-step levels with a wakeRequested latch."

**④ Choice**: "For selection: start learning from Pi/Qwen-Agent (two languages, two forms). For production, combine Codex's context split + DeepSeek's Inbox + Grok's self-healing and redaction. On the TS stack, reuse OpenCode directly; when you need a RAG-style assistant fast, Qwen-Agent's Memory-as-Agent composition is the quickest path."

## 13.4 Frequent Follow-Ups × 30-Second Answers

| Follow-up | Answer points | Anchor |
|------|---------|------|
| Why not tiktoken? | chars/4 is dependency-free and sufficient for budget control (leave buffer below the threshold); the Qwen-Agent counterexample proves even big vendors split into two camps | `claude-code-haha/src/utils/tokens.ts` vs `Qwen-Agent/qwen_agent/utils/tokenization_qwen.py` |
| How do you keep cache hit rates up? | Sort tools with localeCompare + freeze the prompt + contentHash instead of random UUIDs; disabling prefix caching measured 98% miss | `claude-code-haha/src/services/api/claude.ts:361` |
| When can tools run in parallel? | Parallel only when isReadOnly && isConcurrencySafe; preflight stays serial; Pi requires terminate set on every tool | `claude-code-haha/src/Tool.ts:362` |
| How do you make resume trustworthy? | Write the user message before calling the model + boundary anchors (pre-write/version/offset) + startup self-healing | `QueryEngine.ts:451` / `history.rs:93` / Grok journal |
| When do you go multi-Agent? | Decision boundary: ≤10 steps → single Agent; parallel gathering → Orchestrator-Worker (Anthropic measured ~90% speedup, token ~15×); tightly coupled edits → single thread; multiple roles → Swarm, but worktree + no nesting are mandatory | `AgentTool/builtInAgents.ts` / [Ch9 §9.1.2](../ch08-multi-agent.md#_9-1-2-逐篇精读-多-agent-的五次形态变化与一次实证清算) (zh) |
| How do you defend against prompt injection? | Accept that it is probabilistic: evaluate permissions along the call chain, truncate and trace results, tiered approval memory, worst-case blast radius ≤ the boundary of a single authorization | [Ch11 Threat-Model Quadrants](../ch10-reliability.md#_11-2-1-威胁模型四象限) (zh) |
| How do you evaluate your Agent? | Two layers: outcome (SWE-bench-style scoring in CI) + process (trace step analysis); control the three classes of bias in LLM-as-Judge | `codex-rs/e2e/benchmark` |

## 13.5 Pocket Card

```
┌──────────────────────────────────────────────────────────────┐
│ Loop:    three nested layers; while/FSM/Actor/counter forms  │
│ Tools:   same-source+visibility+cross-cutting permissions+   │
│          sandbox; even read-only goes through the gate       │
│ Context: chars/4→window-buffer→4-layer compression→          │
│          projection→cache breakpoints                        │
│ Session: append-only+boundary anchors+startup self-healing+  │
│          live/cumulative                                     │
│ Model:   single SDK→AI SDK→adapter stripping; 401 cut to 12  │
│ Security: injection is probabilistic; deny must write back;  │
│          ask has tiered memory                               │
│ Multi:   plan=file; sub-Agent=isolated unit; no nesting      │
│ Eval:    outcomes set the bar + processes find bottlenecks,  │
│          wired into CI                                       │
└──────────────────────────────────────────────────────────────┘
```
