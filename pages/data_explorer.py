# -*- coding: utf-8 -*-
"""页面5：真实面经数据库 —— 浏览与检索采集到的笔面经原始记录"""
import streamlit as st
import pandas as pd

import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from modules.ui import inject_theme, sidebar_status

st.set_page_config(page_title="真实面经数据库", page_icon="🗂", layout="wide")
inject_theme()
sidebar_status()

CSV_PATH = pathlib.Path(__file__).resolve().parent.parent / "data" / "面经数据" / "records_full.csv"

st.title("🗂 真实面经数据库")
st.caption("数据来源：牛客网 / Codetop / 职题库 / 赛码网 / 应届生求职网 公开页面采集，逐条可溯源（url 字段为原始链接）")

if not CSV_PATH.exists():
    st.warning(
        "尚未找到数据文件 `data/面经数据/records_full.csv`。\n\n"
        "运行 `python scripts/collect_interview_data.py` 即可从公开网站采集并生成该文件。"
    )
    st.stop()

@st.cache_data(show_spinner="加载数据库…")
def load():
    return pd.read_csv(CSV_PATH, encoding="utf-8-sig").fillna("")

df = load()

# ---------- 总览指标 ----------
c1, c2, c3, c4 = st.columns(4)
c1.metric("记录总数", f"{len(df):,}")
c2.metric("数据源", df["source"].nunique())
c3.metric("覆盖公司/主体", f"{df.loc[df['company'] != '', 'company'].nunique():,}")
dates = df.loc[df["publish_date"] != "", "publish_date"]
c4.metric("时间范围", f"{dates.min()} ~ {dates.max()}" if len(dates) else "—")

# ---------- 筛选器 ----------
with st.container(border=True):
    fc1, fc2, fc3 = st.columns([1.2, 1.2, 2])
    src = fc1.multiselect("数据源", sorted(df["source"].unique()))
    ind = fc2.multiselect("行业", sorted([i for i in df["industry"].unique() if i]))
    kw = fc3.text_input("关键词检索（标题/摘要/公司）", placeholder="如：银行、管培生、LeetCode")

view = df
if src:
    view = view[view["source"].isin(src)]
if ind:
    view = view[view["industry"].isin(ind)]
if kw:
    mask = (view["title"].str.contains(kw, case=False, regex=False)
            | view["summary"].str.contains(kw, case=False, regex=False)
            | view["company"].str.contains(kw, case=False, regex=False))
    view = view[mask]

# ---------- 分布图 ----------
tab1, tab2 = st.tabs(["按数据源", "按行业"])
with tab1:
    st.bar_chart(view["source"].value_counts().head(12), horizontal=True)
with tab2:
    ind_series = view["industry"].replace("", "未标注")
    st.bar_chart(ind_series.value_counts(), horizontal=True)

# ---------- 明细表 ----------
st.subheader(f"记录明细（{len(view):,} 条）")
show = view[["source", "industry", "stage", "title", "company", "publish_date", "url"]].copy()
show["链接"] = show["url"].apply(lambda u: f"[打开]({u})" if u else "")
st.dataframe(
    show.drop(columns=["url"]).rename(columns={
        "source": "来源", "industry": "行业", "stage": "类型",
        "title": "标题", "company": "公司", "publish_date": "日期"}),
    use_container_width=True, height=460, hide_index=True,
)

st.download_button(
    "⬇️ 导出当前筛选结果（CSV）",
    data=view.to_csv(index=False).encode("utf-8-sig"),
    file_name="面经筛选结果.csv", mime="text/csv",
)

with st.expander("ℹ️ 数据说明与边界（如实声明）"):
    st.markdown(
        "- **应届生求职网**记录为校招招聘公告（列表页公开字段），不是面经正文；BBS 面经需登录，未采集\n"
        "- **职题库 / 赛码网**为题集目录层信息（题集名、简介、练习人次），题目原文需登录/付费，未采集\n"
        "- **牛客网**记录来自 SSR 页面卡片：标题、发帖时间、作者学校、正文前 180 字摘要\n"
        "- **Codetop**为公开题库接口：题目、考察频次、难度，无公司字段\n"
        "- `summary` 一律为原文截断，未做任何改写；`extra` 保留采集时的检索词/原始字段备注"
    )
