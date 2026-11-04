# -*- coding: utf-8 -*-
"""页面4：个人备考数据仪表盘 —— 正确率趋势、考点掌握度雷达、作答历史"""
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

import streamlit as st

from modules import visual
from modules.data_service import (build_topic_mastery, load_records,
                                   written_history_df)
from modules.ui import inject_theme, sidebar_status

st.set_page_config(page_title="个人备考仪表盘", page_icon="📈", layout="wide")
inject_theme()
sidebar_status()
st.title("📈 个人备考数据仪表盘")
st.caption("所有笔试/面试模拟记录自动同步至此，量化呈现你的备考进步")

records = load_records()
if not records["written"] and not records["interview"]:
    st.info("暂无练习记录。请先前往「✍️ AI笔试模拟」或「🎤 AI面试模拟」完成一次练习。")
    st.stop()

all_positions = sorted({r["position"] for r in records["written"]}
                       | {r["position"] for r in records["interview"]})
pos_filter = st.selectbox("筛选岗位（全部=汇总）", ["全部"] + all_positions)
pf = None if pos_filter == "全部" else pos_filter

c1, c2, c3, c4 = st.columns(4)
c1.metric("笔试模拟次数", len(records["written"]) if not pf else
          sum(1 for r in records["written"] if r["position"] == pf))
c2.metric("面试答题数", len(records["interview"]) if not pf else
          sum(1 for r in records["interview"] if r["position"] == pf))
avg_acc = (sum(r["accuracy"] for r in records["written"] if not pf or r["position"] == pf)
           / max(1, len([r for r in records["written"] if not pf or r["position"] == pf])))
c3.metric("平均笔试正确率", f"{avg_acc:.1f}%")
iv_scores = [r["score"] for r in records["interview"] if r.get("score") is not None
             and (not pf or r["position"] == pf)]
c4.metric("面试平均得分", f"{sum(iv_scores) / len(iv_scores):.0f}" if iv_scores else "—")

st.divider()
col1, col2 = st.columns(2)
with col1:
    df = written_history_df(pf)
    if not df.empty:
        st.plotly_chart(visual.accuracy_line(df), use_container_width=True)
    else:
        st.info("暂无笔试记录")
with col2:
    mastery = build_topic_mastery(pf)
    if mastery:
        st.plotly_chart(visual.mastery_radar(mastery), use_container_width=True)
        weakest = min(mastery, key=mastery.get)
        st.warning(f"🎯 当前最薄弱考点：**{weakest}**（正确率 {mastery[weakest]}%），建议前往笔试模拟专项加练。")
    else:
        st.info("暂无考点数据")

st.markdown("##### 笔试模拟历史")
df = written_history_df(pf)
if not df.empty:
    st.dataframe(df, use_container_width=True, hide_index=True)

st.markdown("##### 面试模拟记录")
ivs = [r for r in records["interview"] if not pf or r["position"] == pf]
if ivs:
    for r in reversed(ivs[-8:]):
        score = r.get("score")
        icon = "🟢" if (score or 0) >= 80 else "🟡" if (score or 0) >= 60 else "🔴"
        with st.expander(f"{icon} [{r['time']}] {r['position']} · {r['round']}"
                         f"{'（追问）' if r.get('is_followup') else ''} · 得分 {score if score is not None else '—'}"):
            st.markdown(f"**❓ {r['question']}**")
            st.markdown(f"**你的回答：** {r['answer']}")
            ev = r.get("evaluation", {})
            if ev.get("logic"):
                st.markdown(f"- **逻辑框架：** {ev['logic']}")
            if ev.get("coverage"):
                st.markdown(f"- **信息覆盖：** {ev['coverage']}")
            if ev.get("suggestions"):
                st.markdown(f"- **优化建议：** {ev['suggestions']}")
            if ev.get("key_points"):
                st.markdown("- **高分要点：** " + "；".join(ev["key_points"]))
else:
    st.info("暂无面试记录")
