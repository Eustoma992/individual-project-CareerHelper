# -*- coding: utf-8 -*-
"""冒烟测试：种子数据完整性 + 四个页面可正常渲染（不需要真实 API Key）。"""
import pathlib

import pytest
from streamlit.testing.v1 import AppTest

ROOT = pathlib.Path(__file__).resolve().parent.parent


def _positions():
    import json

    with open(ROOT / "data" / "seed_data.json", encoding="utf-8") as f:
        return json.load(f)["positions"]


def test_seed_data_schema():
    """每个岗位的统计口径必须自洽：占比合计为 1，题量、题目数、关键词齐备。"""
    positions = _positions()
    assert len(positions) >= 16

    for name, body in positions.items():
        written, interview = body["written"], body["interview"]
        assert abs(sum(t["占比"] for t in written["考点分布"]) - 1.0) < 0.01, name
        assert abs(sum(written["题型分布"].values()) - 1.0) < 0.01, name
        assert len(written["面经关键词"]) >= 10, name
        assert len(interview["专业面高频题"]) >= 5, name
        assert len(interview["行为面高频题"]) >= 3, name
        assert set(interview["轮次重点"]) == {"初面", "复面", "终面"}, name
        # 高频题按频次降序，图表才有意义
        freqs = [q["频次"] for q in interview["专业面高频题"]]
        assert freqs == sorted(freqs, reverse=True), name


@pytest.mark.parametrize("page", ["pages/dashboard.py", "pages/written.py",
                                 "pages/interview.py", "pages/profile.py",
                                 "pages/ml_lab.py", "pages/evaluation.py"])
def test_pages_render(page):
    """五个页面在无 API Key、无历史记录时也应正常渲染。"""
    at = AppTest.from_file(str(ROOT / page), default_timeout=120).run()
    assert not at.exception, [e.message for e in at.exception]


def test_dashboard_position_switching():
    """看板切换岗位后不应抛异常（覆盖全部岗位）。"""
    at = AppTest.from_file(str(ROOT / "pages/dashboard.py"), default_timeout=90).run()
    for name in _positions():
        at.selectbox[0].set_value(name).run()
        assert not at.exception, name


def test_ai_without_key_raises_friendly_error():
    """未配置 Key 时，AI 调用应给出可操作的提示而非 401。"""
    from modules import ai_service

    with pytest.raises(RuntimeError, match="DEEPSEEK_API_KEY"):
        ai_service.chat([{"role": "user", "content": "ping"}])


def test_group_split_keeps_examinee_together():
    """按考生分组切分时，同一考生不能同时出现在训练集与测试集。"""
    import numpy as np

    from modules import model_eval as me

    X = np.zeros((20, 2))
    y = np.array([0, 1] * 10)
    groups = np.repeat(np.arange(4), 5)
    tr, te = me.split_dataset(X, y, groups, by_group=True, seed=3)
    assert not set(groups[tr]) & set(groups[te])
    assert len(tr) + len(te) == 20


def test_threshold_metrics_consistency():
    """混淆矩阵四格相加等于样本数，精确率/召回率落在 [0,1]。"""
    import numpy as np

    from modules import model_eval as me

    rng = np.random.default_rng(0)
    y = rng.integers(0, 2, 400)
    proba = np.clip(0.5 + 0.5 * (y - 0.5) + rng.normal(0, 0.15, 400), 0, 1)
    m = me.threshold_metrics(y, proba, 0.5)
    assert m["tn"] + m["fp"] + m["fn"] + m["tp"] == 400
    assert 0 <= m["precision"] <= 1 and 0 <= m["recall"] <= 1
    assert 0 <= m["f1"] <= 1
    # 阈值拉高后召回率不应上升
    assert me.threshold_metrics(y, proba, 0.8)["recall"] <= m["recall"]


def test_lift_table_monotone_when_signal_exists():
    """概率与标签正相关时，档1（P 最低）错误率应明显高于档5。"""
    import numpy as np

    from modules import model_eval as me

    rng = np.random.default_rng(1)
    y = rng.integers(0, 2, 500)
    proba = np.clip(0.5 + 0.5 * (y - 0.5) + rng.normal(0, 0.12, 500), 0, 1)
    lift = me.lift_table(y, proba, bins=5)
    assert len(lift) == 5
    assert lift["样本数"].sum() == 500
    assert lift["实际错误率"].iloc[0] > lift["实际错误率"].iloc[-1]
