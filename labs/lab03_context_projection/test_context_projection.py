"""Lab 03 验收测试：I1（append-only）、I3（投影）、I4（预算触发）。"""

import copy
import unittest

from lab03_context_projection.context_projection import (
    Session,
    estimate_tokens,
    needs_compaction,
    project,
    summarize,
)


def make_session():
    session = Session()
    for i in range(4):
        session.append("user", f"turn-{i} " + "x" * 40)
        session.append("assistant", f"reply-{i} " + "y" * 40)
    return session


class TestContextProjection(unittest.TestCase):
    def test_under_budget_no_compaction(self):
        session = make_session()
        budget = estimate_tokens(session.turns) + 10
        self.assertFalse(needs_compaction(session, budget))
        context = project(session, budget)
        self.assertEqual(context, session.turns)  # 投影即全量

    def test_over_budget_compacts_oldest_first(self):
        session = make_session()
        context = project(session, budget_tokens=40)
        self.assertEqual(context[0]["role"], "summary")
        # 最老轮次进摘要，最新轮次原样保留在投影尾部
        self.assertIn("turn-0", context[0]["content"])
        self.assertEqual(context[-1], session.turns[-1])
        self.assertLess(estimate_tokens(context[1:]),  # kept 部分满足预算
                        estimate_tokens(session.turns))

    def test_session_is_untouched_by_projection(self):
        session = make_session()
        snapshot = copy.deepcopy(session.turns)
        project(session, budget_tokens=10)
        self.assertEqual(session.turns, snapshot)  # I1：投影不改写事实层

    def test_no_turn_is_silently_dropped(self):
        session = make_session()
        context = project(session, budget_tokens=10)
        summary = context[0]["content"]
        kept = context[1:]
        for turn in session.turns:
            covered = turn in kept or summarize(turn) in summary
            self.assertTrue(covered, f"turn lost: {turn['content'][:12]}")
        # 摘要 + 保留轮次 = 全量覆盖，不多不少
        self.assertEqual(len(kept) + summary.count("\n") + 1,
                         len(session.turns))

    def test_append_is_the_only_write_path(self):
        session = Session()
        session.append("user", "a")
        session.append("assistant", "b")
        first = session.turns[0]
        project(session, budget_tokens=0)  # 极端预算也只会折叠，不会改写
        self.assertIs(session.turns[0], first)
        self.assertEqual(len(session.turns), 2)


if __name__ == "__main__":
    unittest.main()
