# -*- coding: utf-8 -*-
"""把 seed_data.json 与 questions.json 打包成静态站可直接 <script> 引入的 data.js。"""
import json
import pathlib
import time

ROOT = pathlib.Path(__file__).resolve().parent.parent
SEED = ROOT / "data" / "seed_data.json"
BANK = ROOT / "data" / "questions.json"
OUT = ROOT / "data.js"

ORDER = [
    "后端开发工程师", "前端开发工程师", "数据分析师", "算法工程师", "产品经理",
    "会计（财务岗）", "审计师（事务所）", "金融分析师",
    "银行管培生（中后台）", "风险管理岗（银行）", "授信审批岗（公司信贷）",
    "运营清算岗（银行）", "合规与反洗钱岗（银行）",
    "投资银行岗（券商）", "固定收益岗（券商）", "财富管理与机构销售岗（券商）",
]

GROUPS = {
    "互联网 / 计算机": ["后端开发工程师", "前端开发工程师", "数据分析师", "算法工程师", "产品经理"],
    "财会 / 审计": ["会计（财务岗）", "审计师（事务所）", "金融分析师"],
    "银行中后台": ["银行管培生（中后台）", "风险管理岗（银行）", "授信审批岗（公司信贷）",
                "运营清算岗（银行）", "合规与反洗钱岗（银行）"],
    "券商": ["投资银行岗（券商）", "固定收益岗（券商）", "财富管理与机构销售岗（券商）"],
}


def main():
    seed = json.loads(SEED.read_text(encoding="utf-8"))
    positions = seed["positions"]
    bank = json.loads(BANK.read_text(encoding="utf-8")) if BANK.exists() else {}

    ordered = [p for p in ORDER if p in positions]
    ordered += [p for p in positions if p not in ordered]

    payload = {
        "meta": {
            "title": "大学生实习&校招笔面试数据分析辅导工具",
            "updated": time.strftime("%Y-%m-%d"),
            "positionCount": len(ordered),
            "questionCount": sum(len(v) for v in bank.values()),
        },
        "groups": GROUPS,
        "positions": {p: positions[p] for p in ordered},
        "questions": {p: bank.get(p, []) for p in ordered},
    }

    body = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    OUT.write_text(
        "/* 由 scripts/build_static_data.py 生成，请勿手工编辑。\n"
        "   数据来源：data/seed_data.json（岗位考情画像）+ data/questions.json（内置题库） */\n"
        f"window.JOB_DATA = {body};\n",
        encoding="utf-8",
    )
    size = OUT.stat().st_size / 1024
    print(f"已生成 {OUT.name}：{len(ordered)} 岗位 / {payload['meta']['questionCount']} 题 / {size:.0f} KB")


if __name__ == "__main__":
    main()
