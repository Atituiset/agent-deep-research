# C 层（内容深化）设计文档 —— 另立项执行

> 本轮改造已完成 A（一致性清扫）+ B（结构层对齐）。本文档是 C 层的执行设计，
> 三件事都需要回源码仓补调研，不属于纯文档工程，因此单独立项。
> 触发方式：对 agent 说"执行 C-LAYER-PLAN 的第 N 项"。

## C1：Qwen-Agent / Hermes 进入对证层（最高优先）

**问题**：全书自称九家，但 Qwen-Agent 在 ch03/04/05/08 的对证表中缺席、Hermes 在
ch04/06/07/08/09/10 中缺席。本轮已在所有缺席表格下加了注记（注明缺谁、何处有专章），
但注记只是止血，补齐才是治愈。

**做法**（每章一条流水线）：
1. 回到本地源码仓：`~/Projects/Qwen-Agent` 与 Hermes 仓（见 appendix-research-log 的仓库清单）
2. 按该章对证表的既有列维度，为两家各跑一遍"读码 → 提炼 → 锚点（file:line）"
3. 表格补行 + 正文补 1-2 段精读（对齐既有行的颗粒度）
4. 删除对应注记；appendix-sources.md 补锚点注册
5. 章节顺序：ch04（Tools，Qwen 的 fncall 文本协议是全书唯一对照组，价值最高）→
   ch08（多 Agent，Hermes async_delegation）→ ch03（Loop）→ ch05（Context）→ 其余

**验收**：对证表行数 = 9；全书 grep 对证表注记"本表实列/未含"归零；附录 B 锚点两家各 ≥10 条。

## C2：配套 my-agent Lab 骨架仓

**问题**：Ch12 的 Lab 地图引用的 `my-agent/` 骨架仓不存在，Lab 无法开箱即跑——
这是与李书"实验即正文、全部可跑"差距的物理载体。

**做法**：
1. 新建 `my-agent/` 子目录（或独立仓 my-agent-lab，本书 git submodule/subtree 引入）
2. 以 Pi 的 200 行 runLoop 为起点（Ch3 Lab 3 已有骨架），每个 Lab 一个分支或目录：
   `lab03-loop/`（基础 while 循环）→ `lab04-tool-router/`（schema 校验）→
   `lab05-context/`（transformContext + compaction 触发）→ `lab07-session/`（append-only 日志 + resume）
3. 每个 Lab 含：可跑的骨架代码 + 验收测试（对应书内验收 checkbox）+ README 链回书内章节
4. 书内各 Lab 节加"开箱即跑"链接

**验收**：clone 后每个 Lab `npm test`（或 pytest）绿；书内 Lab 地图每条都有可点链接。

## C3：真实轨迹解剖节（每组件章一节）

**问题**：李书的杀手锏是"解剖真实产物"（τ²-bench 任务逐字段拆、真实轨迹逐条消息分析）。
我们的锚点体系是"读码"，缺"读轨迹"。

**做法**：
1. 每个组件章新增一节「轨迹解剖」：选一条真实 session 轨迹（本机 ~/.kimi-code 或
   ~/.config/opencode 的运行记录即可生成标本），逐字段/逐消息拆解该章主题在轨迹上的显影
   （例：Ch5 解剖一次 auto-compaction 前后的消息序列；Ch7 解剖一次崩溃恢复后的 session 重建）
2. 每节固定三段：标本来源与获取方式 → 逐段拆解（带轨迹原文引用）→ 反推回源码锚点
3. 标本文件存 `docs/public/traces/`（匿名化处理，脱敏密钥与路径）

**验收**：Ch3–Ch9 每章一节；每条解剖都能从轨迹字段反跳到至少一个 file:line 锚点。

## 排期建议

C1 拆分章派工，预计每个章节 1-2 个 agent 会话；C2 是独立小项目（1 天量级）；
C3 依赖标本采集，建议先做一个试点章（推荐 Ch5，compaction 轨迹最容易复现）再推广。
