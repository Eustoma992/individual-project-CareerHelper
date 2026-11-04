# -*- coding: utf-8 -*-
"""页面2：AI笔试模拟 —— 按考点权重出题、自动评分、薄弱考点定位与专项加练"""
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

import streamlit as st

from modules import ai_service
from modules.data_service import (append_written_record, load_records,
                                   load_seed_data)
from modules.ui import inject_theme, sidebar_status

st.set_page_config(page_title="AI笔试模拟", page_icon="✍️", layout="wide")
inject_theme()
sidebar_status()
st.title("✍️ AI 笔试模拟")
st.caption("题目由 AI 依据岗位考情统计结果生成：考点覆盖贴合统计占比，答题后自动评分并定位薄弱考点")


def normalize_answer(q):
    """把模型给的 answer 规整为字母集合（选择题）。"""
    ans = str(q.get("answer", "")).upper()
    return {ch.strip() for ch in ans.split(",") if ch.strip() in "ABCD"}


def grade(q, user):
    """返回 (是否正确, 得分100制)。客观题本地判分，主观题由 AI 评分。"""
    qtype = q.get("type", "单选")
    if qtype in ("单选", "多选"):
        correct = normalize_answer(q)
        return user == correct, 100 if user == correct else 0
    # 简答/编程：AI 评分
    try:
        res = ai_service.grade_subjective(q["question"], q.get("answer", ""),
                                          user or "（未作答）")
        score = max(0, min(100, int(res.get("score", 0))))
        return score >= 60, score
    except Exception as e:
        st.warning(f"AI 评分调用失败：{e}")
        return False, 0


positions = load_seed_data()
pos = st.selectbox("目标岗位", list(positions.keys()), key="w_pos")

c1, c2 = st.columns([1, 3])
n_q = c1.slider("题量", 3, 10, 5, help="题量越大，生成耗时越长")
if c2.button("🚀 依据考情统计生成试卷", type="primary", use_container_width=True):
    w = positions[pos]["written"]
    try:
        with st.spinner("AI 正在依据考点权重出题…（约10-40秒）"):
            qs = ai_service.generate_written_questions(
                pos, w["考点分布"], w["题型分布"], n_q)
        st.session_state.update({"wq_questions": qs, "wq_submitted": False,
                                 "wq_results": None, "wq_pos": pos})
        st.rerun()
    except Exception as e:
        st.error(f"出题失败：{e}")

# ---------- 答题区 ----------
if "wq_questions" in st.session_state:
    qs = st.session_state["wq_questions"]
    st.divider()
    st.subheader(f"试卷 · {st.session_state.get('wq_pos', pos)}（{len(qs)}题）")

    for i, q in enumerate(qs):
        qtype = q.get("type", "单选")
        opts = q.get("options") or []
        with st.container(border=True):
            st.markdown(
                f"**第{i+1}题** ` {qtype} ` ` 考点:{q.get('topic','-')} ` ` 难度:{q.get('difficulty','-')} `")
            st.markdown(q.get("question", ""))
            if qtype == "单选":
                st.session_state.setdefault(f"ans_{i}", None)
                st.radio("你的答案", opts or ["A", "B", "C", "D"],
                         key=f"ans_{i}", label_visibility="collapsed", index=None)
            elif qtype == "多选":
                st.multiselect("你的答案（可多选）", opts or ["A", "B", "C", "D"],
                               key=f"ans_{i}", label_visibility="collapsed")
            else:
                st.text_area("你的作答", key=f"ans_{i}", height=120,
                             label_visibility="collapsed",
                             placeholder="在此输入你的答案（简答/计算题请写清思路、步骤与结果）")

    if not st.session_state.get("wq_submitted"):
        if st.button("📤 交卷并评分", type="primary"):
            with st.spinner("正在评分（简答/计算/案例题由 AI 阅卷）…"):
                results = []
                topic_stats = {}
                for i, q in enumerate(qs):
                    qtype = q.get("type", "单选")
                    user = st.session_state.get(f"ans_{i}")
                    if qtype in ("单选", "多选"):
                        user = {o[0] for o in (user or []) if isinstance(o, str) and o}
                    ok, score = grade(q, user)
                    topic = q.get("topic", "未分类")
                    a = topic_stats.setdefault(topic, [0, 0])
                    a[0] += 1 if ok else 0
                    a[1] += 1
                    results.append({"q": q, "user": user, "ok": ok, "score": score})
                total = len(qs)
                correct = sum(1 for r in results if r["ok"])
                append_written_record(st.session_state.get("wq_pos", pos), total,
                                      correct, correct / total * 100, topic_stats,
                                      [{"question": r["q"]["question"],
                                        "topic": r["q"].get("topic"),
                                        "ok": r["ok"], "score": r["score"]}
                                       for r in results])
                st.session_state.update({"wq_results": results, "wq_submitted": True})
            st.rerun()

# ---------- 成绩与复盘 ----------
if st.session_state.get("wq_results"):
    results = st.session_state["wq_results"]
    total = len(results)
    correct = sum(1 for r in results if r["ok"])
    st.divider()
    st.subheader("📊 评分结果")
    m1, m2, m3 = st.columns(3)
    m1.metric("总正确率", f"{correct / total * 100:.0f}%")
    m2.metric("答对题数", f"{correct} / {total}")
    weak = [t for t, (c, n) in
            {r["q"].get("topic", "未分类"): (0, 0) for r in results}.items()]
    weak_topics = sorted({r["q"].get("topic", "未分类") for r in results if not r["ok"]})
    m3.metric("薄弱考点数", len(weak_topics))

    st.markdown("##### 逐题解析")
    for i, r in enumerate(results):
        q = r["q"]
        icon = "✅" if r["ok"] else "❌"
        with st.container(border=True):
            st.markdown(f"{icon} **第{i+1}题**（{q.get('type')} · {q.get('topic')}） 得分：{r['score']}")
            st.markdown(f"**题目：** {q.get('question')}")
            if q.get("options"):
                st.markdown(f"**正确答案：** {q.get('answer')}")
            st.markdown(f"**解析：** {q.get('explanation', '—')}")
            if not r["ok"]:
                st.error("该题定位到薄弱考点，已加入专项训练推荐。")

    # 薄弱考点专项加练
    st.markdown("##### 🎯 针对性专项训练")
    if weak_topics:
        st.markdown(f"检测到薄弱考点：**{'、'.join(weak_topics)}**，可针对这些考点加练同类题目。")
        if st.button("生成薄弱考点专项练习题（3题）"):
            w = positions[st.session_state.get("wq_pos", pos)]["written"]
            topics = [{"考点": t, "占比": 1 / len(weak_topics)} for t in weak_topics]
            try:
                with st.spinner("正在生成专项题目…"):
                    extra = ai_service.generate_written_questions(
                        st.session_state.get("wq_pos", pos), topics,
                        {"单选": 0.5, "简答": 0.5}, 3)
                st.session_state.update({"wq_questions": extra, "wq_submitted": False,
                                         "wq_results": None, "wq_pos": st.session_state.get("wq_pos", pos)})
                st.success("专项题已生成，请在上方完成作答。")
                st.rerun()
            except Exception as e:
                st.error(f"生成失败：{e}")
    else:
        st.success("本卷全部答对，没有薄弱考点，继续保持！")

    st.info("💾 本次作答已自动同步至「📈 个人备考仪表盘」，可查看正确率趋势与考点掌握度变化。")
