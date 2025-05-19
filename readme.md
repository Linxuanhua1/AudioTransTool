# AudioTranscTool

## 警告！！！！这个项目现在还处于测试阶段，请使用前先复制一份源文件，在转换后对比一下看看有没有出问题！！

## MORA的音源会被压缩到flac8

AudioTranscTool诞生的原因十分简单，因为ffmpeg对于音频的32bit音频的转码和flac分割存在问题，所以这个脚本是用python基于各个常用音频格式的codec写的。
mac和linux，部分codec没有发在unix平台下运行的可执行文件，还没想好怎么解决。

### 特点：

1. 不支持推理cue的编码格式，主流的几个库测试下来对于中文编码和多种语言混合的编码格式正确率不高，所以请自己手动转换cue的编码格式为utf-8，只支持utf-8，对于shift-js、gbk、gb2312之类的都不支持！！！
2. 转码支持apev2 (ape, tak)、id3v2.3&4 (wav, tta)、mp4 (m4a)的元数据映射到vorbis comment (flac)。
3. 支持32bit int wav和32bit in m4a转换到flac。（32bit float wav会被跳过）
4. 支持自动分轨，基于帧的分割，而不是基于时间，更符合CUESHEET的标准（基于文件名检测，当cue的名字和音频的名字相同时就会分割，仅支持flac分割，脚本里会先把所有支持的无损格式音频转换成flac）
5. 支持使用Catalognumber在musicbrainz搜索对应元数据
6. 支持转码常见图片格式到jxl，比如webp，png，tiff，jpg，bmp
7. 支持一些简单的元数据批处理
8. 未来还会更新别的功能，看我有没有空

### 配置：

在config.toml里可以选择开启哪些功能

```
activate_cue_splitting = true   # 是否开启分轨功能，默认为true
activate_image_transc = true    # 是否开启照片转码，默认为true，转换所有支持格式到jxl
is_delete_single_track = true   # 分轨时是否删除原来的整轨和cue，默认为true
is_delete_origin_audio = true   # 是否删除转码前的音频，默认为true
is_delete_origin_img = true     # 是否删除转码前的图片，默认为true
max_workers = 8                 # 多进程转码的个数，建议取cpu核心数，多了容易卡
separators = ["/", "&", ", ", "; ", " _ ", " / ", "、"]                   # 分隔符自定义
```

### 使用教程：

首先，确保你的python版本在3.11以上

第二步，下载项目的release，然后解压

第三步，安装项目文件夹下lib里的vcredist_x86.exe

第四步，切换终端目录到代码文件夹，在终端里输入

```
pip install -r requirements.txt
```

第五步

```
python transcode.py
```

接着根据提示，输入需要转码的文件夹路径就可以运行了



meta_handler是一些用来批处理元数据的小工具

包含以下几个功能：

1. 分割音频的艺术家、专辑艺术家和编曲家
2. 删除musictag导致的m4a元数据损坏
3. 字符串去重
4. 从vgm拉取系列数据并创建对应文件夹
5. 根据光盘编号从musicbrainz拉取数据
6. 提取文件夹名重命名文件夹
7. 根据歌曲标签重命名文件夹
8. （未完成）根据文件夹下的.txt和.log的文件名写入音频的光盘编号标签
9. 提取文件夹名中的光盘编号写入音频标签

使用方法：

```
python meta_handler.py
```

然后根据内部的提示输入即可