# MusicBox

> 本项目的前身是 **AudioTranscTool**。经过一轮重构后，转码、媒体整理、远程抓取等能力被拆分成清晰的分层模块，并新增了「自定义任务流」。这是重构后的第一个稳定版。

MusicBox 是一个面向**无损音乐收藏管理**的命令行工具：把各种无损/有损音频规整为 FLAC / WavPack，把图片规整为 JPEG XL，按 cue 精确分轨，并提供一组围绕「文件夹 / 标签 / 封面」的批处理整理功能，还能从 VGMdb 拉取专辑信息自动建立文件夹结构。

之所以用 Python 基于各音频格式的 codec 自己实现，而不是直接调 ffmpeg，是因为 ffmpeg 对 32bit 音频的转码、以及基于 cue 的精确分割存在问题。MusicBox 直接调用各格式的命令行编解码器，并以**帧**为单位切分，更贴合 CUESHEET 标准。

> **仅支持 Windows**。代码使用了 Windows 扩展长路径（`\\?\`）、`cls` 清屏，且依赖的编解码器为 Windows x86 可执行文件。

---

## 功能特点

程序启动后是一个三级主菜单：`transcode` / `media_ops` / `Custom Task Process`。

### 1. transcode（转码）

| 子功能 | 说明 |
| --- | --- |
| **audio transcode** | 自动识别音源并选择目标格式。APE、TAK、TTA、ALAC(m4a)、WAV、AIFF、整数 WavPack → **FLAC**（`--best` 最高压缩）；32bit float 的 WAV / AIFF、DSD（dsf / dff）、浮点/DSD WavPack → **WavPack**（无损封装，可选开关）。会先批量 probe 元数据，由 `FormatChecker` 判断是否需要转换及目标格式，转码完成后迁移元数据。 |
| **split cue** | 基于 cue 的整轨分割。先把可直接解码的无损格式解码为 PCM，再**按帧切分**（`sample_rate // 75`，符合 CD frame，而非按时间），逐轨输出 FLAC 并写入 cuesheet 元数据。检测逻辑：当某无损整轨存在同名 `.cue` 时即分轨。 |
| **image transcode** | webp / png / tiff / jpg / bmp → **JPEG XL**（`cjxl -q 100` 无损；JPEG 用 `-j 1` 无损封装），并迁移元数据。另支持把指定文件名（默认 `Cover`）的图片统一转换/重命名为 `png`。 |

线程策略：音频处理瓶颈在硬盘，`is_hdd = true` 时使用单线程，否则用物理核心数；图片压缩瓶颈在 CPU，始终用物理核心数。

> 转码相关补充：
> - MORA 等「未压缩的 FLAC」会在开启 `is_en_flac0_compress` 后被重新压缩为高压缩 FLAC。
> - 32bit float 浮点音频、DSD 默认跳过，需分别开启 `is_en_flt_compress` / `is_en_dsd_compress`。
> - DST 压缩的 DFF 无法直接转换，会被跳过并提示手动处理。

### 2. media_ops（媒体整理）

| 子功能 | 说明 |
| --- | --- |
| **根据音频标签重命名文件夹** | 读取标签并扫描文件夹（音质、来源、内容后缀、log 评分），按 `config.toml` 里的 Jinja2 模板生成文件夹名。来源判定由 `[rename.match_rules]` 的有序规则驱动；目录下存在 `.log` 时调用 `cambia` 解析 EAC / XLD 抓轨评分。 |
| **提取文件夹名重命名文件夹** | 用正则从现有文件夹名提取字段，再套用输出模板。*（未压力测试）* |
| **提取内嵌图片并删除内嵌图片** | 提取音频内嵌封面到同目录（按内容去重，保存为 `Cover.png` / `Cover(n).png`），并清除音频内的内嵌图片。 |
| **分割音频的自定义字段** | 按配置的分隔符把 `ARTIST` / `ALBUMARTIST` / `COMPOSER` 等**单值**字段拆分为多值。*（未压力测试）* |
| **从 VGMdb 拉取数据并创建对应文件夹** | 输入 product URL，自动识别 product（具体作品）/ franchise（系列）页面，按模板批量创建专辑 / 作品文件夹。franchise 支持 `flat`、`grouped` 两种归组模式。**需要在 config 填入 VGMdb 登录 cookie。** |

> 「根据光盘编号从 MusicBrainz 拉取数据」目前还未完成。

### 3. Custom Task Process（自定义任务流）

在**同一个文件夹**上，按 `config.toml` 里 `[custom_task].task_pipeline` 定义的顺序依次执行多个任务，可混合转码与整理两类任务（列入即执行）：

- transcode 任务：`audio_transcode`、`split_cue`、`image_transcode`
- organizer 任务：`rename_from_tag`、`rename_from_name`、`extract_and_remove`、`separate_tag`

当 pipeline 同时包含 `audio_transcode` 与 `split_cue` 时，带同名 cue 且可直接分轨的整轨会自动跳过转码，交给分轨步骤处理，避免重复解码。

---

## 安装与使用

### 1. 准备运行环境

- **Python 3.11 及以上**（用到标准库 `tomllib`；开发环境为 3.13）。
- **仅限 Windows。**

### 2. 下载并解压 release

release 内含 `bin/` 目录，已打包好所需的命令行编解码器与 libvips（`bin/vips-dev-8.18/`）。启动时程序会自动把 `bin/` 与 `bin/vips-dev-8.18/bin` 加入 `PATH`，无需手动配置环境变量。

`bin/` 中包含的外部工具（如自行准备需保证可在命令行调用）：

| 用途 | 可执行文件 |
| --- | --- |
| FLAC 编解码 | `flac` |
| WavPack 编码 / 解码 / 探测 | `wavpack` / `wvunpack` |
| Monkey's Audio (APE) 解码 | `MAC` |
| TAK 解码 | `Takc` |
| TTA 解码 | `ttaenc` |
| ALAC (m4a) 解码 | `refalac` |
| JPEG XL 编码 | `cjxl` |
| 元数据探测 / 迁移 | `exiftool` |
| EAC / XLD 抓轨日志解析 | `cambia` |
| 图片解码后端 | `libvips`（`vips-dev-8.18`） |

### 3. 安装 vcredist_x86.exe

安装项目 `lib` 目录下的 **`vcredist_x86.exe`**（x86 编解码器与 libvips 运行所需的 Visual C++ 运行库）。

### 4. 安装 Python 依赖

切换终端目录到代码文件夹，执行：

```bash
pip install .
```

主要依赖：`mutagen`、`pyvips`、`tqdm`、`psutil`、`jinja2`、`tomlkit`、`beautifulsoup4`、`requests`、`chardet`、`musicbrainzngs`。

### 5. 运行

```bash
python musicbox.py
```

按菜单提示输入数字选择功能、输入文件夹路径即可。各级菜单输入 `#` 返回上一级 / 主菜单。

---

## 配置

首次运行会自动生成一份**带完整注释**的 `config.toml`（默认所有开关均为 `false`）。之后若新版本新增了配置项，启动时会自动把缺失的键补上默认值并写回，且保留你已有的修改与注释。

配置分为四个区块，下面只列出常用项，完整注释见生成的 `config.toml` 本身：

### `[transcode]` — 转码

```toml
is_del_single_trk   = false   # 分轨后是否删除原整轨
is_del_cue          = false   # 是否删除 cue 文件
is_del_src_audio    = false   # 是否删除转码前的源音频
is_en_flac0_compress = false  # 是否压缩未压缩的 FLAC（如 MORA 音源）
is_en_flt_compress  = false   # 是否压缩浮点音频（常见于部分 ASMR / e-onkyo）
is_en_dsd_compress  = false   # 是否压缩 DSD
is_del_src_img      = false   # 是否删除转码前的图片
is_hdd              = true    # 存储介质是否为 HDD；HDD 单线程，SSD 用物理核心数
img_to_png_names    = ["Cover"]  # 这些文件名（不区分大小写）的图片统一转/改名为 png
```

> ⚠️ 开启任意 `is_del_*` 开关会**删除原文件**，请确认无误后再启用。

### `[custom_task]` — 自定义任务流

```toml
task_pipeline = ["audio_transcode", "split_cue", "image_transcode"]
```

### `[vgm]` — VGMdb 抓取

```toml
franchise_mode = "grouped"   # flat / grouped 两种系列归组模式
fetch_threads  = 4
cookie         = ""          # 从浏览器复制整段 VGMdb Cookie，必填
product_fld_tpl = "[{date}] {product_name}"
album_fld_tpl   = "[{date}][{catno}][{album}][{media_format}]"
```

### `[rename]` — 重命名

包含元数据切分分隔符 `seps`、要切分的字段 `sep_fields`、文件夹名提取正则、输出命名模板 `output_template`（Jinja2，支持 `{% if VAR %}` 可选字段），以及来源匹配规则数组表 `[[rename.match_rules]]`（有序匹配，命中即用，全未命中走 `source_fallback`）。可用字段、可切分字段、规则字段含义在 `config.toml` 内均有详细注释。

---

## 注意事项

- 虽然已是稳定版，但在批量开启删除类开关前，建议先用少量样本测试、对比一下结果再大规模处理。
- 如果某个文件一直转码失败，常见原因是标签里写入了**非法字符或中文字段名**，导致解析失败，可尝试用mp3tag删除元数据后再尝试。
- 转码 / 分轨过程中按 Ctrl+C 中断时，程序会清理未完成的输出文件。

---

更详细的模块结构与运行流程见 [`architecture.md`](./architecture.md)。
