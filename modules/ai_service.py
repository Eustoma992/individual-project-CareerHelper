# -*- coding: utf-8 -*-
"""DeepSeek API 封装：出题、评分、面试评估，全部以岗位考情统计结果作为提示词依据。"""
import json
import re

import requests

from config import DEEPSEEK_API_KEY, DEEPSEEK_BASE_URL, DEEPSEEK_MODEL


NO_KEY_HINT = (
    "未配置 DeepSeek API Key。请在环境变量 `DEEPSEEK_API_KEY`、"
    "或 `.streamlit/secrets.toml`（部署时用 Secrets 面板）中填入你的 key，"
    "格式参考 `.streamlit/secrets.toml.example`。"
)


def chat(messages, temperature=0.7, timeout=120):
    """调用 DeepSeek chat/completions，返回文本；失败抛出异常。"""
    if not DEEPSEEK_API_KEY:
        raise RuntimeError(NO_KEY_HINT)
    resp = requests.post(
        f"{DEEPSEEK_BASE_URL}/chat/completions",
        headers={"Authorization": f"Bearer {DEEPSEEK_API_KEY}"},
        json={"model": DEEPSEEK_MODEL, "messages": messages, "temperature": temperature},
        timeout=timeout,
    )
    resp.raise_for_status()
    return resp.json()["choices"][0]["message"]["content"]


def extract_json(text):
    """从模型回复中稳健地提取 JSON（容忍 markdown 代码块包裹）。"""
    text = text.strip()
    m = re.search(r"```(?:json)?\s*(.*?)```", text, re.S)
    if m:
        text = m.group(1).strip()
    start = min([i for i in (text.find("["), text.find("{")) if i >= 0])
    end = max(text.rfind("]"), text.rfind("}"))
    return json.loads(text[start:end + 1])


def generate_written_questions(position, topics, type_mix, n_questions):
    """
    根据岗位高频考点权重生成笔试题。
    topics: [{考点, 占比}], type_mix: {题型: 占比}
    返回题目列表 [{type, topic, question, options, answer, explanation, difficulty}]
    """
    topic_desc = "；".join(f"{t['考点']}（统计占比{t['占比']:.0%}）" for t in topics)
    types_desc = "、".join(f"{k}{v:.0%}" for k, v in type_mix.items())
    # 按题型占比分配题量
    counts = {}
    remaining = n_questions
    type_items = sorted(type_mix.items(), key=lambda x: -x[1])
    for i, (t, ratio) in enumerate(type_items):
        if i == len(type_items) - 1:
            counts[t] = remaining
        else:
            c = round(n_questions * ratio)
            counts[t] = c
            remaining -= c

    sys_prompt = (
        "你是一名资深校园招聘笔试命题专家。你必须严格依据给定的岗位考情统计数据出题，"
        "题目考点分布要贴合各考点的统计占比，不得出与统计考点无关的泛化题目。"
        "只输出 JSON，不要输出任何其他文字。"
    )
    allowed_types = "|".join(counts.keys())
    user_prompt = f"""岗位：{position}
该岗位笔试高频考点统计（按占比加权分布考点）：{topic_desc}
题型统计分布：{types_desc}
请生成共 {n_questions} 道笔试题，各题型数量为：{json.dumps(counts, ensure_ascii=False)}。
要求：
1. 每道题的考点必须从上述考点列表中选取，考点覆盖比例大致与占比一致；
2. 单选/多选题给4个选项；其余题型（简答、计算题、案例题、编程题等）不给选项，但要在题干中把已知条件、数据或场景交代清楚；
3. answer 字段：单选/多选填正确选项字母（多选用逗号分隔，如"A,C"）；计算题填关键计算步骤与最终结果；简答/案例/编程题填参考答案要点；
4. explanation 为解析，并说明该考点为何高频（结合校招考情）。
输出 JSON 数组，每项格式：
{{"type": "{allowed_types}", "topic": "考点名", "question": "题干", "options": ["A. ..", "B. ..", "C. ..", "D. .."], "answer": "...", "explanation": "...", "difficulty": "易|中|难"}}"""
    result = chat([{"role": "system", "content": sys_prompt},
                   {"role": "user", "content": user_prompt}], temperature=0.8)
    return extract_json(result)


def grade_subjective(question, reference, user_answer):
    """AI 评分简答/编程题，返回 {score: 0-100, comment}。"""
    prompt = f"""你是校招笔试阅卷官。请依据参考答案对考生作答评分（0-100分）。
题目：{question}
参考答案要点：{reference}
考生作答：{user_answer}
只输出 JSON：{{"score": 整数0-100, "comment": "一两句点评，指出得分点与失分点"}}"""
    result = chat([{"role": "user", "content": prompt}], temperature=0.2)
    return extract_json(result)


def evaluate_interview_answer(position, question, user_answer, round_name="初面"):
    """面试回答评估，返回 {score, logic, coverage, suggestions, key_points}。"""
    prompt = f"""你是{position}岗位的资深面试官，正在进行{round_name}模拟面试。
面试问题：{question}
候选人回答：{user_answer}
请结合该岗位的考察特征评估回答，只输出 JSON：
{{"score": 整数0-100,
"logic": "对回答逻辑框架的评价（STAR结构/条理性等），2-3句",
"coverage": "回答中关键信息的覆盖情况：覆盖了什么、遗漏了什么，2-3句",
"suggestions": "具体可落地的优化建议，给出改进后的表达思路，3句以内",
"key_points": ["该题高分回答必须覆盖的3-5个关键要点"]}}"""
    result = chat([{"role": "user", "content": prompt}], temperature=0.4)
    return extract_json(result)


def generate_interview_followup(position, question, user_answer, history_brief=""):
    """根据候选人回答生成一个追问，模拟真实面试的多轮追问。"""
    prompt = f"""你是{position}岗位的面试官。候选人刚回答了问题："「{question}」"，回答内容："「{user_answer}」"。
之前对话概要：{history_brief}
请像真实面试官一样，针对回答中最值得深挖的点提出一个追问（不要重复之前的问题）。只输出追问的问题文本，不要其他内容。"""
    return chat([{"role": "user", "content": prompt}], temperature=0.8).strip()


def polish_position_intro(position, stats_summary):
    """基于考情统计生成一段岗位考情解读，失败时返回 None。"""
    try:
        prompt = f"""以下是{position}岗位笔试与面试考情的统计结果：
{stats_summary}
请写一段150字以内的考情解读，指出复习侧重点，语气客观。直接输出文本。"""
        return chat([{"role": "user", "content": prompt}], temperature=0.5).strip()
    except Exception:
        return None
