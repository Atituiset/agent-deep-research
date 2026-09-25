"""Lab 02 验收测试：路由、三道校验、call_id 回填、错误回填。"""

import unittest

from lab02_tool_router.tool_router import ToolRouter

ADD_SCHEMA = {
    "type": "object",
    "properties": {"a": {"type": "integer"}, "b": {"type": "integer"}},
    "required": ["a", "b"],
}


def make_router():
    router = ToolRouter()
    router.register("add", ADD_SCHEMA, lambda args: args["a"] + args["b"])
    return router


class TestToolRouter(unittest.TestCase):
    def test_routes_by_name_and_fills_call_id(self):
        result = make_router().handle({"id": "c1", "name": "add",
                                       "input": {"a": 2, "b": 3}})
        self.assertEqual(result, {"role": "tool_result", "tool_use_id": "c1",
                                  "content": 5})

    def test_unknown_tool_is_reported_not_raised(self):
        result = make_router().handle({"id": "c2", "name": "rm", "input": {}})
        self.assertTrue(result["is_error"])
        self.assertEqual(result["tool_use_id"], "c2")
        self.assertIn("unknown tool", result["content"])

    def test_missing_required_field(self):
        result = make_router().handle({"id": "c3", "name": "add",
                                       "input": {"a": 1}})
        self.assertTrue(result["is_error"])
        self.assertIn("missing required field: b", result["content"])

    def test_wrong_type_rejected(self):
        result = make_router().handle({"id": "c4", "name": "add",
                                       "input": {"a": "x", "b": 1}})
        self.assertTrue(result["is_error"])
        self.assertIn("expected integer", result["content"])

    def test_bool_is_not_an_integer(self):
        result = make_router().handle({"id": "c5", "name": "add",
                                       "input": {"a": True, "b": 1}})
        self.assertTrue(result["is_error"])

    def test_handler_exception_does_not_crash_router(self):
        router = ToolRouter()
        router.register("boom", {"type": "object", "properties": {}},
                        lambda args: 1 / 0)
        # handler 自身的运行时错误不在 ToolError 覆盖范围内——校验层的
        # 承诺是「可预期的失败必回填」，不可预期的崩溃应暴露给 Harness
        with self.assertRaises(ZeroDivisionError):
            router.handle({"id": "c6", "name": "boom", "input": {}})


if __name__ == "__main__":
    unittest.main()
