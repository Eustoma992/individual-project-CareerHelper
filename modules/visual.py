# -*- coding: utf-8 -*-
"""可视化模块：考点分布、题型占比、趋势折线、掌握度雷达、面经词云。"""
import os
import random

import jieba
import matplotlib
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import plotly.graph_objects as go
from wordcloud import WordCloud

# 跨平台中文字体：Windows / macOS / Linux（云端用 packages.txt 安装 fonts-noto-cjk）
_FONT_CANDIDATES = [
    "C:/Windows/Fonts/msyh.ttc",
    "C:/Windows/Fonts/simhei.ttf",
    "/System/Library/Fonts/PingFang.ttc",
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
    "/usr/share/fonts/opentype/noto/NotoSansCJKsc-Regular.otf",
    "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
    "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc",
    "/usr/share/fonts/truetype/arphic/uming.ttc",
]


def _cjk_font_path():
    """返回第一个存在的中文字体文件，供 WordCloud 使用；找不到返回 None。"""
    for path in _FONT_CANDIDATES:
        if os.path.isfile(path):
            return path
    return None


matplotlib.rcParams["font.sans-serif"] = [
    "Microsoft YaHei", "SimHei", "PingFang SC", "Noto Sans CJK SC",
    "WenQuanYi Zen Hei", "sans-serif",
]
matplotlib.rcParams["axes.unicode_minus"] = False

# 蓝色系配色（深浅蓝渐进）
PALETTE = ["#0F2C4C", "#1F4E79", "#2E75B6", "#4472C4", "#5B9BD5",
           "#6C8EBF", "#8FAADC", "#9DC3E6", "#BDD7EE", "#DEEBF7"]


def topic_bar(topics):
    """考点分布柱状图。topics: [{考点, 占比}]"""
    df = pd.DataFrame(topics).sort_values("占比", ascending=False)
    fig = go.Figure(go.Bar(
        x=df["考点"], y=df["占比"] * 100, marker_color=PALETTE[2],
        text=[f"{v:.0%}" for v in df["占比"]], textposition="outside",
        customdata=df["题量"], hovertemplate="%{x}<br>占比 %{y:.1f}%（约%{customdata}题）<extra></extra>",
    ))
    fig.update_layout(title="笔试考点分布（统计占比）", yaxis_title="占比 (%)",
                      xaxis_title="", height=400, margin=dict(t=50, b=30))
    return fig


def type_pie(type_mix):
    """题型占比饼图。type_mix: {题型: 占比}"""
    fig = go.Figure(go.Pie(
        labels=list(type_mix.keys()), values=[v * 100 for v in type_mix.values()],
        marker=dict(colors=PALETTE), hole=0.45,
        textinfo="label+percent", texttemplate="%{label}<br>%{percent}",
    ))
    fig.update_layout(title="题型分布", height=360, margin=dict(t=50, b=20))
    return fig


def freq_bar(items, title, top_n=10):
    """高频问题频次横向条形图。items: [{问题, 频次}]"""
    df = pd.DataFrame(items).sort_values("频次").tail(top_n)
    fig = go.Figure(go.Bar(
        x=df["频次"], y=df["问题"], orientation="h",
        marker_color=PALETTE[4], text=df["频次"], textposition="outside",
    ))
    fig.update_layout(title=title, xaxis_title="被提及次数（面经统计）",
                      height=max(320, 36 * len(df) + 90), margin=dict(t=50, b=30, l=10))
    return fig


def accuracy_line(df):
    """正确率趋势折线图。df 需含 序号/accuracy/position 列。"""
    fig = go.Figure()
    for i, pos in enumerate(df["position"].unique()):
        sub = df[df["position"] == pos]
        fig.add_trace(go.Scatter(
            x=sub["序号"], y=sub["accuracy"], mode="lines+markers", name=pos,
            line=dict(color=PALETTE[i % len(PALETTE)], width=3),
        ))
    fig.add_hline(y=60, line_dash="dot", line_color="#2E75B6",
                  annotation_text="及格参考线 60%")
    fig.update_layout(title="笔试模拟正确率趋势", xaxis_title="模拟次数（按岗位分组）",
                      yaxis_title="正确率 (%)", yaxis_range=[0, 105], height=400)
    return fig


def mastery_radar(mastery):
    """考点掌握度雷达图。mastery: {考点: 正确率}"""
    topics = list(mastery.keys())
    values = list(mastery.values())
    fig = go.Figure(go.Scatterpolar(
        r=values + values[:1], theta=topics + topics[:1],
        fill="toself", fillcolor="rgba(46,117,182,0.25)",
        line=dict(color=PALETTE[1], width=2),
    ))
    fig.update_layout(title="考点掌握度雷达图（各考点正确率 %）",
                      polar=dict(radialaxis=dict(range=[0, 100])),
                      height=460)
    return fig


def make_wordcloud(keywords):
    """面经关键词词云（模拟 jieba 分词后的高频统计结果）。"""
    freq = {}
    for k in keywords:
        # jieba 复核分词，粒度更细，模拟真实统计流程
        for w in jieba.cut(k):
            w = w.strip()
            if len(w) >= 2:
                freq[w] = freq.get(w, 0) + random.randint(3, 9)
    wc = WordCloud(font_path=_cjk_font_path(), width=760, height=320,
                   background_color="white", colormap="Blues",
                   prefer_horizontal=0.95).generate_from_frequencies(freq)
    fig, ax = plt.subplots(figsize=(7.6, 3.2), dpi=100)
    ax.imshow(wc, interpolation="bilinear")
    ax.axis("off")
    ax.set_title("面经高频关键词词云", fontsize=13, color="#1F4E79")
    plt.tight_layout()
    return fig
