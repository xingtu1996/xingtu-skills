# XingTu Skills · AI Agent 技能聚合仓

> 一份发布，多工具通用（Claude Code / CodeBuddy / Codex / Cursor / Gemini CLI）。find-skills 可检索。

> **👋 云端 Agent（Muse）从这里开始**：若你要接手行途公众号全域运营，按序读——
> ① `MUSE-ONBOARDING.md`（接入手册 + 可直接投喂的选题/工作流提示词）→ ② `PUBLISHING-PIPELINE.md`（端到端流程地图 + 硬闸门）→ ③ 按需 Read `skills/<名称>/SKILL.md`。
> 私有全量口径在 `xingtu1996/xingtu-vault`（授权后读 `云端AGENT入口.md`）。

![License](https://img.shields.io/badge/license-MIT-green.svg) ![Skills](https://img.shields.io/badge/skills-82-blue.svg) ![Platform](https://img.shields.io/badge/platform-Claude%20%7C%20CodeBuddy%20%7C%20Codex%20%7C%20Cursor%20%7C%20Gemini%20CLI-orange.svg) ![Categories](https://img.shields.io/badge/categories-5-purple.svg) ![Last Commit](https://img.shields.io/github/last-commit/xingtu1996/xingtu-skills.svg)

## 🎯 这是什么

`xingtu-skills` 是行途开源矩阵的**技能资产仓**。收录在真实 AI 工程实践中打磨的 SKILL.md 技能，遵循跨工具事实标准（name + description + when_to_use），一个技能全平台可用。

**已收录 82 个生产级技能**，覆盖：token 压缩、代码审查、安全重构、调研、迁移、证据审查、仓库探索、验证收敛、内容去AI味、对抗审查、数据核实、事实核查门禁、沙箱网络绕行、零依赖分发、零成本视觉、开源巡检、身份钉定等场景。

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

## 🧠 Skills 清单（82）

### 内容创作 · 自媒体（4 · 2026-09-11 新增 fact-check-gate）
| Skill | 说明 |
|-------|------|
| de-ai-flavor | 行途自媒体去 AI 味：公众号/封面/标题/摘要文案人话化（PUB-013 五法） |
| adversarial-review | 行途自媒体多专家对抗审查：封面/标题/正文/数据四角色并行（PUB-017） |
| codemax-report | 行途数据核实：cc-switch 本地库核实文章数字 + CodeMax API 汇报 |
| fact-check-gate | 行途成稿事实核查门禁：拆层→五档标记→推理链检查→补强版（PUB-018 + BCI B-009） |

### 技能治理（4 · 🆕 2026-09-27 第四批）
| Skill | 说明 |
|-------|------|
| evolve-skills | >- 技能建议 / 技能体检 / 要不要做成技能 / 这个该沉淀成技能吗 / 技能该升级了 / 技能老化了 / 技能没人用 / 技能触发不了 / 技能该淘汰 / 库太肥了要淘 / skill hygiene / skill evolution —— 在干活的过程中主动产出**技能建议**：① 建议* |
| harness-governance | 对 harness 常驻配置层做减法治理闭环：审计→报告→人审→执行→回归。标尺：常驻<窗口5%、入口<200行、单文件<16KB；五分类 KEEP/SIMPLIFY/MOVE/DELETE/CONFLICT；只移不删、人审不可跳过。触发词：harness 治理/瘦身/审计/配置减法/上下文超标/s |
| cross-repo-skill-curation | 跨仓技能策展蒸馏 playbook。当用户让另一个仓/项目的 .claude（skills/agents/hooks/CLAUDE.md/settings）里"有什么值得蒸馏/借鉴/搬过来"，或要把某仓成熟资产收进技能池时使用。流程：只读侦察 → 四分类分级（GENERIC-KEEP / SKIP- |
| egress-allowlist | 给环境做外网放通清单（白名单域名）——适用于"给客户做外网放通清单""这个环境要放通哪些域名""外网访问需求""白名单怎么列""依赖库下载源有哪些"。核心是查清每个服务的真实下载域名（含 CDN），避免只列主域名导致"能查询、不能下载"。 |

### 内容工程 · 发布运营（28 · 🆕 2026-09-27 第三批 +27，含首批范式 wechat-draft-api）
| Skill | 说明 |
|-------|------|
| conference-archive | 会议/论坛/行业大会素材归档与蒸馏。当用户参加完线下会议、行业论坛、技术大会后，要求"整理一下""归档""沉淀素材""把录音和拍图整理成文章素材库"时使用。输入：录音 record_id、现场拍图、口述观点、官方议程 PDF、系统纪要。输出 |
| content-matrix-channel-audit | 全渠道内容矩阵环境审计（周期性战略盘点，只读不动手）：以资深全平台内容运营操盘手视角，实地核实固定数据源（materials_library.json + 今日调度_*.json + 分发凭证 glob + 变现盘点 README + 各分 |
| legal-compliance-baseline | 法律合规基线维护与出书适配性延伸检查。Use when 用户说跑合规扫描/合规门禁/法律基线、极限词误报太多/精度调整/白名单迭代、content_gate 第⑦门禁接入/维护、AI标识义务/人工智能生成合成内容标识办法待办、🟡人工核清单管 |
| mp-daily-ops-report | 行途每日晨间决策指令 + 封面交替管线（定时 09:30 / 手动补跑）。当用户说"出运营日报/跑日报/补跑今天日报/今天数据怎么样/明日封面什么底色/封面交替判定/日报简报推微信/日报定时任务挂了"时触发。以资深全平台 IP 操盘手角色预 |
| mp-distribution-evidence-loop | 行途分发闭环回填傻瓜流程：发出去之后把凭证收进闭环。当用户说"发出去了/截图给你/回填凭证/闭环率怎么涨/丢进投放口/今天分发算不算数/闭环转起来了吗"时触发。截图规范命名 `分发凭证_<平台>_<日期>` 入 `outputs/多平台分发 |
| mp-group-push-copy | 公众号发布配套的群推话术四版 + 置顶评论生成管线。当用户说"给我群推话术/置顶评论/怎么转发到群里/帮我写推荐语/这篇往哪个群发/发出去没人看/群里发了带来关注了再来要/话术缺活人味/置顶像空气对话/留言区要不要带#"时触发。读家族存档与 |
| mp-sentiment-tracker | > |
| mp-title-collision-rename | 公众号标题撞题核查与换题执行闭环：WebSearch 双查取并集 → 撞题判定（同题含大媒体 ≥3 篇 = 换题）→ 规则出三候选交 boss 拍板 → 六载体同步替换（先数后改、assert 实测计数）→ 封面改文案 + 字号断行自检 + |
| xingtu-expression-logic | > |
| xingtu-ingest | 素材入库总控（行途）——当用户说"入库/收入素材库/存到素材库/记一下这条素材/把这个收进选题池/分析并入库"并给出内容（文本/链接/对话/想法/截图描述）时使用。自动分析内容价值分级（黄金/关键/重点/高知），按类型落到素材卡/选题池/黄 |
| xingtu-orchestrate | > |
| audio-friendly-adapt | 听友好版改编 skill——把图文成稿派生为适合语音朗读/播客/视频号语音的纯文本版本。自动执行 PUB-024 六条铁律（砍元信息/编号口语化/数字口语化/图表口述/加问候道别/命名规范），改编后过 PUB-026 完结检查。触发词：听友 |
| certification-submission-kit | 平台个人/职业认证提交包生成流水线。Use when 用户说 公众号认证/视频号认证/知乎认证/掘金认证/百家号认证/CSDN认证/小红书认证/职业认证/身份认证/兴趣认证/认证描述/公众称谓/主体姓名/职业身份/认证材料/认证驳回/认证额 |
| concept-anchor-figure | Turn one article's core idea into a single watermark-free vector infographic (HTML -> PNG via fig_fit), in the workspace |
| content-format-audit | 内容格式策略评估管线（阶段性复跑、跨篇策略级，只评估不动稿）：提取正文格式元素清单（blockquote 摘要/我是谁/目录/信息说明/标签行/合集块/延伸阅读/图注等 + 首屏结构检查）→ 对标双参照系（机构媒体 APPSO/机器之心 v |
| mp-group-audience-check | 微信群熟人密度安检——在群里推公众号内容前，先查该群成员中有多少是你的微信好友（通过单聊消息表验证真好友，排除群里见过但没加的人），输出熟人密度评级和"能不能推"建议。触发词：查群里有多少好友、群里有没有熟人、能不能在这个群发公众号、群熟人 |
| mp-publish-sop | 公众号「成稿→草稿箱」十步一条龙 SOP 编排层（🆕 09-16，v1.8.0 TOKEN-09 复盘）：串联事实回源/标题撞题/图文密度/法律合规/排版重渲/封面三检/门禁/建稿回查/回收/配套件，含本轮全部实测坑位与回查凭证模板，供任意 |
| pub-infographic-supplement | 公众号长文图文密度补齐管线：按 PUB-048 做图/千字密度对标 → 定位文字墙节 → 素材只取正文原文写信息图 HTML（家族配色：纯白 #FFFFFF 底、黑红灰主色，DESIGN.md §四；1080px 视口 @2x）→ fig_ |
| session-sediment | 会话即刻沉淀 xingtu 版——自动盘点成果/决策链/AI协作模式/沉淀资产/纠偏偏好/踩坑教训，反哺到行途素材库（xingtu-vault）+ 会话复盘 + 选题池 + 元宝素材库，产出继续会话提示词。触发词：沉淀会话/会话沉淀/记录会 |
| wechat-channel | 本地微信通道（行途）——读取、萃取、蒸馏、获取本地微信消息，支持按联系人或群（wxid 定位），支持按名字/关键词反查 wxid。触发词：微信通道、读微信、微信消息、微信萃取、微信蒸馏、微信抓取、查微信聊天、导出聊天记录、微信会话盘点、搜微 |
| wechat-mp-analytics | 公众号后台只读数据分析（行途）——用 bsk 接管已登录 Chrome，拉取阅读/分享/粉丝/图文明细，回流舆情与内容战略研判。触发词：查公众号后台、拉后台数据、阅读分析、粉丝数据、数据分析、舆情回流、图文分析、已发表内容、mp.weixi |
| wechat-mp-publish | 微信公众号后台自动化发布 Skill。发前核查（群发额度/发表记录/草稿箱）→ 把一篇成稿（HTML/PM doc JSON/官方草稿 API）导入公众号草稿箱、设置标题/摘要/原创/封面/合集/公众号名片，最终引导人工群发的全流程自动化  |
| x-auto-publish | 行途品牌自动宣发：基于本地工作空间素材（发布包/推文素材包/配图/品牌台账），用 bsk 真实浏览器自动发推（Thread 接龙）、同步各平台 profile 资料、小红书图文发布框架。触发词：发推、发 X、宣发、同步 profile、换简 |
| xingtu-blue-ocean-strategy | 蓝海市场与受众战略分析（行途）——当用户要求为自己/公司/产品/内容账号/app/创业项目做市场调研、蓝海判断、受众与变现人群分析、需求缺口识别、定位与主方向锁定、90 天战略路线图时使用。也适用于「帮我分析下这个方向/赛道/人群」「这个市 |
| xingtu-multiplatform-distribution | 公众号首发后的多平台分发流水线——按平台规格生成变体（掘金/知乎/CSDN/小红书/抖音/X）+ 变体过 de_ai_flavor_check 去AI味 + 配图（HTML→PNG 卡片；母稿非表格信息图按本地绝对路径内嵌进变体 MD 并出 |
| xingtu-workspace-context | 行途工作空间上下文桥接（豆包/通用版）——当用户在行途(xingtu)自媒体复利工程工作区协作，需要理解空间定位、六层架构、关键路径、工作铁律、Skill路由时使用。触发词：行途工作空间、开始行途工作、xingtu上下文、行途空间规则、了解 |
| yuanbao-archive-pipeline | 元宝分享内容全流程自动化抓取→解密→提取→增量抓取→蒸馏→入库。触发词：抓元宝/元宝抓取/元宝入库/元宝归档/定时抓元宝/元宝全文抓取/元宝会话盘点。适用于用户转发给元宝AI的微信消息的自动化抓取、解析原稿、蒸馏提炼、入库到素材库。 |
| wechat-draft-api | 微信公众号官方 API 建稿：token 获取/草稿增删查/永久素材/封面图安全压缩，凭据全部参数化（环境变量+CLI），零第三方依赖。Use when: 草稿箱建稿、API 传图、发前 dry-run。 |
| mp-prepublish-draft-verify | 公众号发文前凭证闭环核验：事实回源→图文同步→建稿前五查（占位/灰框/主题色/图文密度/撞题）→dry-run「嵌图 N/N」→API 回查字节比对→回收缺陷稿。专治「看似就绪实则错名/漏榜/图静默消失」。 |
| publish-pack-planning | 发布包规划层总纲：动笔前把一个论点规划成整套发布包。Step 0 论证溯源（论点→论证→论据三段论+证伪）→基础素材→发布操作素材→分发话术→六目录验收。只规划不执行。 |
| daily-judgment-brief | 发布综合判断基线+每日对账：读判断土壤 reference.md→拉 stats/publish_board→排期与 48h 分诊对账→假设台账 H-* 逐条结算→落每日判断简报。发后评估与口径守卫，只读。 |
| wechat-cover-gen | 公众号封面生成管线（真人剪影路线）：image_gen 出无文字场景图→curl 下载→HTML 右侧压字→fig_fit 渲 900×383→Read 看图 OCR 回查。黑/白严格交替，三原色黑#1a1a1a/白#fff/橙红#F2644F。 |
| xingtu-article-sync | 文章库发布同步总控：发文后一条命令完成新文章收编→prev/next 与开源仓互链→index.json→三处展示层→Data API 推三仓。幂等。 |
| xiaobot-ops | 小报童平台运营专家：定位/定价/调价/买断制/内容公约/提现官方规范 + 行途双轨定价策略 + 申请专栏表单实战提示 + 运营 checklist。 |

### 工具链 · 工程化实战（18 · 🆕 2026-09-27 第二批 +9）
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
| git-identity-pin | 跨仓 Git 身份钉定：审计/钉定/干跑三模式，把非 skip 仓统一成全局默认提交身份（示例映射，无真实信息） |
| github-repo-gallery | 把 GitHub 仓库清单生成可检索画廊/索引：分类、语言、描述归档，便于复看与分享 |
| hidden-contract-audit | 隐藏契约审计：扫描代码/配置里未声明的行为（隐藏副作用、越权调用），输出红旗清单 |
| ip-platform-fit-audit | IP 平台适配审计：评估内容/项目与发布平台的契合度，给出适配建议 |
| svgtopng-cn-fonts | SVG→PNG 中文渲染：本地 cairosvg 管线 + 中文字体嵌入，零水印矢量转位图 |
| xingtu-oss-guard | 开源矩阵健康度巡检：隐私复扫/未推送/文章闭环/skills 同步/harness 跟进/门面一致性 六维自动化防线 |
| xingtu-role-audit | 角色审计：检查 AI 协作中的角色定义是否与项目实际职责对齐 |
| xingtu-rule-keeper | 规则守护：比对 rules/ 与 skill 引用，发现漂移/断链/过期条目 |
| zcode-session-export | ZCode 会话导出：把本地 AI 会话整理成可归档/可分享的结构化文档 |

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

## 📊 技能体系统筹页（Insights）

- **[docs/index.html](docs/index.html)** — 纵观全仓：三层引擎架构 · 孵化决策树与提示词模板 · 实践感触 · 实践指标（desc 预算/完整度/触发命中率）· 脱敏方法论 · 待办看板
- **[INSIGHTS.md](INSIGHTS.md)** — 统筹页的活文档数据源，随每批技能进仓/回炉滚动追加

## 关联项目

- [xingtu-prompts](https://github.com/xingtu1996/xingtu-prompts) — 提示词库：轻场景复制即用；沉淀成 Skill 后进本仓
- [dsh-xingtu-skills](https://github.com/xingtu1996/dsh-xingtu-skills) — DSH 插件包：本仓技能的 DSH 一键安装版

## 关于作者 · 行途

一线 AI 工程化实践者 · FDE 方向。这些技能不是写出来的，是每天真用、用完回炉改的。

- 公众号「**行途**」（长文首发，微信搜索关注）
- GitHub / X：`@xingtu1996` ｜ 博客：https://xingtu1996.github.io
- 方法论旗舰仓：[xingtu-ai-engineering](https://github.com/xingtu1996/xingtu-ai-engineering)

## 📄 许可证

MIT License

