# -*- coding: utf-8 -*-
"""牛客面经卡片解析测试版"""
import re


def clean(s):
    s = re.sub(r'&nbsp;|&amp;|&quot;|&#39;', ' ', s)
    return re.sub(r'\s+', ' ', re.sub(r'<[^>]+>', '', s)).strip()


def parse_nowcoder(h):
    pos = [m.start() for m in re.finditer(r'id="feed-(?:post|dynamic)-content-', h)]
    out = []
    for i, p in enumerate(pos):
        prev = h[pos[i - 1] if i > 0 else 0: p]
        seg = h[p:p + 3000]
        am = re.search(r'href="(/(?:discuss|feed/main/detail)/[^"?]+)', seg)
        if not am:
            continue
        # 标题：作者区里最后一个加粗标题块
        tb = re.findall(r'tw-font-bold[^>]*>(.{0,600}?)</div>', prev, re.S)
        title = clean(tb[-1]) if tb else ''
        if not title:
            tm = re.search(r'class="[^"]*\bpo\b[^"]*"[^>]*>([^<]{4,80})</a>', prev)
            title = clean(tm.group(1)) if tm else ''
        times = re.findall(r'show-time[^>]*>([^<]{3,30})</', prev)
        authors = re.findall(r'class="[^"]*job-text[^"]*"[^>]*>([^<]{2,40})</a>', prev)
        # 摘要：feed-text 锚点内容
        fm = re.search(r'class="feed-text[^"]*"[^>]*>(.*?)</a>', seg, re.S)
        summary = clean(fm.group(1)) if fm else ''
        out.append({
            'title': title[:80],
            'url': 'https://www.nowcoder.com' + am.group(1),
            'time_text': times[-1].strip() if times else '',
            'author': authors[-1].strip() if authors else '',
            'summary': summary[:180],
        })
    return out
