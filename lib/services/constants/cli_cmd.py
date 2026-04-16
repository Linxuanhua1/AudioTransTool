
CMD_WAVBYTES2FLAC = "flac - --best --threads=16 -o \"{out_p}\""

CMD_PCMBYTES2FLAC = ("flac --force-raw-format --sign=signed --endian={endian} --channels={channels}"
                     "--sample-rate={sample_rate} --bps={bps} - --best --threads=16 -o \"{out_p}\"")

CMD_BYTES2WV = "wavpack --threads=12 -hhx6 - {out_p}"

CMD_TAK2WAVBYTES = 'Takc -d \"{file_p}\" -'

CMD_APE2WAVBYTES = 'MAC \"{file_p}\" - -d -threads=16'

CMD_TTA2WAVBYTES = 'ttaenc -d \"{file_p}\" -'

CMD_M4A2WAVBYTES = 'refalac -D \"{file_p}\" -o -'

CMD_WAVPACK2WAVBYTES = 'wvunpack --wav --threads=12 \"{file_p}\" -'

CMD_FLAC2WAVBYTES = 'flac -d --stdout -'


AUDIO_EXT2CLI_CMD= {
    ".tak": CMD_TAK2WAVBYTES,
    ".tta": CMD_TTA2WAVBYTES,
    ".ape": CMD_APE2WAVBYTES,
    ".m4a": CMD_M4A2WAVBYTES,
    ".wv": CMD_WAVPACK2WAVBYTES,
    ".flac": CMD_FLAC2WAVBYTES,
}