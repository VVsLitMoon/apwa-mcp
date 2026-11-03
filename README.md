# APWA · 基于 MCP 的多阶段 Agent 工作流

把一条 14 个阶段的专业任务流水线封装成 **19 个 MCP 工具**，支持依赖拓扑编排、断点续跑、质量门禁循环和交付物打包。

验证场景选用学术写作 —— 因为它同时具备「阶段多、阶段间依赖强、单阶段产出可校验」三个特征，是压测编排能力的合适样本。

- [案例研究：用它跑完一篇信用风险实证论文](docs/case-study.md)
- [架构与状态机说明](docs/architecture.md)

---

## 要解决的问题

把长流程任务整个丢给 LLM，通常坏在四个地方：

| 失败模式 | 具体表现 |
| --- | --- |
| 上下文漂移 | 跑到第 8 步，已经忘了第 2 步定下的参数 |
| 阶段跳步 | 该先做文献综述，直接开始写正文 |
| 中途崩溃 | 进程断了只能从第一步重来 |
| 产出无法验收 | 每步输出是自由文本，下游无法稳定消费 |

这个项目的做法：**把每个阶段固化成带输入输出契约的 Skill，用 MCP server 暴露为工具，调度交给客户端。**

于是「第 N 步的产出是什么形状」变成 schema，「第 N 步依赖谁」变成声明式依赖，「崩了怎么办」变成 checkpoint。

## 架构

```
          Claude Desktop / 任意 MCP 客户端
                      │  stdio · JSON-RPC
                      ▼
┌───────────────────────────────────────────────┐
│  src/server.py   MCP Server                   │
│    ├── skill_registry   14 Skill → 19 tools   │
│    ├── orchestrator     run_pipeline 拓扑编排 │
│    ├── checkpoint       状态机 / 断点续跑     │
│    └── delivery         交付包打包            │
└───────────────────────────────────────────────┘
          │ 读取                        │ 产物
          ▼                             ▼
  skills/Skill-01..14.md        runtime/skill_outputs/*.json
  inputSchema / outputSchema     每阶段产物 + 执行状态
  依赖声明 / system prompt
```

## 19 个工具

**14 个阶段工具**（`skill_01` ~ `skill_14`）：需求采集 → 文献预检索 → 选题 → 精准检索 → 文献综述 → 研究设计 → 代码生成 → 实验执行 → 结果分析 → 论文大纲 → 全文撰写 → 评阅 → 定向修改 → 规范终检。

**5 个编排工具：**

| 工具 | 作用 |
| --- | --- |
| `run_pipeline` | 按依赖拓扑序串联执行多个 Skill，未就绪阶段自动跳过 |
| `checkpoint_decision` | 断点决策：`skip` / `rerun` / `continue` |
| `confirm_skill_01` | 确认需求基线，解锁下游全部 Skill |
| `pipeline_status` | 查看 14 个阶段的执行状态与产物完整性 |
| `generate_delivery` | 汇总论文、代码、图表、引用核验为交付包 |

## 四个设计要点

**1. 依赖声明式，执行拓扑序。**
每个 Skill 在 md 头部声明 `must_deps` / `opt_deps`，注册表据此排序 —— 下游阶段不会在上游产出缺失时被调用。

**2. 双档 inputSchema。**
每个 Skill 同时提供 slim（6 个核心字段）与 full（展开全部参数）两版。先用最小必填跑通，需要细调再展开。

**3. 断点续跑。**
状态落在 `runtime/skill_outputs/*.json`。进程中断后重新连接，`pipeline_status` 能看出走到哪一步，`checkpoint_decision` 决定重跑还是跳过。

**4. 质量门禁循环。**
Skill 12 评阅得分低于阈值时自动触发 Skill 13 定向修改，循环上限由 `MAX_REVIEW_ROUNDS` 控制，避免无限返工。

## 快速开始

```bash
git clone <repo-url>
cd apwa-mcp

python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt

python src/server.py --test      # 自检：解析 Skill、构建注册表
```

自检成功会输出：

```
OK — 14 Skills parsed
[apwa] Loaded 14 skills, 19 tools
```

接入 MCP 客户端（以 Claude Desktop 为例）：把 `mcp.json.example` 里的绝对路径换成你本机路径，写入客户端的 `claude_desktop_config.json`，完全退出客户端后重新打开。

```json
{
  "mcpServers": {
    "apwa": {
      "command": "python",
      "args": ["/ABSOLUTE/PATH/TO/apwa-mcp/src/server.py"]
    }
  }
}
```

> 依赖版本必须锁定：`mcp` 2.x 重写了 `Server` API（移除 `list_tools` / `call_tool` 装饰器），本项目按 1.x 编写。`requirements.txt` 已钉住 `mcp==1.9.0` + `pydantic==2.9.2`。

## 目录结构

```
apwa-mcp/
├── src/
│   ├── server.py           MCP server 入口，注册 19 个工具
│   ├── config.py           路径与常量（相对项目根，可用环境变量覆盖）
│   ├── skill_registry.py   Skill 注册表、拓扑排序、工具列表
│   ├── skill_parser.py     从 md 文件解析 inputSchema / outputSchema / 依赖
│   ├── tool_handlers.py    14 个阶段工具的处理函数
│   ├── orchestrator.py     run_pipeline 编排执行
│   ├── checkpoint.py       状态读写与断点决策
│   └── delivery.py         交付包打包
├── skills/                 14 个 Skill 定义（md，含 schema 与 prompt）
├── docs/
│   ├── architecture.md     架构与状态机细节
│   └── case-study.md       案例研究：一篇信用风险实证论文
├── requirements.txt
└── mcp.json.example
```

## 跑起来是什么样

以下为一次真实运行的输出（不是示意）。

**自检：**

```
$ python src/server.py --test
[apwa] Loading SkillRegistry, SKILL_DIR from config...
[apwa] Loaded 14 skills, 19 tools

    OK — 14 Skills parsed
    OK — 14 Skills registered
    OK — 19 tools generated
    OK — checkpoint system functional
    OK skill_01 ... OK skill_14
    OK confirm_skill_01 / run_pipeline / checkpoint_decision / pipeline_status / generate_delivery
```

**MCP 客户端握手并查询状态：**

```
server : apwa-pipeline 1.0.0
proto  : 2025-03-26
tools  : 19
         skill_01, skill_02, skill_03, skill_04, skill_05, skill_06, ...
         checkpoint_decision, confirm_skill_01, pipeline_status, generate_delivery

> pipeline_status
{
  "skill_01": { "status": "not_started", "skill_id": 1 },
  "skill_02": { "status": "not_started", "skill_id": 2 },
  ...
}
```

**调用 run_pipeline（Skill 03 → 11），输出节选：**

```
# Pipeline Execution Plan: Skill 03 → Skill 11

拓扑执行序: [3, 4, 5, 6, 7, 8, 9, 10, 11]
共 9 个 Skill

### ▶ Skill 03: 通用选题生成与多维打磨 Skill (依赖: 通用领域文献预检索与热点分析 Skill)
### ▶ Skill 04: 通用精准文献检索与深度研读 Skill (依赖: Skill 02, Skill 03)
### ▶ Skill 05: 通用结构化文献综述撰写 Skill (依赖: Skill 03, Skill 04)
...
### ▶ Skill 11: 通用论文全章节撰写与整合 Skill (依赖: ..., Skill 10)

## 立即执行

请先调用 `skill_03` 开始执行。
```

每一行都把该阶段的 `must_deps` 展开到括号里 —— 依赖图不是画在文档里给人看的，是执行时真的按它排序的。

上面是全新建库时的样子（全部 `▶`）。在跑过一轮的项目里，已完成的阶段会标成 `⏭ … 自动跳过`，异常中断的标 `🚫 … 管道暂停` —— 这就是断点续跑在输出侧的表现。案例研究里第 3 轮实验能直接复用前两轮的数据阶段，靠的就是它。

## 局限

- 只走 stdio 传输，无并发、无会话隔离，一个进程同时服务一个客户端
- 状态存本地 JSON，不支持多机部署
- Skill 质量取决于 prompt 与 schema 的设计，目前没有自动化评测集
- Skill 08 的危险模式扫描是正则黑名单，只能拦截明显问题，不等于沙箱

---

## 参考

- [Model Context Protocol 规范](https://modelcontextprotocol.io/)
- Python SDK：`mcp==1.9.0`
