# AudioTranscTool

## 警告！！！！这个项目现在还处于测试阶段，请使用前先复制一份源文件，在转换后对比一下看看有没有出问题！！

AudioTranscTool诞生的原因十分简单，因为ffmpeg对于音频的32bit音频的转码和flac分割存在问题，所以这个脚本是用python基于各个常用音频格式的codec写的。
mac和linux，部分codec没有发在unix平台下运行的可执行文件，还没想好怎么解决。

### 特点：

1. 不支持推理cue的编码格式，主流的几个库测试下来对于中文编码和多种语言混合的编码格式正确率不高，所以请自己手动转换cue的编码格式为utf-8，只支持utf-8，对于shift-js、gbk、gb2312之类的都不支持！！！
2. 支持apev2 (ape, tak)、id3v2.3&4 (wav, tta)、mp4 (m4a)的元数据映射到vorbis comment (flac)。
3. 支持32bit int wav和32bit in m4a转换到flac。（32bit float wav会被跳过）
4. 支持自动分轨，基于帧的分割，而不是基于时间，更符合CUESHEET的标准（基于文件名检测，当cue的名字和音频的名字相同时就会分割，仅支持flac分割，脚本里会先把所有支持的无损格式音频转换成flac）
5. 未来支持使用Asin、Barcode、Catalognumber和ascoutid+专辑名在musicbrainz搜索对应元数据
6. 未来还会更新别的功能，看我有没有空

### 配置：

在config.toml里可以选择开启哪些功能

```
activate_cue_splitting = true   # 是否开启分轨功能，默认为true
is_delete_single_track = false  # 分轨时是否删除原来的整轨和cue，默认为false
is_delete_origin_audio = false  # 是否删除转码前的音频，默认为false
```

### 使用教程：

首先，确保你的python版本在3.11以上

第二步，下载项目源代码，下载ffmpeg (只需要把ffmpeg里的ffprobe.exe搬到encoders文件夹里就可以了)

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

