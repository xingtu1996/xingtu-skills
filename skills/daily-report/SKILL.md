---
name: daily-report
description: 把当日工作整理成钉钉日报并落盘打包——固定格式（今日工作/明日工作/相关截图）+ 附稿目录 + zip。触发词：写日报/工作日报/日报/今天做了什么/日报附稿/日报打包/daily report/居家办公日报。
---

# 工作日报——生成、归档、打包

## 一、触发场景

| 触发场景 | 触发词示例 |
|---------|-----------|
| 生成日报 | "写日报"、"帮我写份日报"、"今天的工作日报"、"日报生成" |
| 归档打包 | "日报附稿"、"打成包"、"放到 DCDOC"、"日报提交" |
| 补图重打包 | "截图配好了"、"重新打包"、"日报加上截图" |

## 二、固定格式（钉钉日报，勿自造结构）

```markdown
## 今日工作

**一、{项目名} —— {工作主题}**

1. {事项}：{一句话说明}
2. {事项}：{一句话说明}

**二、{项目名} —— {工作主题}**

1. ...

## 明日工作

1. {一句话}
2. {一句话}

## 相关截图

（待补充 / 见 `截图/` 目录：<截图说明>）
```

要点：
- 项目**加粗**，事项编号；每条一行，不写过程写结果
- **明日工作与今日工作不重复条目**；同一件事（如"升级 + 回顾升级测试"）合并成一条
- 不写工时、不写客套；不承诺做不到的事

## 三、流程

### Step 1 采集素材（不问就用）

按优先级取证，能查就别问：
1. **当前会话上下文**（用户口述 + 本次产出）
2. **今日 git 提交**：各仓 `git log --since=midnight --author=$(git config user.name) --oneline`
3. **当日改动文件**：`git status` / 产物目录 mtime 当天
4. 仍缺的（明日计划、客户反馈）**一次问全**，别来回问

### Step 2 术语核对（易错，必做）

| 类型 | 真相源 | 常见错写 |
|------|--------|---------|
| 项目名 | 项目目录名 / AGENTS.md | 同名异写以真相源为准 |
| 人名 | `.Codex/user-config.yaml` / 干系人清单 | 同音异写需核实 |
| 需求名 | spec 目录名 | 同音异写以 spec 目录名为准 |
| 工单号 | git 提交 / spec | 内部项目 ≠ ***REMOVED*** |
| 平台名 | — | GitLab ≠ GitHub（公司用 gitlab.***REMOVED***.com） |

拿不准的**关键术语问一次**，别照抄口语错词；改过的术语在回复里**说明改动依据**。

### Step 3 落盘

```
<项目>/doc/DCDOC/工作日报/{YYYYMMDD}-工作日报附稿/
├── 工作日报_{YYYYMMDD}.md
└── 截图/
```

- 默认落盘项目：当前工作目录所属项目；用户指定则从其指定
- `doc/` 已 gitignore，不会推送
- 一天一份，同日多次修订**就地覆盖**，不新建目录

### Step 4 打包

⚠️ **中文文件名必须带 UTF-8 标志**，macOS `zip` / `ditto` 都不写该标志 → Windows/钉钉后台解压乱码。用 Python：

```bash
cd "<...>/工作日报" && python3 - <<'PY'
import zipfile, os
root='{YYYYMMDD}-工作日报附稿'; out='工作日报_{YYYYMMDD}.zip'
with zipfile.ZipFile(out,'w',zipfile.ZIP_DEFLATED) as z:
    for dp,_,fs in os.walk(root):
        if not fs: z.writestr(dp+'/','')
        for f in fs:
            if f=='.DS_Store': continue
            z.write(os.path.join(dp,f), os.path.join(dp,f))
PY
```

验证：`python3 -c "import zipfile;print([i.flag_bits & 0x800 for i in zipfile.ZipFile('工作日报_{YYYYMMDD}.zip').infolist()])"` → 全 True。

### Step 5 交付

- 正文**直接贴 Markdown 源码**给用户复制到钉钉
- 报告落盘绝对路径 + zip 路径（白盒，用户能直接打开）
- 截图未配齐时明确说"配齐后重跑 Step 4 即可"

## 四、提交到钉钉（实测 2026-09-28）

走 `dingtalk-misc` → `references/report.md`。本仓已固定的参数：

| 项 | 值 |
|---|---|
| 模板 | **空白日志** `***REMOVED***`（单字段"内容"，type=1 / contentType=markdown） |
| 接收人 | ***REMOVED*** `***REMOVED***`、***REMOVED*** `***REMOVED***`（`dws aisearch person --query <姓名> --dimension name` 解析，唯一命中才用） |
| 提交 | `dws report entry submit --template-id 17432b55... --contents-file <payload.json> --to-user-ids "***REMOVED***,***REMOVED***" --format json` |

payload（写工作目录内相对路径，避免 shell 引号问题）：

```json
[{"key":"内容","sort":0,"content":"<Markdown 正文>","contentType":"markdown","type":1}]
```

**正文用粗体 `**标题**` 而非 `#`**（钉钉日志 Markdown 支持有限，历史实证只用了粗体 + `![图](url)`）。

### 三个硬限制（客户端能做的事，API 做不到）

| 限制 | 后果 | 应对 |
|------|------|------|
| **不支持附件** | submit 只有 `contents` + `--to-user-ids`，无附件参数 | zip 留本地归档；要发附件走钉盘 / 单聊（`dingtalk-drive` / `dingtalk-chat`） |
| **无编辑接口** | `entry` 只有 get/stats/submit，提交后改不了 | **截图必须配齐再提交**，否则永久留"（截图稍后补充）" |
| **标题不可指定** | 平台生成"××的空白日志"；客户端写会自动带日期（"××的工作日志 YYYYMMDD"） | 接受，或提交后在钉钉客户端手工改标题 |

提交后必须读回：`dws report entry get --report-id <ID>` 核对模板 + 内容。

## 五、坑

| 坑 | 处置 |
|----|------|
| zip 中文乱码 | 见 Step 4，用 Python 打包并校验 flag |
| 明日工作与今日重复 | 合并同类项后再定稿 |
| 人名/项目名错写 | Step 2 核对表，宁可不写人名 |
| 把格式参考当内容 | 用户贴的旧日报截图是**格式模板**，内容以当日素材为准（先确认） |

<!-- public-sync: 2026-10-12 | 脱敏版本 | 源 ~/.agents/skills/daily-report -->
