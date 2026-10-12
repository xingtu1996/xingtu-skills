#!/usr/bin/env python3
"""Minimal LevelDB SSTable + WAL reader for Chromium IndexedDB forensics."""
import os, sys, glob, struct, json, re

try:
    from cramjam import snappy
    def un_snappy(b):
        return bytes(snappy.decompress_raw(b))
except Exception:
    def un_snappy(b):
        raise RuntimeError("snappy unavailable")

MAGIC = 0xdb4775248b80fb57

def read_varint(buf, pos):
    result = 0; shift = 0
    while True:
        b = buf[pos]; pos += 1
        result |= (b & 0x7f) << shift
        if not (b & 0x80):
            break
        shift += 7
        if shift > 63:
            raise ValueError("varint too long")
    return result, pos

def decompress(content, ctype):
    if ctype == 0:
        return content
    if ctype == 1:
        try:
            return un_snappy(content)
        except Exception:
            return None
    return None

def parse_block(raw, size):
    """raw: bytes at block offset; size: block content size. Trailer is 5 bytes after."""
    if len(raw) < size + 5:
        return None
    content = raw[:size]
    ctype = raw[size]
    crc = raw[size+1:size+5]
    data = decompress(content, ctype)
    if data is None:
        return None
    n = len(data)
    if n < 4:
        return []
    restart_count = struct.unpack_from('<I', data, n-4)[0]
    if restart_count == 0:
        return []
    restart_off = n - 4 - restart_count*4
    if restart_off < 0 or restart_off > n:
        return []
    entries = []
    pos = 0
    last_key = b''
    try:
        while pos < restart_off:
            shared, pos = read_varint(data, pos)
            non_shared, pos = read_varint(data, pos)
            vlen, pos = read_varint(data, pos)
            key = last_key[:shared] + data[pos:pos+non_shared]; pos += non_shared
            val = data[pos:pos+vlen]; pos += vlen
            last_key = key
            entries.append((key, val))
    except Exception:
        pass
    return entries

def read_sstable(path, max_blocks=None):
    buf = open(path, 'rb').read()
    if len(buf) < 48:
        return []
    footer = buf[-48:]
    m = struct.unpack_from('<Q', footer, 40)[0]
    if m != MAGIC:
        footer = buf[-44:]
        if len(footer) < 44:
            return []
    try:
        p = 0
        _, p = read_varint(footer, p)          # metaindex offset
        _, p = read_varint(footer, p)          # metaindex size
        idx_off, p = read_varint(footer, p)
        idx_size, p = read_varint(footer, p)
    except Exception:
        return []
    index = parse_block(buf[idx_off:], idx_size)
    if not index:
        return []
    out = []
    n = 0
    for _, hval in index:
        try:
            hp = 0
            boff, hp = read_varint(hval, hp)
            bsize, hp = read_varint(hval, hp)
        except Exception:
            continue
        ents = parse_block(buf[boff:], bsize)
        if ents:
            out.extend(ents)
        n += 1
        if max_blocks and n >= max_blocks:
            break
    return out

def read_wal(path):
    """Parse leveldb write-ahead log records."""
    data = open(path, 'rb').read()
    out = []
    pos = 0
    BS = 32768
    log = []
    while pos + 7 < len(data):
        # skip to next block boundary if less than 7 bytes remain
        block_left = BS - (pos % BS)
        if block_left < 7:
            pos += block_left
            continue
        crc, length, rtype = struct.unpack_from('<IHB', data, pos)
        if rtype == 0 or length == 0 or length > block_left - 7:
            pos += 1
            continue
        payload = data[pos+7:pos+7+length]
        pos += 7 + length
        if rtype == 1:      # FULL
            log.append(payload)
        elif rtype == 2:    # FIRST
            log.append(payload)
        elif rtype == 3:    # LAST
            if log:
                log[-1] += payload
        elif rtype == 4:    # MIDDLE
            if log:
                log[-1] += payload
        # the assembled item is a batch; parse write batch
    for batch in log:
        out.extend(parse_write_batch(batch))
    return out

def parse_write_batch(b):
    if len(b) < 12:
        return []
    pos = 12
    res = []
    while pos < len(b):
        try:
            rtype = b[pos]; pos += 1
            klen, pos = read_varint(b, pos)
            key = b[pos:pos+klen]; pos += klen
            val = b''
            if rtype == 1:
                vlen, pos = read_varint(b, pos)
                val = b[pos:pos+vlen]; pos += vlen
            res.append((key, val, rtype))
        except Exception:
            break
    return res

def extract_text(blob):
    """Pull readable UTF-8 runs out of a V8-serialized / raw value."""
    if not blob:
        return []
    out = []
    for m in re.finditer(rb'(?:[\x20-\x7e]|[\xc2-\xf4][\x80-\xbf]+){4,}', blob):
        try:
            t = m.group().decode('utf-8')
        except Exception:
            continue
        if re.search(r'[\u4e00-\u9fff]', t) or len(t) > 20:
            out.append(t)
    return out

if __name__ == '__main__':
    tgt = sys.argv[1]
    mode = sys.argv[2] if len(sys.argv) > 2 else 'sst'
    files = sorted([p for p in glob.glob(os.path.join(tgt, '*')) if os.path.isfile(p)])
    allents = []
    for f in files:
        base = os.path.basename(f)
        if mode in ('sst', 'auto') and base.endswith('.ldb'):
            allents += [(base, k, v) for k, v in read_sstable(f)]
        if mode in ('wal', 'auto') and base.endswith('.log'):
            allents += [(base, k, v) for k, v, _ in read_wal(f)]
    print(f"### files={len(files)} entries={len(allents)}", file=sys.stderr)
    for base, k, v in allents:
        ks = ''.join(extract_text(k))[:120]
        vs = extract_text(v)
        if not vs:
            continue
        print(f"--- [{base}] KEY: {ks}")
        print("     " + " || ".join(vs[:12])[:1200])
