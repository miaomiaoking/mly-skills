---
name: pdf-wrong-question-collector
description: 从用户给的习题 PDF 中按"哪道题错了"截取原题（题干+图形，绝不重绘），插入用户指定的错题本文件（无则新建、有则追加），并上传到 ima「数学/错题本」。当用户说"这道题错了""第X题错了，加到错题本""把错题收进错题本""PDF 里的错题截出来"时使用。
agent_created: true
---

# PDF 错题收录

## 用途

用户发来一份习题 PDF，并指出"第 5 题、第 9 题错了"。本技能负责：
1. 从 PDF 中**按题截取完整区域**（题号、题干、选项、图形，4 倍渲染），并**自动在同目录找配对的【答案】卷截取该题答案**；
2. **询问用户要加进哪个错题本**（列出已有的让其选，也可新建）；
3. 追加进该错题本并重渲染 HTML + PDF（版式对齐《数学错题练习集-51题-天苗-原图溯源版》：封面不独占整页、每题右上黑字出处、**文末答案单独成页**）；
4. 上传/覆盖到 ima「数学 → 错题本」。

## 铁律

- **只截原版面，绝不重绘、绝不脑补**任何图形或题干文字。
- 截图必须**目检**（用 ViewImage 逐张看）：题干是否完整、图形是否被裁掉、有没有把下一题带进来。不合格就调 `--page/--hint` 或改坐标重截，不许直接交付。
- **目标错题本必须由用户选**，不许默认塞进某一个；用户没选就问。
- 追加时先查重（同来源 + 同题号），重名默认跳过，确认要覆盖才加 `--replace`。

## 路径与命令

```
PY=/Users/miaoliyun/.workbuddy/binaries/python/envs/default/bin/python
S=~/.workbuddy/skills/pdf-wrong-question-collector/scripts
BOOKS=~/个人信息/宋泽辰/数学/错题本
```

## 执行流程

### 1. 确认输入

需要两样东西，缺哪个问哪个（不要猜题号）：
- 习题 PDF 的本地绝对路径（用户可能只给了文件名，先在 `~/个人信息/宋泽辰/数学/`、`~/Downloads`、`~/Desktop` 里 `mdfind -name` 找）；
- 错题题号，支持 `5`、`5,9`、`5-7`。

### 2. 定位并截取

```bash
$PY $S/qa_extract.py list --pdf "<PDF>"          # 先看锚点：P页码 / 题号 / 题干前40字
$PY $S/qa_extract.py crop --pdf "<PDF>" --q 5,9 --out /tmp/wq_<时间戳>
```

- `crop` 会**自动在同目录匹配答案卷**（卷名含「答案/解析」且归一化后与原卷同名，如《【答案】第9节课基础卷02.pdf》），并额外截取该题答案 → `q05_ans.png`。匹配不到会提示，答案页留"待补"。
  - 手动指定：`--answer-pdf <路径>`；跳过答案：`--no-answer`。
- `list` 出现同题号多候选（卷一/卷二各自编号）时，用题干关键词 `--hint "关键词"` 或 `--page N` 指定。
- 输出：`q05.png`、`q05_ans.png`、`meta.json`（含 qno/page/stem/answer_img/answer_source）。
- **逐张 ViewImage 目检**（题目截图和答案截图都要看）：图像是否从题号开始、到下一题之前结束；图形边缘是否被切；跨页题是否拼接正确；**答案截图里数值是否真的已填入**。印章、页眉页脚混入属正常，可接受。

### 3. 询问目标错题本（必做）

```bash
$PY $S/wrongbook.py list
```

把结果整理成选项，用 **AskUserQuestion** 让用户选：
- 已存在的每个错题本一项（显示"名称 · N 题"）；
- 加一项「新建错题本」（选它再问名称，默认 `数学错题本`）。
用户明确说了文件名的，直接匹配；匹配不到就按新建处理并告知。

### 4. 追加并渲染

```bash
$PY $S/wrongbook.py add --book "<错题本名>" --meta /tmp/wq_<时间戳>/meta.json
# 确认要覆盖同名同题号的旧条目时加 --replace
```

输出 `$BOOKS/<名称>.json`（数据源）、`.html`、`.pdf`。版式（对齐溯源版）：
- 封面标题区不独占整页，紧接题目；
- 每题一卡：右上「原题出处：卷名 · 第 N 页」**黑字无底色**，左上蓝色题号，下方原题截图；
- **答案页单独成页**（新起一页，两栏紧凑）：每条 = 橙色题号 + 答案文本或答案截图 + 出处；答案缺失标「（答案待补）」。

答案补充/人工确认：用户口述答案时写入文本（与答案截图并存）：

```bash
$PY $S/wrongbook.py answer --book "<错题本名>" --q 5 --text "比例尺 1:5000000"
```

### 5. 上传 ima

目标：`config.json` 的 `kb`（默认 数学 / ima_kb_2FBXYE1j / 文件夹 folder_7522967156182865「错题本」）。

1. `mcp__ima-mcp__get_knowledge_list`（`folder_id` = kb.folder_id）查同名文件是否存在；
2. `mcp__ima-mcp__create_media`：`apply_upload_mode=1`、`content_type=application/pdf`、`file_ext=pdf`、`file_name=<名称>.pdf`、`file_size=<字节数>`、`knowledge_base_id`。
   ⚠️ **file_size 必须在调用前一刻 `stat -f%z` 实测**——渲染或任何写操作之后文件会变，拿旧值会 403（Content-Length 与签名不符）；
3. 用返回的 `upload_url.presigned_url` + `auth_headers` 上传：

```bash
$PY $S/ima_put.py --url "<presigned_url>" --file "$BOOKS/<名称>.pdf" --headers '<auth_headers JSON>'
```

4. `mcp__ima-mcp__add_knowledge`：`media_id` + `folder_id` + `knowledge_base_id`，
   重名策略：已存在 → `DUPLICATE_NAME_STRATEGY_REPLACE`，不存在 → `DUPLICATE_NAME_STRATEGY_SAVE`；
5. 回查 `get_knowledge_list`：条目数不重复、`parse_progress` 会异步到位。

上传失败（鉴权/超限）时如实报错，不要重试超过一次，本地文件仍然有效。

### 6. 交付

报告：收了哪几题、来自哪个 PDF 第几页、进了哪本错题本（现共 N 题）、本地 HTML/PDF 路径、ima 上传结果（新增/覆盖/失败）。把 PDF 用 present_files 打开给用户看。

## 常见问题

| 现象 | 处理 |
|---|---|
| 题号找不到 | PDF 可能是扫描件无文字层；先 `list --pages` 看范围，仍无锚点则用 `--page` + 手动坐标裁剪（脚本 `crop_question` 的 y 范围可改），或请用户指明页码 |
| 截到一半图形 | 题图常位于题干右侧或被下一题挤压，检查 `list` 的下一个锚点位置；必要时在脚本里把 `y_end` 放宽 6→20pt 后重截 |
| 跨页题拼接错 | `crop_question` 支持跨 2 页；超过 2 页的长题请分页截两张并人工确认 |
| 错题本被误覆盖 | 数据源是 `$BOOKS/<名称>.json`，改回 json 后 `wrongbook.py render --book <名称>` 即可重排 |

## 详细参考

题号锚点规则、区域判定逻辑、HTML 排版参数：`references/rules.md`。
面向用户的通俗使用说明（用户问"这个 skill 怎么用/能干什么"时展示）：`USAGE.md`。
