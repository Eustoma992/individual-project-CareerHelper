# -*- coding: utf-8 -*-
"""生成静态站内置笔试题库：每个岗位按考点权重与题型配比出 12 道题（含答案解析）。

用法：
    python scripts/build_question_bank.py            # 只补缺失岗位
    python scripts/build_question_bank.py --force    # 全部重新生成
"""
import concurrent.futures as futures
import io
import json
import os
import pathlib
import re
import time
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parent.parent
SEED = ROOT / "data" / "seed_data.json"
OUT = ROOT / "data" / "questions.json"
PER_POSITION = 12


def api_key():
    key = os.getenv("DEEPSEEK_API_KEY")
    if key:
        return key.strip()
    secrets = ROOT / ".streamlit" / "secrets.toml"
    if secrets.exists():
        m = re.search(r'DEEPSEEK_API_KEY\s*=\s*"([^"]+)"', secrets.read_text(encoding="utf-8"))
        if m:
            return m.group(1)
    raise SystemExit("未找到 DEEPSEEK_API_KEY")


def chat(prompt, temperature=0.8):
    body = json.dumps({
        "model": "deepseek-chat",
        "messages": [
            {"role": "system", "content": "你是一名资深校园招聘笔试命题专家，只输出 JSON，不要任何多余文字。"},
            {"role": "user", "content": prompt},
        ],
        "temperature": temperature,
        "max_tokens": 4200,
    }).encode()
    req = urllib.request.Request(
        "https://api.deepseek.com/chat/completions", data=body,
        headers={"Authorization": f"Bearer {api_key()}", "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=180) as r:
        return json.loads(r.read())["choices"][0]["message"]["content"]


def extract_json(text):
    text = text.strip()
    m = re.search(r"```(?:json)?\s*(.*?)```", text, re.S)
    if m:
        text = m.group(1).strip()
    start = min(i for i in (text.find("["), text.find("{")) if i >= 0)
    end = max(text.rfind("]"), text.rfind("}"))
    return json.loads(text[start:end + 1])


def allocate(type_mix, n):
    """按题型占比分配题量，保证合计为 n。"""
    items = sorted(type_mix.items(), key=lambda x: -x[1])
    counts, remaining = {}, n
    for i, (t, ratio) in enumerate(items):
        if i == len(items) - 1:
            counts[t] = remaining
        else:
            c = max(1, round(n * ratio))
            counts[t] = c
            remaining -= c
    return counts


def build_prompt(position, written):
    topics = "；".join(f"{t['考点']}（占比{t['占比']:.0%}）" for t in written["考点分布"])
    counts = allocate(written["题型分布"], PER_POSITION)
    return f"""岗位：{position}
该岗位笔试高频考点及统计占比：{topics}
题型配比：{"、".join(f"{k}{v:.0%}" for k, v in written["题型分布"].items())}
请生成 {PER_POSITION} 道笔试题，各题型数量严格为：{json.dumps(counts, ensure_ascii=False)}

要求：
1. 每题 topic 必须从上面考点列表中选取，题目数量与考点占比大致匹配；
2. 单选/多选题必须有 4 个选项，格式 ["A. 内容","B. 内容","C. 内容","D. 内容"]，answer 为字母（多选如 "A,C"）；
3. 简答/计算题/案例题不给选项（options 为 []），题干要交代清楚已知条件和数据；answer 写参考答案要点或计算步骤与结果；计算题的数值要能算通，不得自相矛盾；
4. explanation 写 2-4 句解析，说明为什么这么答，并点出该考点为什么在校招中高频；
5. difficulty 取 "易" / "中" / "难"，整体难度分布约 3:5:2；
6. 题目要贴近真实校招笔试，不要出现"以下哪个不是"这类凑数题。

只输出 JSON 数组，每项：
{{"type":"{ "|".join(counts.keys()) }","topic":"考点名","question":"题干","options":[],"answer":"参考答案","explanation":"解析","difficulty":"中"}}"""


def clean(item, written):
    qtype = str(item.get("type", "简答")).strip()
    valid = list(written["题型分布"].keys())
    if qtype not in valid:
        qtype = "简答" if "简答" in valid else valid[0]
    topic = str(item.get("topic", "")).strip() or written["考点分布"][0]["考点"]
    opts = item.get("options") or []
    if not isinstance(opts, list):
        opts = []
    opts = [str(o).strip() for o in opts if str(o).strip()]
    if qtype in ("单选", "多选"):
        if len(opts) < 4:
            raise ValueError(f"选择题选项不足：{item.get('question', '')[:20]}")
        opts = opts[:4]
    else:
        opts = []
    answer = str(item.get("answer", "")).strip()
    if not answer:
        raise ValueError("缺少答案")
    return {
        "type": qtype,
        "topic": topic,
        "question": str(item.get("question", "")).strip(),
        "options": opts,
        "answer": answer,
        "explanation": str(item.get("explanation", "")).strip(),
        "difficulty": item.get("difficulty") if item.get("difficulty") in ("易", "中", "难") else "中",
    }


def gen_one(position, written):
    last_err = None
    for attempt in range(3):
        try:
            raw = chat(build_prompt(position, written))
            items = extract_json(raw)
            if not isinstance(items, list) or len(items) < 8:
                raise ValueError(f"题目数量异常：{len(items) if isinstance(items, list) else 'n/a'}")
            cleaned = [clean(x, written) for x in items]
            return position, cleaned, None
        except Exception as e:  # noqa: BLE001
            last_err = e
            time.sleep(2 + attempt * 3)
    return position, None, repr(last_err)


def main():
    force = "--force" in os.sys.argv
    positions = json.loads(SEED.read_text(encoding="utf-8"))["positions"]
    bank = {}
    if OUT.exists() and not force:
        bank = json.loads(OUT.read_text(encoding="utf-8"))

    todo = [(p, v["written"]) for p, v in positions.items() if p not in bank]
    print(f"待生成岗位：{len(todo)}，已存在：{len(bank)}")

    with futures.ThreadPoolExecutor(max_workers=4) as pool:
        futs = {pool.submit(gen_one, p, w): p for p, w in todo}
        for fut in futures.as_completed(futs):
            name, items, err = fut.result()
            if err:
                print(f"  ✗ {name}: {err}")
            else:
                bank[name] = items
                print(f"  ✓ {name}: {len(items)} 题")

    OUT.write_text(json.dumps(bank, ensure_ascii=False, indent=1), encoding="utf-8")
    total = sum(len(v) for v in bank.values())
    print(f"已写入 {OUT.relative_to(ROOT)}：{len(bank)} 个岗位 / {total} 道题")


if __name__ == "__main__":
    main()
