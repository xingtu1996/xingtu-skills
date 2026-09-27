---
name: repo-rename-desensitize
description: 项目/仓库「全库更名」+「真名脱敏」的一体式 SOP，附带公开前的历史暴露面核查与分发产物重打包。当用户说「项目名是不是该改」「全库改名」「改名成 X」「把这个清一下别泄漏真名」「开源前脱敏」「仓库别带上我的名字」「包名/应用名换掉」时触发。覆盖：改名影响面盘点 → 缓存耦合确认 → 路径 git mv → 内容批量替换（三大小写变体）→ 分类脱敏 → 历史暴露面核查 → 产物重打包 → 台账回写。
agent_created: true
---

# 全库更名 + 真名脱敏 SOP

> 动因来源：行途 `text2vido → book2vido` 更名（2026-09-16）。
> 那次踩到的四个真坑全部沉淀在下面 §【硬教训】里。

## 何时用

- 项目/包/应用改名（`oldname → newname`），且改名要覆盖代码 + 文档 + 打包产物 + 目录
- 开源/公开前要清洗「本机绝对路径 / 用户名 / 真名 / 公司标识」
- 仓库要从 private 转 public 前的准备

## 铁律（先做这三件，再动手）

1. **先纠事实，再执行。** 用户对"改名历史"的记忆常是错的。
   在动任何一行之前，先取证：`git log --all -S"<旧名>"`、首提交 README 首行、仓创建时间 vs 首提交时间、
   `gh search repos <新名>`（查撞名）。
   **若结论是"从未改名"，就要在交付里明确纠正，别顺着用户的假设做。**
2. **先备份，走工作区自带脚本。**
   `bash tools/safety/backup-before-op.sh "<描述>" <path...>`（行途工作区）。
   另加一个 tarball 兜底并 `tar -tzf` 验证可读。
3. **删除一律走 `safe-delete.sh`（mv 到回收站），绝不 `rm -rf`。**

---

## 执行顺序（顺序错了会返工）

### 第 0 步 · 影响面盘点
```bash
find . -iname "*<旧名>*" -not -path "./.git/*"        # 名字含旧名的路径
git grep -l -i "<旧名>"                                # 被跟踪文件
grep -ril "<旧名>" --exclude-dir=.git --exclude-dir=dist .   # 含未跟踪
```
把结果分成四类：**路径** / **内容** / **产物** / **外部引用（含定时任务、其他项目、memory）**。

### 第 1 步 · 确认"缓存/指纹"是否与名字耦合 ★硬教训①
**改名最常见的隐性代价是缓存全失效或静默错位。**
先读缓存键生成逻辑：
```bash
grep -rn "cache_key\|fingerprint\|sha256\|hexdigest" src/
```
- 若键是**内容指纹** → 改名不影响缓存，无需清理（本次结果：样本 sha256 前缀 `09bd9369…` 恰是缓存目录名 → 反证）。
- 若键**含包名/路径** → 必须清缓存或迁移，否则表现为"变慢了"或读错缓存。
> 判定法：拿一个已知样本算它的指纹，看是否等于现有缓存目录名。

### 第 2 步 · 路径改名（保 git 历史）
```bash
git mv src/<旧> src/<新>
git mv src/<旧>.egg-info src/<新>.egg-info     # 建议顺手移出跟踪：它是 pip 再生元数据
git mv specs/<日期>-<旧>-<主题> specs/<日期>-<新>-<主题>
```
**用 `git mv`，不要 `mv`** —— 否则 git 记成"删除+新增"，历史断掉。

### 第 3 步 · 内容批量替换（**三个大小写变体都要覆盖**）★硬教训②
```python
REPL = [('oldname','newname'), ('OldName','NewName'), ('OLDNAME','NEWNAME')]
```
- ⚠️ **`TEXT2VIDO_OUT` 这类环境变量名是大写** —— 只替换小写会漏掉，运行时静默失效。
- ⚠️ **分两轮做**：第一轮只扫 `git ls-files` 的**被跟踪**文件；
  第二轮扫**未跟踪**新文件（本次就漏了自己新建的 3 个 tools 脚本 + 2 个 doc）。
  否则会出现"仓库干净但本地脚本还是旧名"。
- ⚠️ **后缀过滤会漏无扩展名文件**（`PKG-INFO`、`LICENSE`、`.gitignore`），单独列白名单。
- ⚠️ 别忘 **`.gitignore` 里的注释**（如 `dist/OldName.app`）——它不影响行为但会误导后人。

### 第 4 步 · 分类脱敏（**最忌一刀切**）★硬教训③

| 类别 | 处置 |
|---|---|
| **可执行代码**（脚本里的硬编码绝对路径） | **必须改** → 项目相对路径 + `Path.home()` / `$HOME` |
| **文档示例**（README/HANDOFF 的 `cd /Users/xxx`） | 改为 `<仓库根>` 或相对路径 |
| **验证记录 / 审计日志**（specs 的 validator、verification-report） | 🔴 **禁改** —— 改写＝篡改证据。改为**标红登记为公开前阻塞项** |
| **构建脚本的本机默认值** | 去字面量（`"/Users/me/..."` → `"$HOME/..."`），行为不变 |
| **元文档**（描述"有多少文件泄漏"的段落） | 脱敏 **且** 把易漂的计数换成**可复算的口径命令** |

配套：
- 权限/版权资产（样例 PDF）→ 加 `.gitignore`，并**用 `git check-ignore -v <真实路径>` 实证**（肉眼看着对 ≠ 生效）。
- 含真名的截图 → 同上去忽略，**绝不入库**。

### 第 5 步 · 旧素材目录腾名（当新名与既有目录撞车时）
```bash
cp -p <旧目录>/<文件> <项目内新位置>/       # 先拷
shasum -a 256 <两边> | 逐一比对              # 再校验（逐文件，别只看目录大小）
bash tools/safety/safe-delete.sh <旧目录>    # 最后 mv 进回收站（可 restore）
```
⚠️ 撞车很常见（本例：项目要叫 `book2vido`，而 `~/xingtu/book2vido/` 已经是素材目录）。
**先拷 + 校验 + 再移**，绝不等价于"先删再建"。

### 第 6 步 · 产物重打包 ★硬教训④
改了包名/应用名后，`dist/` 里的旧产物**必须重出**：
```bash
# 先把旧产物 safe-delete（否则构建脚本的 rm -rf 会触发沙箱批量删除护栏，构建中断但产物没删 → 用旧包打新包）
bash tools/safety/safe-delete.sh dist/<Old>.app dist/<Old>.dmg
bash packaging/build_app.sh && bash packaging/build_dmg.sh
```
**验证三件（缺一不可）**：
1. `<新>.app/Contents/MacOS/<新> --selftest` 全绿
2. **端到端真跑一次**，核验产物文件真实存在 + `ffprobe` 规格正确（别只看日志说"成功"）
3. `xattr -p com.apple.quarantine <app>` 确认无隔离属性（决定双击能否直接开）

### 第 7 步 · 🔴 历史暴露面核查（**最容易漏、最要命**）
> **工作区清干净 ≠ 可以公开。**

```bash
git log --all -p | grep -c "<敏感串>"        # 历史里出现多少次
git log --all --oneline -S"<敏感串>"          # 涉及几个提交
git log --format="%an <%ae>" | sort -u        # 提交作者身份是否也是真名
```
- 若历史里有 → **必须历史重写**才能公开：`git filter-repo --replace-text <file>`
  （仓很新/很小的话，"压成单条初始提交"更省事）。
- 提交作者若是真名 → 同样要 `filter-repo --mailmap` 或重建。
- **把这条写进 CHANGELOG + specs/README 红框**，否则下一个人以为清完了。

### 第 8 步 · 台账回写
- 项目 `CHANGELOG.md`：置顶新条目，**必须给"行为变更表"**（import 名 / 产物名 / 环境变量 / 输出目录 / bundle id）。
- `HANDOFF.md`：待办区加"公开前阻塞"，并提醒接续者哪些路径已变。
- 工作区根 `CHANGELOG.md` + 当日 memory：一行摘要 + 口径命令。
- 历史日志（旧日期的 memory / 旧会话记录）**不改**（append-only，改写＝篡改历史）。

---

## 【硬教训】四条（来自 text2vido 那次）

1. **缓存键决定改名的隐性成本。** 先确认键是内容指纹还是包名，再决定要不要清缓存。
2. **大小写三变体 + 两轮扫描（被跟踪 / 未跟踪）+ 无扩展名文件**，漏一个就留一条尾巴。
   验证一律用 `git grep -l <旧名>` 收尾，且**权威口径是直接查名字**（不是查正则）。
3. **脱敏要分类**：代码必须改、文档改、**验证记录禁改只登记**。
   而且**脱敏口径命令自身可能含敏感串**（`git grep -l <真名>`）→ 换成通用模式
   `git grep -lE '/Users/[^/]+/'`；注意这个模式会**自匹配自己的文档文本**，别被假阳性骗了。
4. **产物不会自己更新。** 改完名字一定要重打包 + 端到端真跑 + 核验文件实体。
   另：`rm -rf dist/<app>` 会触发沙箱批量删除护栏 → 用 `safe-delete.sh` 先移走。

## 收尾自查清单

```bash
git grep -l -i "<旧名>"                      # 应为空（CHANGELOG 的更名条目除外）
git grep -l "<真名>"                          # 应只剩刻意保留的验证记录
grep -ril "<旧名>" . --exclude-dir=.git --exclude-dir=dist --exclude-dir=.backups
git check-ignore -v <应忽略的文件>            # 每条都要有输出
git status --short | wc -l                   # 心里有数
<新app> --selftest                           # 全绿
```
