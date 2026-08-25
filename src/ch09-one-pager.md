# 第13章 一页纸速查

> 全书压缩成一张纸 + 5 分钟陈述框架 + 高频追问表。需要快速回顾时只看本章；平时当书签用。

## 13.1 一页纸（可直接打印）

```
Agent Infra 一页纸（八家源码对照版，2026-08）

【定位】Agent Infra = LLM 之上的操作系统：Prompt+Loop+Tools+Context+Session+Model 六件套
【历史】ReAct(2022)→Reflexion/Voyager(2023)→SWE-agent/CodeAct(2024)；Toolformer→FC(2023-06)→MCP(2024-11)；
        MemGPT(2023)→A-MEM(2025 NeurIPS 写入时代理)→FadeMem(2026 衰减)；
        CAMEL/MetaGPT/AutoGen(2023)→LangGraph(2024)→多Agent实证清算(2024-25)

【Loop 三层】turn loop → sampling retry loop → stream consume loop
  形态谱系：while(Claude/Pi) vs FSM(DeepSeek Phase{idle|maintenance|running}) vs Actor(Grok ChatStateActor)
            vs 库形态计数器(Qwen-Agent MAX_LLM_CALL_PER_RUN=20)
  打断语义：Inbox.splice(next-turn|next-step) 最精确；steer 回调最简

【Tools 四分水岭】同源(spec+handle 焊死防 schema 漂移) / 可见性分级(ToolExposure Direct→Hidden)
  权限横切(deny>ask>allow, 只在编排器判一次) / 沙箱(bwrap<gVisor<worktree 文件隔离)
  并行：默认串行；isConcurrencySafe 才并行；preflight 永远串行

【Context 四层防线】估算(chars/4; Qwen-Agent 用真 tiktoken 是例外)→预算(window-buffer 或 85%)
  压缩(snip粗删→micro细删→collapse折叠→摘要; 顺序不可换)→缓存(cache_control 断点稳定:
  工具排序/localeCompare/contentHash; 实验关前缀=98% miss)

【Session 三底线】append 唯一写路径 + turn/start 边界不丢(预写Claude/版本Codex/偏移Grok)
  启动自愈(repair_dangling_tool_calls)。库形态(Qwen-Agent/Pi core)可留白给宿主——分层选择非缺陷

【Model 三阶段】单SDK直连→AI SDK 统一(10+ provider)→适配器剥除(adapterDefaults 剥离+
  context_details 重写 total 为 live)。live 驱动压缩、cumulative 驱动计费，永不分混

【安全四象限】副作用大→沙箱+审批；输入可疑(web)→只读也危险！注入=数据变指令(arXiv:2302.12173)
  失败先归一再处置(Network retry-exp / RateLimit retry-after / PTL withhold / 401 截断12字符)
  密钥 SENT_BEARER_PREFIX_LEN=12 全链路脱敏

【多 Agent 两原则】规划是显式状态容器(plan 落盘为文件, 可 diff 可回滚)
  子 Agent 是隔离执行单元(worktree/Actor/Cordis Scope)；禁嵌套 teammate 防递归风暴
  分界条件：并行搜集/弱耦合→O-W 提速约90%但 token ~15×(Anthropic 2025-06)；
            强耦合编辑/动作不可逆→单线程共享上下文(Cognition 同月檄文)

【评测两层】结果指标(SWE-bench pass@k)定门槛 + 过程指标(trace 步骤分析/PRM)定位瓶颈
```

## 13.2 八家一句话（被问"你研究过哪些"时用）

| 家 | 关键词 |
|----|--------|
| Claude Code | 四层压缩防线、cache 断点稳定、权限横切面——产品级细节之王 |
| Codex | Turn/Step 二分、每步重建 ToolRouter、OTel 原生——系统化之王 |
| Grok Build | Actor 无锁、启动自愈、密钥前缀 12 字符——可靠性之王 |
| DeepSeek | Cordis waterfall 插件拦截、Inbox next-turn/next-step——扩展性之王 |
| OpenCode | Effect+Drizzle、fork idMap 重映射——现代 TS 栈范本 |
| Pi | 200 行 runLoop、transformContext 投影——教学级起点 |
| Qwen-Agent | Memory=RAG Agent、fncall_prompts 文本协议 FC、六件缺三件的库形态——对照组 |
| Claw | parity_audit 移植方法论——反面教材兼翻译桥梁 |
| Hermes | ContextEngine 可插拔 + 技能自生成学习闭环 + 7 终端后端——自进化路线代表 |

## 13.3 五分钟陈述框架（总→分→证→选）

**① 总**："Agent Infra 是 LLM 之上的操作系统，我精读了九家实现——五家产品级 Harness（Claude/Codex/Grok/DeepSeek/OpenCode）、两家教学与框架形态（Pi/Qwen-Agent）、一家移植对照（Claw）。剥开都是六件套：Prompt+Loop+Tools+Context+Session+Model，每件都有清晰的论文源头到工程纵深的演化线。"

**② 分**："分水岭在四处。Loop 上 while 易读但打断难，生产选 FSM 或 Actor；Tools 上可见性分级比数量重要，权限必须横切；Context 上 chars/4 估算是共识（Qwen-Agent 用真 tiktoken 是唯一例外）、压缩必分层；Session 上可重放优于可恢复，turn/start 边界必须有锚点。"

**③ 证**："三个印象最深的细节：Codex 每 StepContext 重建 ToolRouter 杜绝悬垂工具调用；Grok 启动时 repair_dangling_tool_calls 修复带毒历史；DeepSeek Inbox 把打断分为 next-turn 与 next-step 两级并加 wakeRequested 闩锁。"

**④ 选**："选型上教学从 Pi/Qwen-Agent 入手（两种语言两种形态），生产组合 Codex 的上下文二分 + DeepSeek 的 Inbox + Grok 的自愈与脱敏。TS 栈直接复用 OpenCode；需要快速做 RAG 型助手时 Qwen-Agent 的 Memory-as-Agent 组合最快。"

## 13.4 高频追问 × 30 秒答案

| 追问 | 答案要点 | 锚点 |
|------|---------|------|
| 为什么不用 tiktoken？ | chars/4 零依赖够预算控制（阈值留 buffer）；Qwen-Agent 反例证明大厂也分两派 | `claude-code-haha/src/utils/tokens.ts` vs `Qwen-Agent/qwen_agent/utils/tokenization_qwen.py` |
| 缓存命中率怎么保？ | 工具 localeCompare 排序 + prompt 冻结 + contentHash 替代随机 UUID；关前缀缓存实测 98% miss | `claude-code-haha/src/services/api/claude.ts:606` |
| 工具何时能并行？ | isReadOnly && isConcurrencySafe 才并行，preflight 仍串行；Pi 要求 terminate 全员置位 | `claude-code-haha/src/Tool.ts:362` |
| resume 怎么保证可信？ | 先写 user 再调模型 + 边界锚点（预写/version/offset）+ 启动自愈 | `QueryEngine.ts:451` / `history.rs:93` / Grok journal |
| 多 Agent 何时上？ | 分界条件：≤10 步单 Agent；并行搜集→Orchestrator-Worker（Anthropic 实测提速约90%、token ~15×）；强耦合编辑单线程；多角色→Swarm 但必须 worktree + 禁嵌套 | `AgentTool/builtInAgents.ts` / Ch9 §9.1.2 |
| 提示注入怎么防？ | 承认概率问题：权限按调用链评估、结果截断溯源、审批分级记忆、最坏后果≤单次授权边界 | Ch11 威胁模型四象限 |
| 怎么评测你的 Agent？ | 结果（SWE-bench 式判分进 CI）+ 过程（trace 步骤分析）双层；LLM-as-Judge 控三类偏置 | `codex-rs/e2e/benchmark` |

## 13.5 便携卡片

```
┌────────────────────────────────────────────────────────┐
│ Loop:    三层嵌套；while/FSM/Actor/计数器四形态          │
│ Tools:   同源+可见性+横切权限+沙箱；只读也要过闸         │
│ Context: chars/4→window-buffer→四层压缩→投影→缓存断点    │
│ Session: append-only+边界锚点+启动自愈+live/cumulative   │
│ Model:   单SDK→AI SDK→适配器剥除；401 截 12 字符         │
│ 安全:    注入是概率问题；deny 必回填；ask 分级记忆        │
│ Multi:   plan=文件；子Agent=隔离单元；禁嵌套             │
│ 评测:    结果定门槛+过程找瓶颈，进 CI                     │
└────────────────────────────────────────────────────────┘
```
