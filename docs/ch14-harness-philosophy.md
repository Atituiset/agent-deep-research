# 第14章 Harness 思想总纲：九家设计哲学

> 组件级对比（Ch3–Ch11）回答"每个部件怎么做"；本章回答更高层的两个问题：**为什么同样六个部件，各家长成了完全不同的形状？以及工业界的论文与博客里，这些分歧被怎样辩论过？**这是全书的思想收束。

## 本章图谱

```
三大流派            元隐喻         代表              一句话纲领
─────────          ─────         ─────             ─────────
系统派             OS/进程        Claude·Codex·Grok   "Agent 是一台需要内核的机器"
框架派             库/组合        Pi·Qwen-Agent       "Agent 是一组可组合的函数"
进化派             生物体         Hermes              "Agent 是会自己长大的有机体"
(支线) 总线派      事件总线       DeepSeek            "一切能力皆插件"
      工程派       现代栈范本     OpenCode            "把正确的事做规范"
      镜像派       移植对照       Claw                "翻译即审计"

证据链三层         论文(思想源头) → 技术博客(工程化转译) → 源码(最终判决)
```

## 14.1 证据链：论文 → 技术博客 → 源码

Harness 的每个思想都能沿三层证据链回溯。这张表是本章的地图，也是全书方法论：

| 思想 | 论文层（思想源头） | 博客层（工程化转译） | 源码层（本书对证） |
|------|------------------|--------------------|------------------|
| 循环式智能体 | ReAct (arXiv:2210.03629)；Reflexion (NeurIPS 2023) | Anthropic《Building Effective Agents》(2024-12)：区分 **workflow**（预定义路径）与 **agent**（模型动态掌舵） | 九家主循环（Ch3） |
| 接口设计优先 | SWE-agent (NeurIPS 2024)：ACI 设计空间决定成功率 | Anthropic《Writing effective tools for agents》：为模型而非人写工具文档 | ToolExposures/defer_loading（Ch4） |
| 最小复杂度 | Sutton《The Bitter Lesson》(2019)；Agentless (arXiv:2407.01489) | OpenAI《A Practical Guide to Building Agents》(2025)：先单代理+断点，再考虑多代理 | Pi/Qwen-Agent 极简形态 |
| 记忆与上下文 | MemGPT (2310.08560)；A-MEM (NeurIPS 2025) | Manus《Context Engineering》(2025-07)；Anthropic《Effective Context Engineering》(2025) | 四层压缩/ContextEngine ABC（Ch5/6） |
| 编排与委派 | CAMEL/MetaGPT/AutoGen (2023) | Anthropic《How We Built Our Multi-Agent Research System》(2025-06)；Cognition《Don't Build Multi-Agents》(2025-06)**正面交锋** | AgentTool/Collaboration-mode（Ch9） |
| 推理与工具内化 | DeepSeek-R1 (arXiv:2501.12948)：RL 内化长链推理 | OpenAI《New Tools for Building Agents》(2025-03)：Responses API 托管工具 | hosted tools / fncall_prompts（Ch8） |

> 方法论说明：论文给"可能性"，博客给"代价核算"，源码给"最终取舍"。只读论文会高估复杂度（Agentless 教训），只读博客会低估深度（KV-cache 背后是 PagedAttention 谱系），只读源码则知其然不知其所以然。

## 14.2 五条哲学轴：九家定位矩阵

同一组组件的差异，都能沿五条轴解释：

| 家 | 轴1 控制权 | 轴2 工程组织 | 轴3 能力观 | 轴4 约束观 | 轴5 扩展观 |
|----|-----------|-------------|-----------|-----------|-----------|
| Claude Code | 产品全托管 | TS 大仓单应用 | 静态集+defer_loading | 家长式（默认收紧） | MCP 首发 + Skill 目录 |
| Codex | 产品全托管 | Rust 30+ crate(Bazel) | 静态+server 侧 hosted | approval_policy 分级 | MCP + 命名空间 |
| Grok Build | 产品全托管 | Rust 50+ crate(Actor 边界) | 静态+ToolKind 反查 | 密钥脱敏贯穿 | plugin_registry |
| DeepSeek | 产品全托管 | TS 60+ 包(Cordis) | preset 组装 | waterfall 前置拦截 | 一切皆插件 |
| OpenCode | 产品全托管 | Bun monorepo(Effect) | 六类内置 agent+skill 包 | Ruleset 合并 | MCP + plugin 包 |
| Pi | 库交还宿主 | pnpm 5 包极简 | 回调注入一切 | beforeToolCall 钩子 | extension 包 |
| Qwen-Agent | 库交还宿主 | 单仓 Python 包 | TOOL_REGISTRY 注册制 | 信任宿主（无沙箱无权限） | mcpServers 即插 |
| Claw | 镜像上游 | Python+Rust 双轨 | 复刻上游 | 内联 authorize | 无 |
| Hermes | 产品全托管(网关) | Python 单体(9207 行) | **技能自生成** | 审批工具化+环境式 | agentskills.io |

## 14.3 轴1 控制权：workflow 还是 agent？

Anthropic《Building Effective Agents》给出被广泛引用的分界：**workflow 是开发者预编排的 LLM 调用链（prompt chaining/routing/parallelization/orchestrator-workers/evaluator-optimizer 五模式），agent 是模型自己决定路径与工具用量的循环**。这条分界恰好切开九家：

- **库派卖的是 workflow 原语**：Qwen-Agent 的 router/group_chat、Pi 的 `getSteeringMessages` 回调——把控制流交还宿主；
- **产品派卖的是 agent 本身**：五家产品的主循环都是"模型掌舵 + Harness 执法"，用户只给目标不给流程图；
- **OpenAI 指南的中庸立场**（《A Practical Guide》）：先做单 agent + 人工断点（human-in-the-loop），确认必要再升级多代理——这解释了为何九家全部以 Orchestrator-Worker 为最大编排粒度，Swarm 至今稀缺。

> 公理升级："留白是定价"（14.2 旧结论）应精确化为：**库派定价的是 workflow 自由度，产品派定价的是 agent 可靠性**。两者在 Anthropic 的定义里根本是两种商品。

## 14.4 轴2 工程组织：单体与微内核之争

```
单体派    Hermes run_agent.py 9207 行 —— 研究迭代速度优先
微内核派  Codex(Bazel+30 crate) · Grok(50+ crate) · DeepSeek(Cordis 60 包) —— 团队协作优先
分层折中  OpenCode(Effect Layer 强制注入) · Claude(ts 大仓目录约定)
极简派    Pi(agent 包 <3000 行) —— 教学优先
```

实证观察：工程组织与团队规模正相关，与思想优劣无关。Codex 仓库自带的 17 章 mdBook（`book/src/ch01-overview…ch17-engineering`）证明微内核派必须"文档换认知"；Hermes 单体则靠 `AGENTS.md` 与测试目录维持纪律。教训：**边界跟着组织走，不要提前抽象**。

## 14.5 轴3 能力观：静态、动态、自进化与"模型侧吞并"

```
静态能力观    发布时确定工具集，运行时只做可见性分级（多数派）
动态组合观    preset/plugin 启动期组装（DeepSeek composition / OpenCode skill 包）
自进化观      运行中生成并持久化新能力（Hermes _create_skill = Voyager 唯一完整落地）
模型侧吞并    ← 2025 年后的第四种力量
```

**模型侧吞并**是轴3 最新变量，三家证据：

1. OpenAI Responses API 把 `web_search/file_search/computer_use` 做成**服务端托管工具**（2025-03），工具执行发生在模型厂的基础设施里，Harness 只收到结果——Ch8 所述 Grok `context_details` 重写 total_tokens 正是为消化这种 server-side loop；
2. Meta 在 llama-models 开源仓库直接公开官方 system prompt，Llama 3.1 采用 **pythonic 工具调用格式**（`[tool_call(...)]`）而非 JSON——证明"调用协议"已被焊进权重，Harness 必须适配模型的原生方言（Qwen-Agent `fncall_prompts` 文本协议 FC 同理，是对无原生 FC 模型的逆向兼容）;
3. DeepSeek-R1 用 RL 把长链推理内化到 `<think>` 里，工具调用退居其后——提示"推理型模型 + 极简工具集"可能优于"普通模型 + 重 Harness"。

> 对自研者的含义：**Harness 的护城河恰恰是模型做不了的四件事——持有状态、执行权限、管理环境、归因成本**（对应 Session/Tools/沙箱/Trace）。工具本身正在变成模型厂的商品。

## 14.6 轴4 约束观：三种安全立场与分层护栏

家长式（Claude/Codex/Grok）、自由式（Qwen-Agent/Pi）、环境式（Hermes 七终端后端）之外，OpenAI 指南补充了工程化的中间件思路：**护栏分层**——输入分类器 → 工具级审批 → 输出过滤 → 人工断点，每层独立可测。这与 Claude 的横切权限晶格（deny>ask>allow）可叠加而非二选一。详见 Ch11 威胁模型四象限。

## 14.7 轴5 扩展观：协议、总线与市场

MCP（工具互通）、Cordis waterfall（切面拦截）、agentskills.io/Skill 目录（技能分发）三条路线详见各章；思想层的判断是：**协议路线赢在互操作性，总线路线赢在表达力，市场路线赢在分发**。2026 年的事实收敛是"MCP 做底座 + Skill 做分发"，总线派退守企业内部场景。

## 14.8 四场思想交锋（博客层的正面辩论）

Harness 设计的核心争议都发生过公开交锋。逐场复盘并给出演进判决：

### 交锋 A：该不该造复杂 Harness？——苦涩教训 vs ACI 设计学

- **反方**：Sutton《Bitter Lesson》——通用方法+算力终胜人类先验；Agentless (2024-07) 用"定位→修复→验证"三段无 Agent 流水线在当时打平甚至超过复杂 Agent 框架，且成本仅零头。
- **正方**：SWE-agent (NeurIPS 2024) 证明**接口质量本身**（ACI）是独立变量——同样的模型，设计好的工具接口显著提分。
- **判决（2026 回看）**：两者都对，但作用在不同时间尺度上。模型变强让"昨天的复杂 Harness"贬值（Agentless 对）；但"今天的最优接口"永远需要设计（SWE-agent 对）。九家的演进史就是持续拆掉过时脚手架、搭上新脚手架的过程——例如 Claude 用 `ToolSearch defer_loading` 替代了早期的大清单注入。

### 交锋 B：多 Agent 到底该不该建？——Anthropic vs Cognition

这是 2025 年最著名的一次公开对立：

- **Anthropic**《How We Built Our Multi-Agent Research System》（2025-06）：Orchestrator-Worker 让研究类任务**提速约 90%**；但坦承代价——多 Agent 系统耗 token 约为单聊的 **~15×**、单 Agent 约 **4×**；经验是"教编排者如何委派、告诉子代理如何分配努力"。
- **Cognition**《Don't Build Multi-Agents》（同期）：两条原则——①**共享完整上下文**；②**行动携带隐含决策，冲突的隐含决策必然产出烂结果**——据此主张当前模型做不好真多 Agent，推荐单线程线性 Agent + 上下文压缩（正是 Devin 的路线）。
- **九家的实际站队**：全部实现了 Orchestrator-Worker（Ch9），无一实现 Cognition 反对的"自由 Swarm 生产化"；Claude 甚至同时吸收双方——`LocalAgentTask` 后台化（Anthropic 阵营）+ 子代理继承父上下文摘要而非空白起步（向 Cognition 原则让步）。
- **判决**：分歧其实是**任务拓扑之争**——可并行检索的研究任务吃 Anthropic 路线，强耦合编辑的编码任务吃 Cognition 路线。九家用"子代理隔离 + 主线程汇总"同时占了两头。

### 交锋 C：上下文工程的三份宣言——Manus、Anthropic、Cognition

三篇博客构成 2025 年"Context Engineering"运动的正典，观点高度收敛于三点，分歧在手段：

| 原则 | Manus (2025-07) | Anthropic (2025) | Cognition (2025-06) |
|------|----------------|------------------|--------------------|
| 不改写历史 | **append-only**（永不修改过去的 action，只追加 undo） | compaction 保留边界前后段 | 单线程顺序推进 |
| 外部化记忆 | **文件系统即终极上下文**（大输出落盘，引用不入栈） | **结构化笔记**（NOTES.md/记忆工具） | 压缩摘要 |
| 目标保鲜 | **todo.md 复述**（每轮重写目标到上下文尾部对抗 lost-in-middle） | 即时检索（JIT context）替代预载 | — |
| 独有贡献 | KV-cache 命中率是第一指标（缓存输入价差约一个数量级）；**保留错误**作为决策锚点；mask 工具而非移除（logits 屏蔽防状态机违约） | 注意力预算隐喻；压缩触发阈值工程化 | 行动=隐含决策（不可逆性论证） |

**九家落地对照**：Manus 的 todo.md ↔ 各家 TodoWrite/plan 落盘（Ch9）；append-only ↔ Session 追加铁律（Ch7 I1）；保留错误 ↔ Grok repair 补 error-result 而非删除（Ch11）；mask 工具 ↔ Codex ToolExposures=NONE（不注册但保留 schema 校验，Ch4）；KV-cache 第一 ↔ Claude 缓存断裂检测事件（Ch5.6）。**三份宣言在九家里全部有对应物**——这是"公共知识"最硬的证据。

### 交锋 D：模型厂会不会把 Harness 吞掉？——护城河重划

DeepSeek-R1 内化推理、OpenAI 托管工具、Meta 焊协议入权重（见 14.5）。表面看 Harness 要被架空；实际重划后的版图是：

```
模型厂吞得走的：工具执行、部分推理、调用协议
模型厂吞不走的：跨厂状态(Session)、企业权限(审批/审计)、
               执行环境(沙箱/后端)、成本归因(分账)、评测闭环
```

这正是九家中产品派五家的估值逻辑，也解释了为何 OpenAI 自己也要发 Codex CLI——**模型厂下场做 Harness 恰恰证明这一层不可省略**。

## 14.9 流派融合预测（修订）

基于上述交锋的判决：

1. **产品派吸收进化派**：技能自生成将成为标配，前置条件是"技能签名+沙箱试运行"（Hermes 已验证需求，安全机制先行）；
2. **协议救活库派**：会话导出标准（sessionwire 类）一旦成型，Qwen-Agent/Pi 以 import/export 补齐 Session 短板；
3. **Cognition 原则成为多 Agent 默认约束**：共享上下文从美德变为架构要求——子代理默认带父上下文投影（Grok `PromptContext.audience` 已是雏形）；
4. **Harness 竞争主战场迁移**：从"功能齐全度"转向"上下文经济学"（KV-cache 命中率、注意力预算分配）——Manus 宣言的胜利。

## 14.10 给自研者的流派选择树

```
你的用户是谁？
├─ 终端开发者本人 ──► 系统派起步：Pi 打底，逐个加 Claude 的闸（Ch12 路线）
├─ 应用开发者(你做SDK) ──► 框架派：Qwen-Agent 形态；Session/Memory 留白但留接口，
│                          按 14.8C 清单实现 import/export 备将来
└─ 无人值守自动化 ──► 进化派+环境式：Hermes 为蓝本；先建审批分层（14.6）再开自进化
                      ⚠ 顺序不可反：没学会约束就开自进化 = Excessive Agency 现形记
通用第一步（不分流派）：按 Manus 宣言自查——append-only？目标复述？错误保留？
                        cache 断点稳定？（Ch5.6 三件套一天即可补齐）
```

## 小结

- [ ] 能沿"论文→博客→源码"三层证据链讲清任一条哲学轴（如用 Bitter Lesson/Agentless/SWE-agent 讲复杂度之争）
- [ ] 能复述 2025 两篇对立檄文的核心论点（Anthropic 15×token 提速 90% vs Cognition 共享上下文两原则），并说出九家的站队位置
- [ ] 能背出上下文工程三宣言的四个收敛点，并在任一家源码中指出对应物
- [ ] 能回答"模型厂吞不掉 Harness 的什么"并给出源码证据

> 组件讲完了，思想收束了。回到 [Ch12](./ch10-roadmap.md) 选定路线，或翻 [Ch13](./ch09-one-pager.md) 带走一页纸。
