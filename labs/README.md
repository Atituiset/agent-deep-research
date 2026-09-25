# Agent Deep Research · Labs

与书配套的可运行实验包：纯 Python 3.10+ 标准库，零依赖，不联网。每个 lab 用一段 <100 行的实现 + 一组 unittest 验收测试，验证书中的一条核心论断。

## 一览

| Lab | 验证的论断 | 对应章节 | 对应 Lab | 运行方式 |
| --- | --- | --- | --- | --- |
| [lab01_minimal_loop](./lab01_minimal_loop/) | Loop 必须自带刹车：max_hops 预算闸 + abort 取消，trajectory 只增不改 | [Ch3 Loop](../docs/ch03-loop.md) | — | `python3 -m unittest lab01_minimal_loop.test_minimal_loop -v` |
| [lab02_tool_router](./lab02_tool_router/) | 工具是带 schema 的契约：三道校验 + 按名路由 + call_id 回填 | [Ch4 Tools](../docs/ch04-tools.md) | Lab 4 | `python3 -m unittest lab02_tool_router.test_tool_router -v` |
| [lab03_context_projection](./lab03_context_projection/) | 投影而非改写：Session append-only（I1）、Context = project(Session)（I3）、预算触发压缩不动事实层（I4） | [Ch5 Context](../docs/ch05-context.md) | — | `python3 -m unittest lab03_context_projection.test_context_projection -v` |

单 lab 运行命令在 `labs/` 目录下执行；在仓库根一次跑全部：

```bash
python3 -m unittest discover -s labs -v
```

## 设计原则

1. **mock 不联网、不随机**：model 一律用确定性规则（如「trajectory 里已有工具结果就收尾」），测试在任何机器、任何时间结果一致。
2. **每个 lab 实现 <100 行**：只保留论断本身所需的最小结构，让读者一次读完；教学级注释（中文要点、英文标识符）。
3. **测试即验收标准**：每个测试方法对应书中一条可证伪的性质（预算闸跳闸、schema 拒绝、Session 不被改写……），全绿即论断成立。
4. **三个 lab 递进**：lab01 的 append-only trajectory 是 lab03 Session 的预演；lab02 的 tool_result 回填正是 lab03 中被投影、被压缩的轮次内容。
