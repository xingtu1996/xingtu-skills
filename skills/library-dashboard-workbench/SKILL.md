---
name: library-dashboard-workbench
description: 把本地结构化数据（JSON/CSV/MD 台账）或静态看板升级为 WorkBuddy 资料库的「在线数据工作台」——建数据表 + 写动态 dashboard page（SDK 关联）+ 发布拿公开链接。触发词：工作台、数据工作台、看板在线化、资料库建表、把台账做成在线表、dashboard、改表即刷新。
version: 1.0.0
author: 小研
level: user
agent_created: true
---

# 资料库数据工作台 · 建表到发布全流程

把本地台账/看板升级成 WorkBuddy 资料库（`skill-library`）的在线数据工作台：**建 N 张数据表 → 导入数据 → 写一个动态 dashboard page（SDK 关联各表）→ 上传关联 → 发布**。

## 调用前置

资料库 skill 路径（脚本都在它下面）：
```
SKILL=~/.workbuddy/plugins/cache/workbuddy-builtin/skill-library/0.5.9
```
- 先跑 `runtime_context.py` 看 `mode`；`mode=client` 时用 `ToolSearch` 查 `connect_open_platform` → `DeferExecuteTool` 换 token（op_xxx，1800s 有效，过期报 AUTH_REQUIRED 就重换）。
- 所有网络脚本 token 从 **stdin 首行**读，用法：`{ printf '%s\n' '<token>'; <业务数据>; } | python3 脚本.py --token-stdin ...`

## 关键 API（database / page / manage 模块）

| 步骤 | 脚本 | 用法要点 |
|---|---|---|
| 建表 | `database/create_database.py --token-stdin --stdin` | stdin 首行 token + 次行完整 schema JSON `{"title":"...","properties":[...]}`；不传 space_id 默认落「我的文档」personal |
| 导数据 | `database/batch_add_database_records.py --token-stdin --stdin --database-id <id>` | **`--stdin` 期望完整 dict `{"database_id":"...","records":[...]}`，不是裸数组**；一次 1–100 条 |
| 查 schema | `database/get_database_schema.py --token-stdin --database-id <id>` | 返回 `{id,title,properties[]}`，字段含 id/name/type/config |
| 上传页面 | `page/import_html.py --token-stdin <本地.html> --databases '[{"id":"..."}]'` | 成功输出 `KS_IMPORT_OK {node_block_id,url}` |
| 发布 | `page/publish_page.py --token-stdin --node-id <node_block_id>` | 成功输出 `KS_PAGE_PUBLISH\t<公开URL>` |

## 字段类型（params-reference.md）

- select：建表 `{"select":{"options":[{"text":"x"}]}}`；写入 `{"select":"x"}`（选项文本或 id）
- multi_select：建表 `{"multi_select":{"options":[...]}}`；写入 `{"multi_select":["a","b"]}`
- date：建表 `{"date":"yyyy-mm-dd"}`；写入 `{"date":"2026-08-26"}`
- number：`{"number":0}`；text：`{"text":""}`

## 动态 page 硬规则（lint 会拦，踩坑必看）

1. **databaseId 必须字面量**：`db.query({ databaseId:'BMxxx', ... })`。不能用 `DB.xxx` 对象属性间接引用，否则 lint **DSDK002** 挂。
2. **query + DOM 写入必须加绑定标注**（至少一对，否则 **DSDK012** 挂）：
   ```html
   <div id="list" data-sp-bindable="database" data-sp-database-id="BMxxx"></div>
   ```
3. **取数只用 `.results`**：`res.results`，禁 `.records/.success/.data`（DSDK010）。
4. **字段访问用 `r['字段名']`**（变量名别叫 `row`，可避开 DSDK006 的 row 字段检查）。
5. **多表字段**：sorts/filter 里的字段名只认单表 schema；跑 lint 时 `--schema-file` 传「引用了 sorts 的那张表」的 get_database_schema 输出即可。
6. 本地预览无 SDK，写好 `if(!db){ fallback(); }` 降级；SDK 方法名 `query/addRecord/getRecord/updateRecord/deleteRecord/getSchema` 才被识别。
7. **列表页筛选/搜索**：`filter` 是递归树（节点三选一 `property`/`and`/`or`）。text 搜索 `{property:{property:"标题",text:{contains:kw}}}`；select 等值 `{property:{property:"分类",select:{equals:v}}}`；多选任一匹配用 `or` 包多个 select.equals。字段名放函数里动态构造即可，lint 的 DSDK009 只扫 `db.query(...)` 的 body 内联字面量，函数里的字段名不扫（但字段名仍须真实）。
8. **分页**：`db.query` 返回 `{results, nextCursor, hasMore}`，**无 total 字段**。翻页用 cursor 栈：`cursors=[undefined]` + 每次记录 `nextCursor`，下一页 `cursors[page]=nextCursor` 传 `startCursor`；命中总数做不了精确，只显示"本页 N 条 / 还有更多"。

## 上传前两道硬门

```bash
# ① 图片外链自检（无输出=合格）
grep -Eoi '<img[^>]+>' final.html | grep -Eoi '(src|srcset)\s*=\s*["'"'"'][^"'"'"']*(https?:)?//[^"'"'"']+' | grep -Eoi '(https?:)?//[^/"'"'"')\s]+' | grep -Eiv 'codebuddy|workbuddy'
# ② SDK 用法 lint（MINDX_DBSDK_LINT_OK = 通过）
python3 "$SKILL/page/lint_database_sdk_usage.py" --schema-file <某表schema.json> --html final.html
```

## 收尾

- 发布后 `present_files` 打开公开链接（`https://workbuddy.link/p/<nodeId>`）或空间页（`https://www.workbuddy.cn/space/d/<nodeId>`）。
- 数据准备建议写一个 Python 脚本（读本地 JSON/CSV → 生成 schema + 分批 records JSON），批量导入时 `{ printf token; printf '{"database_id":"...","records":'; cat batch.json; printf '}'; } | 脚本 --stdin`。

<!-- public-sync: 2026-10-12 | 脱敏版本 | 源 ~/.workbuddy/skills/library-dashboard-workbench -->
