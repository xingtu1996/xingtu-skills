# 微信通道 · 关键路径表

> 统一事实源：本表与 `scripts/wechat_channel.py` 顶部常量保持一致。路径变更时两处同步。

## 一、微信数据（只读真相源）

| 内容 | 路径 |
|------|------|
| 微信原始加密库（db_storage） | `${HOME}/Library/Containers/com.tencent.xinWeChat/Data/Documents/xwechat_files/<YOUR_WECHAT_DB_DIR>/db_storage` |
| 解密密钥（14 库，常驻） | `${WORKSPACE}/data/wechat_decrypted/keys.json` |
| 解密库（明文 SQLite） | `${WORKSPACE}/data/wechat_decrypted_latest/`（与 `~/PrivateData/wechat/wechat_decrypted_latest/` 同副本） |
| 密钥兜底副本 | `~/PrivateData/wechat/all_keys.json`（root 权限，首次提 key 用） |

### 解密覆盖范围（实测 2026-09-08）

| 库 | 状态 | 说明 |
|----|------|------|
| `message/message_0~5.db` | ✅ 已解密 | 会话消息主体（Msg_<hash> 表），含 2026-09 最新数据 |
| `message/message_fts.db` / `message_resource.db` | ✅ 已解密 | 搜索索引 / 资源 |
| `contact/contact_fts.db` | ✅ 已解密 | 联系人/群名搜索索引。**search_key 字段含微信号**（格式如 `高旭东 PO 科码 广州Jackgxd20xy广东 深圳`，可正则提取微信号），但非结构化、不保证全覆盖 |
| `contact/contact.db` | ❌ 未解密 | 联系人真实库（昵称/备注→wxid 映射），密钥缺失 |
| `session/session.db` | ❌ 未解密 | 会话列表（可补名字映射） |
| `bizchat` / `chatbot` / `sns` / `media` / `weclaw` 等 | ❌ 未解密 | 公众号消息、chatbot 等 |

> **影响**：当前通道以 **wxid 定位会话**（消息表名 = `Msg_` + md5(wxid).hexdigest()，实测可靠）。昵称→wxid 映射有两条路径：
> 1. **search 子命令**（推荐，不依赖 contact.db）：跨所有消息表搜索关键词，从命中样例反查 wxid，样例即身份证据。
> 2. **FTS search_key 正则提取**（尽力而为）：`contact_fts.db` 的 search_key 拼接了备注名+微信号+地区，可提取部分映射，但格式不统一、非全覆盖。
> 补解密 `contact.db` 后可获得完整映射。
> **微信 4.x 表结构**：消息表为按会话 hash 命名的 `Msg_<hash>`，同一会话可跨多个 message 库（如元宝在 message_0 与 message_5），读取/统计须跨库累加。
> **自定义微信号**：部分联系人的 user_name 不是 `wxid_` 开头而是自定义 ID（如 `custom_id_example1`、`custom_id_example2`），CLI 会先试读消息表确认，有消息即视为有效 wxid。

## 二、工具脚本（行途既有，复用不重写）

| 用途 | 脚本 | 调用方式 |
|------|------|---------|
| 解密微信库 | `tools/wechatdecryption/decrypt.py` | `decrypt_all(db_dir, keys_file, out_dir)` |
| 会话消息解析（zstd+appmsg） | `tools/wechat_chat_analyzer/yuanbao_full_extract.py` | `extract(wxid, dbdir)`，返回结构化消息 |
| AI 蒸馏总结 | `tools/wechat_chat_analyzer/wechat_summary.py` | `--input <csv/json> -o <out>`（MD 解析格式不同，走 CSV 最稳） |
| 元宝增量抓取管道 | `tools/wechat_chat_analyzer/run_pipeline.sh` | `bash run_pipeline.sh`（解密→提取→增量抓取→归档） |
| 元宝卡片提取 | `tools/wechat_chat_analyzer/yuanbao_full_extract.py` | `--dbdir <解密库> --wxid wxid_xxxxxxxxxxxx -o outputs/yuanbao_inventory` |
| 元宝增量抓取 | `tools/yuanbao_incremental_fetch.py` | 水位线驱动，产物按日归档 |
| 元宝归档入库 | `tools/wechat_chat_analyzer/ingest_yuanbao_archive.py` | `ingest_yuanbao_archive.py yuanbao` |

**Python 解释器**：`${HOME}/.workbuddy/binaries/python/envs/default/bin/python`（已装 pycryptodome/zstandard/sqlite3）

## 三、输出与归档落点

| 内容 | 路径 |
|------|------|
| 微信通道默认输出根 | `~/xingtu/outputs/wechat_channel/<wxid>/<动作>_<YYYYMMDD_HHMM>/` |
| 元宝增量批次 | `~/xingtu/outputs/yuanbao_inventory/增量批次/YYYY-MM-DD/` |
| 元宝全量主仓库 | `~/xingtu/outputs/yuanbao_inventory/元宝全文抓取/` |
| 元宝水位线 | `~/xingtu/outputs/yuanbao_inventory/.yuanbao_watermark.json` |
| 元宝卡片索引 | `~/xingtu/outputs/yuanbao_inventory/yuanbao_cards.json` |
| 素材库（素材卡） | `~/xingtu/素材库/素材卡_*.md` |
| 素材库索引 | `~/xingtu/素材库/素材库索引.md` |
| vault 元宝归档 | `~/xingtu/xingtu-vault/02_内容仓库 (Content Hub)/06_元宝对话挖掘/` |
| vault 选题池 | `~/xingtu/xingtu-vault/02_内容仓库 (Content Hub)/01_灵感与选题池/` |

## 四、跨工具标准化接入（四端全局，统一指向实体）

> Skill 实体统一存放于 **全局事实源** `${HOME}/.agents/skills/wechat-channel/`。各工具按**各自标准目录**放软链指向实体，修改实体即四端全局生效。

| 工具 | 标准目录 | 接入方式 | 状态 |
|------|---------|---------|------|
| **Claude Code** | `~/.claude/skills/`（用户级） | `wechat-channel` → 软链 | ✅ 全局 |
| **Codex** | `~/.codex/skills/`（用户级） | `wechat-channel` → 软链 | ✅ 全局 |
| **WorkBuddy** | `~/.workbuddy/skills/`（用户级） | `wechat-channel` → 软链 | ✅ 全局 |
| **豆包** | skill root `~/.agents/skills/`（实体直放）+ `~/DoubaoWork/skills/` 软链 | 实体即 root，双覆盖 | ✅ 全局 |
| Claude（xingtu 项目内） | `~/xingtu/.claude/skills/` | 软链 | ✅ |
| Codex（xingtu 项目内） | `~/xingtu/.agents/skills/` | 软链 | ✅ |

> 路由登记：xingtu 空间内触发词路由见 `~/xingtu/AGENTS.md`「核心 Skills + 触发规则」表。
