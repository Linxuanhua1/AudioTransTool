from audio_handler import *


AUDIO_HANDLERS = {
    '.wav': WavHandler,
    '.m4a': M4aHandler,
    '.ape': ApeHandler,
    '.tak': TakHandler,
    '.tta': TtaHandler,
    '.flac': FlacHandler,
    ".wv": WavepackHandler,
    ".dsf": DSDHandler,
    ".dff": DSDHandler,
    ".aiff": AiffHandler,
    ".aif": AiffHandler,
    ".aifc": AiffHandler,
}

