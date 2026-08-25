# 第1章 全景与定位

> 先回答四个问题：Agent Infra 是什么、它从哪来（60 年历史脉络）、为什么 2025–2026 成了拐点、九家实现各自站在哪里。本章是全书地图——后续每章都会回到这张地图上定位。

## 1.1 Agent Infra 的层次

```
┌──────────────────────────────────────────────┐
│  Agent Application（应用）                    │
│  Claude Code / Codex CLI / OpenCode / Pi    │
├──────────────────────────────────────────────┤
│  Agent Infrastructure（基础设施）← 本书       │
│  Runtime │ Context │ Tools │ Memory │ Obs    │
├──────────────────────────────────────────────┤
│  LLM API / Model Serving（模型层）           │
│  Anthropic / OpenAI / DeepSeek / xAI / Qwen │
└──────────────────────────────────────────────┘
```

传统软件与 Agent 软件的类比在八家源码中得到逐一印证：

| 传统组件 | Agent 对应 | 本书证据 |
|---------|-----------|---------|
| 操作系统 | Runtime（调度 LLM + 工具） | 全部 9 家均有 `loop/turn/_run/run_conversation` 主循环 |
| 内存管理 | Memory / Context | 8 家有 compaction/projection；Qwen-Agent 用 RAG 替代；Hermes 把引擎做成可插拔 ABC |
| 文件系统 | Tool System | 全部 9 家均有 Tool 注册表与执行分离 |
| 进程/线程 | Session / Turn | 产品形态 6 家持久化 Session；库形态（Qwen-Agent/Pi core）交还宿主；Hermes 以 SQLite FTS5 做跨会话检索 |
| 系统日志 | Trace / Observability | 全部记录 token/耗时/工具轨迹，粒度各异 |
> **读表注 | 什么叫 compaction 与 projection？**（详见 Ch5.5/Ch7）
>
> MemGPT 的 OS 类比：上下文窗口 ≈ RAM，外部历史 ≈ Disk。落成两个动作——
>
> - **compaction（压实）**：窗口装不下全量历史时，把老轮次**摘要**成几句话（如 50KB 的文件读取结果 → 一行"已读过 X"），腾出空间。Claude 的四层压缩（Ch5.4）是最精细的实现。
> - **projection（投影）**：Session 永远保留全量（append-only），每次请求只把"当前可见子集"发给模型——像数据库 VIEW：底层不动，视图随查询变。Codex `for_prompt()`、Pi `transformContext` 都是投影函数。
>
> 二者关系：**compaction 是生成投影的手段之一；projection 是"不改写历史"的纪律**。特例两行：Qwen-Agent 不存对话记忆、每轮用 RAG 检索临时换页（`memory/memory.py:32`）；Hermes 把整套策略抽成 `ContextEngine(ABC)` 运行时可换（`context_engine.py:89`）。

## 1.2 Agent 全史：从能力安全到大模型智能体（1966–2026）

Agent Infra 不是凭空出现的——它是四条独立 lineage 的会合：

### 谱系一：系统与沙箱（"怎么安全地执行"）

```
1966  Capability-Based Security (Dennis & Van Horn)   能力即授权 → 工具 allowlist
1979  chroot                                            文件视图隔离原点
2000s Linux namespaces/cgroups/seccomp                 容器地基
2017  bubblewrap(bwrap)                                 无 root 沙箱 CLI 化 → Codex linux-sandbox
2018  gVisor(Google)/Firecracker(AWS)                   用户态内核/微 VM → 云端强隔离
2024+ @anthropic-ai/sandbox-runtime / xai-grok-sandbox 沙箱成为 Agent 标配件
```

### 谱系二：规划与推理（"怎么决定下一步"）

```
2022-10 ReAct (arXiv:2210.03629, ICLR 2023)   reason→act→observe 循环 → 一切 Loop 的祖先
2023-03 Reflexion (NeurIPS 2023)               语言化自我反思 → stop-hook/自评的雏形
2023-05 Voyager                                skill library 终身学习 → Skill 系统(Ch9)
2024-02 CodeAct (ICML 2024)                    代码即行动空间 → code_interpreter/bash 为核心工具
2024-05 SWE-agent (arXiv:2405.15793)           Agent-Computer Interface 设计空间 → 工具人机工程学
> **读表注 | Voyager 的"技能库终身学习"是什么？**（详见 Ch9/Ch14 轴3）
>
> Voyager (arXiv:2305.16291) 在 Minecraft 里演示了不训权重的学习：每学会一件事，
> 就把解法写成带描述的可复用代码存入**技能库**；下次先检索复用，没有才探索，学会再入库。
> ——"学习"以代码形式在外部累积（ReAct 答"单次怎么走"、Reflexion 答"失败怎么改"，
>   Voyager 答"这次学的下次如何不重学"）。
>
> 2026 年的产品化对应：Hermes `_create_skill()` 任务后自主建技能并自我改进（唯一完整闭环）；
> Codex `ToolExposures.DEFERRED` / Claude `defer_loading` = 技能按需加载；
> Claude Skill 目录 / agentskills.io 标准 = 技能分发市场。
```

### 谱系三：工具调用（"怎么连接外部世界"）

```
2023-02 Toolformer (arXiv:2302.04761)          自监督学会调 API → 工具学习范式确立
2023-06 OpenAI Function Calling                协议标准化第一枪
2023-05 Gorilla (arXiv:2305.15334)             检索式工具选择 + 幻觉缓解
2024-11 MCP (Anthropic)                        工具生态互操作标准 → 八家中七家原生支持
2024  BFCL (Berkeley Function Calling Leaderboard)  工具调用可评测化
```

### 谱系四：记忆与上下文（"怎么记住"）

```
2017  Transformer 自注意力                      上下文的物理上限开始被讨论
2023-07 Lost in the Middle (arXiv:2307.03172)  长窗口≠好记忆
2023-10 MemGPT (arXiv:2310.08560)              OS 分页类比 → compaction 的理论源头
2023-12 RULER (arXiv:2404.06654→2024)          长上下文真实有效长度可测
2024-08 Prompt Caching (Anthropic)             前缀缓存改变成本结构 → Ch5 缓存断点设计
2025  A-MEM (NeurIPS 2025)                     Zettelkasten 写入时代理 → 记忆主动组织
2026  FadeMem/memorywire                        衰减遗忘 / 记忆互操作标准提案
```

**会合点**：2024–2025 年，SWE-bench 把四条谱系压进同一个考场——一个能修复 GitHub issue 的系统必须同时解决执行安全（谱系一）、多步规划（谱系二）、工具接入（谱系三）与长任务记忆（谱系四）。Agent Infra 作为独立工程学科由此确立。

## 1.3 为什么 2025–2026 是拐点

四个推力在本书的源码对照中清晰可见：

1. **学术收敛**：MemGPT → A-MEM → FadeMem → memorywire；ReAct → SWE-agent。九家实现中，Claude 的 `snip/micro/collapse`、Grok 的 `two_pass`、DeepSeek 的 `compaction-basic + tool-result-pruner` 都是对同一批论文的不同工程回答。
2. **产业验证**：独立的 Memory Infra 团队出现；八家里已有 5 家把 Memory/Context 拆为独立 crate/package（Grok `xai-grok-compaction/xai-grok-memory`、DeepSeek `compaction-*`、Codex `context_manager`、OpenCode 隐藏 compaction agent、Claude compact 服务目录）。
3. **模型侧变化**：长上下文（200K–1M）与 Prompt Caching 让"全量重放 + server cache"（Codex `store:false`）成为可行解，也让"token 预算驱动的压缩"成为必选项。
4. **生态标准化**：MCP 成事实标准（除 Pi 外均原生支持），Skill/Plugin 成为第二层扩展。

## 1.4 八家定位一张图

按"**抽象层厚度**"（横轴）与"**工程完备度**"（纵轴）定位：

```
工程完备度 ↑
            │ Claude Code ●      Codex ●
            │ Grok Build ●
            │ DeepSeek ●     OpenCode ●
            │
            │        Pi ●        Qwen-Agent ●
            │   Claw(移植中)●
            └────────────────────────────→ 抽象层厚度（插件化/多模型/多Agent）
              库/框架 ←──────────→ 产品/Harness
```

| 家 | 一句话定位 | 最值得抄的 | 对应深读章节 |
|----|-----------|-----------|-------------|
| **Claude Code** | 功能最全的产品级 Harness（TS+Bun） | 四层压缩、cache 断点稳定、权限横切 | Ch3/5/11 |
| **Codex** | 最系统化的 Rust 工程（Bazel+30 crate） | Turn/Step 二分、OTel、linux-sandbox | Ch3/8/11 |
| **Grok Build** | 可靠性标杆（Actor+Journal+worktree） | 启动自愈、密钥前缀脱敏、live/cumulative 分账 | Ch7/10/11 |
| **DeepSeek Harness** | 插件化极致（Cordis 事件总线） | Inbox 打断语义、waterfall 钩子、step 级重试 | Ch3/9 |
| **OpenCode** | 现代 TS 栈范本（Effect+Drizzle+AI SDK） | fork idMap、Truncate 统一截断、10+ provider | Ch7/8 |
| **Pi** | 教学级最小闭环（TS） | 200 行 runLoop、两阶段 transformContext | Ch2/3/5 |
| **Qwen-Agent** | 唯一纯框架库（Python，阿里） | Memory=RAG Agent 组合、fncall_prompts 文本协议 FC、TOOL_REGISTRY | Ch4/6/11 对照组 |
| **Claw** | 移植桥梁（Python 快照+Rust 运行时） | parity_audit 方法论、"反例库" | 各章反面案例 |
| **Hermes Agent** | 自改进学习闭环（Python 单体，Nous Research） | 可插拔 ContextEngine、7 终端后端、技能自生成、轨迹压缩 | Ch3/5/6/11 |

> 读法提示：把 **Qwen-Agent 当对照组**——它在 Session/Trace/权限三层留白，恰好反衬产品形态五家各自补了什么（详见 7.3.2/10.3.2/11.3.2 三处专节分析）。

## 1.5 本书的读法：五段式

第 3–11 章每章固定五段：**①历史脉络与论文 lineage → ②原理深潜 → ③对证分解（源码锚点）→ ④结论权衡 → ⑤未来方向**，并配 Lab 与思考题。建议先读本章时间线建立坐标系，再按 Ch12 的四阶段路线进入各章——每段都能回答"这行代码是哪篇论文的哪个思想落地成的"。

> 下一章把"无论哪家都绕不开"的公共知识形式化为六件套模型，并给出六件套各自的演化小史。
