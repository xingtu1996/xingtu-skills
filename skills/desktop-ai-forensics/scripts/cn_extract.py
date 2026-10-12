#!/usr/bin/env python3
"""Extract Chinese conversation text from Chromium IndexedDB / leveldb stores."""
import os, sys, glob, re, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ldb import read_sstable, read_wal

# a "sentence" = run of chars containing at least 3 han chars
SENT = re.compile(r'[^\x00-\x08\x0b\x0c\x0e-\x1f]{6,}')
HAN = re.compile(r'[\u4e00-\u9fff]')

def chinese_segments(blob, minhan=3, minlen=6):
    if not blob:
        return []
    t = blob.decode('utf-8', 'ignore')
    out = []
    for m in SENT.finditer(t):
        s = m.group().strip()
        if len(s) < minlen:
            continue
        if len(HAN.findall(s)) < minhan:
            continue
        if '\ufffd' in s:      # garbled -> likely not real text
            continue
        out.append(s)
    return out

def gather(path, minhan=3, minlen=6):
    cnt = collections.Counter()
    nfiles = 0
    nentries = 0
    files = sorted([p for p in glob.glob(os.path.join(path, '*')) if os.path.isfile(p)])
    for f in files:
        b = os.path.basename(f)
        ents = []
        try:
            if b.endswith('.ldb'):
                ents = read_sstable(f)
            elif b.endswith('.log') and os.path.getsize(f) > 100:
                ents = [(k, v) for k, v, _ in read_wal(f)]
        except Exception as e:
            print(f"   !! {b}: {e}", file=sys.stderr)
            continue
        nfiles += 1
        nentries += len(ents)
        for k, v in ents:
            for s in chinese_segments(v, minhan, minlen):
                cnt[s] += 1
            for s in chinese_segments(k, minhan, minlen):
                cnt[s] += 1
    return cnt, nfiles, nentries

if __name__ == '__main__':
    path = sys.argv[1]
    minhan = int(sys.argv[2]) if len(sys.argv) > 2 else 3
    limit = int(sys.argv[3]) if len(sys.argv) > 3 else 60
    cnt, nf, ne = gather(path, minhan)
    print(f"### {os.path.basename(path.rstrip('/'))}: files={nf} entries={ne} unique_cn={len(cnt)}", file=sys.stderr)
    for s, n in cnt.most_common(limit):
        print(f"[{n}] {s[:600]}")
