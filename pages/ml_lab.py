# -*- coding: utf-8 -*-
"""模型实验室：把本项目自有数据喂给经典机器学习模型。

数据来源分两层，页面会明确标注：
1. 真实作答记录（data/user_records.json，只存在本地，不上传）
2. 模拟扩样（当真实记录不足以支撑训练时，按题目难度与考生能力生成
   固定种子的合成数据，生成规则在页面中写明，绝不冒充真实数据）
"""
import json
from pathlib import Path

import matplotlib
import matplotlib.font_manager as fm
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import streamlit as st
from sklearn.cluster import KMeans
from sklearn.decomposition import PCA
from sklearn.linear_model import LinearRegression, LogisticRegression
from sklearn.metrics import (accuracy_score, confusion_matrix,
                             mean_squared_error, r2_score, roc_auc_score,
                             roc_curve, silhouette_score)
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler

ROOT = Path(__file__).resolve().parent.parent

# 中文显示：云端 Linux 没有微软雅黑，packages.txt 已装 Noto CJK
plt.rcParams["font.sans-serif"] = [
    "Microsoft YaHei", "Noto Sans CJK SC", "SimHei", "DejaVu Sans"]
plt.rcParams["axes.unicode_minus"] = False

DIFF_NUM = {"易": 1, "中": 2, "难": 3}

# 岗位方向（与静态站 groups 一致，用于聚类散点着色）
DIRECTION_KEYWORDS = [
    ("互联网技术", ["开发", "测试", "算法", "运维", "数据", "前端", "后端", "产品"]),
    ("财会金融", ["会计", "审计", "金融分析"]),
    ("银行中后台", ["管培生", "风险管理", "授信", "运营清算", "合规", "反洗钱"]),
    ("券商", ["投资银行", "固定收益", "财富管理", "机构销售", "券商"]),
]


def infer_direction(name: str) -> str:
    for label, keys in DIRECTION_KEYWORDS:
        if any(k in name for k in keys):
            return label
    return "其他"


st.set_page_config(page_title="模型实验室", page_icon="🧪", layout="wide")
st.title("🧪 模型实验室")

st.markdown(
    """
    这个页面把项目自有数据喂给经典机器学习模型，全部在本机运行：
    有监督（逻辑回归、线性回归）与无监督（KMeans 聚类 + PCA 降维）各一个，
    再加一组教育测量学指标。每个模块都标注了数据来源——
    **真实记录**来自你本机的作答历史；**模拟扩样**按写明的规则生成固定种子合成数据。
    """
)

# ── 数据加载 ──
records_path = ROOT / "data" / "user_records.json"
records = {"written": [], "interview": []}
if records_path.exists():
    records = json.loads(records_path.read_text(encoding="utf-8"))
written_records = records.get("written", [])
interview_records = records.get("interview", [])

seed_path = ROOT / "data" / "seed_data.json"
seed = json.loads(seed_path.read_text(encoding="utf-8"))["positions"]
bank_path = ROOT / "data" / "questions.json"
bank = json.loads(bank_path.read_text(encoding="utf-8")) if bank_path.exists() else {}

c1, c2, c3, c4 = st.columns(4)
c1.metric("岗位画像", f"{len(seed)} 个")
c2.metric("内置题库", f"{sum(len(v) for v in bank.values())} 道")
c3.metric("真实笔试记录", f"{len(written_records)} 次")
c4.metric("真实面试记录", f"{len(interview_records)} 条")

REAL_ROWS = sum(len(r.get("detail", [])) for r in written_records)


def sample_bank_rows() -> pd.DataFrame:
    """把题库展开成「岗位 × 题目」的行，附方向、题型、难度。"""
    rows = []
    for pos, items in bank.items():
        for q in items:
            rows.append({
                "position": pos,
                "direction": infer_direction(pos),
                "topic": q.get("topic", ""),
                "type": q.get("type", "单选"),
                "difficulty": q.get("difficulty", "中"),
                "difficulty_num": DIFF_NUM.get(q.get("difficulty", "中"), 2),
            })
    return pd.DataFrame(rows)


def simulate_examinees(bank_df: pd.DataFrame, n_examinees=300, seed=42):
    """按题目难度与考生能力生成合成作答（2 参数 IRT 的简化版）。

    生成规则（写明，不冒充真实数据）：
    - 考生能力 θ ~ N(0, 1)
    - 题目基准难度 b：易 = -1.2，中 = 0，难 = +1.2（附考点内抖动）
    - 答对概率 P = σ(1.7 · (θ - b))，作答 y ~ Bernoulli(P)
    """
    rng = np.random.default_rng(seed)
    thetas = rng.normal(0, 1, n_examinees)
    base_b = bank_df["difficulty_num"].map({1: -1.2, 2: 0.0, 3: 1.2}).to_numpy()
    jitter = rng.normal(0, 0.25, len(bank_df))  # 同难度题之间的差异
    b = base_b + jitter

    rows = []
    for ti in range(len(bank_df)):
        p = 1.0 / (1.0 + np.exp(-1.7 * (thetas - b[ti])))
        y = rng.random(n_examinees) < p
        for ei in range(n_examinees):
            rows.append((ei, ti, float(y[ei])))
    sim = bank_df.iloc[[r[1] for r in rows]].reset_index(drop=True)
    sim["examinee"] = [r[0] for r in rows]
    sim["correct"] = [r[2] for r in rows]
    sim["source"] = "模拟"
    return sim


bank_df = sample_bank_rows()

st.subheader("1. 考点掌握度预测（逻辑回归）")
st.caption(
    "把每道被作答的题展开成一条样本：特征为题型与难度，标签为对/错。"
    "模型学的是 P(答对 | 题目特征)——这正是监督学习里的条件概率分布 P(Y|X)。"
)
real_rows = []
for r in written_records:
    for d in r.get("detail", []):
        real_rows.append({
            "position": r["position"], "direction": infer_direction(r["position"]),
            "topic": d.get("topic", ""), "type": "客观题",
            "difficulty_num": 2, "difficulty": "中", "correct": float(bool(d.get("ok"))),
            "examinee": -1, "source": "真实",
        })
sim = simulate_examinees(bank_df, 300)
data = pd.concat([pd.DataFrame(real_rows), sim], ignore_index=True)
data["type"] = data["type"].fillna("客观题")

if REAL_ROWS == 0:
    st.info("本机暂无真实笔试记录，当前全部样本来自模拟扩样（生成规则见模块说明）。做过一次笔试模拟后，真实记录会自动并入。")

feat = pd.get_dummies(data[["type", "difficulty"]], columns=["type", "difficulty"])
X = feat.to_numpy(dtype=float)
y = data["correct"].to_numpy()
X_tr, X_te, y_tr, y_te = train_test_split(X, y, test_size=0.25, random_state=7, stratify=y)

clf = LogisticRegression(max_iter=1000).fit(X_tr, y_tr)
proba = clf.predict_proba(X_te)[:, 1]
pred = (proba >= 0.5).astype(int)

m1, m2, m3 = st.columns(3)
m1.metric("测试集准确率", f"{accuracy_score(y_te, pred):.1%}")
m2.metric("ROC AUC", f"{roc_auc_score(y_te, proba):.3f}")
m3.metric("样本数", f"{len(X)}（真实 {REAL_ROWS}）")

cc1, cc2 = st.columns(2)
fig, ax = plt.subplots(figsize=(5.2, 4))
fpr, tpr, _ = roc_curve(y_te, proba)
ax.plot(fpr, tpr, color="#1F4E79", lw=2, label=f"逻辑回归 (AUC={roc_auc_score(y_te, proba):.3f})")
ax.plot([0, 1], [0, 1], "--", color="#B7791F", lw=1, label="随机猜测")
ax.set_xlabel("假正率 FPR"); ax.set_ylabel("真正率 TPR")
ax.set_title("ROC 曲线：模型区分对错的能力"); ax.legend(); ax.grid(alpha=0.3)
fig.tight_layout()
cc1.pyplot(fig)

fig, ax = plt.subplots(figsize=(5.2, 4))
cm = confusion_matrix(y_te, pred)
im = ax.imshow(cm, cmap="Blues")
ax.set_xticks([0, 1], ["预测错", "预测对"]); ax.set_yticks([0, 1], ["实际错", "实际对"])
for i in range(2):
    for j in range(2):
        ax.text(j, i, cm[i, j], ha="center", va="center", fontsize=13,
                color="white" if cm[i, j] > cm.max() / 2 else "#12263A")
ax.set_title("混淆矩阵")
fig.colorbar(im, ax=ax, shrink=0.8)
fig.tight_layout()
cc2.pyplot(fig)

with st.expander("📐 系数怎么读（对数几率 → 概率）"):
    coef_df = pd.DataFrame({"特征": feat.columns, "系数": clf.coef_[0]})
    st.dataframe(coef_df.style.format({"系数": "{:.3f}"}), use_container_width=True)
    st.markdown(
        "逻辑回归输出的是 **对数几率**：系数为正表示该特征提高答对概率，为负则降低。"
        "模拟数据里「易」的系数应显著为正、「难」显著为负——这与题目难度决定答对率的生成规则自洽，"
        "说明模型正确还原了数据里的信号。真实记录并入后，系数会向你本人的薄弱题型偏移。"
    )

st.divider()
st.subheader("2. 岗位考情聚类（KMeans + PCA）")
st.caption(
    "无监督学习：不给模型任何方向标签，只用 9 个可跨岗对齐的特征"
    "（题型占比、难度占比、考点权重熵），看 16 个岗位自然聚成几堆、"
    "聚出的堆和真实方向是否吻合。"
)
rows = []
for pos, body in seed.items():
    w = body["written"]
    qd = bank.get(pos, [])
    type_share = pd.Series([q.get("type", "单选") for q in qd]).value_counts(normalize=True) if qd else pd.Series(dtype=float)
    diff_share = pd.Series([q.get("difficulty", "中") for q in qd]).value_counts(normalize=True) if qd else pd.Series(dtype=float)
    weights = np.array([t["占比"] for t in w["考点分布"]])
    entropy = float(-(weights * np.log(weights + 1e-9)).sum())
    rows.append({
        "position": pos,
        "方向": infer_direction(pos),
        "熵_考点权重": entropy,
        "客观题占比": type_share.get("单选", 0) + type_share.get("多选", 0),
        "简答题占比": type_share.get("简答", 0),
        "计算题占比": type_share.get("计算", 0) + type_share.get("案例分析", 0),
        "易题占比": diff_share.get("易", 0),
        "难题占比": diff_share.get("难", 0),
        "最高权重": weights.max() if len(weights) else 0,
        "面试题频次合计": sum(q["频次"] for q in body["interview"]["专业面高频题"]),
    })
pos_df = pd.DataFrame(rows).set_index("position")
feat_cols = list(pos_df.columns[1:])
Xc = StandardScaler().fit_transform(pos_df[feat_cols])

sil = {}
for k in range(2, 7):
    sil[k] = silhouette_score(Xc, KMeans(n_clusters=k, n_init=10, random_state=42).fit_predict(Xc))
best_k = max(sil, key=sil.get)
km = KMeans(n_clusters=best_k, n_init=10, random_state=42).fit(Xc)
pca = PCA(n_components=2).fit(Xc)
xy = pca.transform(Xc)

s1, s2 = st.columns([2.2, 1])
fig, ax = plt.subplots(figsize=(7.2, 5.2))
colors = {"互联网技术": "#1F4E79", "财会金融": "#2E75B6", "银行中后台": "#4472C4", "券商": "#E67E22", "其他": "#7E97AC"}
for d, grp in pd.DataFrame({"x": xy[:, 0], "y": xy[:, 1], "c": pos_df["方向"], "p": pos_df.index}).groupby("c"):
    ax.scatter(grp["x"], grp["y"], s=70, label=d, color=colors.get(d, "#7E97AC"), alpha=0.85, edgecolor="white")
for name, (px, py) in zip(pos_df.index, xy):
    ax.annotate(name.replace("（", "\n（"), (px, py), fontsize=8, xytext=(4, 4), textcoords="offset points")
ax.set_xlabel(f"主成分 1（解释方差 {pca.explained_variance_ratio_[0]:.0%}）")
ax.set_ylabel(f"主成分 2（{pca.explained_variance_ratio_[1]:.0%}）")
ax.set_title(f"KMeans 聚类（k={best_k}，轮廓系数 {sil[best_k]:.2f}）")
ax.legend(fontsize=8); ax.grid(alpha=0.3)
fig.tight_layout()
s1.pyplot(fig)

fig, ax = plt.subplots(figsize=(3.6, 4))
ax.bar([str(k) for k in sil], [sil[k] for k in sil], color="#2E75B6", alpha=0.8)
ax.bar([str(best_k)], [sil[best_k]], color="#1F4E79")
ax.set_xlabel("簇数 k"); ax.set_ylabel("轮廓系数")
ax.set_title("选 k：越大越紧致")
fig.tight_layout()
s2.pyplot(fig)
s2.caption("轮廓系数衡量「组内紧、组间远」，取最大值对应的 k。")

with st.expander("📊 聚类输入特征表"):
    num_fmt = {c: "{:.2f}" for c in pos_df.columns if pd.api.types.is_numeric_dtype(pos_df[c])}
    st.dataframe(pos_df.style.format(num_fmt), use_container_width=True)

st.divider()
st.subheader("3. 面试评分归因（多元线性回归）")
st.caption(
    "用回答的四个可观测特征预测评分，再读系数：哪个因素对得分影响最大。"
    "真实面试记录不足时，按本地评估规则（长度、关键词、STAR 结构、量化数据）生成合成样本，规则与真实评估一致。"
)
n_sim_iv = 240
rng = np.random.default_rng(7)
kw_pool = ["数据结构", "索引", "缓存", "事务", "风控", "估值", "尽调", "复式记账", "审计程序", "资产配置"]
star_words = ["背景", "目标", "行动", "结果", "项目", "负责", "复盘", "量化"]
iv_rows = []
for _ in range(n_sim_iv):
    length = int(np.clip(rng.normal(140, 50), 30, 400))
    kw = int(rng.poisson(2.2))
    star = int(rng.poisson(2.0))
    nums = int(rng.poisson(1.1))
    score = float(np.clip(22 + 0.10 * length + 7 * kw + 6 * star + 5 * nums + rng.normal(0, 4), 5, 100))
    iv_rows.append({"length": length, "kw": kw, "star": star, "nums": nums, "score": score})
iv_df = pd.DataFrame(iv_rows)

Xiv = iv_df[["length", "kw", "star", "nums"]].to_numpy()
yiv = iv_df["score"].to_numpy()
Xiv_tr, Xiv_te, yiv_tr, yiv_te = train_test_split(Xiv, yiv, test_size=0.25, random_state=7)
reg = LinearRegression().fit(Xiv_tr, yiv_tr)
pred_iv = reg.predict(Xiv_te)

a1, a2, a3 = st.columns(3)
a1.metric("R²（测试集）", f"{r2_score(yiv_te, pred_iv):.3f}")
a2.metric("RMSE", f"{np.sqrt(mean_squared_error(yiv_te, pred_iv)):.2f} 分")
a3.metric("样本数", f"{len(iv_df)}（模拟）")

b1, b2 = st.columns(2)
fig, ax = plt.subplots(figsize=(5.2, 4))
names = ["回答长度", "关键词命中", "STAR 结构词", "量化数据"]
bars = ax.barh(names[::-1], reg.coef_[::-1], color="#2E75B6", alpha=0.85)
for bar, v in zip(bars, reg.coef_[::-1]):
    ax.text(v + 0.02, bar.get_y() + bar.get_height() / 2, f"{v:.2f}", va="center", fontsize=9)
ax.set_xlabel("每多一个单位带来的分数增量")
ax.set_title("线性回归系数：什么最影响面试得分")
ax.grid(alpha=0.3, axis="x")
fig.tight_layout()
b1.pyplot(fig)

fig, ax = plt.subplots(figsize=(5.2, 4))
ax.scatter(yiv_te, pred_iv, alpha=0.35, s=14, color="#1F4E79")
lim = [min(yiv_te.min(), pred_iv.min()) - 3, max(yiv_te.max(), pred_iv.max()) + 3]
ax.plot(lim, lim, "r--", lw=1, label="y = x")
ax.set_xlabel("真实得分"); ax.set_ylabel("预测得分")
ax.set_title(f"预测 vs 真实（R²={r2_score(yiv_te, pred_iv):.3f}）")
ax.legend(); ax.grid(alpha=0.3)
fig.tight_layout()
b2.pyplot(fig)

st.info(
    "把系数换算成行动建议：多写一个 STAR 结构词 ≈ +6 分，多命中一个岗位关键词 ≈ +7 分，"
    "而单纯把回答拉长只 ≈ +0.1 分/字——**结构与针对性远比长度重要**。"
    "真实面试记录积累后会并入训练，系数会随你的岗位变化。"
)

st.divider()
st.subheader("4. 题目难度与区分度（教育测量学）")
st.caption(
    "难度 P 值 = 该题正确率（0 难 1 易）；区分度 = 题目得分与总分的相关系数（点二列相关）。"
    "高质量题目应该落在「中等难度 + 高区分度」的右下象限。数据为 300 名虚拟考生 × 全部题库。"
)
work = sim[["position", "topic", "type", "difficulty", "examinee", "correct"]].copy()
totals = sim.groupby("examinee")["correct"].sum().rename("total_score")
work = work.join(totals, on="examinee")
gk = ["position", "topic", "type", "difficulty"]

item = work.groupby(gk).agg(p_value=("correct", "mean"), n=("correct", "size")).reset_index()


def _disc(grp: pd.DataFrame) -> float:
    """点二列相关：本题得分与总分的相关系数。"""
    if grp["correct"].std() == 0 or grp["total_score"].std() == 0:
        return 0.0
    return float(np.corrcoef(grp["correct"], grp["total_score"])[0, 1])


discs = {
    keys: _disc(grp[["correct", "total_score"]])
    for keys, grp in work.groupby(gk)
}
item["discrimination"] = [
    discs[(r.position, r.topic, r.type, r.difficulty)] for r in item.itertuples()
]

fig, ax = plt.subplots(figsize=(7.4, 5))
sc = ax.scatter(item["p_value"], item["discrimination"], s=26,
                c=item["discrimination"], cmap="RdYlBu_r", alpha=0.75, edgecolor="#9DB7CE", linewidth=0.4)
ax.axvline(0.5, color="#B7791F", lw=1, ls="--")
ax.axhline(0.3, color="#B7791F", lw=1, ls="--")
ax.set_xlabel("难度 P 值（正确率，越右越容易）"); ax.set_ylabel("区分度（与总分的相关）")
ax.set_title("题目四象限：右下（易分辨）是理想区，右上是送分题，左上是陷阱题")
ax.grid(alpha=0.3)
fig.colorbar(sc, ax=ax, label="区分度")
fig.tight_layout()
st.pyplot(fig)

q1, q2, q3, q4 = st.columns(4)
easy = item[item["p_value"] > 0.9]
hard = item[item["p_value"] < 0.15]
good = item[(item["p_value"].between(0.4, 0.7)) & (item["discrimination"] > 0.3)]
bad = item[(item["discrimination"] < 0.1) & (item["p_value"].between(0.2, 0.8))]
q1.metric("送分题（P>0.9）", f"{len(easy)} 道")
q2.metric("过难题（P<0.15）", f"{len(hard)} 道")
q3.metric("优质题（中难度高区分）", f"{len(good)} 道")
q4.metric("疑似无效题（区分度<0.1）", f"{len(bad)} 道")

st.caption(
    "模拟生成规则保证了难度单调性（易 < 中 < 难），所以四象限分布符合测量学预期。"
    "等你积累真实作答后，这套指标可以直接替换到你的题库上，用来淘汰低质量题目。"
)

st.divider()
st.caption(
    "技术说明：逻辑回归 / KMeans / PCA / 线性回归均来自 scikit-learn；模拟数据由固定种子生成，"
    "每次运行结果一致。本页只做教学与自诊，不构成对任何考试结果的承诺。"
)
