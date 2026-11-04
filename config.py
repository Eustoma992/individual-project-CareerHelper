# -*- coding: utf-8 -*-
"""全局配置：API 凭据、模型与数据路径。

密钥读取优先级（前者覆盖后者）：
1. 环境变量 ``DEEPSEEK_API_KEY``（本地开发可写在项目根目录的 ``.env``，启动时自动载入）
2. Streamlit Secrets（``.streamlit/secrets.toml`` 或部署平台的 Secrets 面板）
3. 空字符串（此时 AI 功能会给出配置提示，而不是直接抛 401）

仓库中不保存任何真实密钥，请勿把 ``.env`` / secrets.toml 提交到版本库。
"""
import os
import pathlib

BASE_DIR = pathlib.Path(__file__).resolve().parent

# 从项目根目录的 .env 载入凭据；文件不存在或未安装 python-dotenv 时静默跳过。
# override=False：已存在的环境变量优先，方便命令行临时覆盖。
try:
    from dotenv import load_dotenv

    load_dotenv(BASE_DIR / ".env", override=False)
except Exception:
    pass


def _read_secret(name, default=""):
    """按「环境变量 → st.secrets」的顺序读取配置，任何异常都安全降级。

    显式设置为空字符串的环境变量视为「主动清空」，不再回落到 secrets，
    便于测试与临时关闭 AI 功能。
    """
    if name in os.environ:
        return os.environ[name].strip()
    try:
        import streamlit as st

        value = st.secrets.get(name)  # 非运行时环境下会抛异常，已被捕获
        if value:
            return str(value).strip()
    except Exception:
        pass
    return default


# ---------- DeepSeek API ----------
DEEPSEEK_API_KEY = _read_secret("DEEPSEEK_API_KEY")
DEEPSEEK_BASE_URL = _read_secret("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
DEEPSEEK_MODEL = _read_secret("DEEPSEEK_MODEL", "deepseek-chat")


def has_api_key():
    """是否已配置可用的 API Key（页面层据此提示用户）。"""
    return bool(DEEPSEEK_API_KEY)


# ---------- 数据文件 ----------
# 可用 JOBPREP_DATA_DIR 指向可写目录（容器/云端持久化卷）
DATA_DIR = pathlib.Path(_read_secret("JOBPREP_DATA_DIR", str(BASE_DIR / "data")))
SEED_DATA_PATH = DATA_DIR / "seed_data.json"
USER_RECORDS_PATH = DATA_DIR / "user_records.json"
