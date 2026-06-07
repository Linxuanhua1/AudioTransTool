# MusicBox 项目架构

本文档基于当前代码生成，描述 MusicBox 重构后的分层结构与主要运行流程。所有流程图使用 [Mermaid](https://mermaid.js.org/)，可直接在 GitHub / 支持 Mermaid 的 Markdown 阅读器中渲染。

## 设计概览

整体采用**分层 + 注册表**的结构，依赖方向自上而下：

```
入口层  →  应用层  →  服务层  →  标签层 / 工具层  →  外部命令行工具 + Python 库
```

- 转码与整理通过 `tags.registry`（类型 → Reader/Writer 映射）与 `tags.transfer` 复用一套统一的「内部标签」抽象。
- 转码任务、音频/图片处理器、标签 Reader/Writer 都通过**注册表（扩展名 / 类型 → 类）**做分发，新增格式只需登记映射，不改调度逻辑。

## 目录结构

```
musicbox.py                     入口，组装 MusicBoxApp 三个子 App
config.toml                     运行配置（首次运行自动生成）
lib/
├── apps/                       应用层：三个交互式子 App
│   ├── transcode_app.py        转码菜单
│   ├── organizer_app.py        媒体整理菜单
│   └── custom_task_app.py      自定义任务流
├── services/
│   ├── constants/              纯常量（格式、CLI 指令、扫描/重命名/VGM 等）
│   ├── transcode/              转码服务
│   │   ├── transcode_task.py   任务基类（线程策略 / 批量 probe / 并发）
│   │   ├── audio_transcode.py / audio_split.py / image_transcode.py
│   │   ├── registry.py         扩展名 → Handler
│   │   ├── format_checker.py   是否转换 + 目标格式判定
│   │   ├── audio/              各音频格式 Handler + Splitter
│   │   └── image/              各图片格式 Handler
│   └── media_ops/              媒体整理服务
│       ├── folder_naming/      文件夹重命名（FolderRenamer / FieldExtractor / 校验）
│       │   └── folder_scanner/ 文件夹扫描（音质 / 来源 / 内容后缀 / 匹配规则）
│       ├── remote_fetcher/     远程抓取
│       │   └── metadb/vgm/     VGMdb 抓取（fetcher / handler / parser / data_type）
│       ├── tag_separator.py    字段切分
│       ├── image_extractor.py  内嵌图片提取 / 移除
│       ├── catno_helper.py     光盘编号折叠 / 展开
│       └── folder_utils.py     专辑目录收集
├── tags/                       标签抽象层
│   ├── base.py                 MetaReader / MetaWriter / InternalTags
│   ├── registry.py             mutagen 类型 → Reader/Writer
│   ├── transfer.py             TagsTransfer 跨格式元数据迁移
│   ├── tag_mappings.py         各格式字段映射表
│   └── id3.py / vorbis.py / mp4.py / apev2.py / asf.py
└── utils/                      工具层
    ├── generate_config.py      生成 / 补全配置
    ├── log.py                  日志（控制台 + 滚动文件）
    ├── media_probe.py          MediaProbe（exiftool / wvunpack 批量探测）
    ├── path_manager.py         路径管理（扩展长路径 / 防重名 / 安全文件名）
    └── clear_screen.py
```

> **重构遗留提示**：`lib/services/media_ops/` 下的 `folder_renamer/` 与 `folder_scanner/` 两个目录是重构前的旧结构，已不被任何 `__init__` 或外部模块导入（仅自身互相引用）。当前实际生效的是 `folder_naming/`（内含 `folder_scanner/`）。这两个旧目录可以安全删除。

---

## 1. 分层架构图

```mermaid
flowchart TD
    subgraph ENTRY["入口层"]
        MB["musicbox.py · MusicBoxApp"]
    end

    subgraph APPS["应用层 lib/apps"]
        TA["TranscodeApp"]
        OA["OrganizerApp"]
        CTA["CustomTaskApp"]
    end

    subgraph SVC["服务层 lib/services"]
        subgraph TR["transcode"]
            TT["TranscodeTask 基类"]
            ATX["AudioTranscode"]
            ASX["AudioSplit"]
            ITX["ImageTranscode"]
            REG["registry 扩展名→Handler"]
            FC["format_checker"]
            AH["audio: handlers + Splitter"]
            IH["image: handlers"]
        end
        subgraph MO["media_ops"]
            FR["FolderRenamer"]
            FS["FolderScanner + audio_info + match_rules"]
            FE["FieldExtractor / PatternValidator"]
            TS["TagSeparator"]
            IE["ImageExtractor"]
            RF["RemoteFetcher → VGM"]
            CN["CatNoHelper"]
            FU["FolderUtils"]
        end
        CONST["constants 纯常量"]
    end

    subgraph TAGS["标签层 lib/tags"]
        TTRANS["transfer: TagsTransfer"]
        TREG["registry: 类型→Reader/Writer"]
        TFMT["id3 / vorbis / mp4 / apev2 / asf"]
        TMAP["tag_mappings"]
    end

    subgraph UTILS["工具层 lib/utils"]
        GC["generate_config / ensure_config"]
        MP["MediaProbe"]
        PM["PathManager"]
        LOG["log"]
    end

    subgraph EXT["外部依赖"]
        CLI["命令行工具<br/>flac / wavpack / MAC / Takc / ttaenc<br/>refalac / cjxl / exiftool / cambia"]
        PYLIB["Python 库<br/>mutagen / pyvips / jinja2 / bs4<br/>requests / tqdm / psutil / tomlkit"]
    end

    MB --> TA & OA & CTA
    TA --> TT
    CTA --> TT
    CTA --> FR & IE & TS
    OA --> FR & TS & IE & RF
    TT --> ATX & ASX & ITX
    ATX --> REG & FC & AH
    ASX --> AH
    ITX --> REG & FC & IH
    FR --> FS & FE & FU & CN
    AH --> TTRANS
    TTRANS --> TREG
    TREG --> TFMT
    TFMT --> TMAP
    ATX --> MP
    FS --> MP
    AH --> CLI
    ASX --> CLI
    IH --> CLI
    MP --> CLI
    TFMT --> PYLIB
    RF --> PYLIB
    MB --> GC
    PM -.被各层调用.-> SVC
```

---

## 2. 启动与主菜单流程

```mermaid
flowchart TD
    START(["启动 musicbox.py"]) --> CFG["ensure_config<br/>无文件则生成 / 缺键则补默认"]
    CFG --> INIT["创建 MusicBoxApp<br/>实例化三个子 App"]
    INIT --> MENU{"主菜单<br/>1 / 2 / 3 / #"}
    MENU -->|1| M1["TranscodeApp.run"]
    MENU -->|2| M2["OrganizerApp.run"]
    MENU -->|3| M3["CustomTaskApp.run"]
    MENU -->|#| QUIT(["退出"])

    M1 --> S1{"选择子功能"}
    S1 -->|audio transcode| ATX["AudioTranscode.process"]
    S1 -->|split cue| ASX["AudioSplit.process"]
    S1 -->|image transcode| ITX["ImageTranscode.process"]

    M2 --> S2{"选择操作"}
    S2 -->|rename_from_tag| R1["按音频标签重命名"]
    S2 -->|rename_from_name| R2["按文件夹名重命名"]
    S2 -->|extract_and_remove| R3["提取并移除内嵌图片"]
    S2 -->|separate_tag| R4["切分自定义字段"]
    S2 -->|vgm| R5["VGMdb 抓取并建文件夹"]

    M3 --> P1["读取 task_pipeline"]
    P1 --> P2["在同一文件夹按序执行各任务"]

    ATX --> MENU
    ASX --> MENU
    ITX --> MENU
    R1 --> MENU
    R5 --> MENU
    P2 --> MENU
```

---

## 3. 转码流程（TranscodeTask 通用流水线，以音频为例）

```mermaid
flowchart TD
    A["task.process 处理目标文件夹"] --> B["collect_tasks: rglob 收集匹配扩展名的文件"]
    B --> C["跳过空文件与不支持的扩展名"]
    C --> D["MediaProbe 批量探测元数据<br/>exiftool 批量 + wvunpack 逐个"]
    D --> E{"format_checker 判断目标格式"}
    E -->|UNSUPPORTED| SKIP["跳过该文件"]
    E -->|FLAC / WAVEPACK| F["按扩展名创建对应 Handler"]
    F --> G["ThreadPoolExecutor 并发执行<br/>线程数: HDD=1 / SSD=物理核心数"]
    G --> H["Handler.compress_audio"]
    H --> I["解码为 PCM / WAV 字节<br/>调用对应 CLI 解码器"]
    I --> J["重新编码为 FLAC 或 WavPack"]
    J --> K["TagsTransfer 迁移元数据"]
    K --> L{"is_del_src_audio?"}
    L -->|是| M["删除源文件，必要时把输出改回原名"]
    L -->|否| N["保留源文件"]
    M --> DONE["完成"]
    N --> DONE
    H -->|失败或中断| ERR["清理不完整输出并记录日志"]
```

> 图片转码（`ImageTranscode`）复用同一套基类流水线，差异在于：`format_checker` 判断的是「是否可转 JXL」，Handler 通过 `cjxl` 编码，元数据用 `exiftool` 迁移，且线程数恒为物理核心数（瓶颈在 CPU）。
> 分轨（`AudioSplit`）也走同一基类，但只收集「存在同名 cue 且可直接分轨」的整轨，最终调用 `Splitter.split_with_cue` 按帧切分。

---

## 4. 按音频标签重命名（rename_from_tag）流程

```mermaid
flowchart TD
    A["rename_from_tag"] --> B["FolderUtils.collect_album_dirs<br/>收集含音频的专辑目录，识别碟片子目录"]
    B --> C["遍历每个专辑目录"]
    C --> D["FieldExtractor.extract_from_audio_tags<br/>读 DATE / ALBUM / CATALOGNUMBER 等并规整"]
    D --> E{"有有效 DATE 和 ALBUM?"}
    E -->|否| SKIP["跳过该目录"]
    E -->|是| F["FolderScanner.analyze<br/>仅计算输出模板引用到的字段"]
    F --> F1["QUALITY: 批量 probe 计算音质"]
    F --> F2["FOLDER_CONTENT: 拼接内容后缀"]
    F --> F3["SOURCE / SCORE: match_rules 规则或 cambia 解析 log"]
    F1 & F2 & F3 --> G["合并字段后渲染 Jinja2 输出模板"]
    G --> H["safe_filename 生成新文件夹名"]
    H --> I["加入待重命名列表"]
    I --> J["批量执行并询问是否撤回"]
```

---

## 5. VGMdb 抓取流程

```mermaid
flowchart TD
    A["fetch_vgm_and_create_folder"] --> B["输入 product URL，输入 # 返回"]
    B --> C{"URL 合法?"}
    C -->|否| B
    C -->|是| D["VgmHttpClient.get 拉取页面<br/>内置限速与指数退避重试"]
    D --> E{"VgmParser.is_franchise?"}
    E -->|否 · 单作品| F["ProductHandler.process"]
    F --> F1["解析专辑 stubs 列表"]
    F1 --> F2["AlbumBatchProcessor 多线程抓取各专辑"]
    F2 --> F3["按 album_fld_tpl 创建专辑文件夹"]
    E -->|是 · 系列页| G{"franchise_mode"}
    G -->|flat| H["FranchiseFlatHandler<br/>页面所有专辑直接建文件夹"]
    G -->|grouped| I["FranchiseGroupedHandler<br/>先抓子作品再按归属归组"]
    I --> I1["重复专辑归入 Compilation 文件夹"]
```

---

## 6. 标签迁移（TagsTransfer）流程

转码时源/目标文件常常是不同容器格式，元数据迁移统一收敛到 `TagsTransfer`：

```mermaid
flowchart TD
    A["TagsTransfer.transfer_meta 源 → 目标"] --> B["mutagen 识别源与目标文件类型"]
    B --> C{"源是 DSDIFF / dff?"}
    C -->|是| SKIP["无标签可转，跳过"]
    C -->|否| D["registry 查 Reader / Writer"]
    D --> E{"源与目标同标签格式?"}
    E -->|是 · 同组直通| F["Reader.copy_to 直接复制"]
    E -->|否| G["Reader.read 转为 InternalTags 标准化标签"]
    G --> H["Writer.write 写入目标文件"]
```

`InternalTags` 是一套与具体容器无关的「字段名 → 值集合」表示。各格式的 Reader 负责把原生标签读成 `InternalTags`，Writer 负责写回，从而实现 ID3 / Vorbis / MP4 / APEv2 之间的跨格式迁移；同格式之间则走 `copy_to` 直通以避免无谓转换。
