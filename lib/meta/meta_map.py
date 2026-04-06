from enum import Enum
from dataclasses import dataclass


ID3_NOT_SUPPORTED = ['AENC', 'ASPI', 'COMR', 'ENCR', 'EQU2', "ETCO", "GEOB",
                     'GRID', 'LINK', "MCDI", 'MLLT', "OWNE", "PRIV", 'PCNT',
                     "POPM", 'POSS', 'RBUF', "RVA2", 'RVRB', 'SEEK', 'SIGN',
                     'SYTC', "ATXT", 'CHAP', 'CTOC', 'USER', 'RVAD']


class ImageType(Enum):
    Other = 0
    Icon = 1
    OtherIcon = 2
    Front = 3
    Back = 4
    Leaflet = 5
    Media = 6
    LeadArtist = 7
    Artist = 8
    Conductor = 9
    Band = 10
    Composer = 11
    Lyricist = 12
    RecordingLocation = 13
    DuringRecording = 14
    DuringPerformance = 15
    ScreenCapture = 16
    Fish = 17
    Illustration = 18
    BandLogo = 19
    PublisherLogo = 20


@dataclass(frozen=True)
class ImageTag:
    data: bytes
    type: ImageType | None
    desc: str | None
    mime: str | None

    def __str__(self):
        return (
            f"(图片标签: 类型={self.type}, 描述={self.desc}, "
            f"MIME={self.mime}, 数据长度={len(self.data) if self.data else 0})"
        )

    def __repr__(self):
        return (
            f"(图片标签: 类型={self.type}, 描述={self.desc}, "
            f"MIME={self.mime}, 数据长度={len(self.data) if self.data else 0})"
        )


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

APEV2_TO_STANDARD = {
    "Album Artist": "ALBUMARTIST",
    "TRACK": "TRACKNUMBER",
    "Cover Art (Other)": ImageType.Other,
    "Cover Art (Icon)": ImageType.Icon,
    "Cover Art (Other Icon)": ImageType.OtherIcon,
    "Cover Art (Front)": ImageType.Front,
    "Cover Art (Back)": ImageType.Back,
    "Cover Art (Leaflet)": ImageType.Leaflet,
    "Cover Art (Media)": ImageType.Media,
    "Cover Art (Lead Artist)": ImageType.LeadArtist,
    "Cover Art (Artist)": ImageType.Artist,
    "Cover Art (Conductor)": ImageType.Conductor,
    "Cover Art (Band)": ImageType.Band,
    "Cover Art (Composer)": ImageType.Composer,
    "Cover Art (Lyricist)": ImageType.Lyricist,
    "Cover Art (Recording Location)": ImageType.RecordingLocation,
    "Cover Art (During Recording)": ImageType.DuringRecording,
    "Cover Art (During Performance)": ImageType.DuringPerformance,
    "Cover Art (Video Capture)": ImageType.ScreenCapture,
    "Cover Art (Fish)": ImageType.Fish,
    "Cover Art (Illustration)": ImageType.Illustration,
    "Cover Art (Band Logotype)": ImageType.BandLogo,
    "Cover Art (Publisher Logotype)": ImageType.PublisherLogo,
}

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
    "akID": "APPLESTOREACCOUNTTYPE"
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
'TITLE': '©trk',
'TITLESORT': 'sonm',
'TVEPISODE': 'tves',
'TVEPISODEID': 'tven',
'TVNETWORK': 'tvnn',
'TVSEASON': 'tvsn',
'TVSHOW': 'tvsh',
'TVSHOWSORT': 'sosn',
'WORK': '©wrk'
}

# tuple value 单独注册（tracknumber/totaldiscs 反查到原始 key）
MP4_TUPLE_REVERSE: dict[str, tuple[str, int]] = {
'DISCNUMBER': ('disk', 0),
'TOTALDISCS': ('disk', 1),
'TOTALTRACKS': ('trkn', 1),
'TRACKNUMBER': ('trkn', 0)
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

STANDARD_TO_APEV2: dict[str, str] = {'ALBUMARTIST': 'Album Artist', 'TRACKNUMBER': 'TRACK'}