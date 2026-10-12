---
name: zcode-client-ops
description: >
  ZCode（智谱 Z.ai 的 ADE 桌面客户端）的安装、可回退升级，以及「活动卡片不显示 / 领不到免费额度 /
  提示没有可用模型」的诊断。核心手法是从 ~/.zcode/v2/logs 日志实证定位，而非猜测或翻应用二进制。
  触发词：装 ZCode、升级 ZCode、ZCode 没有领取入口、活动卡片不显示、weekend build 领不到、
  ZCode 没有可用模型、zcode 套餐、zcode 额度、zcode-client-ops。
agent_created: true
---

# ZCode 客户端运维与套餐诊断

ZCode 是 Electron 桌面应用（`dev.zcode.app`），不是 CLI。账号态、套餐态、活动态全在本地有痕迹，
**遇到「功能没出现」先读日志，不要猜**。

---

## 一、安装（macOS）

brew cask 有，但**版本可能落后**（2026-09 时停在 3.10.2，官网已 3.11.2）：

```bash
HOMEBREW_NO_AUTO_UPDATE=1 /opt/homebrew/bin/brew install --cask zcode
xattr -dr com.apple.quarantine /Applications/ZCode.app   # 拆「已损坏」拦截
```

装机后**第一件事是核对版本** —— 版本落后会被服务端 429 拒掉（见第三节）。

## 二、查最新版并升级（可回退）

最新版本号与下载地址从官网首页 HTML 里抓（不要猜 URL）：

```bash
curl -sL https://zcode.z.ai/cn | grep -oE 'https://cdn-zcode[^"\\]*macos-arm64\.dmg' | sort -u
```

下载地址规律：
`https://cdn-zcode.z.ai/zcode/electron/releases/<版本>/macos-arm64/ZCode-<版本>-mac-arm64.dmg`

功能引入版本查 changelog：`https://zcode.z.ai/changelog`

可回退升级（旧版**挪走不删**）：

```bash
MP=/tmp/zcode_mnt; mkdir -p "$MP"
hdiutil attach <dmg路径> -nobrowse -mountpoint "$MP" -quiet
/usr/libexec/PlistBuddy -c "Print :CFBundleShortVersionString" "$MP/ZCode.app/Contents/Info.plist"
osascript -e 'tell application "ZCode" to quit'; sleep 3; pkill -x ZCode 2>/dev/null
mv /Applications/ZCode.app /tmp/ZCode-<旧版>.app.bak
ditto "$MP/ZCode.app" /Applications/ZCode.app
xattr -dr com.apple.quarantine /Applications/ZCode.app
hdiutil detach "$MP" -quiet
open -a /Applications/ZCode.app
```

回退：`mv /tmp/ZCode-<旧版>.app.bak /Applications/ZCode.app`

## 三、诊断套餐 / 活动状态（核心）

状态**不在** `~/Library/Application Support/ZCode/`（那里只有 Electron 运行时文件），
而在 **`~/.zcode/v2/`**：

| 文件 | 用途 |
|---|---|
| `logs/YYYY-MM-DD.log` | **主力证据**。搜 `coding-plan-availability`、`billing/balance`、`getManualClaimPlanPreviews` |
| `coding-plan-cache.json` | 入口可见性：`builtin:zai-*` / `builtin:bigmodel-*` 的 available/unavailable + reason |
| `config.json`、`setting.json` | 模型与界面设置 |
| `credentials.json` | 凭据 —— **不要读、不要回显** |

```bash
grep -a "billing/balance" ~/.zcode/v2/logs/$(date +%F).log | tail -5 | cut -c1-500
```

**判定表**

| 日志现象 | 含义 | 处置 |
|---|---|---|
| `请求失败 {"status":429, "url":".../billing/balance?app_version=<ver>"}` | **客户端版本落后，服务端按 app_version 限额放行** | 升到官网最新版；若仍 429 则是服务端限流，等或重试 |
| `请求完成` + `"hasActiveStartPlan":true` | 套餐正常 | 读 entitlements 看可用模型与额度 |
| `reason: coding_plan_not_entitled` | 未订阅该套餐 | 换套餐 / 领活动额度 |
| `reason: coding_plan_not_authenticated` | 对应平台账号未登录 | 在客户端内登录 |

**注意：`billing/balance` 的 URL 带 `?app_version=` 参数 —— 这是服务端做版本门禁的机制。
升级后同一请求从 429 变为 200，是这类「功能不出现」问题的头号原因。**

解析完整套餐与额度：

```bash
python3 - <<'PY'
import os, re, json, datetime
p = os.path.expanduser("~/.zcode/v2/logs/%s.log" % datetime.date.today().isoformat())
raw = open(p, encoding="utf-8", errors="ignore").read()
h = re.findall(r'\[coding-plan-availability\] billing/balance 请求完成 (\{.*)$', raw, re.M)
if not h:
    print("没抓到成功记录 —— 看第三节判定表的 429 分支")
else:
    d = json.loads(h[-1])["payload"]["data"]
    f = lambda x: datetime.datetime.fromtimestamp(x).strftime("%m-%d %H:%M")
    for pl in d.get("plans", []):
        print("%s | %s | %s → %s" % (pl.get("name"), pl.get("status"),
                                     f(pl["starts_at"]), f(pl["ends_at"])))
        for e in pl.get("entitlements", []):
            print("   -", e.get("show_name"), "{:,}".format(e.get("grant_units", 0)), e.get("unit_type"))
    for b in d.get("balances", []):
        print("余额桶 %s: 剩 {:,}/{:,}，周期 %s → %s" % (
            b.get("show_name"), b.get("remaining_units", 0), b.get("total_units", 0),
            f(b["period_start"]), f(b["period_end"])))
PY
```

## 四、领取活动额度（Weekend Build 等）

1. 进客户端，看**左下角活动卡片**（在账号头像上方）
2. **没看到就完全退出重启**（`Cmd+Q` 后重开）—— 官方明确给的处置
3. 点「领取」
4. 「设置 → 模型设置」把连接方式切到对应套餐，状态显示「已启用」才算生效

活动是「先到先得」，前几轮曾一小时领空 —— **窗口一开始就领，别拖**。
额度**只在 ZCode 客户端内有效，不是开放平台 API**，无法喂给 Claude Code / Codex 等外部 harness。

## 五、已知坑（都踩过）

- **别在 `app.asar`（约 293MB）里 grep 中文串** —— 必超时；纯 ASCII 短串也会撞上层出不穷的假阳性
  （曾把地图 bbox 坐标里的数字误认成额度数）。要查功能属于哪个版本，直接看 changelog。
- `~/.workbuddy/skills`（WorkBuddy 用户级技能）**不在 ZCode 的技能扫描范围**。
  ZCode 只扫 Claude Code / Codex CLI / OpenClaw / Augment / Windsurf 的技能目录。
  要把 WorkBuddy 技能接进去必须手建软链：
  `ln -sfn ~/.workbuddy/skills/<技能名> ~/.zcode/skills/<技能名>`
- ZCode 每轮会把**所有启用技能**的元数据（name + ≤250 字 description）注入上下文，
  超预算就降级成「只剩名字」，模型判断不出何时该用哪个 → **自动触发率崩**。
  **必须精选，绝不批量全导。**
- 技能格式与 Claude Code 同构：`~/.zcode/skills/<name>/SKILL.md`，frontmatter 需含
  `name` + `description`（description >1024 字符会**整个技能被丢弃**，不是截断）。
- 项目指令读 `AGENTS.md`（`~/.zcode/AGENTS.md` + 工作区级），**不读 `CLAUDE.md`**（仅 onboarding 时一次性迁移）。
- 自定义供应商支持 Anthropic / OpenAI / OpenRouter / DeepSeek / Moonshot 等兼容协议端点。

<!-- public-sync: 2026-10-12 | 脱敏版本 | 源 ~/.workbuddy/skills/zcode-client-ops -->
