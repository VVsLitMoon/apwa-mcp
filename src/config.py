"""APWA MCP Server — 配置与路径管理。

所有路径都从项目根目录推导，可用环境变量覆盖，克隆到任何机器都能直接跑：
  APWA_SKILL_DIR   Skill 定义文件所在目录（默认 <项目根>/skills）
  APWA_WORK_DIR    运行时状态与交付物目录（默认 <项目根>/runtime）
"""

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
SKILL_DIR = Path(os.environ.get("APWA_SKILL_DIR", BASE_DIR / "skills")).resolve()
WORK_DIR = Path(os.environ.get("APWA_WORK_DIR", BASE_DIR / "runtime")).resolve()

OUTPUT_DIR = WORK_DIR / "skill_outputs"
DELIVERY_DIR = WORK_DIR / "delivery"

# 运行时目录按需创建
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
DELIVERY_DIR.mkdir(parents=True, exist_ok=True)

# Skill 文件名约定：Skill-01-xxx.md
SKILL_FILE_PATTERN = "Skill-{:02d}-*.md"

# 流水线阶段总数
TOTAL_SKILLS = 14

# 评阅-修改循环的最大轮次（Skill 12 / 13）
MAX_REVIEW_ROUNDS = 3

# Skill 08 执行生成代码前的危险模式扫描
DANGEROUS_PATTERNS = [
    (r"os\.system\s*\(", "os.system() call detected"),
    (r"subprocess\.call\s*\(.*shell\s*=\s*True", "subprocess.call() with shell=True"),
    (r"subprocess\.Popen\s*\(.*shell\s*=\s*True", "subprocess.Popen() with shell=True"),
    (r"\beval\s*\(", "eval() call detected"),
    (r"\bexec\s*\(", "exec() call detected"),
    (r"__import__\s*\(\s*['\"]os['\"]", "dynamic os import"),
    (r"/etc/", "Reference to /etc/ system directory"),
    (r"C:\\Windows", "Reference to C:\\Windows system directory"),
    (r"~/.ssh", "Reference to SSH credential directory"),
    (r"~/.aws", "Reference to AWS credential directory"),
    (r"rm\s+-rf\s+/", "Recursive root deletion pattern"),
    (r"shutil\.rmtree\s*\(\s*['\"]/", "Root rmtree pattern"),
]

# 这类论文跳过实验相关阶段（Skill 07 / 08）
THEORY_PAPER_TYPES = {"理论推演", "综述论文"}
