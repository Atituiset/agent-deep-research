# 前言

> 这是一本**可动手、可验收的 Agent 知识地图**——以 9 家真实代码仓为教材（理论卷 T1–T7 已并入为卷 VI），每个组件都从论文脉络讲到源码对证，再到你自己的 Lab。
>
> **如果你目前只在"使用"Agent**：直接从 [第0章](./ch00-user-phenomena.md) 开始——它把你见过的每个使用现象（压缩弹窗、权限确认、/resume、截断标注……）翻译成全书概念。所有机制你都已经见过，只是还不知道名字。

## 为什么是这本书

市面上 Agent 资料的两极：要么"原理讲得很玄"（只有论文没有工程），要么"教程讲得很虚"（只有 API 调用没有设计权衡）。本书走第三条路：

- 每章五段式：**①历史脉络与论文 lineage → ②原理深潜（形式化/算法/反例）→ ③九家源码对证（行号级锚点）→ ④结论与权衡 → ⑤未来方向**
- 每个 Lab 都有骨架、验收标准与常见坑，`git diff` 可检验
- 把 Qwen-Agent 作为"库形态对照组"，划清框架与产品的职责边界

## 研究对象：七码一书

| 代号 | 仓库 | 语言/形态 | 定位 |
|------|------|-----------|------|
| **Claude Code** | `claude-code-haha` (`src/query.ts:219`) | TS+Bun 产品级 | 泄露的 Anthropic 内部实现，功能最全 |
| **Claw** | `claw-code-main` (`rust/crates/runtime/src/conversation.rs:91`) | Python 镜像+Rust | 社区移植，"反例库" |
| **Codex** | `codex` (`codex-rs/core/src/session/turn.rs:153`) | Rust+Bazel 产品级 | OpenAI 官方，最系统化 |
| **OpenCode** | `opencode` (`packages/opencode/src/session/session.ts:224 Info Schema`) | TS+Effect+Bun | SST 团队开源产品 |
| **Pi** | `pi` (`packages/agent/src/agent-loop.ts:155 runLoop`) | TS 库+TUI | 教学级最小闭环 |
| **DeepSeek Harness** | `deepseek-harness` (`packages/core/agent-loop/src/agent.ts:70`) | TS+Cordis 插件化 | DeepSeek 的 Harness |
| **Grok Build** | `grok-build` (`crates/codegen/xai-chat-state/src/actor/state.rs`) | Rust Actor | xAI 实现，可靠性标杆 |
| **Qwen-Agent** | `Qwen-Agent` (`qwen_agent/agent.py:31`) | Python 纯框架库 | 阿里通义；**库形态对照组** |
| **Hermes Agent** | `hermes-agent` (`agent/conversation_loop.py:1766`) | Python 单体+网关 | Nous Research；自改进学习闭环 |
| **Infra 研究** | 已并入本书**卷 VI**（`src/theory/`，T1–T7 + 附录 TA–TE） | 理论底座（论文综述) |

> 所有锚点真实可跳转，详见 [附录 B](./appendix-sources.md)。

## 本书与理论卷（原 agent-infra-research）的关系

那份材料回答"**为什么**需要这些组件"（Memory/Context/Runtime 的论文与生态），已于 2026-08 全量并入本书**卷 VI**（T1–T7 + 附录 TA–TE）；本书正文（Ch1–14）回答"**各家怎么做的、tradeoff 在哪、我该怎么实现**"。重叠主题保留双视角：理论卷给概念工具，源码卷给工程判决。衔接与对位表见 [附录 C](./appendix-bridge.md)。

## 如何使用

| 模式 | 路径 | 时间 | 产出 |
|------|------|------|------|
| **使用者入门**（只会用 Agent？从这进） | Ch0 现象翻译器 → Ch2 六件套 → Ch12 Stage A 动手 | 1 天 | 概念全部对号入座 |
| **建立地图** | Ch1 全史时间线 → Ch2 六件套 → Ch12 路线总览 | 3 小时 | 知识坐标系 + 学习计划 |
| **思想收束** | 读完全部组件章后 → Ch14 九家哲学总纲 | 1 小时 | 三流派判断力 + 自研选型树 |
| **精读一章** | 任选 Ch3–Ch11 五段式，对照锚点走读 | 半天/章 | 能复述"正常路径+边界+失败" |
| **系统动手** | 按 Ch12 四阶段完成全部 Lab | 12–14 周 | mini-agent + 技术判断力 |
| **快速复习** | 只读 [Ch13 一页纸](./ch09-one-pager.md) | 30 分钟 | 要点 + 追问自查 |

## 符号约定

- `file_path:line_number`：源码锚点
- `> 公共规律` / `> 反例` / `> 思考题`：提炼与自检
- `Lab N`：动手实验（骨架→步骤→验收→坑）
- 权衡表标注"适用场景"而非优劣

## 可信度与局限

- 快照：2026-08-22；Claude Code 为泄露版（`999.0.0-local`），官方可能已演进
- Rust 单仓体量巨大，只覆盖 Agent 核心路径，不展开 TUI/Cloud 层
- "共性"均有跨仓证据；"差异"给权衡与场景

