# Lab 01：带预算与取消的最小 Agent Loop

**一句话论断**：生产级 Loop 是「采样→执行→回填」的闭合，其上必须叠加 max_hops 预算闸与 abort 取消两道刹车；没有刹车的 `while(true)` 就是 AutoGPT 式失控。

**对应章节**：[Ch3 Loop](../../docs/ch03-loop.md)（3.2 原理深潜：五道闸、MAX_HOPS=25、取消语义）

## 实现要点（`minimal_loop.py`，<100 行）

- `ScriptedModel`：确定性 mock——trajectory 末尾已有工具结果就收尾，否则继续调用工具；不联网、不随机。
- `run_agent`：每个 hop 先查 `AbortSignal`、再查 `max_hops` 预算，然后才「采样→执行→回填」。
- trajectory append-only：预算熔断（`BudgetExhausted`）与取消（`Aborted`）都保留已产生的轨迹。

## 运行

```bash
python3 -m unittest lab01_minimal_loop.test_minimal_loop -v   # 在 labs/ 目录下
# 或在仓库根：
python3 -m unittest discover -s labs -v
```

四条测试即验收标准：正常完成一轮 tool roundtrip / 预算闸熔断失控模型 / abort 中途打断 / 轨迹只增不改。
