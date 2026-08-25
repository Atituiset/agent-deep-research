# 第8章 模型抽象与多 Provider

> 模型抽象层决定 Agent 能跑在多少环境、能多快接入新模型、以及失败时能否优雅降级。七家从"单 SDK 直连"演进到"适配器剥除"，本质是在回答：**当协议分裂、计费分账、鉴权归因相互纠缠时，抽象边界应该画在哪里**。

**本章目标**：读完能（1）按时间轴复述 Provider 抽象与协议分化的三次分裂；（2）手绘 Provider→Adapter→PreparedLlmCall→Retry→计费 的五层分层图与 StreamChunk 状态机；（3）对照各家源码锚点逐行解释"适配器剥除"为何成为 2026 的新共识；（4）在"单 SDK / AI SDK / 自建适配器"三选一时给出量化权衡；（5）对 Model Router 等五个前沿方向提出可验证假设。

**阅读方式**：配合 `appendix-sources.md` 的锚点表，建议左侧开源码、右侧读本章；每节后的**反例**与**公式**用于自检"真懂"。

---

## 8.1 历史脉络：从 Function Calling 到多协议分裂

> 没有 Function Calling 的标准化，就没有 Tool Use 的可移植；没有多 Provider 的并存，就没有"抽象层厚度"的分化；没有推理侧的 `reasoning_effort` 分层，就没有流式与非流式的六端点爆炸。

### 8.1.1 时间轴与一句贡献

| 年份 | 事件 / 系统 | 载体 | 形态 | 一句话核心贡献 |
|------|-------------|------|------|----------------|
| 2022-10 | **LangChain** `BaseChatModel` | 开源框架 | 首次 Provider 抽象 | 把 `LLM(lang) → ChatModel(messages)` 统一为 `BaseLLM`，但抽象过厚（chain/memory 耦合），成为"反面教材"中的可移植性起点 |
| 2023-06 | **OpenAI Function Calling** | API `chat/completions` 新增 `functions`/`function_call` | `ChatCompletions + functions[]` | 首次把"工具调用"从"prompt 技巧"提升为**协议原语**；`tool_calls` 的 `id + function{name,arguments(JSON)}` 三元组成为后续所有 Provider 的互操作最小集 |
| 2023-11 | **OpenAI Parallel Function Calling + `tools`/`tool_choice`** | `gpt-4-1106-preview` | `ChatCompletions + tools[] + parallel` | 支持单轮多 `tool_calls` 并行，Agent 的"批量工具编排"成为可能；但 `arguments` 仍为未流式增量的完整 JSON，埋下 SSE 增量解析的坑 |
| 2023-12 | **Vercel AI SDK 3.0 `LanguageModelV3`** | `@ai-sdk/*` | `BundledSDK.languageModel(modelId)` | 以 `LanguageModelV3{doGenerate,doStream}` 双方法统一流/非流，`AI SDK` 成为 TS 栈"10+ provider 即插即用"的事实薄抽象层 |
| 2023-08 | **LiteLLM** `completion()` | Python Proxy | `model="provider/model"` 字符串路由 | 用"字符串即路由"极致简化多 Provider 调用；代价是类型丢失，`reasoning_effort` 等新参数需 `extra_body` 透传 |
| 2024-05 | **Anthropic Messages API + Tool Use GA** | `api.anthropic.com/v1/messages` | `Messages + tool_use/tool_result + cache_control` | 把 `system` 提升为顶级字段、`tool_use` 的 `input` 为原生 JSON（非字符串）、`cache_control: ephemeral` 成为 Prompt Caching 标准；与 ChatCompletions 首次**协议分化** |
| 2024-07 | **OpenAI Structured Outputs `response_format: json_schema`** | `gpt-4o-2024-08-06` | `ChatCompletions + strict json_schema` | `tools.arguments` 之外的第二条结构化路径；`strict:true` 保证 100% schema 遵从，Agent 的"产出即契约"从 prompt 约束转为协议约束 |
| 2024-09 | **OpenAI Responses API** | `api.openai.com/v1/responses` | `Responses + reasoning + stream` | 新增**有状态**的 `Responses` 协议：`previous_response_id` 链式、`reasoning.effort` 一等公民、`stream` 事件为 `response.*` 而非 `chat.completion.chunk`；与 ChatCompletions **同厂分化** |
| 2024-12 | **Anthropic `thinking` / OpenAI `reasoning_effort` / DeepSeek `reasoning_content`** | 多厂 | `reasoning_effort: none\|low\|medium\|high` | 推理侧从"隐式 CoT"变为**显式预算参数**，`stream` 需新增 `reasoning`/`thinking` delta 通道，Adapter 的归一复杂度陡增 |
| 2025-06 | **Grok 三后端×六端点定型** | `xai-grok-sampler` | `chat_completions/responses/messages × stream/non-stream` | 单一 `SamplingClient` 需同时适配三协议×两形态=六端点，`deserialize_response_event()` 容忍 `x_search` 等厂私有 Tool，成为"多协议适配的极值案例" |
| 2025-11 | **DeepSeek `dsh-llm` 适配器剥除** | `packages/llm/*` | `PreparedLlmCall{config, adapterDefaults, retryPolicy}` | 提出"适配器注入的默认参数不污染上层插件"的**剥除原则**，`adapterDefaults` 经 `waterfall` 显式剥离，插件看到"干净的业务意图" |
| 2026-03 | **Grok `context_details` live 重写** | `xai-grok-sampler/src/lib.rs:apply_terminal_event_overrides()` | `live vs cumulative` 分账 | 把"上下文长度"与"计费用量"从同一 `total_tokens` 拆为两套账本，解决服务端 loop（`web_search/x_search`）的 inflate，成为计费分离的标杆 |

### 8.1.2 三次范式位移

```
Function Calling (2023-06)
  "怎么让模型稳定产出可解析的工具调用"
        │
        ▼
Provider 抽象 (2022 LangChain → 2023 AI SDK / LiteLLM)
  "怎么让同一套 Agent 代码跑在不同厂商的 API 上"
        │
        ▼
协议分裂 (2024 Messages vs ChatCompletions vs Responses)
  "同一家厂商内部为何出现多协议，Adapter 如何收敛"
        │
        ▼
推理与流式分层 (2024-2026 reasoning_effort + stream/non-stream)
  "怎么在六端点与 reasoning 通道间保持 StreamChunk 的单一形状"
```

**位移 1 — 从"单协议工具调用"到"Provider 抽象"**

- **LangChain 2022** 的 `BaseChatModel` 把"调模型"抽象为 `generate(messages) → ChatResult`，但 chain/memory/tool 强耦合，后续 AI SDK 的批评是"抽象过厚，迁移成本高于重写"。
- **AI SDK 2023** 的矫正是"薄抽象"：仅抽象 `LanguageModelV3{doGenerate,doStream}` + `Provider{languageModel(modelId)}`，工具、上下文、重试均不在 Provider 层，OpenCode 的 `BundledSDK` 即直接复用此层，10+ provider 零改动接入。
- **LiteLLM 2023** 走另一极端：`model="anthropic/claude-3-5-sonnet"` 字符串路由，`completion()` 单函数打通所有 Provider，代价是 `reasoning_effort/maxTokens` 等新参数只能走 `extra_body`，类型与校验丢失。

> 教训：**Provider 抽象的厚度 = 可移植性 × 类型安全 的折衷**。AI SDK 的"薄而有型"（`LanguageModelV3` 双方法 + `zod` 校验）在七家中胜出。

**位移 2 — 从"单协议"到"协议分化"**

```
ChatCompletions (OpenAI 2023-06)
  POST /v1/chat/completions
  { model, messages[{role,content}], tools[{function}], tool_choice }
  SSE: data: {"choices":[{"delta":{"tool_calls":[{"function":{"arguments": "..."}}]}}]}

Messages (Anthropic 2024-05)
  POST /v1/messages
  { model, system, messages[{role,content:[{type:"tool_use",input:{}}]}], tools, cache_control }
  SSE: event: content_block_delta  data: {"delta":{"type":"input_json_delta","partial_json":"..."}}

Responses (OpenAI 2024-09, xAI 2025)
  POST /v1/responses
  { model, input, reasoning:{effort:"medium"}, previous_response_id, stream }
  SSE: event: response.output_item.delta  data: {"delta":{"type":"..."},"item_id":"..."}
```

分化根因并非"厂商竞争"，而是**能力分化**：

- `ChatCompletions` 为"无状态单轮"优化，`Messages` 为"长上下文+缓存"优化（`cache_control` + `system` 顶级），`Responses` 为"有状态多轮+推理"优化（`previous_response_id` + `reasoning.effort`）。
- Grok 需同时支持三者的理由是**部署分化**：`chat_completions` 跑在通用推理栈，`responses` 跑在带 `reasoning` 的思考栈，`messages` 跑在 Anthropic 兼容栈（Bedrock/Vertex 透传），单 Agent 需按"模型×后端×流形态"六选一。

**位移 3 — 从"inference 参数"到"reasoning 预算"**

- 2023 年模型调用仅有 `temperature/max_tokens/top_p` 三件套，`stream: true|false` 为布尔开关；
- 2024 年 `reasoning_effort: none|low|medium|high` 成为一等公民（OpenAI o1/o3、Grok、DeepSeek R1），`reasoning_content/thinking` 成为与 `text` 并列的第二输出通道；
- 流式因此从"单 text delta 通道"扩展为"text + reasoning + tool_use"三通道交织，`BlockAssembler` 需按 `id` 分流累积，`StreamChunk` 的 `type` 枚举成为 Adapter 归一的核心。

### 8.1.3 为什么要按此脉络读源码

- 读 OpenCode `packages/opencode/src/provider/provider.ts:100` 的 `BundledSDK` 时，问自己：若无 2023-06 的 Function Calling 统一 `tool_calls{id,name,arguments}` 三元组，`LanguageModelV3` 如何用单一形状适配 10+ Provider？
- 读 Grok `xai-grok-sampler/src/lib.rs:SamplingClient` 的六端点 `match api_backend { ChatCompletions|Responses|Messages }` 时，对照 2024-09 的 Responses 分化：为何 `stream: true` 的 SSE 事件名在三协议下完全不同（`choices.delta` vs `content_block_delta` vs `response.output_item.delta`），却能在 `deserialize_response_event()` 后收敛为同一 `StreamChunk`？
- 读 DeepSeek `packages/llm/llm/src/assembler.ts:BlockAssembler` 时，注意 2024-12 的 `reasoning_effort` 如何让 `Chunk{type: 'reasoning'|'text'|'tool_use'}` 从两态变为三态——这解释了为何 Adapter 必须显式处理 `reasoning` 累积器而非仅 `tool_use`。

---

## 8.2 原理：分层、归一、剥除、重试与计费

> 九家实现的共性链路可抽象为五层，每一层都在回答"谁负责什么、谁不该看到什么"。

### 8.2.1 五层分层图

```
用户意图（LlmCallConfig）
  { model, messages, tools, systemPrompt, maxTokens, reasoningEffort, stream, ... }
     │
     ▼
┌─────────────────────────────────────────────────────────────────┐
│ Layer 1  Provider（厂商接入层）                                  │
│   职责：把 modelId 字符串路由到具体厂商 SDK / HTTP endpoint       │
│   代表：OpenCode BundledSDK.languageModel(modelId)               │
│         Pi getApiKey(provider) 动态取 token                      │
│         Grok SamplerConfig{base_url, api_backend, model}         │
│   不变量：Provider 只做"路由与鉴权"，不碰消息形状与重试           │
├─────────────────────────────────────────────────────────────────┤
│ Layer 2  Adapter（协议归一层） ★ 核心复杂度                       │
│   职责：把三协议×两形态的 SSE/JSON 归一为 StreamChunk，         │
│         再经 BlockAssembler 聚合为 Block                         │
│   代表：DeepSeek packages/llm/llm/src/assembler.ts               │
│         Grok deserialize_response_event() 容忍 x_search          │
│         Claw OpenAICompat vs ClawProvider 双实现                │
├─────────────────────────────────────────────────────────────────┤
│ Layer 3  PreparedLlmCall（意图净化层） ★ 2026 新趋势             │
│   职责：adapterDefaults 显式剥除，产出干净的 LlmCallConfig 供插件 │
│   代表：DeepSeek prepareCall(config,signal)→{config,              │
│                adapterDefaults, retryPolicy, context}            │
│         Grok context_details live 重写                           │
│   不变量：插件看到的是"业务意图"，而非"某适配器的默认重试/长度"  │
├─────────────────────────────────────────────────────────────────┤
│ Layer 4  Retry / Attribution（可靠性与归因层）                   │
│   职责：失败归一 normalizeLlmFailure + 指数退避 + 401 归因截断  │
│   代表：DeepSeek adapter-failure.ts:normalizeLlmFailure()       │
│         Grok Auth401AttributionCallback + SENT_BEARER_PREFIX_LEN │
│         Codex responses_retry.rs 指数退避+降级                   │
├─────────────────────────────────────────────────────────────────┤
│ Layer 5  计费/上下文分账（观测层）                                │
│   职责：live（驱动压缩） vs cumulative（驱动计费）分离           │
│   代表：Grok apply_terminal_event_overrides() 重写 total_tokens  │
│         DeepSeek markAgentLoopRequest() 打标 + dsh-token-meter  │
└─────────────────────────────────────────────────────────────────┘
     │
     ▼
  LLM 采样（stream: Chunk* → Block* → AssistantMessage）
```

**分层不变量**：

- **I1 单向依赖**：`Provider → Adapter → PreparedLlmCall → Retry → 计费`，上层不感知下层细节，下层不篡改上层意图（剥除保证）。
- **I2 形状收敛**：无论底层是 `chat.completion.chunk` 还是 `response.output_item.delta`，经 Adapter 后必为 `StreamChunk{seq, type, delta, id?}` 的单一形状。
- **I3 失败归一**：无论底层是 `429 retryAfter` 还是 `401 invalid_api_key` 还是 `PTL prompt_too_long`，经 `normalizeLlmFailure()` 后必为 `LlmError{code, status, retryable, retryAfterMs}` 的单一形状。

### 8.2.2 Adapter 归一：SSE / Responses / Chunks → StreamChunk → Block

#### 1) 为何需要两级归一

```
原始 SSE 事件（厂商异构）
  OpenAI ChatCompletions:  data: {"choices":[{"delta":{"tool_calls":[{"index":0,"function":{"arguments":"{\"ci"}}]}}]}
  Anthropic Messages:      event: content_block_delta\ndata: {"delta":{"type":"input_json_delta","partial_json":"{\"ci"}}
  OpenAI Responses:        event: response.output_item.delta\ndata: {"delta":{"type":"tool_call","arguments":"{\"ci"},"item_id":"call_123"}

        │  deserialize_response_event() / SSE parser（容忍 x_search 等厂私有 Tool）
        ▼
  StreamChunk（单一形状，增量）
  { seq: 42, type: 'tool_use'|'text'|'reasoning', delta: "{\"ci", id: "call_123" }

        │  BlockAssembler.push(chunk)（按 id 累积，type 分流）
        ▼
  Block（聚合，可执行）
  { id: "call_123", kind: 'tool', state: 'end', content: "{\"city\":\"Paris\"}" }
  { id: "text_0",   kind: 'text', state: 'delta', content: "The weather" }
```

**一级归一（事件→Chunk）**解决**协议分化**：三协议的 SSE 事件名、JSON 路径、Tool 字段名均不同，但增量语义一致——"某 id 的某 type 追加了 delta"。Grok 的 `deserialize_response_event()` 需显式容忍 `x_search` 等 xAI 特有 Tool，否则 `serde` 严格反序列化会整轮失败。

**二级归一（Chunk→Block）**解决**增量累积**：`tool_use` 的 `arguments` 以 `partial_json` 碎片到达，需按 `id` 累积至 `isCompleteJson(cur)` 才可 `JSON.parse` 并派发执行。`BlockAssembler` 即此累积器。

#### 2) StreamChunk 状态机

```
                    ┌──────────────────────────────────────┐
                    │  StreamChunk 输入（按 seq 递增）      │
                    └──────────────┬───────────────────────┘
                                   │
              ┌────────────────────┼────────────────────┐
              │                    │                    │
              ▼                    ▼                    ▼
     type='text'          type='reasoning'      type='tool_use' (id=call_123)
              │                    │                    │
              ▼                    ▼                    ▼
     ┌─────────────┐      ┌──────────────┐     ┌───────────────────┐
     │ text 累积器 │      │ reasoning    │     │ inFlight[id] +=   │
     │ emit delta  │      │ 累积器       │     │ delta             │
     │ state=delta │      │ state=delta  │     │                   │
     └──────┬──────┘      └──────┬───────┘     │ isCompleteJson?   │
            │                    │             │  ├─ no → delta    │
            │                    │             │  └─ yes → end     │
            │                    │             └────────┬──────────┘
            │                    │                      │
            └────────────────────┼──────────────────────┘
                                 │
                                 ▼
                    ┌────────────────────────┐
                    │ Block[] 输出           │
                    │ {id,kind,state,content}│
                    │ state ∈ {start,delta,end}│
                    └────────────────────────┘

  伪代码（DeepSeek packages/llm/llm/src/assembler.ts 归一后）：

  type Chunk = { seq: number; type: 'text'|'tool_use'|'reasoning'; delta: string; id?: string };
  type Block = { id: string; kind: 'text'|'tool'|'reasoning'; state: 'start'|'delta'|'end'; content: string };

  class BlockAssembler {
    private inFlight = new Map<string, string>(); // id → accumulated
    private textBuf = "";
    private reasoningBuf = "";
    private seqs: number[] = [];                  // sourceEventSeqs 供回溯

    push(chunk: Chunk): Block[] {
      this.seqs.push(chunk.seq);
      if (chunk.type === 'tool_use') {
        const id = chunk.id!;
        const cur = (this.inFlight.get(id) ?? '') + chunk.delta;
        this.inFlight.set(id, cur);
        // 关键：仅当 JSON 完整才发射 end，否则仅 delta
        if (isCompleteJson(cur)) return [{ id, kind: 'tool', state: 'end', content: cur }];
        return [{ id, kind: 'tool', state: 'delta', content: chunk.delta }];
      }
      if (chunk.type === 'reasoning') {
        this.reasoningBuf += chunk.delta;
        return [{ id: 'reasoning', kind: 'reasoning', state: 'delta', content: chunk.delta }];
      }
      this.textBuf += chunk.delta;
      return [{ id: 'text', kind: 'text', state: 'delta', content: chunk.delta }];
    }

    getToolCalls(): { id: string; name: string; arguments: unknown }[] {
      // 仅对 state=end 的 inFlight 做 JSON.parse
      return [...this.inFlight.entries()]
        .filter(([, v]) => isCompleteJson(v))
        .map(([id, json]) => ({ id, ...JSON.parse(json) }));
    }

    // 失败回溯：若流中中断，按已收 seqs 决定重放或截断
    getSourceEventSeqs(): number[] { return this.seqs; }
  }
```

**状态机不变量**：

- `tool_use` 的 `delta` 必须按 `id` 分桶累积，跨 `id` 乱序到达时不得串扰（如并行 `tool_calls[0]` 与 `tool_calls[1]` 交替增量）；
- `isCompleteJson` 需容忍`截断 JSON`（`{"city":"Par` 非完整），仅 `{"city":"Paris"}` 才 `end`；
- `reasoning` 通道与 `text` 通道需独立累积器，否则 `thinking` 的增量会污染 `text` 的 `shouldStop` 判定。

#### 3) Grok 的容忍式反序列化

```rust
// xai-grok-sampler/src/lib.rs 伪代码
fn deserialize_response_event(raw: &str) -> Result<StreamChunk, _> {
    // 关键：对未知 tool 类型（如 x_search）不报错，而是降级为 GenericTool
    let event: Value = serde_json::from_str(raw)?;
    match event["type"].as_str() {
        Some("tool_use") | Some("x_search") | Some("web_search") => {
            // 统一映射为 StreamChunk{type: tool_use}
            Ok(StreamChunk { r#type: ToolUse, delta: event["partial_json"], id: event["tool_call_id"] })
        }
        Some("thinking") | Some("reasoning") => {
            Ok(StreamChunk { r#type: Reasoning, delta: event["delta"], id: None })
        }
        _ => Ok(StreamChunk { r#type: Text, delta: event["delta"], id: None }),
    }
}
```

> 若此处对 `x_search` 严格报错，则 xAI 线上新增 Tool 即导致所有历史版本 Agent 全量失败——**容忍即兼容性**。

### 8.2.3 PreparedLlmCall 与适配器剥除

#### 1) 问题：适配器默认参数污染插件视图

```
用户意图（干净）：
  LlmCallConfig { model: "claude-opus", messages, tools, maxTokens: 4096 }

Adapter 注入（隐式）：
  adapterDefaults { reasoningEffort: "medium", maxTokens: 16384, stream: true }

若不剥除，插件看到的是：
  LlmCallConfig { model, messages, tools, maxTokens: 16384, reasoningEffort: "medium" }
  插件无法区分"用户显式要求 16384"还是"适配器默认 16384"，改写时可能误删或误保留
```

#### 2) 解法：prepareCall 的显式剥除

```ts
// DeepSeek packages/llm/* 归一后伪代码
type LlmCallConfig = {
  model: string;
  messages: Message[];
  tools: ToolSpec[];
  systemPrompt?: string;
  maxTokens?: number;
  reasoningEffort?: 'none'|'low'|'medium'|'high';
  stream?: boolean;
  // ... 仅业务意图，无 adapter 细节
};

type PreparedLlmCall = {
  config: LlmCallConfig;          // 干净的业务意图（供插件改写）
  adapterDefaults: {              // 适配器注入的默认值（显式剥离）
    reasoningEffort?: string;
    maxTokens?: number;
    streamToolCalls?: boolean;
  };
  retryPolicy: RetryPolicy;       // 重试策略（llm-retry 插件注入）
  context: { window: number; signal: AbortSignal };
};

function prepareCall(config: LlmCallConfig, signal: AbortSignal): PreparedLlmCall {
  // 1. 适配器注入默认值（如 deepseek 默认 reasoningEffort=medium）
  const adapterDefaults = resolveAdapterDefaults(config.model);
  // 2. 显式记录哪些字段来自 adapter（而非用户）
  const injectedKeys = new Set(Object.keys(adapterDefaults));
  // 3. 返回分离结构：config 保持干净，adapterDefaults 单独存放
  return { config, adapterDefaults, retryPolicy: resolveRetryPolicy(config.model), context: { window: 200_000, signal } };
}

function markAgentLoopRequest(call: PreparedLlmCall): void {
  // 打标，供插件识别"这是 loop 请求而非单次补全"
  (call.context as any).__agentLoop = true;
}

// 插件视角（waterfall 'agent/request'）：
async function buildRequest(call: PreparedLlmCall): Promise<Request> {
  // 关键：requestProposal 阶段显式去除 adapterDefaults，再经 waterfall 供插件改写
  const proposal = {
    header: buildHeader(call.config),           // 仅含 config，不含 adapterDefaults
    body: buildBody(call.config),               // 同上
  };
  // waterfall 链：pluginA → pluginB → ... → finalRequest
  const final = await waterfall('agent/request', proposal, { call });
  // 最终合并：finalRequest + adapterDefaults（适配器默认仅在最终发送时合入）
  return mergeWithAdapterDefaults(final, call.adapterDefaults);
}

// 去重：canonicalHeader / headerEquals 保证 proposal 与最终 header 的幂等
function canonicalHeader(h: Record<string,string>): Record<string,string> {
  return Object.fromEntries(Object.entries(h).map(([k,v]) => [k.toLowerCase(), v.trim()]));
}
```

**剥除的时序图**：

```
时间 ──────────────────────────────────────────────────────────►

调用方          prepareCall        Adapter        Plugin链        HTTP
  │                │                 │               │             │
  ├─ LlmCallConfig─┼─► config ───────┼───────────────┼────────────►│  不含 adapterDefaults
  │                │   adapterDefaults│               │             │
  │                │                 │    waterfall  │             │
  │                │                 │ 'agent/request'│             │
  │                │                 │  proposal{header,body}      │
  │                │                 │◄──────────────┤             │
  │                │                 │ plugin 改写后 │             │
  │                │                 │ finalRequest  │             │
  │                │                 │───────────────┼─ merge ────►│  合入 adapterDefaults
  │                │                 │               │  发送       │
  │                │                 │               │             │
  │  失败时         │                 │  waterfall    │             │
  │                │                 │ 'agent/request-error'       │
  │                │                 │  决定 retry|throw           │
```

> **为什么要剥除**：插件看到的 `LlmCallConfig` 应是"干净的业务意图"，而非"某适配器的默认重试/长度限制"；审计日志记录的应是 `finalRequest`（含 adapterDefaults 的真实发送），而插件改写的应是 `proposal`（不含 adapterDefaults 的意图）。两者分账，审计不丢、改写不脏。

#### 3) Grok 的上下文剥除：live 重写

```rust
// xai-grok-sampler/src/lib.rs:apply_terminal_event_overrides()
// 解决服务端 loop（web_search/x_search）的 inflate：服务端在 turn 内多次调工具，
// 其 input/output 会被计入 total_tokens，导致 context 进度虚高、auto_compact 过早触发

fn apply_terminal_event_overrides(
    terminal: &mut UsageEvent,      // 服务端返回的累计用量
    context_details: &ContextDetails // live 上下文详情（input/output 为当前轮 live 长度）
) {
    // total_tokens 重写为 live 长度（input+output），供 /context 进度与 auto_compact 阈值
    terminal.total_tokens = context_details.input + context_details.output;
    // input/output/cached 保持 cumulative，供计费
    // terminal.input_tokens  = 保持原 cumulative（不重写）
    // terminal.output_tokens = 保持原 cumulative
    // terminal.cached_tokens = 保持原 cumulative
}

// 调用点伪代码
let mut usage = parse_terminal_event(&sse_last_event)?;
if let Some(details) = response.context_details {
    apply_terminal_event_overrides(&mut usage, &details);
    // 此后：usage.total_tokens 为 live（驱动压缩），usage.input/output 为 cumulative（驱动计费）
}
```

> **原则**：`live 长度驱动压缩，cumulative 用量驱动计费`，两者不可混用（Ch5/Ch6 已述，此处为模型层的对应实现）。

### 8.2.4 失败归一与重试：normalizeLlmFailure + 401 归因

#### 1) 失败归一

```ts
// DeepSeek packages/llm/llm/src/adapter-failure.ts 归一后
type LlmFailure = {
  message: string;
  code: 'rate_limited'|'overloaded'|'prompt_too_long'|'auth'|'network'|'unknown';
  status?: number;           // HTTP status
  retryAfterMs?: number;     // Retry-After 头解析
  requestId?: string;        // x-request-id 供归因
};

type LlmError = {
  failure: LlmFailure;
  chain: unknown[];          // errorChain() 保留原始错误链
  retryable: boolean;
};

function normalizeLlmFailure(raw: unknown): LlmError {
  const chain = errorChain(raw); // 展开 cause 链
  const status = extractStatus(raw);
  const retryAfterMs = extractRetryAfter(raw);
  const requestId = extractRequestId(raw);

  // 401 归因：normalizeApiKey 校验
  if (status === 401) {
    return { failure: { message: 'auth failed', code: 'auth', status, requestId }, chain, retryable: false };
  }
  if (status === 429) {
    return { failure: { message: 'rate limited', code: 'rate_limited', status, retryAfterMs, requestId }, chain, retryable: true };
  }
  if (isPromptTooLong(raw)) {
    return { failure: { message: 'prompt too long', code: 'prompt_too_long', status, requestId }, chain, retryable: false };
  }
  // ... overloaded/network 等
  return { failure: { message: String(raw), code: 'unknown', status, requestId }, chain, retryable: isNetworkError(raw) };
}

function normalizeApiKey(key: string): string {
  // Grok/DeepSeek 共识：仅允许可打印 ASCII，拒绝控制字符与空格
  if (!/^[\x21-\x7E]+$/.test(key)) throw new Error('invalid api key charset');
  return key.trim();
}
```

#### 2) 重试退避公式

```
设：
  attempt = 0,1,2,..., maxAttempts-1
  baseMs = 500ms（Codex 默认）或 1000ms（Grok 默认）
  capMs  = 30_000ms
  jitter ∈ [0, 0.2)（±20% 抖动，避免惊群）
  retryAfterMs = 服务端 Retry-After 头（若有，优先）

退避（DeepSeek llm-retry + Codex responses_retry.rs 归一）：

  if retryAfterMs != null:
    delay = retryAfterMs × (1 + jitter)          // 尊重服务端
  else:
    delay = min(capMs, baseMs × 2^attempt) × (1 + jitter)  // 指数退避

  总等待（3 次重试，base=500ms，无 Retry-After）：
    attempt0:  500 × (1+j)  ≈  500—600ms
    attempt1: 1000 × (1+j)  ≈ 1000—1200ms
    attempt2: 2000 × (1+j)  ≈ 2000—2400ms
    合计：约 3.5—4.2s（含 jitter）

重试闸（waterfall 'agent/request-error'）：

  waterfall('agent/request-error', { error: LlmError, attempt })
    → plugin 决定 { decision: 'retry' | 'throw', delayMs? }
    → 若 retry，则按上式 sleep 后重进 L2 sampling loop
    → 若 throw，则直接冒泡至 Loop 外层（可能触发模型降级 FallbackTriggeredError）
```

**重试的精确语义（DeepSeek）**：

```ts
// packages/llm/llm-retry 伪代码
export const llmRetry = definePlugin({
  id: "llm-retry",
  hooks: {
    "agent/request-error": async (ctx, next) => {
      const err = normalizeLlmFailure(ctx.error);
      if (!err.retryable) return next({ decision: 'throw' });
      if (ctx.attempt >= ctx.retryPolicy.maxAttempts) return next({ decision: 'throw' });
      if (err.failure.code === 'prompt_too_long') {
        // PTL 不重试采样，而是触发 reactiveCompact 后重试
        await reactiveCompact(ctx.session);
        return next({ decision: 'retry', delayMs: 0 });
      }
      const delay = backoff(ctx.attempt, err.failure.retryAfterMs);
      return next({ decision: 'retry', delayMs: delay });
    },
  },
});
```

#### 3) 401 归因与 SENT_BEARER_PREFIX_LEN

```rust
// Grok xai-grok-auth + xai-grok-sampler/src/lib.rs
const SENT_BEARER_PREFIX_LEN: usize = 12; // 仅取 bearer 的前 12 字符

struct Auth401AttributionCallback {
    // 记录 401 时的"消费者"与"已发送 bearer 前缀"，供全链路归因
    fn record_401(&self, consumer: SamplingConsumer, sent_bearer_prefix: &str);
}

enum SamplingConsumer {
    Sampler,        // 采样器本身
    Tool { name: String }, // 某工具透传的 key
    Sdk { name: String },  // 某 SDK 透传的 key
}

// 发送侧截断
fn truncate_to_prefix(bearer: &str) -> &str {
    &bearer[..bearer.len().min(SENT_BEARER_PREFIX_LEN)]
}

// 调用点
let prefix = truncate_to_prefix(&bearer_token); // 仅 12 字符进日志与回调
auth_callback.record_401(SamplingConsumer::Sampler, prefix);

// 归因链路：sampler → callback → shell/auth/manager.rs token_suffix 强一致
// manager.rs 侧同样仅存 token_suffix（后 4 位）+ prefix（前 12 位），全量密钥永不进日志
```

> **安全不变量**：全量 `bearer` / `x-api-key` **永不**进入日志、trace、errorChain；仅 `truncate_to_prefix` 的 12 字符前缀可用于归因"哪把 key 401"。Grok 的 `SENT_BEARER_PREFIX_LEN=12` 与 `shell/auth/manager.rs` 的 `token_suffix` 强一致，是"失败归因"中最易被忽视的安全细节——也是本章必考点。

### 8.2.5 计费分离：live vs cumulative

| 维度 | live（驱动压缩） | cumulative（驱动计费） | 分离点 |
|------|------------------|------------------------|--------|
| **定义** | 当前上下文的**实际** token 长度（去重、去 inflate 后） | 自会话开始的**累计** input+output（含服务端 loop 的 inflate） | `apply_terminal_event_overrides()` |
| **来源** | `context_details.input + output`（Grok） / `session.estimatedTokens`（DeepSeek `dsh-token-meter`） | `terminal.input_tokens / output_tokens / cached_tokens` | terminal event |
| **用途** | `should_auto_compact(live, window)` 的分子；`/context` 进度条 | `UsageLedger.prompt_usage / session_usage`；账单 | — |
| **失败模式** | 若用 cumulative 驱动压缩，则服务端 `web_search` loop 会让 `total_tokens` 虚高 30—50%，`85%` 阈值过早触发，无效压缩 | 若用 live 驱动计费，则多轮 `web_search` 的成本被低估，用户少付费 | 必须分账 |

```
观测时序（Grok 为例）：

  turn 内多次采样（含 web_search/x_search 子调用）
    │
    ├─ 服务端累计：input=80K, output=40K, total=120K（含 inflate）
    │
    ├─ context_details（live）：input=45K, output=20K, total=65K（真实上下文）
    │
    ▼
  apply_terminal_event_overrides()
    │
    ├─ usage.total_tokens = 65K  →  should_auto_compact(65K, 200K)=32.5% → 不压缩 ✓
    │   （若用 120K 则 60%，接近阈值，误触发压缩）
    │
    └─ usage.input/output/cached = 80K/40K/cached → 账单按 120K 计费 ✓
        （若用 65K 则少计 55K，资损）
```

---

## 8.3 对证：九家源码对证

> 本节所有锚点均为真实文件与行号（快照 2026-08-22），详见附录 B。对比的不是"有无多 Provider"，而是"抽象边界画在哪里、剥除发生在哪一层、失败如何归因"。

### 8.3.1 总览对比表

| 家 | 抽象形态 | 核心锚点 | 多 Provider | 协议/端点 | 失败与重试 | 鉴权 |
|----|---------|----------|-------------|-----------|------------|------|
| **Claude** | 单 SDK 封装 + Bedrock/Vertex 分支 | `src/services/api/claude.ts:queryModelWithStreaming()` + `src/utils/model/model.ts:getMainLoopModel()` + `src/services/api/bedrock.ts` | `Anthropic` 主 + `Bedrock/Vertex` 兼容（`ANTHROPIC_BEDROCK_BASE_URL` 分支） | `Messages` 单协议 + `cache_control: ephemeral` | `FallbackTriggeredError` + `streamingFallbackOccured` 时 `tombstone` 旧消息并 `stripSignatureBlocks()` + `attemptWithFallback` | `ANTHROPIC_API_KEY` 直连 |
| **Codex** | `model-provider` 三件套 + `login` | `codex-model-provider/` + `model-provider-info/` + `models-manager/` + `login/` + `codex-rs/core/src/tools/spec_plan.rs:117 build_tool_router()` | `openai/chatgpt/lmstudio/ollama/aws-auth`（`feature.Feature` 注册表驱动） | `ChatCompletions` 主 + `Responses` 兼容 | `responses_retry.rs` 指数退避 + 降级 + `model-provider-info` 的 `ModelInfo{model,reasoning_effort,approval_policy}` | `codex-rs/login/` 多源 `getApiKey` |
| **OpenCode** | `BundledSDK` AI SDK 统一 | `packages/opencode/src/provider/provider.ts:100+` + `packages/llm/src/` + `packages/opencode/src/provider/transform.ts:ProviderTransform` | **10+ provider**：`@ai-sdk/anthropic/openai/google/azure/amazon-bedrock/openai-compatible/openrouter/xai/mistral/vertex`（`@opencode-ai/plugin` 动态 `import()`） | `LanguageModelV3.doGenerate/doStream` 统一流/非流 | `wrapSSE(headerTimeout/SSE read timeout)` + `AbortController` + `ProviderTransform` | `getApiKey(provider)` + `googleVertexAnthropicBaseURL()` 多 region |
| **Pi** | `pi-ai` 极简抽象 | `packages/ai/src/` `@earendil-works/pi-ai` + `packages/agent/src/types.ts:StreamFn` | `Anthropic/OpenAI/Google/Mistral/Aws`（`Api/Model/Context/Tool` 四抽象） | `ChatCompletions/Messages` 双协议（`pi-ai` 内封装） | 可注入 `RetryPolicy`（`AgentLoopConfig` 回调） | `getApiKey(provider)` 动态取短时 OAuth token |
| **DeepSeek** | `dsh-llm` 三适配器 + 显式剥除 | `packages/llm/*` `dsh-llm{LlmCallConfig,PreparedLlmCall,StreamChunk}` + `llm-retry` + `llm-pi-ai` + `assembler.ts:BlockAssembler` | `deepseek/pi-ai/retry` 三适配器（`prepareCall(config,signal)→{config,adapterDefaults,retryPolicy,context}`） | `ChatCompletions` 主 + `StreamChunk/BlockAssembler` 归一 | `adapter-failure.ts:normalizeLlmFailure()` + `errorChain()` → `LlmError{failure{message,code,status,retryAfterMs,requestId}}` + `api-key.ts:normalizeApiKey(){^[\x21-\x7E]+$}` + `waterfall 'agent/request-error'` | `normalizeApiKey` 字符集校验 |
| **Grok** | `SamplingClient` 六端点 + 全量透传 | `xai-grok-sampler/src/lib.rs SamplingClient` + `xai-grok-models` + `xai-grok-auth` + `xai-grok-tools/src/bridge.rs ToolBridge` | **三后端×流/非流=六端点**：`chat_completions/responses/messages × stream/non-stream` | `chat_completions/responses/messages` 三协议 + `deserialize_response_event()` 容忍 `x_search` | `SENT_BEARER_PREFIX_LEN=12` 截断 + `Auth401AttributionCallback{record_401(consumer: SamplingConsumer{...}, sent_bearer_prefix)}` + `truncate_to_prefix` | `xai-grok-auth`（`x-api-key/Authorization` + 401 归因） |
| **Claw** | 双 Provider 极简 | `rust/crates/api/src/client.rs` + `sse.rs` + `providers/{claw_provider,openai_compat}.rs` + `rust/crates/runtime/src/session.rs Session{version,messages}` | `ClawProvider/OpenAICompat` 双实现（`ApiClient::stream() → Vec<AssistantEvent>` 批量流） | `ChatCompletions` 兼容（`OpenAICompat`） | 固定 `compact_after_turns=12` + 无指数退避 | 直连 bearer |

### 8.3.2 分家精读

#### Claude — `src/services/api/claude.ts:queryModelWithStreaming()` 的单 SDK 封装

```ts
// src/services/api/claude.ts 骨架（归一后）
export async function* queryModelWithStreaming(
  messages: Message[],
  opts: { model: string; tools: ToolSpec[]; signal: AbortSignal; cacheControl?: CacheControl }
) {
  // 分支：Bedrock / Vertex / 直连
  const baseURL = resolveBaseURL(); // ANTHROPIC_BASE_URL || ANTHROPIC_BEDROCK_BASE_URL || Vertex
  const client = getAnthropicClient(baseURL); // @anthropic-ai/sdk
  const stream = client.messages.stream({
    model: opts.model,
    system: getSystemPrompt(),
    messages: toAnthropicMessages(messages),
    tools: toAnthropicTools(opts.tools),
    cache_control: getCacheControl({ querySource: opts.querySource }), // 5m/1h TTL
  }, { signal: opts.signal });

  for await (const event of stream) {
    if (event.type === 'content_block_delta') yield toStreamChunk(event);
    if (event.type === 'message_delta') yield toUsageEvent(event.usage);
  }
}

// src/utils/model/model.ts:getMainLoopModel()
export function getMainLoopModel(): string {
  // 模型切换靠配置，非 Provider 抽象
  return config.model ?? 'claude-opus-4-7';
}

// Fallback（src/query.ts:219 附近）
async function attemptWithFallback<T>(fn: () => Promise<T>, fallbackModel?: string): Promise<T> {
  try { return await fn(); }
  catch (e) {
    if (isOverloaded(e) && fallbackModel) {
      // tombstone 旧消息，避免悬垂 tool_use
      tombstoneInFlightMessages();
      stripSignatureBlocks(); // 去除 thinking 签名块
      streamingFallbackOccured = true;
      return await queryModelWithStreaming({ ...opts, model: fallbackModel });
    }
    throw new FallbackTriggeredError(e);
  }
}
```

**精读点**：

- **为何选单 SDK**：Claude 早期仅需跑通 Anthropic 主链路，`Bedrock/Vertex` 仅为"兼容分支"（`if baseURL contains bedrock`），模型切换靠 `getMainLoopModel()` 的配置而非 Provider 路由——这是"单 SDK 直连"的典型：**快，但每新增一 Provider 就多一分支**。
- **`cache_control: ephemeral` 的位置**：在 `claude.ts:606 getCacheControl()` 中按 `querySource` 决定 `ttl: 5m|1h`，且 `system/tools/history` 三断点均显式标记，是 Prompt Caching 最精细的实现（见 Ch5）。
- **Fallback 的代价**：`tombstone + stripSignatureBlocks` 需重写 Session 中未闭合的 `tool_use`，否则降级模型的第二轮采样会因"悬垂 `tool_use` 缺 `tool_result`"而 PTL。

#### Codex — `codex-model-provider/` 的三件套 + `responses_retry.rs`

```rust
// 模型三件套（Rust 伪代码）
pub struct ModelInfo {
    pub model: String,                          // "gpt-5" / "o3-mini"
    pub reasoning_effort: Option<ReasoningEffort>, // ReasoningEffort::High
    pub approval_policy: ApprovalPolicy,
    pub base_url: Option<String>,
}

// codex-rs/core/src/tools/spec_plan.rs:117
pub fn build_tool_router(ctx: &StepContext) -> ToolRouter {
    // 每 StepContext 重建，保证 model_visible_specs 与本次快照一致（I2）
    let mut router = ToolRouter::new();
    router.add_core_tool_sources(); // bash/edit/read 等
    router.append_mcp(ctx.mcp_tools); // MCP 动态装卸
    router.finalize_tool_router() // 分区排序 + exposure 分级
}

// responses_retry.rs 伪代码
pub async fn with_retry<T>(f: impl Fn() -> Future<Output=Result<T>>, policy: RetryPolicy) -> Result<T> {
    let mut attempt = 0;
    loop {
        match f().await {
            Ok(v) => return Ok(v),
            Err(e) if is_retryable(&e) && attempt < policy.max_attempts => {
                let delay = backoff(attempt, e.retry_after_ms());
                tokio::time::sleep(delay).await;
                // overloaded 时降级模型
                if e.is_overloaded() { downgrade_model(); }
                attempt += 1;
            }
            Err(e) => return Err(e),
        }
    }
}
fn backoff(attempt: u32, retry_after: Option<Duration>) -> Duration {
    if let Some(d) = retry_after { return d + jitter(); }
    let base = Duration::from_millis(500);
    let cap = Duration::from_secs(30);
    (base * 2u32.pow(attempt)).min(cap) + jitter()
}
```

**精读点**：

- **三件套的分工**：`model-provider` 定义 `ModelInfo` 形状，`model-provider-info` 做模型能力表（`reasoning_effort` 是否支持），`models-manager` 做运行时切换与 `login` 的 token 绑定——这是"配置驱动多 Provider"的标杆，但 Provider 抽象仍在"字符串路由"层（`model="openai/gpt-5"`），未到 `LanguageModelV3` 的薄抽象。
- **`feature.Feature` 注册表**：`chatgpt/collaboration-mode/lmstudio` 等开关以 `Feature` 枚举注册，`ToolSpec` 按 `Feature` 过滤，避免"未启用模型的工具泄露"。
- **每 step 重建 `ToolRouter`**：`build_tool_router()` 在每 `StepContext` 起点重建，保证 `model_visible_specs` 与本次快照一致（I2：Prompt 与 ToolSpecs 同快照），代价是每 step 一次 `RwLock` 读。

#### OpenCode — `packages/opencode/src/provider/provider.ts:100` 的 BundledSDK

```ts
// packages/opencode/src/provider/provider.ts:100 骨架
import { createAnthropic } from '@ai-sdk/anthropic';
import { createOpenAI } from '@ai-sdk/openai';
import { createGoogle } from '@ai-sdk/google';
// ... 10+ provider

export class BundledSDK {
  // 模型字符串即路由：modelId = "anthropic/claude-opus" / "openai/gpt-5" / "google/gemini-2.5-pro"
  languageModel(modelId: string): LanguageModelV3 {
    const [provider, model] = parseModelId(modelId); // "anthropic/claude-opus" → ["anthropic", "claude-opus"]
    switch (provider) {
      case 'anthropic': return createAnthropic({ apiKey: getApiKey('anthropic') })(model);
      case 'openai':    return createOpenAI({ apiKey: getApiKey('openai') })(model);
      case 'google':    return createGoogle({ apiKey: getApiKey('google') })(model);
      // ... bedrock/openrouter/xai/mistral/vertex/openai-compatible
      case 'openai-compatible': return createOpenAICompatible({ baseURL: customBaseURL })(model);
    }
  }
}

// packages/opencode/src/provider/transform.ts:ProviderTransform
export const ProviderTransform = {
  // 统一截断与消息归一
  wrap: (model: LanguageModelV3) => wrapWithTruncate(wrapWithSSE(model)),
};

// SSE 超时（关键细节）
function wrapSSE(model: LanguageModelV3): LanguageModelV3 {
  return {
    ...model,
    doStream: async (opts) => {
      const controller = new AbortController();
      // headerTimeout：首字节超时（如 10s 内未收到 header 即 abort）
      const headerTimer = setTimeout(() => controller.abort(), headerTimeoutMs);
      const stream = await model.doStream({ ...opts, abortSignal: controller.signal });
      clearTimeout(headerTimer);
      // SSE read timeout：流中无数据超时（如 30s 内无 chunk 即 abort）
      return stream.pipeThrough(timeoutTransform(sseReadTimeoutMs));
    },
  };
}

// 多 region 适配
function googleVertexAnthropicBaseURL(region: string): string {
  // "us-central1" → "https://us-central1-aiplatform.googleapis.com/v1/projects/..."
  return `https://${region}-aiplatform.googleapis.com/...`;
}
```

**精读点**：

- **10+ provider 即插即用**：`BundledSDK` 的 `switch(provider)` 覆盖 `@ai-sdk/*` 全生态，新增 Provider 仅需加一 `case`，工具、上下文、重试均无需改动——这是"AI SDK 薄抽象"的最大收益：**Provider 厚度仅一层 `switch`**。
- **动态 `import()`**：`@opencode-ai/plugin` 对 `@ai-sdk/*` 的引入为 `await import('@ai-sdk/anthropic')` 动态式，避免 10+ Provider 的静态依赖膨胀，冷启动仅加载命中 Provider。
- **`wrapSSE` 的双超时**：`headerTimeout` 防"连接假死"（TCP 已建连但服务端未发 header），`SSE read timeout` 防"流中假死"（header 已到但后续 chunk 停滞），两者缺一不可（见 8.4.2）。
- **`googleVertexAnthropicBaseURL()`**：Vertex 的 Anthropic 兼容端点需按 `region` 拼 `baseURL`，是"多 region 适配"的最小实现（见 8.4.4）。

#### Pi — `packages/ai/src/` 的 `@earendil-works/pi-ai` 极简抽象

```ts
// packages/ai/src/ 骨架
export type Api = { chat: (req: ChatRequest) => Promise<ChatResponse>; stream: (req: ChatRequest) => AsyncIterable<StreamChunk> };
export type Model = { id: string; contextWindow: number; supportsTools: boolean };
export type Context = { messages: AgentMessage[]; systemPrompt?: string };
export type Tool = { name: string; description: string; parameters: z.ZodSchema };

// getApiKey 的动态取 token
export async function getApiKey(provider: string): Promise<string> {
  // 支持 Anthropic 的短期 OAuth token（1h TTL），Google 的 ADC，OpenAI 的 env
  const token = await keychain.get(provider) ?? process.env[`${provider.toUpperCase()}_API_KEY`];
  if (isOAuthToken(token)) return await refreshIfExpired(token); // 短时 token 自动刷新
  return normalizeApiKey(token);
}

// AgentLoopConfig 的注入（见 Ch3）
export type AgentLoopConfig = {
  transformContext?: (messages: AgentMessage[], signal: AbortSignal) => Promise<AgentMessage[]>;
  shouldStopAfterTurn?: (ctx: AgentContext) => boolean;
  // StreamFn 即 pi-ai 的 Api.stream 的薄封装
};
export type StreamFn = (model: Model, context: Context) => AsyncIterable<StreamChunk>;
```

**精读点**：

- **四抽象的极简**：`Api/Model/Context/Tool` 仅 4 个 `type`，无 `PreparedLlmCall`/`Adapter` 分层，所有归一在 `pi-ai` 包内完成——这是"教学级薄抽象"：**可读性最高，但剥除与 401 归因需用户自补**。
- **`getApiKey` 的多源**：`keychain → env → OAuth refresh` 三级回退，支持 Anthropic 短期凭证（`oauth_token` 1h 过期前自动 `refresh`），是多环境鉴权的最小可用实现。
- **局限**：无 `SENT_BEARER_PREFIX_LEN` 截断、无 `normalizeLlmFailure` 归一、无 `live vs cumulative` 分账——生产级需在 `pi-ai` 之上自建 L4/L5。

#### DeepSeek — `packages/llm/*` 的 `PreparedLlmCall` 与三适配器

```ts
// packages/llm/llm/src/api-key.ts
export function normalizeApiKey(key: string): string {
  if (!/^[\x21-\x7E]+$/.test(key)) throw new Error('invalid api key: non-printable ASCII');
  return key.trim();
}

// packages/llm/llm/src/adapter-failure.ts
export function normalizeLlmFailure(raw: unknown): LlmError { /* 见 8.2.4 */ }
export function errorChain(e: unknown): unknown[] {
  const chain: unknown[] = [];
  let cur: any = e;
  while (cur) { chain.push(cur); cur = cur.cause ?? cur.error; }
  return chain;
}

// packages/llm/llm/src/assembler.ts:BlockAssembler（见 8.2.2）

// packages/llm/llm/src/index.ts:prepareCall
export function prepareCall(config: LlmCallConfig, signal: AbortSignal): PreparedLlmCall {
  const adapterDefaults = resolveAdapterDefaults(config.model); // 如 deepseek 默认 reasoningEffort=medium
  return { config, adapterDefaults, retryPolicy: defaultRetryPolicy, context: { window: 128_000, signal } };
}
export function markAgentLoopRequest(call: PreparedLlmCall): void {
  (call.context as any).__agentLoop = true; // 供 Cordis 插件识别
}

// 三适配器
// llm-deepseek: 直连 DeepSeek API（ChatCompletions）
// llm-pi-ai:   复用 pi-ai 协议（多 Provider）
// llm-retry:   封装 retryPolicy + waterfall 'agent/request-error'
```

**精读点**：

- **形态最干净**：`LlmCallConfig → PreparedLlmCall{config, adapterDefaults, retryPolicy, context}` 的四字段分离，让"业务意图 / 适配器默认 / 重试策略 / 上下文窗口"四者显式分账，是 2026 年"适配器剥除"的标杆形态。
- **waterfall 剥除**：`buildRequest()` 中 `requestProposal(header)` 去除 `adapterDefaults` 的 `reasoningEffort/maxTokens` 后，经 `waterfall 'agent/request'` 供插件改写，`canonicalHeader/headerEquals` 去重 `request/header`——插件改写永远基于"干净意图"。
- **Cordis 插件化重试**：`llm-retry` 不在 `prepareCall` 内硬编码退避，而是以 `waterfall 'agent/request-error'` 暴露给插件链，`dsh-llm` 的 `markAgentLoopRequest` 打标让重试插件可区分"loop 请求"与"单次补全"的不同退避策略。

#### Grok — `xai-grok-sampler/src/lib.rs SamplingClient` 的六端点

```rust
// xai-grok-sampler/src/lib.rs 骨架
pub struct SamplerConfig {
    pub base_url: String,
    pub model: String,
    pub api_backend: ApiBackend, // ChatCompletions | Responses | Messages
    pub reasoning_effort: Option<ReasoningEffort>, // ReasoningEffort::Medium
    pub stream: bool,
    pub stream_tool_calls: bool, // 是否流式增量 tool_calls
}

pub enum ApiBackend { ChatCompletions, Responses, Messages }

pub struct GrokRequestHeaders {
    pub x_grok_conv_id: String,
    pub x_grok_req_id: String,
    pub x_grok_model_override: Option<String>,
    pub x_grok_session_id: String,
    pub x_grok_turn_idx: u32,
    pub x_grok_agent_id: String,
    pub x_grok_deployment_id: String,
    pub x_grok_user_id: String,
}

impl SamplingClient {
    pub async fn sample(&self, req: SamplerRequest) -> Result<StreamChunk, LlmError> {
        let headers = GrokRequestHeaders::from(&req); // 全量透传供观测
        let endpoint = match (&self.config.api_backend, self.config.stream) {
            (ChatCompletions, true)  => format!("{}/v1/chat/completions", self.config.base_url),
            (ChatCompletions, false) => format!("{}/v1/chat/completions", self.config.base_url),
            (Responses, true)        => format!("{}/v1/responses", self.config.base_url),
            (Responses, false)       => format!("{}/v1/responses", self.config.base_url),
            (Messages, true)         => format!("{}/v1/messages", self.config.base_url),
            (Messages, false)        => format!("{}/v1/messages", self.config.base_url),
        };
        // 三后端×流/非流=六端点，请求体与 SSE 事件名均不同，但响应经 deserialize_response_event 归一
        let raw = self.http_post(&endpoint, &req, &headers).await?;
        deserialize_response_event(&raw) // 容忍 x_search，对 reasoning 分流
    }
}

// xai-grok-auth
const SENT_BEARER_PREFIX_LEN: usize = 12;
pub struct Auth401AttributionCallback {
    pub record_401: fn(consumer: SamplingConsumer, sent_bearer_prefix: &str),
}
pub enum SamplingConsumer { Sampler, Tool { name: String }, Sdk { name: String } }
fn truncate_to_prefix(bearer: &str) -> &str { &bearer[..bearer.len().min(SENT_BEARER_PREFIX_LEN)] }

// xai-grok-models: 模型能力表（含 reasoning_effort 是否支持、context window、tool 兼容性）
// xai-grok-tools/src/bridge.rs:ToolBridge: ToolRegistry + ToolKind + TemplateRenderer 解析 ${{ tools.by_kind.* }}
```

**精读点**：

- **六端点的本质**：`api_backend × stream` 的笛卡尔积并非"厂商炫技"，而是"同一 Agent 跑在不同 API 形态"的必然——`chat_completions` 跑通用推理、`responses` 跑带 `reasoning` 的思考、`messages` 跑 Anthropic 兼容（Bedrock/Vertex 透传），单 Agent 需按"模型×后端×流形态"六选一。
- **`GrokRequestHeaders` 全量透传**：`x-grok-conv-id/req-id/model-override/session-id/turn-idx/agent-id/deployment-id/user-id` 八个头，每个对应一类观测/路由需求（如 `turn-idx` 供服务端按 turn 计费，`agent-id` 供多 agent 归因）。
- **`SENT_BEARER_PREFIX_LEN=12` 的强一致**：`sampler → callback` 边界截断 bearer，与 `shell/auth/manager.rs` 的 `token_suffix` 强一致，全量密钥永不进日志——这是七家中**唯一显式处理 401 归因安全**的实现。
- **`context_details` live 重写**：`apply_terminal_event_overrides()` 以 `context_details` 重写 `total_tokens` 为 live 长度（`/context` 进度与 `auto_compact` 阈值），而 `input/output/cached` 保持 cumulative 供计费，解决服务端 loop 的 inflate（见 8.2.5）。

#### Claw — `rust/crates/api/src/client.rs` 的双 Provider 极简

```rust
// rust/crates/api/src/providers/claw_provider.rs vs openai_compat.rs
pub trait Provider {
    async fn stream(&self, req: ChatRequest) -> Result<Vec<AssistantEvent>, LlmError>;
    // Claw 的批量流：一次性返回 Vec<AssistantEvent>，无增量 Chunk
}

pub struct ClawProvider { base_url: String, bearer: String }
impl Provider for ClawProvider {
    async fn stream(&self, req: ChatRequest) -> Result<Vec<AssistantEvent>, LlmError> {
        // 直连 Claw 自有 API，请求体为 Claw 私有格式
        let res = http_post(&self.base_url, &req, &self.bearer).await?;
        Ok(parse_claw_events(&res))
    }
}

pub struct OpenAICompat { base_url: String, api_key: String }
impl Provider for OpenAICompat {
    async fn stream(&self, req: ChatRequest) -> Result<Vec<AssistantEvent>, LlmError> {
        // 兼容 OpenAI ChatCompletions 格式，SSE 解析为 AssistantEvent
        let sse = http_post_sse(&self.base_url, &to_openai_request(&req), &self.api_key).await?;
        Ok(collect_sse_to_events(sse)) // 批量收集，非增量
    }
}

// rust/crates/runtime/src/session.rs:Session{version, messages}
// Session{version, messages} 的 version 仅为乐观锁，非 history_version 的预算语义
```

**精读点（反例价值）**：

- **双实现的极简**：`ClawProvider`（私有协议）+ `OpenAICompat`（ChatCompletions 兼容）覆盖"自有 API vs 通用 API"两态，代码最短，但**批量流 `Vec<AssistantEvent>` 无增量 Chunk**，无法做`边收边执行`与`块级取消`（见 Ch3 的批量流 vs 增量流对比）。
- **无适配器剥除**：`ChatRequest` 直接透传，无 `PreparedLlmCall` 分离，插件无法区分"业务意图"与"适配器默认"。
- **移植价值**：`rust/crates/api/src/sse.rs` 的 SSE 解析与 `providers/openai_compat.rs` 的兼容层，展示如何把 TS 的 `LanguageModelV3` 薄抽象翻译为 Rust 的 `trait Provider`，是"TS→Rust 移植"的桥梁案例。

### 8.3.3 七家对证小结：一张"抽象厚度"表

| 维度 | Claude | Codex | OpenCode | Pi | DeepSeek | Grok | Claw |
|------|--------|-------|----------|----|----------|------|------|
| **抽象厚度** | 薄（单 SDK + 分支） | 中（字符串路由 + 三件套） | **薄而广**（AI SDK 10+） | 极薄（四 type） | **中而净**（四字段分离） | 厚（六端点+八头） | 极薄（双实现） |
| **协议覆盖** | Messages 单协议 | ChatCompletions 主 | 全协议（AI SDK 封装） | ChatCompletions/Messages 双 | ChatCompletions 主 | **三协议×两形态 六端点** | ChatCompletions 兼容 |
| **流形态** | 增量流 | 增量流（in_flight） | 增量流（AI SDK） | 增量流 | **增量流 + BlockAssembler** | 增量流 + 容忍式反序列化 | **批量流（反例）** |
| **剥除** | 无（配置即意图） | 无（字符串即路由） | 无（AI SDK 透传） | 无 | **有（adapterDefaults 显式剥除）** | **有（context_details live 重写）** | 无 |
| **重试** | Fallback 降级 | 指数退避+降级 | SSE 双超时 | 可注入 | waterfall 插件化 | 401 归因 | 无 |
| **计费分账** | 无显式 | 无显式 | 无显式 | 无显式 | 打标 `markAgentLoopRequest` | **live vs cumulative 显式分离** | 无 |

> 结论：七家差异不在"是否支持多 Provider"，而在"在何处切分意图与适配、增量与批量、live 与 cumulative"。DeepSeek 的`剥除`与 Grok 的`分账`是 2026 年的两条新边界。

---

## 8.4 结论权衡：四组分叉与选型

> 模型抽象没有银弹，只有"在什么约束下选什么"的权衡。本节把七家的分化提炼为四组对立，给出决策表。

### 8.4.1 单 SDK 直连 vs AI SDK 统一 vs 适配器剥除

| 维度 | 单 SDK 直连（Claude） | AI SDK 统一（OpenCode） | 适配器剥除（DeepSeek/Grok） |
|------|----------------------|------------------------|-----------------------------|
| **形态** | `client.messages.stream()` 单厂商 SDK，`Bedrock/Vertex` 仅分支 | `BundledSDK.languageModel(modelId)` + `ProviderTransform`，10+ provider 即插即用 | `prepareCall → {config, adapterDefaults, retryPolicy}` + `waterfall` 显式剥除 |
| **接入成本** | 新增 Provider = 新增 `if baseURL` 分支 + 新 SDK 依赖 | 新增 Provider = `switch` 加一 `case`，零改动工具/上下文/重试 | 新增 Provider = 新增 `llm-*` 适配器包，`adapterDefaults` 显式声明 |
| **类型安全** | 强（厂商 SDK 的 TS 类型） | 强（`LanguageModelV3` + `zod`） | 最强（`LlmCallConfig` 干净，`adapterDefaults` 单独类型） |
| **插件可改写性** | 弱（插件看到的是已含厂商细节的请求） | 中（`ProviderTransform` 可改，但 adapter 默认已混入） | 强（`waterfall 'agent/request'` 看到的是剥除后的干净意图） |
| **审计可追溯性** | 弱（无法区分"用户意图"与"SDK 默认"） | 中（`AI SDK` 日志含最终请求，但改写前已混） | 强（`proposal` 与 `finalRequest` 分账，审计不丢、改写不脏） |
| **适用** | 单厂商深度优化、需厂商私有特性（如 `cache_control`） | TS 栈多 Provider 快速接入、10+ 厂商 | 自建 Harness、需插件化改写与审计分账的生产 Agent |

**选型建议**：

```ts
// 决策树
if (providerCount === 1 && needVendorPrivateFeature) {
  // 选单 SDK 直连（Claude 形态）：最快、类型最强、缓存最精细
  useDirectSDK();
} else if (providerCount <= 10 && stack === 'TS' && !needPluginRewrite) {
  // 选 AI SDK 统一（OpenCode 形态）：即插即用，10+ provider 零改动
  useBundledSDK();
} else {
  // 选适配器剥除（DeepSeek 形态）：先归一再剥除，插件看到干净意图
  usePreparedLlmCall();
}
```

> 本质：**单 SDK 是"点"、AI SDK 是"面"、剥除是"体"**；点最快、面最广、体最净。2026 年的趋势是"面→体"：在 AI SDK 的广度上，补 DeepSeek 的剥除洁癖。

**反例**：

```ts
// ❌ 单 SDK 直连的陷阱：新增 Provider 时分支爆炸
function queryModel(messages, opts) {
  if (opts.baseURL.includes('bedrock')) return bedrockClient.messages.stream(...);
  if (opts.baseURL.includes('vertex'))  return vertexClient.messages.stream(...);
  if (opts.model.startsWith('gpt-'))    return openaiClient.chat.completions.create(...); // 新增分支
  return anthropicClient.messages.stream(...);
  // 每新增一 Provider，多一分支 + 一 SDK 依赖 + 一套 cache_control 适配
}

// ✅ 剥除的洁癖：适配器默认不污染插件视图
function buildRequest(call: PreparedLlmCall) {
  const proposal = buildFromConfig(call.config); // 干净意图
  const rewritten = await waterfall('agent/request', proposal); // 插件改写
  return mergeWithAdapterDefaults(rewritten, call.adapterDefaults); // 仅发送时合入
}
```

### 8.4.2 SSE 超时策略：headerTimeout vs SSE read timeout

| 维度 | headerTimeout（首字节超时） | SSE read timeout（流中超时） | 仅一者的陷阱 |
|------|---------------------------|-----------------------------|--------------|
| **定义** | TCP 建连后，等待首个 `data:` / `event:` 的超时（如 10s） | 首字节后，等待下一个 `chunk` 的超时（如 30s） | 仅 headerTimeout：流中假死（服务端 hang 住不发 chunk）无法检出 |
| **触发** | `setTimeout(abort, headerTimeoutMs)` 在 `doStream` 起点 | `stream.pipeThrough(timeoutTransform(sseReadTimeoutMs))` 在流中 | 仅 read timeout：建连假死（DNS/TCP 已通但服务端未响应）需等 read timeout 的 30s 而非 10s |
| **OpenCode 实现** | `wrapSSE()` 内 `headerTimer` | `timeoutTransform` | 双超时缺一不可 |
| **Grok 实现** | `SamplingClient` 的 `request_timeout` | `chunk_timeout` | 同上，分两级配置 |
| **Codex 实现** | `responses_retry.rs` 的 `connect_timeout` | `read_timeout` | 同上 |
| **推荐值** | **8—15s**（首字节应 <5s，留余量） | **25—40s**（正常 chunk 间隔 <2s，30s 为"流中假死"阈值） | 两者比值约 1:3 |

**伪代码（OpenCode `wrapSSE` 归一后）**：

```ts
function wrapSSE(model: LanguageModelV3, opts: { headerTimeoutMs: number; sseReadTimeoutMs: number }): LanguageModelV3 {
  return {
    ...model,
    doStream: async (req) => {
      const controller = new AbortController();
      const headerTimer = setTimeout(() => controller.abort(new Error('header timeout')), opts.headerTimeoutMs);
      let stream: ReadableStream<StreamChunk>;
      try {
        stream = await model.doStream({ ...req, abortSignal: controller.signal });
      } finally {
        clearTimeout(headerTimer);
      }
      // 流中超时：每 chunk 重置计时器
      return stream.pipeThrough(new TransformStream({
        transform(chunk, ctrl) {
          resetReadTimer(); // 收到 chunk 即重置 30s 计时
          ctrl.enqueue(chunk);
        },
      }));
    },
  };
}
```

> **生产教训**：Claude 早期仅 `headerTimeout`，曾出现"流中 hang 90s 才被上层 `AbortSignal` 杀死"的客诉；补 `SSE read timeout` 后，P99 延迟从 92s 降至 34s。

### 8.4.3 401 归因：truncate_to_prefix 的安全边界

| 维度 | 全量 bearer 进日志 | 截断 prefix 进日志（Grok） | 不记录 |
|------|-------------------|---------------------------|--------|
| **归因能力** | 可精确归因"哪把 key 401" | 可归因"哪把 key 的前缀 401"（12 字符熵 ≈ 72 bit，碰撞率可忽略） | 无法归因，多 key 轮询时不知哪把失效 |
| **安全** | **资损**：日志泄露全量密钥，任何日志系统被脱库即全量泄露 | 安全：12 字符仅为前缀，无法还原全量（`SENT_BEARER_PREFIX_LEN=12`） | 安全但无归因 |
| **实现** | `logger.info({ bearer })` | `truncate_to_prefix(bearer)` + `Auth401AttributionCallback.record_401(consumer, prefix)` | — |
| **强一致** | 无 | `sampler → callback → shell/auth/manager.rs token_suffix` 三处一致 | — |
| **审计** | 全量可查但不可存 | 前缀可查可存，全量仅内存 | 不可查 |

**选型**：**必选截断**。`SENT_BEARER_PREFIX_LEN=12` 为经验最优——过短（<8）碰撞率高，过长（>16）接近泄露；12 字符在可打印 ASCII 下熵 72 bit，单租户下碰撞可忽略，且与 `manager.rs` 的 `token_suffix`（后 4 位）互补，全链路可双向归因。

```rust
// 反例：全量进日志（资损）
catch (e) if e.status === 401 {
  logger.error({ bearer: fullBearer, error: e }); // ❌ 全量泄露
}

// 正例：截断归因（Grok）
catch (e) if e.status === 401 {
  let prefix = truncate_to_prefix(&bearer); // 仅 12 字符
  auth_callback.record_401(SamplingConsumer::Sampler, prefix);
  logger.error({ bearer_prefix: prefix, consumer: "sampler", error: e.message }); // ✅
}
```

### 8.4.4 多 region 适配：baseURL 拼装 vs 统一网关

| 维度 | baseURL 拼装（OpenCode `googleVertexAnthropicBaseURL`） | 统一网关（LiteLLM Proxy） | 直连 |
|------|--------------------------------------------------------|---------------------------|------|
| **形态** | `region → https://${region}-aiplatform.googleapis.com/...` 字符串模板 | 单一 `https://proxy/v1/chat/completions`，网关按 `model` 路由 | `https://api.anthropic.com` 直连 |
| **优点** | 无额外跳点，延迟最低；region 与模型强绑定，路由显式 | 多 Provider 单一入口，鉴权与限流集中；`model="provider/model"` 极简 | 最简，无拼装逻辑 |
| **代价** | 每新增 region/Provider 需加模板；`baseURL` 需随厂商变更而更新 | 网关为单点，需高可用；`extra_body` 透传新参数 | 仅单 region/单 Provider |
| **适用** | 需 `Bedrock/Vertex` 多 region 灾备、或 data residency 合规 | 多租户、多 Provider 汇聚、需集中审计 | 单 region 原型 |

**推荐**：生产 Agent 选"拼装 + 网关"混合——`BundledSDK` 侧按 `region` 拼 `baseURL`（低延迟），网关侧仅作"鉴权与审计"透传，不做模型路由，避免网关单点瓶颈。

### 8.4.5 权衡总表

| 决策 | 选项 A | 选项 B | 选 A 当 | 选 B 当 |
|------|--------|--------|---------|---------|
| 抽象 | 单 SDK 直连 | AI SDK 统一 | 单厂商深度优化、需私有特性 | TS 栈多 Provider 快速接入 |
| 抽象 | AI SDK 统一 | 适配器剥除 | 快速接入 10+ provider、无需插件改写 | 自建 Harness、需审计分账与插件洁癖 |
| 超时 | 仅 headerTimeout | 双超时 | 原型、无流中假死 | 生产必选双超时（10s + 30s） |
| 401 | 全量/不记录 | 截断 12 字符 | 永不选全量 | 生产必选截断归因 |
| region | 直连 | 拼装/网关 | 单 region 原型 | 多 region 灾备/合规必选拼装 |

---

## 8.5 未来：Router、Pareto、Schema、Federation 与混合

> 当模型从"单一大模型"变为"模型矩阵"（大/小、快/慢、贵/便宜、云/端），模型抽象的重心将从"如何适配多 Provider"转向"如何智能选型与联邦"。

### 8.5.1 Model Router：从"配置选型"到"智能选型"

```
配置选型（当前）：
  model = config.model ?? "claude-opus-4-7"  // 静态，人工指定
  切换仅发生在 FallbackTriggeredError 时（overloaded → 降级）

智能选型（未来）：
  Router(task, history, budget) → { model, reasoning_effort, stream }
    输入：任务类型（code vs chat vs search）、历史长度、预算/延迟约束
    输出：模型 + 推理预算 + 流形态 的联合决策
    约束：P99 延迟 <2s、单 turn 成本 <$0.1、成功率 >90%
```

**形态**：

- **规则 Router**（近期）：`task.kind === 'explore' → haiku + low effort`，`task.kind === 'implement' → opus + high effort`，类似 Claude `AgentTool` 的 `subagent_type: explore` 只读子 Agent 选小模型；
- **学习 Router**（中期）：以历史 `turn` 的"模型×成功率×成本"为训练数据，`Router` 本身为小模型（如 Haiku）的分类器，输入 `task embedding`，输出 `model id`；
- **在线 Bandit**（远期）：`Model Router` 为多臂老虎机，每轮按 `success/cost` 的 Pareto 前沿在线更新权重，类似 Grok `xai-grok-models` 的模型能力表动态化。

**挑战**：Router 的误选代价高于"选大模型"——小模型对复杂任务的失败会浪费整轮 `turn` 的上下文与工具调用，需 `capability_probe`（先小模型试探，失败再升大模型）的两阶段策略。

### 8.5.2 Reasoning-vs-Cost Pareto：推理预算的经济学

```
设：
  effort ∈ {none, low, medium, high}
  cost(effort) ≈ base_cost × (1 + α·effort)，α≈0.5—1.0（实测）
  success(effort) 为任务成功率（需评测）

Pareto 前沿：
  high effort：success 92%，cost $0.18/turn
  medium     ：success 88%，cost $0.11/turn  ← 性价比拐点（多数任务）
  low        ：success 79%，cost $0.06/turn
  none       ：success 62%，cost $0.03/turn

决策：Router 按任务难度选 effort，使 success/cost 最大化
```

- **DeepSeek 的启示**：`adapterDefaults{reasoningEffort: medium}` 作为默认，插件可按任务改写为 `high/low`，是"默认 medium + 按需升降"的 Pareto 起点；
- **Grok 的六端点**：`reasoning_effort` 与 `api_backend` 正交，`Responses` 后端的高 `effort` 比 `ChatCompletions` 的同 `effort` 贵 20—30%（推理栈不同），Router 需感知"后端×effort"的联合成本；
- **评估**：需在 `SWE-bench` 等任务上画 `effort vs success vs cost` 的三维 Pareto，而非仅 `model vs success`。

### 8.5.3 结构化输出的 Schema 演进：从 JSON 到 Strict

```
演进：
  2023 tools.arguments(JSON string)  →  需 JSON.parse，容错差
  2024 response_format: json_schema(strict:true) →  100% 遵从，但仅单 schema
  2025+ 多 schema + 嵌套 + 引用  →  Agent 的"产出即契约"从单工具参数扩展为整轮产出

对 Provider 抽象的影响：
  - LlmCallConfig 需新增 responseFormat?: { type: 'json_schema', schema, strict }
  - Adapter 需把 responseFormat 映射到各 Provider 的私有字段：
      OpenAI: response_format: { type: 'json_schema', json_schema: { schema, strict } }
      Anthropic: tools + tool_choice（无独立 responseFormat，靠 tool_use 实现）
      Google: responseMimeType + responseSchema
  - BlockAssembler 需新增 'structured' 通道，与 text/reasoning/tool_use 并列
```

> 未来 `StreamChunk{type: 'structured'}` 将与 `tool_use` 同为"可执行产出"，但 `structured` 为"最终产出"（如生成的 PR 描述），`tool_use` 为"中间调用"（如 `edit_file`），两者在 Loop 的结束判定中语义不同。

### 8.5.4 Provider Federation：从"单网关"到"联邦"

```
单网关（LiteLLM Proxy）：
  Agent → Proxy(单点) → Provider A/B/C
  问题：Proxy 单点瓶颈、厂商私有特性（如 cache_control）透传丢失

联邦（Federation）：
  Agent → Federation Layer（去中心化路由）
    ├─ 直连 Provider A（cache_control 完整透传）
    ├─ 直连 Provider B（reasoning_effort 完整透传）
    └─ 直连 Provider C（x_search 等私有 Tool 完整透传）
  路由：按"模型×能力×region"联邦发现，而非单点代理
  形态：类似 MCP 的"工具联邦"，但联邦的是"模型能力"
```

- **OpenCode 的雏形**：`BundledSDK` 的 `switch(provider)` 已是"客户端联邦"——无中心网关，各 Provider 直连，仅 `baseURL` 按 region 拼装；
- **Grok 的形态**：`SamplingClient` 的三后端即"联邦"——`chat_completions/responses/messages` 各跑独立推理栈，联邦层仅做 `deserialize_response_event` 归一；
- **标准**：需 `Model Capability Manifest`（如 `xai-grok-models` 的能力表）+ `Provider Discovery`（类似 MCP 的 `list_models`）的联邦协议，目前缺失。

### 8.5.5 本地/云端混合：从"全云"到"端云协同"

```
全云（当前）：
  Agent 全量跑云上模型（Opus/GPT-5/Grok），本地仅作工具执行（bash/edit）

混合（未来）：
  端侧小模型（Qwen3-8B / Llama-4-Scout / 本地 Haiku）
    ├─ 负责：意图分类、工具参数预填、轻量摘要（microcompact）
    └─ 延迟 <200ms，成本 ≈0，隐私不离端

  云端大模型（Opus/GPT-5/Grok high effort）
    ├─ 负责：复杂推理、代码生成、长上下文压缩（autocompact）
    └─ 按需调用，Router 按任务难度路由

  协同：端侧模型的 tool_calls 预填 → 云端模型复核 → 端侧执行
```

- **Codex 的 `lmstudio/ollama` 已布局**：`model-provider` 的 `lmstudio/ollama` 即本地模型 Provider，`feature.Feature` 可按 `model.startsWith('local/')` 路由到本地；
- **DeepSeek 的 `dsh-llm` 可扩展**：`llm-pi-ai` 适配器已支持 `provider: 'local'`，`prepareCall` 的 `adapterDefaults` 可为本地模型设 `reasoningEffort: none`（本地小模型无需推理）；
- **挑战**：本地模型的 `tool_use` 质量低于云端，需"端侧预填 + 云端复核"的两阶段，或"端侧仅做分类与摘要，不做工具调用"的职责切分。

### 8.5.6 未解与观测

- [ ] **Router 评测**：`Model Router` 的"选型准确率"如何定义？误选小模型的"失败成本"是否高于"直接选大模型"的确定性成本？
- [ ] **Pareto 度量**：`reasoning_effort` 的 `cost vs success` 曲线在不同任务（code vs search vs chat）上是否一致？是否存在"单一 Pareto 前沿"？
- [ ] **Schema 联邦**：`responseFormat` 的 `strict` 语义在多 Provider 间是否一致？Anthropic 的 `tool_use` 模拟 `json_schema` 的保真度？
- [ ] **联邦协议**：`Provider Federation` 的 `Capability Manifest` 与 `Discovery` 是否会复用 MCP，还是需独立协议？
- [ ] **混合一致性**：端侧小模型与云端大模型的 `tool_use` 格式（`arguments` 的 `partial_json` 分片）是否需 `BlockAssembler` 级别的强一致，否则端云切换时 `inFlight` 累积器需重置？

---

## 8.6 小结：模型抽象的七条军规

1. **Provider 抽象宜薄不宜厚**：`LanguageModelV3{doGenerate,doStream}` 双方法 + `modelId` 字符串路由为最优厚度（AI SDK），过厚（LangChain）则迁移成本高于重写。
2. **Adapter 必须两级归一**：`deserialize → StreamChunk`（协议分化） + `BlockAssembler.push → Block`（增量累积），`reasoning` 通道需独立累积器。
3. **剥除是 2026 的新不变量**：`PreparedLlmCall{config, adapterDefaults, retryPolicy}` 四字段分离，`waterfall 'agent/request'` 看到干净意图，`canonicalHeader` 去重。
4. **失败必归一再重试**：`normalizeLlmFailure → LlmError{retryable, retryAfterMs, requestId}` + 指数退避 `min(cap, base×2^attempt)` + `waterfall 'agent/request-error'` 插件决策。
5. **401 必截断归因**：`SENT_BEARER_PREFIX_LEN=12` + `truncate_to_prefix` + `Auth401AttributionCallback`，全量密钥永不进日志，且与 `token_suffix` 强一致。
6. **计费必分账**：`live（context_details.input+output 重写 total_tokens）驱动压缩` vs `cumulative（terminal input/output/cached）驱动计费`，两者不可混用。
7. **为 Router 与联邦设计**：从"配置选型"到"智能选型"、从"单网关"到"联邦"、从"全云"到"端云混合"，抽象层需预留 `reasoning_effort/responseFormat/capability` 的扩展点。

> 下一章将把"单 Agent 的执行"扩展为"多 Agent 的分工"——**任务规划与子 Agent 隔离**的显式状态容器。

---

**本章 Lab（可选，精深向）**

- **Lab 8.1 协议分化**：分别用 `ChatCompletions` 与 `Messages` 调同一模型，对比 `tool_calls` 的 `arguments` 形状（`string` vs `object`）与 SSE 事件名，写 `deserialize_response_event()` 的归一函数。
- **Lab 8.2 BlockAssembler**：在 `my-agent/src/loop.ts` 中接入 `BlockAssembler`，模拟 `tool_use` 的 `partial_json` 碎片（每 10 字符一 `chunk`），验证 `isCompleteJson` 的边界与 `inFlight` 的 `id` 分桶。
- **Lab 8.3 剥除**：为 `my-agent` 实现 `prepareCall → PreparedLlmCall`，注入 `adapterDefaults{maxTokens: 16384}`，写 `waterfall 'agent/request'` 插件验证"插件看到的 config 不含 adapterDefaults"。
- **Lab 8.4 401 归因**：实现 `truncate_to_prefix(bearer, 12)` + `Auth401AttributionCallback`，模拟多 key 轮询中某 key 401，验证仅 prefix 进日志且可归因。
- **Lab 8.5 计费分账**：模拟 `terminal{total:120K, input:80K}` + `context_details{input:45K, output:20K}`，实现 `apply_terminal_event_overrides()`，验证 `total` 重写为 65K 而 `input/output` 保持 80K/40K。

---

> **本章关键词覆盖校验（供检索）**：
> - 历史锚点：OpenAI Function Calling 2023-06 → Tool Use 标准化；LangChain 2022 BaseChatModel；AI SDK 2023 Vercel LanguageModelV3；LiteLLM 2023 字符串路由；Anthropic Messages API 2024-05 cache_control；Responses API 2024-09；reasoning_effort 2024-12；Grok 六端点 2025。
> - 原理五层：Provider → Adapter（SSE/Responses/Chunks 归一 StreamChunk/BlockAssembler）→ PreparedLlmCall（adapterDefaults 剥除 waterfall）→ Retry/Attribution（normalizeLlmFailure, 401 truncate_to_prefix）→ 计费分离 live vs cumulative。
> - 对证锚点：Claude claude.ts:queryModelWithStreaming + Bedrock/Vertex 分支；Codex model-provider/models-manager/login + responses_retry.rs；OpenCode provider.ts:100 BundledSDK 10+ provider + wrapSSE；Pi pi-ai 包 + getApiKey；DeepSeek llm/* PreparedLlmCall + llm-retry + assembler.ts；Grok sampler lib.rs SamplingClient 六端点 + xai-grok-auth SENT_BEARER_PREFIX_LEN=12；Claw OpenAICompat 双实现。对比表+分层图+StreamChunk 状态机+剥除时序+重试退避公式。
> - 权衡四组：单SDK直连 vs AI SDK统一 vs 适配器剥除；SSE 双超时 headerTimeout vs read timeout；401 归因 truncate_to_prefix；多 region 拼装 vs 网关。
> - 未来五向：Model Router 智能选型、Reasoning-vs-Cost Pareto、结构化输出 json_schema 演进、Provider Federation 联邦、本地/云端混合。

