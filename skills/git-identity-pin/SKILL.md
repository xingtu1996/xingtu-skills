---
name: git-identity-pin
description: 扫描某目录树下所有 git 仓库，按业务域分类把 local 提交身份(user.name/email)钉死为指定身份，防止品牌身份污染公司提交或反之。适用于 git 身份空间隔离治理：全局默认公司邮箱、xingtu 品牌空间单独覆盖、开源玩具仓保留品牌身份等多身份并存场景。支持审计(--audit)、干跑(--dry-run)、按路径前缀跳过(--skip)。
version: 1.0.0
metadata:
  author: xingtu
  agent_created: true
---

# git-identity-pin

## 何时用
- boss 拍板"全局默认公司邮箱，只有项目有要求才定制品牌身份"后的落地/巡检工具
- 多 git 身份并存需要空间隔离：公司项目用公司邮箱、xingtu 品牌公开仓用「行途 XingTu」、个人开源玩具保留品牌身份
- 批量把某根目录下 local 错配成品牌身份的仓库，重钉成全局默认身份（防未来 commit 身份漂移）
- 审计"哪些仓 local 身份 ≠ 全局 / 残留旧身份"

## 核心原则
- **local 优先于 global**：git 取 `.git/config` 的 local 身份，写 local 即固定，不受全局改动影响
- **只改 local config，不动 commit 历史、不 push**（历史 author 需 git filter-repo 另做）
- 先 `--audit` / `--dry-run` 看清再写

## 用法
```bash
PY=<工作区根>/.workbuddy/binaries/python/versions/3.13.12/bin/python3

# 1. 审计：列出 ROOT 下所有仓库的 local/全局身份 + 历史 email
$PY scripts/scan_and_pin.py --root <工作区根>/projects --audit

# 2. 干跑：把非 skip 仓钉成全局默认身份(<真名>/co-mall)，只报告不改
$PY scripts/scan_and_pin.py --root <工作区根>/projects --pin --skip open --dry-run

# 3. 执行：跳过 open 子目录，其余钉成全局默认身份
$PY scripts/scan_and_pin.py --root <工作区根>/projects --pin --skip open

# 4. xingtu 品牌空间重钉为品牌身份(指定 name/email)
$PY scripts/scan_and_pin.py --root <工作区根>/xingtu/github \
   --pin --name "行途 XingTu" --email "274853659+xingtu1996@users.noreply.github.com"

# 5. 输出 JSON 报告
$PY scripts/scan_and_pin.py --root <工作区根>/projects --audit --report /tmp/out.json

# 6. 按业务域映射文件钉死（推荐：支持多身份，防前司仓被误覆盖）
$PY scripts/scan_and_pin.py --root <工作区根>/projects --pin \
   --mapfile maps/boss_identity_map.json
# 映射含 default(全局company) + rules: crv系→crv.com.cn / xingtu→品牌身份 / open→skip
```

## 参数
- `--root DIR`：扫描根（必填）
- `--audit`：只读审计模式（默认行为，不写）
- `--pin`：钉死模式（把 local 身份写成目标）
- `--name / --email`：模式A 目标身份；省略读全局 `~/.gitconfig` 的 user.name/email
- `--skip REL...`：模式A 跳过前缀（如 `open` `kds`）
- `--mapfile PATH`：模式B 业务域映射 JSON（含 `default` + `rules[]`）；`match` 既匹配路径前缀也匹配仓库名/basename 前缀（如 `crv-` / `crv-local/` 都命中 crv 系）
- `--dry-run`：只报告计划改动，不写 .git/config
- `--report PATH`：把审计/结果写 JSON

## 隔离模型（boss 2026-09-11 拍板）
全局=公司邮箱(默认) / xingtu=行途 XingTu(local 覆盖，唯一例外) / crv 系=前司 crv.com.cn(local 钉死，前司项目不伪装现雇主) / 其他项目=继承全局。

⚠️ **勿用模式A"钉成全局 company"无脑覆盖**：会把手动钉成 `crv.com.cn` 的前司仓误改成现雇主邮箱。多身份并存必须用模式B `--mapfile`。

## 注意
- 嵌套仓库：只取顶层 git root（父目录非 git root 的），子模块不重复处理
- 历史 email 仅用于审计提示，钉死只看当前 local 目标
- 脚本本身零依赖、纯 stdlib
- 跑 git 子进程若遇沙箱 SIGKILL，Bash 调用加 `dangerouslyDisableSandbox: true`
