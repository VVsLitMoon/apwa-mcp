# 通用论文结构与大纲设计 Skill

## 一、技能描述
本Skill在实验完成、所有材料就位后、开始写论文之前，设计一份完整的论文论证骨架和章节大纲。这不是标题列表——是精确到段落级论证逻辑的施工蓝图：每一节要证明什么、用什么证据、与前后节如何衔接、分配多少字数。核心价值在于用20%的时间做结构设计，避免80%的论文返工。

## 二、前置依赖
- 必须完成：通用实验结果深度分析与可视化 Skill（需要results_narrative和figures_and_tables）
- 必须完成：通用结构化文献综述撰写 Skill（需要literature_review_draft和gap_argument）
- 必须完成：通用研究方法与实验方案设计 Skill（需要research_framework和data_plan）
- 必须完成：通用选题生成与多维打磨 Skill（需要confirmed_topic）
- 必须完成：通用论文需求采集与初始化 Skill（需要requirements_baseline）

## 三、输入格式
```json
{
  "requirements_baseline": "必填 - Skill 1的需求基线（word_count, paper_level, citation_style等）",
  "confirmed_topic": "必填 - Skill 3的选题信息",
  "literature_review_draft": "必填 - Skill 5的综述草稿",
  "gap_argument": "必填 - Skill 5的gap_argument",
  "research_framework": "必填 - Skill 6的研究框架",
  "results_narrative": "必填 - Skill 9的完整分析报告",
  "discussion_bridge": "必填 - Skill 9的discussion_bridge",
  "figures_and_tables": "必填 - Skill 9的图表清单",
  "revisability_notes": "必填 - Skill 5的revisability_notes，用于规划文献综述的改写策略",
  "context": "自由文本 - 携带Skill 1-9的完整输出"
}
```

## 四、输出格式
```json
{
  "thesis_blueprint": {
    "title_page": {"working_title": "论文暂定标题", "alternative_titles": ["备选标题"], "title_rationale": "命名策略说明"},
    "abstract_outline": "摘要预写框架（200-300字，标注各部分占比）",
    "overall_structure": "章节列表与概要",
    "argument_flow": "论文整体论证逻辑线（200-300字）——从一个不熟悉该领域的人的视角，描述论文的论证如何逐章推进"
  },
  "chapter_outlines": [
    {
      "chapter_number": 1,
      "chapter_title": "...",
      "estimated_word_count": 0,
      "chapter_purpose": "本章在论文论证中的作用（一句话）",
      "sections": [
        {
          "section_title": "...",
          "estimated_word_count": 0,
          "core_argument": "本节要证明的论点",
          "evidence_to_use": ["使用的证据来源（引用Skill产出或图表编号）"],
          "transitions": {"from_previous": "与前一节的衔接", "to_next": "与后一节的衔接"},
          "key_references": ["本节必须引用的文献"],
          "subsections": ["必要时进一步拆分"]
        }
      ]
    }
  ],
  "material_assignment": {
    "figures_placement": [{"figure_id": "...", "placed_in": "章节号", "paired_paragraph": "配套的论证段落描述"}],
    "tables_placement": [{"table_id": "...", "placed_in": "...", "paired_paragraph": "..."}],
    "lit_review_rewrite_plan": "文献综述的改写策略——针对revisability_notes的每一项给出具体改写方向"
  },
  "quality_guidelines": {
    "word_budget_allocation": {"引言": "10-15%", "文献综述": "20-25%", "方法": "15-20%", "实验": "20-25%", "讨论": "15-20%", "结论": "5-10%"},
    "key_quality_criteria": ["每节必须有明确的core_argument", "每个图表必须有配套的分析段落", "文献综述必须与讨论章节形成前后呼应"],
    "common_mistakes_to_avoid": ["结果与分析章节写成数据堆砌", "讨论章节复述结果而非升华", "引言和结论雷同"]
  },
      "user_outline_confirmed": "必填 - 用户是否已确认大纲设计",
    "output_text": "自由文本 - 论文设计与大纲说明文档，以学术风格撰写，包含所有论证逻辑的叙事说明"
}
```

## 五、系统提示词

你是一位资深学术写作者和论文导师，专长是在动笔前做结构设计。你知道一个事实：论文写不好的根本原因几乎从来不是"写作本身不好"，而是"结构设计没做好"。你的任务就是在一切材料的交汇点上，构建一份完整的论文建筑蓝图。


### ⏱ 预估耗时与检查点
- **预估总耗时**：8-12分钟
- **检查点1**（约4分钟）：整体论证流设计完成 → 审核argument_flow是否逻辑自洽
- **检查点2**（约10分钟）：逐节大纲完成 → ★ 审核每节的core_argument和证据分配，确认文献综述改写策略

⚠ 本Skill是关键确认节点：大纲一旦定稿，论文的整体结构就锁定了。花时间检查每章的论证是否有断裂。

### 任务目标
基于前面所有Skill的产出，设计一份从标题到最后一节参考文献的完整论文大纲。这不是提纲——是论证骨架设计图，精确到每节要论证什么、用什么证据、如何衔接、分配多少篇幅。

### 执行步骤

1. **盘点全部材料**：
   - 汇总所有入参中的信息：需求基线、选题论证、文献综述、研究方法、实验结果、讨论要点
   - 识别材料之间的逻辑关系和潜在张力（如文献综述的某些论述与实验结果不完全吻合——这些张力恰恰是改写文献综述的指导线索）

2. **确定章节架构**（根据paper_level和paper_type）：
   - 标准的实证研究论文结构：
     - 第一章 引言（问题提出、研究意义、研究问题/假设、论文结构）
     - 第二章 文献综述（领域背景→方法演进→研究空白→本研究定位）
     - 第三章 研究方法（研究框架→数据→模型→评估→可解释性方案）
     - 第四章 实验结果与分析（模型性能→假设验证→可解释性发现→稳健性）
     - 第五章 讨论（结果解读→文献对话→实践启示→局限性）
     - 第六章 结论与展望（主要贡献→研究局限→未来方向）
     - 参考文献
     - 附录（可选）
   - 根据实际paper_level和paper_type做调整，不要机械套用

3. **设计论证流（argument_flow）**——这是本Skill的核心产出：
   - 从第一章到最后一章，用200-300字描述论证如何逐层推进
   - 这是论文的"剧情梗概"——确保不是你一个人觉得逻辑通，而是任何一个没看过你实验的人读了都觉得论证自然

4. **逐节填充骨架**（每节必须回答以下问题）：
   - 本节要证明什么？（core_argument——一个明确的陈述句）
   - 用什么证据来证明？（evidence_to_use——具体到引用编号或图表ID）
   - 它与前一节和后一节的关系是什么？（transitions）
   - 它占用多少篇幅？（estimated_word_count——与总字数预算对齐）

5. **图表-段落配对**（material_assignment）：
   - 每个图/表指定它应该出现在哪一节、配合哪段论证
   - 每个图/表都必须有一个"配套论证段落"——不允许论文中出现"图X展示了…"就完了的写法

6. **文献综述改写规划**（lit_review_rewrite_plan）：
   - 对照Skill 5的revisability_notes和Skill 9的实验结果，规划文献综述需要改写的地方
   - 具体化到：哪一节需要改写、改写方向是什么、新的论证重点是什么
   - 这是实现"论文像人反复推敲写出来的"的关键一步

7. **字数预算**：将总字数按比例分配到各章各节，确保不出现某章过于臃肿或单薄

### 约束条件

- **章节结构不能复制已有文献综述的章节结构**：文献综述是材料，大纲设计是建筑——材料的结构不等于建筑的结构
- **每章必须有单一的、不可替代的论证贡献**：如果删除这章论文论证不受影响→这章就不应该存在
- **实验和讨论必须区隔清楚**：实验结果说"是什么"，讨论说"意味着什么"——大纲中两章的core_argument不能有重叠
- **引言必须包含明确的"本文贡献"声明**：不是"本文研究了..."而是"本文的主要贡献是..."
- **字数预算必须严肃**：总预算不能超过requirements_baseline.word_count的110%或低于80%
- 在output_text末尾必须包含"请在确认大纲后回复，我将开始撰写全文"的明确提示


## 六、失败处理策略
- 异常类型：材料之间存在无法调和的矛盾（如文献综述声称某方法最优但实验结果不支持） → 处理方式：在大纲中明确标注这个矛盾，规划讨论章节需要对此做出解释，同时标注文献综述需要改写以弱化绝对化表述或更新证据方向
- 异常类型：字数预算严重不足（即使按最紧缩分配，关键论证章节的字数仍不够） → 处理方式：识别可以精简的边缘内容和可以移到附录的内容，如果仍不足，在output_text中建议用户调整word_count
- 异常类型：缺少某类关键信息（如没有稳健性检验结果） → 处理方式：大纲中为该内容预留位置并标注"待补充"，不因为缺材料而删除应有的章节

## 七、使用示例

### 示例输入（概要）
```json
{
  "requirements_baseline": {"paper_level": "硕士毕业论文", "word_count": "30000", "citation_style": "GB/T 7714"},
  "confirmed_topic": {"topic_title": "基于SHAP特征归因的信用评估模型可解释性增强"},
  "results_narrative": {"rq_answers": [{"research_question": "RQ1...", "answer": "部分建立..."}]},
  "discussion_bridge": {"key_takeaways": ["LightGBM精度优势约10个百分点AUC", "21.7%非典型个案..."], "connection_to_literature": "..."},
  "context": "完整上下文..."
}
```

### 示例输出（节选）
```json
{
  "thesis_blueprint": {
    "title_page": {
      "working_title": "基于SHAP特征归因的信用评估模型可解释性增强研究——以LightGBM为核心的三层解释框架设计与验证",
      "alternative_titles": ["从全局到个案：信用评估模型中SHAP可解释性的分层应用研究"],
      "title_rationale": "主标题体现核心方法（SHAP）和应用领域（信用评估），副标题体现创新点（三层框架）和方法（LightGBM）。遵循中文硕士论文命名惯例：方法+领域+问题。"
    },
    "abstract_outline": "【背景】信用评估模型精度提升伴随可解释性下降（2句）→【问题】现有SHAP应用停留在技术验证层面，缺乏面向业务人员的解释体系（1句）→【方法】本研究构建了全局→特征组→个案的三层可解释性框架，在LightGBM信用模型上验证（2句）→【结果】框架在精度保持（AUC=0.782）的同时显著提升审计可读性；发现21.7%个案为'非典型'边缘情形（2句）→【贡献】为风控行业提供了从模型解释到业务决策的标准化方案（1句）",
    "overall_structure": "共六章：引言→文献综述→研究方法→实验结果与分析→讨论→结论与展望",
    "argument_flow": "论文的论证线是阶梯式的：第一步（引言）提出信用评估面临精度-可解释性两难，现有SHAP研究的工程化应用存在缺口；第二步（文献综述）系统梳理了从评分卡到深度学习的方法演进，证实了可解释性从可选项变为必需项的行业趋势，同时揭示SHAP应用的关键断裂——技术验证充分但业务转化缺失；第三步（方法）设计了兼顾技术精度和业务可读性的三层解释框架，给出具体的实现方案；第四步（实验）用实证数据验证了框架的技术有效性（AUC保持）和业务可用性（审计可读性评分）；第五步（讨论）将结果置入学界和业界的双重语境中解读，特别是有21.7%的非典型个案的发现挑战了'全局解释足够'的默认假设；第六步（结论）收敛于核心贡献和实践启示。整篇论文的逻辑闭环是：现象（精度-可解释性矛盾）→ 缺口（工程化断层）→ 方案（三层框架）→ 验证（实证）→ 反思（非典型个案挑战）→ 贡献（标准化方案）。"
  },
  "chapter_outlines": [
    {
      "chapter_number": 4,
      "chapter_title": "实验结果与分析",
      "estimated_word_count": 6500,
      "chapter_purpose": "以数据回答三个研究问题，用实证证据支撑核心claim",
      "sections": [
        {
          "section_title": "4.1 模型性能评估",
          "estimated_word_count": 1800,
          "core_argument": "LightGBM在信用违约预测上显著优于可解释的基线模型，精度优势约10个百分点AUC，且与XGBoost的性能差异在统计显著性边界上。",
          "evidence_to_use": ["Table 1 模型性能综合对比", "Figure 1 ROC曲线对比", "Figure 2 KS曲线对比", "DeLong检验结果（Bootstrap CI）"],
          "transitions": {"from_previous": "承接第三章的方法设计，本章汇报该方法在真实数据上的执行结果", "to_next": "模型表现确立后，接下来验证RQ1：这些模型的SHAP解释在全局和个案层面的一致性"},
          "key_references": ["Lundberg 2017 (方法来源)", "Chen 2023 (XGBoost信用评估对比)"]
        },
        {
          "section_title": "4.3 可解释性分析结果",
          "estimated_word_count": 2200,
          "core_argument": "三层可解释性框架在技术上可行：全局→特征组→个案的解释信息传递路径成立，但约21.7%的个案为'非典型'——其决策逻辑与全局模式显著偏离，这是三层框架最有价值的发现。",
          "evidence_to_use": ["Figure 3 全局SHAP重要性排序", "Figure 4 个案SHAP瀑布图（典型vs非典型对比）", "Figure 5 全局-个案特征排名一致性散点图", "Table 3 三层解释信息传递完整性评估"],
          "transitions": {"from_previous": "模型性能确认后，本节回答论文的核心创新问题：三层解释框架是否实际可用？", "to_next": "RQ1-3全部回答完毕后，下一章将结果放入更广阔的学术和实践语境中讨论"},
          "key_references": ["Lundberg et al. 2020 (从局部到全局解释)", "Explainable AI in financial services (2023)"]
        }
      ]
    }
  ],
  "material_assignment": {
    "figures_placement": [
      {"figure_id": "FT01", "placed_in": "§4.1", "paired_paragraph": "§4.1第二段——三个模型ROC曲线的视觉对比，配合AUC数值差异的统计显著性讨论"},
      {"figure_id": "FT04", "placed_in": "§4.3", "paired_paragraph": "§4.3第三段——展示典型vs非典型个案的SHAP瀑布图对比，配合'21.7%非典型个案'的核心发现论述"}
    ],
    "lit_review_rewrite_plan": "1. §2.2关于'SHAP计算开销'的论述——根据实验结果（SHAP计算占训练时间<5%），将'SHAP计算开销是部署瓶颈'调整为'在中等规模数据集上SHAP开销可控，部署瓶颈更多在解释结果的组织和业务化而非计算本身'。2. gap_argument中'缺乏业务可用性方案'——实验结果已提供初步方案，综述的缺口论证应从'完全没有方案'调整为'现有方案未经验证/未标准化'。3. 补充2025-2026年最新文献2-4篇，弥补Skill 5的4篇引用缺口。"
  },
  "quality_guidelines": {
    "word_budget_allocation": {"引言": "10% (3000)", "文献综述": "22% (6600)", "方法": "18% (5400)", "实验": "22% (6600)", "讨论": "18% (5400)", "结论": "10% (3000)"},
    "key_quality_criteria": ["实验结果中的每个数据点必须配合一句解读性文字，不允许纯描述", "讨论章节的connection_to_literature节必须至少引用5篇文献（对应该节论述的文献对话）", "结论章节不能重复引言，必须升华为'本研究之后，领域知道了什么之前不知道的'"],
    "common_mistakes_to_avoid": ["结果章节写成'图X展示了...'的图注堆砌", "讨论章节复述结果百分比（应该讨论百分比的含义而非百分比本身）", "引言中'本文结构'段写成章节标题列表（应该描述论证的推进逻辑）"]
  },
  "output_text": "## 论文结构与大纲设计说明\n\n### 一、整体论证架构\n\n本论文围绕一个核心主张展开……（完整大纲文档，约3000-4000字）"
}
```
