# -*- coding: utf-8 -*-
"""模型评估工具：「评估四件套」拆成纯函数。

四件套 = 基准对比 → 混淆矩阵 → 精确率/召回率 → 信号质量（分层增益）。
这里不依赖 Streamlit，页面只负责展示，计算可在 tests 里直接断言。

数据口径与 pages/ml_lab.py 保持一致（同一套 IRT 模拟规则、同一种子、
同样的「题型 + 难度」特征），因此本模块评估的就是模型实验室里的那个模型。
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import confusion_matrix
from sklearn.model_selection import GroupShuffleSplit, train_test_split

DIFF_NUM = {"易": 1, "中": 2, "难": 3}
DIFF_B = {1: -1.2, 2: 0.0, 3: 1.2}  # IRT 基准难度
DISC = 1.7                          # 区分度


def expand_bank(bank: dict) -> pd.DataFrame:
    """题库 ``{岗位: [题, ...]}`` → 一行一题，附难度数值。"""
    rows = []
    for pos, items in bank.items():
        for q in items:
            diff = q.get("difficulty", "中")
            rows.append({
                "position": pos,
                "topic": q.get("topic", ""),
                "type": q.get("type", "单选"),
                "difficulty": diff,
                "difficulty_num": DIFF_NUM.get(diff, 2),
            })
    return pd.DataFrame(rows)


def simulate_examinees(bank_df: pd.DataFrame, n_examinees: int = 300,
                       seed: int = 42) -> pd.DataFrame:
    """2 参数 IRT 简化版：θ ~ N(0,1)，P(答对) = σ(1.7·(θ − b))。

    与 pages/ml_lab.py 同一规则、同一种子 —— 两页看到的是同一份模拟数据。
    """
    rng = np.random.default_rng(seed)
    thetas = rng.normal(0, 1, n_examinees)
    b = (bank_df["difficulty_num"].map(DIFF_B).to_numpy()
         + rng.normal(0, 0.25, len(bank_df)))
    rows = []
    for ti in range(len(bank_df)):
        p = 1.0 / (1.0 + np.exp(-DISC * (thetas - b[ti])))
        y = rng.random(n_examinees) < p
        for ei in range(n_examinees):
            rows.append((ei, ti, float(y[ei])))
    sim = bank_df.iloc[[r[1] for r in rows]].reset_index(drop=True)
    sim["examinee"] = [r[0] for r in rows]
    sim["correct"] = [r[2] for r in rows]
    sim["source"] = "模拟"
    return sim


def build_dataset(bank_df: pd.DataFrame, written_records=None) -> pd.DataFrame:
    """真实记录 + 模拟扩样，拼成一行一次作答。

    每次笔试算一个独立「考生」（1_000_000 + 序号），这样按考生分组切分时
    同一场笔试不会同时出现在训练集和测试集里。
    """
    frames = []
    real = []
    for i, rec in enumerate(written_records or []):
        for d in rec.get("detail", []):
            real.append({
                "position": rec.get("position", ""),
                "topic": d.get("topic", ""),
                "type": "客观题",
                "difficulty": "中",
                "difficulty_num": 2,
                "correct": float(bool(d.get("ok"))),
                "examinee": 1_000_000 + i,
                "source": "真实",
            })
    if real:
        frames.append(pd.DataFrame(real))
    frames.append(simulate_examinees(bank_df))

    data = pd.concat(frames, ignore_index=True)
    data["type"] = data["type"].fillna("客观题")
    data["difficulty"] = data["difficulty"].fillna("中")
    return data


def make_features(data: pd.DataFrame):
    """题型与难度转哑变量（与 ml_lab 同一套特征）。"""
    feat = pd.get_dummies(data[["type", "difficulty"]], columns=["type", "difficulty"])
    return feat.to_numpy(dtype=float), list(feat.columns)


def split_dataset(X, y, groups, test_size=0.25, seed=7, by_group=True):
    """切分数据。

    by_group=True：按考生分组切，同一考生的所有作答只落在一边（防「抄自己」）；
    by_group=False：随机打乱切，仅用于对照实验，观察泄漏有多大。
    """
    if by_group:
        splitter = GroupShuffleSplit(n_splits=1, test_size=test_size,
                                     random_state=seed)
        return next(splitter.split(X, y, groups=groups))
    return train_test_split(np.arange(len(y)), test_size=test_size,
                            random_state=seed, stratify=y)


def fit_logistic(X_tr, y_tr, X_te):
    """训练逻辑回归并返回测试集 P(答对)。"""
    clf = LogisticRegression(max_iter=1000).fit(X_tr, y_tr)
    return clf, clf.predict_proba(X_te)[:, 1]


def baseline_scores(y_tr, y_te, diff_tr, diff_te):
    """三条基线：多数类、随机猜、只按难度猜。

    返回 ``(dict[名称 -> 准确率], 多数类标签)``。任何模型都必须先超过第一条，
    否则「准确率 71%」只是个脱离语境的数字。
    """
    majority = int(round(float(np.mean(y_tr))))
    word = "答对" if majority == 1 else "答错"
    out = {f"多数类（永远猜“{word}”）": float(np.mean(y_te == majority))}
    out["随机猜（抛硬币）"] = 0.5
    rule = LogisticRegression(max_iter=1000).fit(
        np.asarray(diff_tr, dtype=float).reshape(-1, 1), y_tr)
    pred = rule.predict(np.asarray(diff_te, dtype=float).reshape(-1, 1))
    out["只按难度猜"] = float(np.mean(pred == y_te))
    return out, majority


def threshold_metrics(y, proba, thr: float = 0.5) -> dict:
    """给定阈值算混淆矩阵与四项指标。

    正类 = 「答对」。因此
    - FP = 模型说会、实际做错 → 假安全（最贵的一格）
    - FN = 模型说危险、实际会做 → 白复习（次贵）
    - 精确率 = 放行可信度；召回率 = 会做的题被正确放行的比例
    """
    y = np.asarray(y, dtype=int)
    pred = (np.asarray(proba) >= thr).astype(int)
    tn, fp, fn, tp = confusion_matrix(y, pred, labels=[0, 1]).ravel()
    prec = tp / (tp + fp) if tp + fp else 0.0
    rec = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2 * prec * rec / (prec + rec) if prec + rec else 0.0
    return {
        "pred": pred,
        "tn": int(tn), "fp": int(fp), "fn": int(fn), "tp": int(tp),
        "acc": float((tp + tn) / len(y)),
        "precision": float(prec), "recall": float(rec), "f1": float(f1),
    }


def lift_table(y, proba, bins: int = 5) -> pd.DataFrame:
    """分层增益：按预测 P(答对) 从低到高分档，看每档的实际错误率。

    档1 = 模型最不看好的那批题（风险最高）。若错误率随档位单调下降，
    说明模型的排序能力真实存在 —— 这就是「信号质量」，比单一准确率更抗质疑。
    """
    y = np.asarray(y, dtype=int)
    proba = np.asarray(proba, dtype=float)
    order = np.argsort(proba, kind="mergesort")
    rows = []
    for i, chunk in enumerate(np.array_split(order, bins), start=1):
        rows.append({
            "档位": f"档{i}",
            "样本数": int(len(chunk)),
            "平均预测 P(答对)": float(np.mean(proba[chunk])),
            "实际错误率": float(1.0 - np.mean(y[chunk])),
        })
    return pd.DataFrame(rows)
