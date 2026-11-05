# -*- coding: utf-8 -*-
"""从习题 PDF 中截取指定题目的完整区域（题干 + 选项 + 图形）。

用法：
  python qa_extract.py list  --pdf <path> [--pages 1-3]
      列出 PDF 中识别到的题号锚点（页码 / 题号 / 题干前 30 字），供确认定位
  python qa_extract.py crop  --pdf <path> --q 5,9 [--page 3] [--hint 关键词] --out <dir>
      截取指定题目 → <dir>/q05.png、q09.png 及 meta.json

设计要点：
  - 题目区域 = 本题题号行 → 下一题题号行（同页）；跨页时延续到下一页首个题号前
  - 4 倍渲染，保证打印清晰；只截真实版面，绝不做任何重绘
"""
import argparse, json, os, re, sys
import pymupdf

NUM_PATTERNS = [
    # 主题号：5. / 5、/ 5．（排除 4.07、18.84 这类小数：句点后不能紧跟数字）
    re.compile(r'^\s*(\d{1,3})\s*[.、．]\s*(?!\d)'),
    re.compile(r'^\s*第\s*(\d{1,3})\s*题'),
]
# 括号小问 (1)（1）只在主题号找不到时兜底，且不作为题目边界
SUB_PATTERNS = [re.compile(r'^\s*[（(]\s*(\d{1,3})\s*[)）]\s*')]
ZOOM = 4.0

def norm(s):
    return s.replace(" ", "").replace("\u3000", "")

def page_lines(page):
    """返回 [(y0, y1, x0, x1, text)]，按 y 排序"""
    out = []
    d = page.get_text("dict")
    for b in d["blocks"]:
        if b.get("type") != 0:
            continue
        for l in b["lines"]:
            txt = "".join(s["text"] for s in l["spans"]).strip()
            if txt:
                bb = l["bbox"]
                out.append((bb[1], bb[3], bb[0], bb[2], txt))
    out.sort(key=lambda x: x[0])
    return out

def anchors(page, include_sub=False):
    """识别本页题号锚点（同题号相邻 4pt 内去重）。
    ny1 = 题号数字 span 的底部：整行 bbox 可能被公式/大字号 span 撑高，
    边界判断一律用数字 span，避免把上一题卷进来或漏掉下一题。"""
    res, seen = [], []
    pats = NUM_PATTERNS + (SUB_PATTERNS if include_sub else [])
    for y0, y1, x0, x1, txt in page_lines(page):
        for pat in pats:
            m = pat.match(txt)
            if m:
                no = int(m.group(1))
                if any(s[0] == no and abs(s[1] - y0) < 4 for s in seen):
                    break
                seen.append((no, y0))
                # 找到行内以题号开头的 span，取其底部
                ny1 = y0 + (y1 - y0) * 0.6
                d = page.get_text("dict", clip=(x0, y0, x1, y1))
                for b in d["blocks"]:
                    if b.get("type") != 0:
                        continue
                    for l in b["lines"]:
                        for s in l["spans"]:
                            if s["text"].strip().startswith(m.group(0).strip()[:len(m.group(0).strip())]):
                                ny1 = s["bbox"][3]
                                break
                        else:
                            continue
                        break
                    else:
                        continue
                    break
                res.append({"no": no, "y0": y0, "y1": y1, "ny1": ny1,
                            "text": txt, "snippet": txt[:40]})
                break
    return res

def cmd_list(args):
    doc = pymupdf.open(args.pdf)
    pages = range(len(doc))
    if args.pages:
        a, _, b = args.pages.partition("-")
        pages = range(int(a) - 1, int(b or a))
    for pno in pages:
        for a in anchors(doc[pno]):
            print(f"P{pno+1}\t题{a['no']}\ty={a['y0']:.0f}\t{a['snippet']}")
    doc.close()

def find_question(doc, qno, page_hint=None, hint=None):
    """返回 (page_index, anchor)；主锚点找不到时兜底用括号小问"""
    def collect(include_sub):
        out = []
        for pno in range(len(doc)):
            if page_hint is not None and pno + 1 != page_hint:
                continue
            for a in anchors(doc[pno], include_sub=include_sub):
                if a["no"] == qno:
                    out.append((pno, a))
        return out

    cands = collect(False) or collect(True)
    if not cands:
        return None
    if hint:
        for pno, a in cands:
            pg = doc[pno]
            seg = pg.get_textbox(pymupdf.Rect(30, a["y0"], pg.rect.width - 30, min(a["y0"] + 120, pg.rect.height)))
            if norm(hint) in norm(seg):
                return (pno, a)
    return cands[0]

FOOTER_PAT = re.compile(
    r'^(奇辑工作室|.{0,12}工作室$|\d{1,3}$|第?[一二三四五六七八九十]+\s*[、．.].{0,18}$)')

def trim_tail(lines):
    """去掉区域尾部混入的页脚/页码/板块标题行，返回保留的行与新的 y_end"""
    while lines and FOOTER_PAT.match(lines[-1][4]):
        lines = lines[:-1]
    return lines, (lines[-1][1] + 8 if lines else None)

def crop_question(doc, pno, a, qno, out_dir, fname=None):
    """截取单题：本题锚点 y → 下一锚点 y（同页）；无下题时裁到本页正文末尾并判断是否跨页"""
    pg = doc[pno]
    W, H = pg.rect.width, pg.rect.height
    x0, x1 = 34, W - 34

    nxt = [x for x in anchors(pg) if x["y0"] > a["ny1"] + 2 and x["no"] != qno]
    if nxt:
        y_end, end_page, y_next_start = nxt[0]["y0"] - 2, pno, nxt[0]["y0"]
    else:
        # 无同页下题：先按本页正文末尾收（剔除页脚/板块标题）
        lines = [(y0, y1, xx0, xx1, t) for (y0, y1, xx0, xx1, t) in page_lines(pg) if y0 > a["ny1"] and y1 < H - 30]
        kept, y_end = trim_tail(lines)
        end_page, y_next_start = pno, None
        # 末行不是完整句（不以终止性标点收尾）→ 本题可能跨页，延续到下一页
        last_txt = kept[-1][4].strip() if kept else ""
        if last_txt and not re.search(r'[。？！）)”"：:]$', last_txt):
            for p2 in range(pno + 1, min(pno + 3, len(doc))):
                na = anchors(doc[p2])
                if na:
                    end_page, y_next_start = p2, na[0]["y0"] - 2
                    break

    # 起点：锚点行顶部略上收，但不得越过上一行的底部
    # （公式行会撑高整行 bbox，须以上一行真实底部为界，防止把上一题卷进来）
    prev_bottom = max((l[1] for l in page_lines(pg)
                       if l[1] <= a["y0"] + 4 and abs(l[0] - a["y0"]) > 0.5), default=0)
    y_start = max(a["y0"] - 3, prev_bottom + 1, 20)
    if end_page == pno:
        clip = pymupdf.Rect(x0, y_start, x1, y_end)
        pix = pg.get_pixmap(matrix=pymupdf.Matrix(ZOOM, ZOOM), clip=clip)
        pix.save(os.path.join(out_dir, fname or f"q{qno:02d}.png"))
    else:
        # 跨页：两页分别渲染后竖向拼接
        p1 = pg.get_pixmap(matrix=pymupdf.Matrix(ZOOM, ZOOM),
                           clip=pymupdf.Rect(x0, y_start, x1, H - 34))
        p2 = doc[end_page].get_pixmap(matrix=pymupdf.Matrix(ZOOM, ZOOM),
                                      clip=pymupdf.Rect(x0, 20, x1, y_next_start or (doc[end_page].rect.height - 34)))
        total_h = p1.height + p2.height + 12
        w = max(p1.width, p2.width)
        canvas = pymupdf.Pixmap(pymupdf.csRGB, pymupdf.IRect(0, 0, w, total_h), False)
        canvas.set_rect(canvas.irect, (255, 255, 255))
        y = 0
        for p in (p1, p2):
            ps = pymupdf.Pixmap(pymupdf.csRGB, p)
            ps.set_origin(0, y)
            canvas.copy(ps, ps.irect)
            y += p.height + 12
        canvas.save(os.path.join(out_dir, fname or f"q{qno:02d}.png"))

    # 文本（题干）
    txt = pg.get_textbox(pymupdf.Rect(x0, y_start, x1, y_end)).strip()
    if end_page != pno:
        txt += "\n" + doc[end_page].get_textbox(
            pymupdf.Rect(x0, 20, x1, y_next_start or (H - 34))).strip()
    return {
        "qno": qno,
        "page": pno + 1,
        "end_page": end_page + 1,
        "image": f"q{qno:02d}.png",
        "stem": txt,
    }

def canon(s):
    """卷名归一化：去【】（）/空格/连字符，去“答案”“解析”字样，用于匹配答案卷"""
    s = re.sub(r'[【】\[\]（）()\s\-—_·.。]', '', s)
    for w in ("答案", "解析", "参考答案", "试卷"):
        s = s.replace(w, "")
    return s

def find_answer_pdf(pdf_path):
    """在同目录找配对的答案卷（【答案】xxx / xxx-答案 / xxx解析）"""
    d = os.path.dirname(os.path.abspath(pdf_path))
    base = os.path.basename(pdf_path)
    key = canon(os.path.splitext(base)[0])
    for f in sorted(os.listdir(d)):
        if not f.lower().endswith(".pdf") or f == base:
            continue
        stem = os.path.splitext(f)[0]
        if not re.search(r'答案|解析', stem):
            continue
        if canon(stem) == key:
            return os.path.join(d, f)
    return None

def cmd_crop(args):
    os.makedirs(args.out, exist_ok=True)
    doc = pymupdf.open(args.pdf)
    qs = [int(x) for x in re.split(r'[,\s，、]+', args.q.strip()) if x]
    ans_pdf = args.answer_pdf or (None if args.no_answer else find_answer_pdf(args.pdf))
    adoc = pymupdf.open(ans_pdf) if ans_pdf and os.path.exists(ans_pdf) else None
    if adoc:
        print(f"[答案卷] {os.path.basename(ans_pdf)}")
    else:
        print("[答案卷] 未找到配对答案卷，答案页将留空待补", file=sys.stderr)
    metas = []
    for q in qs:
        hit = find_question(doc, q, args.page, args.hint)
        if not hit:
            print(f"[WARN] 未定位到题 {q}，请先用 list 查看锚点", file=sys.stderr)
            continue
        pno, a = hit
        m = crop_question(doc, pno, a, q, args.out)
        m["source_pdf"] = os.path.basename(args.pdf)
        m["source_title"] = os.path.splitext(os.path.basename(args.pdf))[0]
        if adoc:
            # 答案卷版式通常与原卷一致：优先在原卷同页找，避免同号多候选时截到知识点部分
            ahit = find_question(adoc, q, pno + 1, args.hint) or find_question(adoc, q, None, args.hint)
            if ahit:
                apno, aa = ahit
                crop_question(adoc, apno, aa, q, args.out, fname=f"q{q:02d}_ans.png")
                m["answer_img"] = f"q{q:02d}_ans.png"
                m["answer_page"] = apno + 1
                m["answer_source"] = os.path.basename(ans_pdf)
            else:
                print(f"[WARN] 答案卷中未定位到题 {q}", file=sys.stderr)
        metas.append(m)
        print(f"[OK] 题{q} → {m['image']}" + ("（含答案截图）" if m.get("answer_img") else "（无答案）"))
    meta_path = os.path.join(args.out, "meta.json")
    old = []
    if os.path.exists(meta_path):
        try:
            old = json.load(open(meta_path, encoding="utf-8"))
        except Exception:
            old = []
    json.dump(old + metas, open(meta_path, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"meta → {meta_path} （{len(metas)} 题）")
    doc.close()
    if adoc:
        adoc.close()

def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    p1 = sub.add_parser("list")
    p1.add_argument("--pdf", required=True)
    p1.add_argument("--pages")
    p2 = sub.add_parser("crop")
    p2.add_argument("--pdf", required=True)
    p2.add_argument("--q", required=True)
    p2.add_argument("--page", type=int)
    p2.add_argument("--hint")
    p2.add_argument("--out", required=True)
    p2.add_argument("--answer-pdf", help="指定答案卷；缺省则按卷名自动匹配同目录【答案】卷")
    p2.add_argument("--no-answer", action="store_true", help="不截取答案")
    args = ap.parse_args()
    cmd_list(args) if args.cmd == "list" else cmd_crop(args)

if __name__ == "__main__":
    main()
