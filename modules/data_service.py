# -*- coding: utf-8 -*-
"""数据服务：种子考情数据加载 + 用户作答记录的持久化与统计。"""
import json
import time
from datetime import datetime

import pandas as pd
import streamlit as st

from config import SEED_DATA_PATH, USER_RECORDS_PATH


@st.cache_data
def load_seed_data():
    with open(SEED_DATA_PATH, encoding="utf-8") as f:
        return json.load(f)["positions"]


def load_records():
    """读取用户作答记录（笔试会话 + 面试会话）。"""
    if USER_RECORDS_PATH.exists():
        with open(USER_RECORDS_PATH, encoding="utf-8") as f:
            return json.load(f)
    return {"written": [], "interview": []}


def save_records(records):
    USER_RECORDS_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(USER_RECORDS_PATH, "w", encoding="utf-8") as f:
        json.dump(records, f, ensure_ascii=False, indent=2)


def append_written_record(position, total, correct_count, accuracy,
                          topic_stats, question_results):
    """记录一次笔试模拟。topic_stats: {考点: [对数, 总数]}"""
    records = load_records()
    records["written"].append({
        "time": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "ts": time.time(),
        "position": position,
        "total": total,
        "correct": correct_count,
        "accuracy": round(accuracy, 1),
        "topic_stats": topic_stats,
        "detail": question_results,
    })
    save_records(records)


def append_interview_record(position, round_name, question, answer,
                            evaluation, is_followup=False):
    records = load_records()
    records["interview"].append({
        "time": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "ts": time.time(),
        "position": position,
        "round": round_name,
        "question": question,
        "answer": answer,
        "score": evaluation.get("score"),
        "is_followup": is_followup,
        "evaluation": evaluation,
    })
    save_records(records)


def build_topic_mastery(position=None):
    """聚合所有笔试记录，输出 {考点: 正确率}，用于雷达图。"""
    records = load_records()["written"]
    agg = {}
    for r in records:
        if position and r["position"] != position:
            continue
        for topic, (c, t) in r.get("topic_stats", {}).items():
            a = agg.setdefault(topic, [0, 0])
            a[0] += c
            a[1] += t
    return {k: round(v[0] / v[1] * 100, 1) for k, v in agg.items() if v[1] > 0}


def written_history_df(position=None):
    records = load_records()["written"]
    if position:
        records = [r for r in records if r["position"] == position]
    if not records:
        return pd.DataFrame()
    df = pd.DataFrame(records)
    df["序号"] = range(1, len(df) + 1)
    return df[["序号", "time", "position", "total", "correct", "accuracy"]]
