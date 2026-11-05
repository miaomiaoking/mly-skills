# PDF 错题收录 · 技术参考

## 1. 题号锚点识别（qa_extract.py）

- 主锚点正则：`^\s*(\d{1,3})\s*[.、．]\s*(?!\d)` 和 `^\s*第\s*(\d{1,3})\s*题`。
  负向断言 `(?!\d)` 排除小数误判（`4.07 公顷`、`18.84 厘米`、`0.625 × 2`）。
- 括号小问 `（1）(1)` 默认**不作为锚点也不作为边界**；仅当主锚点找不到该题号时兜底启用（`find_question` 的 `include_sub=True` 二次扫描）。
- 同一题号在 4pt 内出现多次（题号行与题干行分开排版时）会去重。
- 题号按板块重新编号很常见（填空题 1-12、应用题 1-5），所以 `crop` 支持也鼓励 `--page` + `--hint`：
  - `--page N`：只在第 N 页找；
  - `--hint "关键词"`：取题干前 120 字含该关键词的候选。

## 2. 截取区域判定

- **锚点边界用「题号数字 span 的 bbox」（anchor 的 `ny1`），不用整行 bbox**——
  含上下结构分数/大公式的行会被数学字体 span 撑高（实测一行 bbox 从 582→618 横跨前后两题），
  用整行 bbox 判边界会把上一题卷进来、或因 `x.y0 > a.y1` 漏判下一题。
- 区域 = 本题锚点行 y0（与上一行底部取大者，再上移 ≤3pt）→ 同页下一锚点 y0（上移 2pt），
  横向取正文宽度（34pt ~ 页宽-34pt）。
- 本页无下一锚点时（本题是本页最后一题）：
  1. 取锚点数字 span 底部以下、页底以上的所有文本行，用 `FOOTER_PAT` 从尾部剔除页脚行
     （`奇辑工作室`、纯页码、`一、二、…` 开头的板块标题、`××工作室`）；
  2. 剩余最后一行若**不以终止性标点**（`。？！））”"：:`）收尾 → 判定本题跨页，
     延续到后续 1 页的首个锚点前；两页分别 4 倍渲染后竖向白底拼接。
- 渲染倍率 ZOOM=4（约 288 DPI），A4 页单题 PNG 约 30~150KB。

## 2b. 答案截取

- `crop` 默认在同目录按卷名配对答案卷：归一化（去`【】（）/-—_·.空白`、去「答案/解析/参考答案/试卷」字样）后相等的即配对，
  如《第15节课直播测试-提升卷04.pdf》↔《【答案】第15节课直播测试—提升卷04.pdf》（连字符全半角不同也能配对）。
- 答案卷里题目与原卷同版式、空格处已填答案，按同题号锚点截取 → `q{no}_ans.png`，目检确认数值确实已填。
- 找不到答案卷/答案卷无该题号：答案页该条显示「（答案待补）」，可后续用 `wrongbook.py answer --q N --text ...` 补文本，
  或用户补充后重截。

## 3. 错题本数据格式（wrongbook.py）

- 目录：`config.json` 的 `book_dir`（默认 `~/个人信息/宋泽辰/数学/错题本`）。
- 数据源 `<名称>.json` 是唯一真源；`.html` / `.pdf` 由 `render` 全量重生成，随时可重建。
- 图片副本：`<book_dir>/figs/<名称>/<来源>_q05.png` 与 `<来源>_q05_ans.png`（文件名清洗过，防特殊字符）。
- 排版（对齐《数学错题练习集-51题-天苗-原图溯源版》，用户指定参考）：
  - 封面标题区不独占整页（`page-break-after:auto`），紧接题目；
  - 每题一卡（page-break-inside:avoid）：右上「原题出处」**黑字无底色** + 左上题号 + 原题截图；
  - 文末**答案页** `page-break-before:always` 单独成页，`column-count:2` 两栏紧凑，
    每条 = 橙色题号 + 答案文本/答案截图 + 出处；按卷名分块，块标题浅橙底。
  题干 OCR 文本**只存 json 不展示**——截图即原题，避免 OCR 噪声重复出现；图片缺失时才回退展示文本。
- PDF 生成：无头 Chrome `--headless=new --no-pdf-header-footer --print-to-pdf`，A4。

## 4. ima 上传链路（已实测）

```
get_knowledge_list（查重名）
  → create_media(apply_upload_mode=1, content_type=application/pdf, file_size=实测)
      返回 media_id + upload_url.presigned_url + auth_headers
  → ima_put.py --url <presigned_url> --file <pdf> --headers '<auth_headers JSON>'
      HTTP 200 即上传成功
  → add_knowledge(media_id, folder_id, knowledge_base_id,
        duplicate_name_strategy: 重名 REPLACE / 新名 SAVE)
  → get_knowledge_list 回查
```

- `auth_headers` 必须原样携带（Content-Type / x-cos-acl / Content-Length），Content-Length 值必须与 create_media 申报的 file_size 完全一致——**申报前一刻 stat 实测**，任何重新渲染都会改变文件大小（血泪教训：渲染后未重新申报 → 403）。
- presigned_url 有效期约 12 小时（url_expired_ts），单次 PUT。
- 只 PUT 不 add_knowledge 时文件是孤儿对象，**不会出现在知识库里**，可用于测试。
- 环境有 HTTP(S)_PROXY（127.0.0.1），实测经代理 PUT 正常；若遇 SSL 中断可加 `--no-proxy` 直连。

## 5. 已知边界

- 扫描件无文字层时 `list` 无锚点：只能 `--page` + 人工指定 y 范围，或请用户指明页码后整页截图。
- 选择题选项在图中的题、选项跨行的题：区域按行边界裁剪，选项行属普通文本行，不会被误剔。
- 双栏排版试卷未验证；当前实现假设单栏。
