# 第四章：Agent Runtime 设计模式

## Agent Loop 的状态机分析

### 从"循环"到"状态机"

大多数 Agent 框架把 Agent Loop 实现为一个简单的 `while` 循环。但生产级的 Agent Runtime 应该被建模为一个**有限状态机（FSM）**。

```
                    ┌─────────────────────────────────────┐
                    │                                     │
                    ▼                                     │
            ┌──────────────┐                              │
            │   IDLE       │                              │
            │  (等待输入)   │                              │
            └──────┬───────┘                              │
                   │ user_message                         │
                   ▼                                      │
            ┌──────────────┐                              │
            │ CONTEXT_PREP │  ← 摘要压缩 / Token 预算检查  │
            └──────┬───────┘                              │
                   │                                      │
                   ▼                                      │
            ┌──────────────┐                              │
            │  LLM_CALL    │                              │
            └──────┬───────┘                              │
                   │                                      │
        ┌──────────┴──────────┐                           │
        ▼                     ▼                           │
   text_output           tool_calls                       │
        │                     │                           │
        ▼                     ▼                           │
   ┌──────────┐        ┌──────────────┐                   │
   │ STREAM   │        │ TOOL_EXEC    │                   │
   │ _RESPONSE│        └──────┬───────┘                   │
   └────┬─────┘               │                           │
        │              ┌──────┴──────┐                    │
        │              ▼             ▼                    │
        │        tool_success   tool_error                │
        │              │             │                    │
        │              ▼             ▼                    │
        │        ┌──────────┐ ┌──────────────┐           │
        │        │ RESULT   │ │ ERROR_HANDLE │           │
        │        │ _INTEGRATE│ │ (retry/abort)│           │
        │        └────┬─────┘ └──────┬───────┘           │
        │             │              │                    │
        │             ▼              ▼                    │
        │        ┌────────────────────────┐               │
        └───────▶│   CHECK_END_CONDITION  │               │
                 └───────────┬────────────┘               │
                             │                            │
                   ┌─────────┴─────────┐                  │
                   ▼                   ▼                  │
              end_turn            continue                │
              (输出结果)          (回到 LLM_CALL)           │
                   │                   │                  │
                   ▼                   └──────────────────┘
            ┌──────────────┐
            │   IDLE       │
            └──────────────┘
```

### 为什么状态机优于简单循环

| 维度 | 简单 while 循环 | 状态机 |
|------|----------------|--------|
| **暂停/恢复** | 需要额外实现 | 天然支持（保存当前 state） |
| **可观测性** | 需要额外埋点 | 每次状态转换都是天然的 trace point |
| **并发** | 难以支持 | 可以定义并发状态转换规则 |
| **回滚** | 几乎不可能 | 可以回到之前的状态 |
| **测试** | 需要 mock 整个循环 | 可以单独测试每个状态 |

LangGraph 的设计哲学正是基于这个洞察——它把 Agent 的执行建模为**有向图上的状态转换**。

### 状态的详细定义

```
State: CONTEXT_PREP
  触发: user_message 到达
  动作:
    1. 估算当前 context 的 token 数
    2. 如果超过预算 → 触发 compaction (摘要压缩)
    3. 如果 compaction 失败 → 降级为 truncation (直接丢弃旧消息)
    4. 应用 Prompt Caching 策略
  转换:
    → LLM_CALL (context 准备完成)
    → IDLE (context 准备失败且不可恢复)

State: LLM_CALL
  触发: context 准备完成
  动作:
    1. 组装最终 messages (system + summary + recent + user_input)
    2. 调用 LLM API
    3. 应用超时控制 (默认 120s, 可配置)
    4. 应用重试策略 (指数退避, 最多 3 次)
  转换:
    → STREAM_RESPONSE (text output)
    → TOOL_EXEC (tool_calls)
    → ERROR_HANDLE (API error / timeout)

State: TOOL_EXEC
  触发: LLM 返回 tool_calls
  动作:
    1. 验证 tool_call 参数 schema
    2. 检查权限 (是否需要用户确认)
    3. 执行工具 (串行, 按 LLM 返回的顺序)
    4. 捕获执行结果 (stdout, stderr, exit code, duration)
    5. 截断过大的结果 (>50KB → 保留头尾)
  转换:
    → RESULT_INTEGRATE (执行成功)
    → ERROR_HANDLE (执行失败)

State: RESULT_INTEGRATE
  触发: 工具执行完成
  动作:
    1. 将 tool_result 格式化为 messages 追加到 context
    2. 更新 token 计数
    3. 记录 trace (工具名, 参数, 结果大小, 耗时)
  转换:
    → CHECK_END_CONDITION

State: CHECK_END_CONDITION
  触发: 结果已集成
  判断:
    1. LLM 返回了 stop_reason="end_turn"? → STREAM_RESPONSE
    2. hop_count >= max_hops (25)? → STREAM_RESPONSE (强制截断)
    3. 否则 → LLM_CALL (继续循环)
```

---

## 工具执行模型：从串行到并行的演进

### 为什么 my-agent 选择串行

my-agent 的文档中写道："串行工具执行——工具有副作用，并行难保证一致性。"

这个判断是对的，但可以更精确地分析：

### 工具依赖的形式化分析

给定一组 LLM 返回的 tool_calls `[T1, T2, ..., Tn]`：

```
定义: 依赖关系 T_i → T_j
  当 T_j 的参数引用了 T_i 的输出时，T_j 必须在 T_i 之后执行。

依赖关系有三种来源:
1. 显式依赖: T_j 的参数是 T_i 的返回值（如先 read_file，再基于内容 write_file）
2. 隐式依赖: T_i 和 T_j 操作同一文件/T_j 依赖 T_i 的副作用
3. 无依赖: T_i 和 T_j 完全独立

LLM 在单次 response 中返回的多个 tool_calls 之间:
- 如果是 tool_call 的不同 id → 理论上可并行（但 LLM 意图可能是顺序的）
- 如果是 tool_use 的嵌套 → 明确是顺序的
```

### 推荐的执行策略

```python
def execute_tools(tool_calls: list[ToolCall]) -> list[ToolResult]:
    """
    智能工具执行: 检测依赖关系，无依赖的并行，有依赖的串行
    """
    
    # Step 1: 构建依赖图
    dep_graph = build_dependency_graph(tool_calls)
    # Step 2: 拓扑排序分组
    # 同一组内的工具无依赖 → 可并行
    # 组与组之间有依赖 → 串行
    execution_groups = topological_group(dep_graph)
    
    results = []
    for group in execution_groups:
        if len(group) == 1 or not has_side_effects(group):
            # 单工具或无副作用 → 并行执行
            group_results = await parallel_execute(group)
        else:
            # 多工具且有副作用 → 串行（按 LLM 返回顺序）
            group_results = await serial_execute(group)
        results.extend(group_results)
    
    return results
```

### 关键边界条件

**1. 工具超时的连锁效应**

```
假设 T1, T2 并行，T2 超时（30s）
→ T2 被 abort，但 T1 可能仍在运行
→ LLM 只收到了 T1 的结果 + T2 的 timeout error
→ LLM 可能会重试 T2 或做出不完整的判断

解决方案:
- 并行组设置统一的超时上限 (max(tool_timeouts) + buffer)
- 超时后: 返回已完成的结果 + 未完成的标记为 "TIMEOUT"
```

**2. 工具输出截断的语义影响**

```
bash 工具返回: "Binary file matches" (只有 20 字节)
→ LLM 可能认为输出不完整，尝试更多工具调用来获取完整信息

bash 工具返回: 50KB 的 grep 结果被截断为前 45KB + 后 5KB
→ LLM 看不到中间部分，可能漏掉关键信息

更好的策略:
- 不截断，而是让 LLM 用更精确的工具（如 grep 的 -A/-B/-C 参数）
- 如果确实需要截断，在截断处插入 "--- TRUNCATED, N bytes omitted ---"
```

**3. 工具权限升级的场景**

```
Agent: T1: read_file("/etc/config.prod")     # 需要确认
       T2: write_file("/etc/config.prod")    # 需要确认
       T3: bash("cat /var/log/app.log")      # 不需要确认

如果 T1 的确认被用户拒绝:
→ T2 不能执行（因为 T1 和 T2 操作同一文件）
→ T3 可以继续执行（独立于 T1/T2）
```

---

## 错误处理分类学

Agent Runtime 中的错误比传统软件更复杂，因为在 LLM 和工具之间有一层**语义鸿沟**。

### 错误的五个层次

```
Level 1: 基础设施错误 (Infrastructure)
  - API timeout, rate limit, network error
  - 处理: 自动重试 + 指数退避
  - LLM 可见性: 不需要（在 Runtime 层处理）

Level 2: 工具执行错误 (Tool Execution)
  - 文件不存在、权限不足、命令语法错误
  - 处理: 返回错误信息给 LLM + LLM 决定下一步
  - LLM 可见性: 需要（作为 tool_result 返回）

Level 3: 工具结果语义错误 (Semantic Tool Error)
  - 工具执行成功，但结果不符合预期
  - 示例: read_file 成功，但读到的内容不是 LLM 期望的
  - 处理: LLM 检测 + 自适应（调整策略/参数）
  - LLM 可见性: 完全可见

Level 4: Agent 策略错误 (Strategic Error)
  - LLM 的推理路径错误（选择了错误的工具序列）
  - 示例: LLM 不断循环调用同一个工具，期待不同结果
  - 处理: Runtime 检测循环 + 注入纠正 prompt + 增加 hop
  - LLM 可见性: 需要 Runtime 的 meta-cognitive 反馈

Level 5: 目标级错误 (Goal-level Error)
  - 用户的目标在当前约束下无法实现
  - 示例: "部署到 production"但用户没有 production 权限
  - 处理: Agent 向用户说明约束并提出替代方案
  - LLM 可见性: 需要 + 需要和用户互动
```

### 每层的处理策略

```python
class AgentErrorHandler:
    """分层错误处理"""
    
    async def handle(self, error: AgentError, context: AgentContext):
        if error.level == ErrorLevel.INFRASTRUCTURE:
            return await self._handle_infra(error)
        elif error.level == ErrorLevel.TOOL_EXECUTION:
            return await self._handle_tool_error(error, context)
        elif error.level == ErrorLevel.TOOL_SEMANTIC:
            return await self._handle_semantic(error, context)
        elif error.level == ErrorLevel.STRATEGIC:
            return await self._handle_strategic(error, context)
        elif error.level == ErrorLevel.GOAL:
            return await self._handle_goal(error, context)
    
    async def _handle_infra(self, error):
        """基础设施错误: 静默重试"""
        for attempt in range(3):
            try:
                await asyncio.sleep(2 ** attempt)  # 指数退避
                return await retry_operation()
            except:
                continue
        raise UnrecoverableError("Max retries exceeded")
    
    async def _handle_tool_error(self, error, ctx):
        """工具错误: 返回错误给 LLM，让 LLM 决定"""
        return ToolResult(
            success=False,
            error=error.message,
            suggestion=f"Try: {error.suggestion}"  # 可选
        )
    
    async def _handle_strategic(self, error, ctx):
        """策略错误: Runtime 检测并干预"""
        if error.type == "LOOP_DETECTED":
            # 检测到 LLM 在循环调用同一工具
            ctx.inject_system_message(
                "Notice: You've called the same tool with similar parameters "
                "3 times. The results haven't changed. Consider a different approach."
            )
            ctx.bump_hop_limit(3)  # 给 LLM 额外 3 hops 来纠正
            return "continue"
```

### 循环检测的算法

```
LLM 陷入循环的模式:
1. 同一工具 + 相同参数 → 肯定是循环
2. 同一工具 + 相似参数（如只改了行号）→ 可能是循环  
3. 不同工具 + 但结果始终不变 → 可能是更隐蔽的循环

检测策略:
- 记录最近 N 个 tool_call 的 (tool_name, param_hash)
- 如果出现 3 次重复 → 标记 LOOP_DETECTED
- 如果 5 hops 内没有产生新的有效信息 → 标记 NO_PROGRESS
```

---

## 多 Agent 编排的深入分析

### 编排的本质：Task Decomposition 的形式化

多 Agent 编排的核心问题是**任务分解**：

```
给定: 用户目标 G, Agent 能力集 A = {a1, a2, ..., an}
问题: 将 G 分解为子任务 {g1, g2, ..., gm}，分配给 Agent

约束条件:
1. 能力匹配: gi 必须能被某个 aj 执行
2. 依赖顺序: gi → gj 如果 gi 的输出是 gj 的输入
3. 资源上限: 并行的 Agent 数 ≤ 预算
4. 截止时间: 总 wall time ≤ deadline

优化目标:
- min(总 wall time) 受限于依赖路径
- max(结果质量) 受限于 Agent 能力
- min(总 Token 成本)
```

### Orchestrator-Worker 的详细设计

这是当前生产中最常用的模式：

```
Orchestrator (编排者)
  │
  │ 职责:
  │ 1. 理解用户目标 → 制定执行计划
  │ 2. 维护全局状态（已完成什么、还需要什么）
  │ 3. 动态调整计划（基于 Worker 结果）
  │ 4. 处理 Worker 失败（重分配、降级）
  │
  ├── Worker 1: 执行子任务 → 返回结果 + 置信度
  ├── Worker 2: 执行子任务 → 返回结果 + 置信度
  └── Worker 3: 执行子任务 → 返回结果 + 置信度
```

**Orchestrator 的 prompt 模板**:

```markdown
## Role
You are a task orchestrator. Your job is to decompose a user goal into subtasks,
dispatch them to workers, and synthesize the results.

## Current State
Goal: {{goal}}
Completed: {{completed_tasks}}
Pending: {{pending_tasks}}
Worker Results: {{worker_results}}

## Available Workers
{{#each workers}}
- {{name}}: {{description}}
{{/each}}

## Your Task
1. Review worker results
2. Decide: is the goal achieved?
   - Yes → synthesize final answer
   - No → create next set of subtasks
3. If creating subtasks:
   - Each subtask must be specific and self-contained
   - Assign to the most capable worker
   - Specify dependencies if any

## Rules
- Never create a subtask that duplicates completed work
- If a worker failed, try a different approach or worker
- If stuck after 3 iterations, explain the blocker to the user
```

### 何时 Multi-Agent 是正确选择

**决策矩阵**：

```
单 Agent 足够了，如果你遇到的是:
├─ 单一路径推理（不需要多视角）
├─ Latency 敏感（multi-agent 增加编排开销）
├─ Token 预算有限（multi-agent 增加总 Token 消耗）
└─ 任务边界模糊（难以清晰分解）

Multi-Agent 值得，如果你遇到的是:
├─ 明确可分解（如"分析代码 + 写文档 + 写测试"）
├─ 需要多视角验证（如"审查这个安全方案"→ 三个安全专家 Agent 独立审查）
├─ 天然并行（如"为这 5 个模块分别写单元测试"）
├─ 专业化深度（如"前端专家 Agent + 后端专家 Agent + DevOps Agent"）
└─ 需要对抗性思维（如"一个 Agent 写方案，另一个 Agent 找漏洞"）
```

### Multi-Agent 的反模式

| 反模式 | 表现 | 根因 | 修复 |
|--------|------|------|------|
| **Echo Chamber** | 多个 Agent 输出相似内容 | Agents 共享同一 LLM，缺乏多样性 | 给不同 Agent 注入不同的 system prompt + 不同视角 |
| **Orchestrator 瓶颈** | Orchestrator 成为性能瓶颈 | 所有信息流经 Orchestrator | 允许 Worker 之间点对点通信 |
| **过度分解** | 任务被分解得过于细碎 | Orchestrator 过于"热心" | 设置每层分解的粒度下限 |
| **失控循环** | Orchestrator 不断创建新的 subtask | 没有收敛条件 | 设置 max_iterations + total_token_budget |
| **Accountability Gap** | 最终结果有问题，但不知道是哪个 Agent 的错 | Trace 不完整 | 每个 subtask 的输出标注来源 Agent |

---

## 生产环境中的 5 个关键问题

### 问题 1: Long-running Agent 的持久化

```
场景: Agent 执行 30 分钟的任务（代码重构、多文件修改）
问题: 如果在 25 分钟时进程崩溃，已执行的工作全丢

解决方案: Checkpoint-based Recovery

每隔 N 个 hops（如 5）自动 checkpoint:
- Context 状态 → 磁盘
- 已完成的 tool calls 及其结果 → 磁盘
- 当前 state_machine 状态 → 磁盘

恢复时:
- 从最近的 checkpoint 恢复
- 重新执行 checkpoint 后的 hops（幂等性问题需要处理）
```

Temporal 这类 Durable Execution 引擎正是解决这个问题的——它将每个 hop 持久化为不可变事件，崩溃后从断点继续。

### 问题 2: Token 预算的实时监控

```
场景: 用户启动了一个 agent，前 5 hops 消耗了 30K tokens
问题: 照此速度，20 hops 将消耗 120K tokens → $0.36

解决方案: Budget-Aware Execution

class TokenBudget:
    def __init__(self, max_cost: float, model_pricing: dict):
        self.max_cost = max_cost
        self.pricing = model_pricing
        self.spent = 0.0
    
    def can_afford_next_hop(self, estimated_tokens: int) -> bool:
        cost = estimated_tokens * self.pricing["input"] / 1000
        return self.spent + cost <= self.max_cost * 0.8  # 留 20% buffer
    
    def report_to_agent(self):
        """当预算接近上限时通知 Agent"""
        if self.spent > self.max_cost * 0.7:
            return f"Budget alert: {self.spent}/{self.max_cost} spent. Be concise."
```

### 问题 3: 工具描述与实际行为不一致

```
场景: 工具 write_file 的描述说 "Returns success/failure"
       但实际实现在某些情况下返回了 "Partial success: wrote 80%, file locked for remaining 20%"

问题: LLM 根据工具描述做出假设，但实际行为超出描述范围

解决方案: Tool Contract Testing

- 每个工具需要定义 Contract: {expected_inputs, expected_outputs, error_cases}
- CI 中自动测试 tool contract
- 当 tool 行为变更时，自动更新 tool description 并验证 LLM 是否仍能正确使用
```

### 问题 4: Context 污染

```
场景: Agent 执行了一个 bash 命令，输出 20KB 的日志
      但其中只有 200 bytes 是真正有用的

问题: 大量的低质量 tool result 占据了 context window，挤出了真正重要的信息

解决方案: Tool Result Filtering

1. 重要性预估: 在 tool result 返回给 LLM 之前，快速评估其信息密度
2. 摘要化: 将大输出（>5KB）自动摘要为关键信息 + 统计信息
3. LLM 控制: 允许 LLM 在 tool call 中指定 want_summary=true

示例:
  bash("tail -n 1000 /var/log/app.log")
  
  实际输出: 1000 行日志 → 摘要化为:
  "Last 1000 lines: 950 INFO, 47 WARN, 3 ERROR.
   Errors: [Connection refused at 10:23, OOM at 10:25, Timeout at 10:28].
   Full output available via read_file('/tmp/full_output.txt')"
```

### 问题 5: Agent Death Spiral

```
场景: Agent 执行到第 15 hop，context 接近满载
      每次新的 LLM 调用越来越慢（因为 context 越来越大）
      工具输出被截断得越来越多（因为 context 空间不够）
      → Agent 的质量在加速下降

这被称为 "Death Spiral"

解决方案:
1. 积极 Compaction: 不要等到 context 满了再做摘要，在 60-70% 时就开始
2. 自适应 Hop Limit: 根据任务复杂度动态调整 max_hops
3. 质量监控: 检测到连续 hops 的 output 质量下降 → 提前结束 + 报告
4. Context 分层: Working Memory (<5K) + Recent (<15K) + Summary (<10K) 
   严格分离，避免互相挤压
```

---

## 从 my-agent 看 Runtime 实现的最佳实践

> **说明**：my-agent 是本人的 TypeScript CLI Agent 实践项目（Agent Loop / Context / Tools），不是 Anthropic 的官方仓库——附录 C 曾误标为官方参考实现，已于 2026-08 更正。

### my-agent 的架构亮点

回顾 my-agent 的 Runtime 设计，有几个值得强调的工程决策：

**1. ContextManager 的 "chars/4" 估算**

```
为什么不用 tiktoken 精确计数？

权衡:
- tiktoken: 精确计数，但引入 15MB 的依赖 + 加载时间
- chars/4: 有 10-20% 误差，但零依赖、零延迟

对于 Token 预算管理：10-20% 的误差是可以接受的
→ 因为预算本身就有安全边际（reserveForResponse + safety margin）
→ 精确到 byte 不是必要的

这是一个好的工程判断。
```

**2. Session + Trace 双持久化**

```
Session (对话状态持久化):
- 目的: 恢复对话
- 内容: ContextManager 序列化（rawHistory + summaries）
- 写入时机: /save 命令 or 自动定时

Trace (执行轨迹持久化):
- 目的: 调试 + 评测
- 内容: 每 hop 的工具调用、token 使用、耗时
- 写入时机: 每 hop 后追加

为什么分开？
- Session 是"状态"，Trace 是"日志"
- 恢复时只需要 Session，不需要 Trace
- Trace 可以很大（大量 hops），不应该影响 Session 的恢复速度
```

**3. Planner 的独立模块设计**

```
/plan → Planner.tree → Context → LLM

而非:
LLM 直接 plan + execute（混在一起）

为什么分离？
- Plan 结构可以被其他模块消费（如可视化、评估）
- 用户可以审阅计划后再执行
- Plan 可以持久化，跨 session 追踪进展
```

### my-agent 可以增强的方向

基于本报告的研究，my-agent 的 Runtime 可以在以下方向演进：

| 增强点 | 当前状态 | 建议 | 优先级 |
|--------|---------|------|--------|
| Memory System | Session 扁平持久化 | 引入 MemGPT 式分层 Memory | 高 |
| Multi-Agent | 单 Agent | 增加 Lightweight Orchestrator | 中 |
| Tool Contract | 无 | 添加 Tool Contract 定义 + 测试 | 中 |
| Budget Control | 仅 Token 计数 | 增加 Cost Budget + 实时报告 | 中 |
| Checkpoint | 无 | Hop-level Checkpoint for Recovery | 低 |
| Death Spiral 检测 | 无 | Context 质量监控 + 提前终止 | 低 |
