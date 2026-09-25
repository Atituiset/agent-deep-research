# Agent Deep Research — How 9 Agent Harnesses Really Work

[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](https://opensource.org/licenses/MIT)
[![GitHub Pages](https://img.shields.io/badge/docs-GitHub%20Pages-blue)](https://atituiset.github.io/agent-deep-research/)
[![English Edition](https://img.shields.io/badge/English%20edition-inside-brightgreen)](https://atituiset.github.io/agent-deep-research/en/)

**Read online: [atituiset.github.io/agent-deep-research](https://atituiset.github.io/agent-deep-research/)** (中文为主 · [English edition](https://atituiset.github.io/agent-deep-research/en/) in progress)

## Elevator Pitch

What actually happens between your prompt and an agent's answer? This book takes apart the source code of 9 real agent harnesses — Claude Code, Codex, OpenCode, Pi, DeepSeek Harness, Grok Build, Claw, Qwen-Agent, and Hermes — and shows that they all converge on one formula: **Agent = Model + Harness**, where the Harness decomposes into six pieces: Prompt, Loop, Tools, Context, Session, and Model. Every claim is anchored to a `file_path:line_number` in the original repositories, so you can verify it yourself. Each chapter follows the same five-part rhythm: paper lineage → principle deep-dive → source-code evidence → trade-off verdict → future directions. You get a one-page printable cheat sheet, a 10-week hands-on learning path, and five reusable design patterns (append-only, projection-over-mutation, boundary set + retention set, failure boundary, minimal Harness tax) distilled from how nine teams solved the same problems differently. Source snapshot: 2026-08-22.

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

The English edition currently covers `index`, `preface`, `ch01-landscape`, `ch02-common-model`, `ch09-one-pager`, and `ch14-harness-philosophy` under [`docs/en/`](docs/en/), served at `/en/`.

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

## 在线阅读

- GitHub Pages：<https://atituiset.github.io/agent-deep-research/>
- 英文版（翻译进行中）：<https://atituiset.github.io/agent-deep-research/en/>
- 本地：`npm run docs:dev`

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
