"""Lossless extraction of JPEG bitstreams from TIFF/Compression=7 (new-style JPEG).

Strips are individually-coded abbreviated JPEG streams sharing one JPEGTables
segment.  They are concatenated into a single scan by inserting RSTn markers at
the strip boundaries (each strip covers a whole number of MCU rows), so the
entropy-coded data is copied verbatim -- no decode, no re-encode.
"""
import struct, sys, math

TYPESZ = {1:1, 2:1, 3:2, 4:4, 5:8, 6:1, 7:1, 8:2, 9:4, 10:8, 11:4, 12:8}
SOF_OK = {0xC0, 0xC1}          # baseline / extended sequential huffman
STANDALONE = {0xD8, 0xD9, 0x01} | set(range(0xD0, 0xD8))


class Bad(Exception):
    pass


def read_ifds(buf):
    bo = '<' if buf[:2] == b'II' else '>'
    if buf[:2] not in (b'II', b'MM') or struct.unpack(bo+'H', buf[2:4])[0] != 42:
        raise Bad('not a classic TIFF')
    ifds = []
    off = struct.unpack(bo+'I', buf[4:8])[0]
    while off:
        n = struct.unpack(bo+'H', buf[off:off+2])[0]
        tags = {}
        for i in range(n):
            e = off + 2 + i*12
            tag, typ, cnt = struct.unpack(bo+'HHI', buf[e:e+8])
            size = TYPESZ.get(typ, 1) * cnt
            vo = e + 8 if size <= 4 else struct.unpack(bo+'I', buf[e+8:e+12])[0]
            tags[tag] = (typ, cnt, vo, size)
        ifds.append(tags)
        off = struct.unpack(bo+'I', buf[off+2+n*12:off+6+n*12])[0]
    return bo, ifds


def ints(buf, bo, tags, tag, default=None):
    if tag not in tags:
        return default
    typ, cnt, vo, size = tags[tag]
    fmt = {1:'B', 3:'H', 4:'I', 6:'b', 8:'h', 9:'i'}[typ]
    return list(struct.unpack('%s%d%s' % (bo, cnt, fmt), buf[vo:vo+cnt*struct.calcsize(fmt)]))


def raw(buf, tags, tag, default=None):
    if tag not in tags:
        return default
    _, _, vo, size = tags[tag]
    return buf[vo:vo+size]


def scan_markers(b, stop_at_sos=True):
    """Yield (marker, pos, seglen) for a JPEG byte string."""
    out, i, n = [], 0, len(b)
    while i < n - 1:
        if b[i] != 0xFF:
            raise Bad('marker expected at %d, got %02x' % (i, b[i]))
        m = b[i+1]
        if m == 0xFF:
            i += 1
            continue
        if m in STANDALONE:
            out.append((m, i, 0))
            i += 2
            continue
        L = struct.unpack('>H', b[i+2:i+4])[0]
        out.append((m, i, L))
        if m == 0xDA and stop_at_sos:
            return out
        i += 2 + L
    return out


def parse_tables(jt):
    """Split JPEGTables into its DQT/DHT/DRI segments (dropping SOI/EOI)."""
    segs = []
    for m, pos, L in scan_markers(jt, stop_at_sos=False):
        if m in (0xD8, 0xD9):
            continue
        if m not in (0xDB, 0xC4, 0xDD, 0xDC):
            raise Bad('unexpected marker %02x in JPEGTables' % m)
        segs.append(jt[pos:pos+2+L])
    return b''.join(segs)


def strip_parts(s, idx):
    """Return (sof_segment, sos_segment, entropy_bytes) of one strip stream."""
    ms = scan_markers(s)
    if ms[0][0] != 0xD8:
        raise Bad('strip %d: no SOI' % idx)
    sof = sos = None
    for m, pos, L in ms:
        if m == 0xD8:
            continue
        if m in SOF_OK:
            sof = s[pos:pos+2+L]
        elif m == 0xDA:
            sos = s[pos:pos+2+L]
            data_start = pos + 2 + L
        elif m in (0xDB, 0xC4):
            raise Bad('strip %d: per-strip tables (%02x) unsupported' % (idx, m))
        elif m == 0xDD:
            raise Bad('strip %d: already has DRI' % idx)
        elif 0xC0 <= m <= 0xCF and m not in (0xC4, 0xC8, 0xCC):
            raise Bad('strip %d: unsupported SOF %02x' % (idx, m))
    if sof is None or sos is None:
        raise Bad('strip %d: missing SOF/SOS' % idx)
    if s[-2:] != b'\xff\xd9':
        raise Bad('strip %d: does not end with EOI' % idx)
    data = s[data_start:-2]
    # entropy data must contain no markers other than stuffed 0xFF00
    i = 0
    while True:
        i = data.find(b'\xff', i)
        if i < 0:
            break
        if i + 1 >= len(data):
            raise Bad('strip %d: trailing 0xFF' % idx)
        nxt = data[i+1]
        if nxt != 0x00 and not (0xD0 <= nxt <= 0xD7):
            raise Bad('strip %d: marker FF%02x inside scan' % (idx, nxt))
        if 0xD0 <= nxt <= 0xD7:
            raise Bad('strip %d: pre-existing restart marker' % idx)
        i += 2
    return sof, sos, data


def sof_info(sof):
    seg = sof[4:]
    prec = seg[0]
    h, w = struct.unpack('>HH', seg[1:5])
    nc = seg[5]
    comps = []
    for c in range(nc):
        cid, hv, tq = seg[6+c*3:9+c*3]
        comps.append((cid, hv >> 4, hv & 15, tq))
    return prec, h, w, comps


def icc_app2(icc):
    out = []
    chunks = [icc[i:i+65519] for i in range(0, len(icc), 65519)]
    for n, ch in enumerate(chunks, 1):
        body = b'ICC_PROFILE\x00' + bytes([n, len(chunks)]) + ch
        out.append(b'\xff\xe2' + struct.pack('>H', len(body)+2) + body)
    return b''.join(out)


def convert(path, ifd_index=0):
    buf = open(path, 'rb').read()
    bo, ifds = read_ifds(buf)
    tags = ifds[ifd_index]
    g = lambda t, d=None: ints(buf, bo, tags, t, d)

    if g(259, [None])[0] != 7:
        raise Bad('compression is %r, not 7 (JPEG)' % g(259))
    if 322 in tags or 324 in tags:
        raise Bad('tiled TIFF not supported')
    if g(284, [1])[0] != 1:
        raise Bad('planar configuration %r' % g(284))
    W, H = g(256)[0], g(257)[0]
    spp = g(277, [1])[0]
    rps = g(278)[0]
    photo = g(262)[0]
    bps = g(258, [8])
    if set(bps) != {8}:
        raise Bad('bits per sample %r' % bps)
    offs, counts = g(273), g(279)
    if len(offs) != len(counts):
        raise Bad('strip offset/count mismatch')
    nstrips = len(offs)
    if nstrips != math.ceil(H / rps):
        raise Bad('strip count %d != ceil(%d/%d)' % (nstrips, H, rps))

    jt = raw(buf, tags, 347)
    if jt is None:
        raise Bad('no JPEGTables tag')
    tbl = parse_tables(jt)

    sof0 = sos0 = None
    pieces = []
    for i, (o, c) in enumerate(zip(offs, counts)):
        sof, sos, data = strip_parts(buf[o:o+c], i)
        if i == 0:
            sof0, sos0 = sof, sos
        else:
            if sos != sos0:
                raise Bad('strip %d: SOS differs' % i)
            if sof[:5] + sof[7:] != sof0[:5] + sof0[7:]:   # only height may differ
                raise Bad('strip %d: SOF differs' % i)
        want = rps if i < nstrips - 1 else H - rps*(nstrips - 1)
        if struct.unpack('>H', sof[5:7])[0] != want:
            raise Bad('strip %d: SOF height %d != %d' %
                      (i, struct.unpack('>H', sof[5:7])[0], want))
        pieces.append(data)

    prec, sh, sw, comps = sof_info(sof0)
    if sw != W:
        raise Bad('SOF width %d != TIFF width %d' % (sw, W))
    if len(comps) != spp:
        raise Bad('SOF components %d != SamplesPerPixel %d' % (len(comps), spp))
    hmax = max(c[1] for c in comps)
    vmax = max(c[2] for c in comps)
    mcu_w, mcu_h = 8*hmax, 8*vmax
    if rps % mcu_h:
        raise Bad('RowsPerStrip %d not a multiple of MCU height %d' % (rps, mcu_h))
    mcus_per_row = math.ceil(W / mcu_w)
    restart = mcus_per_row * (rps // mcu_h)
    if restart > 0xFFFF:
        raise Bad('restart interval %d too large' % restart)

    # colour space signalling
    cids = [c[0] for c in comps]
    app14 = b''
    if spp == 3:
        if photo == 2:      # RGB stored as-is
            if cids != [82, 71, 66]:
                raise Bad('RGB photometric but component ids %r' % cids)
            body = b'Adobe\x00\x64\x00\x00\x00\x00\x00\x00'   # version 100, transform 0
            app14 = b'\xff\xee' + struct.pack('>H', len(body)+2) + body
        elif photo == 6:    # YCbCr
            body = b'Adobe\x00\x64\x00\x00\x00\x00\x00\x01'
            app14 = b'\xff\xee' + struct.pack('>H', len(body)+2) + body
        else:
            raise Bad('unsupported photometric %d' % photo)
    elif spp == 1:
        if photo not in (0, 1):
            raise Bad('unsupported photometric %d for 1 sample' % photo)
        if photo == 0:
            raise Bad('WhiteIsZero JPEG needs inversion; refusing')
    else:
        raise Bad('unsupported SamplesPerPixel %d' % spp)

    icc = raw(buf, tags, 34675)
    out = [b'\xff\xd8']
    if icc:
        out.append(icc_app2(icc))
    out.append(app14)
    out.append(tbl)
    # SOF with the full image height
    out.append(sof0[:5] + struct.pack('>H', H) + sof0[7:])
    out.append(b'\xff\xdd\x00\x04' + struct.pack('>H', restart))
    out.append(sos0)
    for i, data in enumerate(pieces):
        if i:
            out.append(bytes([0xFF, 0xD0 + ((i - 1) % 8)]))
        out.append(data)
    out.append(b'\xff\xd9')

    entropy = sum(len(p) for p in pieces)
    return b''.join(out), dict(W=W, H=H, spp=spp, photo=photo, rps=rps,
                               nstrips=nstrips, restart=restart, icc=len(icc or b''),
                               entropy=entropy, npages=len(ifds))


if __name__ == '__main__':
    import os, glob
    args = sys.argv[1:]
    outdir = 'jpeg'
    if '-o' in args:
        i = args.index('-o'); outdir = args[i+1]; del args[i:i+2]
    files = sorted(args) if args else sorted(glob.glob('*.tif'))
    os.makedirs(outdir, exist_ok=True)
    tin = tout = 0
    for p in files:
        jpg, info = convert(p)
        dst = os.path.join(outdir, os.path.splitext(os.path.basename(p))[0] + '.jpg')
        with open(dst, 'wb') as fh:
            fh.write(jpg)
        tin += os.path.getsize(p); tout += len(jpg)
        print('%s -> %s  %dx%d  %d strips  DRI=%d  %d -> %d bytes'
              % (p, dst, info['W'], info['H'], info['nstrips'], info['restart'],
                 os.path.getsize(p), len(jpg)))
    print('total: %.1f MB -> %.1f MB' % (tin/1e6, tout/1e6))
