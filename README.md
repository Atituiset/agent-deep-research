# Agent Deep Research — 九家 Agent 实现思想对比

基于 **9 家真实 Agent 源码**（Claude Code / Codex / OpenCode / Pi / DeepSeek Harness / Grok Build 等）的由浅入深对比研究。提炼公共知识，给出一页纸速查与 10 周学习路径，落盘为 **VitePress**，可一键发 **GitHub Pages**。

> 源码快照：2026-08-22 · 全书结论均标注 `file_path:line_number` 锚点，可回溯

## 在线阅读

- GitHub Pages（需启用）：`https://<your-org>.github.io/agent-deep-research/`
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

目录侧边栏配置见 `docs/.vitepress/config.mts`。

## 快速开始

```bash
# 安装依赖（需 Node.js 18+）
npm install

# 本地预览（http://localhost:5173）
npm run docs:dev

# 构建
npm run docs:build  # 产物在 docs/.vitepress/dist/

# 预览构建产物
npm run docs:preview
```

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

## 发布到 GitHub Pages

1. 推送到 GitHub，`Settings → Pages → Source: GitHub Actions`
2. 推送到 `main` 分支自动触发 `.github/workflows/deploy.yml`
3. 构建产物 `docs/.vitepress/dist/` 自动部署

## 目录

```
agent-deep-research/
├── docs/                  # VitePress 站点
│   ├── .vitepress/        # 配置（config.mts）
│   ├── index.md           # 首页
│   ├── preface.md         # 前言
│   ├── ch00-*.md …        # 正文章节
│   └── theory/            # 卷 VI 理论底座
├── .github/workflows/deploy.yml
├── local-agent.md         # 原始需求
├── package.json
└── README.md
```

## 贡献

欢迎提 issue / PR 纠错与增量：

- 每 6 个月重跑一次九家 `git log --oneline` 的 diff
- 关注 `memorywire` / `two_pass` / `memory_flush` 等新信号
- 中间调研见 `docs/appendix-research-log.md`

## 许可

MIT
