# -*- coding: utf-8 -*-
"""测试前置：把项目根目录加入 sys.path，并把数据目录指向临时副本（不污染个人记录）。"""
import os
import pathlib
import shutil
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

_TMP = pathlib.Path(tempfile.mkdtemp(prefix="jobprep-test-"))
shutil.copy(ROOT / "data" / "seed_data.json", _TMP / "seed_data.json")
os.environ["JOBPREP_DATA_DIR"] = str(_TMP)
os.environ.setdefault("DEEPSEEK_API_KEY", "")
