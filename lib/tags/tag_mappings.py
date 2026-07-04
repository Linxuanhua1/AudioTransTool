from mutagen.id3 import (
    TALB, TBPM, TCOM, TCON, TCOP, TCMP, TDEN, TDES, TKWD, TCAT,
    MVNM, MVIN, GRP1, TDOR, TDLY, TDRC, TDRL, TDTG, TENC, TEXT, TFLT,
    TGID, TIT1, TIT2, TIT3, TKEY, TLAN, TLEN, TMED, TMOO, TOAL, TOFN,
    TOLY, TOPE, TOWN, TPE1, TPE2, TPE3, TPE4, TPRO, TPUB,
    TRSN, TRSO, TSO2, TSOA, TSOC, TSOP, TSOT, TSRC, TSSE, TSST,
    WCOM, WCOP, WFED, WOAF, WOAR, WOAS, WORS, WPAY, WPUB,
    TIPL, TMCL, IPLS, TORY,
)
from mutagen.mp3 import MP3
from mutagen.trueaudio import TrueAudio
from mutagen.wave import WAVE
from mutagen.aiff import AIFF
from mutagen.dsf import DSF
from mutagen.flac import FLAC
from mutagen.ogg import OggFileType
from mutagen.oggvorbis import OggVorbis
from mutagen.aac import AAC
from mutagen.monkeysaudio import MonkeysAudio
from mutagen.wavpack import WavPack
from mutagen.tak import TAK
from mutagen.mp4 import MP4
from mutagen.asf import ASF

from lib.tags import ImageType


# ============================================================================
# Mutagen 文件类型分组
# ============================================================================

ID3_TYPES = (MP3, TrueAudio, WAVE, AIFF, DSF)
VORBIS_TYPES = (FLAC, OggFileType, OggVorbis)
MP4_TYPES = (AAC, MP4)
APEV2_TYPES = (MonkeysAudio, WavPack, TAK)
ASF_TYPES = ASF


# ============================================================================
# ID3 相关映射
# ============================================================================

# ID3 不支持的帧
ID3_NOT_SUPPORTED = [
    'AENC', 'ASPI', 'COMR', 'ENCR', 'EQU2', "ETCO", "GEOB",
    'GRID', 'LINK', "MCDI", 'MLLT', "OWNE", "PRIV", 'PCNT',
    "POPM", 'POSS', 'RBUF', "RVA2", 'RVRB', 'SEEK', 'SIGN',
    'SYTC', "ATXT", 'CHAP', 'CTOC', 'USER', 'RVAD'
]

ID3_TXXX_MUSICBRAINZ_DESC_TO_VORBIS = {
    "MUSICBRAINZ ALBUM RELEASE COUNTRY": "RELEASECOUNTRY",
    "MUSICBRAINZ ALBUM STATUS": "RELEASESTATUS",
    "MUSICBRAINZ ALBUM TYPE": "RELEASETYPE",
}

VORBIS_TO_ID3_TXXX_MUSICBRAINZ_DESC = {
    "RELEASECOUNTRY": "MUSICBRAINZ ALBUM RELEASE COUNTRY",
    "RELEASESTATUS": "MUSICBRAINZ ALBUM STATUS",
    "RELEASETYPE": "MUSICBRAINZ ALBUM TYPE",
}

# ID3V2.3里TYER是年份，TDAT是几月几日，TRDA才是写完整日期的
ID3_TO_STANDARD = {
    'TALB': 'ALBUM',
    'TBPM': 'BPM',
    'TCOM': 'COMPOSER',
    'TCON': 'GENRE',
    'TCOP': 'COPYRIGHT',
    'TCMP': 'COMPILATION',
    'TDAT': 'DATE',
    'TDEN': 'ENCODINGTIME',
    'TDES': 'PODCASTDESC',
    'TKWD': 'PODCASTKEYWORDS',
    'TCAT': 'PODCASTCATEGORY',
    'MVNM': 'ITUNESMOVEMENTNAME',
    "MVIN": "ITUNESMOVEMENTNUMBER",
    'GRP1': 'GROUPING',
    'TDOR': 'ORIGINALDATE',
    "TDLY": "AUDIODELAY",
    'TDRC': 'DATE',
    'TDRL': 'RELEASETIME',
    'TDTG': 'TAGGINGTIME',
    'TENC': 'ENCODEDBY',
    'TEXT': 'LYRICIST',
    'TFLT': 'FILETYPE',
    'TGID': 'PODCASTID',
    "TIME": "RECORDINGTIME",
    'TIT1': 'CONTENTGROUP',
    'TIT2': 'TITLE',
    'TIT3': 'SUBTITLE',
    'TKEY': 'INITIALKEY',
    'TLAN': 'LANGUAGE',
    'TLEN': 'LENGTH',
    'TMED': 'MEDIATYPE',
    'TMOO': 'MOOD',
    'TOAL': 'ORIGINALALBUM',
    'TOFN': 'ORIGINALFILENAME',
    'TOLY': 'ORIGLYRICIST',
    'TOPE': 'ORIGARTIST',
    "TORY": "ORIGINALDATE",
    'TOWN': 'FILEOWNER',
    'TPE1': 'ARTIST',
    'TPE2': 'ALBUMARTIST',
    'TPE3': 'CONDUCTOR',
    'TPE4': 'MIXARTIST',
    'TPOS': ('DISCNUMBER', "TOTALDISCS"),
    "TPRO": "PRODUCEDNOTICE",
    'TPUB': 'PUBLISHER',
    'TRCK': ('TRACKNUMBER', "TOTALTRACKS"),
    "TRDA": "DATE",
    'TRSN': 'NETRADIOSTATION',
    'TRSO': 'NETRADIOOWNER',
    'TSO2': 'ALBUMARTISTSORT',
    'TSOA': 'ALBUMSORT',
    'TSOC': 'COMPOSERSORT',
    'TSOP': 'ARTISTSORT',
    'TSOT': 'TITLESORT',
    'TSRC': 'ISRC',
    'TSSE': 'ENCODERSETTINGS',
    'TSST': 'SETSUBTITLE',
    'TYER': 'DATE',
    'WCOM': 'WWWCOMMERCIALINFO',
    'WCOP': 'WWWCOPYRIGHT',
    'WFED': 'PODCASTURL',
    'WOAF': 'WWWAUDIOFILE',
    'WOAR': 'WWWARTIST',
    'WOAS': 'WWWAUDIOSOURCE',
    'WORS': 'WWWRADIOPAGE',
    'WPAY': 'WWWPAYMENT',
    'WPUB': 'WWWPUBLISHER',
    'TIPL': 'INVOLVEDPEOPLE',
    'TMCL': 'MUSICIANCREDITS',
    'IPLS': 'INITIALKEY',
    'USLT': 'LYRICS',
    'SYLT': 'LYRICS',
    'PCST': 'PODCAST',
    "UFID:http://musicbrainz.org": 'MUSICBRAINZ_TRACKID'
}

STANDARD_TO_ID3: dict[str, str] = {
    'ALBUM': 'TALB',
    'ALBUMARTIST': 'TPE2',
    'ALBUMARTISTSORT': 'TSO2',
    'ALBUMSORT': 'TSOA',
    'ARTIST': 'TPE1',
    'ARTISTSORT': 'TSOP',
    'AUDIODELAY': 'TDLY',
    'BPM': 'TBPM',
    'COMPILATION': 'TCMP',
    'COMPOSER': 'TCOM',
    'COMPOSERSORT': 'TSOC',
    'CONDUCTOR': 'TPE3',
    'CONTENTGROUP': 'TIT1',
    'COPYRIGHT': 'TCOP',
    'DATE': 'TDRC',
    'ENCODEDBY': 'TENC',
    'ENCODERSETTINGS': 'TSSE',
    'ENCODINGTIME': 'TDEN',
    'FILEOWNER': 'TOWN',
    'FILETYPE': 'TFLT',
    'GENRE': 'TCON',
    'GROUPING': 'GRP1',
    'INITIALKEY': 'IPLS',
    'INVOLVEDPEOPLE': 'TIPL',
    'ISRC': 'TSRC',
    'ITUNESMOVEMENTNAME': 'MVNM',
    'ITUNESMOVEMENTNUMBER': 'MVIN',
    'LANGUAGE': 'TLAN',
    'LENGTH': 'TLEN',
    'LYRICIST': 'TEXT',
    'LYRICS': 'SYLT',
    'MEDIATYPE': 'TMED',
    'MIXARTIST': 'TPE4',
    'MOOD': 'TMOO',
    'MUSICBRAINZ_TRACKID': 'UFID:http://musicbrainz.org',
    'MUSICIANCREDITS': 'TMCL',
    'NETRADIOOWNER': 'TRSO',
    'NETRADIOSTATION': 'TRSN',
    'ORIGARTIST': 'TOPE',
    'ORIGINALALBUM': 'TOAL',
    'ORIGINALDATE': 'TORY',
    'ORIGINALFILENAME': 'TOFN',
    'ORIGLYRICIST': 'TOLY',
    'PODCAST': 'PCST',
    'PODCASTCATEGORY': 'TCAT',
    'PODCASTDESC': 'TDES',
    'PODCASTID': 'TGID',
    'PODCASTKEYWORDS': 'TKWD',
    'PODCASTURL': 'WFED',
    'PRODUCEDNOTICE': 'TPRO',
    'PUBLISHER': 'TPUB',
    'RECORDINGTIME': 'TIME',
    'RELEASETIME': 'TDRL',
    'SETSUBTITLE': 'TSST',
    'SUBTITLE': 'TIT3',
    'TAGGINGTIME': 'TDTG',
    'TITLE': 'TIT2',
    'TITLESORT': 'TSOT',
    'WWWARTIST': 'WOAR',
    'WWWAUDIOFILE': 'WOAF',
    'WWWAUDIOSOURCE': 'WOAS',
    'WWWCOMMERCIALINFO': 'WCOM',
    'WWWCOPYRIGHT': 'WCOP',
    'WWWPAYMENT': 'WPAY',
    'WWWPUBLISHER': 'WPUB',
    'WWWRADIOPAGE': 'WORS'
}

ID3_TUPLE_REVERSE: dict[str, tuple[str, int]] = {
    'DISCNUMBER': ('disk', 0),
    'TOTALDISCS': ('disk', 1),
    'TOTALTRACKS': ('trkn', 1),
    'TRACKNUMBER': ('trkn', 0)
}

ID3_FRAME_CLASSES: dict[str, type] = {
    'TALB': TALB, 'TBPM': TBPM, 'TCOM': TCOM, 'TCON': TCON, 'TCOP': TCOP,
    'TCMP': TCMP, 'TDEN': TDEN, 'TDES': TDES, 'TKWD': TKWD, "TORY": TORY,
    'TCAT': TCAT, 'MVNM': MVNM, 'MVIN': MVIN, 'GRP1': GRP1, 'TDOR': TDOR,
    'TDLY': TDLY, 'TDRC': TDRC, 'TDRL': TDRL, 'TDTG': TDTG, 'TENC': TENC,
    'TEXT': TEXT, 'TFLT': TFLT, 'TGID': TGID, 'TIT1': TIT1, 'TIT2': TIT2,
    'TIT3': TIT3, 'TKEY': TKEY, 'TLAN': TLAN, 'TLEN': TLEN, 'TMED': TMED,
    'TMOO': TMOO, 'TOAL': TOAL, 'TOFN': TOFN, 'TOLY': TOLY, 'TOPE': TOPE,
    'TOWN': TOWN, 'TPE1': TPE1, 'TPE2': TPE2, 'TPE3': TPE3, 'TPE4': TPE4,
    'TPRO': TPRO, 'TPUB': TPUB, 'TRSN': TRSN, 'TRSO': TRSO, 'TSO2': TSO2,
    'TSOA': TSOA, 'TSOC': TSOC, 'TSOP': TSOP, 'TSOT': TSOT, 'TSRC': TSRC,
    'TSSE': TSSE, 'TSST': TSST,
    'WCOM': WCOM, 'WCOP': WCOP, 'WFED': WFED, 'WOAF': WOAF, 'WOAR': WOAR,
    'WOAS': WOAS, 'WORS': WORS, 'WPAY': WPAY, 'WPUB': WPUB,
    'TIPL': TIPL, 'TMCL': TMCL, 'IPLS': IPLS,
}


# ============================================================================
# APEv2 相关映射
# ============================================================================

APEV2_TO_STANDARD = {
    "ALBUM ARTIST": "ALBUMARTIST",
    "TRACK": ("TRACKNUMBER", "TOTALTRACKS"),
    "COVER ART (OTHER)": ImageType.Other,
    "COVER ART (ICON)": ImageType.Icon,
    "COVER ART (OTHER ICON)": ImageType.OtherIcon,
    "COVER ART (FRONT)": ImageType.Front,
    "COVER ART (BACK)": ImageType.Back,
    "COVER ART (LEAFLET)": ImageType.Leaflet,
    "COVER ART (MEDIA)": ImageType.Media,
    "COVER ART (LEAD ARTIST)": ImageType.LeadArtist,
    "COVER ART (ARTIST)": ImageType.Artist,
    "COVER ART (CONDUCTOR)": ImageType.Conductor,
    "COVER ART (BAND)": ImageType.Band,
    "COVER ART (COMPOSER)": ImageType.Composer,
    "COVER ART (LYRICIST)": ImageType.Lyricist,
    "COVER ART (RECORDING LOCATION)": ImageType.RecordingLocation,
    "COVER ART (DURING RECORDING)": ImageType.DuringRecording,
    "COVER ART (DURING PERFORMANCE)": ImageType.DuringPerformance,
    "COVER ART (VIDEO CAPTURE)": ImageType.ScreenCapture,
    "COVER ART (FISH)": ImageType.Fish,
    "COVER ART (ILLUSTRATION)": ImageType.Illustration,
    "COVER ART (BAND LOGOTYPE)": ImageType.BandLogo,
    "COVER ART (PUBLISHER LOGOTYPE)": ImageType.PublisherLogo,
    "DISCNUMBER": ("DISCNUMBER", "TOTALDISCS"),
}

STANDARD_TO_APEV2: dict[str, str] = {
    'ALBUMARTIST': 'Album Artist',
    'TRACKNUMBER': 'TRACK'
}

APEV2_TUPLE_REVERSE: dict[str, tuple[str, int]] = {
    'DISCNUMBER': ('DISCNUMBER', 0),
    'TOTALDISCS': ('DISCNUMBER', 1),
    'TOTALTRACKS': ('TRACK', 1),
    'TRACKNUMBER': ('TRACK', 0)
}

IMAGE_TYPE_TO_APE: dict[ImageType, str] = {
    ImageType.Leaflet: 'Cover Art (Leaflet)',
    ImageType.DuringRecording: 'Cover Art (During Recording)',
    ImageType.DuringPerformance: 'Cover Art (During Performance)',
    ImageType.ScreenCapture: 'Cover Art (Video Capture)',
    ImageType.Band: 'Cover Art (Band)',
    ImageType.Composer: 'Cover Art (Composer)',
    ImageType.Front: 'Cover Art (Front)',
    ImageType.Back: 'Cover Art (Back)',
    ImageType.Media: 'Cover Art (Media)',
    ImageType.LeadArtist: 'Cover Art (Lead Artist)',
    ImageType.Fish: 'Cover Art (Fish)',
    ImageType.Illustration: 'Cover Art (Illustration)',
    ImageType.RecordingLocation: 'Cover Art (Recording Location)',
    ImageType.Lyricist: 'Cover Art (Lyricist)',
    ImageType.Artist: 'Cover Art (Artist)',
    ImageType.Conductor: 'Cover Art (Conductor)',
    ImageType.BandLogo: 'Cover Art (Band Logotype)',
    ImageType.PublisherLogo: 'Cover Art (Publisher Logotype)',
    ImageType.Other: 'Cover Art (Other)',
    ImageType.Icon: 'Cover Art (Icon)',
    ImageType.OtherIcon: 'Cover Art (Other Icon)'
}


# ============================================================================
# MP4 相关映射
# ============================================================================

MP4_TO_STANDARD = {
    '©alb': 'ALBUM',
    'aART': 'ALBUMARTIST',
    'soaa': 'ALBUMARTISTSORT',
    'soal': 'ALBUMSORT',
    '©ART': 'ARTIST',
    'soar': 'ARTISTSORT',
    'tmpo': 'BPM',
    '©cmt': 'COMMENT',
    'cpil': 'COMPILATION',
    '©wrt': 'COMPOSER',
    'soco': 'COMPOSERSORT',
    'cprt': 'COPYRIGHT',
    '©prt': 'COPYRIGHT',
    'desc': 'DESCRIPTION',
    '©dir': 'DIRECTOR',
    'disk': ('DISCNUMBER', 'TOTALDISCS'),
    '©too': 'ENCODEDBY',
    '©gen': 'GENRE',
    '©grp': 'GROUPING',
    'apID': 'ITUNESACCOUNT',
    'rtng': 'ITUNESADVISORY',
    'plID': 'ITUNESALBUMID',
    'atID': 'ITUNESARTISTID',
    'cnID': 'ITUNESCATALOGID',
    'cmID': 'ITUNESCOMPOSERID',
    'sfID': 'ITUNESCOUNTRYID',
    'pgap': 'ITUNESGAPLESS',
    'geID': 'ITUNESGENREID',
    'hdvd': 'ITUNESHDVIDEO',
    'stik': 'ITUNESMEDIATYPE',
    'ownr': 'ITUNESOWNER',
    'purd': 'ITUNESPURCHASEDATE',
    '©mvi': 'MOVEMENT',
    '©mvn': 'MOVEMENTNAME',
    '©mvc': 'MOVEMENTTOTAL',
    '©nrt': 'NARRATOR',
    'pcst': 'PODCAST',
    'catg': 'PODCASTCATEGORY',
    'ldes': 'PODCASTDESC',
    'egid': 'PODCASTID',
    'keyw': 'PODCASTKEYWORDS',
    'purl': 'PODCASTURL',
    '©pub': 'PUBLISHER',
    'rate': 'RATE',
    'shwm': 'SHOWMOVEMENT',
    'sdes': 'STOREDESCRIPTION',
    '©nam': 'TITLE',
    '©trk': 'TITLE',
    'sonm': 'TITLESORT',
    'trkn': ('TRACKNUMBER', 'TOTALTRACKS'),
    'tves': 'TVEPISODE',
    'tven': 'TVEPISODEID',
    'tvnn': 'TVNETWORK',
    'tvsn': 'TVSEASON',
    'tvsh': 'TVSHOW',
    'sosn': 'TVSHOWSORT',
    '©lyr': 'LYRICS',
    '©wrk': 'WORK',
    '©day': 'DATE',
    "akID": "APPLESTOREACCOUNTTYPE",

    # MusicBrainz
    "----:com.apple.iTunes:MusicBrainz Album Artist Id": "MUSICBRAINZ_ALBUMARTISTID",
    "----:com.apple.iTunes:MusicBrainz Album Id": "MUSICBRAINZ_ALBUMID",
    "----:com.apple.iTunes:MusicBrainz Album Release Country": "RELEASECOUNTRY",
    "----:com.apple.iTunes:MusicBrainz Album Status": "RELEASESTATUS",
    "----:com.apple.iTunes:MusicBrainz Album Type": "RELEASETYPE",
    "----:com.apple.iTunes:MusicBrainz Artist Id": "MUSICBRAINZ_ARTISTID",
    "----:com.apple.iTunes:MusicBrainz Disc Id": "MUSICBRAINZ_DISCID",
    "----:com.apple.iTunes:MusicBrainz Original Album Id": "MUSICBRAINZ_ORIGINALALBUMID",
    "----:com.apple.iTunes:MusicBrainz Original Artist Id": "MUSICBRAINZ_ORIGINALARTISTID",
    "----:com.apple.iTunes:MusicBrainz Release Group Id": "MUSICBRAINZ_RELEASEGROUPID",
    "----:com.apple.iTunes:MusicBrainz Release Track Id": "MUSICBRAINZ_RELEASETRACKID",
    "----:com.apple.iTunes:MusicBrainz Track Id": "MUSICBRAINZ_TRACKID",
    "----:com.apple.iTunes:MusicBrainz TRM Id": "MUSICBRAINZ_TRMID",
    "----:com.apple.iTunes:MusicBrainz Work Id": "MUSICBRAINZ_WORKID",
}

STANDARD_TO_MP4: dict[str, str] = {
    'ALBUM': '©alb',
    'ALBUMARTIST': 'aART',
    'ALBUMARTISTSORT': 'soaa',
    'ALBUMSORT': 'soal',
    'APPLESTOREACCOUNTTYPE': 'akID',
    'ARTIST': '©ART',
    'ARTISTSORT': 'soar',
    'BPM': 'tmpo',
    'COMMENT': '©cmt',
    'COMPILATION': 'cpil',
    'COMPOSER': '©wrt',
    'COMPOSERSORT': 'soco',
    'COPYRIGHT': '©prt',
    'DATE': '©day',
    'DESCRIPTION': 'desc',
    'DIRECTOR': '©dir',
    'ENCODEDBY': '©too',
    'GENRE': '©gen',
    'GROUPING': '©grp',
    'ITUNESACCOUNT': 'apID',
    'ITUNESADVISORY': 'rtng',
    'ITUNESALBUMID': 'plID',
    'ITUNESARTISTID': 'atID',
    'ITUNESCATALOGID': 'cnID',
    'ITUNESCOMPOSERID': 'cmID',
    'ITUNESCOUNTRYID': 'sfID',
    'ITUNESGAPLESS': 'pgap',
    'ITUNESGENREID': 'geID',
    'ITUNESHDVIDEO': 'hdvd',
    'ITUNESMEDIATYPE': 'stik',
    'ITUNESOWNER': 'ownr',
    'ITUNESPURCHASEDATE': 'purd',
    'LYRICS': '©lyr',
    'MOVEMENT': '©mvi',
    'MOVEMENTNAME': '©mvn',
    'MOVEMENTTOTAL': '©mvc',
    'NARRATOR': '©nrt',
    'PODCAST': 'pcst',
    'PODCASTCATEGORY': 'catg',
    'PODCASTDESC': 'ldes',
    'PODCASTID': 'egid',
    'PODCASTKEYWORDS': 'keyw',
    'PODCASTURL': 'purl',
    'PUBLISHER': '©pub',
    'RATE': 'rate',
    'SHOWMOVEMENT': 'shwm',
    'STOREDESCRIPTION': 'sdes',
    'TITLE': '©nam',
    'TITLESORT': 'sonm',
    'TVEPISODE': 'tves',
    'TVEPISODEID': 'tven',
    'TVNETWORK': 'tvnn',
    'TVSEASON': 'tvsn',
    'TVSHOW': 'tvsh',
    'TVSHOWSORT': 'sosn',
    'WORK': '©wrk',
    "MUSICBRAINZ_ALBUMARTISTID": "----:com.apple.iTunes:MusicBrainz Album Artist Id",
    "MUSICBRAINZ_ALBUMID": "----:com.apple.iTunes:MusicBrainz Album Id",
    "RELEASECOUNTRY": "----:com.apple.iTunes:MusicBrainz Album Release Country",
    "RELEASESTATUS": "----:com.apple.iTunes:MusicBrainz Album Status",
    "RELEASETYPE": "----:com.apple.iTunes:MusicBrainz Album Type",
    "MUSICBRAINZ_ARTISTID": "----:com.apple.iTunes:MusicBrainz Artist Id",
    "MUSICBRAINZ_DISCID": "----:com.apple.iTunes:MusicBrainz Disc Id",
    "MUSICBRAINZ_ORIGINALALBUMID": "----:com.apple.iTunes:MusicBrainz Original Album Id",
    "MUSICBRAINZ_ORIGINALARTISTID": "----:com.apple.iTunes:MusicBrainz Original Artist Id",
    "MUSICBRAINZ_RELEASEGROUPID": "----:com.apple.iTunes:MusicBrainz Release Group Id",
    "MUSICBRAINZ_RELEASETRACKID": "----:com.apple.iTunes:MusicBrainz Release Track Id",
    "MUSICBRAINZ_TRACKID": "----:com.apple.iTunes:MusicBrainz Track Id",
    "MUSICBRAINZ_TRMID": "----:com.apple.iTunes:MusicBrainz TRM Id",
    "MUSICBRAINZ_WORKID": "----:com.apple.iTunes:MusicBrainz Work Id",
}

# tuple value 单独注册（tracknumber/totaldiscs 反查到原始 key）
MP4_TUPLE_REVERSE: dict[str, tuple[str, int]] = {
    'DISCNUMBER': ('disk', 0),
    'TOTALDISCS': ('disk', 1),
    'TOTALTRACKS': ('trkn', 1),
    'TRACKNUMBER': ('trkn', 0)
}

MP4_BOOL_FIELDS = ['cpil', 'pgap', 'hdvd', 'pcst', 'shwm']
MP4_INT_FIELDS = [
    'tmpo', 'rtng', 'plID', 'atID', 'cnID', 'cmID', 'sfID',
    'geID', 'stik', 'tves', 'tvsn', 'akID',
]


# ============================================================================
# ASF/WMA 相关映射
# ============================================================================
ASF_SKIP_TO_MAP = [
    # 编码器信息
    "WM/ToolName",
    "WM/ToolVersion",
    "WM/EncodedBy",
    "WM/EncodingSettings",
    "WM/EncodingTime",
    "WM/ModifiedBy",
    "ENCODERSETTINGS",

    # 编解码器技术参数
    "DeviceConformanceTemplate",
    "IsVBR",
    "WMFSDKVersion",
    "WMFSDKNeeded",

    # VBR/码率相关（编解码器自动写入）
    "VBRPeak",
    "VBRAverage",
    "WM/WMADRCPeakReference",
    "WM/WMADRCAverageReference",
    "WM/WMADRCPeakTarget",
    "WM/WMADRCAverageTarget",

    # 文件技术属性（SDK自动生成）
    "WM/UniqueFileIdentifier",
    "WM/MediaClassPrimaryID",
    "WM/MediaClassSecondaryID",
    "WM/MediaPrimaryClassID",

    # 旧版的字段名，不保留直接删除
    "WM/Track",
]

ASF_TO_STANDARD = {
    # Content Description Object 常见字段
    "Title": "TITLE",
    "Author": "ARTIST",
    "Copyright": "COPYRIGHT",
    "Description": "COMMENT",
    "Rating": "RATING",

    # Extended Content Description / Metadata 常见音频字段
    "WM/AlbumTitle": "ALBUM",
    "WM/ARTISTS": "ARTISTS",
    "WM/AlbumArtist": "ALBUMARTIST",
    "WM/AlbumArtistSortOrder": "ALBUMARTISTSORT",
    "WM/IsCompilation": "COMPILATION",
    "WM/Composer": "COMPOSER",
    "WM/Conductor": "CONDUCTOR",
    "WM/Writer": "LYRICIST",
    "WM/Genre": "GENRE",
    "WM/Year": "YEAR",
    "WM/TrackNumber": "TRACKNUMBER",
    "WM/PartOfSet": ("DISCNUMBER", "TOTALDISCS"),
    "WM/BeatsPerMinute": "BPM",
    "WM/InitialKey": "INITIALKEY",
    "WM/Language": "LANGUAGE",
    "WM/Lyrics": "LYRICS",
    "WM/Mood": "MOOD",
    "WM/Publisher": "PUBLISHER",
    "WM/ISRC": "ISRC",
    "WM/Media": "Media",
    "WM/ArtistSortOrder": "ARTISTSORT",
    "WM/Barcode": "BARCODE",
    "WM/Script": "SCRIPT",
    "WM/CatalogNo": "CATALOGNUMBER",
# TODO: 这个字段需要有额外处理，ID需要转换为对应的类
#    "WM/GenreID": "GENRE",

    # 排序/扩展来源相关
    "WM/OriginalAlbumTitle": "ORIGINALALBUM",
    "WM/OriginalArtist": "ORIGARTIST",
    "WM/OriginalFilename": "ORIGINALFILENAME",
    "WM/OriginalLyricist": "ORIGLYRICIST",
    "WM/OriginalReleaseTime": "ORIGINALDATE",
    "WM/OriginalReleaseYear": "ORIGINALYEAR",

    # 分组/说明类
    "WM/ContentGroupDescription": "CONTENTGROUP",
    "WM/SubTitle": "SUBTITLE",

    # URL 类
    "WM/AuthorURL": "WWWARTIST",
    "WM/AudioFileURL": "WWWAUDIOFILE",
    "WM/AudioSourceURL": "WWWAUDIOSOURCE",
    "CopyrightURL": "WWWCOPYRIGHT",
    "WM/PromotionURL": "WWWPUBLISHER",

    # MusicBrainz 类
    "MusicBrainz/Track Id": "MUSICBRAINZ_TRACKID",
    "MusicBrainz/Album Id": "MUSICBRAINZ_ALBUMID",
    "MusicBrainz/Album Release Country": "RELEASECOUNTRY",
    "MusicBrainz/Release Track Id": "MUSICBRAINZ_RELEASETRACKID",
    "MusicBrainz/Album Artist Id": "MUSICBRAINZ_ALBUMALISTARTISTID",
    "MusicBrainz/Album Status": "RELEASESTATUS",
    "MusicBrainz/Artist Id": "MUSICBRAINZ_ALBUMARTISTID",
    "MusicBrainz/Release Group Id": "MUSICBRAINZ_RELEASEGROUPID",
    "MusicBrainz/Album Type": "RELEASETYPE",
    "MusicBrainz/Disc Id": "MUSICBRAINZ_DISCID",
    "MusicBrainz/Original Album Id": "MUSICBRAINZ_ORIGINALALBUMID",
    "MusicBrainz/Original Artist Id": "MUSICBRAINZ_ORIGINALARTISTID",
    "MusicBrainz/TRM Id": "MUSICBRAINZ_TRMID",
    "MusicBrainz/Work Id": "MUSICBRAINZ_WORKID",

}

# ASF_TO_STANDARD 的反向映射（标准字段 -> ASF 字段）。
# 由 ASF_TO_STANDARD 中所有“非元组”条目反转而来，标准值彼此唯一，无冲突。
# 元组条目 WM/PartOfSet -> (DISCNUMBER, TOTALDISCS) 不在此处，单独由 ASF_TUPLE_REVERSE 处理。
STANDARD_TO_ASF: dict[str, str] = {
    'TITLE': 'Title',
    'ARTIST': 'Author',
    'COPYRIGHT': 'Copyright',
    'COMMENT': 'Description',
    'RATING': 'Rating',
    'ALBUM': 'WM/AlbumTitle',
    'ARTISTS': 'WM/ARTISTS',
    'ALBUMARTIST': 'WM/AlbumArtist',
    'ALBUMARTISTSORT': 'WM/AlbumArtistSortOrder',
    'COMPILATION': 'WM/IsCompilation',
    'COMPOSER': 'WM/Composer',
    'CONDUCTOR': 'WM/Conductor',
    'LYRICIST': 'WM/Writer',
    'GENRE': 'WM/Genre',
    'YEAR': 'WM/Year',
    'TRACKNUMBER': 'WM/TrackNumber',
    'BPM': 'WM/BeatsPerMinute',
    'INITIALKEY': 'WM/InitialKey',
    'LANGUAGE': 'WM/Language',
    'LYRICS': 'WM/Lyrics',
    'MOOD': 'WM/Mood',
    'PUBLISHER': 'WM/Publisher',
    'ISRC': 'WM/ISRC',
    'Media': 'WM/Media',
    'ARTISTSORT': 'WM/ArtistSortOrder',
    'BARCODE': 'WM/Barcode',
    'SCRIPT': 'WM/Script',
    'CATALOGNUMBER': 'WM/CatalogNo',
    'ORIGINALALBUM': 'WM/OriginalAlbumTitle',
    'ORIGARTIST': 'WM/OriginalArtist',
    'ORIGINALFILENAME': 'WM/OriginalFilename',
    'ORIGLYRICIST': 'WM/OriginalLyricist',
    'ORIGINALDATE': 'WM/OriginalReleaseTime',
    'ORIGINALYEAR': 'WM/OriginalReleaseYear',
    'CONTENTGROUP': 'WM/ContentGroupDescription',
    'SUBTITLE': 'WM/SubTitle',
    'WWWARTIST': 'WM/AuthorURL',
    'WWWAUDIOFILE': 'WM/AudioFileURL',
    'WWWAUDIOSOURCE': 'WM/AudioSourceURL',
    'WWWCOPYRIGHT': 'CopyrightURL',
    'WWWPUBLISHER': 'WM/PromotionURL',
    'MUSICBRAINZ_TRACKID': 'MusicBrainz/Track Id',
    'MUSICBRAINZ_ALBUMID': 'MusicBrainz/Album Id',
    'RELEASECOUNTRY': 'MusicBrainz/Album Release Country',
    'MUSICBRAINZ_RELEASETRACKID': 'MusicBrainz/Release Track Id',
    'MUSICBRAINZ_ALBUMALISTARTISTID': 'MusicBrainz/Album Artist Id',
    'RELEASESTATUS': 'MusicBrainz/Album Status',
    'MUSICBRAINZ_ALBUMARTISTID': 'MusicBrainz/Artist Id',
    'MUSICBRAINZ_RELEASEGROUPID': 'MusicBrainz/Release Group Id',
    'RELEASETYPE': 'MusicBrainz/Album Type',
    'MUSICBRAINZ_DISCID': 'MusicBrainz/Disc Id',
    'MUSICBRAINZ_ORIGINALALBUMID': 'MusicBrainz/Original Album Id',
    'MUSICBRAINZ_ORIGINALARTISTID': 'MusicBrainz/Original Artist Id',
    'MUSICBRAINZ_TRMID': 'MusicBrainz/TRM Id',
    'MUSICBRAINZ_WORKID': 'MusicBrainz/Work Id',
}

# 元组字段反查：标准字段 -> (ASF 字段, 在 "a/b" 中的下标)
# 对应 ASF_TO_STANDARD 里的 "WM/PartOfSet": ("DISCNUMBER", "TOTALDISCS")
ASF_TUPLE_REVERSE: dict[str, tuple[str, int]] = {
    'DISCNUMBER': ('WM/PartOfSet', 0),
    'TOTALDISCS': ('WM/PartOfSet', 1),
}
