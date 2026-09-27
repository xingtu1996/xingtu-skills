# XingTu Skills · AI Agent 技能聚合仓

> 一份发布，多工具通用（Claude Code / CodeBuddy / Codex / Cursor / Gemini CLI）。find-skills 可检索。

![License](https://img.shields.io/badge/license-MIT-green.svg) ![Skills](https://img.shields.io/badge/skills-41-blue.svg) ![Platform](https://img.shields.io/badge/platform-Claude%20%7C%20CodeBuddy%20%7C%20Codex%20%7C%20Cursor%20%7C%20Gemini%20CLI-orange.svg) ![Categories](https://img.shields.io/badge/categories-4-purple.svg) ![Last Commit](https://img.shields.io/github/last-commit/xingtu1996/xingtu-skills.svg)

## 🎯 这是什么

`xingtu-skills` 是行途开源矩阵的**技能资产仓**。收录在真实 AI 工程实践中打磨的 SKILL.md 技能，遵循跨工具事实标准（name + description + when_to_use），一个技能全平台可用。

**已收录 41 个生产级技能**，覆盖：token 压缩、代码审查、安全重构、调研、迁移、证据审查、仓库探索、验证收敛、内容去AI味、对抗审查、数据核实、事实核查门禁、沙箱网络绕行、零依赖分发、零成本视觉等场景。

## 🧩 DeepSeek Harness（DSH）兼容

本仓技能遵循跨工具事实标准（SKILL.md：`name + description + when_to_use`），是 DeepSeek Harness「一切皆插件」模型中 **skills 插件**的直接消费格式——DSH 可将 `skills/` 目录作为技能插件加载，无需改写。同一份技能同时兼容 Claude Code / CodeBuddy / Codex / Cursor / Gemini CLI。

## 📦 安装

```bash
# 方式一：harness 一键拉全
git clone --recurse-submodules https://github.com/xingtu1996/xingtu-harness.git
cd xingtu-harness && ./install.sh

# 方式二：单独拉本仓
git clone https://github.com/xingtu1996/xingtu-skills.git
cp -r skills/<skill-name> ~/.claude/skills/
```

## 🧠 Skills 清单（41）

### 内容创作 · 自媒体（4 · 2026-09-11 新增 fact-check-gate）
| Skill | 说明 |
|-------|------|
| de-ai-flavor | 行途自媒体去 AI 味：公众号/封面/标题/摘要文案人话化（PUB-013 五法） |
| adversarial-review | 行途自媒体多专家对抗审查：封面/标题/正文/数据四角色并行（PUB-017） |
| codemax-report | 行途数据核实：cc-switch 本地库核实文章数字 + CodeMax API 汇报 |
| fact-check-gate | 行途成稿事实核查门禁：拆层→五档标记→推理链检查→补强版（PUB-018 + BCI B-009） |

### 工具链 · 工程化实战（9 · 🆕 2026-09-27 新增）
| Skill | 说明 |
|-------|------|
| git-push-in-sandbox | 沙箱内 `git push` 失败（502 CONNECT tunnel / ssh 超时）的诊断与绕行：`gh api` 通而 push 不通时的四条通道选型 |
| python-cli-to-macos-app | Python/CLI → 零依赖 macOS `.app`：体积账算法 + 三条生死线检测（relocate / `otool -L` / 静态二进制）+ launcher 设计 |
| zero-cost-visuals-iconify | 零成本画面层：Iconify 20 万+ 开源图标按关键词取图 + 品牌色上色 + 离线缓存；含受控词表前置的核心教训 |
| xingtu-token-saver | 省 Token 成熟度八层诊断（需求/检索/协议/输入压缩/散文/生成/prompt/config），只诊断不改配置 |
| skill-vetter | 安装前安全审查：装任何社区/第三方 skill 之前先查红旗、权限范围与可疑模式 |
| constitution-amendment | 把口述定调落成项目宪法条目（CONSTITUTION.md / rules/）的 SOP：找缺口→备份→入宪→联动同步→CHANGELOG |
| repo-rename-desensitize | 项目/仓库全库更名 + 真名脱敏一体式 SOP：影响面盘点→批量替换→分类脱敏→历史暴露面核查→产物重打包 |
| sqlcipher-offline-verify | 离线验证 SQLCipher 4 数据库密钥（HMAC-SHA512 页校验筛真密钥），仅密码学校验，不涉及逆向/注入 |
| xingtu-collab-evolution-loop | AI 协作偏好自我进化闭环：调研取证→复盘归因→沉淀 SSoT→反哺约束 四环工作流 + 四不防错自检 |

### 交付质量 · 通用（2）
| Skill | 说明 |
|-------|------|
| discernment-nudge | 交付后追加核验追问，防盲从 |
| writing-guidelines | 单篇文风与写作规范审查 |

### Caveman 系列 · token 压缩与工作流（14）
| Skill | 说明 |
|-------|------|
| caveman | 极简压缩沟通模式，实测省 65% 输出 token |
| caveman-commit | 超压缩 commit message 生成 |
| caveman-compress | 压缩记忆类自然语言文件（CLAUDE.md 等） |
| caveman-discover | 发现仓库内所有 LLM 工作流 |
| caveman-evidence-review | 只读审查 Caveman Cloud 证据 |
| caveman-explore | 只读仓库探索器，主动使用 |
| caveman-help | 全部 caveman 模式的速查卡 |
| caveman-learn | 闭环 Caveman learn 报告 |
| caveman-manage | 管理 caveman 模式配置 |
| caveman-optimize | 优化 token 使用 |
| caveman-review | 审查/评估 |
| caveman-setup | 初始化配置 |
| caveman-stats | 统计分析与使用情况 |
| cavecrew | 委派给 caveman 风格子代理的决策指南 |

### Ponytail 系列 · 极简与债务（6）
| Skill | 说明 |
|-------|------|
| ponytail | 懒但正确——最简可行解，质疑任务必要性 |
| ponytail-audit | 债务审计 |
| ponytail-debt | 技术债识别与记录 |
| ponytail-gain | 增益分析 |
| ponytail-help | 速查卡 |
| ponytail-review | 审查 |

### 工程实践（6）
| Skill | 说明 |
|-------|------|
| investigate-first | 先调查后行动 |
| lean-build | 精益构建 |
| migration | 迁移支持 |
| safe-refactor | 保持行为的重构 |
| surgical-patch | 外科手术式精准修改 |
| verify-and-stop | 验证即止，不扩范围 |

## 🔍 AI 可检索

- **`marketplace.json`**：37 条技能索引（name + description + tags），供 find-skills 检索
- **SKILL.md frontmatter**：description 遵循 `[做什么] + [Use when: 关键词]` 公式，是唯一被自动检索的字段
- **跨工具事实标准**：一份 SKILL.md，Claude Code / CodeBuddy / Codex / Cursor / Gemini CLI 通用

## 关联项目

- [xingtu-prompts](https://github.com/xingtu1996/xingtu-prompts) — 提示词库：轻场景复制即用；沉淀成 Skill 后进本仓
- [dsh-xingtu-skills](https://github.com/xingtu1996/dsh-xingtu-skills) — DSH 插件包：本仓技能的 DSH 一键安装版

## 关于作者 · 行途

一线 AI 工程化实践者 · FDE 方向。这些技能不是写出来的，是每天真用、用完回炉改的。

- 公众号「**行途技术手记**」（长文首发，微信搜索关注）
- GitHub / X：`@xingtu1996` ｜ 博客：https://xingtu1996.github.io
- 方法论旗舰仓：[xingtu-ai-engineering](https://github.com/xingtu1996/xingtu-ai-engineering)

## 📄 许可证

MIT License

