# 附录 B：被否决的观点及原因

本附录记录了在 3-vote 对抗性验证中被否决的主张（≥ 2/3 否决）。了解"什么被否决了"和"为什么被否决"同样重要——它帮助我们区分"看起来对的"和"经过验证的"。

---

## 否决的量化性能主张

### 1. Letta (GPT-4o-mini + filesystem) 74.0% vs Mem0 68.5%

**主张**:
> Letta agents running GPT-4o-mini with plain filesystem tools (grep, search_files, open/close) achieve 74.0% accuracy on the LoCoMo long-conversation QA benchmark, outperforming Mem0's best graph-based variant at 68.5%.

**否决**: 0-3

**可能原因**:
- Benchmark（LoCoMo）的适用性存疑——是否代表真实场景？
- 数字来自 Letta 自身发布的 benchmark，缺乏独立复现
- 实验设置（temperature、prompt、tool 配置）的细微差异可能显著影响结果

### 2. A-MEM 的量化改进

**主张 A**:
> A-MEM achieves a 2x improvement on multi-hop reasoning over existing agent memory baselines, with 45.85 temporal F1 on LoCoMo versus MemGPT's 25.52.

**否决**: 0-3

**主张 B**:
> A-MEM reduces token consumption by 85-93% compared to full-context approaches, using only 2,520 tokens per query versus approximately 16,977 for MemGPT.

**否决**: 1-2

**可能原因**:
- A-MEM 的评估指标选择可能有利于其架构
- Token 计数的比较基准（full-context vs MemGPT 的检索方式）不统一
- A-MEM 论文本身较新（2025.02），缺乏充分的第三方复现

### 3. FadeMem 的性能数据

**主张 A**:
> FadeMem's dual-layer architecture achieves 45% storage reduction compared to fixed-window baselines.

**否决**: 0-3

**主张 B**:
> The adaptive memory fusion mechanism is the single most impactful component of FadeMem — removing it causes a 53.7% drop in multi-hop F1 score.

**否决**: 1-2

**可能原因**:
- 实验设置和对比基线的选择可能未覆盖最新方案
- FadeMem 的衰减参数设定是否具有普适性存疑
- 论文较新，独立复现不足

---

## 否决的架构主张

### 4. AgentArch Benchmark 的性能结论

**主张**:
> Even the best LLMs achieve at most 35.3% end-to-end success on complex enterprise workflows under strict Acceptable Score criteria.

**否决**: 0-3

**来源**: github.com/ghas-results/AgentArch

**可能原因**:
- Benchmark 的"Acceptable Score"标准可能过严（要求 correct tools + correct arguments + correct final decision 同时满足）
- Benchmark 的任务设计是否代表"真实企业工作流"存疑
- 模型迭代速度快（2026.07），benchmark 可能已经过时

### 5. OKX 的 Agent Infrastructure 角色主张

**主张**:
> OKX explicitly defines agent memory infrastructure as requiring 'auditable, versioned, rollback-capable middleware for persistent, stateful reasoning'.

**否决**: 0-3

**可能原因**:
- OKX JD 的语言可能被过度解读——实际可能是更常规的 Infra 岗位
- 缺乏多来源交叉验证
- OKX 的组织架构（Agent Infra 是否为独立团队）未确认

---

## 方法论启示

### 为什么这么多主张被否决？

1. **Benchmark 生态不成熟**：Agent Memory 缺乏公认的、广泛使用的标准 benchmark。不同的论文使用不同的评估指标和数据集，直接比较数字危险。

2. **供应商发布的研究**：Letta 发布的 benchmark 同时对自己的产品有利——这不是说数据造假，而是实验设置、基线选择、指标定义等方面存在大量可以影响结果的自由度。

3. **论文复现不足**：A-MEM、FadeMem 等论文较新（2025-2026），缺乏第三方独立复现。学术界的量化主张在未经复现前应被视为"方向性信号"而非"已确认事实"。

4. **Agent 系统的非确定性**：Agent 行为受 prompt、temperature、tool description、环境状态等多种因素影响，任何单一基准数字都需要在多个设置下重复实验才能确认。

### 研究者的教训

- **永远要求独立复现**：一篇论文/一篇博客上的数字，乘以 0（先不相信），然后逐步找到独立复现的证据再调高置信度
- **区分"方向性观察"和"精确数字"**："Letta 可能在某些场景下比 Mem0 表现更好"是一个合理的弱主张；"Letta 比 Mem0 高 5.5%"需要强证据
- **关注架构描述而非性能数字**：MemGPT 的 OS 类比、A-MEM 的写入代理——这些架构概念比具体的 benchmark 数字更重要、更持久
