# -*- coding: utf-8 -*-
"""页面公共组件：全局样式与侧边栏状态提示。"""
import streamlit as st

from config import has_api_key

_CSS = """
<style>
:root { --primary: #1F4E79; }
h1, h2, h3 { color: #1F4E79 !important; }
[data-testid="stSidebar"] { background: linear-gradient(180deg,#0F2C4C,#1F4E79); }
[data-testid="stSidebar"] * { color: #EAF2FA !important; }
.stButton > button[kind="primary"] { background:#1F4E79; border-color:#1F4E79; }
</style>
"""


def inject_theme():
    """注入蓝色系全局样式（每个页面调用一次）。"""
    st.markdown(_CSS, unsafe_allow_html=True)


def sidebar_status():
    """在侧边栏展示 API 配置状态，避免未配置时用户看到费解的 401。"""
    with st.sidebar:
        st.markdown("---")
        if has_api_key():
            st.caption("🔑 DeepSeek API 已配置")
        else:
            st.warning(
                "未检测到 DEEPSEEK_API_KEY。\n\n"
                "本地：复制 `.streamlit/secrets.toml.example` 为 "
                "`.streamlit/secrets.toml` 并填入 key；\n\n"
                "部署：在应用 Secrets 中配置同名变量。"
            )
        st.caption("📄 使用说明与部署文档见仓库 README")
