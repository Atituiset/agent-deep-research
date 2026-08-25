# 第10章 可观测性与评测

> 没有度量就没有工程。本章回答三个问题：(1) Agent 该记什么——trace 的最小完备集；(2) 怎么归因——live/cumulative 与成本分账；(3) 怎么评好坏——从 SWE-bench 到 process reward 的评测脉络。

## 本章图谱

```
论文/标准 lineage          工程对证                    结论
──────────────            ──────────                 ──────────
OpenTelemetry 2019  ──►   tengu_*/codex-otel    ──►  trace 最小集 =
Distributed Tracing       EventV2Bridge              turn/request/span 三层
2010 Google Dapper        UsageLedger                live≠cumulative
SWE-bench 2023      ──►   benchmark/e2e 目录     ──►  结果指标 ≠ 过程质量
Tau-bench 2024                                       过程奖励是方向
WebArena 2023                                        自建 eval 优先
LLM-as-Judge 2023
Process Reward 2024
```

## 10.1 历史脉络与论文 lineage

### 10.1.1 可观测性：从 Dapper 到 Agent Trace

Agent trace 不是新发明——它把分布式系统二十年的追踪实践平移到了"一次 turn 跨 N 次模型调用与工具执行"的新场景上。读懂这段历史，才能明白为什么各家字段设计殊途同归。

```
2010   Google Dapper 论文（Sigelman et al.）
         └── 分布式追踪三原语：Span / TraceId / Annotation
              │  "一次请求跨 N 个服务" ≈ "一个 turn 跨 M 次工具调用"
2012/2017  Zipkin(Twitter) / Jaeger(Uber) 开源实现
         └── 追踪从 Google 内部技术变为行业标配
2019   OpenTelemetry 合并 OpenTracing + OpenCensus
         └── 统一 SDK 标准：trace/metric/log 三信号
              │  Codex 直接采用 → codex-otel
2022   ChatGPT 上线，Agent 会话可观测需求萌芽
2023   LangSmith/Langfuse/W&B Weave 相继发布
         └── LLM observability 成为独立品类：记录 prompt/response/token/tool
```

**Dapper 解决了什么问题？** 2010 年的 Google 搜索一次请求要穿过几十个服务，出问题时工程师只能靠日志时间戳人肉拼凑因果。Dapper 的方案优雅到可以用三句话说完：①把每次工作单元抽象为 **Span**（带起止时间的树节点），一次请求的所有 Span 构成一棵以 **TraceId** 为根的调用树；②TraceId 与父子关系通过 RPC 框架**自动注入透传**——业务代码零侵入；③用**采样**控制开销（按概率只记录千分之一），使全链路追踪在性能上几乎免费。这三招对 Agent 一一对应：Span ≈ 一次模型调用或工具执行；TraceId ≈ SessionID 贯穿整个会话；采样思想则变成"turn 级全记、工具级按需记"（Claude `tengu_*` 全事件 vs Pi 内存事件流的粒度差异）。Dapper 论文里最值得记住的判断是：**可观测性必须是基础设施的义务而非应用的选修课**——这正是本章 10.4 "trace 先于功能"铁律的思想源头。

**OpenTelemetry 为什么能统一江湖？** 此前 OpenTracing（API 标准）与 OpenCensus（Google 的 SDK）分裂生态，用户被迫二选一。2019 年 CNCF 把两者合并为 OTel：一套 API + SDK + **语义约定**（如 `http.method` 这类标准属性名），trace/metric/log 三种信号共享一个资源标识。它的关键承诺是 vendor-neutral：埋点一次，Jaeger/Grafana/Datadog 任接。九家中 Codex 是唯一原生 OTel 的（`codex-otel`），其余家自建事件总线（`tengu_*`、`EventV2Bridge`、Cordis telemetry）但字段设计殊途同归——因为它们回答的是同一组问题：这次调用谁发起、花了多少 token、哪个环节最慢。OTel 社区正在制定的 GenAI 语义约定（`gen_ai.*` attributes）一旦成熟，Agent trace 将像 HTTP span 一样跨厂商互通（见 10.5 未来方向）。

### 10.1.2 评测：从静态基准到过程评测

评测这条线的内在张力只有一个：**你到底想测"结果对不对"，还是"过程合不合理"？** 七年间所有基准的分化都是对这个问题的不同站位：

| 时间 | 基准/论文 | 核心贡献 | 局限 |
|------|----------|---------|------|
| 2023-03 | **SWE-bench**（Jimenez et al., arXiv:2310.06770） | 真实 GitHub issue 修复 + 测试通过判分 | 只看最终 patch，不看过程 |
| 2023-07 | **AgentBench**（Liu et al., arXiv:2308.03688） | 8 类环境统一评测 Agent 能力 | 环境真实性有限 |
| 2023-08 | **WebArena**（Zhou et al., arXiv:2307.13854） | 自托管真实网站的长 horizon 任务 | 部署重 |
| 2023-10 | **LLM-as-Judge**（MT-Bench, Zheng et al., arXiv:2306.05685） | 用强模型给开放输出打分 | judge 偏置（位置/长度/自偏好） |
| 2024-05 | **Tau-bench**（Yao et al., arXiv:2406.12045） | 用户模拟+工具+策略符合度的双重评测 | 领域窄（航空/零售） |
| 2024-08 | **SWE-bench Verified**（OpenAI） | 人工过滤坏样本，可信度大增 | 规模缩小 |
| 2023→ | **Process Reward Models**（PRM800K 2023-05；Math-Shepherd arXiv:2312.08935 等） | 给推理步骤逐步打分而非只看结果 | 需要步骤级标注 |

几篇关键工作的血肉：

- **SWE-bench：让"会修 bug"第一次可判分**。Princeton 团队从 12 个真实 Python 开源仓库抓取 2,294 个 issue-PR 对，每个实例附带该 PR 触及的测试：修复后 F2P（fail-to-pass）测试必须由红变绿、P2P（pass-to-pass）测试不能由绿变红——判分完全客观，无需人工。这个设计让 SWE-bench 成为 Agent 军备竞赛的标准考场，但也埋下两个著名缺陷：测试可能被"绕过"（直接改测试文件也算过）、issue 描述常缺失关键上下文（人类开发者也要靠仓库考古补齐）。2024-08 OpenAI 发布 **Verified** 子集：请人类承包商逐条验证 500 个可干净评测的样本，坏样本剔除后榜单排名发生明显洗牌——**基准本身也是需要审计的 artifact**。
- **WebArena：环境即考卷**。此前 Web 评测多用录制的静态页面快照，Agent 只要做"看起来对的事"。WebArena 反其道：自托管四个真实网站的开源克隆（论坛、购物、GitLab、地图），812 个长 horizon 任务以**后置条件**判分（数据库里真的多了那张订单吗）而非截图对比。代价是部署重（一套 Docker Compose），收益是不可作弊——状态改变骗不了数据库。
- **Tau-bench：给"服务型 Agent"加上策略与用户两面镜子**。ReAct 作者团队的后续工作，瞄准客服类场景的双难：既要完成任务（工具调对了），又不能违反公司政策（退款额度、身份核验）。做法是让 LLM 扮演**有隐藏需求的用户模拟器**与 Agent 多轮博弈，同时用规则引擎核对每步是否符合领域 policy；指标采用 pass^k——k 次独立运行**全部**通过才算过，暴露"平均分掩盖的不稳定性"。航空/零售两域的实测显示最强模型的 pass^1 也不到七成——服务型 Agent 离生产还差几个数量级。
- **LLM-as-Judge / MT-Bench：没有标准答案时怎么打分**。Zheng et al. 用 GPT-4 当裁判给两个模型的开放回答打分，与人类偏好一致率超八成——于是开放式任务终于有了可扩展的评分器。但他们同时系统性地记录了裁判的三类偏置：**位置偏置**（先出现的答案占优）、**长度偏置**（更长的答案得分更高）、**自偏好**（GPT-4 裁判偏爱 GPT-4 的文风）。工程对策由此定型：交换答案顺序取平均、按长度归一、judge 与 candidate 异源。这套控制变量法至今仍是所有用 judge 的 eval 的标配。
- **Process Reward Models：把分数拆到每一步**。结果奖励（ORM）只知道"最终错了"，不知道错在哪步。OpenAI 的 *Let's Verify Step by Step*（Lightman et al., 2023）用人工标注 800K 步级正确性标签（PRM800K）证明：过程监督训练出的 PRM 在数学上显著优于结果监督，且能抑制"碰巧答对的错误推理"。Math-Shepherd（2023-12）随后解决了标注贵的问题：**用 MC rollout 自动生成步级标签**——从某一步出发随机续写 N 次，最终答对率高则该步大概率正确。PRM 对 Agent 工程的意义在 Ch10.5 展开：当每步都有分数，"在线回滚劣质动作"的自愈闭环才有了信号源。

> 脉络总结：评测正从"结果对不对"（pass@k）走向"过程合不合理"（每步工具选择是否必要、token 是否浪费、是否走捷径）。这与 trace 记录的粒度直接耦合——**没有过程数据，过程评测无从谈起**；反过来说，PRM 在线化的前提是把 trace 记到步级。

## 10.2 原理深潜：Trace 最小完备集与用量归一

### 10.2.1 Trace 的三层模型

```
Session Trace（审计级）
 └── Turn Record（决策级）        ← 每次 run() 一条
      ├── request 快照: model / system_prompt hash / tools hash / context_tokens
      ├── response: text 摘要 / stop_reason / usage{input,output,cache_read,cache_creation}
      ├── Tool Spans（执行级）    ← 每次工具调用一条
      │     ├── name / args hash(全量 args 入敏感日志有风险) / duration_ms
      │     └── result_size / truncated? / error? / approval?(allow|deny|ask)
      └── children?: 子 Agent Turn Records（递归）
```

最小完备集 = 上面加粗字段。缺一项的典型事故：

- 缺 `tools hash`：无法解释"为何这轮 cache 全 miss"（工具清单变了 → 前缀断点失效，见 Ch5.6）；
- 缺 `stop_reason`：无法区分"模型认为完成"与 `max_tokens` 截断，重试策略失据；
- 缺子 Agent 归因（parentSessionId）：多 Agent 场景下成本无法分摊到具体子任务。

### 10.2.2 用量归一：live vs cumulative（承接 7.2.5）

```rust
// Grok xai-grok-sampler/src/lib.rs apply_terminal_event_overrides() 思想
fn normalize_usage(raw: Usage, context_details: ContextDetails) -> NormalizedUsage {
    NormalizedUsage {
        total_live: context_details.input + context_details.output, // 重写！驱动压缩阈值
        input_cumulative: raw.input,      // 保持累计，驱动计费
        output_cumulative: raw.output,
        cached: raw.cached,
    }
}
```

为什么必须分离：服务端 loop 工具（web_search 等）会让 API 返回的 `total_tokens` 包含搜索内部消耗，若直接用它做 `should_auto_compact(total, window)` 判断，会在上下文远未满时误触发压缩。

### 10.2.3 成本分账公式

```
TurnCost = cached_in × p_cache_read
         + cache_write × p_cache_write
         + uncached_in × p_input
         + out × p_output
         + Σ tool_costs(外部 API 计费)
SessionCost = Σ TurnCost + Σ ChildSessionCost(parent 归因)
```

Claude 的 `tengu_*` 事件把 `cache_creation/cache_read/input/output` 四项分开上报，正是为了让上式可算。只记单一 `total_tokens` 的实现，在引入 caching 后账单永远对不上。

## 10.3 对证分解：九家源码对证

### 10.3.1 总览对比表

| 家 | Trace 载体 | 记录粒度 | 评测设施 | 特色 |
|----|-----------|---------|---------|------|
| Claude | `tengu_auto_compact_succeeded/tengu_compact_ptl_retry/tengu_prompt_cache_break` + headlessProfilerCheckpoint | hop 级：assistantText/toolCalls/tokenUsage/compactionEvent | fixtures/ + tests/ 目录 | cache 断裂检测哈希 system+tools |
| Codex | `codex-otel`（原生 OpenTelemetry） | turn/request 级 span | codex-rs/e2e/benchmark + book 全套内部文档 | 八家中唯一 OTel 标准 |
| Grok | `UsageLedger`(prompt_usage/session_usage 分账) + harness_trace_buffer → harness_trace_turns | turn 级 + 子 Agent 发现(turn_{N}) | SOURCE_REV/ 第三方审查痕迹 | live/cumulative 强制分账 |
| DeepSeek | session-stats/session-telemetry/session-title 包 | waterfall 事件级(agent/pre-step 等) | BENCHMARK.md + vitest 双配置 | telemetry 即插件(Cordis) |
| OpenCode | `EventV2Bridge` + BackgroundJob | PartUpdated/PartDelta 流式粒度 | 无公开 bench，靠 STATS.md 运营数据 | UI 实时渲染即消费方 |
| Pi | AgentEvent{agent_start…agent_end} EventStream | turn/message 级 | docs/book 全书 + pi-test 脚本 | 事件流可直接被测试断言 |
| Claw | TranscriptStore entries | entry 级 | parity_audit.py 对齐上游 | 以"上游行为对齐"为评测 |
| Qwen-Agent | log.py logger + parallel_executor 计时 | 函数级 print/logging | benchmark/ 目录(官方评测脚本) | 最朴素：logger.warning 即 trace |

### 10.3.2 Qwen-Agent 对照：库形态的最小可观测

`qwen_agent/log.py` 只是一行 `logger = logging.getLogger(...)` 封装；工具失败时 `_call_tool`（`agent.py:196-203`）拼一段含 traceback 的 error_message 作为字符串返回给模型。对比之下：

- **优点**：零依赖、零侵入，宿主应用用自己的 logging/APM 体系接住；
- **缺点**：无结构化字段（token 数要自己从响应里抠）、无 parent 归因、无成本分账；
- **启示**：可观测性是产品责任而非库责任的又一例证（同 Session，见 7.3.2）。若要在 Qwen-Agent 上建 eval，得先包一层 `BaseChatModel.chat()` 拦截器补齐 usage 记录。

### 10.3.3 Claude 的 promptCacheBreakDetection：为性能而生的观测

`promptCacheBreakDetection.ts` 对 system+tools 做哈希比对，一旦检测到前缀变化立即上报 `tengu_prompt_cache_break`。这是把"观测"用在优化闭环上的范例：**不是等用户抱怨贵了才查，而是每次断裂都有事件可查**。

### 10.3.4 评测对证：各家如何验证自己没退化

- Codex：`codex-rs/e2e/benchmark/` 保证长链路不回归 + Bazel 单仓统一构建（30+ crate）；
- Claude：fixtures/ 固化输入输出快照，tests/ 单测覆盖 compact 边界；
- Qwen-Agent：benchmark/ 目录提供官方跑分入口（对接内部模型），tests/ 为 pytest 单测；
- Claw：最特殊——以 `parity_audit.py` 把"与 claude-code-haha 行为一致"作为评测目标，这是移植项目的正确姿势。

> 共性结论：**评测=回归测试（防退化）+ 基准跑分（对外可比）两层**，缺一层都会在迭代中盲飞。

## 10.4 结论权衡

### 10.4.1 自建事件 vs OTel 标准

| 维度 | 自建(tengu/EventV2) | OTel(codex-otel) |
|------|--------------------|------------------|
| 接入成本 | 低，随代码演进自由改字段 | 中，需遵循语义约定 |
| 生态复用 | 弱（自家后端） | 强（Jaeger/Grafana/Datadog 直连） |
| 演进风险 | 字段漂移无人管 | 标准约束倒逼稳定性 |
| 建议 | 单机 CLI 产品起步期 | 多服务/云端/企业部署期 |

### 10.4.2 结果评测 vs 过程评测

```
只有结果(pass/fail)：能排名，不能改进 —— 失败案例里 80% 是过程问题
                          （选错文件、重复读、压缩时机不当）
只有过程(步骤分)：可指导改进，但易被 hack（刷步骤数）
生产配方：结果指标定门槛 + 过程指标定位瓶颈
         （SWE-bench 判分 + trace 步骤分析）
```

LLM-as-Judge 用于开放任务时必须控制三类偏置（位置/长度/自偏好）：交换顺序取平均、长度归一化、judge 与 candidate 异源。

### 10.4.3 三条铁律

1. **trace 先于功能**：新特性（compaction/subagent/hosted tools）上线当天就要有自己的事件名，否则出事无据可查（Claude 每个 compact 变体都有独立 tengu 事件是范本）；
2. **钱和上下文分两本账**：live 驱动行为、cumulative 驱动计费，任何混用迟早出事故；
3. **评测进 CI**：基准跑分不进 CI 就只是发布会素材（Codex e2e/benchmark 进 Bazel 构建是范本）。

## 10.5 未来方向

1. **OTel GenAI 语义约定成熟**：gen_ai.* attribute 标准化后，Agent trace 将像 HTTP span 一样跨厂商互通，Codex 的先行优势会变成行业默认。
2. **过程奖励驱动运行时**：PRM 不止用于离线评测——在线给每个工具调用实时打分，低于阈值的动作自动回滚重试（与 Ch11 自愈层合流）。
3. **成本感知调度**：UsageLedger 反馈给 Model Router（Ch8 未来方向），简单子任务自动降级到便宜模型，预算成为一等调度约束。
4. **评测环境标准化**：WebArena/Tau-bench 的"自托管环境"思路与 MCP 结合——eval harness 本身就是一个 MCP server，任何 Agent 可插拔参评。
5. **Qwen-Agent 类库的可观测插件化**：宿主注入 tracer 即获得全套结构化 trace，可能成为框架库的事实接口（类似 Python logging 的 handler 模式）。

## Lab 10：给最小 Agent 补上 Trace + 成本分账（约 100 行 TS）

**目标**：在 Lab 7 的 SessionStore 之上，实现三层 trace 与 live/cumulative 分离。

```ts
// lab/trace.ts 骨架
interface ToolSpan { name; argHash; ms; resultSize; err?; approval? }
interface TurnRecord {
  req: { model; sysHash; toolsHash; ctxTokens };
  res: { stopReason; usage: { in; out; cacheRead; cacheWrite } };
  spans: ToolSpan[]; child?: string /* childSessionId */;
}
class Ledger {
  live = 0; cumulativeIn = 0; cumulativeOut = 0;
  onUsage(u, contextDetails?) { /* live=contextDetails??in+out; cumulative 累加 */ }
  shouldCompact(window, buffer) { return this.live > window - buffer; }  // 只用 live!
}
function cost(t: TurnRecord, price): number { /* 按 10.2.3 公式 */ }
```

**验收**：
- [ ] 模拟一次带 web_search 虚高的 usage（total 含搜索消耗），`shouldCompact` 判断用的是修正后的 live；
- [ ] 两个子 Agent 的成本能通过 parent 归因汇总到根会话；
- [ ] 改变 toolsHash 后能触发 "cache_break" 告警事件。

**常见坑**：① argHash 对大对象直接 JSON.stringify（应先规范化键序）；② 忘记把子 Agent usage 递归上卷；③ price 表硬编码单模型（应按 model 键控）。

## 小结与思考题

- [ ] 能列出 trace 最小完备集并说出缺每项的事故模式
- [ ] 能推导 TurnCost 公式并解释 cache 四项拆分的必要性
- [ ] 能对比 SWE-bench（结果）与 PRM（过程）两条评测路线的适用场景
- [ ] 能解释为什么 Qwen-Agent 的 logger 方案在库形态下是合理的

**思考题**：
1. 若让你为八家的 trace 字段做一张超集 schema，哪些字段必有争议？怎么调和？
2. 过程奖励模型在线化后，"刷过程分"的新型 hack 会长什么样？
3. 你的 Agent 每月成本突增 40%，按本章的 trace 设计给出你的排查顺序。

---
