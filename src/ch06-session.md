# 第7章 Session / Trace / 持久化

> Session 解决“记住”、Trace 解决“说清”、持久化解决“不丢”。七家的共识是：**可重放（replay）优于可恢复（restore），追加（append）优于覆盖，可观测必须内建**。—— 本章把 Session 从“一个 Vec<Message>”还原为“一条 WAL”，把 Trace 从“打日志”还原为“分布式追踪”，逐行对证七家如何让 `--resume` 可信、让 `fork` 可分支、让崩溃不带毒。

## 本章图谱

```
历史脉络 ──► 原理抽象 ──► 七家对证 ──► 权衡取舍 ──► 未来演进
Fowler 05    Session.append  Claude/Codex  jsonl vs     Federation
WAL/LSM/rep  turn边界/幂等  Grok/DeepSeek  SQLite vs   Time-travel
jsonl→SQLite history_version OpenCode/Pi   Journal      GC/压缩
CRDT+分支    自愈repair    Claw对比表    turn不丢vs  Memory融合
可重放vs恢复 分支/fork                  live/cumul  性能
```

---
## 7.1 历史脉络：从 Event Sourcing 到 ChatGPT 后的 Session 演进

> Session 像数据库的 WAL，Trace 像分布式追踪的 span。读懂 Session 的历史，就是读懂“状态如何不丢”的工程史。

### 7.1.1 起点：Event Sourcing 2005（Fowler）与 WAL/LSM

2005 年 Martin Fowler 在 *Event Sourcing* 一文中形式化了一个反直觉思想：**不存“当前状态”，存“导致状态的所有事件”**；状态是事件折叠（fold）的结果。

```
传统 CRUD：  State_n = UPDATE(State_{n-1}, command)  →  只存 State_n（丢失因果）
Event Sourcing： State_n = fold(∅, [Event_0, ..., Event_{n-1}])  →  存全量 Event log（可重放）
```

这一思想并非凭空而来，其工程祖先是数据库的 **WAL（Write-Ahead Log）** 与 **LSM（Log-Structured Merge Tree）**：

| 祖先 | 核心机制 | 对 Session 的遗传 |
|------|----------|-------------------|
| **WAL（ARIES 1992, PostgreSQL/MySQL InnoDB）** | 先写日志再改数据；崩溃后按 LSN 重放；`fsync` 保证持久化 | Session 的 `append` 即 WAL 的 `write`；`turn/start` 即 `checkpoint`；`fsync` 对应 `flushSessionStorage()` / `Journal.sync()` |
| **LSM（O'Neil 1996, LevelDB/RocksDB）** | 内存 memtable 批量刷盘为 SSTable；后台 compaction 合并 | DeepSeek 的 `WriteBehind + Revision` 批量刷盘、Claude 的 `compactConversation()` 后台摘要，均是 LSM 的“延迟合并”思想 |
| **Replication Log（Raft 2014, Kafka 2011）** | leader append log → follower replay；log 即事实 | Grok 的 `ChatStateActor` 单 task 拥有 log、OpenCode 的 `EventV2Bridge` 广播 `SessionV1.Event.*`，均是“log 为唯一事实源” |

> 一句话遗传：**“log 即数据库”** 在 Agent 侧演变为 **“Session 即数据库”**。Session 追加即事务提交，压缩即 compaction，分支即 fork，恢复即 replay。

#### 不变量：Event Sourcing 的三条公理（对应 Session I1-I3）

```
I1  Append-only：   log 只能追加，不能原地修改已提交事件（否则 replay 不确定）
I2  Total Order：   log 有全序（LSN / history_version / offset），消费者按序重放
I3  Deterministic Fold： 同一 log 序列 fold 出同一状态（幂等、无副作用的 replay）
```

七家 Session 的分化，本质是对 I1-I3 的不同“持久化 + 排序”实现（见 7.2）。

### 7.1.2 演进：会话在 ChatGPT 2022 后的三次位移

| 阶段 | 时间 | 标志系统 | Session 形态 | 持久化 | 分支 | 失效教训 |
|------|------|----------|--------------|--------|------|----------|
| **1. 无 Session** | 2022.10 ReAct / 2022.11 ChatGPT | 纯 prompt 循环 | 内存 `Message[]` | 无 | 无 | 刷新即失忆；无法 `--resume` |
| **2. 文件 Session** | 2023 AutoGPT/BabyAGI → 2024 Claude Code / Codex | `Vec<Message>` + 文件 | `jsonl` 追加（Claude `~/.claude/projects/<hash>/<id>.jsonl`） | 无/手工 fork | 进程崩溃丢最后 1 轮（未 fsync）；多会话文件散落 |
| **3. 结构化 Session** | 2024-2025 OpenCode/Pi/DeepSeek | `Session extends Vec<Message>` + `SessionTable/PartTable` | SQLite + jsonl 双后端 + `Revision` | `fork(sessionID, messageID?)` 克隆 msgs+parts + `idMap` 重映射 | 崩溃后残留 `dangling tool_calls` 导致后续每轮 PTL（Grok 教训） |
| **4. 可观测 Session** | 2025-2026 Grok/DeepSeek/Claude | `ConversationItem + UsageLedger + TraceBuffer` | `Journal + turn_capture offset` | `xai-fast-worktree (btrfs/overlay)` 真分支 | `live vs cumulative` 计费用量分离；无 Trace 则无法归因 cache miss |

**位移 1 — 从“内存数组”到“追加日志”**：ChatGPT 初期 `history = []` 仅存内存，刷新即丢。Claude 率先把 `getTranscriptPath() → ~/.claude/projects/<cwd-hash>/<sessionId>.jsonl` 作为 WAL，每条 `user/assistant/tool_result` 即时追加，保证 `--resume` 可重放。这是 **I1 的落地**。

**位移 2 — 从“单文件”到“双后端+分支”**：当会话需被检索（`/load <id>` / `listByProject`）与分支（`fork` 探索不同解法）时，`jsonl` 的“只能逆序扫描”成为瓶颈。OpenCode 引入 `Drizzle SessionTable{project_id,workspace_id,parent_id} + PartTable{session_id, message_id, part_type}`（见 7.3.3 schema），Pi 提供 `session-tree + sqlite-backend` 双实现，DeepSeek 同时支持 `jsonl/sqlite` 双后端（插件化 `WriteBehind`）。分支模型从“文件拷贝”升级为“git branch”语义（见 7.1.4）。

**位移 3 — 从“可恢复”到“可重放 + 可观测”**：仅“能恢复最近状态”不够，生产要求“能重放任意时刻、能审计每 turn 的 token/工具/耗时、能从崩溃中自愈”。Grok 的 `Journal + turn_capture{turn_start_offset, pre_replacement_messages}` 与 Claude 的 `tengu_*` 全链路事件，即此位移的标杆。

### 7.1.3 持久化 lineage：`jsonl → SQLite → CRDT/Journal`

```
1960s 磁带日志
  │
  ├─ 1992 ARIES/WAL ──► PostgreSQL WAL ──► 2011 Kafka log ──► 2014 Raft log
  │     先写后改           LSN 排序           分区追加           共识追加
  │
  ├─ 1996 LSM ──► 2011 LevelDB/RocksDB ──► 2024 DeepSeek WriteBehind
  │     批量合并          SSTable              Revision 延迟写
  │
  ├─ 2022 ChatGPT 内存数组 ──► 2024 Claude jsonl (session.jsonl) ──► 2025 DeepSeek jsonl/sqlite 双后端
  │                                追加+100ms防抖                  Revision+WriteBehind
  │
  ├─ 2024 OpenCode SQLite (Drizzle) ──► 2025 Pi sqlite-backend
  │     SessionTable/PartTable              session-tree
  │
  └─ 2011 CRDT (Shapiro) ──► 2020 Automerge ──► 2025 Grok Journal + 未来 Session Federation
        无冲突合并              JSON CRDT              跨设备多写合并
```

| 代际 | 代表 | 追加语义 | 查询 | 分支 | 崩溃一致性 | 适用 |
|------|------|----------|------|------|------------|------|
| **jsonl** | Claude `session.jsonl` + `history.jsonl` | 行追加（`JSON.stringify(event)+"\n"`），`O(1)` | 逆序扫描 `makeLogEntryReader()` | 文件拷贝 + `compact_boundary.preservedSegment{head/tail/anchor}` 重链接 | `flushSessionStorage()` 100ms 防抖；进程崩溃丢最后 1 行 | 单机 CLI、原型、最简可重放 |
| **SQLite** | OpenCode `Drizzle` + Pi `sqlite-backend` + DeepSeek `sqlite` | 事务批量写（`INSERT PartTable`），`O(log n)` | SQL `listByProject(roots/start/search)` | `Session.fork()` 克隆 rows + `idMap` 重映射 `parentID/tail_start_id` | WAL 模式 + 事务；进程崩溃可恢复到最后事务 | 需检索/分页/多项目隔离的生产 |
| **Journal/CRDT** | Grok `xai-sqlite-journal Journal` + 未来 Federation | `Journal.append(ConversationItem)` + `turn_capture offset` 批量投影 | 游标 + offset 切片 `conversation[off..]` | `xai-fast-worktree (btrfs/overlay)` 真文件分支 + 内存逻辑分支 | `Journal` 即 WAL；`ChatState::new()` 时 `dedup + repair` 自愈 | 云端多租户、跨设备、高并发 |

> 本质：**jsonl 是“最诚实的 log”**（可重放、无 schema 约束、易审计）；**SQLite 是“可查询的 log”**（可索引、可分页、需 schema 迁移）；**Journal/CRDT 是“可合并的 log”**（多写端、无冲突、为 Federation 预演）。

### 7.1.4 分支模型：`git branch` 的类比与 `fork/join` 语义

Session 的分支是 Agent 探索“不同解法”的核心（如 `plan` 模式先分支再合并），其模型直接抄自 `git`：

```
git:      commit ──► branch ──► merge (3-way) ──► log --graph
Session:  turn   ──► fork   ──► (无自动 merge，仅保留多分支) ──► listByProject(roots)
```

#### 分支原语对比

| 维度 | `git branch` | Session `fork` | 共同约束 |
|------|--------------|----------------|----------|
| **创建** | `git branch <new> <commit>` | `Session.fork(sessionID, messageID?)`（OpenCode） / `session-tree.branch`（Pi） / `xai-fast-worktree`（Grok） | 需指定锚点（`commit`/`messageID`/`turn_capture offset`） |
| **隔离** | worktree / 文件拷贝 | 内存 `structuredClone` + DB 克隆 rows + `idMap` 重映射（OpenCode） / `btrfs/overlay` 快速 worktree（Grok） | 隔离级别：内存 < DB 克隆 < 文件 worktree |
| **血缘** | `parent` 指针 | `SessionTable.parent_id` + `tail_start_id` + `fork #N` 标题 | 血缘可追溯，`listByProject` 可画树 |
| **合并** | `merge/rebase` | **无自动合并**（Agent 选择“保留分支”或“人工 cherry-pick”），Pi 的 `session-tree` 仅导航不合并 | 避免“自动合并导致上下文污染” |
| **查询** | `git log --graph --all` | `Session.query(roots/start/search)` + Claude `getMessagesAfterCompactBoundary()` | 树状可视化 |

#### 分支图（ASCII，OpenCode/Pi/Grok 的归一）

```
时间 ──────────────────────────────────────────────────────►

main:  ──●──●──●──●──●  (Session A, parent_id=null)
          │  │
          │  └─●──●  (fork #1, parent_id=A, tail_start_id=msg_3, messageID=msg_3)
          │     │  "尝试用 Rust 重写"
          │     └─●  (fork #1.1, 从 #1 的 msg_5 再 fork)
          │
          └─●──●──●  (fork #2, parent_id=A, tail_start_id=msg_2)
                "尝试 Plan 模式"

存储（OpenCode Drizzle，见 7.3.3 schema）：

SessionTable:  | id | parent_id | title      | createdAt |
               | A  | null      | main       | t0        |
               | A1 | A         | fork #1    | t1        |
               | A2 | A         | fork #2    | t2        |

PartTable:     | session_id | message_id | parent_id | part_type | content |
               | A          | msg_1      | null      | user      | ...     |
               | A          | msg_2      | msg_1     | assistant | ...     |
               | A1         | msg_1'     | null      | user      | (clone) |
               | A1         | msg_4'     | msg_3'    | assistant | (new)   |
               └─ idMap: {msg_1→msg_1', msg_2→msg_2', msg_3→msg_3'} 重映射血缘
```

> 设计要点：**分支是“写时复制（COW）”**。OpenCode 的 `Session.fork()` 克隆 `msgs+parts` 并重映射 `parentID/tail_start_id`，保证 `fork` 后两分支的 `history_version` 独立递增、互不污染；Grok 的 `xai-fast-worktree (btrfs/overlay)` 进一步把“文件分支”也 COW，避免“子 Agent 改文件污染主 Session”。

### 7.1.5 可重放（Replay） vs 可恢复（Restore）：一字之差，天壤之别

| 维度 | 可重放（Replay） | 可恢复（Restore） |
|------|------------------|-------------------|
| **定义** | 从 `log[0..n]` 按序 `fold` 出**任意时刻**的 `State_n`；幂等、可审计 | 仅恢复**最近一次 checkpoint** 的 `State_n`；丢中间因果 |
| **要求** | Append-only log + 全序 + 确定性 fold（I1-I3） | 仅需最新快照（snapshot） |
| **能力** | `--resume` 到任意 turn、`fork` 到任意 `messageID`、`trace` 回放、`time-travel debugging` | `--resume` 仅到最后 turn，无法审计“为何产生该决策” |
| **成本** | 存储全量 log（jsonl/SQLite/Journal），查询需扫描或索引 | 存储单快照，查询 `O(1)` |
| **代表** | Claude `session.jsonl` 全量 + `makeLogEntryReader()` 逆序读；DeepSeek `Session.append(eventType)` 全量事件；Grok `Journal` 全量 `ConversationItem` | 早期 `StoredSession{messages,tokens}` 直写（Claw 早期）；`snapshot/restore` 快照 |

```
可恢复（Restore）：   snapshot_n ──► State_n   （丢 [0..n-1] 因果，无法 fork 到 n-1）

可重放（Replay）：    log[0] → log[1] → ... → log[n]  ──fold──► State_{n+1}
                        │        │              │
                        ├─► State_1  State_2  State_n+1  （任意前缀可 fold）
                        └─► fork 到 log[k] 再 replay → 新分支（git branch 语义）
```

> 各家共识：**必须可重放**。`my-agent` 的 `ContextManager.serialize()` 存 `rawHistory + summaries` 即“快照+增量 log”混合，为的就是既可快速恢复（读快照），又可在 `fork` 时重放（读 log）。若仅可恢复，则 `Session.fork(sessionID, messageID?)` 无法实现“从中间消息分支”。

#### 失败案例：仅可恢复的代价

- **Claw 早期** `rust/crates/runtime/src/session.rs Session{version,messages}` 直写 `~/.claw/sessions/<uuid>.json`，无 log，仅 snapshot。后果：进程在 `assistant tool_calls` 与 `tool_result` 之间崩溃，snapshot 残留 `dangling tool_calls`，下次启动直接 PTL（见 7.2.5 自愈）。
- **单一 snapshot 的 fork 失效**：若仅存快照，`fork` 只能从最新状态分叉，无法“回到 3 轮前重试另一种解法”——这正是 `plan` 模式与 `branch/navigation`（Pi `docs/book/14-branch-navigation.md`）要解决的。

---

## 7.2 原理深潜

### 7.2.1 Session.append：唯一写路径与事件即日志

Event Sourcing 落到 Agent 上，就是 `append(eventType)` 成为唯一写路径，任何读取（投影/恢复/fork）都是 log 的 fold：

```ts
// DeepSeek packages/session/*: 事件类型全集（各家大同小异）
type SessionEvent =
  | { t: 'turn/start' }                              // turn 边界锚点（崩溃恢复存档点）
  | { t: 'step/start' | 'step/end' }
  | { t: 'user/message'; msg: UserMsg }
  | { t: 'assistant/chunk'; seq: number; delta: string } // 流式增量，seq 保证全序
  | { t: 'assistant/message'; msg: AsstMsg; usage?: TokenUsage }
  | { t: 'request/header' | 'request/context' };     // 归一去重后入 log
```

三条不变量（对应 Ch2 的 I1）：

1. **全序**：每个事件带单调 `seq`/`Revision`，流式 chunk 不乱序；
2. **幂等 fold**：同一 log 重放两遍结果一致——`request/header|context` 需去重（DeepSeek `canonicalHeader/headerEquals`）；
3. **先写后调**：user 消息在 `callModel()` 前落盘（Claude `QueryEngine.ts:451 recordTranscript` 预写），崩溃时"用户说过什么"永不丢。

### 7.2.2 turn/start 边界不丢的三种实现

"崩溃后从哪个事件续跑"是持久化的核心难题。八家给出三种等价但成本不同的方案：

```
方案A 预写（write-ahead）：    Claude —— submitMessage 先写 user 消息再调模型
方案B 版本号（versioning）：   Codex —— ContextManager.history_version 每次 record_items 递增
方案C 偏移量（offset capture）：Grok —— turn_capture.turn_start_offset 记录本 turn 在 log 中的起点
```

| 方案 | 恢复代价 | 写放大 | 适用 |
|------|---------|--------|------|
| A 预写 | 读 log 尾部即可 | 低（每 turn 一条） | jsonl 追加型存储 |
| B 版本号 | 需索引 version→log 位置 | 中 | 内存态历史 + 外置 log |
| C 偏移量 | `conversation[offset..]` bulk 切片，O(1) 定位 | 最低 | Actor 内大数组 + Journal |

Grok 的 offset 设计最精巧：`turn_capture.pre_replacement_messages` 在 compaction 改写历史前暂存旧段落，`restore_snapshot` 时可撤销压缩——相当于给 log 加了"逻辑 undo"。

### 7.2.3 崩溃恢复时序与自愈

```
正常运行：
  append(turn/start) → append(user/msg) ──► callModel() ──► append(assistant/chunk×N)
                                                          → append(assistant/message)
在 assistant/chunk 与 tool_result 之间断电：
  log: [turn/start, user/msg, asst(chunk1), asst(chunk2)✂]  ← tool_calls 已声明、result 缺失
重启自愈（Grok ChatState::new()）：
  dedup_duplicate_tool_results()   // 重试导致的重复 result 折叠为一条
  repair_dangling_tool_calls()     // 为悬垂 tool_calls 补合成 tool_result(is_error=true)
  → log 变为合法对话，模型可继续推理而非 PTL
```

> 反例（无自愈的后果）：Claw 早期 snapshot 直写，残留悬垂 `tool_calls`；下次请求把非法历史发给 API → `prompt_too_long` 或 400。这正是 Ch11 自愈层的存在理由。

### 7.2.4 分支：idMap 重映射算法

`Session.fork(sessionID, messageID?)` 本质是"log 的 copy-on-write 视图"。OpenCode 的实现要点：

```ts
// packages/opencode/src/session/session.ts:693（伪代码化）
function fork(sid, mid?) {
  const msgs = mid ? page(sid, upTo(mid)) : all(sid);       // 只取前缀
  const idMap = new Map(msgs.map(m => [m.id, newId()]));     // 旧ID→新ID
  const parts = cloneParts(msgs).map(p => remap(p, idMap));  // part.parentID 级联改写
  return create({ ...meta, parentID: sid, title: `${baseTitle} #${n}` });
}
```

两个易错点：(1) `part` 与 `message` 是两张表，重映射必须级联，否则 PartDelta 事件找不到宿主；(2) 分支标题必须可区分（OpenCode 用 `fork #N`），否则分叉树在 `listByProject()` 里不可读。

### 7.2.5 live vs cumulative：用量分账原则

Trace 里同一个 `total_tokens` 有两种语义，混用会导致压缩误触发或账单错误（Ch10 展开）：

```
live        = 当前上下文实际长度       → 驱动 should_auto_compact、/context 进度条
cumulative  = Σ 各次请求 input+output → 驱动计费、报表
```

Grok 的教训最典型：服务端 loop 工具（`web_search/x_search`）会让 API 返回的 `total_tokens` 虚高（含搜索内部消耗），于是 `apply_terminal_event_overrides()` 用 `context_details.input+output` **重写 total 为 live**，而 `input/output/cached` 保持 cumulative 供计费。

## 7.3 对证分解：九家源码对证

### 7.3.1 总览对比表

| 家 | Session 载体 | 持久化介质 | 分支能力 | 自愈/查询 | 边界方案 |
|----|-------------|-----------|---------|----------|---------|
| Claude | `~/.claude/projects/<cwd-hash>/<sessionId>.jsonl` + 全局 `history.jsonl` | jsonl 追加 + `flushSessionStorage()` 100ms 防抖 | `compact_boundary.preservedSegment{head/tail/anchor}` 重链接 | `makeLogEntryReader()` 逆序读 + lockfile 并发保护 | A 预写（`QueryEngine.ts:451`） |
| Codex | `ContextManager{items, history_version}`（`context_manager/history.rs:93`） | `rollout.jsonl` + thread-manager | 多 thread + `ResumeSource` | `history_version` 递增检测过期视图 | B 版本号 |
| Grok | `ChatState.conversation: Vec<ConversationItem>` | `xai-sqlite-journal Journal`（SQLite） | worktree 级文件分支（`xai-fast-worktree` btrfs/overlay） | 启动自愈 `repair_dangling_tool_calls` | C 偏移量（`turn_capture`） |
| DeepSeek | `session-persistence/{jsonl,sqlite}` 双后端 | Revision + WriteBehind 延迟批量写 | session-checkpoint-policy 快照点 | `SessionQuery` SQL 检索 + projection-cache | 事件全序 seq |
| OpenCode | Drizzle `SessionTable` + `PartTable`（SQLite） | SQLite + `EventV2Bridge` 事件桥 | `Session.fork()` idMap 重映射（消息级） | `listByProject(roots,start,search)` 树查询 | 消息 ID 锚定 |
| Pi | `session-tree` + `sqlite-backend` | SQLite | branch/navigation 显式导航（`book/14`） | `AgentContext.messages` 全量内存保留 | 树结构天然定位 |
| Claw | `src/session_store.py StoredSession` | JSON 直写（原型级） | 无 | 无自愈 | 无边界保障 |
| **Qwen-Agent** | **核心库无持久层**：`messages` 由调用方持有并传入 `run()`（`agent.py:78`） | 无（会话文件仅在 `qwen_server` GUI 层） | 仅 `copy.deepcopy(messages)` 防御性拷贝（`agent.py:91`），无 fork | 工具异常转字符串回填（`_call_tool` `agent.py:178-203`），无崩溃自愈 | 无 |

### 7.3.2 Qwen-Agent：库形态 vs 产品形态的分水岭

Qwen-Agent 是八家中唯一的"纯框架库"：它把六件套中的 **Session 整件留白**，交还给宿主应用。这个反例的价值在于划清了边界——

```
库形态（Qwen-Agent / pi 的 agent 包）：
  run(messages) -> Iterator[responses]      # 无状态，history 归 caller
  ✓ 可嵌入任意宿主（GUI/Web/测试）
  ✗ 无 resume/fork/审计；长会话靠 caller 自己拼 history

产品形态（Claude Code / Codex / OpenCode）：
  进程内持有 Session + 自动持久化 + --resume
  ✓ 断点续传、分支、trace 审计
  ✗ 存储管理/GC/隐私成为产品责任
```

对证细节：`qwen_agent/agent.py:78 run()` 入口处 `copy.deepcopy(messages)`——因为 `_run` 会原地 `messages.extend(output)`，不深拷贝会污染调用方的列表。这是库形态下唯一需要的"隔离"，却也是它全部的状态管理。同理 `fncall_agent.py:73 _run()` 循环里 `response` 与 `messages` 双轨追加（一个对外 yield、一个对内喂模型），本质是"内存版双写 log"——**库不是没有 Session 思想，只是把它压缩成了两个 list 变量**。

> 结论：Session 不是"要不要做"，而是"做在哪一层"。库把它上移给宿主，产品把它下沉为自己——Pi 是中间态（core 库无状态 + storage 包可选挂载）。

### 7.3.3 Claude：预写 + 防抖 + 逆序读的产品级细节

`claude-code-haha/src/utils/sessionStorage.ts` 三个值得抄的点：

1. **路径按 cwd hash 分桶**：`projects/<cwd-hash>/<sessionId>.jsonl`，多项目互不干扰且天然支持"按项目列出会话"；
2. **100ms 防抖 flush**：高频 chunk 写合并为低频磁盘写，崩溃最多丢 100ms 增量（user 消息因预写不受影响）；
3. **逆序读**：`makeLogEntryReader()` 从文件尾反向扫描找最近 N 条，避免全量加载大会话。

### 7.3.4 Grok：Journal + Actor 的强一致组合

Actor 单 task 独占 `ChatState`（Ch3），持久化由独立的 `xai-sqlite-journal` 承担——内存数组与磁盘 journal 通过 `turn_start_offset` 对齐。这形成"两级 log"：内存 `Vec<ConversationItem>` 服务热路径（bulk 切片投影），SQLite journal 服务冷恢复（逐条 replay）。崩溃后 `ChatState::new()` 从 journal 重建内存态并跑自愈，两级各司其职。

## 7.4 结论权衡

### 7.4.1 存储介质决策树

```
需要跨进程共享/SQL 检索？ ──是──► SQLite（OpenCode/Pi/DeepSeek/Grok Journal）
        │否
需要人肉查看/管道友好？   ──是──► jsonl 追加（Claude/Codex rollout）
        │否
纯内存 + 宿主持久化      ──────► 无持久层（Qwen-Agent）
```

| 维度 | jsonl 追加 | SQLite | Journal(SQLite)+内存双轨 |
|------|-----------|--------|------------------------|
| 写吞吐 | 高（顺序追加） | 中（事务开销） | 高（内存热写） |
| 恢复速度 | 尾部扫描快，全量慢 | 索引查询 O(log n) | O(1) offset 切片 |
| 分支支持 | 弱（需复制文件段） | 强（外键级联） | 强（offset + COW） |
| 人肉调试 | 直接 cat/tail | 需 CLI | 两头兼顾 |
| 代表 | Claude/Codex | OpenCode/Pi | Grok/DeepSeek(sqlite 后端) |

### 7.4.2 durability vs throughput

逐事件同步写（durability 最高）与 WriteBehind 批量刷盘（吞吐最高）之间，生产答案通常是**分级**：边界事件（`turn/start`、`user/message`、`assistant/message`）同步落盘，增量事件（`assistant/chunk`）防抖/延迟合并。Claude 的 100ms 防抖与 DeepSeek 的 Revision+WriteBehind 是同一原则的两种参数化。判据一句话：**丢一条 chunk 能重放模型输出吗？不能丢的才同步写**——chunk 丢了顶多 UI 回退半句，user 消息丢了则整个 turn 因果断裂。

### 7.4.3 三条工程铁律（对证汇总）

1. **append-only + 先写后调**（I1 + 方案A）：所有家殊途同归；
2. **边界锚点必须有**（turn/version/offset 三选一），否则崩溃恢复退化为赌博；
3. **自愈在启动时做**，不在读写路径做——Grok 把 `repair_dangling_tool_calls` 放 `ChatState::new()`，一次付清，热路径零开销。

## 7.5 未来方向

1. **Session Federation（跨设备同步）**：本地 log 如何与云端任务（Codex cloud-tasks、CCR 远程 agent）双向同步？CRDT/Merkle-DAG 式 merge 将从论文兴趣变成产品刚需，Pi 的 session-tree 与 OpenCode 的 share_url 是雏形。
2. **Time-travel debugging for Agents**：Redux DevTools 之于前端 = Trace replay 之于 Agent。"跳到第 k 个工具调用、改输入、从该点分叉重放"会把 fork 从功能变成调试器原语。
3. **Log GC 与分层归档**：全量可重放的代价是无限增长。未来会出现"热 log（近 N turn）/温快照（compaction 边界）/冷归档（对象存储+摘要索引）"三级，DeepSeek 的 projection-cache 已在做温层。
4. **Session–Memory 合流**：Memory 系统（Ch6）成熟后，Session log 会分化出"事实层"（供 memory ingestion）与"过程层"（供 replay），两层不同 retention 策略——FadeMem 式衰减可能直接作用在冷 log 上。
5. **库形态的标准化回归**：MCP 统一了工具，下一个被标准化的可能是"会话导出格式"（类 memorywire 的 sessionwire）：Qwen-Agent 这类库只要实现 import/export 即可获得完整 Session 能力，而不必自带持久层。

## Lab 7：最小 append-only Session（约 120 行 TS）

**目标**：实现"事件 log + turn 边界 + 崩溃自愈 + fork"四件套的最小可用版。

```ts
// lab/session.ts —— 骨架，验收见下
type Ev =
  | { seq: number; t: 'turn/start' }
  | { seq: number; t: 'user'; msg: string }
  | { seq: number; t: 'asst'; msg: string; calls?: { id: string }[] }
  | { seq: number; t: 'tool_result'; id: string; ok: boolean };

class SessionStore {
  private log: Ev[] = [];
  private lastTurnStart = 0;
  constructor(private persistPath?: string) {}            // 每次 append 同步落盘（简化）
  append(e: Omit<Ev, 'seq'>) { /* 1. 分配递增 seq  2. turn/start 记录 offset  3. 落盘 */ }
  repair(): number { /* 2. 扫描尾部：asst.calls 中没有对应 tool_result 的 id，
                            补 {t:'tool_result', ok:false}；返回修复数 */ }
  fork(atSeq: number): SessionStore { /* 3. 取 log[0..atSeq) 深拷贝为新 store */ }
  replay(): string[] { /* 4. fold 出最终对话视图 */ }
}
```

**验收**：
- [ ] 写入 3 个 turn 后 kill -9 进程，重启能 `replay()` 出完整前缀；
- [ ] 手工删掉最后一条 `tool_result` 再 `repair()`，修复数=1 且后续 LLM 调用不再报 dangling；
- [ ] `fork(atSeq)` 后两个 store 各自 append 互不影响（COW 生效）。

**常见坑**：① 忘记在 `turn/start` 更新 offset，导致恢复点漂移；② fork 用浅拷贝，两分支共享同一数组；③ repair 只查最后一个 turn——若崩溃发生在 compaction 之后需全量扫（Grok 选择启动时全量，正是为此）。

## 小结与思考题

- [ ] 能画出"事件类型全集 + 三不变量"，说明为何 `assistant/chunk` 可异步写而 `user/message` 必须 pre-write
- [ ] 能对比 turn 边界三方案（预写/版本号/偏移量）的恢复代价与适用存储
- [ ] 能解释 Qwen-Agent "无持久层"不是缺陷而是分层选择，及库/产品形态各自的代价
- [ ] 能说出 live vs cumulative 混用的两种事故表现

**思考题**：
1. 若把 Claude 的 100ms 防抖改成 0ms（每 chunk 同步 fsync），吞吐损失多少数量级？什么场景值得？
2. `compact_boundary.preservedSegment` 重链接失败时，`--resume` 应报错还是降级截断？依据？
3. 给 Qwen-Agent 补一个可选 `SessionStore` 插件接口，API 怎么设计才不破坏 `run(messages)` 的纯函数性？

---
