"""步骤 3：每个 <prefix>_G*.md → 同名 PDF（A4 / 9.5pt / 紧排版 / 答案页另起）
用法：python build_pdf.py
"""
import re, html, os, glob
from playwright.sync_api import sync_playwright
from common import load_config, prefix

cfg = load_config()
pf = prefix(cfg)

CSS = """
  @page { size: A4; margin: 13mm 12mm; }
  body { font-family: "PingFang SC","Hiragino Sans GB","Microsoft YaHei",serif;
         font-size: 9.5pt; line-height: 1.5; color: #1a1a1a; }
  h1 { font-size: 15pt; text-align: center; margin: 0 0 4mm; letter-spacing: 1px; }
  h1.newpage { page-break-before: always; }
  h2 { font-size: 12pt; margin: 5mm 0 1.8mm; padding-bottom: 1mm;
       border-bottom: 1px solid #333; page-break-after: avoid; }
  h3 { font-size: 10.5pt; margin: 3mm 0 1.2mm; color: #2b4a8b; page-break-after: avoid; }
  h4 { font-size: 10pt; margin: 2.5mm 0 1mm; }
  p { margin: 0 0 1.6mm; text-align: justify; }
  strong { font-weight: 600; }
  code { background: #f2f4f7; padding: 0 2px; border-radius: 2px; font-family: inherit; }
  blockquote { margin: 0 0 3mm; padding: 1mm 3mm; color: #555;
               border-left: 2.5px solid #c9d3e4; background: #fafbfd; font-size: 9pt; }
  hr { border: none; border-top: 1px solid #d8dde6; margin: 3mm 0; }
"""

def inline(s):
    s = html.escape(s)
    s = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", s)
    s = re.sub(r"`([^`]+)`", r"<code>\1</code>", s)
    return s

def md_to_html(md_path):
    lines = open(md_path, encoding="utf-8").read().split("\n")
    body, i = [], 0
    while i < len(lines):
        line = lines[i].rstrip()
        if not line:
            i += 1
            continue
        if line.startswith("---"):
            body.append("<hr>")
            i += 1
            continue
        if line.startswith("> "):
            body.append(f"<blockquote>{inline(line[2:])}</blockquote>")
            i += 1
            continue
        m = re.match(r"^(#{1,4})\s+(.*)", line)
        if m:
            lvl, txt = len(m.group(1)), inline(m.group(2))
            cls = ' class="newpage"' if lvl == 1 and "参考答案" in txt else ""
            body.append(f"<h{lvl}{cls}>{txt}</h{lvl}>")
            i += 1
            continue
        buf = []
        while i < len(lines) and lines[i].strip() and not re.match(r"^(#{1,4}\s|> |---)", lines[i].strip()):
            buf.append(lines[i].strip())
            i += 1
        if buf:
            body.append("<p>" + "<br>".join(inline(b) for b in buf) + "</p>")
    return f"""<!DOCTYPE html><html lang="zh-CN"><head><meta charset="utf-8">
<style>{CSS}</style></head><body>{''.join(body)}</body></html>"""

srcs = sorted(glob.glob(str(cfg["_out"] / f"{pf}_G*.md")))
if not srcs:
    raise SystemExit("未找到 md，请先运行 fetch_wrong.py 与 build_md.py")

with sync_playwright() as p:
    b = p.chromium.launch(channel="chrome")
    for src in srcs:
        tmp = cfg["_data"] / (os.path.basename(src)[:-3] + ".html")
        open(tmp, "w", encoding="utf-8").write(md_to_html(src))
        out_pdf = src[:-3] + ".pdf"
        pg = b.new_page()
        pg.goto("file://" + str(tmp))
        pg.wait_for_timeout(800)
        pg.pdf(path=out_pdf, format="A4", print_background=True,
               margin={"top": "13mm", "bottom": "11mm", "left": "12mm", "right": "12mm"})
        pg.close()
        d = open(out_pdf, "rb").read()
        pages = len(re.findall(rb"/Type\s*/Page[^s]", d))
        print(f"已生成 {os.path.basename(out_pdf)} | {pages} 页 | {len(d)//1024} KB")
    b.close()
