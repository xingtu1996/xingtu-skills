---
name: xingtu-workspace-context
description: 行途工作空间上下文桥接（豆包/通用版）——当用户在行途(xingtu)自媒体复利工程工作区协作，需要理解空间定位、六层架构、关键路径、工作铁律、Skill路由时使用。触发词：行途工作空间、开始行途工作、xingtu上下文、行途空间规则、了解行途。豆包工作区不吃 AGENTS.md/CLAUDE.md，本 Skill 以 SKILL.md 桥接注入行途空间上下文。
---

# 行途工作空间上下文（豆包桥接版）

> 豆包工作区不读取项目根目录 AGENTS.md / .claude/CLAUDE.md，本 Skill 用 SKILL.md 桥接注入行途空间的核心上下文。遇到"行途/素材/选题/入库/沉淀"等任务时，先加载本上下文再执行。

## 空间定位

行途 = 自媒体复利工程工作区。服务于主理人「行途」（Builder · 仍在写代码），深度参与其 **AI 时代个人 IP 与内容资产复利工程**。

- AI 是选手（受控轨道上执行），人是裁判（审查决策），同一套标准人 AI 共用。
- 核心是**内容与素材资产**（xingtu-vault / 素材库），工具是手段。

## 关键路径（常用）

| 内容 | 路径 |
|------|------|
| 素材库（可发布素材卡 + 索引） | `${WORKSPACE}/素材库/`（`素材库索引.md`） |
| 内容仓库（vault） | `${WORKSPACE}/xingtu-vault/02_内容仓库 (Content Hub)/` |
| 元宝素材挖掘 | `.../06_元宝对话挖掘/` |
| 会话复盘 | `.../04_会话与复盘 (Archive & Review)/` |
| 选题池 | `.../01_灵感与选题池/` |
| 工具脚本 | `${WORKSPACE}/tools/` |
| Skills 统一事实源 | `${WORKSPACE}/.agents/skills/` |

## 资产入口（先读这三个）

1. `DIRECTORY.md` — 资产注册中心（所有 harness 资产位置）
2. `HARNESS.md` — 产品说明书（六层架构/纪律/兼容铁律）
3. `README.md` — 内容工程总览

## 工作铁律（红线）

1. 安全删除 + 先备份（禁 rm 硬删，用 `tools/safety/safe-delete.sh`）
2. 响应力优先（前沿实践快速转内容）
3. 利他第一性（内容对准目标用户、积累信任）
4. 差异化分发（禁一篇通稿全平台同步）
5. 自包含（产物不硬编码绝对路径）
6. 防弹工作法（决策留痕 BUL-001、不揽超本分 BUL-002、数字标注来源 BUL-003、方向反复对齐 BUL-004）
7. **敏感信息脱敏**：当前雇主/薪资/入职年限/隐私数据按用户偏好模糊化（强信息安全意识）

## Skill 路由（豆包触发词）

| 操作类型 | 触发 Skill | 用途 |
|------|------|------|
| 沉淀会话/复盘/总结 | `session-sediment` | 会话即刻沉淀反哺素材库 |
| 入库/收素材/存素材库 | `xingtu-ingest` | 素材入库总控 |
| 抓元宝文章 | `yuanbao-article-fetch` | 元宝链接抓全文 |
| 写/改公众号 | `xingtu-content-craft` | 内容创作总装 |
| 审查文风 | `writing-guidelines` | 写作规范审查 |
| 交付后核验 | `discernment-nudge` | 核验追问防盲从 |

## 素材入库流程（用户说"入库"时）

```
读取内容 → 价值分级(🥇黄金/🔴关键/🟡重点/🟢高知) → 定落点
→ 生成素材卡/选题/萃取 → 落盘 → 登记索引(素材库/素材库索引.md) → 输出入库报告
```

## 跨工具机制速查

| 工具 | 读取入口 | Skill 来源 |
|------|---------|-----------|
| Claude Code | `.claude/CLAUDE.md`（+ 根 AGENTS.md） | `.claude/skills/`（软链） |
| Codex | 根 `AGENTS.md` | `$REPO_ROOT/.agents/skills`（自动扫描） |
| WorkBuddy | 根 `AGENTS.md`（含 Skill 触发映射表） | `.workbuddy/skills/`（软链） |
| 豆包工作 | 不吃 AGENTS.md/CLAUDE.md | `.agents/skills`（skill roots 扫描）+ `.user_skills` |

## 版本历史

| 日期 | 变更 |
|------|------|
| 2026-09-02 | V1.0 新建：豆包/通用桥接版（解决豆包不吃 AGENTS.md 的上下文注入缺口） |

<!-- public-sync: 2026-09-27 | 脱敏版本 | 源 .agents/skills/xingtu-workspace-context -->
