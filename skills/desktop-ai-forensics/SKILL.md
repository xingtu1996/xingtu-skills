---
name: desktop-ai-forensics
description: 对桌面 AI 应用（豆包工作 / WorkBuddy / 千问办公 QwenWorkCN / CherryStudio / Trae 等基于 Electron+Chromium 的客户端）做本地数据取证——解析 IndexedDB LevelDB 存储、还原会话元数据与行为痕迹、审计定时任务健康度与技能自进化记录、审计沙箱产物与浏览器页面快照；并覆盖 **WorkBuddy 专属的 `~/.workbuddy/` 结构化痕迹**与**千问办公专属的 `agents.db`（定时任务/技能进化/主动提醒，三者里信息量最大）**（sessions 表 / artifact-index / audit-log / changes-index / modify_backup）与**跨 harness 移交**（把会话痕迹固化成可移交的「信源坐标」，让 Claude Code / Codex 等能接手并追到过程）。当用户问「分析某 AI 客户端的会话/历史记录」「能不能把它在另一个工具里做的工作搬过来」「XX 工具到底做了什么」「让其他 agent 接手这个项目、能引用当前会话作信源」「这个产品是怎么一步步变成这样的」时使用。
agent_created: true
---

# 桌面 AI 应用本地取证

## 何时用

- 「分析 XX 工具的会话信息 / 历史记录 / 它做过什么」
- 评估「能否把 A 工具的产出/会话借力到 B 工具」
- 客户端数据排障：会话丢失、缓存异常、登录态排查
- 工具链治理：量化某工具在项目里的实际参与度

## 核心判断（先记住这条，能省一半时间）

**绝大多数国产 AI 桌面客户端不在本地存会话正文。** 实测豆包工作：IndexedDB 里 39,570 条记录解压后可读，中文正文 0 条——对话原文在服务端。

所以路径要分层：

| 想要 | 去哪找 | 能否拿到 |
|---|---|---|
| 会话正文 | 本地 IndexedDB | 通常拿不到 |
| 会话元数据（ID/时间/项目引用） | 本地 IndexedDB | 能 |
| 行为痕迹（打开过什么页面/文件） | BrowserUse / saman_shell_db_storage / 沙箱目录 | 能，且信息量最大 |
| 工具产出物 | 沙箱 envs 目录 / 工作区 CHANGELOG 工具列 | 能 |
| 参与度量化 | 项目 CHANGELOG 的 `--tool` 列 | 最可靠 |

## 数据根位置（macOS）

```
~/Library/Application Support/<AppName>/
├── Default/IndexedDB/*.leveldb          # 会话库（元数据为主）
├── Default/IndexedDB/*.indexeddb.blob   # 大对象（图片/文件）
├── Default/BrowserUse/PageSessions/     # 内置浏览器页面会话快照 .bin
├── Default/sandbox_envs_dir/envs/<uuid>/  # 每次 agent 任务的沙箱（最有价值）
│   └── .playwright-mcp/                 # page-*.yml + console-*.log（操作回放）
├── Default/saman_shell_db_storage/      # 页面标题/URL 索引
├── Default/Local Storage/leveldb
├── sandbox_runtime/bases/               # 内置工具链（python/node/rg/git）
└── sandbox_runtime/downloads/
```

其他应用对应：`CodeBuddy`、`WorkBuddy`、`CherryStudio`、`Trae`、`Kiro`、`Codex`、`Antigravity`。

## ⭐ WorkBuddy 还有第二套数据根：`~/.workbuddy/`（比 LevelDB 好用得多）

上面那套是 Chromium 的。**WorkBuddy 另有一套结构化的**——不是 LevelDB，是 **sqlite + JSON 索引**，
不用解压、不用写解析器，`sqlite3` / `json.load` 直接读。**要追溯「它做过什么」，优先来这儿，别先去啃 leveldb。**

```bash
ls ~/.workbuddy/          # 顶层还有：blobs/ artifact-index/ changes-index/ audit-log/ workspace/ app/ cache/
```

| 信源 | 路径 | 能答什么 | 局限 |
|---|---|---|---|
| **sessions 表** | `~/.workbuddy/workbuddy.db` | 会话 id / **cwd** / 标题 / 模型 / 起止时间 / `session_usage`（token 用量） | 只有元数据 |
| **artifact-index** | `~/.workbuddy/artifact-index/<sid>.json` | **该会话全部产出物**：路径 / 大小 / 创建与更新时间 / MIME。`artifacts[]`，每条带 `_meta.ownerConversationId` 可自校验 | 只含**显式交付**过的产物（如 present_files），过程性产物不在内 |
| **audit-log** | `~/.workbuddy/audit-log/<YYYY-MM-DD>.jsonl` | **命令级取证**：`commandPreview` 全文 / 时间戳 / `decision`（allowed·blocked·approved）/ **`prevHash`+`hash` 防篡改链**。按 `sessionId` 过滤 | 只有命令，**没有意图与结论** |
| **changes-index** | `~/.workbuddy/changes-index/<sid>.json` | 文件改动批次账（`changes[].files[].{filePath,action,additions,deletions}`） | ⚠️ **只覆盖 cwd** —— cwd 不是项目根时，项目改动**不在内**（极易误判成"没改过"） |
| **workspace/sessions** | `~/.workbuddy/workspace/sessions/<sid>/modify_backup/` | 文件触达记录，命名 `<序号>.<op>.<hash>.<原文件名>`。**非空的能还原改动前内容** | ⚠️ 绝大多数是 **0 字节空壳**（只证明"碰过"）。判据：`find <dir> -type f -size +0` |

```bash
SID=<会话id>
sqlite3 ~/.workbuddy/workbuddy.db "select id,cwd,title,model,datetime(created_at/1000,'unixepoch','localtime') from sessions where id='$SID'"
python3 -c "import json;d=json.load(open('$HOME/.workbuddy/artifact-index/$SID.json'));print(len(d['artifacts']),'件产出物')"
grep -c "$SID" ~/.workbuddy/audit-log/2026-09-15.jsonl
find ~/.workbuddy/workspace/sessions/$SID/modify_backup -type f -size +0 | wc -l
```

**两个必踩的坑**：
1. **`cwd` 不等于项目根。** 会话的 cwd 可能是历史残留目录 → `changes-index` 收录的就全是无关文件，
   而项目改动一件都看不见。**接手前先比对 `sessions.cwd` 与真实项目路径。**
2. **git 起点晚于工作起点。** 实测一例：首件产出物比首笔 git 提交早 **41 小时** ——
   那 41 小时**只有 `artifact-index` 记着**。所以「git 里没有」≠「没发生过」。

**会话正文**：与其它客户端一致，不在本地（IndexedDB 实测停在 2026-07-09，无该会话 id；`blobs/` 亦无）。
→ 在服务端。所以「引用 sessionid 作信源」= **交坐标，不是交正文**。

## ⭐⭐ 千问办公（QwenWorkCN）有第三套：`agents.db`——三者里信息量最大的一个

**别只查 IndexedDB。** 千问办公把 agent 运行时的结构化状态全放在一个 sqlite 里，
不加密、不压缩，`sqlite3` 直读，**比 WorkBuddy 的 workbuddy.db 还丰富**（38 张表）。

```bash
ls -la ~/Library/Application\ Support/QwenWorkCN/data/agents.db   # 常见 70MB+
sqlite3 "file:$HOME/Library/Application Support/QwenWorkCN/data/agents.db?mode=ro" ".tables"
```

| 表 | 能答什么 |
|---|---|
| `scheduled_tasks` | 定时任务定义；**`missed_run_policy`**（skip / run_latest）——别家没有 |
| `task_run_logs` | 每次执行 **`error` 是结构化 JSON**（`{"type":"missed","reason":"startup"}`），可归因 |
| `scheduled_task_admissions` | **幂等准入游标**，防重跑——这是成熟调度器的标志 |
| `skill_evolution_suggestions` | **系统观察会话后自动提名** create/update skill，带 confidence / summary / status（pending·evolving·expired） |
| `nudge_logs` | 主动提醒流：`memory_saved`（自动沉淀的记忆）/ `skill_suggested` / `reflection` |
| `chats` / `sub_chats` / `messages` + `messages_fts` | 会话与全文检索（有正文，和豆包不一样） |
| `projects` / `local_projects` / `workspaces` | 项目与工作区绑定 |
| `app_settings` | 客户端开关 |

**取证价值排序**：想看「这个客户端替我干了多少活、哪些在悄悄失败」→ `scheduled_tasks` + `task_run_logs`；
想看「它学到了什么」→ `nudge_logs` + `skill_evolution_suggestions`。

对照：WorkBuddy 的 `automations` + `automation_runs` **只有 `result_success` 布尔值，没有失败原因**，
也没有错过策略 —— 所以「任务建了从没跑过」这类问题在 WorkBuddy 侧只能靠 `last_run_at IS NULL` 反推。

## ⭐ 顺带：审计「自动化有没有真的在跑」（跨客户端通病）

实测某工作区：17 个定时任务 → **5 故障 / 7 预警 / 4 个建了从未执行**，跑起来的成功率 67%~82%。
这类问题不会报错、不会有人发现，只能查库。判定口径：

```python
# 从未执行：enabled 且 last_run_at 为空
lvl = "故障(从未执行)" if total == 0 else \
      "故障" if ok/total < 0.5 else \
      "预警" if ok/total < 0.85 or last_status == "error" else "健康"
```

**坑**：千问的 `{"type":"missed","reason":"startup"}` 是「开机错过的补跑」，
**不是任务逻辑有病**——别当故障报，会误导决策。

## 操作步骤

### 1. 定位数据根

```bash
ls ~/Library/Application\ Support/ | grep -iE "doubao|workbuddy|cherry|trae|kiro|codex"
find ~/Library/Application\ Support/<App> -maxdepth 4 -type d -name "*leveldb*"
du -sh ~/Library/Application\ Support/<App>/Default/IndexedDB/*
```

### 2. 解析 IndexedDB（不要用 strings，会漏）

`strings` 读不到中文——Chromium 的 LevelDB SSTable 数据块默认 **Snappy 压缩**（block trailer type=1）。

```bash
# 装解压库（cramjam 带预编译 wheel，含 snappy）
<python> -m pip install cramjam

# 解析单个库
<python> scripts/leveldb_read.py "<path>.indexeddb.leveldb" auto
<python> scripts/cn_extract.py  "<path>.indexeddb.leveldb" 3 60
```

`leveldb_read.py` 做的事：读 footer 魔数 `0xdb4775248b80fb57` → 取 index block handle → 解析 index block → 逐个 data block 按 trailer 判压缩类型解压 → 前缀共享还原 key。同时支持 WAL（`.log`）记录解析。

### 3. 扫全库找痕迹（含正文判断）

```bash
for d in ~/Library/Application\ Support/<App>/Default/IndexedDB/*/; do
  <python> scripts/cn_extract.py "$d" 3 20
done
```

中文为 0 = 正文不在本地，立即转向第 4 步，不要在 IndexedDB 上继续耗。

### 4. 挖沙箱与页面快照（信息量最大的一步）

```bash
# 沙箱环境清单（有的会带 .playwright-mcp 操作回放）
find ~/Library/Application\ Support/<App>/Default/sandbox_envs_dir -maxdepth 4 | head -60

# 页面会话快照
for f in ~/Library/Application\ Support/<App>/Default/BrowserUse/PageSessions/*.bin; do
  strings -a "$f" | grep -E "^https?://" | head -5
done
```

`.playwright-mcp/page-*.yml` 是 Playwright 的 ARIA 快照，**能还原出当时页面上的完整文本**（含文章正文、按钮文案）。文件名是 UTC 时间戳，注意换算北京时间 +8。

用文件名时间戳算沙箱任务时刻，比文件 mtime 可靠。

### 5. 交叉验证与量化

```bash
# 工作空间里的工具归属统计（最硬的证据）
grep -oE '\| (doubao|workbuddy|zcode|cli|-) \|$' CHANGELOG.md | sort | uniq -c | sort -rn
```

## 本次实测结论（豆包工作 / 2026-09-10）

- 数据根 `~/Library/Application Support/DoubaoWork/`，内置 Chromium 147.0.7727.149
- IndexedDB 23 库；核心 5 库解析出 39,570 条记录，**中文 0 条** → 正文在服务端
- 沙箱环境 5 个实例（09-02 ~ 09-08），内置 lark-cli / mediakit-cli 能力包
- `sandbox_envs_dir/envs/cc4ec6e9/.playwright-mcp/` 保留了 2026-09-05 01:20-01:23 操作公众号后台的完整回放（7 张 page 快照 + 7 份 console 日志）
- CHANGELOG 工具归属：doubao 323 / workbuddy 155 / 未知 13 → 豆包工作占 65.8%

## 坑

1. **不要用 `strings`** —— Snappy 压缩后中文全丢，会误判成「没有数据」。
2. **IndexedDB 无中文 ≠ 解析失败** —— 先确认解压通了、英文字段能读出来，再下结论。
3. **`.bin` 页面会话用 `strings -a` 只出 ASCII** —— 中文要用 Python `decode('utf-8','ignore')` 再正则。
4. **客户端运行中也能只读** —— 遇到 LOCK 不要尝试写入，读 `.ldb` / `.log` 即可。
5. **文件 mtime 会骗人** —— Playwright 快照 mtime 是落盘时间，用文件名里的 UTC 时间戳算实际时刻。
6. **别只看 IndexedDB** —— 沙箱目录 + 页面会话 + CHANGELOG 三者交叉，才是完整证据链。

## 跨 harness 移交：把痕迹固化成「信源坐标」

当目标不是「分析它做了什么」而是「**让别的 agent（Claude Code / Codex / …）能接手，并追得到过程**」时：

**先认一件事**：跨 harness 的**原生 resume 做不到**（Claude Code 恢复不了 WorkBuddy 的会话状态）。
但 n=1 的项目**不需要**那套 —— 把「过程」转成 **「可读的当前状态 + 痕迹坐标」** 就够了，成本近乎为零。

**交付形态**（写成一份机器可读 + 一份人可读，落进项目仓库）：

```json
{
  "schema": "session-provenance/v1",
  "session": { "id": "...", "harness": "...", "model": "...", "cwd": "...", "createdAt": "...",
               "_cwdTrap": "cwd 与项目根的差异及后果" },
  "sources": [ { "id": "...", "path": "...", "provides": "...", "count": 0,
                 "readWith": "可复制的命令", "confidence": "高/中",
                 "caveat": "局限" } ],
  "cannot": [ { "what": "拿不到什么", "where": "为什么", "howToGet": "替代路径" } ],
  "readRecipe": { "steps": ["一条条可复制、能真跑的命令"] }
}
```

硬要求：
1. **`cannot` 节必须诚实** —— 明确写出「会话正文不在本地」这类事实。只写能拿到什么，等于误导接手的人去撞墙。
2. **`readRecipe` 必须真跑过一遍** —— 没跑过的配方是空文档（这是本仓自己踩过的坑）。
3. **`caveat` 要写出「单独用会错在哪」** —— 例如 `changes-index` 只覆盖 cwd，单独用它会把「没改过」当结论。
4. **含绝对路径 = 内部文件**，标注「不得随公开仓分发」——否则这就是一次脱敏事故。

**配套**：项目里给一个入口指针（`AGENTS.md` 的导航表加一行即可），
让接手的人**第一条就能找到这份坐标**，而不是靠翻目录发现。

## 合规边界

只读分析自己的客户端数据，不写入、不篡改、不绕过登录态。发现的凭证/隐私内容（token、真名、邮箱）在产出报告里必须脱敏。

<!-- public-sync: 2026-10-12 | 脱敏版本 | 源 ~/.workbuddy/skills/desktop-ai-forensics -->
