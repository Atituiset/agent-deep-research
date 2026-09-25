# Preface

> **On naming**: *Agent Deep Research* is the title of this project; *Agent Infra* is the field it studies. Throughout the book we call that layer the **Harness** — the run-and-govern layer inside the agent but outside the model. Treat the two as synonyms.

> This is a **hands-on, verifiable Agent knowledge map** — built from 9 real codebases as its textbook (the theory volume T1–T7 has been merged in as Volume VI). Every component is traced from its paper lineage, to line-level source verification, to your own Lab.
>
> **If you have only ever *used* Agents**: start directly with [Chapter 0](/ch00-user-phenomena) (zh) — it translates every usage phenomenon you've already seen (compaction popups, permission prompts, /resume, truncation markers...) into the concepts used throughout the book. You've met every mechanism already; you just don't know its name yet.

## Why this book

Agent resources on the market sit at two extremes: either "theory so abstract it floats" (papers with no engineering) or "tutorials so thin they evaporate" (API calls with no design trade-offs). This book takes a third path:

- Every chapter follows a five-part structure: **① historical context and paper lineage → ② principle deep-dive (formalisms / algorithms / counterexamples) → ③ source verification across the nine codebases (line-level anchors) → ④ conclusions and trade-offs → ⑤ future directions**
- Every Lab ships with a skeleton, acceptance criteria, and common pitfalls — verifiable via `git diff`
- Qwen-Agent serves as the "library-form control group", drawing the boundary between framework and product responsibilities

## Research subjects: nine products, one book

| Codename | Repository | Language / Form | Positioning |
|------|------|-----------|------|
| **Claude Code** | `claude-code-haha` (`src/query.ts:219`) | TS+Bun, product-grade | Leaked Anthropic internal implementation; most feature-complete |
| **Claw** | `claw-code-main` (`rust/crates/runtime/src/conversation.rs:91`) | Python mirror + Rust | Community port; the "counterexample library" |
| **Codex** | `codex` (`codex-rs/core/src/session/turn.rs:153`) | Rust+Bazel, product-grade | OpenAI official; most systematic |
| **OpenCode** | `opencode` (`packages/opencode/src/session/session.ts:224 Info Schema`) | TS+Effect+Bun | Open-source product from the SST team |
| **Pi** | `pi` (`packages/agent/src/agent-loop.ts:155 runLoop`) | TS library + TUI | Teaching-grade minimal Loop |
| **DeepSeek Harness** | `deepseek-harness` (`packages/core/agent-loop/src/agent.ts:70`) | TS + Cordis plugins | DeepSeek's Harness |
| **Grok Build** | `grok-build` (`crates/codegen/xai-chat-state/src/actor/state.rs`) | Rust Actor | xAI implementation; reliability benchmark |
| **Qwen-Agent** | `Qwen-Agent` (`qwen_agent/agent.py:31`) | Python pure framework library | Alibaba Tongyi; **library-form control group** |
| **Hermes Agent** | `hermes-agent` (`agent/conversation_loop.py:1766`) | Python monolith + gateway | Nous Research; self-improving learning Loop |
| **Infra research** | Merged into this book as **Volume VI** (`docs/theory/`, T1–T7 + appendices TA–TE) | Theory foundation (paper survey) |

> All anchors are real and jumpable; see [Appendix B](/appendix-sources) (zh).

## Relationship to the theory volume (formerly agent-infra-research)

That material answers "**why** these components are needed" (papers and ecosystem around Memory/Context/Runtime); it was fully merged into this book as **Volume VI** (T1–T7 + appendices TA–TE) in 2026-08. The main text (Ch1–14) answers "**how each product does it, where the trade-offs are, and how I should implement it myself**." Overlapping topics keep both perspectives: the theory volume supplies the conceptual tools, the source volume delivers the engineering verdicts. For the cross-reference table, see [Appendix C](/appendix-bridge) (zh).

## How to use this book

| Mode | Path | Time | Outcome |
|------|------|------|------|
| **User on-ramp** (only ever used Agents? enter here) | Ch0 phenomenon translator → Ch2 the six pieces → Ch12 Stage A hands-on | 1 day | Every concept finds its slot |
| **Build the map** | Ch1 full-history timeline → Ch2 the six pieces → Ch12 roadmap overview | 3 hours | A knowledge coordinate system + learning plan |
| **Synthesize the ideas** | After finishing all component chapters → Ch14 nine-product philosophy | 1 hour | Judgment across the three schools + a build-vs-buy decision tree |
| **Deep-read one chapter** | Pick any of Ch3–Ch11, walk the five parts against the anchors | half a day per chapter | Able to retell "the normal path + boundaries + failures" |
| **Systematic hands-on** | Complete all Labs across Ch12's four stages | 12–14 weeks | mini-agent + technical judgment |
| **Quick review** | Read only the [Ch13 one-pager](./ch09-one-pager.md) | 30 minutes | Key points + self-check questions |

## Notation

- `file_path:line_number`: source-code anchor
- `> Common pattern` / `> Counterexample` / `> Thought question`: distillations and self-checks
- `Lab N`: hands-on exercise (skeleton → steps → acceptance → pitfalls)
- Trade-off tables are labeled with "applicable scenarios" rather than good/bad

## Credibility and limitations

- Snapshot: 2026-08-22; Claude Code is the leaked version (`999.0.0-local`), and the official release may have evolved
- The Rust monorepos are enormous; only the Agent core paths are covered — the TUI/Cloud layers are not expanded
- Every "commonality" is backed by cross-repo evidence; every "difference" comes with trade-offs and scenarios
