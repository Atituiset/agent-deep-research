# Agent Deep Research — How 9 Agent Harnesses Really Work

> **Naming**: *Agent Deep Research* is the project/book title; *Agent Infra* is the field it studies. Inside the book we call that layer the **Harness** — same thing, engineering view. 书名 Agent Deep Research，研究对象 Agent Infra（Agent 基础设施），书中统一以 Harness 指代该层。

[![Read Online](https://img.shields.io/badge/read-GitHub%20Pages-blue)](https://atituiset.github.io/agent-deep-research/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![English Edition](https://img.shields.io/badge/English%20edition-in%20progress-brightgreen)](https://atituiset.github.io/agent-deep-research/en/)
[![GitHub stars](https://img.shields.io/github/stars/Atituiset/agent-deep-research?style=social)](https://github.com/Atituiset/agent-deep-research/stargazers)

**[中文](#中文版说明) · [English](https://atituiset.github.io/agent-deep-research/en/)** · Read online: **[atituiset.github.io/agent-deep-research](https://atituiset.github.io/agent-deep-research/)**

## Elevator Pitch

What actually happens between your prompt and an agent's answer? This book takes apart the source code of 9 real agent harnesses — Claude Code, Codex, OpenCode, Pi, DeepSeek Harness, Grok Build, Claw, Qwen-Agent, and Hermes — and shows that they all converge on one formula: **Agent = Model + Harness**, where the Harness decomposes into six pieces: Prompt, Loop, Tools, Context, Session, and Model. Every claim is anchored to a `file_path:line_number` in the original repositories, so you can verify it yourself. Each chapter follows the same five-part rhythm: paper lineage → principle deep-dive → source-code evidence → trade-off verdict → future directions. You get a one-page printable cheat sheet, a 10-week hands-on learning path, and five reusable design patterns (append-only, projection-over-mutation, boundary set + retention set, failure boundary, minimal Harness tax) distilled from how nine teams solved the same problems differently. Source snapshot: 2026-08-22.

## Chapters at a Glance

| Ch | One-line core | Read online | Lab |
|----|---------------|-------------|-----|
| 0 From Your Own Usage | Translates the usage phenomena you've already seen into the book's concept map | [read](https://atituiset.github.io/agent-deep-research/ch00-user-phenomena) | — |
| 1 Landscape & Positioning | `Agent = Model + Harness`; the 60-year lineage and where the nine harnesses stand ([EN](https://atituiset.github.io/agent-deep-research/en/ch01-landscape)) | [read](https://atituiset.github.io/agent-deep-research/ch01-landscape) | — |
| 2 The Common Model | Formalizes the six pieces — Prompt / Loop / Tools / Context / Session / Model ([EN](https://atituiset.github.io/agent-deep-research/en/ch02-common-model)) | [read](https://atituiset.github.io/agent-deep-research/ch02-common-model) | — |
| 3 Agent Loop | The "sample → act → append" closure, guarded by budget / retry / assembly / interrupt / observability | [read](https://atituiset.github.io/agent-deep-research/ch03-loop) | [labs/](labs/) |
| 4 Tools, Permissions, Sandbox | Visibility grading, approval, sandboxing, parallelism — spec and execution from one source | [read](https://atituiset.github.io/agent-deep-research/ch04-tools) | [labs/](labs/) |
| 5 Context Engineering | Estimate → budget → trigger → compress → cache; Context = project(Session) | [read](https://atituiset.github.io/agent-deep-research/ch05-context) | [labs/](labs/) |
| 6 Memory Deep-Dive | From MemGPT to A-MEM: remembering next turn and staying coherent across sessions | [read](https://atituiset.github.io/agent-deep-research/ch05b-memory) | [labs/](labs/) |
| 7 Session / Trace / Persistence | Append-only WAL as the single write path; Trace as its observable projection | [read](https://atituiset.github.io/agent-deep-research/ch06-session) | [labs/](labs/) |
| 8 Model Abstraction | One clean sampling call over fragmented protocols, auth, and billing | [read](https://atituiset.github.io/agent-deep-research/ch07-model) | [labs/](labs/) |
| 9 Multi-Agent & Planning | Plan as on-disk artifact, sub-agents as isolated execution units, four topologies | [read](https://atituiset.github.io/agent-deep-research/ch08-multi-agent) | [labs/](labs/) |
| 10 Observability & Evals | The trace evidence chain, usage normalization, and cost attribution | [read](https://atituiset.github.io/agent-deep-research/ch09-observability) | [labs/](labs/) |
| 11 Safety & Reliability | Defense in depth: permission lattice → sandbox → failure normalization → layered self-healing | [read](https://atituiset.github.io/agent-deep-research/ch10-reliability) | [labs/](labs/) |
| 12 Learning Path | A 12–14 week paper × source × implementation route; every lab has a skeleton and acceptance bar | [read](https://atituiset.github.io/agent-deep-research/ch10-roadmap) | — |
| 13 The One-Pager | The whole book on one printable A4 + a 5-minute pitch framework + FAQ ([EN](https://atituiset.github.io/agent-deep-research/en/ch09-one-pager)) | [read](https://atituiset.github.io/agent-deep-research/ch09-one-pager) | — |
| 14 Harness Philosophy | Five philosophical axes, four public debates, five "vocabulary bonds" ([EN](https://atituiset.github.io/agent-deep-research/en/ch14-harness-philosophy)) | [read](https://atituiset.github.io/agent-deep-research/ch14-harness-philosophy) | — |

Labs are runnable, deterministic mini-experiments under [`labs/`](labs/) — each one verifies a single claim from the book (stated in its docstring). Run them all with `python3 -m unittest discover -s labs -v`.

## How to Read This Book

1. **Start at Ch0** if you come as a *user* — it maps the phenomena you already know onto the concepts.
2. **Then Ch1–Ch2** for the map: the master formula and the six pieces.
3. **Deep-read the component chapters (Ch3–Ch11)** in whatever order your problem demands; each is self-contained and re-hangs itself on the master formula.
4. **Close with Ch13** — the one-pager compresses everything into a single sheet; use Ch12 if you want the hands-on path, and Ch14 for the design-philosophy wrap-up.

## Companion Resources

- **English edition**: [`docs/en/`](docs/en/), served at [`/en/`](https://atituiset.github.io/agent-deep-research/en/) — currently covers index, preface, Ch1, Ch2, Ch13, Ch14
- **Figures**: [`docs/public/figures/`](docs/public/figures/) — the architecture diagrams used across chapters (SVG)
- **[C-LAYER-PLAN.md](C-LAYER-PLAN.md)**: the content-deepening roadmap (Qwen-Agent / Hermes evidence backfill, etc.)

## Structure

| Volume | Chapters | Content |
|--------|----------|---------|
| I Getting Started | Ch1 Landscape · Ch2 Common Model (six pieces) | Shared knowledge, a 200-line minimal loop |
| II Principles | Ch3 Loop · Ch4 Tools · Ch5 Context · Ch6 Memory · Ch7 Session · Ch8 Model · Ch9 Multi-Agent | Source-level comparison across 9 harnesses |
| III Engineering | Ch10 Observability & Evals · Ch11 Safety & Reliability | Line-level evidence + labs |
| IV Growth | Ch12 Learning Path · Ch13 One-Pager | Roadmap + cheat sheet |
| V Synthesis | Ch14 Harness Philosophy | Design philosophy wrap-up |
| VI Theory Base | T1–T7 + Appendices TA–TE (former `agent-infra-research`, fully merged) | The "why": theory, industry roles, ecosystem, Safety/Federated Memory, multimodal edge inference |
| Appendices | A Glossary · B Source Index · C Theory Bridge · D Research Log · E Papers | Verifiable |

## Quick Start

```bash
# Install dependencies (Node.js 18+)
npm install

# Local preview (http://localhost:5173)
npm run docs:dev

# Build (output in docs/.vitepress/dist/)
npm run docs:build

# Preview the build
npm run docs:preview
```

## Research Subjects

| Codename | Repository | Positioning |
|----------|-----------|-------------|
| Claude Code | `../claude-code-haha` | Leaked Anthropic internal implementation, most complete |
| Claw | `../claw-code-main` | Community Rust port |
| Codex | `../codex` | OpenAI's official Codex CLI |
| OpenCode | `../opencode` | Modern open-source agent on SST + Effect + AI SDK |
| Pi | `../pi` | Minimal, readable teaching-grade implementation |
| DeepSeek Harness | `../deepseek-harness` | Cordis plugin-based harness |
| Grok Build | `../grok-build` | xAI actor-isolation implementation |
| Hermes | `../hermes-agent` | Nous Research self-improving learning loop |
| Qwen-Agent | `../Qwen-Agent` | The only pure framework library (control group) |

## Deploy to GitHub Pages

1. Push to GitHub, then `Settings → Pages → Source: GitHub Actions`
2. Pushing to `main` triggers `.github/workflows/deploy.yml`
3. `docs/.vitepress/dist/` is deployed automatically

## Repository Layout

```
agent-deep-research/
├── docs/                  # VitePress site
│   ├── .vitepress/        # Config (config.mts, i18n locales)
│   ├── en/                # English edition (in progress)
│   ├── index.md           # Home
│   ├── ch00-*.md …        # Chapters
│   └── theory/            # Volume VI theory base
├── labs/                  # Runnable labs, one verified claim each
├── C-LAYER-PLAN.md        # Content-deepening roadmap
├── .github/workflows/deploy.yml
├── local-agent.md         # Original requirements
├── package.json
└── README.md
```

## Contributing

Issues and PRs are welcome:

- Re-run the nine repos' `git log --oneline` diff every 6 months
- Watch for new signals like `memorywire` / `two_pass` / `memory_flush`
- Intermediate research notes live in `docs/appendix-research-log.md`

## License

MIT

---

# 中文版说明

基于 **9 家真实 Agent 源码**（Claude Code / Codex / OpenCode / Pi / DeepSeek Harness / Grok Build 等）的由浅入深对比研究。提炼公共知识，给出一页纸速查与 10 周学习路径，落盘为 **VitePress**，已发布到 GitHub Pages。

> 源码快照：2026-08-22 · 全书结论均标注 `file_path:line_number` 锚点，可回溯

**在线阅读**：[GitHub Pages](https://atituiset.github.io/agent-deep-research/)（中文主线）· [English edition](https://atituiset.github.io/agent-deep-research/en/)（翻译进行中）· 本地 `npm run docs:dev`

## 章节总表

| 章 | 一句话核心 | 在线读 | 实验/Lab |
|----|-----------|--------|----------|
| 第0章 从你的使用经验出发 | 把你已见过的使用现象翻译成全书的概念地图 | [在线读](https://atituiset.github.io/agent-deep-research/ch00-user-phenomena) | — |
| 第1章 全景与定位 | 统摄公式 `Agent = Model + Harness`，60 年脉络与九家站位（[EN](https://atituiset.github.io/agent-deep-research/en/ch01-landscape)） | [在线读](https://atituiset.github.io/agent-deep-research/ch01-landscape) | — |
| 第2章 公共模型：六件套 | 形式化 Prompt / Loop / Tools / Context / Session / Model（[EN](https://atituiset.github.io/agent-deep-research/en/ch02-common-model)） | [在线读](https://atituiset.github.io/agent-deep-research/ch02-common-model) | — |
| 第3章 Agent Loop 精读 | "采样→执行→回填"闭合 + 预算/重试/装配/打断/观测五道闸 | [在线读](https://atituiset.github.io/agent-deep-research/ch03-loop) | [labs/](labs/) |
| 第4章 Tool / 权限 / 沙箱 | 可见性分级、审批、沙箱与并行；规格与执行同源 | [在线读](https://atituiset.github.io/agent-deep-research/ch04-tools) | [labs/](labs/) |
| 第5章 Context 工程 | 估算 → 预算 → 触发 → 压缩 → 缓存；Context = project(Session) | [在线读](https://atituiset.github.io/agent-deep-research/ch05-context) | [labs/](labs/) |
| 第6章 Memory 深潜 | 从 MemGPT 到 A-MEM：下一轮还记得、跨会话仍连贯 | [在线读](https://atituiset.github.io/agent-deep-research/ch05b-memory) | [labs/](labs/) |
| 第7章 Session / Trace / 持久化 | append-only WAL 为唯一写路径，Trace 是其可观测投影 | [在线读](https://atituiset.github.io/agent-deep-research/ch06-session) | [labs/](labs/) |
| 第8章 模型抽象与多 Provider | 把分裂的协议、鉴权与计费收敛成一次干净的采样调用 | [在线读](https://atituiset.github.io/agent-deep-research/ch07-model) | [labs/](labs/) |
| 第9章 多 Agent 与任务规划 | plan 落盘为 artifact，子 Agent 是隔离执行单元，四类拓扑 | [在线读](https://atituiset.github.io/agent-deep-research/ch08-multi-agent) | [labs/](labs/) |
| 第10章 可观测性与评测 | 贯穿全栈的 Trace 证据链、用量归一与成本分账 | [在线读](https://atituiset.github.io/agent-deep-research/ch09-observability) | [labs/](labs/) |
| 第11章 安全、可靠性与自愈 | 纵深防御：权限晶格 → 沙箱隔离 → 失败归一 → 分层自愈 | [在线读](https://atituiset.github.io/agent-deep-research/ch10-reliability) | [labs/](labs/) |
| 第12章 精深学习路径 | 12–14 周论文 × 源码 × 实现路线，每个 Lab 有骨架与验收标准 | [在线读](https://atituiset.github.io/agent-deep-research/ch10-roadmap) | — |
| 第13章 一页纸速查 | 全书压缩成一张 A4 + 5 分钟陈述框架 + 高频追问表（[EN](https://atituiset.github.io/agent-deep-research/en/ch09-one-pager)） | [在线读](https://atituiset.github.io/agent-deep-research/ch09-one-pager) | — |
| 第14章 Harness 思想总纲 | 五条哲学轴、四场公开交锋、五个词汇债券（[EN](https://atituiset.github.io/agent-deep-research/en/ch14-harness-philosophy)） | [在线读](https://atituiset.github.io/agent-deep-research/ch14-harness-philosophy) | — |

Lab 是 [`labs/`](labs/) 下的可运行迷你实验——每个 Lab 验证书里的一句话（写在其 docstring 里）。全部运行：`python3 -m unittest discover -s labs -v`。

## 如何阅读本书

1. **使用者入口：先读第 0 章**——把你已经见过的使用现象映射到全书概念，之后进任何一章都不迷路。
2. **再读第 1–2 章拿地图**：统摄公式与六件套坐标系。
3. **按需精读组件章（第 3–11 章）**：每章自洽，开头都会把自己挂回统摄公式，顺序可按你手头的问题定。
4. **用第 13 章一页纸收束**：30 分钟回顾全书；想动手走第 12 章学习路径，想收思想读第 14 章。

## 配套资源

- **英文版**：[`docs/en/`](docs/en/)，线上 [`/en/`](https://atituiset.github.io/agent-deep-research/en/)——目前覆盖 index、preface、Ch1、Ch2、Ch13、Ch14
- **插图**：[`docs/public/figures/`](docs/public/figures/)——各章架构图（SVG）
- **[C-LAYER-PLAN.md](C-LAYER-PLAN.md)**：内容深化（C 层）执行设计——Qwen-Agent / Hermes 对证补齐等

## 本书结构

| 卷 | 章节 | 内容 |
|----|------|------|
| I 入门 | Ch1 全景与定位 + Ch2 公共模型（六件套） | 公共知识，200 行最小闭环 |
| II 进阶 | Ch3 Loop · Ch4 Tools · Ch5 Context · Ch6 Memory · Ch7 Session · Ch8 Model · Ch9 多 Agent | 九家源码级对比 |
| III 工程 | Ch10 可观测评测 · Ch11 安全可靠性 | 行号级对证 + Lab |
| IV 成长 | Ch12 精深学习路径 + Ch13 一页纸速查 | 路径 + 速查 |
| V 综合 | Ch14 Harness 思想总纲 | 设计哲学收束 |
| VI 理论底座 | T1–T7 + 附录 TA–TE（原 `agent-infra-research` 全量并入） | Why 视角：理论框架、行业岗位、生态图谱、Safety/Federated、多模态端侧 |
| 附录 | A 术语表 · B 源码索引 · C 理论卷衔接 · D 中间调研落盘 · E 论文索引 | 可验证 |

目录侧边栏配置见 `docs/.vitepress/config.mts`。英文版页面位于 `docs/en/`，由 VitePress `locales` 的 `en` locale（`/en/`）驱动。

## 研究对象

| 代号 | 仓库 | 定位 |
|------|------|------|
| Claude Code | `../claude-code-haha` | 泄露的 Anthropic 内部实现，功能最全 |
| Claw | `../claw-code-main` | 社区 Rust 移植 |
| Codex | `../codex` | OpenAI 官方 Codex CLI |
| OpenCode | `../opencode` | SST + Effect + AI SDK 的现代开源 Agent |
| Pi | `../pi` | 极简可读的教学级实现 |
| DeepSeek Harness | `../deepseek-harness` | Cordis 插件化 Harness |
| Grok Build | `../grok-build` | xAI Actor 隔离实现 |
| Hermes | `../hermes-agent` | Nous Research 自改进学习闭环 |
| Qwen-Agent | `../Qwen-Agent` | 唯一纯框架库（对照组） |
| 理论底座 | ~~`../agent-infra/agent-infra-research`~~ → **已并入本书卷 VI**（2026-08） | 单仓维护，原仓库可归档 |

> 理论卷与源码卷现已同仓：卷 VI 答"为什么"，Ch1–14 答"怎么做的、如何选"。对位表见 `docs/appendix-bridge.md`。

## 一页纸（30 分钟速查）

见 `docs/ch09-one-pager.md`：含一页 A4 可打印版、5 分钟陈述框架（总→分→证→选）、7 个高频追问的 30 秒答案、便携卡片。

## 许可

MIT
