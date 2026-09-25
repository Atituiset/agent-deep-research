"""Lab 03：append-only Session + project() 预算投影 + compaction 触发。

演示 Ch5（docs/ch05-context.md，5.2.2 与 5.4.3）的不变量 I1/I3/I4，即
「投影而非改写」：Session 是只增不改的事实层（I1：append 是唯一写路径）；
发给模型的上下文永远由 Context = project(Session) 现算（I3）；估算超预算时
触发 compaction——最老轮次折叠成摘要进入投影，Session 本体一个字符都不动
（I4 预算不变量）。改写 Session 的实现会让 resume/fork 丢失历史。
"""

CHARS_PER_TOKEN = 4  # 对齐 Ch5 5.2.1：chars/4 的粗粒度 token 估算


class Session:
    """事实层：只增不改。resume/fork 依赖这份全量历史。"""

    def __init__(self):
        self.turns = []

    def append(self, role, content):  # I1：唯一写路径
        self.turns.append({"role": role, "content": content})


def estimate_tokens(turns):
    """粗粒度估算：够用即可触发，精细估算（tiktoken）留给生产实现。"""
    return sum(len(t["content"]) for t in turns) // CHARS_PER_TOKEN


def needs_compaction(session, budget_tokens):
    """链路「估算→预算→触发」的触发判据。"""
    return estimate_tokens(session.turns) > budget_tokens


def summarize(turn):
    """最老轮次的占位摘要：真实系统由小模型生成，lab 里确定性截断即可。"""
    return f"[{turn['role']}] {turn['content'][:20]}..."


def project(session, budget_tokens):
    """I3：Context = project(Session)。

    超预算时从最老轮次开始折叠为一条 summary 消息；kept 轮次原样保留。
    Session 不被触碰——压缩只发生在投影层。
    """
    kept = list(session.turns)
    summarized = []
    if needs_compaction(session, budget_tokens):
        while kept and estimate_tokens(kept) > budget_tokens:
            summarized.append(summarize(kept.pop(0)))  # 压缩：最老优先
    context = []
    if summarized:
        context.append({"role": "summary", "content": "\n".join(summarized)})
    context.extend(kept)
    return context
