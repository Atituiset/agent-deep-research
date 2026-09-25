"""Lab 01：带预算与取消的最小 Agent Loop。

演示 Ch3（docs/ch03-loop.md）的论断：生产级 Loop 是「采样→执行→回填」的闭合，
其上必须叠加两道刹车——max_hops 预算闸与 abort 取消；没有刹车的 while(true)
就是 AutoGPT 式失控（见 Ch3 1.1 与 3.2）。同时 trajectory 只增不改（append-only），
这正是 Ch5 不变量 I1 在 Loop 层的预演。
"""

MAX_HOPS_DEFAULT = 25  # 对齐 Ch3：生产实现的 MAX_HOPS=25


class BudgetExhausted(RuntimeError):
    """预算闸跳闸：hop 数超过 max_hops，Loop 主动熔断而不是无限烧钱。"""


class Aborted(RuntimeError):
    """取消闸生效：abort 信号到达后 Loop 在下一个 hop 边界干净退出。"""


class AbortSignal:
    """step 级取消令牌（Ch3 3.2.3：abort 是事件，不是 Ctrl-C）。"""

    def __init__(self):
        self.aborted = False

    def abort(self):
        self.aborted = True


class ScriptedModel:
    """确定性 mock：不联网、不随机。

    规则只有一条——trajectory 末尾已有工具结果就收尾回答，否则继续发起工具调用。
    """

    def step(self, trajectory):
        last = trajectory[-1] if trajectory else None
        if last is not None and last["role"] == "tool_result":
            return {"role": "assistant", "content": "done"}
        return {"role": "tool_call", "tool": "echo", "input": {}}


def echo_tool(name, args):
    return f"{name} ok"


def run_agent(model, task, max_hops=MAX_HOPS_DEFAULT, signal=None, tool_runner=echo_tool):
    """最小 Loop：采样→执行→回填，每 hop 前先查取消、再查预算。

    返回完整 trajectory（append-only）；预算耗尽抛 BudgetExhausted，
    收到取消信号抛 Aborted——两种失败都保留已产生的轨迹，供观测与恢复。
    """
    signal = signal or AbortSignal()
    trajectory = [{"role": "user", "content": task}]
    hops = 0
    while True:
        if signal.aborted:  # 闸一：取消（打断语义）
            raise Aborted(f"aborted after {hops} hop(s)")
        if hops >= max_hops:  # 闸二：预算（hop 上限）
            raise BudgetExhausted(f"max_hops={max_hops} exhausted")
        step = model.step(trajectory)  # 采样一次
        trajectory.append(step)  # 回填：只增不改
        hops += 1
        if step["role"] == "assistant":  # 结束判定：模型主动收尾
            return trajectory
        result = tool_runner(step["tool"], step["input"])  # 执行
        trajectory.append({"role": "tool_result", "content": result})
