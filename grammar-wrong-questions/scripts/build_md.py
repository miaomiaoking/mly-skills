"""步骤 2：把 wrong_all.json 按 G 级别拆成多个 MD
输出：<cwd>/语法错题整理_G1.md、_G2.md …（练习题在前 + 独立答案页）
"""
import json, re, html, datetime
from collections import Counter, OrderedDict
from common import load_config, wrong_json, dict_json, prefix

cfg = load_config()
data = json.load(open(wrong_json(cfg), encoding="utf-8"))
dic = json.load(open(dict_json(cfg), encoding="utf-8"))["data"]

MODULE, POINT = {}, {}
def walk(nodes):
    for n in nodes:
        iv = n.get("itemValue", "")
        if iv.startswith("G") and iv.count("-") == 1:
            MODULE[iv] = n["name"].strip()
        if iv.startswith("G") and iv.count("-") == 2:
            POINT[iv] = n["name"].strip()
        walk(n.get("children") or [])
walk(dic)

def clean(s):
    if not s:
        return ""
    s = re.sub(r"<br\s*/?>", "\n", s)
    s = re.sub(r"</p>\s*<p[^>]*>", "\n", s)
    s = re.sub(r"<[^>]+>", "", s)
    s = html.unescape(s).replace("\u00a0", " ").replace("\u3000", " ")
    return "\n".join(x.strip() for x in s.split("\n") if x.strip())

def parse_answer(x):
    if not x:
        return []
    if isinstance(x, str):
        try:
            x = json.loads(x)
        except Exception:
            return [x]
    out = []
    for row in x:
        out.extend([str(i) for i in row] if isinstance(row, (list, tuple)) else [str(row)])
    return out

TYPE_NAME = {"choiceFill": "选择填空", "choice": "单项选择", "blank": "填空题",
             "lightup": "点亮选词", "sentence": "连词成句", "correction": "改错题"}
TYPE_ORDER = ["choice", "choiceFill", "blank", "lightup", "sentence", "correction"]
LETTERS = "ABCDEFGH"

rows = []
for o in data:
    q, r = o["question"], o["record"]
    if not q:
        continue
    try:
        qm = json.loads(q["questionModel"])
    except Exception:
        qm = {}
    rows.append({
        "g": r["grammarItemValue"], "p": r["pointItemValue"],
        "topic": (r.get("practiceContent") or "").strip(),
        "type": qm.get("typeCode", "?"),
        "title": clean(qm.get("questionTitle")),
        "options": [clean(x) for x in (qm.get("options") or [])],
        "remark": clean(qm.get("questionRemark")),
        "answer": parse_answer(q.get("referenceAnswer")),
        "seq": q.get("sequenceNo") or 0,
    })

rows.sort(key=lambda x: (x["g"], x["p"], x["topic"],
                         TYPE_ORDER.index(x["type"]) if x["type"] in TYPE_ORDER else 99, x["seq"]))

def fmt_answer(x):
    ans = x["answer"]
    if not ans:
        return ""
    items = [a.replace("##", "").replace("||", " → ") for a in ans]
    opts = [o.replace("##", "") for o in x["options"]]
    labeled = []
    for a in items:
        if a in opts and x["type"] in ("choiceFill", "choice"):
            i = opts.index(a)
            labeled.append(f"{LETTERS[i]}. {a}" if i < len(LETTERS) else a)
        else:
            labeled.append(a)
    return "；".join(labeled)

def fmt_q(x, idx):
    parts = [f"**{idx}.（{TYPE_NAME.get(x['type'], x['type'])}）**"]
    if x["remark"]:
        parts.append(f"> {x['remark']}")
    t = x["title"]
    if x["type"] == "lightup":
        parts.append(t.replace("##", ""))
        parts.append("候选词：" + " / ".join(o.replace("##", "") for o in x["options"]))
    elif x["type"] == "correction":
        fixed = re.sub(r"##([^#]+)##", lambda m: m.group(1).split("||")[0], t)
        parts.append("原句：" + fixed)
        bad = re.findall(r"##([^#]+)##", t)
        if bad:
            parts.append("需修改之处：`" + "`、`".join(b.replace("||", " → ") for b in bad) + "`")
    elif x["type"] == "sentence":
        parts.append(t)
        parts.append("备选词：" + " / ".join(x["options"]))
        if x["answer"]:
            s = ""
            for tok in x["answer"]:
                s += tok if (not s or tok in ".,!?;:") else " " + tok
            return "\n\n".join(parts), s
    else:
        parts.append(t)
        if x["options"]:
            if len(x["options"]) <= 6:
                parts.append("　".join(f"{LETTERS[i]}. {o}" for i, o in enumerate(x["options"])))
            else:
                parts.append(" / ".join(x["options"]))
    return "\n\n".join(parts), fmt_answer(x)

groups = OrderedDict()
for x in rows:
    groups.setdefault(x["g"].split("-")[0], []).append(x)

today = datetime.date.today().isoformat()
pf = prefix(cfg)
total = 0
for gname, items in groups.items():
    doc = [f"# {pf} · {gname}", "",
           "> 来源：Grammar Island · 巩固 → 已改错",
           f"> 账号：{cfg.get('student_name', '')}",
           f"> 共 {len(items)} 题｜生成日期：{today}", "", "---"]

    n = 0          # 册内累计题数（用于统计）
    seq = 0        # 每个级别独立编号
    answers = []
    cur_g = cur_p = cur_topic = None
    for x in items:
        if x["g"] != cur_g:
            cur_g = x["g"]
            doc += ["", f"## {cur_g}　{MODULE.get(cur_g, cur_g)}", ""]
            cur_p = cur_topic = None
            seq = 0                      # 级别切换 → 编号归 1
        if x["p"] != cur_p or x["topic"] != cur_topic:
            cur_p, cur_topic = x["p"], x["topic"]
            doc += ["", f"### {POINT.get(cur_p, cur_p)}　—　{x['topic']}", ""]
        n += 1
        seq += 1
        body, ans = fmt_q(x, seq)
        doc += [body, ""]
        answers.append((seq, x, ans))

    doc += ["", "---", "", "# 参考答案", "", "> 按级别内题号对照，建议做完后再翻看。", ""]
    cur_g = None
    for idx, x, ans in answers:
        if x["g"] != cur_g:
            cur_g = x["g"]
            doc += ["", f"## {cur_g}　{MODULE.get(cur_g, cur_g)}", ""]
        doc.append(f"{idx}. {ans if ans else '—'}")
    doc.append("")

    s = re.sub(r"\n{3,}", "\n\n", "\n".join(doc))
    path = cfg["_out"] / f"{pf}_{gname}.md"
    open(path, "w", encoding="utf-8").write(s)
    total += n
    mods = ", ".join(sorted({x["g"] for x in items}))
    print(f"已生成 {path.name} | {n} 题 | 模块 {mods}")

print("合计:", total, "题 |", dict(Counter(x["type"] for x in rows)))
