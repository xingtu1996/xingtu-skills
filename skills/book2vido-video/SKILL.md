---
name: book2vido-video
description: 把 PDF / Markdown / 长文转成竖屏短视频（本地运行、零 API key）。当用户说「把这个 PDF 做成视频」「文本转视频」「做个短视频」「book2vido」「出片」「按第 N 章出片」时使用。驱动本地 book2vido GUI 的 HTTP API，全流程在本机完成。
---

# book2vido · 文本/PDF → 竖屏短视频

本地跑、不花一分钱、不需要任何 API key（配音用 edge-tts 免费接口，画面用 Pillow 现画，合成用 FFmpeg）。

## 何时用

- 用户给一个 PDF / md / txt，想要一条能发的短视频
- 用户说「按第 3 章出片」「把这本书做成视频」
- 用户想批量把长文转视频

## 前置检查（必做，别跳过）

按这个顺序确认，缺哪个就明确告诉用户缺哪个：

| 依赖 | 检查命令 | 缺失时 |
|---|---|---|
| book2vido 仓库 | `--repo` 指向的目录里有 `src/book2vido/` | 让用户给路径 |
| Python 依赖 | 仓库里能 `python -m book2vido.gui --help` | 见仓库 README 的安装步骤 |
| FFmpeg | `which ffmpeg` | `brew install ffmpeg` |
| Ollama（可选） | `curl -s localhost:11434/api/tags` | 不装也能跑，会降级到规则分镜（质量下降，提前说明） |

**环境体检可以直接问服务**：`b2v.py start` 后 `curl http://127.0.0.1:<port>/api/check-env`，它会一次性回报 ffmpeg/ollama 状态。

## 一条龙（最常用）

```bash
python3 ~/.workbuddy/skills/book2vido-video/scripts/b2v.py \
  auto /path/to/书.pdf \
  --repo /path/to/book2vido \
  -o ~/Movies/out.mp4
```

脚本会自动：探测空闲端口启动 GUI → 上传文件 → 发起任务 → 轮询进度 → 下载成片。

只出某一章（PDF 才会分章；md/txt 整篇当一章）：

```bash
... auto 书.pdf --repo /path/to/book2vido --chapter 3 -o ch03.mp4
```

## 分步（需要中间控制时用）

```bash
B2V=~/.workbuddy/skills/book2vido-video/scripts/b2v.py
$B2V start --repo /path/to/book2vido        # 打印 http://127.0.0.1:<port>
$B2V upload  /path/to/书.pdf                # 返回服务端 path
$B2V run   <服务器返回的 path> --chapter 3   # 返回 job_id，自动轮询到 done
$B2V status <job_id>                        # 单独查进度
$B2V fetch  <video_name> -o out.mp4         # 下载成片
$B2V stop                                   # 用完关掉
```

## 服务端 API（脚本封装的就是这几个，需要时可裸调）

| 端点 | 作用 |
|---|---|
| `POST /api/upload` | multipart 上传，存到仓库 `uploads/` |
| `GET /api/outline?path=` | 取章节列表（PDF 才有） |
| `POST /api/run` | body `{path, chapters:[int], voice}`，返回 `job_id` |
| `GET /api/status?job_id=` | 进度/日志/结果 |
| `GET /api/video/<name>` | 成片流 |
| `GET /api/history` | 历史成片（默认目录 `~/Movies/Book2Vido`） |
| `GET /api/check-env` | ffmpeg / ollama 体检 |

## 已知坑

- **端口**：GUI 默认 8765，但本机常被其他服务（如行途工作台）占用，且 `start_server` 的兜底是 `pkill -9 -f book2vido.gui`——占用者是别的进程时它杀不掉，会直接崩。所以**脚本在客户端探测空闲端口后用 `--port` 传入**，不要裸跑 `python -m book2vido.gui`。
- **输入格式**：只支持 PDF 和纯文本/Markdown。**图片输入目前不支持**——`extractor.py` 对非 PDF 一律当文本读，`visualizer.py` 也不接受自定义图片素材。用户要给图片，先告诉他这个限制。
- **首次跑会慢**：ollama 要先拉模型（qwen3:8b 约 5GB）。想快可用规则降级，但口播稿质量明显下降，别默默降级，要说明。
- **历史成片在 `~/Movies/Book2Vido`**，不是仓库里。

## 交付前必做

出片后**自己看一眼**再交给用户：用 `ffprobe` 确认时长/分辨率，或让用户直接打开 mp4。不要只凭「done=true」就说做好了。
