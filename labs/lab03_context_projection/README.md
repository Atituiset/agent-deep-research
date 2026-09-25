# Lab 03：append-only Session + 预算投影 + compaction 触发

**一句话论断**：「投影而非改写」——Session 只增不改（I1），上下文永远由 `Context = project(Session)` 现算（I3），超预算时最老轮次折叠成摘要进入投影而 Session 本体不动（I4）。

**对应章节**：[Ch5 Context](../../docs/ch05-context.md)（5.2.2 预算三档推导的不变量 I4；5.4.3 投影 vs 重写的不变量 I1/I3）

## 实现要点（`context_projection.py`，<100 行）

- `Session`：事实层，`append()` 是唯一写路径；resume/fork 依赖这份全量历史。
- `estimate_tokens`：`chars/4` 粗估算，对齐书中 5.2.1。
- `needs_compaction`：「估算→预算→触发」链路的触发判据。
- `project(session, budget)`：超预算时从最老轮次开始折叠为一条 summary 消息，kept 轮次原样保留；**Session 不被触碰**。

## 运行

```bash
python3 -m unittest lab03_context_projection.test_context_projection -v   # 在 labs/ 目录下
# 或在仓库根：
python3 -m unittest discover -s labs -v
```

五条测试即验收标准：预算内投影即全量 / 超预算最老优先压缩 / 投影后 Session 深比较不变（I1）/ 没有任何轮次被静默丢弃 / 极端预算下 append 仍是唯一写路径。
