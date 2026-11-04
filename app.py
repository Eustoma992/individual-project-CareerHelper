# -*- coding: utf-8 -*-
"""大学生实习&校招笔面试数据分析辅导工具 · 主页：使用流程导航"""
import streamlit as st

from modules.ui import inject_theme, sidebar_status

APP_TITLE = "大学生实习&校招笔面试数据分析辅导工具"

st.set_page_config(
    page_title=APP_TITLE,
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded",
)

# 蓝色系全局主题
inject_theme()
sidebar_status()

st.title("🎓 " + APP_TITLE)
st.caption("基于真实面经统计的 AI 笔试/面试模拟工具 —— 从了解考情，到专项训练，再到量化复盘")

st.markdown(
    """
    <div style="background:linear-gradient(135deg,#0F2C4C,#1F4E79 55%,#2E75B6);border-radius:14px;
    padding:22px 28px;margin-bottom:18px;">
    <p style="font-size:17px;color:white;margin:0 0 6px;"><b>为什么这个工具可靠？</b></p>
    <p style="color:#DCE9F5;font-size:14px;margin:0;line-height:1.8;">
    所有模拟题均以公开求职网站采集的真实面经与真题的<b style="color:#9DC3E6">统计结果</b>为依据生成，
    按岗位、题型、轮次三个维度组织数据，避免 AI 凭空出题导致的泛化与幻觉；
    你的每一次练习都会同步到个人仪表盘，形成「模拟 → 反馈 → 再练习」的学习闭环。</p>
    </div>
    """,
    unsafe_allow_html=True,
)

st.subheader("三步使用流程")

c1, c2, c3 = st.columns(3, gap="medium")
with c1:
    st.markdown(
        """#### 📊 第一步 · 看考情
        在 **岗位数据看板** 选择目标岗位，浏览考点分布、题型频次、
        高频面试问题与各轮次考察重点，明确复习方向与范围。""")
with c2:
    st.markdown(
        """#### ✍️ 第二步 · 专项练
        进入 **AI笔试模拟** 或 **AI面试模拟** 进行针对性练习。
        系统依据统计结果控制题目的考点覆盖与难度分布。""")
with c3:
    st.markdown(
        """#### 📈 第三步 · 量化复盘
        作答记录自动同步至 **个人备考仪表盘**，查看正确率趋势、
        考点掌握度雷达与失分点汇总，量化看到自己的提升。""")

st.divider()
st.markdown(
    """
    **开始使用** 👉 点击左侧边栏进入任意模块：

    | 模块 | 说明 |
    |------|------|
    | 📊 岗位数据看板 | 真实考情统计可视化：考点分布 / 题型频次 / 高频面试题 / 轮次重点 |
    | ✍️ AI 笔试模拟 | 按考点权重生成单选/多选/简答/计算等题型，自动评分并定位薄弱考点 |
    | 🎤 AI 面试模拟 | 按高频题多轮提问；支持 **麦克风语音作答（本地转写）** 与问题朗读，评估逻辑框架与关键信息覆盖，支持回放复盘 |
    | 📈 个人备考仪表盘 | 正确率折线趋势 + 考点掌握度雷达 + 完整作答历史 |
    """
)
