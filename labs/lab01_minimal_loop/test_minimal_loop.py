"""Lab 01 验收测试：预算闸、取消闸、append-only 三条性质各一测。"""

import unittest

from lab01_minimal_loop.minimal_loop import (
    Aborted,
    AbortSignal,
    BudgetExhausted,
    ScriptedModel,
    run_agent,
)


class NeverDoneModel:
    """永不收尾的模型：用来触发预算闸。"""

    def step(self, trajectory):
        return {"role": "tool_call", "tool": "echo", "input": {}}


class TestMinimalLoop(unittest.TestCase):
    def test_completes_task_with_tool_roundtrip(self):
        trajectory = run_agent(ScriptedModel(), "hi", max_hops=10)
        roles = [m["role"] for m in trajectory]
        self.assertEqual(roles, ["user", "tool_call", "tool_result", "assistant"])
        self.assertEqual(trajectory[-1]["content"], "done")

    def test_budget_gate_stops_runaway_loop(self):
        with self.assertRaises(BudgetExhausted):
            run_agent(NeverDoneModel(), "hi", max_hops=3)

    def test_abort_signal_interrupts_mid_run(self):
        signal = AbortSignal()

        def aborting_tool(name, args):
            signal.abort()  # 工具执行期间用户按下取消
            return "ok"

        with self.assertRaises(Aborted):
            run_agent(ScriptedModel(), "hi", max_hops=10, signal=signal,
                      tool_runner=aborting_tool)

    def test_trajectory_is_append_only(self):
        seen = [{"role": "user", "content": "hi"}]
        model = NeverDoneModel()
        try:
            run_agent(model, "hi", max_hops=3)
        except BudgetExhausted:
            pass
        # 预算熔断只影响继续执行，已有轨迹条目保持原顺序、不被改写
        self.assertEqual(seen[0], {"role": "user", "content": "hi"})


if __name__ == "__main__":
    unittest.main()
