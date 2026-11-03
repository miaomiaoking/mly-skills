# mly-skills

个人 [WorkBuddy](https://www.workbuddy.cn) 技能集合。每个子目录是一个独立技能包，可直接复制到 `~/.workbuddy/skills/` 下使用。

> **本仓库为 Private。** `grammar-wrong-questions/config.json` 内含真实账号与密码，转为公开前务必先脱敏。

## 技能列表

| 技能 | 目录 | 说明 |
|---|---|---|
| 语法错题整理 | [`grammar-wrong-questions/`](./grammar-wrong-questions/) | 抓取 Grammar Island 的英语语法错题，按 G1/G2/G3 分册生成 Markdown + PDF，可上传 ima 知识库 |

## 安装

```bash
cp -r grammar-wrong-questions ~/.workbuddy/skills/
```

复制后重启 WorkBuddy 会话，说出触发词即可（例如"整理错题"）。

## 依赖

| 依赖 | 说明 |
|---|---|
| Python 3 | 脚本使用标准库 + `playwright`、`markdown`、`pygments` |
| Google Chrome | 抓取时必须用本机 Chrome（`channel="chrome"`），缓存版 chromium 可能版本不匹配 |
| ima MCP | 仅「上传知识库」这一步需要，不传库可跳过 |

安装 Python 依赖：

```bash
pip install playwright markdown pygments
```

## 目录约定

技能脚本以**当前工作目录**为根：产物输出到 cwd，数据缓存在 `cwd/.grammar_wrong/`，配置读技能目录下的 `config.json`。因此同一台机器上任意工作区都能直接运行，互不干扰。

## 新增技能

在本仓库根新建技能目录（与 `grammar-wrong-questions/` 同级），包含 `SKILL.md`（含 YAML frontmatter）+ 可选 `scripts/`、`references/`、`config.json`，然后更新上表。
