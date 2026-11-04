# -*- coding: utf-8 -*-
"""页面3：AI面试模拟 —— 按岗位高频题多轮提问、AI评估、回放复盘"""
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

import streamlit as st

from modules import ai_service, speech
from modules.data_service import (append_interview_record, load_records,
                                   load_seed_data)
from modules.ui import inject_theme, sidebar_status

st.set_page_config(page_title="AI面试模拟", page_icon="🎤", layout="wide")
inject_theme()
sidebar_status()
st.title("🎤 AI 面试模拟")
st.caption("按岗位高频面试题依次提问，支持多轮追问；AI 结合岗位特征评估逻辑框架与关键信息覆盖")

positions = load_seed_data()
pos = st.selectbox("目标岗位", list(positions.keys()), key="iv_pos")
rounds = list(positions[pos]["interview"]["轮次重点"].keys())
round_name = st.selectbox("模拟轮次", rounds,
                          help="不同轮次考察重点不同：初面重基础，复面重项目与设计，终面重素质")

# 初始化面试会话
if st.button("🎬 开始新一轮模拟面试", type="primary"):
    bank = positions[pos]["interview"]
    prof = bank["专业面高频题"][:3]
    behav = bank["行为面高频题"][:2]
    queue = []
    if round_name == "初面":
        queue = [q["问题"] for q in (behav[:1] + prof[:3])]
    elif round_name == "复面":
        queue = [q["问题"] for q in (prof[:3] + behav[:1])]
    else:
        queue = [q["问题"] for q in (behav[:3] + prof[:1])]
    st.session_state.update({
        "iv_queue": queue, "iv_idx": 0, "iv_transcript": [],
        "iv_followups": 0, "iv_round": round_name,
    })  # 注意：岗位由上方 selectbox（key="iv_pos"）自动维护，不能再写入，否则报状态冲突
    st.rerun()

state_ok = "iv_queue" in st.session_state and st.session_state["iv_idx"] < len(st.session_state["iv_queue"])

if state_ok:
    queue = st.session_state["iv_queue"]
    idx = st.session_state["iv_idx"]
    question = queue[idx]
    done = st.session_state["iv_transcript"]

    # 进度
    st.progress(idx / len(queue), text=f"第 {idx + 1} / {len(queue)} 题 · 轮次：{st.session_state['iv_round']}")
    st.markdown(f"##### 🎙️ 面试官提问（{'追问' if idx > 0 and st.session_state.get('iv_last_followup') else '正式题'}）")
    st.markdown(
        f"""<div style="background:#EEF3F8;border-radius:12px;padding:16px;font-size:16px">
        <b>{question}</b></div>""", unsafe_allow_html=True)

    # 朗读问题（可选，模拟真实面试的口头提问）
    if st.button("🔊 朗读这道题", key=f"iv_tts_{idx}",
                 help="使用语音合成朗读问题，更贴近真实面试场景"):
        try:
            with st.spinner("正在合成语音…"):
                st.session_state[f"iv_qaudio_{idx}"] = speech.tts(question)
        except Exception as e:
            st.warning(f"朗读失败（不影响作答）：{e}")
    if f"iv_qaudio_{idx}" in st.session_state:
        st.audio(st.session_state[f"iv_qaudio_{idx}"], format="audio/mp3")

    # 语音转写结果回填：必须在 text_area 实例化之前写入，否则 Streamlit 会报状态冲突
    pending_key = f"iv_pending_answer_{idx}"
    if st.session_state.get(pending_key):
        st.session_state[f"iv_answer_{idx}"] = st.session_state.pop(pending_key)
        st.session_state[f"iv_voice_{idx}"] = True

    answer = st.text_area("✍️ 你的回答（可直接打字，或用下方麦克风录音后自动转写）",
                          height=150, key=f"iv_answer_{idx}")

    # —— 语音作答：录音 → 本地转写 → 填入回答 —— #
    audio = st.audio_input("🎤 语音作答：点击录音，说完后点击停止（仅录音，不调用摄像头）",
                           key=f"iv_mic_{idx}")
    if audio is not None:
        st.audio(audio)
        transcribe_btn = st.button("🔎 识别录音并填入回答", type="secondary",
                                   key=f"iv_asr_{idx}")
        if transcribe_btn:
            try:
                with st.spinner("正在本地识别语音（首次需加载模型，约 10–30 秒）…"):
                    text = speech.transcribe(audio.getvalue(),
                                             suffix=(audio.name.rsplit(".", 1)[-1]
                                                     if "." in audio.name else "wav"))
                if text:
                    st.session_state[pending_key] = text
                    st.rerun()
                else:
                    st.warning("没有识别到语音内容，请靠近麦克风重录，或直接打字作答。")
            except Exception as e:
                st.error(f"语音识别失败：{e}（可直接打字作答，不影响本轮模拟）")

    c1, c2, c3 = st.columns([1, 1, 2])
    submit = c1.button("提交回答，获取 AI 评估", type="primary")
    follow = c2.button("🔁 模拟面试官追问", disabled=not answer.strip())
    giveup = c3.button("跳过此题")

    if submit or follow or giveup:
        is_followup = follow and idx > 0 and st.session_state.get("iv_last_followup")
        if giveup:
            evaluation = {"score": 0, "logic": "未作答。", "coverage": "未作答。",
                          "suggestions": "建议参考关键要点组织回答。", "key_points": []}
            user_answer = "（跳过）"
        else:
            with st.spinner("AI 面试官正在评估你的回答…"):
                try:
                    if follow:
                        # 追问：生成新问题入队
                        brief = "；".join(f"Q:{t['question'][:30]}" for t in done[-2:])
                        new_q = ai_service.generate_interview_followup(
                            st.session_state["iv_pos"], question, answer, brief)
                        queue.insert(idx + 1, new_q)
                        st.session_state["iv_last_followup"] = True
                        append_interview_record(
                            st.session_state["iv_pos"], st.session_state["iv_round"],
                            question, answer, {"score": None, "logic": "已回答，等待追问后的整体评估",
                                               "coverage": "", "suggestions": "追问已加入队列",
                                               "key_points": []}, is_followup=True)
                        st.session_state["iv_idx"] += 1
                        st.rerun()
                    evaluation = ai_service.evaluate_interview_answer(
                        st.session_state["iv_pos"], question, answer,
                        st.session_state["iv_round"])
                except Exception as e:
                    st.error(f"AI 评估调用失败：{e}")
                    st.stop()
            user_answer = answer
            st.session_state["iv_last_followup"] = False

        st.session_state["iv_transcript"].append({
            "question": question, "answer": user_answer,
            "evaluation": evaluation, "is_followup": is_followup,
            "voice": st.session_state.get(f"iv_voice_{idx}", False)})
        append_interview_record(st.session_state["iv_pos"], st.session_state["iv_round"],
                                question, user_answer, evaluation, is_followup)
        st.session_state["iv_idx"] += 1
        st.rerun()

elif "iv_queue" in st.session_state:
    # 本轮结束：汇总
    st.success("🎉 本轮模拟面试完成！以下是整体评估汇总。")
    transcript = st.session_state["iv_transcript"]
    scores = [t["evaluation"].get("score") or 0 for t in transcript]
    m1, m2, m3 = st.columns(3)
    m1.metric("回答题数", len(transcript))
    m2.metric("平均得分", f"{sum(scores) / len(scores):.0f}" if scores else "—")
    weak = [t for t in transcript if (t["evaluation"].get("score") or 0) < 60]
    m3.metric("失分点数", len(weak))

    st.markdown("##### 失分点汇总（复盘重点）")
    for t in weak:
        with st.container(border=True):
            st.markdown(f"**❓ {t['question']}**")
            ev = t["evaluation"]
            st.markdown(f"- **逻辑框架：** {ev.get('logic', '—')}")
            st.markdown(f"- **关键信息覆盖：** {ev.get('coverage', '—')}")
            st.markdown(f"- **优化建议：** {ev.get('suggestions', '—')}")
            if ev.get("key_points"):
                st.markdown("- **高分要点：** " + "；".join(ev["key_points"]))

    with st.expander("📼 完整面试回放", expanded=False):
        for i, t in enumerate(transcript):
            st.markdown(f"**[{i+1}] 面试官：** {t['question']}")
            tag = " 🎤（语音作答）" if t.get("voice") else ""
            st.markdown(f"**你：** {t['answer']}{tag}")
            ev = t["evaluation"]
            st.markdown(f"> 得分 **{ev.get('score')}** · {ev.get('suggestions', '')}")
            st.divider()
else:
    st.info("👆 选择岗位与轮次后，点击「开始新一轮模拟面试」。题目来自该岗位真实面经中的高频问题，"
            "支持 **🎤 麦克风语音作答**（本地转写，不上传录音）或打字作答，"
            "还可点击「朗读这道题」听面试官口头提问。作答后 AI 将评估逻辑框架、关键信息覆盖，"
            "并给出可落地的优化建议。")
