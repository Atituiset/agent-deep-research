# 第二章：Agent Memory 架构深度分析

## Memory 为什么是 Agent 的核心瓶颈

### 问题的本质

LLM 是**无状态函数**。给定 `(system_prompt, messages[], tools[])`，它输出 `(text | tool_calls)`。仅此而已。所有关于"Agent 记得什么"的复杂性，都必须在模型之外解决。

这意味着 Agent Memory 本质上是一个**外部状态管理系统**，它需要回答五个问题：

| 问题 | 传统系统类比 | Agent Memory 特殊性 |
|------|-------------|-------------------|
| **存什么** | 数据库 Schema 设计 | 信息由 LLM 生成，没有固定 Schema |
| **怎么存** | 存储引擎选择 | 需要在语义检索和精确查询之间找到平衡 |
| **何时存** | 写入触发条件 | LLM 自主决定 vs 外部规则触发 |
| **何时取** | 查询优化 | LLM 自主判断"我现在需要什么信息" |
| **何时忘** | 数据生命周期 | 遗忘比记住更难——如何判断一段信息不再需要？ |

### 三重不可能三角

Agent Memory 面临一个**不可能三角**——你只能同时满足两个：

```
          精确性
          (Precision)
           /\
          /  \
         /    \
        /  ✗   \
       /        \
      /__________\
  成本             灵活性
  (Cost)          (Flexibility)
```

- **精确 + 便宜**：硬编码规则（精确、零 LLM 成本），但完全不灵活
- **精确 + 灵活**：LLM 驱动的结构化知识图谱，但每次写入都要 LLM 调用
- **灵活 + 便宜**：关键词/向量检索（便宜、适用范围广），但精确度有限

**所有 Memory 架构本质上是在这个三角形中选一个位置。**

### Memory 系统的三个核心指标

```
1. 写入成本 (Write Cost)
   = LLM calls × tokens per call × model price
   范围: 0 (规则写入) → 数千 tokens (A-MEM 风格的笔记构建)

2. 检索延迟 (Retrieval Latency)
   = vector search latency + LLM re-rank latency + traversal latency
   范围: <100ms (简单向量搜索) → 数秒 (多跳 Agentic 检索)

3. 回忆质量 (Recall Quality)
   = f(precision, recall, temporal accuracy, multi-hop capability)
   范围: 低 (纯关键词匹配) → 高 (结构化图谱 + Agentic 检索)
```

这三个指标构成了 Memory 架构选择的**工程基础**。任何架构提案必须明确它在这三个维度上的取舍。

---

## 形式化 Memory 分类体系

当前文献缺乏统一的 Memory 分类法。基于研究综合分析，我提出以下五维分类框架：

### 维度一：时间跨度 (Temporal Span)

| 类型 | 生命周期 | 示例 | 存储需求 |
|------|---------|------|---------|
| **Working Memory** | 单次 Task | 当前推理的中间步骤 | Context Window 内 |
| **Short-term Memory** | 单次 Session（数小时） | 本次对话中的所有 user/assistant 轮次 | Context Manager 摘要 + 原始消息 |
| **Long-term Memory** | 跨 Session（天→年） | 用户偏好、项目知识、已学到的经验 | 持久化 Memory System |
| **Eternal Memory** | 永久 | 系统知识、API 文档、公司政策 | RAG 知识库（只读） |

### 维度二：信息类型 (Information Type)

继承心理学中的记忆分类，映射到 Agent 场景：

| 类型 | 心理学定义 | Agent 映射 | 数据结构 |
|------|-----------|-----------|---------|
| **Episodic** | 个人经历的事件 | "上周修复了 auth bug，用了 3 小时" | 时序事件记录 + 上下文快照 |
| **Semantic** | 事实和概念知识 | "TypeScript 的 strict mode 会影响..." | 结构化事实条目 |
| **Procedural** | 技能和流程 | "部署流程：npm run build → docker build → kubectl apply" | 工作流模板 |
| **Spatial** | 空间关系 | "src/components 在项目的 UI 层" | 文件/目录树、项目结构图谱 |

### 维度三：组织方式 (Organization)

```
扁平化 ◄──────────────────────────────► 高度结构化

Flat Text     Vector      KV Store    Relational    Graph
   │             │            │            │           │
   │             │            │            │           │
简单追加      语义相似      键值对       表格+外键    节点+边
```

每种组织方式的**精确查询能力**和**模糊查询能力**成反比：

| 组织方式 | 精确查询 | 模糊/语义查询 | 多跳推理 | 写入成本 |
|---------|---------|-------------|---------|---------|
| Flat Text | grep/keyword | ❌ | ❌ | 极低 |
| Vector | ❌ | ✅✅✅ | ❌ | 低（embedding） |
| KV Store | ✅ (by key) | ❌ | ❌ | 极低 |
| Relational | ✅✅✅ | ❌ | ✅ (JOIN) | 高（Schema 设计） |
| Graph | ✅✅ | ✅ (Node embedding) | ✅✅✅ | 极高（关系构建） |

### 维度四：代理权位置 (Agency Locus)

这是 MemGPT → A-MEM 演化的核心维度：

```
写入时代理 (Write-time Agency)
  模型自主决定: 是否记录、如何组织、与什么关联、何时更新/删除
  ─────────────────────────────────────────────────
  外部规则决定: 固定 Pipeline、定时触发、阈值规则
检索时代理 (Retrieval-time Agency)
  模型自主决定: 何时检索、检索什么 query、检索几轮、何时停止
  ─────────────────────────────────────────────────
  外部规则决定: 每次 user message 前固定检索 top-k、单一 query
```

**关键洞察**：代理权不需要全有或全无。最实用的系统往往在写入时用外部规则（确定性、低成本），在检索时给 LLM 代理权（灵活性、高价值）。

### 维度五：演化能力 (Evolvability)

| 级别 | 能力 | 代表系统 |
|------|------|---------|
| **Static** | 写入后不变 | 传统 RAG |
| **Versioned** | 支持版本控制 | Git-like Memory |
| **Adaptive** | 基于反馈调整权重 | FadeMem 式的衰减系统 |
| **Self-organizing** | 自主重组结构 | A-MEM |

---

## MemGPT：深入算法层面

> **论文**: [MemGPT: Towards LLMs as Operating Systems](https://arxiv.org/abs/2310.08560), UC Berkeley, 2023
>
> **置信度**: ★★★★★ High

### 不仅仅是类比——是实际的算法映射

MemGPT 不是把 OS 当作"灵感"，而是把 OS 虚拟内存的**实际机制**移植到了 LLM context 管理上。

传统 OS 虚拟内存的核心机制：

```
1. 地址空间: 进程看到连续的大地址空间（"虚拟"的）
2. 物理页面: 实际 RAM 被分割为固定大小的 page frames
3. 页表: 虚拟地址 → 物理地址的映射表
4. Page Fault: 访问的地址不在物理 RAM 中 → 触发中断 → OS 从磁盘加载
5. 页面置换: RAM 满时，选择"最不重要"的页面驱逐到磁盘 (LRU/Clock/etc)
```

MemGPT 的对应映射：

```python
# 伪代码：MemGPT 的 Paging 机制

class MemGPT:
    def __init__(self, context_window_size: int):
        self.main_context = []          # "Physical RAM" - LLM 实际看到的 context
        self.archival_storage = VectorDB()  # "Disk" - 外部持久化存储
        self.context_limit = context_window_size - 8192  # 留出 response buffer
    
    def handle_user_message(self, message: str):
        """每次用户消息触发的主流程"""
        
        # Step 1: 检查 main_context 是否有空间
        while self._estimate_tokens(self.main_context) > self.context_limit:
            # "Page eviction" - 把最不重要的内容写回 archival
            evicted = self.main_context.pop(self._select_fifo_slot())
            if evicted.is_important():
                self.archival_storage.insert(evicted.to_document())
        
        # Step 2: 追加新消息到 main_context
        self.main_context.append({"role": "user", "content": message})
        
        # Step 3: LLM 调用 - 模型可以自主决定使用 memory tools
        response = self._call_llm(self.main_context)
        
        # Step 4: 处理 LLM 的工具调用
        while response.has_tool_calls():
            for tool_call in response.tool_calls:
                if tool_call.name == "retrieve_from_archival":
                    # "Page-in" - 从 archival 加载到 main_context
                    results = self.archival_storage.search(tool_call.query)
                    self.main_context.append({
                        "role": "system",
                        "content": f"Retrieved: {results}"
                    })
                elif tool_call.name == "update_working_memory":
                    # LLM 自主编辑 working memory section
                    self._update_working_memory_section(tool_call.new_content)
            
            response = self._call_llm(self.main_context)
        
        return response.text
```

### 核心机制拆解

#### 1. Main Context 的内部结构

MemGPT 将有限的 context window 划分为多个**功能区域**，每个区域有不同的读写权限：

```
┌─────────────────────────────────────────────┐
│ System Prompt                    (~500 tok) │  ← 只读，cache
├─────────────────────────────────────────────┤
│ Persona Block                     (~200 tok) │  ← 只读，定义 Agent 角色
├─────────────────────────────────────────────┤
│ Human Block                       (~100 tok) │  ← 只读，定义用户角色
├─────────────────────────────────────────────┤
│ Working Memory / Scratchpad     (~1,500 tok) │  ← LLM 自主读写
│  (LLM 可以随时 call update_working_memory    │
│   来修改这一段——像一个草稿本)                  │
├─────────────────────────────────────────────┤
│ Recall Memory                    (~2,000 tok) │  ← 系统写入，LLM 只读
│  (从 Archival 检索到的结果放在这里)            │
├─────────────────────────────────────────────┤
│ Conversation History            (~4,000 tok) │  ← 追加写入
│  (最近的 user/assistant 消息)                 │
├─────────────────────────────────────────────┤
│ Response Buffer                  (~8,192 tok) │  ← 留给 LLM 输出
└─────────────────────────────────────────────┘
```

**这个分区设计是 MemGPT 最关键但最容易被忽视的部分**。它解决了"如何在有限的 context 中组织不同类型的信息"这个问题——这本质上是 Context Engineering，见第三章。

#### 2. "Page Fault" 的触发机制

在传统 OS 中，page fault 由硬件 MMU 自动触发。在 MemGPT 中，没有对等的"硬件"——需要 LLM 自己判断何时需要检索。

MemGPT 的做法：

```
策略 A: 被动检索 (Reactive)
  - LLM 在生成过程中，如果"感觉"需要更多信息
  - 生成一个 retrieve_from_archival tool call
  - 等价于: LLM 自己触发 page fault

策略 B: 主动检索 (Proactive)  
  - System Prompt 中指示 LLM: "在回答之前，先检查是否需要更多信息"
  - LLM 在回答之前先调用 retrieve_from_archival
  - 等价于: prefetch

策略 C: 外部触发 (External)
  - 外部代码检测到 context 中缺少关键信息 → 自动检索注入
  - 等价于: OS 的预取算法 (prefetching)
```

实际部署中，三种策略往往组合使用。**策略 C 是最被低估的**——很多系统过度依赖 LLM 自主判断，忽视了确定性规则的性价比。

#### 3. "Page Eviction" 的选择策略

当 main_context 满了，需要决定驱逐什么。MemGPT 支持多种策略：

| 策略 | 逻辑 | 适用场景 |
|------|------|---------|
| **FIFO** | 驱逐最早进入的消息 | 简单场景，信息价值随时间递减 |
| **LLM-judged** | LLM 判断每段信息的"重要性"，驱逐最不重要的 | 复杂场景，信息价值不均 |
| **Content-type priority** | System > Working > Recall > History 的优先级 | 大多数生产场景 |
| **Hybrid** | FIFO 驱逐 History，LLM-judged 压缩 Working | 推荐 |

#### 4. Working Memory 的自编辑机制

这是 MemGPT 最具创新性的设计之一——LLM 可以**自己编辑自己的 context**：

```
User: "帮我写一个 Python HTTP server"

# LLM 首先更新 Working Memory:
function_call: update_working_memory({
  new_content: """
  Task: 编写 Python HTTP server
  Constraints: 使用标准库, 支持 GET/POST, 错误处理
  Progress: 尚未开始
  Decisions: []
  Open Questions: [port 选择? 是否需要 threading?]
  """
})

# 然后 LLM 开始回答...
# 每次有新的决策或进展, LLM 可以再次更新 Working Memory
```

**为什么这很重要**：

- 传统 RAG：memory 内容由外部代码决定，LLM 只能被动消费
- MemGPT Working Memory：**LLM 自主维护一个结构化的任务状态**，在长对话中保持 focus

这类似于一个开发者在做复杂任务时，自己写 todo list 来跟踪进展。**这个能力使得 Agent 在处理超长任务时不会"忘记自己在做什么"。**

---

## A-MEM：深入算法层面

> **论文**: [A-MEM: Zettelkasten-Inspired Agent Memory](https://arxiv.org/abs/2502.12110), NeurIPS 2025
>
> **置信度**: ★★★★★ High

### Zettelkasten 的具体映射

卢曼的 Zettelkasten 方法有三条核心规则：

| Zettelkasten 规则 | A-MEM 映射 |
|-------------------|-----------|
| **原子性**：每张卡片只记一个想法 | 每个 Note 对应一个独立的实体/事件/决策 |
| **链接优先**：新卡片必须先与已有卡片建立链接 | Link Generation 阶段 LLM 遍历已有笔记寻找链接点 |
| **非线性**：不按分类目录组织，而是通过链接形成网络 | 检索时沿链接图谱遍历，而非按类别检索 |

### 四个阶段的详细算法

#### Stage 1: Note Construction（笔记构建）

```
输入: 一段新的对话/工具输出/外部信息
输出: 一个或多个结构化的 Note

算法:
1. 实体提取: LLM 从信息中提取关键实体
   - Person, Project, File, Decision, Error, Constraint...
   
2. 事实提取: 对每个实体，提取可独立成立的事实陈述
   - "User A prefers TypeScript strict mode"
   - "File X was modified to add retry logic"
   - "Decision: use serial tool execution to avoid race conditions"
   
3. 置信度标注: 对每个事实标注确定性
   - CONFIRMED: 用户明确陈述
   - OBSERVED: 从行为中观察
   - INFERRED: LLM 推理得出
   - TENTATIVE: 待确认
   
4. 时间戳: 记录信息的时间
   - occurred_at: 事件实际发生时间
   - observed_at: Agent 观察到的时间
   
5. 创建 Note 对象:
   {
     id: "note-2026-07-23-001",
     type: "decision",
     content: "Use serial tool execution to avoid race conditions",
     entities: ["my-agent", "tool-system"],
     confidence: "CONFIRMED",
     timestamp: "2026-07-23T10:30:00Z",
     source: "conversation-turn-15"
   }
```

**这一阶段的核心 tradeoff**：提取越详细，检索越精确；但提取越详细，写入成本（LLM tokens）越高。

#### Stage 2: Link Generation（链接生成）

```
输入: 新创建的 Note
输出: 与已有笔记的链接集合

算法:
1. 候选检索: 用新 Note 的 embedding 检索 top-K 相似已有笔记

2. LLM 链接判断: 对每个候选，LLM 判断是否存在有意义的链接
   链接类型:
   - RELATES_TO: 一般相关
   - CONTRADICTS: 与已有信息冲突
   - EXTENDS: 是对已有信息的补充/更新
   - DEPRECATES: 使旧信息过时
   - CAUSED_BY: 因果关系
   - PREREQUISITE_OF: 前置条件
   
3. 创建双向链接:
   Note_A.links.append({target: Note_B, type: "EXTENDS"})
   Note_B.backlinks.append({source: Note_A, type: "EXTENDED_BY"})
```

**这步是最贵的**——每个新 Note 都要 LLM 调用来判断链接。优化策略：
- 批量处理：攒 5-10 个新 Note 再一起做链接
- 低优先级信息跳过链接生成，仅做 embedding
- 用 smaller model 做链接判断（如果有足够好的小模型）

#### Stage 3: Memory Evolution（记忆演化）

```
周期性后台任务（非实时，降低写入路径延迟）:

1. 重复检测:
   - 找到 embedding 相似度 > 0.95 的 Note 对
   - LLM 判断是否真的是重复
   - 合并 + 保留更完整的版本 + 创建 MERGED_INTO 链接

2. 冲突检测:
   - 找到 CONTRADICTS 链接的 Note 对
   - LLM 判断哪个版本更新/更可靠
   - 标记旧版本为 SUPERSEDED

3. 孤岛清理:
   - 找到没有任何链接的孤立 Note
   - LLM 判断是真正独立的信息还是遗漏的链接
   - 如果是后者，补充链接

4. 衰减:
   - 长期未被访问的 Note 降低权重
   - 被 DEPRECATES 的 Note 压缩存储（仅保留摘要）
```

#### Stage 4: Retrieval（检索）

```
输入: 用户 query
输出: 相关信息集合

算法（混合检索）:
1. Embedding Search: query embedding → top-20 候选 Note
2. Graph Traversal: 从候选 Note 沿链接遍历 k-hop
   - 1-hop: 直接关联的信息
   - 2-hop: 间接关联（如通过同一实体连接）
3. LLM Re-rank: LLM 对候选 Note 进行相关性排序
4. Context Assembly: 将排序后的 Note 组合成适合 context window 的格式
```

### A-MEM 的深层设计决策

**为什么要把代理权放在写入时？**

这不是一个随意的选择。A-MEM 的基本假设是：

> 写入时比检索时有更多的**信息**来做正确的事。

具体来说：

| | 写入时 | 检索时 |
|---|--------|--------|
| **可用信息** | 完整的对话上下文 + 刚发生的事情 | 只有用户的 query |
| **时间压力** | 低（可以异步） | 高（用户等待响应） |
| **LLM 质量要求** | 中等（非实时路径） | 高（直接影响用户体验） |
| **错误可恢复性** | 高（后续 Evolution 可以修正） | 低（检索结果直接给用户） |

**这个设计的反直觉之处**：它在写入时花了更多 Token（用 LLM 构建笔记+链接），但整体可能更经济——因为写入时的高质量组织使得检索时更便宜、更准确。

---

## 文献中 5 个最深刻的 Memory 设计原则

基于 MemGPT、A-MEM、FadeMem 以及被否决但仍有启发的主张，我提炼出以下原则：

### 原则 1: "把决策权放在信息最完整的地方"

MemGPT 在检索时给 LLM 代理权（因为 LLM 理解当前 query 的完整上下文）。A-MEM 在写入时给 LLM 代理权（因为写入时 LLM 理解信息的完整上下文）。两者不矛盾——它们都在应用同一条原则。

**启示**：不要在所有环节都给 LLM 代理权（成本爆炸），也不要所有环节都用固定规则（缺乏灵活性）。在信息最完整、时间最充裕的环节给代理权。

### 原则 2: "Memory 系统应该像活的组织，而非死的仓库"

A-MEM 的 Memory Evolution 阶段（自动合并、衰减、强化链接）体现了这一点。静态存储的问题在于：信息的**意义**随时间变化。昨天重要的决策可能今天被推翻了，但静态存储不会自动反映这一点。

**启示**：Memory 系统需要后台的"维护进程"——检测重复、解决冲突、衰减旧信息、强化重要链接。这不应该是用户或 Agent 手动触发的。

### 原则 3: "遗忘是实现可扩展 Memory 的前提"

FadeMem 的核心洞察。如果不遗忘，Memory 会无限增长。但遗忘不能是简单的 LRU——信息的"重要性"不是时间的简单函数。

**启示**：遗忘策略应该是**多维的**（时间、访问频率、语义重要性、情感权重），而不是单维的 LRU。并且遗忘不等于删除——可以压缩存储（保留摘要，丢弃细节）。

### 原则 4: "存储结构的选择不如 Agent 如何使用它重要"

Letta Benchmark 的方向性观察（具体数字被否决，但方向有价值）：GPT-4o-mini + 纯文件系统的组合在某些场景下接近专用 Memory 系统。关键差异不在于存储引擎，而在于 Agent 的 tool-use 能力——它是否知道如何有效地迭代查询、纠错、多跳搜索。

**启示**：花时间优化 Agent 的 Memory tool-use prompt 和策略，可能比花时间选择/迁移存储后端更有价值。

### 原则 5: "Memory 的正确性比完整性更重要"

一条错误但完整的记忆 > 十条正确但孤立的片段。Memory 冲突（两条记忆矛盾）比 Memory 缺失（记不起来）危害更大——因为它会导致 Agent 基于错误信息行动。

**启示**：Memory 系统应该：
- 优先存储高置信度信息，标记低置信度信息
- 主动检测冲突并标记（而非自动选择一边）
- 提供"Memory 来源追溯"——Agent 被告知"这条记忆来自 turn 15 的用户陈述"

---

## Memory 一致性问题

这是当前文献几乎完全忽视的维度，但它是生产系统的关键。

### Agent Memory 的一致性模型

借鉴分布式系统的一致性模型：

| 模型 | 定义 | Agent Memory 映射 |
|------|------|------------------|
| **Strong consistency** | 写入后立即可读 | 同步写入 memory，阻塞等待确认 |
| **Eventual consistency** | 写入后最终可读 | 异步写入，检索时可能看不到刚写入的内容 |
| **Read-your-writes** | 自己的写入对自己可见 | 同一 Agent 的写入在自己的 session 中可见 |
| **Monotonic reads** | 不会看到"回退" | 不会出现检索结果越来越少的情况 |
| **Causal consistency** | 因果相关的操作按序可见 | Memory 更新按因果顺序体现 |

### 生产环境中的具体问题

**问题 1: 写入-检索时间窗**

```
Agent: remember("User prefers TypeScript strict mode")  // 异步写入
Agent: recall("User TypeScript preferences")              // 可能返回空（还没写入）
```

解决方案：
- 同步写入 + read-your-writes 保证（同一 session 内）
- 写入请求立即进入 Agent 的 working memory（不等 archival 确认）

**问题 2: 多 Agent 并发写入冲突**

```
Agent A: remember("Deploy uses Docker")
Agent B: remember("Deploy uses Kubernetes")  // 同时写入
```

解决方案：
- Last-write-wins + 冲突标记（标记两段信息不一致，让人或 LLM 仲裁）
- Agent-specific namespace（每个 Agent 有独立 memory 空间 + 共享只读空间）

**问题 3: Memory 回滚**

```
Agent: remember("Production deploy succeeded")
// 10 分钟后发现部署实际上失败了
Agent: 需要"撤回"刚才的记忆
```

解决方案：
- 不删除，追加一条 CONTRADICTS 链接的记忆
- Versioned memory（支持 checkout 到特定时间点的 memory 状态）

---

## Memory 评估方法的批判性分析

### 当前 Benchmark 的问题

研究过程中，大量关于具体性能数字的主张被否决。这暴露了当前 Memory 评估方法的系统性缺陷：

| 问题 | 影响 | 示例 |
|------|------|------|
| **单一数据集** | 结论不可泛化 | LoCoMo 对对话场景友好，对代码场景不适用 |
| **供应商自评** | 利益冲突 | Letta 的 benchmark 同时测试 Letta |
| **指标不统一** | 无法比较 | 论文 A 用 F1，论文 B 用 Accuracy，论文 C 用 NDCG |
| **Agent 配置敏感性** | 细微差异影响巨大 | Prompt/温度/Tool description 的微小变化改变结论 |
| **缺乏长期评估** | 无法测演化能力 | Memory 系统的质量需要长期使用才能体现 |

### 一个更好的评估框架（提案）

```
Memory 系统评估应该覆盖以下维度:

1. 单轮检索质量
   - Precision@K, Recall@K, MRR, NDCG
   - 在多个数据集上测试（对话、代码、知识问答）

2. 多跳推理能力
   - 需要连接 2+ 条记忆才能回答的问题
   - 测试 Memory 组织方式对推理的支持程度

3. 时间准确性
   - "上周做了什么?" "在改 auth 之前还是之后?"
   - 测试 Memory 的时间维度组织

4. 冲突处理
   - 注入矛盾信息 → 观察系统如何响应
   - 是否检测冲突？如何呈现给 Agent？

5. 演化质量
   - 长期运行（100+ turns）后，Memory 质量是上升还是下降？
   - Memory 是否自动清理了重复/过时信息？

6. 成本效率
   - 每单位回忆质量的 Token 成本
   - 写入成本 vs 检索成本 的平衡
```

---

## 生产 Memory 系统的架构蓝图

基于以上所有分析，这里是一个生产级 Agent Memory 系统的推荐架构：

```
                        ┌──────────────────┐
                        │   Agent Loop     │
                        │   (Runtime)      │
                        └────────┬─────────┘
                                 │
                ┌────────────────┼────────────────┐
                │                │                │
                ▼                ▼                ▼
        ┌──────────────┐ ┌──────────────┐ ┌──────────────┐
        │ Write Path   │ │ Read Path    │ │ Evolution    │
        │ (同步/异步)   │ │ (实时)       │ │ (后台)       │
        └──────┬───────┘ └──────┬───────┘ └──────┬───────┘
               │                │                │
               ▼                ▼                ▼
        ┌──────────────────────────────────────────────┐
        │              Memory Core                     │
        │                                              │
        │  ┌──────────┐  ┌──────────┐  ┌──────────┐  │
        │  │ Working  │  │ Episodic │  │ Semantic │  │
        │  │ Memory   │  │ Store    │  │ Store    │  │
        │  │(Context) │  │(Events)  │  │(Facts)   │  │
        │  └──────────┘  └──────────┘  └──────────┘  │
        │                                              │
        │  ┌──────────────────────────────────────┐   │
        │  │        Link Graph (Relations)         │   │
        │  └──────────────────────────────────────┘   │
        │                                              │
        │  ┌──────────────────────────────────────┐   │
        │  │   Conflict Detector & Resolver        │   │
        │  └──────────────────────────────────────┘   │
        └──────────────────────────────────────────────┘
                         │
                         ▼
        ┌──────────────────────────────────────────────┐
        │           Storage Backend                    │
        │  (Vector DB + Doc Store + Graph DB)          │
        └──────────────────────────────────────────────┘
```

**关键设计决策**：

1. **Write Path 分离**：Working Memory 同步写入（保证 read-your-writes），Episodic/Semantic 异步写入（降低 Agent Loop 延迟）
2. **Evolution 独立**：Memory 演化（重复检测、冲突解决、衰减）是独立的后台进程，不在 Agent Loop 的关键路径上
3. **Conflict Detector 是第一等公民**：不是可选功能，而是架构内置组件
4. **多模态存储**：不是选择一个存储引擎，而是按信息类型使用不同的存储（Working → Context、Episodic → Doc Store、Semantic → Vector + Graph、Relations → Graph）

---

## 小结

Agent Memory 不是 RAG 的简单扩展，它是一个新的系统工程领域。核心挑战不在于"选什么 Vector DB"，而在于：

1. **代理权分配**：在写入时和检索时之间，如何分配 LLM 的自主决策权
2. **信息组织**：如何让 Memory 成为一个"活"的系统，能自我演化而非只是堆积
3. **一致性保证**：在多 Agent、多 Session、并发写入的情况下如何保持 memory 的可靠性
4. **遗忘机制**：如何选择性地遗忘以保持 memory 的可扩展性和质量

**一到两年内会被广泛接受但今天还未被充分理解的观点**：Agent Memory 最终会收敛到类似数据库的 ACID 保证级别——可审计、可回滚、一致性可配置。
