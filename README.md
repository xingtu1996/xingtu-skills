# XingTu Skills · AI Agent 技能聚合仓

> 一份发布，多工具通用（Claude Code / CodeBuddy / Codex / Cursor / Gemini CLI）。find-skills 可检索。

![MIT](https://img.shields.io/badge/license-MIT-green.svg)

## 🎯 这是什么

`xingtu-skills` 是行途开源矩阵的**技能资产仓**。收录在真实 AI 工程实践中打磨的 SKILL.md 技能，遵循跨工具事实标准（name + description + when_to_use），一个技能全平台可用。

**已收录 26 个生产级技能**，覆盖：token 压缩、代码审查、安全重构、调研、迁移、证据审查、仓库探索、验证收敛等场景。

## 📦 安装

```bash
# 方式一：harness 一键拉全
git clone --recurse-submodules https://github.com/xingtu1996/xingtu-harness.git
cd xingtu-harness && ./install.sh

# 方式二：单独拉本仓
git clone https://github.com/xingtu1996/xingtu-skills.git
cp -r skills/<skill-name> ~/.claude/skills/
```

## 🧠 Skills 清单（26）

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

- **`marketplace.json`**：26 条技能索引（name + description + tags），供 find-skills 检索
- **SKILL.md frontmatter**：description 遵循 `[做什么] + [Use when: 关键词]` 公式，是唯一被自动检索的字段
- **跨工具事实标准**：一份 SKILL.md，Claude Code / CodeBuddy / Codex / Cursor / Gemini CLI 通用

## 📄 许可证

MIT License

---

> AI 辅助创作 · 内容基于真实工程实践
