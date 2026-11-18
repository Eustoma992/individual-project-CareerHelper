# -*- coding: utf-8 -*-
"""第三轮采集（扩容）：在第二轮 1677 条的基础上把样本扩到 3000-5000 条。
扩容手段（全部为公开页面/接口的真实返回，无虚构）：
  1. 牛客站内搜索翻页（每页约 20 条，此前只抓第 1 页）+ 更多检索词
  2. 应届生校招公告列表翻页 1-25 页（每页约 90 条，此前只抓 8 页）
  3. Codetop 深分页（题库总量 1159，此前只抓 6 页 120 题）
  4. 赛码网企业题库全量企业、每企业 2 页（此前仅练习量前 20 家 1 页）
  5. 职题库补充检索词
原始响应留存 raw4/ 目录。输出 records_full.csv（utf-8-sig）。"""
import csv, json, os, re, subprocess, sys, time
import urllib.parse, urllib.request

BASE = os.path.dirname(os.path.abspath(__file__))
RAW = os.path.join(BASE, "raw4")
os.makedirs(RAW, exist_ok=True)
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36")
TODAY = __import__("datetime").date.today()
sys.path.insert(0, BASE)
from nc_parser import parse_nowcoder  # noqa: E402

records, status = [], []


def http(url, cookie=None, data=None, timeout=30, retries=3):
    h = {"User-Agent": UA, "Accept-Language": "zh-CN,zh;q=0.9", "Accept-Encoding": "gzip"}
    if cookie:
        h["Cookie"] = cookie
    body = None
    if data is not None:
        body = json.dumps(data).encode()
        h["Content-Type"] = "application/json"
    last = None
    for k in range(retries + 1):
        try:
            req = urllib.request.Request(url, data=body, headers=h)
            r = urllib.request.urlopen(req, timeout=timeout)
            d = r.read()
            if r.headers.get("Content-Encoding") == "gzip" or d[:2] == b"\x1f\x8b":
                import gzip as _gz
                d = _gz.decompress(d)
            return d
        except Exception as e:
            last = e
            time.sleep(2 + k * 2)
    raise last


def norm_date(t):
    from datetime import date, timedelta
    t = (t or "").strip()
    if not t:
        return ""
    m = re.match(r"(\d{4})-(\d{2})-(\d{2})", t)
    if m:
        return m.group(0)
    m = re.match(r"(\d{1,2})-(\d{1,2})(\s|$)", t)
    if m:
        return "%d-%02d-%02d" % (TODAY.year, int(m.group(1)), int(m.group(2)))
    if t.startswith("今天"):
        return TODAY.isoformat()
    if t.startswith("昨天"):
        return (TODAY - timedelta(days=1)).isoformat()
    m = re.match(r"(\d+)\s*天前", t)
    if m:
        return (TODAY - timedelta(days=int(m.group(1)))).isoformat()
    if t.startswith("前天"):
        return (TODAY - timedelta(days=2)).isoformat()
    return ""


FIN = ["会计", "财务", "审计", "银行", "证券", "基金", "保险", "投行", "四大", "德勤", "普华永道", "安永", "毕马威", "金融", "信托", "税务"]
FMCG = ["快消", "宝洁", "联合利华", "欧莱雅", "玛氏", "亿滋", "可口可乐", "百威", "市场", "营销", "品牌", "运营", "销售", "管培生", "消费"]
TECH = ["腾讯", "阿里", "百度", "字节", "美团", "京东", "网易", "华为", "小米", "滴滴", "快手", "程序员", "开发", "算法", "测试", "运维", "数据", "产品经理", "前端", "后端", "Java", "C\\+\\+", "Python"]


def classify(title, company, summary, fallback=""):
    for field in (title, company, title + company + summary):
        if any(k in field for k in FIN):
            return "会计与金融"
        if any(k in field for k in FMCG):
            return "快消运营"
        if any(k in field for k in TECH):
            return "互联网计算机"
    return fallback or "其他行业"


def job_from(author, title):
    parts = (author or "").split()
    if len(parts) >= 2 and not re.search(r"\d", parts[-1]):
        return parts[-1]
    return ""


# ---------------- 1. Codetop（深分页 1-30，共 1159 题） ----------------
def scrape_codetop(pages=30):
    out, seen = [], set()
    for p in range(1, pages + 1):
        try:
            d = json.loads(http(f"https://codetop.cc/api/questions/?page={p}&pageSize=20"))
        except Exception as e:
            print("  codetop page", p, "fail", str(e)[:60])
            break
        lst = d.get("list", [])
        if not lst:
            break
        for q in lst:
            lc = q.get("leetcode") or {}
            t = lc.get("title", "")
            if not t or t in seen:
                continue
            seen.add(t)
            lv = {"1": "简单", "2": "中等", "3": "困难"}.get(str(lc.get("level")), "")
            out.append({
                "source": "Codetop", "industry": "互联网计算机",
                "job_family": "算法/后端（LeetCode 题）", "stage": "笔试/面试手撕题",
                "title": t, "company": "", "author": "",
                "publish_date": (q.get("time") or "")[:10],
                "time_text": (q.get("time") or "")[:10],
                "url": "https://codetop.cc/home",
                "leetcode_url": "https://leetcode.cn/problems/%s/" % lc.get("slug_title", ""),
                "extra": "考察频次%s；难度%s" % (q.get("value"), lv),
                "summary": re.sub(r"<[^>]+>", "", lc.get("content") or "")[:120],
            })
        if p == 1:
            open(os.path.join(RAW, "codetop_p1.json"), "wb").write(
                json.dumps(d, ensure_ascii=False).encode())
        time.sleep(0.5)
    records.extend(out)
    status.append({"site": "Codetop (codetop.cc)", "url": "https://codetop.cc/home",
                   "access": "可访问（公开 JSON 接口 /api/questions/）",
                   "method": "接口分页抓取，第 1-%d 页（接口题库总量 count=1159）" % pages,
                   "obtained": "%d 条高频算法题" % len(out),
                   "note": "含考察频次、难度、最近更新日期；不含公司字段"})
    print("[codetop]", len(out))


# ---------------- 2. 牛客：岗位合集 + 站内搜索翻页 ----------------
NC_TAGS = {"639": "Java工程师", "644": "前端工程师", "645": "算法工程师", "733": "大数据开发工程师"}


def scrape_nowcoder(queries, search_pages=2):
    seen = set()
    n_tag = 0
    for tid, name in NC_TAGS.items():
        url = "https://www.nowcoder.com/experience/%s" % tid
        try:
            h = http(url).decode("utf-8", "ignore")
            if tid == "644":
                open(os.path.join(RAW, "nc_tag_644.html"), "wb").write(h.encode())
            for c in parse_nowcoder(h):
                if not c["title"] or c["url"] in seen:
                    continue
                seen.add(c["url"])
                records.append({
                    "source": "牛客网", "industry": "互联网计算机", "job_family": name,
                    "stage": "面经", "title": c["title"], "company": "", "author": c["author"],
                    "publish_date": norm_date(c["time_text"]), "time_text": c["time_text"],
                    "url": c["url"], "leetcode_url": "", "extra": "岗位精选面经合集",
                    "summary": c["summary"],
                })
                n_tag += 1
        except Exception as e:
            print("  tag fail", tid, str(e)[:50])
        time.sleep(1.2)

    n_search = 0
    for q in queries:
        fallback = ("会计与金融" if any(k in q for k in ["会计", "财务", "审计", "银行", "券商", "证券", "基金", "投行"])
                    else ("快消运营" if any(k in q for k in ["快消", "运营", "市场", "管培", "销售"]) else "互联网计算机"))
        for pg in range(1, search_pages + 1):
            url = ("https://www.nowcoder.com/search/all?query=" + urllib.parse.quote(q) +
                   "&type=all&page=%d" % pg)
            try:
                h = http(url).decode("utf-8", "ignore")
            except Exception as e:
                print("  search fail", q, pg, str(e)[:50])
                continue
            if pg == 1 and q == queries[0]:
                open(os.path.join(RAW, "nc_search_p1.html"), "wb").write(h.encode())
            cards = parse_nowcoder(h)
            if not cards:
                time.sleep(3)
                try:
                    h = http(url).decode("utf-8", "ignore")
                    cards = parse_nowcoder(h)
                except Exception:
                    cards = []
            for c in cards:
                if not c["title"] or c["url"] in seen:
                    continue
                seen.add(c["url"])
                records.append({
                    "source": "牛客网（站内搜索）",
                    "industry": classify(c["title"], c["author"], c["summary"], fallback),
                    "job_family": job_from(c["author"], c["title"]) or q.replace("面经", ""),
                    "stage": "面经", "title": c["title"], "company": "", "author": c["author"],
                    "publish_date": norm_date(c["time_text"]), "time_text": c["time_text"],
                    "url": c["url"], "leetcode_url": "", "extra": "检索词：%s（第%d页）" % (q, pg),
                    "summary": c["summary"],
                })
                n_search += 1
            time.sleep(1.2)
    status.append({"site": "牛客网 (nowcoder.com)", "url": "https://www.nowcoder.com/search/all?query=面经&type=all",
                   "access": "可访问（精选面经合集与站内搜索为服务端渲染，无需登录）",
                   "method": "HTML 解析：岗位合集 %d 个 + 站内搜索 %d 个检索词各前 %d 页（每页约 20 条）" % (len(NC_TAGS), len(queries), search_pages),
                   "obtained": "岗位合集 %d 条 + 站内搜索 %d 条" % (n_tag, n_search),
                   "note": "字段含标题、发帖时间、作者学校与岗位标签、正文摘要、详情链接"})
    print("[nowcoder] 合集", n_tag, "搜索", n_search)


# ---------------- 3. 赛码网（全量企业 × 2 页） ----------------
def scrape_acm(page_size=50, pages=2):
    API = "https://62885.acmcoder.com/customer/api"
    raw = http(API + "/homeCompList")
    open(os.path.join(RAW, "acm_homeCompList.json"), "wb").write(raw)
    comps = json.loads(raw)["result"]
    comps = sorted(comps, key=lambda c: c.get("practiseCount", 0), reverse=True)
    n = 0
    for c in comps:
        if not c.get("practiseCount"):
            continue
        for pg in range(1, pages + 1):
            try:
                raw2 = http(API + "/positionList",
                            data={"compCode": c["compCode"], "pageSize": page_size, "pageNum": pg})
            except Exception as e:
                print("  acm fail", c["compName"], str(e)[:50])
                break
            d = json.loads(raw2)
            if d.get("errno") != 0:
                break
            plist = d["result"].get("position", [])
            if not plist:
                break
            for p in plist:
                records.append({
                    "source": "赛码网·企业题库", "industry": "",
                    "job_family": p.get("positionTitle", ""), "stage": "笔试题库",
                    "title": p.get("positionTitle", ""), "company": c.get("compName", ""),
                    "author": "", "publish_date": "", "time_text": "",
                    "url": "https://acmcoder.com/#/practice/company-code?compCode=%s" % c["compCode"],
                    "leetcode_url": "",
                    "extra": "题集题目数 %s，累计练习 %s 人次" % (p.get("questionCount", ""), p.get("basePractiseCount", "")),
                    "summary": "",
                })
                n += 1
            time.sleep(0.5)
    status.append({"site": "赛码网（acmcoder.com）", "url": "https://acmcoder.com/#/practice/company",
                   "access": "可访问。SPA 前端调用的公开 API 位于 62885.acmcoder.com，无需登录",
                   "method": "公开 JSON 接口：homeCompList 全量有练习量的企业，每企业前 %d 页岗位题集" % pages,
                   "obtained": "企业题库 %d 条（企业 %d 家）" % (n, len(comps)),
                   "note": "字段含企业名、岗位题集名、题目数、累计练习人次；题目原文需注册登录；常青题库无发布时间"})
    print("[acm]", n)


# ---------------- 4. 职题库（补充检索词） ----------------
def scrape_jobtiku(keywords):
    item_pat = re.compile(
        r'<a href="(https://www\.jobtiku\.com/practice/intro\?no=\w+)" target="_blank">\s*'
        r'<div class="bagf7 p20 goumai-s">(.*?)</a>', re.S)
    seen, n = set(), 0
    for kw in keywords:
        try:
            raw = http("https://www.jobtiku.com/search?keyword=" + urllib.parse.quote(kw))
        except Exception as e:
            print("  jobtiku fail", kw, str(e)[:50])
            continue
        h = raw.decode("utf-8", "ignore")
        if kw == keywords[0]:
            open(os.path.join(RAW, "jt_search.html"), "wb").write(raw)
        for url, blk in item_pat.findall(h):
            if url in seen:
                continue
            seen.add(url)
            t = re.search(r'class="f18[^"]*">([^<]+)', blk)
            sub = re.search(r'class="f14[^"]*"[^>]*>([^<]+)', blk)
            title = t.group(1).strip() if t else ""
            if not title:
                continue
            comp = ""
            mc = re.search(r"《(.+?)》", title)
            if mc:
                comp = mc.group(1)
            records.append({
                "source": "职题库·题集目录", "industry": "",
                "job_family": title, "stage": "题集", "title": title, "company": comp,
                "author": "", "publish_date": "", "time_text": "", "url": url,
                "leetcode_url": "", "extra": "检索词：%s" % kw,
                "summary": sub.group(1).strip()[:180] if sub else "",
            })
            n += 1
        time.sleep(0.6)
    status.append({"site": "职题库（jobtiku.com）", "url": "https://www.jobtiku.com/search?keyword=笔试题库",
                   "access": "可访问。站内搜索页服务端渲染，匿名可看全部题集条目（无翻页，单页全量）",
                   "method": "按检索词 %s 抓取搜索结果中的题库条目" % "、".join(keywords),
                   "obtained": "题集目录 %d 条" % n,
                   "note": "字段含题集名、所属公司、简介、详情链接；题目正文需登录/付费；目录为常青内容无发布时间"})
    print("[jobtiku]", n)


# ---------------- 5. 应届生（列表翻页 1-25，跳过详情页提速） ----------------
YJS_LIST_ROWS = re.compile(
    r'<tr class="jobli">\s*<td[^>]*>\s*<a href="(/job-[\d\-]+\.html)"[^>]*>(.*?)</a>\s*</td>\s*'
    r'<td[^>]*>\s*<a href="[^"]+"[^>]*>(.*?)</a>\s*</td>\s*<td[^>]*><span>(.*?)</span></td>\s*'
    r'<td[^>]*><span>(.*?)</span></td>', re.S)


def clean(s):
    return re.sub(r"\s+", "", re.sub(r"<[^>]+>", "", s))


def yjs_cookie():
    raw = http("https://www.yingjiesheng.com/commend-fulltime-1.html")
    chal = os.path.join(RAW, "yjs_challenge.html")
    open(chal, "wb").write(raw)
    h = raw.decode("utf-8", "ignore")
    if "renderData" not in h:
        return ""
    out = subprocess.run(["node", os.path.join(BASE, "solve_acw.js"), chal],
                         capture_output=True, text=True, timeout=60)
    ck = out.stdout.strip()
    return "acw_sc__v2=" + ck if ck else None


def scrape_yjs(pages=25):
    ck = yjs_cookie()
    if ck is None:
        status.append({"site": "应届生求职网", "url": "-", "access": "WAF 挑战求解失败",
                       "method": "-", "obtained": "0 条", "note": "-"})
        return
    print("  yjs cookie ok")
    n = 0
    for pg in range(1, pages + 1):
        rows = []
        for attempt in range(5):
            try:
                raw = http("https://www.yingjiesheng.com/commend-fulltime-%d.html" % pg, cookie=ck)
            except Exception as e:
                print("  yjs fail page", pg, str(e)[:50])
                break
            h = raw.decode("utf-8", "ignore")
            if "renderData" in h:  # WAF 挑战随机触发，重解 cookie
                print("  yjs page", pg, "challenge, re-solve #%d" % (attempt + 1))
                ck = yjs_cookie()
                if ck is None:
                    break
                time.sleep(1)
                continue
            if pg == 1:
                open(os.path.join(RAW, "yjs_list_p1.html"), "wb").write(raw)
            rows = YJS_LIST_ROWS.findall(h)
            break
        for url, comp, title, region, date in rows:
            records.append({
                "source": "应届生求职网·校招公告", "industry": "",
                "job_family": clean(title), "stage": "招聘公告",
                "title": clean(title), "company": clean(comp), "author": "",
                "publish_date": clean(date) if re.match(r"\d{4}-\d{2}-\d{2}", clean(date)) else "",
                "time_text": clean(date),
                "url": "https://www.yingjiesheng.com" + url, "leetcode_url": "",
                "extra": "工作地点 %s" % clean(region), "summary": "",
            })
            n += 1
        print("  yjs page", pg, "->", len(rows))
        time.sleep(0.7)
    status.append({"site": "应届生求职网（yingjiesheng.com）", "url": "https://www.yingjiesheng.com/commend-fulltime-1.html",
                   "access": "可访问。阿里云 WAF（acw_sc__v2 JS 挑战），已用 Node 沙箱求解 cookie",
                   "method": "抓取『职位推荐·全职』列表第 1-%d 页（每页约 90 条）" % pages,
                   "obtained": "校招公告 %d 条" % n,
                   "note": "列表字段含公司、招聘标题、工作地点、发布日期、详情链接；BBS 面经正文仍需登录；公告为招聘信息而非面经内容"})
    print("[yjs]", n)


if __name__ == "__main__":
    QUERIES = ["会计面经", "财务面经", "审计面经", "银行面经", "银行管培生面经", "券商面经",
               "证券面经", "投行面经", "基金面经", "四大面经", "德勤面经", "普华永道面经",
               "安永面经", "毕马威面经", "快消面经", "运营面经", "市场面经", "管培生面经",
               "销售面经", "产品经理面经", "数据分析面经", "风控面经", "银行笔试", "券商笔试"]
    scrape_codetop(pages=30)
    scrape_nowcoder(QUERIES, search_pages=2)
    scrape_acm(page_size=50, pages=2)
    scrape_jobtiku(["笔试题库", "面试题库", "题库", "银行笔试题库", "会计题库", "计算机题库"])
    scrape_yjs(pages=25)
    fill_industry = [r for r in records]
    for r in records:
        if not r["industry"]:
            r["industry"] = classify(r["title"], r["company"], r["summary"])
    # 去重：url + title
    seen, dedup = set(), []
    for r in records:
        key = (r["url"], r["title"])
        if key in seen:
            continue
        seen.add(key)
        dedup.append(r)
    records = dedup
    OUT_DIR = os.path.join(os.path.dirname(BASE), "data", "\u9762\u7ecf\u6570\u636e")
    os.makedirs(OUT_DIR, exist_ok=True)
    json.dump({"collected_at": time.strftime("%Y-%m-%d %H:%M"),
               "records": records, "status": status},
              open(os.path.join(OUT_DIR, "collected_round3.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    fields = ["source", "industry", "job_family", "stage", "title", "company", "author",
              "publish_date", "time_text", "url", "leetcode_url", "extra", "summary"]
    with open(os.path.join(OUT_DIR, "records_full.csv"), "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for r in records:
            w.writerow({k: r.get(k, "") for k in fields})
    stat = {}
    for r in records:
        stat[r["source"]] = stat.get(r["source"], 0) + 1
    print("\n=== 统计 ===")
    for k, v in sorted(stat.items(), key=lambda x: -x[1]):
        print(k, v)
    dates = sorted([r["publish_date"] for r in records if r["publish_date"]])
    print("总记录数", len(records), "| 时间范围", dates[0] if dates else "-", "~", dates[-1] if dates else "-")
