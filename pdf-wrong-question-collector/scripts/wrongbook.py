# -*- coding: utf-8 -*-
"""错题本管理：新建 / 追加题目 / 渲染 HTML+PDF。

版式对齐《数学错题练习集-51题-天苗-原图溯源版》：
  · 封面区不独占整页，标题后紧接题目
  · 每题：右上「原题出处」黑字（无底色）+ 题号 + 原题截图
  · 文末「答案页」单独成页，两栏紧凑，含答案内容与出处

数据文件 <book_dir>/<name>.json：
  {"title": "...", "subject": "数学", "entries": [
      {"qno": 5, "source_title": "第9节课基础卷02", "page": 3,
       "image": "figs/<name>/xxx_q05.png",
       "answer_img": "...q05_ans.png", "answer": "答案文本", "note": "", "added": "2026-11-05"}]}

用法：
  python wrongbook.py list
  python wrongbook.py add --book "数学错题本" --meta <extract_out>/meta.json [--replace]
  python wrongbook.py answer --book "数学错题本" --q 5 --text "答案内容" [--source 卷名]
  python wrongbook.py render --book "数学错题本"
"""
import argparse, base64, datetime, json, os, re, shutil, subprocess

SKILL = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CFG = json.load(open(os.path.join(SKILL, "config.json"), encoding="utf-8"))
BOOK_DIR = os.path.expanduser(CFG["book_dir"])
CHROME = CFG.get("chrome", "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome")

CSS = """
@page{size:A4;margin:15mm 14mm}
*{box-sizing:border-box}
body{font-family:"Songti SC","STSong","SimSun",serif;font-size:11.5pt;line-height:1.7;color:#1a1a1a;margin:0;padding:0}
.cover{text-align:center;padding:4px 0 2px;page-break-after:auto;margin-bottom:6px}
.cover h1{font-family:"PingFang SC","Heiti SC",sans-serif;font-size:20pt;color:#0f3d6b;margin:0 0 4px}
.cover .sub{font-size:13pt;color:#455a64}
.cover .meta{font-size:11pt;color:#78909c;margin-top:8px;line-height:1.6}
.legend{font-size:10.5pt;color:#607d8b;background:#fff8e1;border:1px solid #ffe082;padding:7px 11px;border-radius:4px;margin:8px 0 14px}
h2.sec{font-family:"PingFang SC","Heiti SC",sans-serif;font-size:16pt;color:#fff;background:#1565c0;padding:6px 12px;border-radius:4px;margin:16px 0 10px;page-break-after:avoid}
.prob{border:1px solid #cfd8dc;border-radius:6px;padding:11px 13px;margin:10px 0;page-break-inside:avoid}
.prob .no{font-family:"PingFang SC",sans-serif;font-weight:700;color:#0f3d6b;font-size:13.5pt}
.prob .src{float:right;font-size:10pt;color:#1a1a1a;background:none;padding:2px 0;font-weight:400;max-width:62%}
.prob img{display:block;max-width:100%;margin:8px auto 0;clear:both;border:1px solid #eceff1}
.prob .note{font-size:10pt;color:#b71c1c;margin-top:4px}
.empty{color:#90a4ae;font-size:11pt;padding:20px 0}
/* 答案页 */
.anspage{page-break-before:always}
.anslist{column-count:2;column-gap:22px}
.ansitem{break-inside:avoid;font-size:11.5pt;line-height:1.5;margin:0 0 7px 0;
         padding:5px 8px;border-left:3px solid #ff9800;background:#fafafa;border-radius:3px}
.ansitem b{color:#e65100}
.ansitem .as{color:#607d8b;font-size:10.5pt}
.ansitem .aw{color:#bf360c;font-size:10.5pt}
.ansitem img{display:block;width:100%;margin-top:5px;border:1px solid #eceff1}
.ansgrp{background:#fff3e0;border-left-color:#e65100}
"""

def book_path(name):
    return os.path.join(BOOK_DIR, name + ".json")

def load(name):
    p = book_path(name)
    if not os.path.exists(p):
        return {"title": name, "subject": "数学", "created": str(datetime.date.today()), "entries": []}
    return json.load(open(p, encoding="utf-8"))

def save(name, data):
    os.makedirs(BOOK_DIR, exist_ok=True)
    json.dump(data, open(book_path(name), "w", encoding="utf-8"), ensure_ascii=False, indent=1)

def cmd_list(args):
    if not os.path.isdir(BOOK_DIR):
        print("（目录不存在）" + BOOK_DIR); return
    files = [f for f in os.listdir(BOOK_DIR) if f.endswith(".json")]
    if not files:
        print("（暂无错题本）"); return
    for f in sorted(files):
        d = json.load(open(os.path.join(BOOK_DIR, f), encoding="utf-8"))
        print(f"{f[:-5]}\t{len(d.get('entries', []))} 题\t{BOOK_DIR}")

def _copy_fig(src, book, prefix, qno, kind=""):
    fig_dir = os.path.join(BOOK_DIR, "figs", book)
    os.makedirs(fig_dir, exist_ok=True)
    name = f"{re.sub(r'[^0-9A-Za-z一-龥]+', '', prefix)[:12]}_q{qno:02d}{kind}.png"
    shutil.copy(src, os.path.join(fig_dir, name))
    return os.path.relpath(os.path.join(fig_dir, name), BOOK_DIR)

def cmd_add(args):
    data = load(args.book)
    meta = json.load(open(args.meta, encoding="utf-8"))
    if isinstance(meta, dict):
        meta = [meta]
    base = os.path.dirname(os.path.abspath(args.meta))
    added, skipped, no_ans = 0, 0, []
    for m in meta:
        qno, src = m["qno"], m.get("source_title", "")
        exists = [e for e in data["entries"] if e["qno"] == qno and e["source_title"] == src]
        if exists and not args.replace:
            skipped += 1
            continue
        if exists:
            data["entries"] = [e for e in data["entries"] if not (e["qno"] == qno and e["source_title"] == src)]
        img = _copy_fig(os.path.join(base, m["image"]), args.book, src, qno)
        ans_img = ""
        if m.get("answer_img") and os.path.exists(os.path.join(base, m["answer_img"])):
            ans_img = _copy_fig(os.path.join(base, m["answer_img"]), args.book, src, qno, "_ans")
        else:
            no_ans.append(qno)
        data["entries"].append({
            "qno": qno,
            "source_title": src,
            "page": m.get("page"),
            "image": img,
            "answer_img": ans_img,
            "answer": m.get("answer", ""),
            "answer_source": m.get("answer_source", ""),
            "note": m.get("note", ""),
            "added": str(datetime.date.today()),
        })
        added += 1
    data["entries"].sort(key=lambda e: (e.get("added", ""), e["source_title"], e["qno"]))
    save(args.book, data)
    print(f"[{args.book}] 新增 {added} 题，跳过重复 {skipped} 题，共 {len(data['entries'])} 题")
    if no_ans:
        print(f"[提示] 以下题未取到答案截图，答案页留空待补：{'、'.join('题%d' % q for q in no_ans)}")
    render(args.book, data)

def cmd_answer(args):
    """为某题补写/更新答案文本（答案截图之外的人工确认答案）"""
    data = load(args.book)
    qs = [int(x) for x in re.split(r'[,\s，、]+', str(args.q).strip()) if x]
    hit = 0
    for e in data["entries"]:
        if e["qno"] in qs and (not args.source or args.source in e["source_title"]):
            e["answer"] = args.text
            hit += 1
    save(args.book, data)
    print(f"已更新 {hit} 条答案")
    render(args.book, data)

def _uri(p):
    return "data:image/png;base64," + base64.b64encode(open(p, "rb").read()).decode()

def render(name, data):
    entries = data["entries"]
    groups = {}
    for e in entries:
        groups.setdefault(e["source_title"], []).append(e)
    h = ['<!DOCTYPE html><html lang="zh-CN"><head><meta charset="utf-8">'
         f'<title>{data["title"]}</title><style>{CSS}</style></head><body>']

    # ── 封面：不独占整页 ──
    h.append('<div class="cover"><h1>%s</h1>'
             '<div class="sub">%s · 原题截图 + 答案</div>'
             '<div class="meta">共 %d 题 · 来自 %d 份原卷<br>'
             '题目与答案截图均直接取自原卷 PDF 版面，未做任何重绘或改写<br>'
             '更新日期：%s</div></div>'
             % (data["title"], data.get("subject", "数学"), len(entries), len(groups),
                datetime.date.today()))
    h.append('<div class="legend"><b>说明：</b>① 每题右上角为<b>原题出处</b>（卷名 · 页码）；'
             '② 题目区为原卷版面截图，图形随原题一并保留；'
             '③ 全部答案统一附于文末<b>「答案页」</b>（单独成页，不与题目混排）。</div>')

    if not entries:
        h.append('<div class="empty">（暂无错题）</div>')

    # ── 题目区 ──
    for src, items in groups.items():
        h.append('<h2 class="sec">%s（%d 题）</h2>' % (src, len(items)))
        for e in items:
            h.append('<div class="prob">')
            h.append('<span class="src">原题出处：%s%s</span>'
                     % (e["source_title"], f' · 第 {e["page"]} 页' if e.get("page") else ''))
            h.append('<span class="no">题目 %d</span>' % e["qno"])
            img = os.path.join(BOOK_DIR, e["image"]) if e.get("image") else ""
            if img and os.path.exists(img):
                h.append('<img src="%s" alt="题%d">' % (_uri(img), e["qno"]))
            h.append('<div style="clear:both"></div>')
            if e.get("note"):
                h.append('<div class="note">⚠ %s</div>' % e["note"])
            h.append('</div>')

    # ── 答案页：单独成页 ──
    h.append('<div class="anspage"><h2 class="sec" style="margin-top:0">答案页（全部 %d 题 · 单独成页）</h2>'
             % len(entries))
    h.append('<div class="anslist">')
    for src, items in groups.items():
        h.append('<div class="ansitem ansgrp"><b>%s</b></div>' % src)
        for e in items:
            ans = (e.get("answer") or "").strip()
            item = '<div class="ansitem"><b>题 %d</b>　%s' % (
                e["qno"], ans if ans else ('<span class="as">见下方原卷答案截图</span>' if e.get("answer_img") else '<span class="aw">（答案待补）</span>'))
            if e.get("note"):
                item += '<br><span class="aw">⚠ %s</span>' % e["note"]
            aimg = os.path.join(BOOK_DIR, e["answer_img"]) if e.get("answer_img") else ""
            if aimg and os.path.exists(aimg):
                item += '<img src="%s" alt="题%d答案">' % (_uri(aimg), e["qno"])
            item += '<br><span class="as">出处：%s%s</span></div>' % (
                e["source_title"], f' · 第 {e["page"]} 页' if e.get("page") else '')
            h.append(item)
    h.append('</div></div>')
    h.append('</body></html>')

    os.makedirs(BOOK_DIR, exist_ok=True)
    hp = os.path.join(BOOK_DIR, name + ".html")
    open(hp, "w", encoding="utf-8").write("\n".join(h))
    pp = os.path.join(BOOK_DIR, name + ".pdf")
    if os.path.exists(CHROME):
        subprocess.run([CHROME, "--headless=new", "--disable-gpu", "--no-sandbox",
                        "--no-pdf-header-footer", f"--print-to-pdf={pp}", f"file://{hp}"],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=180)
        print("输出：", pp if os.path.exists(pp) else "(PDF 生成失败，HTML 已生成)")
    else:
        print("未找到 Chrome，仅生成 HTML：", hp)

def cmd_render(args):
    render(args.book, load(args.book))

def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("list")
    a = sub.add_parser("add"); a.add_argument("--book", required=True); a.add_argument("--meta", required=True)
    a.add_argument("--replace", action="store_true")
    b = sub.add_parser("answer"); b.add_argument("--book", required=True); b.add_argument("--q", required=True)
    b.add_argument("--text", required=True); b.add_argument("--source")
    r = sub.add_parser("render"); r.add_argument("--book", required=True)
    args = ap.parse_args()
    {"list": cmd_list, "add": cmd_add, "answer": cmd_answer, "render": cmd_render}[args.cmd](args)

if __name__ == "__main__":
    main()
