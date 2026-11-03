# 错题整理规则（Grammar Island）

> 用途：从 <https://grammar.lehaiya.com/#/grammar> 自动抓取错题 → **按 G 级别拆分成多个文档** → PDF → 上传知识库（同名则覆盖更新）。
> 以后有新错题，直接按本文档执行即可，无需重新摸索。
> 最后验证：2026-11-03（G1 52 题 / G2 7 题，上传 + 覆盖更新均已实测）

---

## 0. 一句话流程

```
登录 → 查错题接口 → 拉题目详情 → build_md.py 按 G 拆分成 语法错题整理_G1/G2….md
     → build_pdf.py 出同名 PDF → 逐个上传（先查库：同名覆盖 / 无则新建）
```

---

## 1. 抓取

### 1.1 环境
- Playwright（venv：`/Users/miaoliyun/.workbuddy/binaries/python/envs/default/bin/python`）
- **必须用本地 Chrome**：`chromium.launch(headless=True, channel="chrome")`
  （缓存里的 chromium-1187 与当前 playwright 版本不匹配，直接 launch 会报 executable doesn't exist）
- 会话文件：`data/gi_state.json`，复用即可免登录；失效时脚本自动重新登录

### 1.2 账号与身份
| 项 | 值 |
|---|---|
| 登录页 | `https://grammar.lehaiya.com/#/login` |
| 手机号 / 密码 | 18612710283 / 123456 |
| 学生 | 宋泽辰（昵称 Thomas） |
| studentId | `1837688880766640130` |

登录页元素：`input[0]`=手机号、`input[1]`=密码、**最后一个 checkbox**=同意协议、按钮文本含「登」。

### 1.3 鉴权
```
Authorization: Bearer <JSON.parse(localStorage['cloud-ui:token'])>
```
（token 存在 localStorage 的 `cloud-ui:token`，值是带引号的 JSON 字符串，必须 JSON.parse）

### 1.4 接口链路（base = `https://grammar.lehaiya.com/api`）
| 步骤 | 接口 | 说明 |
|---|---|---|
| ① 语法模块列表 | `GET /examination/grammarWrongQuestions/getWrongGrammarList?studentId&correctFlag=1&current=1&size=100` | 返回 `["G1-1","G1-2",...]` |
| ② 错题明细 | `GET /examination/grammarWrongQuestions/getWrongQuestions?studentId&correctFlag=1&grammarItemValue=G1-1&current=1&size=100` | 分页，size<100 即末页 |
| ③ 题目详情 | `GET /examination/grammarTopicsQuestion/{questionId}` | 题干/选项/答案/解析 |
| ④ 语法点名 | `GET /admin/businessDict/grammar_points` | 树形，itemValue=G1-1 |

**correctFlag 语义（关键）**
- `0` = 「巩固 → 错题」页（**当前为空**，说明没有未订正的错题）
- `1` = 「巩固 → 已改错」页 ← **我们取这个**，累计做错过的题

### 1.5 关键字段
- `record`：`grammarItemValue`(G1-1) / `pointItemValue`(G1-1-1) / `practiceContent`(话题名) /
  `questionId` / `firstAttemptAnswer` / `secondAttemptAnswer` / `attemptCount` / `createTime`
- `question.questionModel`（JSON 字符串）：`typeCode` / `questionTitle` / `options` / `questionAnswer`
- `question.referenceAnswer`：标准答案（`[["答案"]]` 形式）
- `question.hintText`：解析（HTML，**当前文档不使用**）

### 1.6 题型映射
| typeCode | 中文 | 处理方式 |
|---|---|---|
| `choiceFill` | 选择填空 | 题干 + `A. xx　B. xx` 单行排列 |
| `choice` | 单项选择 | 同上 |
| `blank` | 填空题 | 题干（含 `____` 与提示词） |
| `lightup` | 点亮选词 | 题干去掉 `##` 标记 + 候选词列表 |
| `sentence` | 连词成句 | 中文题干 + 备选词列表 |
| `correction` | 改错题 | 原句（取 `||` 前）+ 需修改之处 |

约定：整卷内题型顺序 `choice → choiceFill → blank → lightup → sentence → correction`。

---

## 2. 生成 MD（`scripts/build_md.py`）

### 2.1 分册规则（**本次调整重点**）
- 按 `grammarItemValue` 的 **G 前缀**拆分：`G1-1 / G1-2 / G1-3 / G1-4` → **G1 一册**；`G2-5 / G2-6` → **G2 一册**
- 一册一个文件，文件名带 G 标识：`语法错题整理_G1.md`、`语法错题整理_G2.md`、`语法错题整理_G3.md` …
- 后续若出现 G3/G4，脚本自动多产出对应文件，无需改代码
- 每册题号从 1 开始独立编号

### 2.2 单册结构（硬性规则）
```
# 语法错题整理 · G1            ← 标题带 G 标识
> 来源：Grammar Island · 巩固 → 已改错
> 账号：宋泽辰（Thomas）
> 共 N 题｜生成日期：YYYY-MM-DD
---
## G1-1　名词①                 ← 模块（H2，即"级别"）
### 名词的定义和分类　—　单元测    ← 知识点 — 话题（H3）
**1.（选择填空）**               ← 级别内编号，从 1 开始
题干
A. …　B. …　C. …　D. …
## G1-2　冠词①                 ← 换级别，编号重新从 1 开始
**1.（选择填空）**
---
# 参考答案                     ← 答案页独立成节（PDF 从此页另起）
## G1-1　名词①
1. C. experiences
```
- **练习题部分不带答案**；答案全部集中到后面的「参考答案」页
- **题号按"级别"重置**：每个 `G{x}-{y}` 模块内部都从 1 开始编号
  （例：G1-1 为 1–22、G1-2 为 1–9、G1-3 为 1–9、G1-4 为 1–12；G2-5 为 1、G2-6 为 1–6）
- 答案页同样按模块分组（`## G1-1 名词①`），组内题号与该模块练习题一一对应
- 选择题答案带选项字母（`C. experiences`），多空用 `；` 连接
- 连词成句给完整句子；改错题给 `got → get`
- **册内只列出接口实际返回的级别**：`getWrongGrammarList` 返回哪些 `G{x}-{y}`，文档里就只有哪些章节
  （当前 G2 只返回 G2-5、G2-6，故 G2 册从 G2-5 开始，编号仍是 G2-5 从 1 起、G2-6 从 1 起）
- **不要为无错题的级别补空章节**，也不要人为调整编号起点；有数据才生成，没数据就保持缺省

### 2.3 内容规则（用户明确偏好）
- **原样摘录**，不做考点标注、不写解析、不加汇总表/薄弱点分析
- 不使用表格展示题目
- 选项一行排列：`A. xx　B. xx`（全角空格分隔）
- 数字/标点保留原文（如 `girls'`），HTML 标签清洗掉

---

## 3. 生成 PDF（`scripts/build_pdf.py`）

自动遍历 `语法错题整理_G*.md`，逐个产出同名 PDF。

| 参数 | 值 |
|---|---|
| 纸张 / 边距 | A4 / 上下 13-11mm、左右 12mm |
| 正文字号 / 行距 | 9.5pt / 1.5 |
| 标题 | H1 15pt 居中、H2 12pt 带下划线、H3 10.5pt 蓝色 |
| 分页 | **仅「参考答案」H1 强制另起一页** |
| 分隔线 | 普通细线，**不可设 page-break**（否则首页大片空白） |

当前基准：G1 52 题 → 7 页；G2 7 题 → 2 页。

---

## 4. 上传知识库（**同名覆盖，不重复新建**）

| 项 | 值 |
|---|---|
| 知识库 | 石头知识库（`ima_kb_sMa16Krk`） |
| 路径 | 英语（`folder_7522489689202231`）→ 语法（`folder_7522490259619855`） |

### 4.1 上传前判断（必做）
1. `mcp__ima-mcp__get_knowledge_list`（`folder_id=folder_7522490259619855`）取该目录现有文件名集合
2. 对每册 `语法错题整理_G{n}.md`：
   - **已存在同名** → `duplicate_name_strategy = DUPLICATE_NAME_STRATEGY_REPLACE`（**在原件上覆盖更新**，不新增条目）
   - **不存在** → `duplicate_name_strategy = DUPLICATE_NAME_STRATEGY_SAVE`（新建）

> 实测结论（2026-11-03）：用 REPLACE 重复上传 `语法错题整理_G2.md`，目录条目总数不变、media_id 更新为新值 —— 即真正"覆盖更新"，不会产生重复文档。

### 4.2 上传三步（每册一次）
1. `mcp__ima-mcp__create_media`：`apply_upload_mode=1`、`content_type=text/markdown`、`file_ext=md`、
   `file_size=<字节数>`、`file_name=<该册文件名>`、`knowledge_base_id=ima_kb_sMa16Krk`
2. 按 create_media 返回的模式写 `data/cos_job.json`，跑 `python scripts/cos_put.py`：
   - **`upload_mode=1`**（返回 `upload_url.presigned_url`）→ job 写
     `{"file","file_size","presigned_url","auth_headers"}`，脚本直接 PUT 该 URL
   - **`upload_mode=0`**（返回 `cos_credential`）→ job 写 `secret_id/secret_key/token/bucket_name/region/cos_key`，
     脚本用 q-sign-algorithm=sha1 手动签名 PUT（**COS SDK 在沙箱装不上**）
   - 两种模式脚本都自动识别，`cos_put.py` 已兼容
3. `mcp__ima-mcp__add_knowledge`：`media_id` + `folder_id` + 按 4.1 选定的重名策略

---

## 5. 执行清单

```bash
PY=/Users/miaoliyun/.workbuddy/binaries/python/envs/default/bin/python
cd /Users/miaoliyun/WorkBuddy/2026-11-01-11-58-57

$PY scripts/fetch_wrong.py   # 抓取（会话失效自动登录；可加 --relogin）
$PY scripts/build_md.py      # 按 G 拆分出 语法错题整理_G*.md，打印每册题数
$PY scripts/build_pdf.py     # 每册生成 PDF，打印页数
# 上传：get_knowledge_list 查重 → 逐册 create_media → cos_put.py → add_knowledge(SAVE/REPLACE)
```

### 核对要点
- [ ] 各册题数之和 = 抓取总题数
- [ ] 每册文件名带 G 标识，标题也带 `· G{n}`
- [ ] 练习题部分搜不到「参考答案」正文（仅有答案页标题）
- [ ] PDF 首页无大片空白
- [ ] 上传后目录条目数：无新增同名重复项；`parse_progress = 100`

---

## 6. 已知坑

1. **chromium 版本不匹配** → 必须 `channel="chrome"`
2. **`correctFlag=0` 是空的**，别拿它当错题源
3. **`firstAttemptAnswer` 不可靠**：多数记录里等于参考答案（疑似被后续练习覆盖），所以文档里不放「我的答案」
4. `getWrongQuestions` 缺 `grammarItemValue` 会 500；缺 `studentId`/`correctFlag` 也会 500
5. MD 里 `- 31. A. is…` 这种列表写法渲染异常 → 改独立段落
6. `---` 不要映射成强制分页
7. ima 的 cos SDK 装不上（沙箱 EEXIST）→ 手动签名
8. 学习数据表 64808 条是**全库**数据，不是个人数据，别用来统计
9. **旧文件**：`语法错题整理.md`（59 题合订本）仍留在知识库，已被分册取代；ima MCP 无删除接口，需在客户端手动删除
