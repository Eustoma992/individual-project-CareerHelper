# -*- coding: utf-8 -*-
"""页面1：岗位数据看板 —— 考情统计可视化"""
import streamlit as st
import streamlit.components.v1 as components

import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from modules import visual
from modules.ai_service import polish_position_intro
from modules.data_service import load_seed_data
from modules.ui import inject_theme, sidebar_status

st.set_page_config(page_title="岗位数据看板", page_icon="📊", layout="wide")
inject_theme()
sidebar_status()

st.title("📊 岗位数据看板")
st.caption("数据来源：公开求职网站笔试真题与面经 → pandas 频次统计 + jieba 关键词提取")

positions = load_seed_data()
pos = st.selectbox("选择目标岗位", list(positions.keys()))
data = positions[pos]

tab_overview, tab_written, tab_interview, tab_rounds = st.tabs(
    ["🏠 总览", "✍️ 笔试考情", "🎤 面试考情", "🪜 轮次重点"])

# ---------- 总览 ----------
with tab_overview:
    w = data["written"]
    iv = data["interview"]
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("笔试核心考点数", len(w["考点分布"]))
    c2.metric("高频面试问题数", len(iv["专业面高频题"]) + len(iv["行为面高频题"]))
    c3.metric("最高频考点", w["考点分布"][0]["考点"])
    c4.metric("面经样本关键词", len(w["面经关键词"]))

    st.markdown("##### AI 考情解读（基于下方统计结果生成）")
    if st.button("生成考情解读", key="intro_btn"):
        summary = (
            "笔试考点分布：" + "；".join(
                f"{t['考点']}{t['占比']:.0%}" for t in w["考点分布"])
            + "。题型分布：" + "、".join(f"{k}{v:.0%}" for k, v in w["题型分布"].items())
            + "。面试专业面最高频问题：" + iv["专业面高频题"][0]["问题"]
        )
        with st.spinner("AI 正在结合统计结果撰写解读…"):
            text = polish_position_intro(pos, summary)
        if text:
            st.success(text)
            st.session_state["intro_text"] = text
        else:
            st.error("调用失败，请检查网络或 API 配置。")
    if "intro_text" in st.session_state:
        st.info(st.session_state["intro_text"])

# ---------- 笔试考情 ----------
with tab_written:
    w = data["written"]
    col1, col2 = st.columns([3, 2])
    with col1:
        st.plotly_chart(visual.topic_bar(w["考点分布"]), use_container_width=True)
    with col2:
        st.plotly_chart(visual.type_pie(w["题型分布"]), use_container_width=True)
    st.plotly_chart(visual.make_wordcloud(w["面经关键词"]), use_container_width=True)

# ---------- 面试考情 ----------
with tab_interview:
    iv = data["interview"]
    col1, col2 = st.columns(2)
    with col1:
        st.plotly_chart(visual.freq_bar(iv["专业面高频题"], "专业面高频问题 Top10"),
                        use_container_width=True)
    with col2:
        st.plotly_chart(visual.freq_bar(iv["行为面高频题"], "行为面高频问题"),
                        use_container_width=True)
    st.markdown("##### 高频问题明细")
    t1, t2 = st.tabs(["专业面", "行为面"])
    with t1:
        st.dataframe(
            [{"排名": i + 1, "问题": q["问题"], "被提及次数": q["频次"]}
             for i, q in enumerate(iv["专业面高频题"])],
            use_container_width=True, hide_index=True)
    with t2:
        st.dataframe(
            [{"排名": i + 1, "问题": q["问题"], "被提及次数": q["频次"]}
             for i, q in enumerate(iv["行为面高频题"])],
            use_container_width=True, hide_index=True)

# ---------- 轮次重点 ----------
with tab_rounds:
    st.markdown("##### 初面 / 复面 / 终面考察重点（依据面经轮次标注统计）")
    rounds = data["interview"]["轮次重点"]
    cols = st.columns(len(rounds))
    icons = {"初面": "🟢", "复面": "🟡", "终面": "🔴"}
    for col, (name, desc) in zip(cols, rounds.items()):
        with col:
            st.markdown(
                f"""<div style="background:#F0F6FC;border-radius:12px;padding:16px;
                border-left:5px solid #1F4E79;height:100%">
                <p style="margin:0 0 8px;font-size:16px;color:#1F4E79"><b>{icons.get(name,'')} {name}</b></p>
                <p style="margin:0;font-size:14px;line-height:1.7;color:#2B4A66">{desc}</p></div>""",
                unsafe_allow_html=True)
    st.info("💡 建议：初面前重点刷基础题，复面前准备好项目的深度追问，终面前梳理职业规划与动机表达。")
