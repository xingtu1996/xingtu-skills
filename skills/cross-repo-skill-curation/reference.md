# reference.md — 跨仓技能策展蒸馏参考

> 承载：四分类判据全表、去重比对技法、hooks 单独评估细则、ctf 首案实录、策展报告模板、落地验证 snippet。SKILL.md 只留流程骨架，细节查这里。

## 一、四分类判据全表

### GENERIC-KEEP（通用可蒸）

满足**全部**：

1. 机制是**流程/纪律/框架**类（如"侦察→Spec→红队→收口"、"配置减法治理闭环"、"何时不并行裁决"），不含特定业务对象；
2. 抹去仓名/路径/人名后仍然完整可执行；
3. 解决的是**跨仓共有的失败模式**（重复造轮子、自查盲区、副本腐烂、越界操作）；
4. 现有三池无同机制覆盖（或只可增强）。

### SKIP-项目·公司专属

命中**任一**即 SKIP：

- 正文含公司/客户/内部产品全称、内网域名、私有 repo 路径、密钥/凭证引用；
- 引用该仓特有目录结构且迁移后需大改（改后已非原机制）；
- 业务口径判断标准（如特定平台的审核阈值、特定基金的合规规则）；
- 脱敏后语义坍塌——把专有名词挖掉就不知道在说什么。

**注意**：专属≠无价值。可在报告中建议 boss 在**该工作区内**单独策展为项目 skill（带范围守卫），但不进全局。

### SKIP-Anthropic / 工具方官方样例

- 名字/正文含 example、starter、template-demo、官方 README 复述；
- 机制在官方文档可查且无该仓自己的工程化增量；
- 判据：蒸它等于抄官方文档，零新增。

### DUPLICATE（与现有池重复）

- 三池 grep 命中同机制关键词（不只同名）；
- 处置三分法：
  - **完全覆盖** → 放弃 + 报告注明"已有 X 覆盖"；
  - **部分覆盖** → 增强既有文件（补小节 + version bump），禁止新造平行技能；
  - **异名近义**（如全局池与项目池各有一份话术技能） → 报告中标注为**既有双副本债务**，交 boss 决定是否按"三池去重→单一事实源+回收站"清算（参考 09-15 `wechat-group-promo-copy` 并入 `mp-group-push-copy` 案例）。

## 二、去重比对技法

```bash
# 按机制词跨池 grep（不要只看技能名）
for pool in ~/.qwenworkcn/skills ${SKILLS_DIR}/skills <项目>/.agents/skills; do
  grep -rliE "何时不并行|并行上限|依赖DAG" "$pool" 2>/dev/null
done

# 同名不同物核验：看 frontmatter description 的触发场景是否真的重叠
head -12 ~/.qwenworkcn/skills/<候选>/SKILL.md
```

- 候选机制词从 Step 0 侦察笔记里取**动词短语**（"交叉验证判真伪"、"独立上下文红队"），不用名词（"review"会满屏命中）。
- 增强落点选择：机制属于既有技能某小节的自然延伸 → 进该文件；是新的独立操作入口 → 才允许新技能。

## 三、hooks / 守卫类单独评估细则

1. **机制兼容性先查再落**：
   - Claude Code：PreToolUse/PostToolUse hook，注册在 settings；
   - ZCode：`.zcode/config.json` + `.zcode/hooks/guard.py`；
   - 千问办公（QwenWork）：**无用户可注册 hook 层**（2026-09-16 实测：settings 无 hooks 项）。此类守卫只对其 Claude/对应 agent 侧生效；千问侧兜底靠规则层（AGENTS.md 红线）+ `tools/safety/` 脚本。落盘时 README 必须写明"对哪个工具生效、对哪个不生效"。
2. **不擅自改 settings.json / config.yaml**——可能与并行任务冲突；注册方式写 README，由 boss 或对应工具会话执行。
3. **实拦测试正反例**（落前跑、测后清日志）：
   - 反例必含绕过变体：大写 `RM -RF`、带引号路径、`find -delete`、`git add -A`；
   - 正例（应放行）：正常构建命令如 `mvn clean package`、`.env.example` 读取；
   - ctf 教训：初版只拦小写，大写绕过被蒸馏代理自查发现并补正则——**复核方仍要独立再测一遍**，不认自查结论。
4. **fail-open 约定**：hook 解析失败放行还是阻断要显式声明（xingtu ZCode 侧 = fail-open，红线兜底在规则层）。
5. 测试触发的运行时日志（`.stats.log` 等）在交付前移出 hooks 目录。

## 四、ctf 首案实录（2026-09-16，策展管线首个完整凭证）

| 资产 | 分类 | 处置 | 验证 |
|---|---|---|---|
| harness-governance（配置减法 SOP） | GENERIC-KEEP | 落双池：`${SKILLS_DIR}/skills/` + `~/.qwenworkcn/skills/` | `diff -q` 两池字节相同；技能列表可见已注册 |
| multi-agent"何时不并行"裁决矩阵 | DUPLICATE-部分覆盖 | **未新造 skill**：P0 串行/P1 并行≤3-5/P2 顺延 + 裁决清单增强进 `specs-engine/references/orchestration.md` §三 | grep 小节在位 |
| 对抗审查三点（脚本交叉验证不请 LLM 法官 / Filter 拦 30-50% 误报 / 用原文片段不用行号定位） | DUPLICATE-部分覆盖 | 并入 `spec-driven-adversarial-workflow` v1.1→**1.2.0** | version 位 + 三点关键词 grep |
| PreToolUse hooks（rm 硬删/敏感文件拦截） | 守卫类单评 | 落 `xingtu/.claude/hooks/` + README；**明确告知千问侧不生效**；未动 settings | 正反例实拦（含大写 RM 补正则）；mvn 放行 |
| ctf 专属段（mvn 相关红线等） | SKIP-项目专属 | 剥离不带入 | — |

收口动作：复核期 `.stats.log` 移出、CHANGELOG 各自留痕、两任务（蒸馏 + 主线 Phase1）零交叉污染。

## 五、策展报告模板

```markdown
# 跨仓策展报告 — <来源仓> → 技能池（YYYY-MM-DD）

## 一、全量分类表
| # | 资产 | 类型(skill/agent/hook/规则) | 分类 | 一句话理由 |

## 二、top-N 蒸馏候选（各三段式）
### 1. <名称>
- 核心机制：
- 相比现有池新增：
- 建议落点：<池 / 全局 or 工作区> + 理由（含污染风险权衡）

## 三、hooks/守卫类单评
- 机制兼容性结论 / 生效面 / 注册方式 / 实拦测试计划

## 四、明确不搬清单（SKIP 各类，含"官方样例/公司侧"）

## 五、既有双副本债务（如发现）

> 状态：未落地任何文件，待 boss 逐项拍板。
```

拍板话术约定：boss 回编号即可（"1、3 落，2 弃，hooks 只落 X 侧"）；未提及项默认不落。

## 六、落地验证 snippet 集

```bash
# 双池同源
diff -q ${SKILLS_DIR}/skills/<name>/SKILL.md ~/.qwenworkcn/skills/<name>/SKILL.md && echo IDENTICAL

# 增强版本位
grep -n "version:" ~/.qwenworkcn/skills/<name>/SKILL.md
grep -n "<新增小节标题>" <被增强文件>

# 来源标注在位
grep -n "策展\|机制源自" ~/.qwenworkcn/skills/<name>/SKILL.md

# 交付纯净（hook 测试日志已清）
ls -la <hooks 目录>

# 报告阶段零变更（拍板前核验目标仓与三池未被改动）
find ~/.qwenworkcn/skills -name SKILL.md -newermt "today" | sort
```
