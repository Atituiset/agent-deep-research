# 附录 C：参考来源清单

## Deep Research 抓取的来源（23 个）

### 学术论文 (Primary)

| # | 论文 | 角度 | 质量 |
|---|------|------|------|
| 1 | [MemGPT: Towards LLMs as Operating Systems](https://arxiv.org/abs/2310.08560) | Academic Frontier | ⭐⭐⭐⭐⭐ |
| 2 | [A-MEM: Zettelkasten-Inspired Agent Memory](https://arxiv.org/abs/2502.12110) | Academic Frontier | ⭐⭐⭐⭐⭐ |
| 3 | [FadeMem: Biologically-Inspired Forgetting for Efficient Agent Memory](https://arxiv.org/abs/2601.18642) | Academic Frontier | ⭐⭐⭐⭐⭐ |
| 4 | [Memory in the LLM Era: Modular Architectures and Strategies in a Unified Framework](https://arxiv.org/abs/2604.01707) | Academic Frontier | ⭐⭐⭐☆☆（VLDB 投稿预印本） |
| 5 | [memorywire: A Vendor-Neutral Wire Format](https://arxiv.org/abs/2606.01138) | Academic Frontier | ⭐⭐⭐⭐☆ |

### 行业报告 & 基准 (Secondary)

| # | 来源 | 角度 | 质量 |
|---|------|------|------|
| 6 | [Letta Blog: Benchmarking AI Agent Memory](https://www.letta.com/blog/benchmarking-ai-agent-memory) | Broad Landscape / Academic | ⭐⭐⭐⭐☆ |
| 7 | [AgentArch Benchmark](https://github.com/ghas-results/AgentArch) | Skeptical Limitations | ⭐⭐⭐⭐☆ |

### 技术博客 (Blog)

| # | 来源 | 角度 | 质量 |
|---|------|------|------|
| 8 | [Vectorize: Hindsight vs Letta Comparison](https://vectorize.io/articles/hindsight-vs-letta) | Broad Landscape | ⭐⭐⭐☆☆ |
| 9 | [HuggingFace Blog: Dynamic Context Engineering for AI Agents](https://huggingface.co/blog/jsemrau/dynamic-context-engineering-for-ai-agents) | Broad Landscape | ⭐⭐⭐⭐☆ |
| 10 | [EdenAI: AI Agent Memory Comparison](https://www.edenai.co/post/ai-agent-memory-mempalace-mem0-and-persistent-context) | Broad Landscape | ⭐⭐⭐☆☆ |
| 11 | [Arize: Orchestrator-Worker Agent Comparison](https://arize.com/blog/orchestrator-worker-agents-a-practical-comparison-of-common-agent-frameworks/) | Practitioner Patterns | ⭐⭐⭐⭐☆ |
| 12 | [Camunda: Hype to Impact - Agentic Orchestration](https://camunda.com/blog/2025/10/hype-to-impact-lessons-learned-making-agentic-orchestration-work/) | Practitioner Patterns | ⭐⭐⭐☆☆ |
| 13 | [ZenML: Production AI Agents with Temporal](https://www.zenml.io/llmops-database/building-production-ai-agents-with-temporal-based-workflow-orchestration) | Practitioner Patterns | ⭐⭐⭐☆☆ |
| 14 | [Milvus Blog: Context Engineering Strategies](https://milvus.io/blog/keeping-ai-agents-grounded-context-engineering-strategies-that-prevent-context-rot-using-milvus.md) | Skeptical Limitations | ⭐⭐⭐☆☆ |

### 招聘信息 (Secondary)

| # | 来源 | 角度 | 质量 |
|---|------|------|------|
| 15 | [ByteDance: Research Scientist (Agent Memory)](https://joinbytedance.com/search/7626144409813387573) | Industry Hiring | ⭐⭐⭐⭐☆ |
| 16 | [ByteDance: Software Engineer (Agent Memory)](https://joinbytedance.com/search/7626145948402010421) | Industry Hiring | ⭐⭐⭐⭐☆ |
| 17 | [OKX: Principal Engineer, Agent Infra](https://www.ziprecruiter.com/c/OKX/Job/Principal-Engineer,-Agent-Infrastructure-&-Memory-Architecture/-in-San-Jose,CA?jid=ee979bb71aab6bb6) | Industry Hiring | ⭐⭐⭐☆☆ |
| 18 | [TechGig: AI Tool Stack Before 2026](https://content.techgig.com/career-advice/ai-tool-stack-developers-must-master-before-2026/articleshow/126230579.cms) | Industry Hiring | ⭐⭐⭐☆☆ |

### 论坛 & 社区 (Forum)

| # | 来源 | 角度 | 质量 |
|---|------|------|------|
| 19 | [LangGraph GitHub Issue #6617](https://github.com/langchain-ai/langgraph/issues/6617) | Skeptical Limitations | ⭐⭐☆☆☆ |

### 不可靠 / 未提取主张 (Unreliable / Filtered)

| # | 来源 | 角度 | 原因 |
|---|------|------|------|
| 20 | DataCamp: CrewAI vs LangGraph vs AutoGen | Practitioner | AI 生成内容，标记为 unreliable |
| 21 | Machine Learning Mastery: Decision Framework | Practitioner | 低质量内容，标记为 unreliable |
| 22 | Latenode: LangGraph vs AutoGen vs CrewAI | Practitioner | 低质量内容聚合，标记为 unreliable |
| 23 | VLDB Memory Survey (arXiv:2604.01707) | Academic | 与 #4 为同一论文的重复条目；已合并处理，正文未依赖其量化结论 |

---

## 本报告引用的额外资源

### 论文

- [Attention Is All You Need](https://arxiv.org/abs/1706.03762) — Transformer 基础（Vaswani et al., 2017）
- [Lost in the Middle: How Language Models Use Long Contexts](https://arxiv.org/abs/2307.03172) — Context 位置敏感性（Liu et al., 2023，第三章引用）
- [ReAct: Synergizing Reasoning and Acting in Language Models](https://arxiv.org/abs/2210.03629) — Agent Loop 模式基础（第四章引用）

### 开源项目

- my-agent — 自研 TypeScript CLI Agent 实践项目（Agent Loop / Context Manager / Tool System 参考实现；非 Anthropic 官方仓库）
- [Letta (MemGPT)](https://github.com/letta-ai/letta) — OS 式 Agent Memory
- [Mem0](https://github.com/mem0ai/mem0) — 混合 Memory（Vector + Graph + KV）
- [Zep](https://github.com/getzep/zep) — 用户级 Memory Graph
- [Cognee](https://github.com/topoteretes/cognee) — Graph-based Memory
- [LangChain](https://github.com/langchain-ai/langchain) — Agent 框架
- [LangGraph](https://github.com/langchain-ai/langgraph) — 状态机 Agent 框架
- [CrewAI](https://github.com/crewAIInc/crewAI) — Multi-Agent 框架
- [AutoGen](https://github.com/microsoft/autogen) — Microsoft Multi-Agent 框架
- [Chroma](https://github.com/chroma-core/chroma) — 轻量级 Vector DB
- [Milvus](https://github.com/milvus-io/milvus) — 分布式 Vector DB
- [Temporal](https://github.com/temporalio/temporal) — Durable Execution 引擎
- [LoCoMo](https://github.com/snap-research/locomo) — 长对话记忆评估基准（ACL 2024，第二章/第六章引用）

### 标准化协议

- [MCP (Model Context Protocol)](https://modelcontextprotocol.io/) — Anthropic
- [A2A (Agent-to-Agent)](https://github.com/google/A2A) — Google

### 行业文章

- [Building Effective Agents](https://www.anthropic.com/research/building-effective-agents) — Anthropic 的 Agent 架构模式（Orchestrator-Worker 等，第四章引用）

## 来源核验记录（2026-08-02）

对本附录做了一次逐条复核，修正如下：

- **my-agent**：原标注为 "Anthropic 的 TypeScript CLI Agent 参考实现"，但 `github.com/anthropics/my-agent` 不存在（404）。按第五章技能树的描述，该仓库实为自研实践项目，已在附录更正归因，并在第四章加了说明、第七章改为自研仓库。
- **HuggingFace 博客**：原链接 slug（`jsemrau/context-engineering-for-agents`）不存在，已更新为 jsemrau 的实际文章链接。
- **FadeMem 标题**：实际论文名为 "Biologically-Inspired Forgetting for Efficient Agent Memory"（arXiv:2601.18642），已更正。
- **arXiv:2604.01707**：曾以不同名称重复列出（#4 / #23），已注明为同一论文并合并处理。该论文是 VLDB 投稿的预印本，"VLDB Memory Survey" 应理解为"投稿中"。
- **第三章价格表**：表中模型为 2024-2025 年的定价，已把表述改为"以 2025 年中的主流模型为示例"，避免被误读为 2026 年 7 月的现行价格。
- **第五章市场估计**：两处无数据支撑的推断（岗位增长率、中美需求量对比）已标注为个人推测。
- 额外补充了正文实际依赖但此前未列入的引用：Lost in the Middle、ReAct、LoCoMo、Building Effective Agents。

---

## 来源质量评级说明

| 等级 | 含义 |
|------|------|
| ⭐⭐⭐⭐⭐ Primary | 同行评议学术论文或原始 benchmark 数据 |
| ⭐⭐⭐⭐☆ Secondary | 公司官方博客、高质量技术分析 |
| ⭐⭐⭐☆☆ Blog | 技术博客、行业分析 |
| ⭐⭐☆☆☆ Forum | 社区讨论、GitHub Issues |
| ⭐☆☆☆☆ Unreliable | 低质量内容、AI 生成、无法验证 |

---

*本附录最后更新: 2026-08-02*
