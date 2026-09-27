---
name: git-push-in-sandbox
description: "在沙箱（WorkBuddy / CodeBuddy 等受限执行环境）里推送 Git 仓库失败时的网络诊断与绕行。当 git push 报 `502 CONNECT tunnel failed`、`Operation timed out`、`ssh_dispatch_run_fatal`，而 `gh api` 却完全正常时使用。触发词：push 失败、推不上去、502 CONNECT tunnel、push 超时、git push 报错、沙箱网络。"
description_zh: "沙箱内 git push 失败的诊断与绕行"
description_en: "Diagnose and work around git push failures inside a sandboxed shell"
agent_created: true
version: 1.0.0
---

# 沙箱内 `git push` 失败的诊断与绕行

## 一、症状签名（一眼识别）

**`gh api` / `gh repo create` 全正常，唯独 `git push` 失败。**

典型报错：

- `fatal: unable to access 'https://github.com/<o>/<r>.git/': CONNECT tunnel failed, response 502`
- `ssh_dispatch_run_fatal: Connection to <ip> port 443: Operation timed out`
- `ssh: connect to host github.com port 22: Operation timed out`

这**不是** GitHub 的问题，也**不是**用户代理配置的问题——是**沙箱出口白名单**只放行了 `api.*`，
没放行 git 协议通道（SSH 与 HTTPS 的 git 端点都被拦）。

## 二、30 秒确诊（照抄）

```bash
# 1) 代理 → github.com      预期：502
curl -x "$HTTPS_PROXY" -sS -o /dev/null -w "%{http_code}\n" --max-time 15 https://github.com
# 2) 直连 → github.com      预期：000（timeout）
curl --noproxy '*'     -sS -o /dev/null -w "%{http_code}\n" --max-time 15 https://github.com
# 3) 代理 → api.github.com  预期：200  ← 关键对照组
curl -x "$HTTPS_PROXY" -sS -o /dev/null -w "%{http_code}\n" --max-time 15 https://api.github.com
```

**判读**：`1 失败 + 2 失败 + 3 成功` → **确诊沙箱白名单**。
不要去折腾 `http.proxy`、`gh auth setup-git`、证书或换 SSH 端点——那些是被"看起来像代理问题"误导的弯路。

> 若 `3` 也失败，才说明是代理/网络本身的问题，另作排查。

## 三、⚠️ 两个假阳性陷阱

1. **`nc -z` 不可信**：`nc -z ssh.github.com 443` 可能报 succeeded，但 SSH 握手数据照样被拦。
   **不要用端口探测下结论，要用完整协议握手验证**：`ssh -T -o ConnectTimeout=12 git@github.com`。
2. **`gh repo create --push` 中途被杀**（如 exit 137 / SIGTERM）：仓库会**建成功但为空**。
   此时不要再建一次，直接补 `git push` 即可。

## 四、解法

### 首选：让 push 跳出沙箱

在该条 Bash 调用上设 `dangerouslyDisableSandbox: true`（会向用户弹授权，属正常流程）：

```bash
cd <repo> && git push -u origin main
```

**不需要**改任何代理配置。跳出沙箱后直连即可通。

### 备用：SSH over 443

若跳出沙箱仍不通，用 GitHub 的 443 SSH 端点（写进 `~/.ssh/config`）：

```
Host github.com
    Hostname ssh.github.com
    Port 443
    User git
    IdentityFile ~/.ssh/<你的密钥>
```

先用 `ssh -T git@github.com` 确认回显 `Hi <user>! You've successfully authenticated, ...`。

### 末选：HTTP 代理 + HTTPS 通道直推（跳出沙箱也不通时）

**症状**：跳出沙箱后仍报 `Connection closed by <ip> port 443`，或 `Connection closed by UNKNOWN port 65535`。
说明问题**不在沙箱白名单**，而在本机到 GitHub SSH 端点的链路（波动 / 被拦）。

先确认本地代理是否活着（端口按实际代理软件调整）：

```bash
for p in 7897 7890 1087 6152; do nc -z -G 2 127.0.0.1 $p 2>/dev/null && echo "$p 开着"; done
```

⚠️ **macOS 自带的 `nc` 不支持 `-X`（SOCKS5）** —— 看 `nc -h` 的 `usage` 行，里面没有 `-X`。
所以 `ProxyCommand "nc -X 5 -x 127.0.0.1:7897 %h %p"` 必然失败（报 `UNKNOWN port 65535`）。
**别在这条路上耗时间**，改用 git 自己的 HTTP 代理 + HTTPS 通道：

```bash
T=$(/opt/homebrew/bin/gh auth token)          # 放进变量，别把 token 直接写进命令字符串
git -c http.proxy=http://127.0.0.1:7897 \
    -c https.proxy=http://127.0.0.1:7897 \
    push "https://x-access-token:${T}@github.com/<owner>/<repo>.git" main:main
```

成功输出形如 `3577591..9134b0e  main -> main`。

**为什么用这个**：`-c` 是**一次性**配置——不动 `origin`（仍保留 SSH）、不动 `~/.ssh/config`、
不动全局 git config。Clash 的混合端口 HTTP 与 SOCKS 共用一个数字，直接用 `http://` 前缀即可。

### 建仓 / 查询在沙箱内照常做

`gh repo create --private`、`gh api` 都走 `api.github.com`，**沙箱内可用**，无需跳出。

## 五、推送后必须复验（返回码 ≠ 结果）

```bash
GH=/opt/homebrew/bin/gh            # 非交互 shell 里 gh 常常不在 PATH
R=owner/repo
$GH api repos/$R --jq '{private:.private,default_branch:.default_branch,pushed_at:.pushed_at}'
$GH api repos/$R/commits --jq '.[] | "\(.sha[0:7]) \(.commit.author.name) <\(.commit.author.email)>"'
$GH api "repos/$R/git/trees/main?recursive=1" --jq '[.tree[]|select(.type=="blob")]|length'
$GH api "repos/$R/git/trees/main?recursive=1" --jq '[.tree[].path|select(test("^(cache/|\\.backups/|.*__pycache__)"))]|length'
```

四项依次确认：**可见性 / 提交身份（绝不能是真实姓名）/ 文件数 / 忽略规则真的生效**。

### ⚠️ 跟踪引用陷阱：直推之后 `git status` 会显示「假落后」

用上面的 `git push "https://x-access-token:${T}@github.com/..."` 直推时，**不会更新
`refs/remotes/origin/main`**（因为推的目标 URL 不是名为 `origin` 的远端）。
后果：复验时 `git status -sb` 显示 `## main...origin/main [ahead 2]`，
看起来"没推上去/落后了"，实际远端早就是最新 —— **假象**。

```bash
# ✅ 判据：查远端真值，别信本地跟踪引用
git ls-remote "https://x-access-token:${T}@github.com/<owner>/<repo>.git" HEAD refs/heads/main

# 想让跟踪引用对齐（可选，纯为消除告警）
git fetch "https://x-access-token:${T}@github.com/<owner>/<repo>.git" main:refs/remotes/origin/main -f
```

**记法**：本地跟踪引用是**缓存**，远端才是事实源。凡"推成功了但状态显示落后"，
先 `ls-remote` 对一下，别急着再推一次（重复推不会出错，但会让你误判推没推上去）。

## 六、其他边角坑

- **`gh` 不在 PATH**：非交互 shell 里 `command -v gh` 常为空 → 用 `/opt/homebrew/bin/gh` 全路径。
- **`git ls-files -z | xargs -0 grep -l <中文模式>` 偶发静默返回空**（无报错、结果为空）：
  批量扫描时改用 `for f in $(git ls-files); do grep -q "<模式>" "$f" && echo "$f"; done`。
  同理，**沙箱内 shell 的 grep 打中文会乱码**——查中文优先用 Grep 工具。
- **提交身份**：推之前先钉死仓库级身份（见 skill `git-identity-pin`），别依赖全局配置。

## 七、一句话总结

> `gh api` 通、`git push` 不通 = 沙箱白名单 → **把 push 那条命令跳出沙箱跑**，然后 `gh api` 复验四项。
