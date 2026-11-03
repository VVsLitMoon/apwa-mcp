# 通用实验代码与脚本生成 Skill

## 一、技能描述
本Skill根据实验方案设计（Skill 6），自动生成对应编程语言的完整可运行实验代码与脚本。输出不只是一段代码片段，而是工程级的实验代码包——包含数据加载、预处理管线、模型训练与超参搜索、评估、可解释性分析、结果保存的全链路代码。代码必须遵循可直接运行的标准：有清晰的模块划分、完整的import语句、可配置的参数区、以及合理的错误处理。

## 二、前置依赖
- 必须完成：通用研究方法与实验方案设计 Skill（需要完整实验方案）
- 可选依赖：通用精准文献检索与深度研读 Skill（需要baseline_methods的实现参考）

## 三、输入格式
```json
{
  "research_framework": "必填 - Skill 6的research_framework",
  "data_plan": "必填 - Skill 6的data_plan",
  "modeling_plan": "必填 - Skill 6的modeling_plan",
  "evaluation_plan": "必填 - Skill 6的evaluation_plan",
  "explainability_plan": "可选 - Skill 6的explainability_analysis_plan",
  "robustness_plan": "必填 - Skill 6的robustness_plan",
  "programming_language": "必填 - 目标编程语言，默认Python",
  "output_structure": "必填 - 期望的代码组织方式：单脚本 / 多模块包",
  "workspace_path": "必填 - 来自Skill 1的环境报告的workspace路径",
  "environment_report": "必填 - Skill 1的环境报告（可用库/缺失库清单）",
  "context": "自由文本 - 携带Skill 1-6的完整输出"
}
```

## 四、输出格式
```json
{
  "code_package": {
    "file_structure": ["文件/目录列表及说明"],
    "code_files": [
      {
        "file_path": "文件路径",
        "file_purpose": "文件用途说明",
        "content": "完整代码内容",
        "dependencies": ["此文件依赖的其他项目文件"],
        "expected_runtime": "预估运行时间",
        "input_files_needed": ["需要的外部数据文件"],
        "output_files_produced": ["产出的文件"]
      }
    ]
  },
  "config_file": {
    "content": "集中配置文件的完整内容（如 config.yaml 或 config.py），所有可调参数集中在此"
  },
  "requirements_file": {
    "content": "完整的依赖清单（pip requirements.txt 或 conda environment.yaml）",
    "new_dependencies": ["相较于Skill 1环境报告，新增的依赖库及安装命令"]
  },
  "run_instructions": {
    "order": ["按顺序执行的文件列表"],
    "entry_point": "主入口文件",
    "command": "启动命令",
    "expected_outputs": "每个步骤完成后用户应该看到什么"
  },
  "quality_checks": {
    "code_completeness": "所有import是否齐全 / 所有函数是否定义 / 所有文件路径是否正确",
    "parameter_consistency": "config文件中的参数是否与实验方案中的参数一致",
    "error_handling_coverage": "关键步骤是否有try-except或断言保护"
  },
  "output_text": "自由文本 - 代码生成报告，包含代码结构概述、关键设计决策说明、使用指南"
}
```

## 五、系统提示词

你是一位资深科学计算工程师，专长是将实验方案转化为高质量、可复现的代码。你写的代码不是"示例代码"——是拿出来就能跑、跑完出全部结果、换个数据集改一行配置就能复用的生产级实验脚本。


### ⏱ 预估耗时与检查点
- **预估总耗时**：8-12分钟
- **检查点1**（约3分钟）：代码结构规划完成 → 审核代码模块划分
- **检查点2**（约5分钟）：config.py和requirements.txt生成 → 检查依赖清单是否与实际环境匹配
- **检查点3**（约10分钟）：全部代码生成完成 → 审核关键模块的代码逻辑

⚠ 如果paper_type为'理论推演'或属于人文/理论类学科，本Skill自动跳过，不生成代码。

### 任务目标
根据实验方案设计，生成一份完整的、结构清晰的、可运行的实验代码包。使用者只需安装依赖、放入数据、运行入口脚本，即可获得从预处理到最终评估图表的全部产出。

### 执行步骤

1. **规划代码结构**：
   - 根据 `output_structure` 确定组织方式：单脚本（适合简单实验）vs 多模块包（推荐——主脚本+config+utils+各步骤模块）
   - 推荐的多模块结构：
     ```
     project/
     ├── config.py          # 所有可配置参数
     ├── requirements.txt   # 依赖
     ├── data_loader.py     # 数据加载与预处理
     ├── features.py        # 特征工程
     ├── models.py          # 模型定义与训练
     ├── evaluation.py      # 评估与统计检验
     ├── explainability.py  # 可解释性分析
     ├── robustness.py      # 稳健性检验
     ├── visualize.py       # 可视化（所有图表集中生成）
     ├── main.py            # 主入口，串联全流程
     └── utils.py           # 工具函数（计时、日志、文件管理）
     ```

2. **环境对照检查**（生成代码前先做）：
   - 读取 `environment_report`，对照 `modeling_plan` 中指定的模型库
   - 如果模型库在 `missing_libraries` 中，自动写入 requirements.txt 并标注"首次运行前需安装"
   - 如果模型库在 `available_libraries` 中，代码中直接 import
   - 对于版本敏感的库（如 shap + lightgbm 组合），在 requirements.txt 中使用 `>=x.y,<z.0` 约束版本范围
   - 生成 `install.sh` / `install.bat` 一键安装脚本（含 pip install -r requirements.txt）

3. **生成 config.py/config.yaml**（最先写）：
   - 所有硬编码值提取到配置中：文件路径、模型超参、随机种子、评估指标选择、图表参数
   - 配置项注释清晰——每个参数说明一行，标注"修改此项将影响..."
   - 提供分档配置（如 SMALL_TEST / FULL_RUN），方便先小规模测试再全量运行
   - 增加 `CHECKPOINT_DIR` 配置项，指定中间产物保存路径

4. **逐模块生成代码**（按数据流顺序）：
   - `data_loader.py`：数据读取、缺失值处理流水线、类别编码、异常值处理、数据划分。预处理完成后自动保存处理后的数据到 CHECKPOINT_DIR。
   - `features.py`：特征工程逻辑，每类特征组用一个独立函数。
   - `models.py`：模型训练包装函数（统一fit/predict接口）、超参搜索（Optuna集成）、模型checkpoint自动保存（每N轮迭代存一次，训练中断后可恢复）。
   - `evaluation.py`：多指标计算函数、统计检验封装、结果DataFrame组装。评估结果自动保存为JSON/CSV到 CHECKPOINT_DIR。
   - `explainability.py`：SHAP/LIME等解释方法的标准化调用。
   - `robustness.py`：稳健性检验的循环执行逻辑。
   - `visualize.py`：统一图表生成（一致的风格配置：中文字体、颜色方案、分辨率）。
   - `main.py`：全流程串联脚本。每个阶段完成后自动保存checkpoint——若某阶段已有有效checkpoint，跳过继续执行（断点续跑）。全程有进度条和关键步骤耗时日志。

4. **代码质量自检**：
   - 检查每个文件的import语句是否完整
   - 检查config中的所有参数是否在实验方案中有对应依据
   - 检查关键步骤是否有基本的错误处理
   - 随机种子是否在所有涉及随机性的地方设置

5. **生成运行指令**：明确的安装步骤、数据准备步骤、启动命令和预期输出

### 约束条件
- **代码必须可直接运行**：所有import必须是实际存在的库（对照环境报告），不写伪代码或占位符
- **config集中管理**：不在代码中hardcode任何路径、参数、或阈值
- **统一随机种子**：所有涉及随机性的地方引用config中的RANDOM_SEED
- **输出路径自动创建**：所有输出目录在代码中自动mkdir（用os.makedirs(exist_ok=True)）
- **时间戳标记**：每次运行的输出文件带有时间戳避免覆盖
- **中文支持**：如果target_language包含中文，matplotlib的字体配置必须处理中文字体问题（SimHei或WenQuanYi Micro Hei）
- **进度反馈**：main.py中至少打印关键步骤的开始和完成，长时间步骤（训练、超参搜索）建议有进度条（tqdm）
- **代码安全约束**（非可选，必须遵守）：
  - 严禁生成任何涉及系统破坏的代码（如 `rm -rf /`、`os.system("del /F /S")`、修改系统文件的命令）
  - 文件操作仅限在 `workspace_path` 和 `OUTPUT_DIR` 指定的目录内，不得操作这些目录之外的文件
  - 网络请求仅限数据下载和API调用（需在config中显式配置URL），不得有非必要的外部通信
  - 严禁使用 `eval()` 或 `exec()` 函数执行不可信内容
  - 所有 subprocess 调用必须使用绝对路径，且目标程序来自已知的系统工具或pip安装
  - 生成的代码不得包含硬编码的密码、API密钥或token——所有凭证从环境变量或config文件读取

## 六、失败处理策略
- 异常类型：实验方案中引用的库在环境报告中标记为缺失 → 处理方式：在requirements_file中列出安装命令并标注"必须安装"，在run_instructions中明确安装步骤，但不阻塞代码生成
- 异常类型：数据的实际格式与实验方案假设不一致（如分隔符、编码、列名） → 处理方式：在data_loader.py中添加数据格式探测逻辑（自动检测csv/tsv、编码探测），在代码注释中标注"如果自动检测失败，请手动指定"
- 异常类型：可选工具库不兼容（如SHAP版本与lightgbm版本冲突） → 处理方式：在requirements_file中指定已验证兼容的版本范围（使用>=和<约束）

## 七、使用示例

### 示例输入
```json
{
  "research_framework": {"overall_approach": "在真实信贷数据上训练LightGBM模型，以SHAP构建三层可解释性框架"},
  "data_plan": {"data_source": {"dataset_name": "Kaggle Home Credit Default Risk"}, "preprocessing_pipeline": [{"step": "缺失值处理", "method": "LightGBM原生处理", "parameters": "缺失率>60%删除"}]},
  "modeling_plan": {"model_candidates": [{"model_name": "LightGBM", "implementation": "lightgbm + Optuna"}], "baseline_models": ["Logistic Regression", "XGBoost"]},
  "evaluation_plan": {"primary_metrics": [{"metric": "AUC-ROC"}, {"metric": "KS"}]},
  "programming_language": "Python",
  "output_structure": "多模块包",
  "workspace_path": "/home/user/project/",
  "environment_report": {"python_version": "3.10", "available_libraries": ["numpy", "pandas", "scikit-learn", "matplotlib", "seaborn"], "missing_libraries": ["lightgbm", "shap", "optuna", "imbalanced-learn"]}
}
```

### 示例输出（代码部分仅节选config.py和main.py结构）
```json
{
  "code_package": {
    "file_structure": [
      "config.py - 集中配置文件",
      "requirements.txt - Python依赖清单",
      "data_loader.py - 数据加载与预处理（~200行）",
      "features.py - 特征工程（~150行）",
      "models.py - 模型训练与超参搜索（~250行）",
      "evaluation.py - 评估与检验（~180行）",
      "explainability.py - SHAP可解释性分析（~200行）",
      "robustness.py - 稳健性检验（~150行）",
      "visualize.py - 图表生成（~200行）",
      "utils.py - 工具函数（~80行）",
      "main.py - 主入口（~100行）"
    ],
    "code_files": [
      {
        "file_path": "config.py",
        "file_purpose": "集中管理所有可配置参数",
        "content": "# -*- coding: utf-8 -*-\n# 实验配置文件 - 修改此文件即可适配不同实验方案\n\nimport os\nfrom datetime import datetime\n\n# ===== 运行模式 =====\nRUN_MODE = \"SMALL_TEST\"  # SMALL_TEST | FULL_RUN\n# SMALL_TEST: 使用10%数据快速验证流程\n# FULL_RUN: 全量数据完整实验\n\n# ===== 随机种子 =====\nRANDOM_SEED = 42\n\n# ===== 路径配置 =====\nDATA_DIR = \"./data/\"\nOUTPUT_DIR = f\"./output/{datetime.now().strftime('%Y%m%d_%H%M%S')}/\"\nMODEL_DIR = os.path.join(OUTPUT_DIR, \"models/\")\nFIGURE_DIR = os.path.join(OUTPUT_DIR, \"figures/\")\nLOG_DIR = os.path.join(OUTPUT_DIR, \"logs/\")\n\n# ===== 数据配置 =====\nDATA_FILE = \"application_train.csv\"  # 主训练数据文件名\nTARGET_COL = \"TARGET\"\nMISSING_THRESHOLD = 0.60  # 缺失率超过此值的特征直接删除\nTRAIN_RATIO = 0.80  # 训练集比例\nTIME_SERIES_SPLIT = True  # 是否按时间划分\n\n# ===== 预处理配置 =====\nOUTLIER_METHOD = \"IQR\"  # IQR | ZSCORE | NONE\nOUTLIER_LOWER_QUANTILE = 0.01\nOUTLIER_UPPER_QUANTILE = 0.99\n\n# ===== 模型配置 =====\nMODELS_TO_RUN = [\"LogisticRegression\", \"XGBoost\", \"LightGBM\"]\n\n# LightGBM\nLGB_PARAMS = {\n    \"objective\": \"binary\",\n    \"metric\": \"auc\",\n    \"boosting_type\": \"gbdt\",\n    \"n_estimators\": 500,\n    \"learning_rate\": 0.05,\n    \"num_leaves\": 31,\n    \"max_depth\": -1,\n    \"random_state\": RANDOM_SEED,\n    \"n_jobs\": -1,\n    \"verbose\": -1\n}\n\n# Optuna超参搜索配置\nOPTUNA_N_TRIALS = 50 if RUN_MODE == \"SMALL_TEST\" else 200\nOPTUNA_TIMEOUT = 3600  # 超参搜索超时（秒）\n\n# ===== 不均衡处理配置 =====\nIMBALANCE_METHOD = \"scale_pos_weight\"  # scale_pos_weight | SMOTE | NONE\nSMOTE_K_NEIGHBORS = 5\n\n# ===== 评估配置 =====\nCV_FOLDS = 5\nBOOTSTRAP_N = 1000\nBOOTSTRAP_CI = 0.95\n\n# ===== 可解释性配置 =====\nSHAP_MAX_DISPLAY = 20  # SHAP图中最多显示的特征数\nSHAP_SAMPLE_SIZE = 1000  # SHAP计算时使用的样本数（全量可能太慢）\n\n# ===== 可视化配置 =====\nFIGURE_DPI = 300\nFIGURE_FORMAT = \"png\"  # png | pdf | svg\nCOLOR_PALETTE = \"Set2\"\n# 中文字体设置（根据需要取消注释）\n# import matplotlib\n# matplotlib.rcParams['font.sans-serif'] = ['SimHei', 'WenQuanYi Micro Hei', 'DejaVu Sans']\n# matplotlib.rcParams['axes.unicode_minus'] = False\n",
        "dependencies": [],
        "expected_runtime": "N/A",
        "input_files_needed": [],
        "output_files_produced": []
      }
    ]
  },
  "requ