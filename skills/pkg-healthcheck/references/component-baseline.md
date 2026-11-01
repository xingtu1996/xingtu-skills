# 发布包组件清单（pkg-healthcheck 脚本数据源）

> 与工作区发布包组件基线 SSoT（必要 10 项 + 完整包必要 4 项 = 14 项）对齐。格式：每行「路径模式 空格 模式」，模式 glob=必查，cond=条件（有则更好/特定阶段）。
> 修改请两边同步（基线文件为唯一真源，本清单供脚本机械核对）。

00_README.md glob
CHANGELOG.md glob
00_状态.md cond
01_正文/*.md glob
02_排版HTML/*.html glob
03_封面/*.png glob
00_标题摘要/标题摘要.md glob
06_发布参考/开箱操作单.md glob
06_发布参考/置顶评论.md glob
06_发布参考/群推话术.md cond
07_作者素材/ cond
08_发布回流/ cond
04_配图/*.png cond
05_合集判定/ cond
