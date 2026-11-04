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
                                 "pages/interview.py", "pages/profile.py"])
def test_pages_render(page):
    """四个页面在无 API Key、无历史记录时也应正常渲染。"""
    at = AppTest.from_file(str(ROOT / page), default_timeout=90).run()
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
