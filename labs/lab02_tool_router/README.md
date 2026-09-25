# Lab 02：带 schema 校验的 Tool Router

**一句话论断**：工具是带 schema 的契约而不是裸函数——模型的 tool_call 必须先过名称/类型/required 三道校验才允许执行，结果一律以 tool_result 按 call_id 回填；校验失败也回填错误结果，因为模型需要「看到」失败才能自我修正。

**对应章节**：[Ch4 Tools](../../docs/ch04-tools.md)（含「Lab 4：实现一个带 schema 校验的 Tool Router」一节）

## 实现要点（`tool_router.py`，<100 行）

- `ToolRouter.register(name, schema, handler)`：按名注册，handler 不直接暴露给模型。
- `validate`：unknown tool / input 非 object / 缺 required / 类型不符（含 `True` 不是 integer 的 Python 陷阱）四种失败全部拒绝。
- `handle(tool_call)`：永远返回带 `tool_use_id` 回填的 tool_result；可预期失败回填 `is_error: True` 而非抛异常。

## 运行

```bash
python3 -m unittest lab02_tool_router.test_tool_router -v   # 在 labs/ 目录下
# 或在仓库根：
python3 -m unittest discover -s labs -v
```

六条测试即验收标准：按名路由 + call_id 回填 / 未知工具 / 缺 required / 类型错误 / bool≠integer / handler 自身崩溃不吞掉。
