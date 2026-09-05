# 第七章：研究计划与学习路径

## 设计原则

在制定学习计划之前，先明确几条原则：

1. **深度优先，广度其次**：与其泛泛了解 20 个框架，不如深入理解 2 个核心架构（MemGPT + A-MEM）并自己实现一遍
2. **代码优先，博客其次**：看 10 篇博客不如读 1 篇论文 + 写 1 个 demo
3. **系统思维贯穿始终**：每学一个组件，问自己"它在整个 Agent Infra 中处于什么位置？它和相邻组件如何交互？"
4. **产出驱动学习**：每个 Phase 有明确的产出物（代码、文章、demo），而不是"学完了"
5. **实战即验证**：以真实架构设计讨论为阶段性验证点，检验知识体系的完整度

---

## 知识体系总览

```
Agent Infra 知识体系 (自上而下)

Level 4: Architecture & Strategy
├─ Agent Memory 架构选型: 什么时候用 MemGPT 模式？什么时候用 A-MEM 模式？
├─ Multi-Agent 编排策略: 单 Agent vs Orchestrator-Worker vs Swarm
├─ Context vs Memory vs RAG 的职责边界
└─ Agent Infra 的技术路线图预判

Level 3: System Design
├─ 端到端 Agent Runtime 设计 (Loop + Context + Memory + Tools)
├─ Memory Pipeline 设计 (Ingestion → Storage → Indexing → Retrieval → Forgetting)
├─ Context Engineering (Token预算 + 摘要策略 + Caching + 窗口布局)
├─ Multi-Agent Memory 共享与一致性
└─ Agent 可观测性与调试

Level 2: Core Implementation
├─ Agent Loop 实现 (状态机 / 串行执行 / 重试策略)
├─ Context Manager 实现 (Token估算 + 摘要触发 + 结构化摘要生成)
├─ Memory System 实现 (Vector存储 / 检索 / 衰减)
├─ Tool System 实现 (Schema定义 / 参数验证 / 执行沙箱 / MCP集成)
└─ Session & Trace 持久化

Level 1: Foundations
├─ Transformer 架构与 Attention 机制
├─ LLM Inference 基础 (prefill / decode / context window / tokenization)
├─ Token Economics (不同模型的定价 / Caching / 成本模型)
├─ 存储系统基础 (Vector DB / Graph DB / KV Store / Document Store)
└─ 分布式系统基础 (Consistency / Checkpoint / Workflow Engine)
```

---

## Phase 1: 基础理论（2 周）

### 目标
建立 Agent Infra 的理论地基。学完这个 Phase 后，能回答"为什么 Agent Memory 不能简单地用 Vector DB + RAG 解决？"

### Week 1: LLM 基础 + Token Economics

| 天 | 课题 | 具体内容 | 产出 |
|----|------|---------|------|
| 1 | Transformer 精要 | "Attention Is All You Need" + Jay Alammar 图解 + 3Blue1Brown 视频 | Attention 机制的手写笔记 |
| 2 | Tokenization 深入 | BPE / SentencePiece / Tiktoken 的原理与差异 | Token 计数实验（chars/4 vs tiktoken） |
| 3 | Context Window 机制 | Prefill vs Decode、Position Encoding、Sliding Window | Context Window 机制总结 |
| 4 | Token Economics 建模 | Anthropic/OpenAI 定价、Prompt Caching、成本计算器 | Excel/代码成本模型 |
| 5 | RAG 深入 | 从 Naive RAG → Advanced RAG → Agentic RAG 的演进 | RAG 演进图谱 |

**Week 1 检查点**:
- [ ] 能用大白话解释 Transformer 的 QKV Attention
- [ ] 能计算一个 20 轮 Agent 对话在不同策略下的 Token 成本
- [ ] 能说清楚 RAG、Advanced RAG、Agentic RAG 之间的本质区别

### Week 2: Memory 基础 + Agent 基础

| 天 | 课题 | 具体内容 | 产出 |
|----|------|---------|------|
| 1 | MemGPT 论文精读 | 逐段阅读 + OS 类比验证 | MemGPT 论文笔记（架构图 + 关键机制） |
| 2 | MemGPT 代码阅读 | Letta 开源代码核心模块 | 核心流程的代码级理解 |
| 3 | A-MEM 论文精读 | 逐段阅读 + 与 MemGPT 对比 | A-MEM vs MemGPT 对比表 |
| 4 | Agent Loop 基础 | my-agent 的 loop.ts 代码精读 | Agent Loop 状态机图 |
| 5 | 本报告阅读 | 全部 7 章详读 | 问题清单（不理解的地方） |

**Week 2 检查点**:
- [ ] 能画出 MemGPT 的 Paging 机制流程图（不需要看论文）
- [ ] 能说清楚 MemGPT 和 A-MEM 在代理权位置上的本质区别
- [ ] 能画出 Agent Loop 的完整状态机

---

## Phase 2: 核心系统（4 周）

### 目标
基于 my-agent，实现一个最小但完整的 Agent Memory System。覆盖从 Loop → Context → Memory → Tools 的完整链路。

### Week 3-4: Agent Runtime 核心

```
Day 1-2: 环境搭建 + 现有代码理解
  - git clone 自研的 my-agent 仓库（本地路径或私有 repo）
  - 跑通 npm run dev
  - 理解每个模块的职责和接口

Day 3-5: ContextManager 重写
  - 当前实现: 基础 Token 估算 + 简单摘要
  - 增强:
    1. 更精确的 Token 估算（可选的 tiktoken 模式）
    2. 结构化摘要模板（见第三章）
    3. 摘要质量验证（LLM 自检）
    4. 多级摘要（粗粒度覆盖全历史 + 细粒度覆盖最近）
    5. 单元测试（验证不同策略的行为）

Day 6-8: Prompt Caching 集成
  - 当前实现: 部分 caching
  - 增强:
    1. System Prompt + Tool Defs 标记 cache_control
    2. 动态 cache 边界（根据 context 大小调整哪些内容在 cache 前缀中）
    3. Cache 命中率监控和日志
    4. 模拟不同对话间隔对 cache hit rate 的影响

Day 9-10: Tool System 增强
  - 当前实现: 4 个基础工具
  - 增强:
    1. Tool Contract 定义和自动验证
    2. Tool 输出截断策略（智能保留关键信息）
    3. Memory 工具: remember, recall, forget（第一阶段先做简单的）
    4. 循环检测 + 自动干预
```

### Week 5-6: Memory Pipeline

```
Day 1-3: Memory Storage Layer
  - 集成 Vector DB (Chroma)
  - 实现:
    1. Ingestion: 从对话中自动提取关键信息
    2. Storage: 将信息存储为 (text, embedding, metadata) 三元组
    3. Indexing: 构建语义索引
    4. Retrieval: 语义搜索 + 关键词搜索

Day 4-6: Memory Management Layer
  - 实现:
    1. Working Memory: Context 中的结构化任务状态
    2. Episodic Memory: 时序事件记录
    3. Semantic Memory: 事实和偏好的结构化存储
    4. 三种 Memory 之间的信息流动

Day 7-8: Memory Evolution
  - 实现:
    1. 重复检测（embedding similarity + LLM 判定）
    2. 冲突检测（发现矛盾信息 → 标记而非自动删除）
    3. 衰减（基于时间和访问频率的权重调整）

Day 9-10: Integration & Testing
  - 将 Memory System 集成到 Agent Loop 中
  - 编写集成测试（模拟 20+ 轮对话，验证 Memory 质量）
  - 编写 Demo: "Ask the agent to remember my preferences, and recall them later"
```

**Phase 2 检查点**:
- [ ] Agent Loop 能独立完成 20+ 轮的工具调用任务
- [ ] ContextManager 在 Token 超限时自动执行结构化摘要
- [ ] Memory System 支持完整的 CRUD + 遗忘 + 冲突检测
- [ ] Prompt Caching 正常工作并可通过日志验证
- [ ] 有 3 个可演示的 use case

---

## Phase 3: 深度专题（6 周）

### 目标
在三个核心方向深入，每个方向 2 周。产出可公开的深度分析或 demo。

### 专题 A: Agentic Retrieval vs Write-time Agency（Week 7-8）

**研究问题**:
- 检索时代理（MemGPT/Letta 模式）和写入时代理（A-MEM 模式）在具体场景下谁更优？
- 两种模式可以混合使用吗？

**实践**:

```
Week 7: 实现 Agentic Retrieval 模式
  - 基于 Phase 2 的 Memory System
  - 增强检索: LLM 自主决定何时检索、检索什么、检索多少次
  - 实现迭代检索: LLM 可以 reformulate query 并重新检索
  - Benchmark: 在 5 个测试场景上测量检索质量

Week 8: 实现 Write-time Agency 模式
  - 基于 A-MEM 的四阶段 Pipeline
  - 实现 Note Construction + Link Generation
  - 对比两种模式在相同场景下的表现
  - 分析: Token 成本、检索延迟、回忆质量、演化能力

  产出: 对比分析报告 + 开源 demo
```

### 专题 B: Multi-Agent Memory Sharing（Week 9-10）

**研究问题**:
- 两个 Agent 如何共享 Memory 而不相互污染？
- 共享 Memory 的冲突如何解决？

**实践**:

```
Week 9: 设计 + 实现
  - 场景: Researcher Agent + Writer Agent 协作写技术报告
  - Researcher: 搜索资料、分析数据、整理发现 → 写入 Shared Memory
  - Writer: 从 Shared Memory 获取发现、组织语言、生成报告
  - 关键设计:
    1. Memory Namespace: Private vs Shared
    2. Conflict Resolution: Last-write-wins + Conflict Marker
    3. Memory Provenance: 每条记忆标注来源 Agent

Week 10: 测试 + 优化
  - 分别用共享 Memory 和不共享 Memory 运行同一任务
  - 对比: 协作质量、Token 消耗、信息传递效率
  - 分析: 哪些类型的信息适合共享？哪些应该隔离？

  产出: Multi-Agent Memory 设计文档 + demo
```

### 专题 C: Context Engineering 深度优化（Week 11-12）

**研究问题**:
- Context 的不同布局策略对 Agent 表现的影响？
- 如何在有限 Token 预算下最大化有效信息密度？

**实践**:

```
Week 11: Context 布局实验
  - 对比 3 种布局策略:
    A: 全量历史（baseline）
    B: Summary + 最近 N 轮（my-agent 默认）
    C: Summary + Working Memory + 最近 N 轮（带位置优化）
  - 在 10 个任务上测试（代码、对话、分析、创作各 2-3 个）
  - 评估: 任务完成率、Token 消耗、完成时间

Week 12: Token Budget Optimization
  - 实现第三章中的 Context Allocator 概念
  - 根据任务类型动态调整各区域的 Token 分配
  - 实现 Context Hygiene 策略（去重、去噪、过期检测）

  产出: Context Engineering 最佳实践指南 + benchmark 数据
```

**Phase 3 检查点**:
- [ ] 专题 A: 完成两种 Memory 范式的对比分析并发布
- [ ] 专题 B: 实现 Multi-Agent Memory Sharing 原型并开源
- [ ] 专题 C: 发布 Context Engineering 最佳实践文档

---

## Phase 4: 持续产出

### 产出节奏

| 类型 | 频率 | 平台 | 示例主题 |
|------|------|------|---------|
| **深度技术文章** | 每 2 周 1 篇 | 个人 Blog + 掘金 | "Agent Memory 的四种范式""Context Engineering 实战" |
| **开源项目** | 持续迭代 | GitHub | Agent Memory 参考实现 |
| **论文笔记** | 每周 1 篇 | 个人 Blog | 新论文的精读笔记 |
| **演讲/分享** | 每季度 1 次 | 公司/Meetup | Agent Infra 技术深度 |

### 架构能力自检清单（优先级排序）

1. **系统设计能力**（最高优先级）
   - 练习: 从 0 设计一个 AR 眼镜的 AI Memory 系统
   - 关键 tradeoff: 端侧 vs 云端、实时 vs 批量、隐私 vs 智能

2. **Memory 架构深度**
   - 能深入讨论 MemGPT 和 A-MEM 的算法细节
   - 能画出完整的 Memory Pipeline 架构图
   - 能分析不同存储引擎在不同场景的适用性

3. **Context Engineering 实操**
   - 能算清楚不同策略的 Token 成本
   - 能解释 Prompt Caching 在不同场景下的收益
   - 有实际的 Token 优化案例

4. **工程能力**
   - my-agent 的代码级理解
   - 能从零搭建一个 Agent Runtime 原型
   - 对生产环境的可靠性、可观测性有思考

### 长期目标

- **6 个月内**: 在 Agent Infra / Memory 方向有 1 个开源项目 + 3 篇深度文章
- **12 个月内**: 在行业中可被识别为这个方向的专家
- **18 个月内**: 能主导一个 Agent Infra 团队的技术方向

---

## 关键资源索引

### 必读论文（按阅读顺序）

| # | 论文 | 为什么必读 | 阅读重点 |
|---|------|-----------|---------|
| 1 | MemGPT (2310.08560) | Agent Memory 的奠基之作 | OS 类比的具体映射、Paging 机制、Working Memory 自编辑 |
| 2 | A-MEM (2502.12110) | 写入代理的范式转变 | 四阶段 Pipeline、与 MemGPT 的对比 |
| 3 | FadeMem (2601.18642) | 遗忘机制 | 双衰减层、adaptive fusion |
| 4 | memorywire (2606.01138) | Memory 标准化 | 5 operations × 4 types 的 wire format |
| 5 | Memory in the LLM Era (2604.01707) | 全景综述（VLDB 投稿预印本） | 4-module unified framework |

### 必读代码（按优先级）

| # | 项目 | 重点模块 | 预计时间 |
|---|------|---------|---------|
| 1 | my-agent | loop.ts, context.ts, tools.ts | 4 小时 |
| 2 | Letta | memory management, agent loop | 8 小时 |
| 3 | Mem0 | memory operations, storage backends | 6 小时 |
| 4 | LangGraph | graph state management, checkpointing | 6 小时 |

### 推荐博客和 newsletter

- **Anthropic Blog**: 模型能力更新、Prompt Caching 最佳实践
- **Letta Blog**: Agent Memory 的工程实践
- **HuggingFace Blog**: Context Engineering 深度文章
- **Milvus Blog**: Vector DB 在 Agent 场景的应用
- **arxiv (cs.AI / cs.CL)**: Agent + Memory + Context 方向的新论文

---

## Phase 5: v2.0 报告的深化方向

当前 v2.0 报告深度已到算法分析和工程设计层面。以下是四个可继续深化的方向，每个方向都从"分析"走向"实现"，从"理解别人的设计"走向"自己做出设计决策"。

### 方向 1: 代码级参考实现

**目标**：把 MemGPT 的 Paging 机制和 A-MEM 的四阶段 Pipeline 写成可运行的代码。

**为什么这个方向重要**

当前报告对这两种架构的分析停留在伪代码和算法描述层面。真正写代码时会遇到大量"魔鬼在细节中"的问题：

- MemGPT 的 `_select_fifo_slot()` 到底怎么选？怎样算"最不重要"的信息？
- A-MEM 的 Note Construction 中，如果 LLM 提取了 50 个实体，哪些值得创建 Note？阈值怎么定？
- Link Generation 的候选检索用 embedding similarity，但阈值设多少？太高会漏链接，太低会生成噪音链接

**实施计划**

```
Week 1-2: MemGPT Paging 实现
  ├─ Day 1-3: Core data structures
  │   - MainContext (分区管理：System / Working / Recall / History)
  │   - ArchivalMemory (Vector DB backend)
  │   - PageTable (context 中的每个 message 映射到 archival id)
  │
  ├─ Day 4-6: Paging mechanism
  │   - retrieve_from_archival: LLM 自主触发 → 语义搜索 → 注入 Recall 区域
  │   - update_working_memory: LLM 自主编辑 Scratchpad
  │   - page_eviction: Context 满时，选择最不重要的 message 驱逐到 archival
  │
  ├─ Day 7-8: Integration with Agent Loop
  │   - 在 my-agent 的 loop.ts 中集成 MemGPT 式的 Paging
  │   - 测试：20 轮对话，观察 context 如何自动分页
  │
  └─ Day 9-10: Write tests + edge cases
      - 测试：context 满了但所有信息都重要 → 应该拒绝驱逐而非丢失
      - 测试：LLM 错误地 evict 了关键信息 → 能否从 archival 恢复？
      - 测试：连续 50 轮对话，memory 是否退化？

Week 3-4: A-MEM Pipeline 实现
  ├─ Day 1-4: Note Construction
  │   - Entity extraction (人名、项目名、文件名、决策点、错误类型...)
  │   - Fact extraction (对每个实体，提取独立的事实陈述)
  │   - Confidence annotation (CONFIRMED / OBSERVED / INFERRED / TENTATIVE)
  │   - Note 创建: {id, type, content, entities, confidence, timestamp, source}
  │
  ├─ Day 5-7: Link Generation
  │   - Candidate retrieval (embedding similarity top-K)
  │   - Link type classification (RELATES_TO / CONTRADICTS / EXTENDS / DEPRECATES / CAUSED_BY)
  │   - Bidirectional link creation
  │   - Optimization: 攒 5-10 个新 Note 批量做链接（减少 LLM 调用）
  │
  ├─ Day 8-9: Memory Evolution (后台任务)
  │   - Duplicate detection (embedding similarity > 0.95 → LLM confirm → merge)
  │   - Conflict detection (CONTRADICTS links → 标记而非自动删除)
  │   - Orphan cleanup (无链接的孤立 Note → LLM 判断是独立信息还是遗漏链接)
  │   - Decay (基于时间 + 访问频率的权重调整)
  │
  └─ Day 10: Integration + Demo
      - 写一个 demo: Agent 经历 20 轮对话后，Memory 自动组织了哪些笔记和链接？
      - 可视化: Note Graph（节点 = Note，边 = Link 类型）

Week 5: 对比分析
  ├─ 同一场景分别用 MemGPT 模式和 A-MEM 模式运行
  ├─ 对比指标:
  │   - 写入成本 (LLM tokens per new information)
  │   - 检索延迟 (time to find relevant memory)
  │   - 回忆质量 (precision/recall on memory QA)
  │   - 演化质量 (50 轮后 memory 的信息密度 vs 噪音比例)
  └─ 产出: 对比分析报告 + 开源代码
```

**预期产出**

- `agent-memory-core`: 一个 TypeScript/Python 包，实现 MemGPT Paging + A-MEM Pipeline
- 对比分析文章：《两种 Agent Memory 范式的代码级对比》
- 可复现的 benchmark 脚本

**关键设计决策点（写代码时必须回答的问题）**

1. Paging 的"驱逐策略"：FIFO vs LLM-judged vs Hybrid？什么时候用哪个？
2. Note 的"原子性"粒度：一个 Note 记一个事实还是记一组相关事实？
3. Link 的质量控制：如何避免 LLM 创建无意义的链接（如"都提到了 TypeScript"这种过于宽泛的链接）？
4. Evolution 的频率：多久运行一次 Memory Evolution？实时 vs 每 N 轮 vs 每天？

---

### 方向 2: Benchmark 数据（独立对比实验）

**目标**：自己设计并运行 Agent Memory 的对比实验，产出第一手数据。

**为什么这个方向重要**

本次 deep-research 的核心教训之一：**几乎所有量化性能主张都在对抗验证中被否决了。** —— Letta 74% vs Mem0 68.5%、A-MEM 2x improvement、FadeMem 82.1% retention……这些数字来自供应商自评或未复现的论文，不可信。

**要得出可信的结论，必须自己跑实验。**

**实验设计**

```
核心对比: Agentic RAG (检索时代理) vs Write-time Agency (写入时代理)

控制变量:
  - 同一个 LLM (Claude Sonnet 4)
  - 同一个 Vector DB backend (Chroma)
  - 同一个 embedding model (text-embedding-3-small)
  - 同一个测试数据集

变化变量:
  - 条件 A (Agentic RAG): 
    写入时 → 直接存原文 + embedding
    检索时 → LLM 自主 query reformulation + 多跳检索
    
  - 条件 B (Write-time Agency):
    写入时 → Note Construction + Link Generation (A-MEM 的 Stage 1-2)
    检索时 → Graph traversal + embedding search

测试场景 (5 个):
  1. 对话记忆: 30 轮对话后回答关于"用户之前说了什么"的问题 (10 QA pairs)
  2. 代码记忆: 跨多个 session 修改同一个项目，测试是否记得之前的修改 (5 tasks)
  3. 决策追踪: Agent 做了 10 个设计决策后，能否回溯"为什么做了这个决策" (5 QA pairs)
  4. 冲突检测: 注入 3 组矛盾信息 → 测试系统是否检测到并标记
  5. 长期演化: 100 轮对话后，Memory 质量是上升还是下降？

评估指标:
  - Precision@K, Recall@K, MRR (标准检索指标)
  - Multi-hop accuracy (需要连接 2+ 条记忆才能回答的问题)
  - Temporal accuracy (事件时序的准确性)
  - Write cost (每单位新信息的 Token 消耗)
  - Retrieval latency (找到相关信息的时间)
  - Memory quality evolution (Memory 中重复/过时/矛盾信息的占比随时间的变化)
```

**实施计划**

```
Week 1: 实验环境搭建
  - 准备测试数据集（5 个场景 × 若干 QA pairs）
  - 实现两种 Memory 模式的统一接口
  - 搭建评估框架（自动打分 + LLM-as-judge）

Week 2: 运行实验
  - 每个条件 × 每个场景 × 3 次重复（减少随机性）
  - 记录所有指标
  - 记录 qualitative 观察（"条件 A 在这个场景下出现了什么意外行为？"）

Week 3: 数据分析 + 撰写报告
  - 统计显著性检验
  - 分析失败案例（两种模式各自的典型失败模式）
  - 产出: 《Agentic RAG vs Write-time Agency: 独立 Benchmark 报告》

Week 4: 发布 + 开源
  - 开源 benchmark 框架（让其他人可以复现和扩展）
  - 发布报告
```

**关键约束**

- **成本**：完整实验估计需要 50-100K tokens 的 LLM 调用，约 $5-15（用 Sonnet）
- **诚实性**：实验设计必须预注册（preregister），不能看完结果再调整假设
- **局限声明**：实验使用 Claude Sonnet 4 而非所有模型，结论不能过度泛化

---

### 方向 3: AR 眼镜场景的定制化分析

**目标**：针对 AR 眼镜场景，做端侧 Memory 的约束分析和架构设计。

**为什么这个方向重要**

消费级 AR 眼镜的 Memory 系统有一个绝大多数 Memory 论文和开源项目不会涉及的约束：**端侧部署**。

AR 眼镜不是一个"有 GPU 集群的后台服务"——它是一个戴在脸上的嵌入式设备。Memory 系统必须在：
- 有限的 RAM（可能只有几百 MB 给 AI 用）
- 有限的存储（几十 GB 的 Flash）
- 有限的算力（TFLite/ONNX 推理，不是 A100）
- 严格的延迟要求（用户看着一个东西，不能等 2 秒才出结果）
- 严格的隐私要求（很多数据不能离设备）
- 混合架构（端侧 + 手机 + 云端协作）

这些约束下运行 Memory 系统。

**研究问题**

```
1. 端侧 Memory 的模型选择
   - 用什么模型做 embedding？（不能跑 text-embedding-3-large，太大了）
   - 用什么模型做 Note Construction？（不能用 Claude Opus，端侧跑不动）
   - 候选: all-MiniLM-L6-v2 (embedding, 22M params) + 端侧小 LLM (如 Llama-3.2-1B)

2. Memory 的分层部署架构
   - 什么数据留在端侧？（隐私敏感的、实时性要求高的）
   - 什么数据上传云端？（需要大模型处理的、需要跨设备同步的）
   - 端侧和云端 Memory 的同步策略？

3. 端侧 Memory 的存储约束
   - Vector DB 在端侧用什么？（Chroma 太大了 → SQLite + sqlite-vec？）
   - Memory 的存储上限？（用户用了 6 个月后，Memory 应该多大？）
   - 端侧的遗忘策略？（存储满了怎么办？）

4. 实时性约束下的 Memory 检索
   - 用户看着一个物体 → AR 眼镜需要 <500ms 内返回相关 Memory
   - Embedding search + LLM query理解 + Memory 结果注入 context
   - 整个流程必须在严格延迟预算内完成

5. 多模态 Memory
   - AR 眼镜的输入不只是文字——还有图像、空间位置、手势
   - 如何为"看到的东西"建立 Memory？
   - "上周四在这家咖啡店见过的那个人"——需要 temporal + spatial + visual memory
```

**产出**

- 《AR 眼镜端侧 Agent Memory 架构设计》——一份针对该类场景的技术方案
- 端侧 Memory 的约束模型（"在 X MB RAM 和 Y ms 延迟下，你能做到什么"）
- 如果时间允许：一个端侧 Memory 的简化原型（用 llama.cpp + SQLite + sqlite-vec）

**延伸价值**

这个方向对应端侧 AI 产品中典型的架构问题——"在严格资源约束下怎么设计 Memory？"——一份具体的、有约束分析的架构方案，比任何理论知识都更有说服力。

---

### 方向 4: Multi-Agent Memory 共享原型

**目标**：实现两个 Agent 共享 Memory 的系统原型，探索共享 Memory 的一致性和隔离问题。

**为什么这个方向重要**

当前几乎所有 Memory 系统都是单 Agent 的。但实际生产环境中，多个 Agent 需要协作（一个 Researcher、一个 Writer、一个 Reviewer）。Memory 共享是 Multi-Agent 系统中**尚未标准化**但**需求明确**的能力。

**研究问题**

```
1. Memory Namespace 设计
   - Private Memory: Agent 自己的记忆，其他 Agent 不可见
   - Shared Memory: 团队共享的记忆，所有 Agent 可读写
   - Read-only Shared Memory: 某些 Agent 只能读，不能写

2. Memory 一致性模型
   - 当 Agent A 写入一条 Memory，Agent B 多久能看到？
   - Eventual consistency (默认) vs Strong consistency (需要时)
   - 如果两个 Agent 同时写入冲突的信息，如何仲裁？

3. Memory Provenance (来源追溯)
   - 每条记忆标注: 来源 Agent、时间、置信度
   - Agent 在回忆时可以评估: "这条记忆来自 Researcher Agent 的推断，
     置信度 TENTATIVE，我应该标记这个不确定性"
   - 如果 Researcher 后来推翻了之前的推断，Writer 使用的 Memory 能自动更新吗？

4. 信息隔离 vs 信息共享的平衡
   - 什么信息应该共享？（事实、决策、用户偏好）
   - 什么信息应该隔离？（Agent 内部的推理过程、临时的假设）
   - 过度共享 → 噪音 + 隐私问题
   - 过度隔离 → 协作效率低
```

**原型设计**

```
场景: 技术报告协作系统

Agent 1 — Researcher:
  - 搜索资料、分析数据、整理发现
  - 写入 Shared Memory:
    - "发现: TypeScript strict mode 使 bug 率降低 15%" (confidence: HIGH, source: paper-X)
    - "发现: Deno 在 cold start 上比 Node.js 快 2x" (confidence: MEDIUM, source: benchmark-Y)
  - Private Memory:
    - "Benchmark Y 的测试方法可能有问题，需要进一步验证" (internal hypothesis)

Agent 2 — Writer:
  - 从 Shared Memory 获取 Researcher 的发现
  - 组织语言、生成报告
  - 写入 Shared Memory:
    - "报告草稿已完成，需要 Reviewer 审查第 3 节的数据部分"
  - Private Memory:
    - "Researcher 关于 Deno 的发现置信度只有 MEDIUM，决定在报告中标注为'初步发现'"

Agent 3 — Reviewer (可选):
  - 审查 Writer 的报告
  - 写入 Shared Memory:
    - "第 3 节: Deno benchmark 的引用需要补充原始来源"
    - 标记: "report-v1 → needs revision on section 3"
```

**实施计划**

```
Week 1: Memory Namespace 实现
  - 设计 namespace 模型: {agent_id}/{scope}/{memory_type}
  - 实现 ACL: 每个 namespace 的读写权限
  - 实现: Agent 写入时指定 scope (private/shared/readonly_shared)

Week 2: Consistency + Conflict Resolution
  - 实现 write 后立刻对自己可见 (read-your-writes)
  - 实现 shared memory 的 eventual consistency model
  - 实现 conflict marker: 两个 Agent 写入矛盾信息时不自动覆盖，
    而是标记 CONFLICT → 通知 Agents 或人工仲裁

Week 3: Provenance + Memory Lineage
  - 每条记忆追加 metadata: {source_agent, timestamp, confidence, based_on: [memory_ids]}
  - 实现: 如果 source memory 被更新，依赖它的 memories 自动标记为 "可能需要更新"
  - 实现: Memory 追溯——"这个结论是怎么得出的？→ 来自 Researcher 的发现 X，基于 paper Y"

Week 4: Demo + 文档
  - Demo: Researcher + Writer + Reviewer 三个 Agent 协作完成一篇技术报告
  - 文档: Multi-Agent Memory Sharing 设计文档
  - 分析: 有 Memory Sharing vs 没有的协作效率对比
```

**预期产出**

- `multi-agent-memory`: 开源原型
- 设计文档: 《Multi-Agent Memory Sharing: 设计空间与实现方案》
- 如果实验效果好：一篇技术博客

**关键设计决策点**

1. **Push vs Pull**：Researcher 的发现是主动 push 给 Writer，还是 Writer 在需要时 pull？
2. **Memory 的"新鲜度"**：Writer 怎么知道 Researcher 的发现是否还是最新的？
3. **Agent 之间的 Trust Model**：如果 Reviewer 对 Researcher 的可信度有疑虑，能否标记 Researcher 的 memory 为 "untrusted"？
