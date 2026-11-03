---
name: grammar-wrong-questions
description: 抓取并整理 Grammar Island（grammar.lehaiya.com）的英语语法错题，按 G1/G2/G3 分册生成 Markdown 与 PDF，并可上传到 ima「石头知识库 → 英语 → 语法」。当用户提到"整理错题""抓错题""错题生成文档/PDF""更新语法错题""Grammar Island 错题"等需求时使用；也适用于只要求重排已有错题文档（原样摘录、答案单独成页、排版紧凑）的场景。
agent_created: true
---

# 语法错题整理

## 用途

从 grammar.lehaiya.com 的「巩固 → 已改错」抓取学生全部错题，按 G 级别拆成多份文档，每份含"练习题（无答案）+ 独立答案页"，输出 MD 与 PDF，可选上传 ima 知识库。

## 何时使用

- 用户要求"整理错题""把错题生成文档/PDF""更新一下语法错题"
- 用户要求把已有错题内容重新排版（原样摘录、答案单独成页、排版紧凑、按 G 分册）

## 关键约定（务必遵守）

- **错题源**：`correctFlag=1`（已改错）。`correctFlag=0` 是"错题"页，当前为空，不要用它。
- **分册**：按 `grammarItemValue` 的 G 前缀拆分，G1-1/G1-2… 归 G1。文件名 `<前缀>_G1.md`、`_G2.md`。
- **内容**：原样摘录，**不写考点、不写解析、不加汇总表**；题目不用表格展示；选项一行排列 `A. xx　B. xx`。
- **结构**：练习题在前（无答案）→ `---` → `# 参考答案` 独立成节；答案按级别分组、组内编号对应。
- **编号**：题号在**每个级别（G{x}-{y} 模块）内部从 1 重新开始**，不是整册连续编号（G1-1 为 1–22、G1-2 为 1–9…；G2-5 为 1、G2-6 为 1–6）。
- **PDF**：A4、9.5pt、行距 1.5、边距 13/12mm；仅"参考答案"强制另起一页；`---` 不可设分页。
- **上传**：先查目录同名，存在则 REPLACE 覆盖，不存在才 SAVE。

## 执行流程

工作目录 = 用户当前工作区（脚本以 cwd 为根，输出到 cwd，数据缓存到 `cwd/.grammar_wrong/`）。配置在技能目录 `config.json`。

```bash
PY=/Users/miaoliyun/.workbuddy/binaries/python/envs/default/bin/python
S=~/.workbuddy/skills/grammar-wrong-questions/scripts

$PY $S/fetch_wrong.py        # 抓取（会话失效自动重登；--relogin 强制重登）
$PY $S/build_md.py           # 按 G 拆册出 MD
$PY $S/build_pdf.py          # 每册出 PDF
# 或一键：$PY $S/run_all.py
```

执行后向用户报告：每册题数、PDF 页数、与上次的题数差异。

## 上传到知识库（可选，需 ima MCP）

1. `mcp__ima-mcp__get_knowledge_list`（`folder_id` 取 `config.json` 的 `kb.folder_id`）查现有同名文件
2. 对每册：
   - `mcp__ima-mcp__create_media`：`apply_upload_mode=1`、`content_type=text/markdown`、`file_ext=md`、`file_size`、`file_name`、`knowledge_base_id`
   - 把 `cos_credential` + `cos_key` + `file` + `file_size` 写入 `cwd/.grammar_wrong/cos_job.json`，运行 `$PY $S/cos_put.py`
   - `mcp__ima-mcp__add_knowledge`：`media_id` + `folder_id` + 重名策略（存在→`DUPLICATE_NAME_STRATEGY_REPLACE`，不存在→`_SAVE`）
3. 上传完成后核对 `parse_progress = 100`，且目录条目无重复

## 详细参考

接口链路、字段语义、题型映射、完整排版规则、已知坑与排查顺序：`references/rules.md`（执行前按需读取）。

常见故障先查这几条：必须 `channel="chrome"` 启动；`getWrongQuestions` 缺 `grammarItemValue` 会 500；`firstAttemptAnswer` 不可信，不要写进文档；ima 的 COS SDK 在沙箱装不上，用 `cos_put.py` 手动签名。
