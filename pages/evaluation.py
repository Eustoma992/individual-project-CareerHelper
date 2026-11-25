# -*- coding: utf-8 -*-
"""模型体检：用 W12 第 7 幕的「评估四件套」审计本项目的预测模型。

五段式：
① 基线榜 —— 先超过「永远猜答对」，才有资格谈准确率
② 混淆矩阵 —— 标出最贵的一格（假安全）
③ 阈值取舍 —— 拉阈值看精确率/召回率怎么此消彼长
④ 分层增益 —— 按预测风险分档，看实际错误率是否单调（信号质量）
⑤ 诚实声明 —— 样本从哪来、切分怎么切、结论能说到哪一步

评估回答的不是「模型多准」，而是「它给你的建议能不能照着做」。
"""
import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import streamlit as st
from sklearn.metrics import precision_recall_curve, roc_auc_score

from modules import model_eval as me

ROOT = Path(__file__).resolve().parent.parent

plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "Noto Sans CJK SC",
                                   "SimHei", "DejaVu Sans"]
plt.rcParams["axes.unicode_minus"] = False

NAVY = "#1F4E79"
RED = "#B03A2E"
AMBER = "#8A6D1F"
GRAY = "#93A5B6"
BLUE_RAMP = ["#123A5E", "#1F4E79", "#3E7CB1", "#7FA8C9", "#BBD0E0"]

st.set_page_config(page_title="模型体检", page_icon="🧾", layout="wide")
st.title("🧾 模型体检 · 评估四件套")
st.caption(
    "基准对比 → 混淆矩阵 → 精确率/召回率 → 分层增益。"
    "这一页检查的是「模型实验室」里那个逻辑回归掌握度模型：同一份数据、同一套特征，"
    "但切分口径更严格（按考生分组），数字可能与模型实验室略有差异。"
    "判断标准不是分数漂亮，而是结论敢不敢拿去指导学生。"
)


@st.cache_data(show_spinner="正在训练并评估模型…")
def prepare():
    """一次算好：数据、特征、两种切分、模型、测试集概率与曲线。"""
    bank_path = ROOT / "data" / "questions.json"
    rec_path = ROOT / "data" / "user_records.json"

    bank = json.loads(bank_path.read_text(encoding="utf-8")) if bank_path.exists() else {}
    records = (json.loads(rec_path.read_text(encoding="utf-8"))
               if rec_path.exists() else {"written": []})

    bank_df = me.expand_bank(bank)
    data = me.build_dataset(bank_df, records.get("written", []))

    X, cols = me.make_features(data)
    y = data["correct"].to_numpy().astype(int)
    groups = data["examinee"].to_numpy()
    diff = data["difficulty_num"].to_numpy(dtype=float)

    # 主口径：按考生分组切分（同一考生的题只落在一边）
    tr, te = me.split_dataset(X, y, groups, by_group=True)
    clf, proba = me.fit_logistic(X[tr], y[tr], X[te])
    y_te = y[te]
    baselines, majority = me.baseline_scores(y[tr], y_te, diff[tr], diff[te])
    acc = float(np.mean((proba >= 0.5).astype(int) == y_te))

    # 对照：随机切分，看看「抄自己」能虚高多少
    tr_r, te_r = me.split_dataset(X, y, groups, by_group=False)
    _, proba_r = me.fit_logistic(X[tr_r], y[tr_r], X[te_r])
    acc_rand = float(np.mean((proba_r >= 0.5).astype(int) == y[te_r]))

    prec_c, rec_c, _ = precision_recall_curve(y_te, proba)

    return {
        "y_te": y_te, "proba": proba,
        "baselines": baselines, "majority": majority,
        "acc": acc, "acc_rand": acc_rand,
        "auc": float(roc_auc_score(y_te, proba)),
        "pr_prec": prec_c, "pr_rec": rec_c,
        "n_total": int(len(y)), "n_test": int(len(y_te)),
        "n_real": int((data["source"] == "真实").sum()),
        "n_sim": int((data["source"] == "模拟").sum()),
        "n_positions": int(data["position"].nunique()),
        "n_examinees": int(np.unique(groups).size),
        "n_features": int(len(cols)),
        "pos_rate": float(y.mean()),
        "coef_names": cols,
        "coef": [float(c) for c in clf.coef_[0]],
    }


meta = prepare()
y_te = meta["y_te"]
proba = meta["proba"]
base_rows = list(meta["baselines"].items())
base_majority = base_rows[0][1]

# ── 页头指标 ──
k1, k2, k3, k4 = st.columns(4)
k1.metric("建模样本", f"{meta['n_total']:,} 条")
k2.metric("测试样本", f"{meta['n_test']:,} 条",
          help="按考生分组切分，占总样本 25%")
k3.metric("模型准确率", f"{meta['acc']:.1%}",
          delta=f"{meta['acc'] - base_majority:+.1%} vs 基准")
k4.metric("考生 / 岗位", f"{meta['n_examinees']:,} / {meta['n_positions']}")

st.divider()

# ─────────────────────────── ① 基线榜 ───────────────────────────
st.subheader("① 基线榜：先过线，再谈准确率")
st.caption(
    "「准确率 71%」单独看毫无意义——如果永远猜「答对」就有 62%，那 71% 只值 9 个点。"
    "任何模型都必须先打败基线，否则它只是在猜多数派。"
)

rows = []
for name, value in base_rows:
    rows.append({
        "选手": name,
        "测试准确率": f"{value:.1%}",
        "vs 多数类": "基准" if name.startswith("多数类") else f"{value - base_majority:+.1%}",
        "判定": "—" if name.startswith("多数类") else ("✓ 过线" if value > base_majority else "✗ 未过线"),
    })
rows.append({
    "选手": "逻辑回归（题型 + 难度）· 本项目模型",
    "测试准确率": f"{meta['acc']:.1%}",
    "vs 多数类": f"{meta['acc'] - base_majority:+.1%}",
    "判定": "✓ 过线" if meta["acc"] > base_majority else "✗ 未过线",
})
st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True)

gain_type = meta["acc"] - meta["baselines"]["只按难度猜"]
if gain_type < 0.01:
    st.markdown(
        f"**多看一个特征值不值？** 模型比「只按难度猜」只高 {gain_type:+.1%} —— "
        f"题型几乎没有带来增量，真正决定答对与否的是难度。"
        f"这不是坏消息：它说明该盯的是「当前水平够不够」，而不是纠结题型分布。"
        f"在模拟数据里这是必然结果，因为难度就是生成规则里唯一的自变量。"
    )
else:
    st.markdown(
        f"**多看一个特征值不值？** 模型比「只按难度猜」高 {gain_type:+.1%}，"
        f"题型确实补充了难度之外的信息，值得保留。"
    )

split_gap = meta["acc"] - meta["acc_rand"]
if abs(split_gap) < 0.005:
    split_note = (
        "切分对照：随机切分与按考生分组切分的准确率几乎一致"
        f"（{meta['acc_rand']:.1%} vs {meta['acc']:.1%}）。"
        "原因是特征里只有题型与难度，不含考生身份——暂时没有「抄自己」的通道。"
        "**一旦加入个人历史正确率这类特征，就必须改按考生分组切。**"
    )
else:
    split_note = (
        f"切分对照：随机切分 {meta['acc_rand']:.1%} 比按考生分组 {meta['acc']:.1%} "
        f"高 {split_gap:+.1%}。这部分差额来自「同一个考生的题同时进了训练和测试」，属于虚高。"
    )
st.info(split_note)

# ─────────────────────────── ② 混淆矩阵 ───────────────────────────
st.subheader("② 混淆矩阵：错在哪一格更贵")
thr = st.slider(
    "判定阈值 —— 模型说「这题你会掌握」所需的最低概率",
    0.30, 0.90, 0.50, 0.05,
    help="门槛越高越保守：只有很有把握才放行，精确率上升、召回率下降。",
)
m = me.threshold_metrics(y_te, proba, thr)

left, right = st.columns([1.05, 1])

with left:
    cells = [
        (0, 1, m["tn"], "真会 · 判对", "#EEF3F8", "#334155"),
        (1, 1, m["fp"], "假安全 · 最贵", "#FBEAE8", RED),
        (0, 0, m["fn"], "会却判错 · 白复习", "#FDF3E3", AMBER),
        (1, 0, m["tp"], "真会 · 判会", "#E8F1F8", NAVY),
    ]
    fig, ax = plt.subplots(figsize=(4.8, 3.9))
    for x0, y0, val, label, face, edge in cells:
        ax.add_patch(plt.Rectangle((x0, y0), 1, 1, facecolor=face,
                                   edgecolor=edge, linewidth=1.4))
        ax.text(x0 + 0.5, y0 + 0.62, f"{val:,}", ha="center", va="center",
                fontsize=15, color=edge, fontweight="bold")
        ax.text(x0 + 0.5, y0 + 0.30, label, ha="center", va="center",
                fontsize=9.5, color=edge)
    ax.set_xlim(0, 2); ax.set_ylim(0, 2)
    ax.set_xticks([0.5, 1.5], ["预测：会错", "预测：会"])
    ax.set_yticks([0.5, 1.5], ["实际会", "实际会错"])
    ax.tick_params(length=0, labelsize=10)
    for spine in ax.spines.values():
        spine.set_visible(False)
    ax.set_title(f"混淆矩阵（阈值 {thr:.2f}，测试集 {meta['n_test']:,} 条）",
                 fontsize=11, color="#12263A")
    fig.tight_layout()
    st.pyplot(fig)
    plt.close(fig)

with right:
    st.markdown(
        f"""
        **正类 = 「答对」**，所以四个格子的价钱不一样：

        - **假安全 {m['fp']:,} 条**（说会、其实不会）：最贵。学生跳过这题，
          直到面试现场才发现不会，没有补救机会。
        - **白复习 {m['fn']:,} 条**（说危险、其实会做）：次贵。只是多花半小时
          重看一遍，属于可控浪费。
        - 正确放行 {m['tp']:,} 条、正确拦下 {m['tn']:,} 条。

        这就是**成本不对称**：宁可让他多复习，也不能让他误以为已经掌握。
        因此调阈值时应该偏向提高**精确率**，而不是召回率。
        """
    )
    st.caption(
        "对照股市：FP 是「假买入信号」，喊涨你买入、实际下跌；"
        "这里 FP 是「假放行信号」，说会你跳过、实际不会。代价方向完全一致。"
    )

# ─────────────────────────── ③ 阈值取舍 ───────────────────────────
st.subheader("③ 阈值取舍：一个阈值换一组代价")
c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("精确率", f"{m['precision']:.1%}", help="说「你会」的那些题里，真会的比例 —— 放行可信度")
c2.metric("召回率", f"{m['recall']:.1%}", help="真正会做的题里，被正确放行的比例")
c3.metric("F1", f"{m['f1']:.1%}", help="精确率与召回率的调和平均")
c4.metric("准确率", f"{m['acc']:.1%}")
c5.metric("ROC AUC", f"{meta['auc']:.3f}", help="整体排序能力，与阈值无关；模型实验室里报的就是它")

pl, pr = st.columns([1, 1.1])
with pl:
    fig, ax = plt.subplots(figsize=(4.8, 3.5))
    ax.plot(meta["pr_rec"], meta["pr_prec"], color=NAVY, lw=1.8, label="P-R 曲线")
    ax.scatter([m["recall"]], [m["precision"]], s=70, color=RED, zorder=3,
               label=f"当前阈值 {thr:.2f}")
    ax.axhline(meta["pos_rate"], ls="--", color=GRAY, lw=1,
               label=f"随机水平（正类占比 {meta['pos_rate']:.0%}）")
    ax.set_xlabel("召回率"); ax.set_ylabel("精确率")
    ax.set_xlim(0, 1); ax.set_ylim(0, 1.02)
    ax.set_title("阈值沿曲线滑动", fontsize=11, color="#12263A")
    ax.legend(fontsize=8, loc="lower left"); ax.grid(alpha=0.25)
    fig.tight_layout()
    st.pyplot(fig)
    plt.close(fig)

with pr:
    st.markdown(
        f"**这个阈值的人话版本**：在 {meta['n_test']:,} 条测试作答里，"
        f"会给出 **{m['fp']:,} 条错误的安全感**（说会、其实不会）"
        f"和 **{m['fn']:,} 条多余的焦虑**（说危险、其实会做）。"
    )
    st.markdown("**产品上的三档**（同一套模型，只是放行门槛不同）：")
    p1, p2, p3 = st.columns(3)
    p1.markdown("**严格 0.70**  \n假安全最少，但要多复习一批本来会的题")
    p2.markdown("**标准 0.50**  \n默认口径，两边折中")
    p3.markdown("**宽松 0.35**  \n几乎全放行，误拦少，假安全明显增多")
    st.caption(
        "和 W12 案例里「拉 K 看指标变化」是同一个动作："
        "那边调邻居数，这边调放行门槛，目的都是让用户在曲线上自己选一个可接受的代价。"
    )

# ─────────────────────────── ④ 分层增益 ───────────────────────────
st.subheader("④ 分层增益：信号是真的还是噪声")
st.caption(
    "把测试集按预测 P(答对) 从低到高分 5 档，再看每档的实际错误率。"
    "如果档位越靠后错误率越低、且大致单调，说明模型的排序能力真实存在——"
    "这比单一准确率更难被质疑。"
)

lift = me.lift_table(y_te, proba, bins=5)
spread = float(lift["实际错误率"].iloc[0] - lift["实际错误率"].iloc[-1])

fig, ax = plt.subplots(figsize=(8.4, 3.4))
bars = ax.bar(lift["档位"], lift["实际错误率"],
              color=BLUE_RAMP[:len(lift)], width=0.58)
for bar, v in zip(bars, lift["实际错误率"]):
    ax.text(bar.get_x() + bar.get_width() / 2, v + 0.012, f"{v:.0%}",
            ha="center", va="bottom", fontsize=10, color="#12263A")
ax.axhline(1 - meta["pos_rate"], ls="--", color=GRAY, lw=1,
           label=f"整体错误率 {1 - meta['pos_rate']:.0%}")
ax.set_ylabel("实际错误率")
ax.set_xlabel("按预测 P(答对) 分档　→　越靠右，模型越看好")
ax.set_ylim(0, max(lift["实际错误率"]) * 1.28)
ax.set_title("档1 风险最高，档5 最稳", fontsize=11, color="#12263A")
ax.legend(fontsize=9); ax.grid(alpha=0.25, axis="y")
fig.tight_layout()
st.pyplot(fig)
plt.close(fig)

lc1, lc2 = st.columns([1, 1.5])
with lc1:
    st.metric("分层差（档1 − 档5）", f"{spread:.1%}",
              help="最高风险档与最低风险档的错误率之差，越大说明区分能力越强")
with lc2:
    monotone = lift["实际错误率"].is_monotonic_decreasing
    if spread > 0.15 and monotone:
        msg = ("五档错误率**严格单调下降**，分层差 {:.1%}——信号真实存在，"
               "模型的排序可以直接用来排复习优先级。").format(spread)
    elif spread > 0.05:
        msg = ("档位大体上随预测走低，但不够干净（分层差 {:.1%}）。"
               "可以用来排序，但不适合当作硬性结论。").format(spread)
    else:
        msg = ("各档错误率差别很小（分层差 {:.1%}），说明模型基本没排出有效顺序——"
               "这种情况下准确率再高也是运气。").format(spread)
    st.markdown(msg)
    st.caption(
        "读法同 W12 的「多空差」：预测涨的日子实际收益率是否高于预测跌的日子。"
        "这里换成「模型说不行的题，实际错误率是否真的更高」。"
    )

show = lift.copy()
show["平均预测 P(答对)"] = show["平均预测 P(答对)"].map(lambda v: f"{v:.1%}")
show["实际错误率"] = show["实际错误率"].map(lambda v: f"{v:.1%}")
show["样本数"] = show["样本数"].map(lambda v: f"{v:,}")
st.dataframe(show, hide_index=True, use_container_width=True)

# ─────────────────────────── ⑤ 诚实声明 ───────────────────────────
st.subheader("⑤ 诚实声明：结论能说到哪一步")

gap = meta["acc"] - base_majority
if gap >= 0.02:
    verdict = (f"模型比多数类基准高 {gap:.1%}，说明题型与难度里确实有可学信号，"
               f"排序能力也可用于安排复习优先级。")
elif gap > 0:
    verdict = (f"只比多数类基准高 {gap:.1%}，优势很薄，不足以支撑强结论，"
               f"更适合当作辅助参考。")
else:
    verdict = (f"准确率比多数类基准低 {abs(gap):.1%}，当前设定下未见稳定边际。"
               f"这也是一个合格的结论——不装作有效，比虚报分数更有用。")

if meta["n_real"] == 0:
    data_note = (
        "样本 100% 来自 IRT 模拟。模拟的生成规则里「难度」是决定答对率的唯一变量，"
        "而模型的特征恰好就是难度 —— 所以上面的分数属于**自证**：模型在还原我们自己写下的规则，"
        "不代表真实考场上也有这个水平。真实记录并入后必须重跑本页。"
    )
else:
    data_note = (
        f"真实记录 {meta['n_real']:,} 条、模拟扩样 {meta['n_sim']:,} 条。"
        f"模拟部分权重更高，解读时以真实记录的表现和分层趋势为准。"
    )

st.warning(
    f"""
**结论**　{verdict}

**数据**　{data_note}

**切分**　按考生分组切分（{meta['n_examinees']:,} 个考生），同一考生的题不会同时出现在
训练集与测试集；随机切分的对照结果见第 ① 段。

**局限**　特征只有题型与难度，没有个人历史；加入个人历史后，样本量与切分纪律都要重新检查，
否则最容易出现的不是「模型不准」，而是「模型很准但只在训练集里准」。
"""
)

with st.expander("📐 这五段和 W12 第 7 幕的对应关系"):
    st.markdown(
        """
| W12 第 7 幕 | 这一页 | 差别 |
|---|---|---|
| 多数类基准 | ① 基线榜（含多数类、随机、只按难度） | 多两条基线：随机与单特征规则 |
| 混淆矩阵，FP 最贵 | ② 混淆矩阵，FP 标「假安全」 | 成本方向一致：假信号最贵 |
| 精确率 / 召回率 / F1 | ③ 阈值取舍 + P-R 曲线 | 多了产品三档的落地建议 |
| 信号质量（多空差） | ④ 分层增益（档1 与档5 的错误率差） | 股票看收益差，这里看错误率差 |
| 时间切分防泄漏 | 按考生分组切分 | 时间序列怕「昨天的自己」，人怕「同一个考生」 |
| 诚实报告「差的结果也是结果」 | ⑤ 诚实声明 | 写明模拟数据是自证 |
        """
    )
    st.caption(
        "W12 原案例：`C:/数据分析与可视化/w12/KNN for stock prediction.ipynb` 第 7 幕。"
    )
