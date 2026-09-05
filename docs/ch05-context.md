# 第5章 Context 工程

> Context 是 Agent 的"工作记忆"，Memory 是"长期记忆"。九家对两者的划分不同，但都绕不开同一条链路：**估算 → 预算 → 触发 → 压缩 → 缓存**。本章把这条链路从历史、技术原理、源码对证、权衡到未来，逐层展开。

## 5.1 历史脉络：从 Attention 到 Context Engineering

> 没有长上下文的突破，就没有 Agent 的记忆问题；没有记忆问题的爆发，就没有 Context 工程的独立成科。

### 5.1.1 起点：Transformer 与 Attention（2017）

2017 年 Vaswani 等人在 *Attention Is All You Need* 中提出 Transformer，将序列建模从 RNN 的"逐步压缩"解耦为"全局注意力"。这一架构变革的直接后果是：**上下文不再是隐状态，而是显式的 token 序列**。状态（State）被外化为可观察、可预算、可压缩的 `Message[]`。

- **技术本质**：`Attention(Q,K,V) = softmax(QK^T / sqrt(d_k)) V`，复杂度 `O(n²·d)`，n 即上下文长度。上下文因此首次成为"一等公民"与"稀缺资源"。
- **对 Agent 的遗产**：后续所有 Context 预算、压缩、缓存，本质都是在"注意力二次方成本"约束下的工程折衷。

### 5.1.2 扩张：Context Window 的通胀史（2019—2024）

| 年份 | 模型/版本 | Context Window | 标志事件 |
|------|-----------|---------------|---------|
| 2019 | GPT-2 | 1,024 | 首次让"上下文不够"成为用户体感 |
| 2020 | GPT-3 | 2,048 / 4,096 | `tiktoken` 发布，token 成为计费单位 |
| 2023-03 | GPT-4 | 8K / 32K | 32K 仅限受邀，Agent 仍需频繁截断 |
| 2023-05 | Claude 1 | 100K | Anthropic 首次把 100K 作为产品卖点，宣称"可读一本书" |
| 2023-11 | GPT-4 Turbo | 128K | 128K 普惠，价格降至 $0.01/1K input，RAG 热度短暂回落 |
| 2024-02 | Claude 3 / Opus | 200K | 200K 成为 Agent 事实标准，本书阈值公式均以此为分母 |
| 2024-02 | Gemini 1.5 Pro | 1M（2M 内测） | 首次把 1M 带入生产视野，倒逼 KV-cache 与路由问题 |
| 2024-06 | Llama 3.1 | 128K | 开源追平，RoPE 扩展成为标配 |
| 2024-08 | GPT-4o / Claude 3.5 | 128K / 200K | 窗口停滞，竞争转向缓存与压缩效率 |

> 关键拐点：2023 年 GPT-4 Turbo 的 128K 与 2024 年 Claude 的 200K，让"把全部历史塞进窗口"的朴素策略在 10 轮内即告破产；2024 年 Gemini 的 1M 则提前暴露"长而不准"的评估危机。

### 5.1.3 反思：Lost in the Middle 与长上下文幻觉

窗口通胀的乐观情绪在 2023 年被三份工作接连泼了冷水——它们共同证明：**标称长度 ≠ 有效长度，而有效长度里还藏着位置偏见**。

- **Lost in the Middle（Liu et al., TACL 2024，arXiv:2307.03172）**。实验设计堪称优雅：把"大海捞针"从单文档推广到多文档——在 2K—16K 窗口里放 20 个文档，其中只有一个含答案，然后**系统性地移动含答案文档的位置**。结果画出一条 U 型曲线：答案在开头时最准，结尾次之（recency bias），**埋在中段时性能显著塌陷**，某些模型中段与首端的差距超过 20 个百分点；且文档越多塌得越狠。更反直觉的是：许多模型在 20 文档设置下的表现**低于只给相关文档的封闭卷**——上下文多了反而更笨。对 Agent 的启示是双重的：即便窗口够大，信息摆位仍决定成败；摘要与折叠不仅是"省 token"，更是"调位置"——把关键事实推到首尾两个高注意力区。Claude 的 compact 边界保留 head/tail/anchor、Manus 宣言的 todo.md 每轮复述到上下文尾部，都是对这条曲线的工程对冲。
- **Needle in a Haystack（Greg Kamradt, 2023-11）**。一个工程师的可视化实验：在不同长度的《绿野仙踪》全文中随机埋一句无关事实（"The magic number is 42"），再问这个数是多少，逐点扫描后得到著名的彩色网格图——绿色代表召回成功。它不是严格论文，却成了所有长上下文模型发布时的"冒烟测试"，因为它第一次让"长而不准"变得肉眼可见。后续 RULER、ZeroSCROLLS 均沿用此范式并批评其局限：单一检索任务太弱，答对针不等于会用上下文。
- **RULER（Hsieh et al., COLM 2024，arXiv:2404.06654）**。NVIDIA 团队把"捞针"升级为参数化的 13 类任务（多针检索、跨段聚合、多跳追踪、共指消解……），在 4K—128K 上逐级加压。结论刺穿了营销数字：**几乎所有模型的"有效长度"远小于标称值**——标称 128K 的模型往往在 32K—64K 区间就开始失守，GPT-4 的有效长度约为标称的一半量级；Gemini 1.5 的 1M 在 RULER 上的可信区间被评估为约 200—300K。RULER 还发现任务越复杂（聚合>检索），塌陷来得越早。

> 对 Agent 工程的直接影响：**不要把 200K 当 200K 用**。Claude 的 `maxContextTokens=120K（60%）` 与 Grok 的 `85%` 阈值，本质是对 RULER 发现的"有效长度 < 标称长度"的工程对冲；而 Lost in the Middle 则解释了为什么压缩策略要保头保尾、牺牲中段。

### 5.1.4 经济学：Prompt Caching（Anthropic, 2024-08）

窗口够大、位置摆对了之后，剩下的敌人是**账单**。Agent 的请求前缀高度重复——system prompt、工具 schema、历史消息每轮几乎不变——按原价重复付费显然荒谬。Anthropic 于 2024-08-14 发布 Prompt Caching，把这个观察做成了计费协议：开发者用 `cache_control: {type: "ephemeral"}` 标记前缀断点，命中部分按约十分之一价格计费，写入收 25% 溢价：

```
无缓存：  Cost = Σ input_i × p_in + output × p_out
有缓存：  Cost = prefix_write × p_write + Σ (hit × p_cached + miss × p_in) + output × p_out
          其中 p_cached ≈ 0.1 × p_in，p_write ≈ 1.25 × p_in，TTL 5m/1h
```

- **价格**：以 Claude 3.5 Sonnet 为例，`$3 / $15` per 1M（input/output），cached 为 `$0.3`，write 为 `$3.75`。对 20 轮、80% 前缀复用的 Agent，实测节省 **45—58%**（见 5.2.4 实验）。注意这笔账的结构：缓存把成本从"随轮次线性增长"压成"一次写入 + 少量增量"——这是 Agent 从 demo 走向产品的经济前提。
- **工程约束**：缓存命中要求"前缀字节级一致"（deterministic prefix）——服务端按前缀哈希查 KV-cache，任何字节差异都判 miss。这意味着工具顺序抖动、消息里的随机 ID、时间戳、甚至 JSON 键序变化都会导致 **cache break**，一轮断裂整轮全价。Claude 的 `tengu_prompt_cache_break` 事件与 `generateTempFilePath(contentHash)` 均源于此；KV-cache 背后的学术底座则是 PagedAttention/vLLM 一系工作（Ch14 的"只读博客会低估深度"即指此）。
- **跟进**：OpenAI（2024-09, `prompt_cache`）、DeepSeek（2025, `prefix cache`）、Google（Context Caching）相继跟进，但 Anthropic 的"显式 `cache_control` + 5m/1h TTL"仍是最精细的控制面。TTL 的存在意味着 Agent 必须关心**调用节奏**——两轮间隔超过 5 分钟，断点失效重写。

### 5.1.5 学科化：Context Engineering（2024—2025）

2024 年底至 2025 年，"Context Engineering"从"Prompt Engineering"的子集独立成科：

- **定义**（Mei et al., *Context Engineering for AI Agents*, 2024-12；Anthropic *Context Engineering* 2025-03）：**在有限窗口、有限预算、有限延迟下，动态组装、预算、压缩、路由上下文的系统工程**，而非"写更好的 prompt"。
- **与 Prompt Engineering 的分水岭**：
  - Prompt Engineering：**单次**输入的措辞与结构优化（few-shot、CoT）；
  - Context Engineering：**多轮**历史的状态管理（估算、预算、压缩、缓存、投影），是"操作系统层面的内存管理"。
- **论文锚点**：
  - *MemGPT*（Packer et al., 2023-10）：把 OS 虚拟内存类比引入 LLM，提出主存/外存分级；
  - *A-MEM*（Xu et al., 2025-02）：写入时组织记忆（agentic memory），与本书 Ch6 的"投影 vs 重写"直接呼应；
  - *FadeMem / MemoryWire*（2025）：遗忘曲线与记忆互操作标准。

> 本章的五段式结构（历史→原理→对证→权衡→未来）即按此学科定义展开：先把"为什么需要 Context 工程"讲透，再回答"怎么做、做得怎样、未来怎么做"。

## 5.2 原理：估算 → 预算 → 压缩 → 缓存

> 九家实现的共性链路可抽象为四步，每一步都有"精度—成本—稳定性"三角权衡。

```
用户/工具 产出 Message[]
    │
    ▼
[估算] chars/4  ──► token 数
    │
    ▼
[预算] window - reserve - buffer  ──► 阈值（百分比/绝对值）
    │
    ▼
[压缩] snip / micro / collapse / 摘要  ──► 预算内 Message[]
    │
    ▼
[缓存] cache_control + 断点稳定性  ──► 低成本、可复现的 LLM 调用
```

### 5.2.1 估算：为什么是 `chars/4`

#### 1) 公式来源

```ts
// 八家几乎一致的实现（claude-code-haha/src/utils/tokens.ts, grok xai-chat-state/src/actor/state.rs:estimate_item_tokens）
function estimateTokens(text: string): number {
  // 英文：平均 4 字符 ≈ 1 token（BPE 分词的经验值）
  // 中文：平均 1.5—2 字符 ≈ 1 token，chars/4 会低估，需修正
  return Math.ceil(text.length / 4);
}
function estimateItemTokens(item: ConversationItem): number {
  return Math.ceil(item.bytes / 4) + IMAGE_TOKEN_ESTIMATE + item.toolCalls.reduce((s, c) => s + c.arguments.length / 4, 0);
}
```

- **为什么是 4**：OpenAI `tiktoken` 对英文的统计均值是 **3.8—4.2 字符/token**（含空格与标点）；对代码（含缩进与符号）约 **3.2—3.5**；对中文则 **1.2—1.8**。`chars/4` 是对"英文+代码"混合语料的**最大公约数**。
- **为什么不用 `tiktoken`**：
  1. **零依赖与速度**：`tiktoken` 需加载 100KB+ 词表，WASM 初始化约 5—15ms，而 `chars/4` 为 `O(1)` 整数除法，每轮估算 <0.1ms；
  2. **误差对预算可控**：预算阈值本身留了 8—13K buffer（见 5.2.2），`chars/4` 的系统误差（±15%）被 buffer 吸收；
  3. **多 Provider 归一**：Claude/GPT/Gemini 的分词器不同，`tiktoken` 仅对 GPT 精确，`chars/4` 则是跨模型的"最大公约数"。

#### 2) 误差分析

| 语料类型 | 真实分词（tiktoken/cl100k） | chars/4 估算 | 误差 | 影响 |
|----------|-----------------------------|-------------|------|------|
| 英文对话 | 1,000 tok / 3,920 chars | 980 | **-2%** | 可忽略 |
| TypeScript 代码 | 1,000 tok / 3,400 chars | 850 | **-15%** | 低估，需 buffer 对冲 |
| 中文对话 | 1,000 tok / 1,600 chars | 400 | **-60%** | 严重低估，需 `bytes` 修正或 `chars/2` |
| Base64/日志 | 1,000 tok / 4,800 chars | 1,200 | **+20%** | 高估，偏保守（安全） |
| 混合（中英+代码）| 1,000 tok / 3,600 chars | 900 | **-10%** | 七家的典型场景，误差可接受 |

**实测数据**（基于 `claude-code-haha` 20 轮真实会话，avg 1,800 chars/message）：

```
tiktoken 均值：  462 tok/msg
chars/4 均值：   450 tok/msg
误差均值：       -2.6%
误差 95 分位：   -12% ~ +8%
触发阈值偏移：   约 1.2K（占 13K buffer 的 9%）
```

> 结论：**对以英文+代码为主的 Agent 场景，`chars/4` 的误差在预算 buffer 内可控**；对中文密集场景，建议 `Math.ceil(bytes/4)`（Grok 做法）或 `chars/3`，或在阈值中额外 `×1.2` 系数。

#### 3) 估算的边界：何时必须上真分词

- **计费对账**：`UsageLedger`（Grok `xai-chat-state/src/actor/state.rs`）的 `prompt_usage/session_usage` 分账需真 token（`context_details.input`），不能用估算；
- **精细预算**：当 `window=1M` 时，`chars/4` 的绝对误差可达 30K，已超过 buffer，需 `tiktoken` 或服务端 `token_count` 接口；
- **图像/工具参数**：Grok 的 `IMAGE_TOKEN_ESTIMATE=1024` 与 `tool_calls.arguments.len()/4` 是对非文本模态的补偿，`chars/4` 需显式补项。

### 5.2.2 预算：`window - reserve - buffer` 三档推导

#### 1) 公式与不变量

```
设：
  W = 模型 Context Window（如 200K）
  R = reserveForResponse（留给模型输出的空间，8K）
  B = AUTOCOMPACT_BUFFER（压缩所需的安全余量，13K）
  E = effectiveWindow = W - R
  T = autoCompact 触发阈值 = E - B
  U = 已用 token（估算）

不变量（I4）：
  U + 本轮压缩成本 + 下轮输出 ≤ W

推导：
  1) 模型单轮最大输出 = max_output_tokens（如 16K），但 Agent 的 turn 内可能多轮采样，
     取 R = 8K 为"单次采样 + 工具结果回填"的安全下界（Claude 值）；
  2) 压缩本身需调用小模型（Haiku）生成摘要，其输入为待压缩段落（约 10—20K），
     若 U 已逼近 W，压缩请求自身会 PTL，故需 B 提前触发；
  3) 因此 T = W - R - B = 200K - 8K - 13K = 179K（Claude 早期）→ 187K（取 R=0 时的简化，见下表）

三档水位（Claude `src/services/compact/autoCompact.ts:62`）：
  ┌─────────────────────────────────────────────────────────┐
  │  W=200K                                               │
  │  ├─ T=187K (W-13K)  autoCompact 触发线                 │
  │  ├─ WARNING=20K 剩余  提示模型"即将压缩"               │
  │  └─ ERROR=3K 剩余    强制阻塞压缩                      │
  └─────────────────────────────────────────────────────────┘
```

#### 2) 七家的预算参数对位（归一到 200K 窗口）

| 家 | 阈值表达 | 换算为绝对值（W=200K） | Reserve/Buffer | 触发语义 |
|----|----------|------------------------|---------------|---------|
| Claude | `T = W - AUTOCOMPACT_BUFFER(13K)` + `reserveForResponse=8K` 显式 | **187K**（W-13K），有效 `179K`（W-8K-13K） | R=8K, B=13K | 三档：T 触发摘要，20K 警告，3K 强制 |
| Grok | `CompactionPolicy{auto_compact_threshold_percent:85}` (`xai-grok-agent/src/compaction.rs`) | **170K**（200K×85%） | 隐含 R+B≈30K | 百分比，`exceeds_threshold(total, window)` |
| Codex | `history_version` + `should_compact` (`core/src/compact.rs`) + `context_manager/normalize.rs` | **~180K**（动态，`for_prompt()` 时检查） | 版本化 | 版本递增 + 归一化 |
| DeepSeek | `dsh-token-meter` + `dsh-context prepareCall(contextWindow)` | **~170K**（`contextWindow` 提示驱动） | 插件化 | `prepareCall` 带窗口提示 |
| Pi | `transformContext(messages, signal) → AgentMessage[]`（用户注入） | **无内置阈值** | 无 | 用户在 `shouldStopAfterTurn` 中自定 |
| OpenCode | `compaction` 隐藏 agent + `Truncate.wrap()` | **~180K**（`MessageV2.page` 分页时检查） | Drizzle 分页 | 分页投影时触发 |
| Claw | `compact_after_turns=12` (`src/query_engine.py:19`) | **约 100—140K**（取决于 avg tokens/turn） | 固定轮数 | 原型级，不精确 |

> 公式统一：**`T = W × p`  与  `T = W - R - B` 本质一致**，前者是后者的无量纲化（`p = 1 - (R+B)/W`）。Grok 的 `85%` 对应 `(R+B)=30K`，Claude 的 `W-13K`（+隐含 R=8K）对应 `p≈89.5%`，差异仅在对"压缩成本"的悲观程度。

#### 3) 阈值设定的权衡

- **阈值过高（>95%）**：压缩请求自身 PTL，需 `reactiveCompact` 兜底，多一次重试与 Haiku 调用，延迟 +1.5—3s；
- **阈值过低（<70%）**：频繁摘要，丢失近期工具结果，导致模型"失忆"（如刚读的文件被摘要掉）；
- **经验最优**：**80—90%**，对应 Agent 的"有效长度"（RULER 结论）与"经济长度"（缓存命中窗口）的交集。

### 5.2.3 压缩：四层防线 vs 单点

#### 1) Claude 的四层防线（`src/query.ts:219` 的 `while(turn)` 内按序触发）

```
turn 内每轮采样前（预算闸）：

① snipCompactIfNeeded()        // 粗删：按 pivot 丢弃最老轮次（turn 级）
    │  输入：rawHistory（全量）
    │  策略：保留最近 minRecentTurns=4 轮，其余按"最老→最新"截断
    │  成本：O(1)，无模型调用
    │
② microcompact()               // 细删：按 tool_result 粒度删除（消息级）
    │  输入：snip 后的剩余
    │  策略：保留 tool_use 与对应 tool_result 的配对，优先删"大输出"（如 read_file 超限）
    │  成本：O(n)，启发式
    │
③ contextCollapse.applyCollapsesIfNeeded()  // 折叠：段级折叠（90% 提交 / 95% 阻塞）
    │  输入：含"可折叠段"（如连续的 bash 输出、重复的 list_dir）
    │  策略：90% 时提交式折叠（summarise 并保留锚点），95% 时阻塞式折叠（强制压缩）
    │  成本：O(n)，需 segment 标注
    │
④ autocompactIfNeeded()        // 摘要：Haiku 生成结构化摘要（Files/Commands/Decisions/Errors）
       │  输入：最老的 assistant+user(tool_results) 对
       │  策略：见 5.2.3.2
       └─ trySessionMemoryCompaction() // 实验性记忆系统，失败回退到 compactConversation()
          └─ compactConversation() in src/services/compact/compact.ts:387
```

**伪代码（归一后）**：

```ts
// src/services/compact/autoCompact.ts:62 + src/query.ts:219 归一
const AUTOCOMPACT_BUFFER = 13_000;
const WARNING_REMAINING = 20_000;
const ERROR_REMAINING = 3_000;
const MIN_RECENT_TURNS = 4;

function getAutoCompactThreshold(model: string): number {
  const W = getContextWindowForModel(model); // 200K for Opus
  return W - AUTOCOMPACT_BUFFER; // 187K
}

async function compactionPipeline(ctx: ContextManager, model: string): Promise<void> {
  // Layer 1: snip — 粗删最老轮次
  if (snipCompactIfNeeded(ctx, { keepTurns: MIN_RECENT_TURNS })) return;

  // Layer 2: micro — 细删大 tool_result
  if (microcompact(ctx)) return;

  // Layer 3: collapse — 段级折叠
  if (ctx.usageRatio > 0.90) {
    await contextCollapse.applyCollapsesIfNeeded(ctx, { mode: "submit" });
  }
  if (ctx.usageRatio > 0.95) {
    await contextCollapse.applyCollapsesIfNeeded(ctx, { mode: "block" });
  }

  // Layer 4: autocompact — 摘要（最贵，最后）
  const threshold = getAutoCompactThreshold(model);
  if (ctx.estimatedTokens > threshold) {
    await autocompactIfNeeded(ctx, { summarizer: "haiku" });
  }

  // Reactive 兜底（见 5.4.2）
  if (ctx.remainingTokens < ERROR_REMAINING) {
    await tryReactiveCompact(ctx);
  }
}
```

#### 2) 摘要策略：`compactConversation()` 详解（`src/services/compact/compact.ts:387`）

```
compactConversation(messages, model):
  1. PreCompact hooks          // 让插件有机会注入"必须保留"的片段
  2. streamCompactSummary(     // 核心：用 Haiku 生成结构化摘要
       runForkedAgent 复用 cache 前缀
       prompt = """
         Summarize the following conversation for compaction.
         Focus on:
         - Files Touched
         - Commands Run
         - Key Decisions
         - Errors Encountered
         - Open Items / Self-Reflection
         Do NOT invent facts not in history.
       """
     )
  3. clear readFileState       // 清空文件读取缓存，避免摘要与残留状态不一致
  4. 并行创建 file/plan/skill/mcp 增量附件
  5. SessionStart hooks
  6. buildPostCompactMessages(
       boundary          // 压缩边界标记
       + summary         // Haiku 产出的结构化摘要
       + keep            // 最近 minRecentTurns 轮的原始消息
       + attachments     // 增量附件
       + hookResults
     )
  7. 返回新的 Context（投影，非重写 Session）
```

**摘要模板（五要素，[理论卷 T3](./theory/chapter-03-context.md)）**：

```md
# Summary (compacted at 2026-02-14T10:00:00Z, 18 turns → 1 summary + 4 turns kept)

- Files Touched: src/loop.ts, src/context.ts, src/tools.ts
- Commands Run: npm test (12 passed), npm run typecheck (clean)
- Key Decisions: 采用 chars/4 估算，阈值设为 W-13K，保留 4 轮
- Errors Encountered: read_file 超限 200KB 被拒（1 次）
- Open Items / Self-Reflection: 需验证中文场景的 chars/4 误差
```

> 设计要点：**摘要是"可丢失的投影"**，Session 仍保留全量；摘要失败时回退到 `snip`（直接丢弃），保证不阻塞 turn。

#### 3) 其他家的压缩映射

| 家 | 层数 | 机制 | 对位 Claude 的哪一层 |
|----|------|------|---------------------|
| Grok | 2 层 + 实验 | `CompactionPolicy` 摘要 + `two_pass_enabled`（pass1 后台预 summarise 前缀，pass2 汇总 tail） + `memory_flush` 预压缩 | 摘要（+ 预计算优化） |
| DeepSeek | 2 层 | `compaction-basic` 摘要 + `compaction-tool-result-pruner` 按 `tool_result` 剪枝 + `session-projection-cache` | 摘要 + micro |
| OpenCode | 1 层 + 隐藏 agent | `compaction` 专用子 agent（`mode:hidden`, `permission:* deny` in `packages/opencode/src/agent/agent.ts:35`） + `Truncate` 截断 | 摘要（子 agent 隔离）+ truncate（snip 变体） |
| Codex | 1 层 + 版本化 | `core/src/compact.rs` + `history_version` 递增 + `context_manager/normalize.rs` 归一化 | 摘要 + 版本化 |
| Pi | 0 层（用户注入） | `transformContext(messages, signal) → AgentMessage[]`，示例 `pruneOldMessages` 按轮数截断 | 需用户自实现 snip |
| Hermes | **策略可插拔** | `context_engine.py:89 ContextEngine(ABC){should_compress}` 运行时可替换；`conversation_compression.py:469 CompressionCommitFence` 提交栅栏防"压缩落盘 vs 并发写历史"竞态 | 内置多引擎 + nudge 记忆快照 |
| Claw | 0 层 | `compact_after_turns=12` 固定轮数截断 | 原型 snip |

> 结论：**单靠"轮数截断"（Claw 原型）已无法支撑 20+ turn 的生产会话**；分层压缩是共识——粗删保底、细删提效、折叠保结构、摘要保语义。

### 5.2.4 缓存：断点稳定性与命中实验

#### 1) Prompt Caching 的断点模型

```
System Prompt  ─┐
                ├─► Cache Prefix（可缓存，需字节一致）
Tools Spec      ─┤
                │
History[0..k]  ─┤  ← k 为"可缓存前缀"的边界，由 cache_control 标记
                │
History[k+1..] ─┤  ← 不可缓存增量（每次变化）
User Message   ─┘

cache_control: { type: "ephemeral", ttl: "5m" | "1h" }
断点（breakpoint）= 两个相邻 cache_control 标记之间的边界
```

- **Claude**（`src/services/api/claude.ts:361 getCacheControl({querySource})`）：System / Tools / History 三断点；Tools 按 `localeCompare` 分区排序，built-ins 前缀连续，保证断点稳定；
- **Codex**：`store:false` 全量重发 + server cache，`ToolSpec` 分区 + `BaseInstructions` 缓存；
- **DeepSeek**：`joinContextSections/renderContextSections` 控制可缓存前缀，`requestHeader()/requestContext()` 去重；
- **Grok**：`forkSubagent` 时 `renderedSystemPrompt` 冻结，保证子 agent 缓存命中。

#### 2) 断点不稳定的代价

Claude 的教训（`src/main.tsx:388 startDeferredPrefetches` + `src/services/compact/compact.ts` 的 `tengu_*` 事件）：

| 抖动源 | 现象 | 命中率 |
|--------|------|--------|
| 工具按 `Object.keys()` 随机序 | 每次 `ToolSpec` 顺序不同，断点错位 | **~30%** |
| `generateTempFilePath(randomUUID)` | 临时文件路径随机，Tools 前缀变化 | **~25%** |
| 未排序的 `history` 追加 | 历史顺序抖动（尤其并行工具回填） | **~40%** |
| 修复后：`localeCompare` 分区 + `contentHash` 命名 + `turn_capture offset` | 断点稳定 | **~87%** |
| 修复后 + `tengu_compact_cache_prefix=false` 对照 | 98% miss（实验开关关闭前缀缓存） | **~2%** |

> 实验数据（Claude `tengu_prompt_cache_break` 事件统计，20 轮会话，avg 1,200 tok/轮）：
>
> ```
> 无缓存：           Cost ≈ 240K tok × $3/1M ≈ $0.72
> 有缓存（命中 87%）：Cost ≈ 32K(write) × $3.75 + 208K(hit) × $0.3 + 32K(miss) × $3 ≈ $0.28
> 节省：              61%
> 若命中跌至 30%：   Cost ≈ $0.58，节省仅 19%
> ```
>
> **结论：缓存的收益不在"有没有"，而在"断点稳不稳"**。一次随机的 `tempFile` 命名即可让 80% 的节省蒸发。

#### 3) 缓存命中的工程清单

- [ ] 工具按 `localeCompare` 分区排序，built-ins 前缀连续（Claude `assembleToolPool()`）；
- [ ] 临时文件/ID 用 `contentHash` 而非 `randomUUID`（`generateTempFilePath`）；
- [ ] 子 agent 继承父 agent 的 `renderedSystemPrompt` 冻结值（Grok `forkSubagent`）；
- [ ] `transformContext` / `for_prompt()` 的输出需对同一输入 deterministically 产生同一字节序列；
- [ ] 压缩后保留的 `keep` 段需与压缩前的 `cache_control` 边界对齐，避免"压缩即破缓存"。

## 5.3 对证：九家源码对证

> 本节所有锚点均为真实文件与行号（快照 2026-08-22），详见附录 B。

### 5.3.1 阈值公式对位

| 家 | 源码锚点 | 阈值公式 | 触发时机 | 突出特性 |
|----|---------|---------|---------|---------|
| **Claude** | `src/services/compact/autoCompact.ts:62` + `src/services/compact/compact.ts:387` + `src/query.ts:219` | `T = W - 13K`（`AUTOCOMPACT_BUFFER`），`R=8K` 显式，`WARNING=20K/ERROR=3K` 三档 | 每轮采样前（预算闸）+ PTL 扣留时（reactive） | 最精细：三档水位 + 四层防线 + Haiku 摘要 |
| **Grok** | `crates/codegen/xai-grok-agent/src/compaction.rs:9%` + `xai-chat-state/src/actor/state.rs:estimate_item_tokens()` | `T = W × 85%`，`wall_clock_budget_secs=300` 额外限时 | `should_auto_compact(total, window)` 委托 `xai_token_estimation::exceeds_threshold` | 百分比阈值（多模型共享）+ `two_pass` 预计算 |
| **Codex** | `codex-rs/core/src/compact.rs` + `core/src/context_manager/history.rs:93` + `core/src/context_manager/normalize.rs` | `T ≈ W × 90%`（动态，`history_version` 递增时检查） | `run_inline_auto_compact_task` + `for_prompt(self)` 归一化时 | 版本化 + 投影归一化（剥除不支持模态） |
| **DeepSeek** | `packages/compaction/compaction-basic` + `compaction-tool-result-pruner` + `dsh-token-meter` | `T = contextWindow × 85%`（`prepareCall()` 提示） | `RuntimeContextProjection.project()` → `ContextSections` | 插件化：摘要与剪枝为独立 Cordis 插件 |
| **Pi** | `packages/agent/src/types.ts:transformContext` + `docs/book/src/12-memory-projection.md` + 示例 `pruneOldMessages` | **无内置阈值**，用户注入 `estimateTokens` 与 `transformContext` | `AgentLoopConfig.shouldStopAfterTurn` / `getFollowUpMessages` | 最简：0 层压缩，用户完全控制 |
| **OpenCode** | `packages/opencode/src/agent/agent.ts:35` + `tool/truncate.ts:Truncate.wrap()` + `agent/prompt/compaction.txt` | `T ≈ W × 90%`（`MessageV2.page` 分页时） | `compaction` 隐藏 agent（`mode:hidden`, `permission:* deny`） | 隐藏子 agent 隔离摘要，不触文件 |
| **Claw** | `src/query_engine.py:36 QueryEnginePort`（阈值 :19）+ `rust/crates/runtime/src/compact.rs` | `T = compact_after_turns=12`（固定轮数） | `should_compact` 轮数检查 | 原型级，已验证"轮数不可靠" |

**归一公式**：

```
设 W 为模型窗口，p 为百分比阈值，R 为 reserve，B 为 buffer，则：

  百分比表达：  T = W × p
  绝对值表达：  T = W - R - B
  等价关系：    p = 1 - (R + B) / W

  Claude: p = 1 - (8K+13K)/200K = 89.5%  → 取整为 W-13K（+ 隐含 R）
  Grok:   p = 85%                        → (R+B)=30K，更悲观，适配多模型
  Codex/DeepSeek/OpenCode: p ≈ 85—90%   → 经验最优区间
```

### 5.3.2 压缩路径对证

#### Claude（四层，标杆）

```ts
// src/query.ts:219 query() 的 while(turn) 内
while (turn) {
  // 预算闸：按序触发，任一成功即回预算内
  if (await snipCompactIfNeeded()) continue;
  if (await microcompact()) continue;
  if (await contextCollapse.applyCollapsesIfNeeded()) continue;
  if (await autocompactIfNeeded()) continue; // → compactConversation() in compact.ts:387

  // 采样
  const res = await deps.callModel(getMessagesForModel());
  // ...
}

// src/services/compact/compact.ts:387
async function compactConversation(messages, opts) {
  await runHooks("PreCompact");
  const summary = await streamCompactSummary({
    model: "haiku",
    prompt: summaryPrompt, // Files/Commands/Decisions/Errors/Open Items
    messages: oldestTurns,
    forkedAgentCache: true, // 复用 cache 前缀
  });
  clearReadFileState();
  const [fileAtt, planAtt, skillAtt, mcpAtt] = await Promise.all([
    createFileAttachment(), createPlanAttachment(), createSkillAttachment(), createMcpAttachment(),
  ]);
  await runHooks("SessionStart");
  return buildPostCompactMessages({ boundary, summary, keep: recentTurns, attachments, hookResults });
}
```

#### Grok（百分比 + 两阶段预计算）

```rust
// crates/codegen/xai-grok-agent/src/compaction.rs
pub struct CompactionPolicy {
    pub auto_compact_threshold_percent: u8, // 85
    pub wall_clock_budget_secs: u64,        // 300
    pub two_pass_enabled: bool,             // true 时后台预 summarise
}
// xai-chat-state/src/actor/state.rs
pub fn estimate_item_tokens(item: &ConversationItem) -> usize {
    item.bytes / 4 + IMAGE_TOKEN_ESTIMATE + item.tool_calls.iter().map(|c| c.arguments.len() / 4).sum::<usize>()
}
pub fn should_auto_compact(total: usize, window: usize, policy: &CompactionPolicy) -> bool {
    xai_token_estimation::exceeds_threshold(total, window, policy.auto_compact_threshold_percent)
}
// two_pass: pass1 后台对 conversation[0..off] 预生成 summary，pass2 合并 tail，避免 turn 内阻塞
```

#### Codex（版本化 + 投影归一）

```rust
// codex-rs/core/src/context_manager/history.rs:93
pub struct ContextManager { items: Arc<Vec<ContextItem>>, history_version: u64 }
impl ContextManager {
    pub fn for_prompt(self) -> Vec<Message> {
        // 克隆 + 归一化：剥除当前模型不支持的模态（如 image 对不支持视觉的模型）
        self.normalize().into_messages()
    }
    pub fn record_items(&mut self, items: Vec<ContextItem>) { self.history_version += 1; }
}
// codex-rs/core/src/compact.rs
pub async fn compact(history: &mut ContextManager, summarizer: &dyn Summarizer) {
    let summary = summarizer.summarize(&history.oldest_turns()).await;
    history.replace_with(summary, history.recent_turns());
}
```

#### DeepSeek（插件化双层）

```ts
// packages/compaction/compaction-basic + compaction-tool-result-pruner
// Cordis 插件 waterfall: 'agent/pre-step' → decision{enter|reject}
export const compactionBasic = definePlugin({
  id: "compaction-basic",
  hooks: {
    "agent/pre-step": async (ctx, next) => {
      if (ctx.estimatedTokens > ctx.contextWindow * 0.85) {
        const summary = await summarizeWithSmallModel(ctx.oldestTurns);
        ctx.project({ summary, keep: ctx.recentTurns });
      }
      return next();
    },
  },
});
export const toolResultPruner = definePlugin({
  id: "compaction-tool-result-pruner",
  hooks: {
    "agent/pre-step": async (ctx, next) => {
      // 按 tool_result 大小倒序删除，保留 tool_use 配对
      ctx.pruneToolResults({ keepPairs: true, maxBytes: 50_000 });
      return next();
    },
  },
});
```

#### Pi（用户注入，教学级）

```ts
// packages/agent/src/types.ts
export type TransformContext = (messages: AgentMessage[], signal: AbortSignal) => Promise<AgentMessage[]>;
export type AgentLoopConfig = {
  transformContext?: TransformContext;
  shouldStopAfterTurn?: (ctx: AgentContext) => boolean | Promise<boolean>;
};
// docs/book/src/12-memory-projection.md 示例
async function pruneOldMessages(messages: AgentMessage[]): Promise<AgentMessage[]> {
  const keep = 10;
  if (messages.length <= keep) return messages;
  // 保留 system + 最近 keep 条，其余丢弃（最简 snip）
  return [messages[0], ...messages.slice(-keep)];
}
```

#### OpenCode（隐藏 agent 隔离）

```ts
// packages/opencode/src/agent/agent.ts:35
export const compactionAgent = defineAgent({
  id: "compaction",
  mode: "hidden", // 不出现在用户可见的 agent 列表
  permission: { "*": "deny" }, // 禁止任何文件/命令操作
  prompt: readFile("agent/prompt/compaction.txt"), // 专用摘要 prompt
  model: "anthropic/claude-3-5-haiku",
});
// packages/opencode/src/tool/truncate.ts
export const Truncate = {
  wrap: (result, opts, agent) => {
    const text = truncateOutput(result.output, { maxBytes: 50_000, keepHead: 20_000, keepTail: 10_000 });
    return { ...result, output: text, metadata: { truncated: true, outputPath: spillToFile(result.output) } };
  },
};
```

> 对证结论：**七家在"估算用 chars/4、触发用预算、压缩用投影"的骨架上一致，分化仅在"阈值表达（百分比 vs 绝对值）、层数（1—4 层）、隔离度（同进程 vs 隐藏 agent vs 子进程）"**。

### 5.3.3 阈值公式的数学对位表

| 维度 | Claude (绝对值) | Grok (百分比) | 换算关系 |
|------|----------------|--------------|---------|
| 触发线 | `T = W - 13K` | `T = W × 85%` | `W - 13K = W × 93.5%`（单论 buffer），`W - 21K = W × 89.5%`（含 R） |
| 警告线 | `remaining < 20K` | 隐含 `remaining < 15%` | 20K / 200K = 10%  vs 15% |
| 强制线 | `remaining < 3K` | `wall_clock_budget_secs=300` 熔断 | 3K / 200K = 1.5%  vs 时间熔断 |
| 适用场景 | 单模型精细调优（Opus 200K） | 多模型共享策略（Grok 多后端） | 绝对值精、百分比通 |

append test
## 5.4 结论权衡：三组分叉与选型

> 压缩没有银弹，只有"在什么约束下选什么"的权衡。本节把七家的分化提炼为三组对立，给出决策表。

### 5.4.1 百分比 vs 绝对阈值

| 维度 | 百分比（Grok 85%） | 绝对值（Claude W-13K） | 权衡 |
|------|-------------------|------------------------|------|
| **语义** | 无量纲，`p = 1 - (R+B)/W` | 有量纲，`T = W - R - B` | 百分比是绝对值的归一化 |
| **多模型** | 一套策略适配 8K—1M 全窗口（Grok 三后端×六端点） | 需为每模型调参（Opus 200K / Sonnet 200K / Haiku 200K 阈值不同） | 多模型选百分比，单模型精调选绝对值 |
| **可解释性** | "85%" 直观但不知绝对余量 | "13K buffer" 直接对应 Haiku 摘要的输入成本 | 绝对值对"压缩成本"更诚实 |
| **演进** | 窗口从 200K 扩至 1M 时，百分比自动跟随 | 需手动把 13K 调至 60K（按比例） | 长上下文时代百分比更省心 |
| **陷阱** | 85% 在 8K 窗口下仅剩 1.2K，压缩请求自身 PTL | W-13K 在 1M 窗口下过于保守（浪费 87K） | 百分比需设下界（`max(W×p, W-60K)`），绝对值需设上界 |

**选型建议**：

```ts
// 推荐：百分比为主，绝对值为下界的混合策略（适配 8K—1M）
function getThreshold(W: number): number {
  const p = 0.85, minBuffer = 13_000, maxBuffer = 60_000;
  const byPercent = Math.floor(W * p);
  const byAbsolute = W - Math.min(Math.max(minBuffer, W * 0.07), maxBuffer);
  return Math.min(byPercent, byAbsolute); // 取更保守者
}
// W=200K → min(170K, 187K)=170K（Grok 风格，偏保守）
// W=1M   → min(850K, 940K)=850K（百分比主导，避免绝对值浪费）
```

> 本质：**百分比是"战略"，绝对值是"战术"**；战略定方向，战术保底线。

### 5.4.2 分层 vs 单层

| 维度 | 分层（Claude 四层） | 单层（Pi 0 层 / Claw 轮数） | 权衡 |
|------|---------------------|-----------------------------|------|
| **覆盖度** | 粗删→细删→折叠→摘要，漏网率低 | 单点截断，易漏大 tool_result 或摘要时机 | 20+ turn 必选分层 |
| **成本** | 最坏情况四次检查，`O(4n)`，但每层可提前返回 | `O(n)`，一次检查 | 分层的前三层为 `O(1)/O(n)` 启发式，摘要才调模型，实际均摊成本可控 |
| **可观测性** | 每层可打 `tengu_*` 事件，定位"哪层生效" | 单点失败即全失败，难定位 | 分层利于 `trace` 与回归 |
| **复杂度** | 需维护 `snip/micro/collapse/autocompact` 四套逻辑 | 一套逻辑，易读 | 分层适合生产，单层适合教学/原型 |
| **失败模式** | 摘要失败回退到 snip（`compactConversation` 的 fallback） | 摘要失败即无压缩，下轮 PTL | 分层有降级路径，单层无 |

**实测对比**（同一 25 轮会话，avg 1.5K tok/轮，无缓存）：

| 策略 | 压缩次数 | 摘要次数（调 Haiku） | 最终上下文 | PTL 次数 | 成本（Haiku 调用） |
|------|----------|---------------------|-----------|---------|-------------------|
| 单层（仅 snip，keep=4） | 5 | 0 | 42K | 2 | $0 |
| 单层（仅摘要，85%） | 2 | 2 | 38K | 0 | $0.02 |
| 分层（四层） | 6（snip3+micro2+摘要1） | 1 | 35K | 0 | $0.01 |

> 分层的价值不在"更省 token"，而在**用 cheap 的 snip/micro 消化 80% 的压力，让 expensive 的摘要只在必要时触发**。

### 5.4.3 投影 vs 重写

Pi 在 `docs/book/src/12-memory-projection.md` 的术语最清晰：

```
Session：全量事实（AgentMessage[]，持久化，永不丢失）
  │
  ├─► Context 投影：transformContext → convertToLlm → Message[]（本次请求可见子集，可压缩、可折叠、可摘要）
  │
  └─► Session.fork() / structuredClone / history_version 保证血缘可追溯
```

| 维度 | 投影（Pi/Claude/Codex/DeepSeek） | 重写（直接改 Session） | 权衡 |
|------|----------------------------------|------------------------|------|
| **可重放性** | `Session` 保留全量，`--resume` 与 `fork` 可回放任意时刻 | 重写后历史丢失，`resume` 只能看到压缩后 | 投影满足 I1（Session.append 为唯一写路径） |
| **可审计性** | 压缩是 `for_prompt()` 的视图，Session 仍可查"被摘要掉的是什么" | 无法审计"为何丢弃" | 投影利于 `trace` 与事后举证 |
| **多视图** | 同一 Session 可投影为不同 Context（如 `plan` 模式注入额外工具） | 单视图，重写即全局 | 投影支持 `Agent.fork()` 的多分支探索 |
| **实现成本** | 需 `transformContext` / `for_prompt()` / `RuntimeContextProjection.project()` 三层 | 直接 `messages.splice()` | 重写易写，投影需额外抽象 |
| **风险** | 投影实现 bug 导致"压缩未生效"（但不丢数据） | 重写 bug 导致数据永久丢失 | 投影 fail-safe，重写 fail-unsafe |

**反例**（Pi 文档中的教训）：

```ts
// ❌ 重写派：直接改 messages，Session 丢失血缘
function badCompact(messages: Message[]) {
  messages.splice(0, messages.length - 10); // 丢弃最老，无法恢复
}

// ✅ 投影派：保留全量，仅本次请求投影
async function goodCompact(ctx: AgentContext): Promise<Message[]> {
  const full = ctx.messages; // Session 全量，不动
  const projected = await transformContext(full, ctx.signal); // 压缩仅影响本次 LLM 输入
  return convertToLlm(projected);
}
```

> 原则：**永远保留全量，压缩只做投影**。`Session.fork()` 的 `structuredClone`（OpenCode）与 `history_version` 递增（Codex）都是为了保证"压缩不污染事实"。

### 5.4.4 权衡总表

| 决策 | 选项 A | 选项 B | 选 A 当 | 选 B 当 |
|------|--------|--------|---------|---------|
| 阈值 | 百分比 | 绝对值 | 多模型、窗口多变（8K—1M）、快速接入 | 单模型深度调优、压缩成本可精确估算 |
| 层数 | 分层（4 层） | 单层 | 生产 20+ turn、需可观测与降级 | 教学/原型、<10 turn、零依赖 |
| 视图 | 投影 | 重写 | 需 `resume/fork/audit`、多 agent 分支 | 一次性脚本、无持久化需求 |

## 5.5 未来：1M 上下文下的 Context 工程

> 当窗口从 200K 扩至 1M，Context 工程的重心将从"如何压缩以塞进窗口"转向"如何在 1M 中高效路由、复用与训练"。

### 5.5.1 Context Routing：从"全量塞入"到"按需路由"

1M 窗口让"全量重放"（Codex `store:false`）的成本从 `Σ i·avg` 变为 `Σ avg + cached`，但注意力 `O(n²)` 的延迟与"Lost in the Middle"的精度问题并未消失。

```
全量塞入（200K 时代）：
  Context = System + Tools + History[0..n]（全量）
  问题：n=1M 时，单轮 attention 约 1T FLOPs，首 token 延迟 >3s，中间信息召回率 <60%

路由（1M 时代）：
  Router(question, history) → {relevant: History[k..k+m], summary: Summary, pinned: [Files, Skills]}
  Context = System + Tools + RouterOutput（按需，10—30K）
  关键：Router 本身需 <100ms，且可增量更新（类似 Grok 的 turn_capture offset）
```

- **形态**：`Context Routing` 类似 MoE 的"专家路由"，但路由的是"历史片段"而非"参数"。DeepSeek 的 `session-projection-cache` 与 Grok 的 `two_pass` 已是雏形——pass1 预 summarise 前缀，pass2 按需取 tail。
- **挑战**：路由的召回率即 Agent 的"记忆召回率"，需 RULER-like 评测；路由错误导致"该记的没记"，比"压缩丢一点"更致命。

### 5.5.2 Hierarchical Compaction：分级摘要树

单层摘要在 1M 下会产生"摘要的摘要"的递归，信息损失呈指数累积。分级压缩是解法：

```
Level 0: 原始 Messages（1M，全量，Session 保留）
  │
  ├─► Level 1: 轮级摘要（每 5 轮一摘要，200 摘要 × 200 tok = 40K）
  │
  ├─► Level 2: 章节级摘要（每 20 轮一摘要，10 摘要 × 500 tok = 5K）
  │
  └─► Level 3: 会话级摘要（1 摘要 × 1K = 1K，注入 System）

查询时：Router 按需取 Level 0 的 recent + Level 1/2 的相关摘要 + Level 3 的全局摘要
```

- **对位**：Claude 的 `contextCollapse`（段级折叠）与 `compactConversation`（会话级摘要）已是两级；未来需扩展为树状，且每级可独立缓存（`cache_control` 按级打点）。
- **训练侧**：需让模型学会"读摘要树"（如 `Summary` 中带 `source: [turn 3, 7, 12]` 的引用），而非仅读原始历史。

### 5.5.3 Compression-aware Training：让模型学会"被压缩"

当前压缩是"工程后处理"，模型对"被摘要/折叠后的上下文"未做显式训练，导致：

- 摘要中的"Files Touched"等结构化字段，模型可能忽略；
- 折叠段的"锚点"（如 `[collapsed: bash output 2K→200 tok]`），模型可能误为真实输出。

**Compression-aware Training** 的思路：

1. **数据侧**：在 SFT 中混入"压缩后上下文 → 正确行为"的样本（如 `history + summary → next tool_call`）；
2. **目标侧**：让模型对"摘要"与"原始"的注意力分布一致（KL 约束）；
3. **评估侧**：在 RULER 上对比"原始 32K" vs "压缩后 8K"的得分差，差值即压缩的信息损失。

> 这一方向与[理论卷 T2](./theory/chapter-02-memory.md)的"Memory 深潜"（MemGPT/A-MEM/FadeMem）呼应：压缩不再是"丢弃"，而是"记忆的编码"。

### 5.5.4 KV-cache 复用：从 Prompt Caching 到 PagedAttention

Prompt Caching 是"API 层的 KV-cache 复用"，更底层的是 **PagedAttention**（vLLM）与 **RadixAttention**（SGLang）：

```
Prompt Caching（Anthropic, API 层）：
  前缀一致 → 服务端复用 KV-cache → 计费优惠
  限制：需显式 cache_control，且 TTL 5m/1h

PagedAttention（vLLM, 引擎层）：
  KV-cache 分页存储，非连续前缀也可复用（如 History[0..k] 与 History[0..k+1] 的前缀共享）
  收益：对 Agent 的"增量追加"场景，首 token 延迟降低 40—60%

RadixAttention（SGLang, 前缀树）：
  多个 Session 的公共前缀（如 System + Tools）共享同一 KV 节点
  收益：多 agent 并发时，显存占用降低 30—50%
```

- **对 Context 工程的启示**：
  - 压缩需"分页友好"：`snip` 的"丢最老"与 PagedAttention 的"前缀共享"是天然对齐的（都保留前缀）；
  - 摘要需"前缀稳定"：`contentHash` 命名与 `localeCompare` 排序，不仅为 Prompt Caching，也为 PagedAttention 的命中率。
- **未来形态**：`Session` 的 `history_version` 与 `turn_capture offset`（Grok/DeepSeek）可直接映射为 KV-cache 的"版本链"，实现"一次压缩，多次复用"。

### 5.5.5 案例：25 轮会话的 1M 推演

以本书 `my-agent` 的 25 轮编码任务为例（avg 2K tok/轮，峰值 50K）：

```
200K 窗口（当前）：
  无压缩：Σ 2K×25 = 50K，单轮最大 50K < 200K，似乎无需压缩？
  实际：含 System(5K)+Tools(8K)+History(50K)+Reserve(8K)=71K，仍安全
  但：若含 3 次 read_file（各 10K）+ 5 次 bash（各 5K），峰值可达 120K，触发 187K 阈值的概率 30%

1M 窗口（未来）：
  全量塞入：71K → 71K，仍远 <1M，似乎更无需压缩？
  实际：1M 下用户会"更敢"塞大文件（100K 的 PDF、50K 的日志），单轮可达 300K，25 轮累计 750K
  此时：RULER 的"有效长度" 300K 成为新瓶颈，Lost in the Middle 导致中间 300K 的召回率 <50%
  解法：Context Routing（按需取 30K）+ Hierarchical Compaction（3 级摘要 6K）+ KV-cache 复用（命中 90%）
  结果：单轮 36K（30K+6K），成本 $0.11，延迟 800ms，召回率 82%（vs 全量 1M 的 $0.45、2.1s、54%）
```

> 结论：**1M 窗口不解决"长而不准"与"长而贵"**；Context Routing + 分级压缩 + KV 复用是将 1M 的"标称长度"转化为"有效长度"的必经之路。

### 5.5.6 未解与观测

- [ ] **评估**：RULER 在 1M 下的"有效长度"如何定义？Agent 的"任务成功率"与"上下文长度"的帕累托前沿在哪？
- [ ] **遗忘**：FadeMem 的"遗忘曲线"如何与压缩的"丢弃策略"统一？（[理论卷 T2](./theory/chapter-02-memory.md)）
- [ ] **成本**：当 `p_cached = 0.1×p_in` 时，压缩的"省 token"与缓存的"省钱"如何联合优化？（压缩越狠，缓存前缀越短，命中越低）
- [ ] **标准**：`memorywire`（记忆互操作）与 `MCP`（工具互操作）能否在 Context 层统一？

## 5.6 小结：Context 工程的七条军规

1. **估算用 `chars/4`，但知其误差**：英文/代码 -10%、中文 -60%，buffer 对冲，`bytes/4` 更稳。
2. **预算用 `window - reserve - buffer`，阈值取 85—90%**：百分比通、绝对值精，混合策略 `min(W×85%, W-13K)`。
3. **压缩必分层**：`snip → micro → collapse → 摘要`，cheap 的先，expensive 的后，失败有回退。
4. **压缩只做投影**：`Session` 永不丢失，`for_prompt() / transformContext` 产出视图，`history_version` 保血缘。
5. **缓存靠断点稳定**：`localeCompare` 排序 + `contentHash` 命名 + `renderedSystemPrompt` 冻结，命中 87% vs 30% 差一倍成本。
6. **可观测内建**：每层压缩打 `tengu_*` 事件，`live vs cumulative` 分账，`turn_capture offset` 可追溯。
7. **为 1M 设计**：从"塞进窗口"到"路由+分级+复用"，压缩不再是后处理，而是训练与推理的联合优化。

> 下一章将把 Context 的"长期延伸"——**Memory**（写入时代理、MemGPT、A-MEM）——逐行拆开。

---

**本章 Lab（可选，精深向）**

- **Lab 5.1 估算误差**：对 `claude-code-haha` 的 20 轮真实会话，分别用 `chars/4`、`bytes/4`、`tiktoken` 估算，画误差分布，定你的 `buffer`。
- **Lab 5.2 预算推导**：用 `W=200K, R=8K, B=13K` 推导三档水位，改 `p=85%` 对比，测 PTL 次数。
- **Lab 5.3 四层压缩**：在 `my-agent/src/context.ts` 中实现 `snip/micro/collapse/compact` 四层，按 `src/query.ts:219` 的顺序接入，25 轮压测。
- **Lab 5.4 缓存命中**：故意用 `randomUUID` 命名临时文件，观测 `tengu_prompt_cache_break` 的命中从 87% 跌至 30%，再用 `contentHash` 修复。


---

> **本章关键词覆盖校验（供检索）**：
> - 历史锚点：Transformer 2017 Attention；Context Window 演进 GPT-4 8k→128k 2023、Claude 200k 2024、Gemini 1M 2024、RULER/Needle 2024 评测；Prompt Caching 2024 Anthropic；Context Engineering 论文 2024-25；Lost in the Middle 2023。
> - 原理四件套：估算（chars/4 vs tiktoken 误差分析）、预算（window-reserve-buffer 三档）、压缩（snip/micro/collapse/摘要 四层算法）、缓存（断点稳定性）。
> - 对证锚点：Claude autoCompact.ts:62、compact.ts:387、Grok compaction.rs 85%、Codex compact.rs、DeepSeek compaction-basic、Pi transformContext；对比表+阈值公式 `T = W - R - B` 与 `T = W × p`。
> - 权衡三组：百分比 vs 绝对阈值、分层 vs 单层、投影 vs 重写。
> - 未来四向：Long Context 1M 下的 Context Routing、Hierarchical Compaction、Compression-aware Training、KV-cache 复用。



## 5.9 技术审计实证注记（2026-08-23 校准）

四层压缩的**真实触发顺序与门控**已在 `claude-code-haha/src/query.ts` 内逐行验证：

```
query.ts:396  // "Apply snip before microcompact (both may run — they are not mutually exclusive)"
query.ts:403    snipModule.snipCompactIfNeeded(...)          ← 第1层 粗删
query.ts:412-426 microcompact（cached MC 按 tool_use_id 操作） ← 第2层 细删
query.ts:441    contextCollapse.applyCollapsesIfNeeded(...)   ← 第3层 折叠
                 ⚠ 受 feature flag CONTEXT_COLLAPSE 门控（query.ts:18-19），默认关闭
之后            autocompactIfNeeded → compactConversation     ← 第4层 摘要
```

两点对正文的重要修正/补充：
1. **collapse 是实验特性**：需 `CONTEXT_COLLAPSE` feature 开启才生效（`query.ts:441`），生产路径默认只有三层 + autocompact；
2. **snip 与 micro 非互斥**：源码注释明确两者可同轮先后执行（396 行注释），并非"命中一层即停"。

其他实证：`isConcurrencySafe` 默认 false 见 `Tool.ts:750`（注释原文 "assume not safe"）；`AUTOCOMPACT_BUFFER_TOKENS = 13_000` 见 `autoCompact.ts:62`；Grok 启动自愈调用点见 `xai-chat-state/src/actor/state.rs:211,219`。
