# 第三章：Context Engineering

## 定义与边界

**Context Engineering** 是对 LLM context window 内容的系统性设计和优化。它不是 Prompt Engineering——后者关注"写什么"，前者关注"在有限空间内放什么、怎么放、放多少、以及什么时候换掉"。

### 与相邻领域的区分

```
                    Context Engineering
                    (窗口内信息的布局与生命周期)
                         │
         ┌───────────────┼───────────────┐
         │               │               │
         ▼               ▼               ▼
    Prompt           Memory          Token
  Engineering       System          Economics
 ("写什么")      ("记住什么")      ("花多少钱")
```

Context Engineering 是 Prompt Engineering 和 Memory System 之间的**桥梁**——Memory 决定"哪些信息可用"，Context Engineering 决定"这些信息中哪些放进当前窗口、以及以什么形式放进去"。

---

## Token 经济学：深入成本模型

### 不同模型的Token成本结构

以 2025 年中的主流模型为示例（价格随模型迭代变化，成本结构不变）：

| 模型 | Context Window | Input $/1M tokens | Output $/1M tokens | Cache Read $/1M |
|------|---------------|-------------------|-------------------|-----------------|
| Claude Opus 4 | 200K | $15.00 | $75.00 | $1.50 |
| Claude Sonnet 4 | 200K | $3.00 | $15.00 | $0.30 |
| GPT-4o | 128K | $2.50 | $10.00 | $1.25 |
| Gemini 2.5 Pro | 1M | $1.25 | $10.00 | $0.16 |

### 长对话的成本增长分析

假设一个 20 轮的 Agent 对话（每轮 1 个 user message + 1 个 assistant response + 平均 1 个 tool call）：

```
策略 A: 全量历史（不压缩）
  每轮 context 大小: 2K (sys) + N*1.5K (历史每轮) + 1K (当前)
  第 20 轮 context: 2K + 30K + 1K = 33K tokens
  
  Total input tokens: Σ(2K + k*1.5K) for k=1..20
                    = 20*2K + 1.5K*20*21/2
                    = 40K + 315K = 355K input tokens
  成本 (Sonnet): 355K * $3/1M = $1.07

策略 B: 摘要 + 最近 4 轮（my-agent 默认）
  Summary 大小: ~3K tokens（覆盖 16 轮）
  每轮 context: 2K (sys) + 3K (summary) + min(N,4)*1.5K (recent) + 1K (current)
  第 20 轮 context: 2K + 3K + 6K + 1K = 12K tokens
  
  Total input tokens ≈ 20 * 12K = 240K input tokens
  成本 (Sonnet): 240K * $3/1M = $0.72
  
  节省: 32%

策略 C: 策略 B + Prompt Caching
  Cached prefix: System Prompt + Tool Defs + Summary prefix ≈ 5K
  每轮新增 input: 12K - 5K(cached) = 7K (full price)
  5K cache read: $0.30 → $0.0015 per round
  
  Total cost: 20 * (7K*$3/1M + $0.0015) = 20 * ($0.021 + $0.0015) = $0.45
  
  节省: 58% vs 全量历史
```

### 关键洞察

1. **摘要压缩不是免费的**：摘要生成本身消耗 Token（调用 Haiku 做摘要大约需要 2-5K tokens 输入 + 500 tokens 输出），但这个成本是**一次性**的（摘要一次，省 N 轮）
2. **Prompt Caching 改变了最优策略**：有了 caching，你应该**尽可能把不变的内容放在前缀**（System Prompt、Tool Defs、固定的背景信息），因为 cache hit 的成本只有原文的 10%
3. **最优摘要频率**：不是"每次超限就摘要"，而是"每 M 轮摘要一次"——M 取决于 Token 节省 vs 摘要成本

### 摘要频率的数学优化

```
设:
  n = 总轮次
  m = 摘要间隔（每 m 轮摘要一次）
  C_summary = 单次摘要的 Token 成本 (~500 tokens 输入 + 200 tokens 输出)
  C_per_turn = 每轮不摘要时 context 增长量 (~1.5K tokens)

不摘要时的累计成本: Σ(k*C_per_turn) for k=1..n = O(n²)
每 m 轮摘要时的累计成本:
  - 摘要成本: (n/m) * C_summary
  - Context 成本: n * (summary_size + m*C_per_turn)
  - 总计: O(n*m + n²/m)

当 n=20, m=4, C_per_turn=1.5K, C_summary=0.7K:
  不摘要: ~355K tokens
  m=4: ~240K tokens (节省 32%)
  m=2: ~260K tokens (摘要太频繁)
  m=8: ~290K tokens (摘要不够频繁)

最优 m 取决于:
  - 对话的信息密度（信息密度高 → m 应该更小，因为旧信息快速过时）
  - 摘要模型的质量（摘要质量高 → m 可以更小，因为摘要信息密度高）
```

---

## 摘要压缩的深入分析

### 摘要质量的量化

一个好的摘要应该满足三个属性：

```
1. 完整性 (Completeness)
   = 摘要中保留的关键信息 / 原始对话中的关键信息
   目标: >90%

2. 简洁性 (Conciseness)  
   = 摘要 Token 数 / 原始对话 Token 数
   目标: <15%

3. 准确性 (Accuracy)
   = 摘要中不存在的幻觉 / 摘要中的所有陈述
   目标: <1%
```

### 摘要策略的类型学

| 策略 | 机制 | 完整性 | 简洁性 | 准确性 | 成本 |
|------|------|--------|--------|--------|------|
| **Simple Truncation** | 丢弃最老的消息 | 0%（完全丢失） | 上限固定 | 100% | 0 |
| **Extractive Summary** | 从原文中选取最重要的句子 | 60-80% | 20-30% | 100% | 低 |
| **Abstractive Summary** | LLM 重新生成摘要 | 80-95% | 5-15% | 95-99% | 中 |
| **Structured Summary** | LLM 按模板生成摘要 | 85-95% | 5-10% | 97-99% | 中高 |
| **Hierarchical Summary** | 多层次摘要（粗粒度→细粒度） | 90-98% | 3-8% | 95-99% | 高 |

### 结构化摘要模板（生产级）

基于 my-agent 的实践和改进：

```markdown
## Context Summary (Turns {{start}}-{{end}})

### Files Modified (按操作类型分组)
| File | Operation | Reason | Turn |
|------|-----------|--------|------|
| src/loop.ts | MODIFIED | Added retry logic for tool calls | 5 |
| src/context.ts | MODIFIED | Changed maxContextTokens default | 6 |
| test/context.test.ts | CREATED | 12 unit tests for ContextManager | 8 |

### Commands Executed (按模块分组)
| Command | Exit Code | Key Output | Turn |
|---------|-----------|------------|------|
| npm test | 0 | 12/12 passed | 8 |
| tsc --noEmit | 1 | 3 type errors (see Errors) | 10 |

### Key Decisions (用户 + Agent 共同决策)
1. [Turn 4] 工具执行策略: 串行而非并行
   Reason: 工具有文件系统副作用，并行可能导致竞态条件
2. [Turn 7] Token 估算方案: chars/4 而非 tiktoken
   Reason: 避免 15MB 依赖，chars/4 对于预算控制的精度足够

### Errors & Resolutions
1. [Turn 10] TypeScript error: 'ToolResult.error' can be undefined
   Fix: Added type guard in loop.ts:165
2. [Turn 15] API timeout (120s) on large context call
   Fix: Reduced maxContextTokens from 120K to 100K

### Open Items (未解决的问题)
- ContextManager 需要添加 compaction 触发条件的单元测试
- Trace JSON 文件增长太快，需要 rotation 策略

### Agent's Self-Reflection (Agent 对自己的评估)
- 本次 Session 效率: 高（20 hops 完成预计 30 hops 的任务）
- 需要改进: 工具描述可以更精确（bash 工具需要更清晰的超时说明）
```

### 摘要质量的验证方法

```python
def validate_summary(original_messages, summary, validation_prompt):
    """
    用 LLM 验证摘要质量
    """
    validation = llm.call(f"""
    Given:
    - Original conversation: {original_messages}
    - Generated summary: {summary}
    
    Answer:
    1. Completeness: Are there any critical facts in the original that are 
       missing from the summary? List them.
    2. Accuracy: Are there any statements in the summary that are 
       NOT supported by the original? List them.
    3. Decision Preservation: Are all key decisions from the original 
       preserved in the summary? If any are missing, list them.
    """)
    
    return {
        "completeness_score": 1 - len(validation.missing_facts) / len(all_critical_facts),
        "accuracy_score": 1 - len(validation.hallucinations) / len(summary_statements),
        "decision_preservation": len(validation.preserved_decisions) / len(all_decisions),
    }
```

**成本考虑**：这个验证步骤本身消耗 Token，不建议每次都做。建议的使用场景：
- 每 20 次摘要做一次抽样验证
- 在发现 Agent 行为异常时（可能是摘要丢失了关键信息）
- 在引入新的摘要策略时做 A/B 对比

---

## Prompt Caching 的进阶策略

### Cache 边界设计

Prompt Caching 的核心约束是：**只有连续的前缀才能被缓存**。这意味着你需要把"不变的"内容放在最前面。

```
可以缓存的前缀：
┌─────────────────────────────────────────┐
│ [System Prompt]        ← cache point 1  │
│ [Tool Definitions]     ← cache point 2  │
│ [Static Knowledge]     ← cache point 3  │
├─────────────────────────────────────────┤ ← cache 边界
│ 以下内容不可缓存（每轮变化）              │
│ [Summary Block]                         │
│ [Recent Messages]                       │
│ [User Input]                            │
└─────────────────────────────────────────┘
```

**设计原则**：

1. **System Prompt 精简化**：把"应该缓存"的内容（角色、工具定义、静态知识）放在 System Prompt 中
2. **动态指导分离**：把"每轮可能变化"的指导放在 Summary 和 Recent Messages 中
3. **Tool Description 独立管理**：工具的描述比工具本身更影响缓存效率——因为 Tool Description 占用 cacheable 前缀空间

### Cache 失效的成本

缓存有 TTL（5 分钟或 1 小时），失效后需要重建：

```
Cache 命中的对话: 
  每轮成本 = cache_read_cost(前缀) + full_cost(新增部分)

Cache 失效时（>5min 间隔）:
  每轮成本 = full_cost(前缀) + full_cost(新增部分)
  → 第一轮多花了 ~$0.01-0.03 (取决于前缀大小)
  
策略:
  - 高频交互（<5min 间隔）→ ephemeral_5m cache
  - 间歇交互（>5min, <1h）→ ephemeral_1h cache
  - 低频交互（>1h）→ 不值得缓存，或使用 Summary 来弥补
```

### 多级缓存架构

```
L1 Cache: System Prompt + Tool Defs
  TTL: 5 min (ephemeral_5m)
  大小: 2-5K tokens
  命中率: 80-95% (同一 session 内连续调用)

L2 Cache: Static Knowledge Base
  TTL: 1 hour (ephemeral_1h)
  大小: 5-20K tokens
  命中率: 50-70% (跨 session, 同一天内)

L3 Cache: Session Context (实验性)
  TTL: Session 生命周期
  大小: 3-10K tokens
  实现: 自定义缓存层（非 Anthropic 原生支持）
  方案: 将 Session 的 Summary + Key Context 存储在外部，每次新 session 注入
```

---

## Context Window 布局策略

### 信息布局对 LLM 表现的影响

[Lost in the Middle](https://arxiv.org/abs/2307.03172) 现象已经被多项研究验证：LLM 对 context 中不同位置的信息，回忆准确率不同：

```
Context Window 中信息位置 vs 回忆准确率:

  准确率
  100% │  ████                 ████
   80% │  ████                 ████
   60% │  ████     ░░░░       ████
   40% │  ████     ░░░░       ████
   20% │  ████ ░░░░░░░░░░ ░░ ████
    0% │─────────────────────────────
       0%     25%     50%     75%    100%
              信息在 Context 中的位置

  ████ = 高回忆率 (开头 10% + 结尾 20%)
  ░░░░ = 低回忆率 (中间 50-70%)
```

**这意味着什么**：

- System Prompt（开头）→ 高回忆 → 放最重要的行为约束
- 对话历史（中间）→ 低回忆 → 放摘要而不是详细历史
- 最新信息（结尾）→ 高回忆 → 放当前任务上下文

### 推荐的 Context 布局

```
┌─────────────────────────────────────────┐
│ System Prompt                            │ ← 高回忆区 (开头)
│ [角色, 约束, 安全规则]                    │
├─────────────────────────────────────────┤
│ Tool Definitions                         │ ← 高-中回忆区
│ [工具名称, 描述, 参数 schema]             │
├─────────────────────────────────────────┤
│ Session Summary                          │ ← 中回忆区
│ [关键决策, 文件修改, 错误, 进展]          │
├─────────────────────────────────────────┤
│ Working Memory                           │ ← 中回忆区（但可能被 LLM 关注）
│ [当前任务状态, 待办, 约束, 假设]          │
├─────────────────────────────────────────┤
│ Recent Messages (最近 4-6 轮)            │ ← 中-高回忆区
│ [原始 user/assistant/tool_result 对]     │
├─────────────────────────────────────────┤
│ Current User Input                       │ ← 最高回忆区 (结尾)
│ [当前 query 或 tool result]              │
└─────────────────────────────────────────┘
```

### 位置敏感的 Tool Result 注入

当 Memory 检索到信息需要注入 context 时：

```
❌ 错误做法: 直接 append 到末尾
   → 打乱了 "Recent → Current" 的连贯性
   → LLM 可能把检索结果当作新的用户输入

✅ 正确做法: 插入到 System Prompt 后面 (Recall Memory 区域)
   → 不影响对话连贯性
   → LLM 明确知道这是"检索到的背景信息"
   → 处于高-中回忆区

示例:
System: ... (system prompt)
System: [Retrieved Memory] The user previously mentioned preferring 
        TypeScript strict mode. This preference was confirmed in 
        a conversation on 2026-07-15.
System: ... (tool definitions)
User: What settings should I use for my new project?
```

---

## Context 污染与防御策略

### 污染的来源

```
1. Tool Output 噪音
   - 大日志文件中 99% 都是无关内容
   - Shell 输出的 ANSI color codes
   - 长文件读取中包含不相关的部分

2. 重复信息
   - 多次调用同一工具，返回类似结果
   - LLM 在每轮 assistant message 中重复之前的内容

3. 过时信息
   - 早期的 tool result 已被后续操作推翻
   - 但仍在 recent messages 中

4. Prompt 膨胀
   - 随着功能增加，System Prompt 越来越长
   - "那就再加一段指导"
```

### 防御策略

```python
class ContextHygiene:
    """Context 卫生管理"""
    
    def sanitize_tool_output(self, output: str, max_len: int = 5000) -> str:
        """净化工具输出"""
        # 1. 移除 ANSI escape codes
        output = re.sub(r'\x1b\[[0-9;]*m', '', output)
        
        # 2. 截断过长的输出
        if len(output) > max_len:
            head = output[:int(max_len * 0.7)]
            tail = output[-int(max_len * 0.3):]
            output = f"{head}\n[... {len(output) - max_len} chars omitted ...]\n{tail}"
        
        # 3. 提取关键信息（如果能识别）
        errors = re.findall(r'(Error|Exception|FAILED|FATAL).*', output)
        if errors:
            output += f"\n\n[Auto-detected {len(errors)} error(s) in output]"
        
        return output
    
    def deduplicate_tool_results(self, recent_results: list) -> list:
        """去重相似的工具结果"""
        seen_hashes = set()
        deduped = []
        for result in recent_results:
            h = hash(result.content[:100])  # 前 100 字符的 hash
            if h not in seen_hashes:
                seen_hashes.add(h)
                deduped.append(result)
            else:
                deduped.append({**result, "content": "[Duplicate of previous result]"})
        return deduped
    
    def detect_context_rot(self, context: list) -> float:
        """检测 context 的信息衰减程度"""
        # 指标 1: 重复信息占比
        # 指标 2: 过时 tool result 数量（在后续操作中被推翻）
        # 指标 3: System Prompt 膨胀度
        # 返回 0-1 的 rot score
        
        total_tokens = estimate_tokens(context)
        system_tokens = estimate_tokens(context[0])  # System prompt
        summary_tokens = estimate_tokens(context.get('summary', ''))
        
        rot_score = system_tokens / total_tokens  # System prompt 占比过高意味着实际信息比例低
        return min(rot_score * 3, 1.0)  # 归一化
```

---

## 高级主题：Context 可编程性

### Context 作为一种"可编程资源"

一个前沿但有实际价值的视角：把 Context Window 当作一种**可编程资源**（类似 GPU 显存），由 Runtime 进行精细的分配和调度。

```python
class ContextAllocator:
    """
    将 Context Window 视为可编程资源
    """
    
    def __init__(self, window_size: int = 200_000):
        self.window = window_size
        self.allocations = {
            'system': Allocation(min=1000, max=5000, priority=Priority.CRITICAL),
            'tools': Allocation(min=500, max=3000, priority=Priority.HIGH),
            'summary': Allocation(min=1000, max=20000, priority=Priority.HIGH),
            'working_memory': Allocation(min=500, max=10000, priority=Priority.MEDIUM),
            'recent_messages': Allocation(min=2000, max=40000, priority=Priority.MEDIUM),
            'retrieved_memory': Allocation(min=0, max=15000, priority=Priority.LOW),
            'response_buffer': Allocation(min=4096, max=16384, priority=Priority.CRITICAL),
        }
    
    def allocate(self, request: dict):
        """
        根据当前任务特征动态分配窗口空间
        
        示例: 如果是代码生成任务 → 减小 recent_messages, 增大 working_memory
              如果是对话总结任务 → 增大 recent_messages, 减小 working_memory
        """
        task_type = self._detect_task_type(request)
        
        if task_type == 'code_generation':
            self.allocations['working_memory'].max = 20000
            self.allocations['recent_messages'].max = 20000
        elif task_type == 'conversation':
            self.allocations['recent_messages'].max = 50000
            self.allocations['working_memory'].max = 5000
        
        # 分配逻辑...
```

### 这个方向为什么重要

随着 Agent 从 demo 走向生产，Context Window 的精细管理会越来越重要。就像数据库需要 Buffer Pool Manager、操作系统需要 Memory Manager——Agent Runtime 需要 **Context Manager** 作为一等公民。

这不是一个"加个摘要就够了"的问题，而是一个需要系统性设计的子系统。
