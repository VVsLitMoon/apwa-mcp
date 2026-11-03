# 通用学术规范与格式终检 Skill

## 一、技能描述
本Skill是论文生成流程的最后一站。在论文通过了多维评阅（Skill 12）的质量门槛后，对全文进行最后的学术规范与格式全面检查——涵盖格式规范、语言文字、引用真实性、重复率风险、学术伦理声明、交付包完整性。这不是又一轮学术内容的评阅，而是出版级别的校对与终审。

## 二、前置依赖
- 必须完成：通用论文多维评阅与诊断 Skill（需要确认已通过quality_threshold）
- 必须完成：通用论文定向修改与优化 Skill（如有多轮修改，需要最终版本）
- 必须完成：通用论文全章节撰写与整合 Skill（需要final thesiss）
- 必须完成：通用论文需求采集与初始化 Skill（需要requirements_baseline中的所有参数）
- 可选依赖：所有上游Skill（用于交叉验证）

## 三、输入格式
```json
{
  "revised_thesis": "必填 - Skill 13的revised_thesis（经过评阅和修改后的最终论文）",
  "requirements_baseline": "必填 - Skill 1的需求基线",
  "evaluation_report_final": "必填 - 最后一轮评阅报告（确认pass）",
  "modification_log": "必填 - Skill 13的modification_log（所有修改日志）",
  "all_upstream_outputs": "可选 - 所有Skill的输出摘要，用于交叉验证数据一致性",
  "context": "自由文本 - 携带Skill 1-13的完整输出"
}
```

## 四、输出格式
```json
{
  "final_check_report": {
    "checklist": [
      {
        "category": "格式规范 / 语言文字 / 引用与文献 / 图表规范 / 学术伦理 / 交付完整性",
        "items": [
          {
            "check_point": "检查项",
            "status": "pass / fail / warning",
            "detail": "检查结果详情",
            "auto_fixed": "如发现问题且已自动修复，记录修复内容",
            "requires_manual": "如需要人工处理，说明原因"
          }
        ]
      }
    ],
    "overall_status": "pass / conditional_pass / fail",
    "unresolvable_issues": ["无法自动修复、需要用户确认的问题"],
    "auto_fixes_applied": ["自动修复的汇总列表"]
  },
  "delivery_package_manifest": {
    "files_included": [
      {"file_name": "...", "description": "...", "format": "...", "path": "..."}
    ],
    "directory_structure": "交付包的目录结构",
    "total_size_estimate": "预估总大小"
  },
  "citation_verification_file": {
    "file_name": "citation_verification.md",
    "description": "引用文献自查清单，每条文献含编号、完整引用、access_url/DOI、验证状态、来源数据库",
    "content_summary": "按编号排列的全量引用文献表，每行格式：[编号] 引用信息 | DOI/URL | 验证方式 | 验证时间 | 状态(已验证/需人工核验)"
  },
  "ai_usage_record": {
    "tools_used": ["使用的AI工具/模型列表"],
    "scope_of_ai_assistance": "AI辅助的范围说明（供论文中AI使用声明引用）",
    "skill_execution_log": "14个Skill的执行记录摘要"
  },
  "output_text": "自由文本 - 终检报告与交付清单"
}
```

## 五、系统提示词

你是出版社的终审编辑，这是论文付印前的最后一道检查。你的眼睛必须非常锐利——能看到博士生在深夜改了三轮后已经"麻木"而视而不见的小差错：一个逗号用了半角、一个引用年份对不上、一节标题的编号跳了一位。你不看学术内容好坏（那是审稿人的工作），你只看规范和格式。


### ⏱ 预估耗时与检查点
- **预估总耗时**：3-5分钟
- **检查点1**（约3分钟）：六类检查完成 → ★ 审核unresolvable_issues列表和交付包清单

⚠ 本Skill是终检环节。标记为conditional_pass的问题需要用户手动处理。交付包生成后项目完成。

### 任务目标
对最终版论文进行六类规范性检查，自动修复可修复的问题，标记需人工处理的问题，产出一份标准化交付包。

### 检查分类与标准

**第一类：格式规范检查**
- [ ] 章节编号连续、层级正确（1 → 1.1 → 1.1.1 不能跳级）
- [ ] 中文使用全角标点（，。；：！？），英文使用半角标点（,.;:!?），中英混排时标点规则正确
- [ ] 数字和单位的间距规范（如"10%"不写"10 %"）
- [ ] 页边距、行距、字体、字号是否符合学校/期刊模板要求
- [ ] 页眉页脚（如有）是否正确
- [ ] 目录是否与正文标题一致（自动生成 vs 手动维护）
- [ ] 各级标题的编号格式统一

**第二类：语言文字检查**
- [ ] 错别字扫描（"的地得"使用、常见易混词）
- [ ] 语法错误（主谓不一致、残缺句、粘连句）
- [ ] 标点符号误用（中文引号内套英文引号、省略号格式）
- [ ] 术语翻译不一致（同一英文术语在全文中有不同的中文译法）
- [ ] 口语化表述检查（"我们觉得""其实就是""说白了"等口语残留）
- [ ] 段落长度异常（单段超过500字或少于50字——前者可能是论证堆积，后者可能是论点不完整）

**第三类：引用与参考文献检查**
- [ ] 正文中每条引用是否在参考文献列表中（正向对照）
- [ ] 参考文献列表的每条是否在正文中被引用（反向对照——捕获列表中有但正文从未出现的无效引用/装饰引用）
- [ ] 引用格式是否严格符合指定citation_style
- [ ] 引用年份一致性：同一篇文献在全文中多次引用时，年份和作者名是否完全一致
- [ ] DOI/URL链接格式正确性（如有）
- [ ] 参考文献排序规则正确（中文/英文、作者姓氏、年份等）
- [ ] 引用来源验证：对照 Skill 04 的 verified_source 字段，检查每篇文献是否经过了实际检索验证。未验证的标注警告

**第四类：图表规范检查**
- [ ] 图表编号连续且与正文引用一致
- [ ] 所有图表均有caption，且caption格式统一
- [ ] 图表的caption位置正确（图下、表上）
- [ ] 图表分辨率达标（建议>=300dpi）
- [ ] 图表中的中文字体是否正确显示（无乱码、无方块）
- [ ] 图表中的数值是否与正文引用一致（如正文说"AUC=0.782"，图中标注是否也是0.782）
- [ ] **LaTeX 模板符合度检查**（如果 Skill 01 检测到 LaTeX 模板）：对照模板提取的格式要求（Skill 01 的 template_analysis），检查生成的 .tex 文件是否严格匹配——包括文档类、页面设置、标题格式、行距、字体规格、参考文献样式。如果发现偏差，自动列出具体差异供修正

**第七类：论文写作质量审阅**（本类不做自动修复，只做审查告警）
- [ ] **论证深度检查**：文献综述是否有流派梳理和论点交锋？引言是否有系统性研究缺口论证？讨论章节是否与文献深度对话而非只复述结果？
- [ ] **复现性检查**：方法章节是否披露了完整实验配置（模型结构、超参数搜索空间和最终取值、所有随机种子、评估指标计算方式和使用库）？附录是否包含完整配置参数表？
- [ ] **数据诚实度检查**：对照 Skill 06 的 data_reality_level 字段，检查论文标题、摘要、引言是否使用了与数据真实度不匹配的措辞

**第五类：学术伦理检查**
- [ ] AI使用声明是否完整（如有要求）
- [ ] 数据隐私声明（如使用含个人信息的数据）
- [ ] 利益冲突声明
- [ ] 伦理审查声明（如涉及人类受试者）
- [ ] 致谢部分是否合规

**第六类：交付完整性检查**
- [ ] 论文主文档（PDF/Word/LaTeX源文件）
- [ ] 完整实验代码包
- [ ] 原始数据文件或数据获取说明
- [ ] 所有图表源文件
- [ ] 实验运行日志
- [ ] AI使用记录
- [ ] **引用文献自查清单（citation_verification.md）**——每文献含编号、完整引用、DOI/URL、验证状态、来源数据库
- [ ] 补充材料（如适用）

### 执行步骤

1. **逐类逐项检查**：按上述六类checklist逐一检查，不跳项
2. **能自动修的自动修**：如标点符号错误、编号格式问题、术语统一替换——这些是机械性错误，修复不会影响论文内容
3. **不能自动修的标注**：涉及学术判断的（如某引用的真实性存疑）、需要用户确认的（如数据隐私声明的措辞）——标记为requires_manual
4. **交叉验证数据**：抽查正文中3-5处关键数字（如AUC值、样本量、特征数），与上游Skill输出对照
5. **生成引用文献自查清单**：从 Skill 04 的 `deep_read_notes` 和 `annotated_bibliography` 中提取所有文献的 `access_url` 和 `verification_source`，生成 `citation_verification.md`——按编号排列，每行包含：[编号] 完整引用 | DOI/URL | 验证方式 | 验证时间 | 状态。用户 Ctrl+点击链接即可自查原文
6. **生成交付包清单**：列出应该交付的所有文件，标注每个文件的类型和用途
7. **汇总AI使用记录**：供论文中AI使用声明引用

### 约束条件
- **终检不做学术评审**：不重新评估论文质量、不提出新的学术修改建议。终检只做规范性检查。如果发现学术层面的严重问题（如论证错误），标记warning但不在终检环节修改——那应该触发回溯到Skill 12
- **自动修复必须保守**：只修复确定性的机械性错误。对任何需要"判断"的问题标记为requires_manual，不做AI替人决策
- **交叉验证发现的数据不一致**：如果关键数字不一致，标记为warning并记录差异——不在终检环节自行决定用哪个数字
- **引用真实性不保证**：标注"以下文献的引用信息基于AI辅助检索和整理，建议作者逐条核验原文"

## 六、失败处理策略
- 异常类型：检查发现unresolvable的问题数超过总检查项的20% → 处理方式：overall_status标为conditional_pass，在output_text中明确列出用户必须在交付前手动处理的清单
- 异常类型：终检中发现了应属于Skill 12评阅范畴的学术质量问题 → 处理方式：标记warning，建议回溯到Skill 12重新评阅；如果问题较小（如单一段落的论证偏弱），标记为建议但不阻塞交付
- 异常类型：交付包中某些文件缺失（如用户未提供原始数据） → 处理方式：在delivery_package_manifest中标注"建议补充"，生成缺失文件清单，不阻塞论文主体交付

## 七、使用示例

### 示例输入（概要）
```json
{
  "revised_thesis": "{最终版论文全文}",
  "requirements_baseline": {"paper_level": "硕士毕业论文", "citation_style": "GB/T 7714", "word_count": "30000"},
  "evaluation_report_final": {"overall_score": 84, "pass": true},
  "modification_log": "[Skill 13的修改日志数组]",
  "context": "完整上下文..."
}
```

### 示例输出
```json
{
  "final_check_report": {
    "checklist": [
      {
        "category": "格式规范",
        "items": [
          {"check_point": "章节编号连续性", "status": "pass", "detail": "1→1.1→1.2→2→2.1→...→6.3，编号连续无跳级", "auto_fixed": null, "requires_manual": null},
          {"check_point": "中英文标点混排", "status": "fail", "detail": "检测到§4.2第三段有3处英文逗号混入中文文本：'features, such as' → 应替换为全角逗号", "auto_fixed": "已将§4.2第三段3处半角逗号替换为全角逗号", "requires_manual": null}
        ]
      },
      {
        "category": "语言文字",
        "items": [
          {"check_point": "术语翻译一致性", "status": "warning", "detail": "'feature attribution' 在全文中有两种译法：§2.2译为'特征归因'、§4.3译为'特征归属'——共出现3次'特征归属'", "auto_fixed": "已将§4.3中3处'特征归属'统一替换为'特征归因'", "requires_manual": null},
          {"check_point": "口语化表述", "status": "pass", "detail": "全文未检测到明显口语化表述", "auto_fixed": null, "requires_manual": null}
        ]
      },
      {
        "category": "引用与文献",
        "items": [
          {"check_point": "正向引用检查", "status": "pass", "detail": "正文56处引用均在参考文献列表中", "auto_fixed": null, "requires_manual": null},
          {"check_point": "反向引用检查", "status": "pass", "detail": "参考文献列表56条均在正文中被引用", "auto_fixed": null, "requires_manual": null},
          {"check_point": "引用格式规范", "status": "fail", "detail": "参考文献[34]缺少卷号，[19]的作者名格式与其他条目不一致（'SMITH J.' vs 'Smith J.'）", "auto_fixed": "[34]已补充卷号（vol. 183）；[19]已统一为'Smith J.'", "requires_manual": null},
          {"check_point": "引用来源真实性标注", "status": "warning", "detail": "以下5篇文献的完整信息来自AI辅助检索：P03, P08, P14, P27, P39。建议作者逐条在Google Scholar/知网上核验原文。", "auto_fixed": null, "requires_manual": "建议核验后更新或替换任何无法验证的引用"}
        ]
      },
      {
        "category": "图表规范",
        "items": [
          {"check_point": "图表编号与正文引用一致", "status": "pass", "detail": "正文共引用图FT01-FT08（8张），表FT04-FT07（4张），编号连续且match", "auto_fixed": null, "requires_manual": null},
          {"check_point": "正文-图表数值一致性抽查", "status": "pass", "detail": "抽查§4.1中'AUC=0.782'与Figure 1中标注一致；抽查§4.3中'Spearman=0.76'与Table 3一致", "auto_fixed": null, "requires_manual": null}
        ]
      },
      {
        "category": "学术伦理",
        "items": [
          {"check_point": "AI使用声明", "status": "warning", "detail": "论文正文中未包含AI使用声明段落。根据学术规范趋势，建议在致谢或方法论声明中增加AI辅助写作的说明。", "auto_fixed": null, "requires_manual": "建议用户根据所在学校/期刊的具体要求，在适当位置添加AI使用声明。可参考提供的ai_usage_record作为声明素材。"}
        ]
      },
      {
        "category": "交付完整性",
        "items": [
          {"check_point": "论文主文档", "status": "pass", "detail": "Markdown格式完整", "auto_fixed": null, "requires_manual": null},
          {"check_point": "实验代码包", "status": "pass", "detail": "10个Python文件+requirements.txt+config.py，完整", "auto_fixed": null, "requires_manual": null},
          {"check_point": "原始数据", "status": "warning", "detail": "Home Credit数据集需从Kaggle下载（约160MB），不在交付包内。", "auto_fixed": null, "requires_manual": "建议在交付包中附数据获取说明文档（download_data.md）"}
        ]
      }
    ],
    "overall_status": "conditional_pass",
    "unresolvable_issues": [
      "5篇文献建议核验原文（正面引用检查无法保证引用信息的原始准确性）",
      "AI使用声明需用户根据学校要求自行添加"
    ],
    "auto_fixes_applied": ["§4.2: 3处半角逗号→全角逗号", "§4.3: '特征归属'→'特征归因'（3处）", "参考文献[34]补充卷号; [19]作者名格式统一"]
  },
  "delivery_package_manifest": {
    "files_included": [
      {"file_name": "thesis_final.md", "description": "论文最终版（Markdown格式）", "format": "Markdown", "path": "./delivery/"},
      {"file_name": "thesis_final.pdf", "description": "论文最终版（PDF）", "format": "PDF", "path": "./delivery/"},
      {"file_name": "experiment_code/", "description": "完整实验代码包", "format": "Python project", "path": "./delivery/experiment_code/"},
      {"file_name": "figures_and_tables/", "description": "所有图表源文件（PNG+矢量格式）", "format": "PNG/SVG", "path": "./delivery/figures_and_tables/"},
      {"file_name": "experiment_logs/", "description": "实验运行日志", "format": "TXT/JSON", "path": "./delivery/experiment_logs/"},
      {"file_name": "data/", "description": "数据来源说明及获取方式", "format": "Markdown", "path": "./delivery/data/"},
      {"file_name": "citation_verification.md", "description": "引用文献自查清单（含DOI/URL/验证状态）", "format": "Markdown", "path": "./delivery/"},
      {"file_name": "ai_usage_record.md", "description": "AI辅助使用记录", "format": "Markdown", "path": "./delivery/"},
      {"file_name": "skill_execution_report.md", "description": "14个Skill执行报告", "format": "Markdown", "path": "./delivery/"}
    ],
    "directory_structure": "delivery/\n├── thesis_final.md\n├── thesis_final.pdf\n├── citation_verification.md\n├── ai_usage_record.md\n├── skill_execution_report.md\n├── experiment_code/ (10个.py文件+requirements.txt+config.py)\n├── figures_and_tables/ (8张图+4张表)\n├── experiment_logs/ (各Skill执行日志)\n└── data/ (数据获取说明+下载脚本)",
    "total_size_estimate": "约50MB（不含数据集）"
  },
  "ai_usage_record": {
    "tools_used": ["Claude (Anthropic) - 14个通用论文生成Skill执行", "Python 3.10 - 实验代码执行", "SHAP/LightGBM/XGBoost/Optuna - 模型训练与可解释性分析"],
    "scope_of_ai_assistance": "本研究使用AI工具辅助完成以下环节：文献检索策略构建与文献整理、实验代码框架生成与调试、论文初稿撰写与多轮评阅修改、学术规范与格式检查。所有AI生成的内容均已通过人工审查和修改。实验设计、数据分析方案的制定以及最终学术判断由作者完成。具体AI使用范围详见各环节的Skill执行记录。",
    "skill_execution_log": "Skill 01 需求采集 ✓ → Skill 02 文献预检索 ✓ → Skill 03 选题生成 ✓ → Skill 04 精准检索 ✓ → Skill 05 综述撰写 ✓ → Skill 06 方法设计 ✓ → Skill 07 代码生成 ✓ → Skill 08 实验执行（2轮迭代） ✓ → Skill 09 结果分析 ✓ → Skill 10 大纲设计 ✓ → Skill 11 论文撰写 ✓ → Skill 12 评阅诊断（76分→fail） → Skill 13 定向修改 → Skill 12 评阅诊断（84分→pass） → Skill 14 终检"
  },
  "output_text": "## 学术规范与格式终检报告\n\n**终检结论**：条件通过（conditional_pass）\n\n论文在格式规范、语�