# AudioTranscTool

AudioTranscTool诞生的原因十分简单，因为ffmpeg对于音频的32bit音频的转码存在问题，所以这个脚本是用python基于各个常用音频格式的codec写的，暂时只写了windows端和无损的音频格式转换。

## 特点：

1. 支持apev2 (ape, tak)、id3v2.3&4 (wav, tta)、mp4 (m4a)的元数据映射到vorbis comment (flac)。
2. 支持32bit int wav和32bit in m4a转换到flac。（32bit float wav会被跳过，因为flac不支持）
3. 支持自动分轨（基于文件名检测，当cue的名字和音频的名字相同时就会分割，仅支持flac分割，脚本里会先把所有支持的无损格式音频转换成flac）
4. 未来支持使用Asin、Barcode、Catalognumber和ascoutid+专辑名在musicbrainz搜索对应元数据
5. 未来还会更新别的功能，看我有没有空

## 使用教程：

首先，确保你的python版本在3.11以上

第二步，下载项目源代码，下载ffmpeg (只需要把ffmpeg里的ffprobe.exe搬到encoders文件夹里就可以了)

第三步，安装项目文件夹里的vcredist_x86.exe

第四步，切换终端目录到代码文件夹，在终端里输入

```
pip install -r requirements.txt
```

第五步

```
python main.py
```

接着根据提示，输入需要转码的文件夹路径就可以运行了

