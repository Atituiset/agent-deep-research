# 附录 E 论文与文献索引

> 全书引用的论文/规范/工程文献一册收拢。按主题分组，每条给出：作者·年份·载体、**一句话读点**（为什么值得读）、以及本书的逐篇精读位置。带 ★ 的是建议优先精读的源头文献；带（博客）的是非同行评审但工程影响重大的文献。

## E.1 Loop / 推理线（精读见 Ch3 §3.1.2）

| 文献 | 出处 | 一句话读点 | 本书位置 |
|------|------|-----------|---------|
| ★ **ReAct**: Synergizing Reasoning and Acting in Language Models | Yao et al., arXiv:2210.03629, ICLR 2023 | 一切 Agent Loop 的祖先；重点读 Figure 1（Thought/Act/Observation 轨迹）与 ALFWorld 错误分析 | Ch3 §3.1.2 |
| ★ **Reflexion**: Language Agents with Verbal Reinforcement Learning | Shinn et al., arXiv:2303.11366, NeurIPS 2023 | "语言即梯度"——失败如何变成下一次输入；Actor/Evaluator/Self-Reflect 三角色拆分至今仍是自评系统的模板 | Ch3 §3.1.2 |
| ★ **Voyager**: An Open-Ended Embodied Agent with Large Language Models | Wang et al., arXiv:2305.16291, NeurIPS 2023 | 技能库（可执行代码 + docstring 向量检索）是一切 Skill 系统的原型；自动课程思想影响任务规划 | Ch3 §3.1.2 / Ch9 §9.1.3 |
| **SWE-agent**: Agent-Computer Interfaces Enable Automated Software Engineering | Yang et al., arXiv:2405.15793, NeurIPS 2024 | ACI 设计学开山：接口是独立变量；编辑护栏（唯一精确匹配）被 Claude/Codex 直接继承 | Ch3 §3.1.2 / Ch4 §4.1.2 |
| **CodeAct** (Executable Code Actions Elicit Better LLM Agents) | Wang et al., arXiv:2402.01230, ICML 2024 | 动作空间坍缩为 Python 的论证；解释器状态跨步保留的红利分析 | Ch3 §3.1.2 |
| **OpenHands** (原 OpenDevin) | Xingyao Wang et al., arXiv:2407.16741, ICLR 2025 | EventStream 事件化 Loop 与委托平台化；"Loop 是事件消费者"思想的系统化落地 | Ch3 §3.1.2 |

## E.2 Tools / 协议线（精读见 Ch4 §4.1.2）

| 文献 | 出处 | 一句话读点 | 本书位置 |
|------|------|-----------|---------|
| ★ **Toolformer**: Language Models Can Teach Themselves to Use Tools | Schick et al., arXiv:2302.04761, NeurIPS 2023 | 自监督插入 API + perplexity 增益过滤——"工具价值由下游预测改善定义"的思想雏形 | Ch4 §4.1.2 |
| ★ **Gorilla**: Large Language Model Connected with Massive APIs | Patil et al., arXiv:2305.15334, NeurIPS 2023 | 检索感知微调（RAFT）+ AST 匹配评测——今天 Tool Search / defer_loading 的源头 | Ch4 §4.1.2 |
| **ToolLLM**: Facilitating LLMs to Master 16000+ Real-world APIs | Qin et al., arXiv:2307.16789, ICLR 2024 | DFSDT 回溯搜索与"工具爆炸"问题首次系统暴露 | Ch4 §4.1.2 |
| **Function Calling** 技术报告（协议，非论文） | OpenAI 2023-06；Anthropic Tool Use 2023-11 | `tools[]/tool_calls/tool` role 三件套锁定了此后所有 Agent 的主干线形 | Ch4 §4.1.2 / Ch8 §8.1 |
| **MCP** (Model Context Protocol) 规范 | Anthropic 2024-11 起，持续演进 | JSON-RPC 2.0 + tools/resources/prompts 三原语 + OAuth 2.1；工具生态化的分水岭 | Ch4 §4.1.2 |
| **BFCL** (Berkeley Function Calling Leaderboard) | UC Berkeley, 2024-02 起持续运营 | AST → 可执行 → 多轮/幻觉工具的评测演进史，"评测即规格" | Ch4 §4.1.2 |

## E.3 Context / Memory 线（精读见 Ch5 §5.1、Ch6 全章）

| 文献 | 出处 | 一句话读点 | 本书位置 |
|------|------|-----------|---------|
| **Attention Is All You Need** | Vaswani et al., arXiv:1706.03762, NeurIPS 2017 | 上下文成为显式 token 序列与稀缺资源的物理起点；O(n²) 注意力是一切预算问题的根源 | Ch5 §5.1.1 |
| ★ **Lost in the Middle**: How Language Models Use Long Contexts | Liu et al., arXiv:2307.03172, TACL 2024 | U 型注意力曲线——信息摆位决定成败；压缩不仅是省 token 更是调位置 | Ch5 §5.1.3 |
| **Needle in a Haystack**（开源实验） | Kamradt, 2023-11（博客/GitHub） | 长上下文"冒烟测试"的发明；彩色网格图让"长而不准"肉眼可见 | Ch5 §5.1.3 |
| ★ **RULER**: What's the Real Context Size of Your Long-Context Models? | Hsieh et al., arXiv:2404.06654, COLM 2024 | 13 类参数化任务证明"有效长度 < 标称长度"；Agent 预算阈值的理论对冲对象 | Ch5 §5.1.3 |
| **Prompt Caching** 产品公告与技术说明 | Anthropic 2024-08-14（博客） | cache_control + TTL 的计费协议；KV-cache 工程底座是 PagedAttention/vLLM 谱系 | Ch5 §5.1.4 |
| ★ **MemGPT**: Towards LLMs as Operating Systems | Packer et al., arXiv:2310.08560, 2023 | OS 分页类比（主存/外存/中断换页）；Claude 四层防线的学理源头 | Ch6 §6.1.3 |
| **Generative Agents**: Interactive Simulacra of Human Behavior | Park et al., arXiv:2304.03442, UIST 2023 | 记忆流 + 重要性评分 + 反思三件套，第一次完整闭环 | Ch6 §6.1.2 |
| ★ **A-MEM**: Agentic Memory for LLM Agents | Xu et al., arXiv:2502.12110, NeurIPS 2025 | Zettelkasten 四阶段 + 写入时代理权——"最重的智能放在写入时" | Ch6 §6.1.3 |
| **Mem0**: Building Production-Ready AI Agents with Scalable Long-Term Memory | Chhikara et al., arXiv:2504.19413, 2025-04（开源 2024.10） | 抽取-更新-检索三阶段与 ADD/UPDATE/DELETE 决策的生产化 | Ch6 §6.1.2 |
| **Letta**（MemGPT 团队产品化） | 2024.10 | 论文→SDK 的分叉样本；Memory Blocks 块化存储 | Ch6 §6.1.2 |
| FAISS 向量检索库 | Johnson et al., 2017（Meta 开源） | IVF/PQ/HNSW——一切向量记忆的地基 | Ch6 §6.1.4 |
| **Zep**: A Temporal Knowledge Graph Architecture for Agent Memory | Rasmussen et al., arXiv:2501.13956, 2025 | 时序知识图谱记忆分支的代表 | Ch6 §6.1.4 |
| **FadeMem**: Biologically-Inspired Forgetting for Efficient Agent Memory | arXiv:2601.18642, 2026 | 艾宾浩斯衰减 + 强化回放 + 重要性门控的可微公式（编号见理论卷附录 TC） | Ch6 §6.1.3 |
| **Memory in the LLM Era**: Modular Architectures and Strategies | arXiv:2604.01707, 2026（VLDB 投稿预印本） | 五维分类 × 四范式框架——本书 Ch6 分类学的直接来源 | Ch6 §6.2 |
| **memorywire**: A Vendor-Neutral Wire Format | arXiv:2606.01138, 2026 | Memory 互操作线缆：`MemoryBlock / MemoryStream / MemoryProvider`——"Memory 的 MCP 时刻" | Ch6 §6.5 |

## E.4 Multi-Agent / 规划线（精读见 Ch9 §9.1）

| 文献 | 出处 | 一句话读点 | 本书位置 |
|------|------|-----------|---------|
| ★ **CAMEL**: Communicative Agents for "Mind" Exploration | Li et al., arXiv:2303.17760, NeurIPS 2023 | inception prompting 让协作涌现；role flipping 与无限客套两种失稳模式的首次记录 | Ch9 §9.1.2 |
| ★ **MetaGPT**: Meta Programming for a Multi-Agent Collaborative Framework | Hong et al., arXiv:2308.00352, ICLR 2024 | SOP 流水线 + 结构化 artifact 通信；"plan 是文档不是聊天"的来源 | Ch9 §9.1.2 |
| **AutoGen**: Enabling Next-Gen LLM Applications via Multi-Agent Conversation | Wu et al., Microsoft, arXiv:2308.08155, 2023 | ConversableAgent + 对话编程——多 Agent 可编程运行时的奠基 | Ch9 §9.1.2 |
| **LangGraph** 框架文档 | LangChain, 2024 | StateGraph/checkpoint/interrupt——协作控制流摊开为数据结构的一极 | Ch9 §9.1.2 |
| ★ **More Agents Is All You Need** | Li et al., arXiv:2402.05120, 2024 | 采样投票扩展律：多 Agent 收益的下界证明（方差削减而非分工智慧） | Ch9 §9.1.2 |
| **How We Built Our Multi-Agent Research System**（博客） | Anthropic, 2025-06 | 生产级正方证词：研究类任务提速约 90%，代价 ~15× token | Ch9 §9.1.2 / Ch14 交锋B |
| **Don't Build Multi-Agents**（博客） | Cognition (Walden Yan), 2025-06 | 反方檄文：共享完整上下文两原则；行动携带隐含决策不可消息同步 | Ch9 §9.1.2 / Ch14 交锋B |
| **Plan-and-Solve** Prompting | Wang et al., arXiv:2305.04091, ACL 2023 | 显式两阶段规划（先制定计划再执行）的提示法源头；BabyAGI 是其工程化身 | Ch9 §9.1.3 |
| ★ **ReWOO**: Decoupling Reasoning from Observations | Xu et al., arXiv:2305.18323, 2023 | 变量化 DAG 计划 + 批量执行的 token 经济学；"动态性 vs 效率"两难的定义者 | Ch9 §9.1.3 |

## E.5 可观测 / 评测线（精读见 Ch10 §10.1）

| 文献 | 出处 | 一句话读点 | 本书位置 |
|------|------|-----------|---------|
| ★ **Dapper**, a Large-Scale Distributed Systems Tracing Infrastructure | Sigelman et al., Google Technical Report, 2010 | Span 树 + TraceId 透传 + 采样三招；"可观测是基础设施义务"的出处 | Ch10 §10.1.1 |
| **OpenTelemetry** 规范 | CNCF, 2019 合并 OpenTracing/OpenCensus | vendor-neutral 三信号统一；GenAI 语义约定是下一代 Agent trace 的互通层 | Ch10 §10.1.1 |
| ★ **SWE-bench**: Can Language Models Resolve Real-World GitHub Issues? | Jimenez et al., arXiv:2310.06770, ICLR 2024 | F2P/P2P 测试判分的客观性设计与两个著名缺陷 | Ch10 §10.1.2 |
| **SWE-bench Verified** 子集 | OpenAI, 2024-08 | 500 条人工过滤样本——基准本身也需要审计 | Ch10 §10.1.2 |
| **AgentBench**: Evaluating LLMs as Agents | Liu et al., arXiv:2308.03688, ICLR 2024 | 8 类环境统一评测的首个尝试 | Ch10 §10.1.2 |
| **WebArena**: A Realistic Web Environment for Building Autonomous Agents | Zhou et al., arXiv:2307.13854, ICLR 2024 | 自托管真实站点 + 后置条件判分——状态改变骗不了数据库 | Ch10 §10.1.2 |
| ★ **Judging LLM-as-a-Judge** (MT-Bench & Chatbot Arena) | Zheng et al., arXiv:2306.05685, NeurIPS 2023 | judge 与人类一致率超八成，同时定型三类偏置的控制方法 | Ch10 §10.1.2 |
| **Tau-bench**: A Benchmark for Tool-Agent-User Interaction in Real-World Domains | Yao et al., arXiv:2406.12045, 2024 | 用户模拟器 + 策略符合度双镜；pass^k 指标暴露不稳定性 | Ch10 §10.1.2 |
| ★ **Let's Verify Step by Step** (PRM800K) | Lightman et al., arXiv:2305.20050, 2023 | 过程监督优于结果监督的系统性证据 | Ch10 §10.1.2 |
| **Math-Shepherd**: Verify and Reinforce LLMs Step-by-step without Human Annotations | Wang et al., arXiv:2312.08935, ACL 2024 | MC rollout 自动生成步级标签——PRM 的规模化路径 | Ch10 §10.1.2 |

## E.6 安全 / 可靠性线（精读见 Ch11 §11.1）

| 文献 | 出处 | 一句话读点 | 本书位置 |
|------|------|-----------|---------|
| **Programming Semantics for Multiprogrammed Computations**（能力安全） | Dennis & Van Horn, CACM, 1966 | "按能力授权而非按身份授权"——工具 allowlist 的五十年老根 | Ch11 §11.1.2 |
| **The Confused Deputy**（短文） | Norm Hardy, 1988 | 编译器借权泄密的寓言；权限必须按完整调用链评估的原型案例 | Ch11 §11.1.2 |
| ★ **Ignore Previous Prompt**: Attack Techniques For Language Models | Perez & Ribeiro, arXiv:2211.09527, 2022 | 直接注入的系统分类：goal hijacking 与 fake completion | Ch11 §11.1.2 |
| ★ **Not What You've Signed Up For**（间接提示注入） | Greshake et al., arXiv:2302.12173, AISec 2023 | "任何进入上下文的内容都是攻击面"——Agent 安全的第一公理来源 | Ch11 §11.1.2 |
| **OWASP Top 10 for LLM Applications** v1 / v2 | OWASP, 2023-08 / 2024-11 | Prompt Injection 始终列 LLM01；Excessive Agency 单列 | Ch11 §11.1.2 |
| ★ **Release It!** (2nd ed. 2018) | Michael Nygard, Pragmatic Bookshelf | Circuit Breaker/Bulkhead/Timeout 三模式——Agent 重试闸/子代理隔离/流超时的一切原型 | Ch11 §11.1.3 |
| **Chaos Engineering**（IEEE Software） | Basiri et al., Netflix, 2016 | "韧性是破坏出来的"；对应各仓故障注入测试 | Ch11 §11.1.3 |

## E.7 思想层（精读见 Ch14）

| 文献 | 出处 | 一句话读点 | 本书位置 |
|------|------|-----------|---------|
| **The Bitter Lesson**（短文） | Rich Sutton, 2019（博客） | 通用方法+算力终胜人类先验——复杂度之争的反方纲领 | Ch14 交锋A |
| **Agentless**: Demystifying LLM-based Software Engineering Agents | Zheng et al., arXiv:2407.01489, 2024 | 三段无 Agent 流水线打平复杂框架——Bitter Lesson 在编码 Agent 的实证 | Ch14 交锋A |
| **Building Effective Agents**（博客） | Anthropic, 2024-12 | workflow vs agent 的权威分界与五模式 | Ch14 §14.3 |
| **A Practical Guide to Building Agents**（博客） | OpenAI, 2025 | 先单代理+断点，再考虑多代理的中庸路线 | Ch14 §14.3 |
| **Context Engineering**（博客） | Manus, 2025-07 | append-only/文件系统终极上下文/todo 复述/KV-cache 第一指标四宣言 | Ch14 交锋C |
| **Effective Context Engineering for AI Agents**（博客） | Anthropic, 2025 | 注意力预算隐喻与压缩触发阈值的工程化 | Ch14 交锋C |
| **DeepSeek-R1**: Incentivizing Reasoning Capability in LLMs via RL | DeepSeek-AI, arXiv:2501.12948, 2025 | RL 内化长链推理——"模型侧吞并 Harness"论的证据之一 | Ch14 §14.5 |

> **核验状态说明**：以上条目的 arXiv 编号与 venue 已于 2026-08-24 经网络/知识库双重抽查（ReAct/MemGPT/A-MEM/Mem0/SWE-bench/Tau-bench 等 20 余篇）；FadeMem / Memory in LLM Era / memorywire 三篇的编号取自理论卷附录 TC（原 agent-infra-research 参考来源清单，2026-08 并入卷 VI）。新增或修正一律登记到附录 D.8。
