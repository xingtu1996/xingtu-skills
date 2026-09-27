---
name: xingtu-token-saver
description: >
  一键诊断当前工作空间的「省 Token 成熟度」——按八层清单（需求/检索/协议/输入压缩/
  散文/生成/prompt/config）逐层扫描打分，输出 HTML/JSON 报告 + 补丁建议。
  只诊断不改配置（不动用户 settings.json），opt-in 手动触发，不污染对话。
  触发词：token-saver、省token诊断、token 诊断、六层诊断、省 token 检查、
  token audit、账单瘦身检查。
argument-hint: "[--pack=lite|full] [--format=text|json]"
license: MIT
---

# xingtu-token-saver（行途省 Token 聚合诊断）

把散在 6 个工具 + 2 层包装里的省 Token 实践收口成**一次诊断**。
母题：把「不用推理的活」从模型手里拿回来。

## 铁律（先读，违反即停）

1. **只诊断，不修改**：绝不改用户的 `.claude/settings.json` / `CLAUDE.md` / SOUL.md。只输出建议。
2. **不发明新命令**：原生命令只有 `/clear`（免费、全新开始）、`/compact`（保留断点但压缩本身花钱）、`/model`（切换会打爆 prompt 缓存）。
3. **opt-in**：用户显式调用才跑，不自动挂 hook、不进每轮对话。

## 用法

用户说「跑一下 token-saver」或 `/xingtu-token-saver [--pack=lite] [--format=text]` 时：

1. 读 `references/checklist.json`（八层检查清单，机器可读）。
2. 执行诊断脚本（标准库零依赖，只读）：

```bash
python3 scripts/token_saver_audit.py --cwd <工作空间路径> --format text   # 人看
python3 scripts/token_saver_audit.py --cwd <工作空间路径> --format json   # 喂给 AI 自动补齐
```

3. 按脚本输出的 `suggestions` 逐条给用户解读：**先说结论（几分、最亏的 2 层），再给补丁**。补丁给命令/改法，不代执行。
4. lite 包只跑静态扫描（~30 项）；full 包在 lite 基础上追加：会话操作习惯访谈（/model 切换频率、/compact vs /clear 偏好）+ 实测账单抽查。

## 八层清单（速览）

| 层 | 名称 | 一句话自检 |
|---|---|---|
| L1 | 需求层 | 有 specs/ 且 No Spec No Code？Reverse Sync 到位？ |
| L2 | 检索层 | CBM/CodeGraph 在用？grep 盲搜 < 5 次/任务？ |
| L3 | 协议层 | rtk 类输出压缩是否挂上？命令行输出 < 1KB？ |
| L4 | 输入压缩层 | 上下文能引用就不粘、能过滤就先滤？ |
| L5 | 散文层 | outputStyle Concise / caveman 类精简安装？ |
| L6 | 生成层 | ponytail 类 YAGNI 在用？代码量 < 50 行/功能？ |
| L7 | prompt 层 | system prompt 有三段论（立规矩→给反例→兜底自问）？ |
| L8 | config 层 | 缓存友好（中途不切 /model）、compact 窗口合理？ |

## 报告口径

- 每层 0-100 分，总分 = 八层均值。**≥80 健康 / 60-79 可补 / <60 优先补**。
- 所有分数是「配置成熟度」不是「省了多少钱」；涉及金额必须标注来源与实测日期（BUL-003）。
- 文案红线：省的是「**不必要** token」，不是省推理。金句：**省 token 是顺便，把『不必要』剥掉才是真本事。**
