"""Lab 02：带 schema 校验的 Tool Router。

演示 Ch4（docs/ch04-tools.md）与 Lab 4 的论断：工具是带 schema 的契约而不是
裸函数——模型给出的 tool_call 必须先过名称/类型/required 三道校验才允许执行，
结果一律以 tool_result 形态按 call_id 回填；校验失败也是回填错误结果而非异常，
因为模型需要「看到」失败才能自我修正。
"""

JSON_TYPES = {
    "string": str,
    "number": (int, float),
    "integer": int,
    "boolean": bool,
    "object": dict,
    "array": list,
}


class ToolError(Exception):
    """路由/校验层的可预期失败，最终都会被回填成 is_error 的 tool_result。"""


class UnknownTool(ToolError):
    pass


class SchemaError(ToolError):
    pass


class ToolRouter:
    """按名注册、按名路由：handler 永远不直接暴露给模型。"""

    def __init__(self):
        self._tools = {}

    def register(self, name, schema, handler):
        self._tools[name] = (schema, handler)

    def validate(self, name, args):
        if name not in self._tools:
            raise UnknownTool(f"unknown tool: {name}")
        schema, _ = self._tools[name]
        if not isinstance(args, dict):
            raise SchemaError("input must be an object")
        for key in schema.get("required", []):
            if key not in args:
                raise SchemaError(f"missing required field: {key}")
        for key, spec in schema.get("properties", {}).items():
            if key not in args:
                continue
            expected = JSON_TYPES[spec["type"]]
            value = args[key]
            # bool 是 int 的子类，integer/number 校验要先把 true/false 挡掉
            if spec["type"] in ("integer", "number") and isinstance(value, bool):
                raise SchemaError(f"field {key}: expected {spec['type']}")
            if not isinstance(value, expected):
                raise SchemaError(f"field {key}: expected {spec['type']}")

    def handle(self, tool_call):
        """处理一条 tool_call，永远返回带 call_id 回填的 tool_result。"""
        call_id = tool_call.get("id")
        try:
            name = tool_call["name"]
            args = tool_call.get("input", {})
            self.validate(name, args)
            _, handler = self._tools[name]
            return {"role": "tool_result", "tool_use_id": call_id,
                    "content": handler(args)}
        except ToolError as exc:  # 校验/路由失败：回填错误，让模型看到
            return {"role": "tool_result", "tool_use_id": call_id,
                    "is_error": True, "content": str(exc)}
