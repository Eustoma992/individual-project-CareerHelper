# -*- coding: utf-8 -*-
"""并行分片下载 whisper 模型文件（hf-mirror 单连接限速，分片可显著提速）。"""
import os
import sys
import concurrent.futures
import urllib.request

URL = "https://hf-mirror.com/Systran/faster-whisper-small/resolve/main/model.bin"
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "models", "faster-whisper-small", "model.bin")
TOTAL = 483_000_000  # 稍后以服务端 Content-Range 为准校正
CHUNKS = 16


def head_size():
    req = urllib.request.Request(URL, method="HEAD", headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return int(r.headers["Content-Length"])


def fetch_range(i, start, end, size):
    part = f"{OUT}.part{i}"
    if os.path.exists(part) and os.path.getsize(part) == end - start + 1:
        return i, True
    for attempt in range(6):
        try:
            req = urllib.request.Request(URL, headers={"User-Agent": "Mozilla/5.0",
                                                      "Range": f"bytes={start}-{end}"})
            with urllib.request.urlopen(req, timeout=120) as r, open(part, "wb") as f:
                while True:
                    b = r.read(262144)
                    if not b:
                        break
                    f.write(b)
            if os.path.getsize(part) == end - start + 1:
                return i, True
        except Exception as e:
            print(f"  chunk {i} retry {attempt + 1}: {e}", flush=True)
    return i, False


def main():
    total = head_size()
    print(f"remote size: {total / 1e6:.1f} MB, chunks: {CHUNKS}", flush=True)
    span = total // CHUNKS + 1
    ranges = []
    for i in range(CHUNKS):
        s = i * span
        e = min(s + span - 1, total - 1)
        if s > e:
            break
        ranges.append((i, s, e))

    ok = 0
    with concurrent.futures.ThreadPoolExecutor(max_workers=CHUNKS) as ex:
        futs = [ex.submit(fetch_range, i, s, e, total) for i, s, e in ranges]
        for f in concurrent.futures.as_completed(futs):
            i, good = f.result()
            ok += good
            print(f"chunk {i}: {'ok' if good else 'FAIL'}", flush=True)

    if ok != len(ranges):
        print("部分分片失败，重试一遍…", flush=True)
        with concurrent.futures.ThreadPoolExecutor(max_workers=CHUNKS) as ex:
            futs = [ex.submit(fetch_range, i, s, e, total) for i, s, e in ranges
                    if not os.path.exists(f"{OUT}.part{i}") or
                    os.path.getsize(f"{OUT}.part{i}") != e - s + 1]
            for f in concurrent.futures.as_completed(futs):
                _, good = f.result()
                if not good:
                    print("仍有分片失败，退出", flush=True)
                    sys.exit(1)

    with open(OUT, "wb") as out:
        for i, s, e in ranges:
            with open(f"{OUT}.part{i}", "rb") as p:
                out.write(p.read())
    for i, _, _ in ranges:
        os.remove(f"{OUT}.part{i}")
    print("size:", os.path.getsize(OUT), "expected:", total, flush=True)


if __name__ == "__main__":
    main()
