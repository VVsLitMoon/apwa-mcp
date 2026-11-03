# 架构与状态机

## 为什么是 MCP + stdio

这套流水线最初写在单个脚本里，跑起来的问题不是"算不出来"，而是**阶段之间靠人脑记状态**：第 3 步定了什么参数、第 5 步的综述用了哪几篇文献、第 8 步实验挂了要退回到哪一步。

换成 MCP server 之后：

- 阶段边界变成**工具边界** —— 调用哪个 Skill、传什么参数，都被 schema 约束住
- 状态从"人脑记"变成**磁盘上的 state 文件**
- 客户端（Claude Desktop 等）负责推理和调度，server 只负责协调和持久化

选 stdio 而不是 HTTP，是因为它零网络配置、随客户端生命周期启停、天然单客户端。代价是没有并发和会话隔离（见 README 局限）。

## 请求流

```
客户端                          server.py
  │                                │
  │ ── initialize ────────────────▶│  构建 SkillRegistry
  │ ◀─ serverInfo / capabilities ──│
  │                                │
  │ ── tools/list ────────────────▶│  返回 19 个工具
  │ ◀──────────────────────────────│
  │                                │
  │ ── tools/call skill_06 ───────▶│  校验依赖 → 读取上游产物
  │                                │  组装 prompt 返回
  │ ◀─ prompt + schema ────────────│
  │                                │
  │  （客户端执行 LLM 推理）         │
  │                                │
  │ ── tools/call skill_06 ───────▶│  带 _store 参数写回产物
  │ ◀─ 写入确认 ───────────────────│
```

关键点：**server 不调用模型**。它把每个阶段需要的上下文、schema、prompt 组装好返回，推理在客户端完成，结果通过 `_store` 参数写回。这条边界让 server 保持无状态推理、可测试、可替换客户端。

## Skill 文件格式

每个 `skills/Skill-NN-*.md` 由三部分组成：

```markdown
## 元信息
skill_id: 06
must_deps: [3, 4, 5]
opt_deps: [1]
output_schema: [research_framework, data_plan, model_plan, ...]

## inputSchema（slim / full 两档）
slim: 6 个核心字段
full: 展开全部可选参数

## system prompt
该阶段的角色、约束、产出要求
```

`skill_parser.py` 解析这三段，`skill_registry.py` 据此构建工具列表和依赖图。

## 状态机

每个 Skill 的状态存在 `runtime/skill_outputs/skill_NN_state.json`：

```
NOT_STARTED ──调用──▶ IN_PROGRESS ──写回产物──▶ COMPLETED
                          │
                          └──异常──▶ BLOCKED ──修复 + continue──▶ IN_PROGRESS
```

| 状态 | 含义 | `run_pipeline` 的处理 |
| --- | --- | --- |
| `NOT_STARTED` | 从未执行 | 排入执行序列 |
| `IN_PROGRESS` | 上次中断，产物不完整 | 提示确认 `continue` 或 `rerun` |
| `COMPLETED` | 产物完整 | 自动跳过 |
| `BLOCKED` | 异常中断，需修复 | 管道暂停，等 `continue` |

产物本身存在 `skill_NN_output.json`，与 state 分开 —— 这样重跑不会覆盖已验证的产物，除非显式 `rerun`。

## run_pipeline 的取舍

`run_pipeline` **不直接执行**整个流水线，而是返回一份**执行计划**：

```
# Pipeline Execution Plan: Skill 03 → Skill 11
拓扑执行序: [3, 4, 5, 6, 7, 8, 9, 10, 11]

### ⏭ Skill 03 — 已完成，自动跳过
### ▶ Skill 04: 精准文献检索与深度研读 (依赖: Skill 03)
### ▶ Skill 05: ...
```

原因：MCP stdio 模型下 server 无法调用 LLM，推理在客户端。所以"编排"实际拆成两半 —— server 算出顺序、校验依赖、过滤已完成阶段；客户端照着计划逐个调用。

这不是妥协，是个正确的分离：**编排逻辑和推理能力解耦**，换任何支持 MCP 的客户端都能用。

## 质量门禁循环

Skill 12（评阅）产出五维评分。若低于阈值：

```
Skill 12 评阅 ──低于阈值──▶ Skill 13 定向修改 ──▶ 回到 Skill 12 重新评阅
                    │                                  │
                    └──── 达到阈值 ──▶ Skill 14 终检 ◀──┘
```

循环上限 `MAX_REVIEW_ROUNDS = 3`，超过则带着当前最好版本进入终检，并在交付包里标记未达标项。

## 交付包

`generate_delivery` 汇总：

```
runtime/delivery/
├── thesis_final.md            正文
├── skill_execution_report.md  每个阶段的执行记录
├── ai_usage_record.md         各阶段 AI 参与情况
├── citation_verification.md   引用核验结果
├── experiment_code/           实验代码
├── figures_and_tables/        图表源文件
└── skill_outputs_archive/     各阶段原始产物
```

`ai_usage_record.md` 是刻意加的：哪些内容是 AI 生成的、哪些是人工判断的，留一份可追溯的记录。做研究这件事上，这个透明度比产出好看更重要。
