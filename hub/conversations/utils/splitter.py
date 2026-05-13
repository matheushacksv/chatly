import re

_SENT_RE = re.compile(r'(?<=[.!?])\s+|\n+')
_CODE_RE = re.compile(r'```.*?```', re.DOTALL)
MIN_CHUNK_LEN = 15

def split_response(text: str) -> list[str]:
    '''Split text por frase; perserva code blocks; mescla fragmentos curtos'''
    if not text or not text.strip():
        return []
    
    blocks = []
    def _stash(m):
        blocks.append(m.group(0))
        return f'\x00BLOCK{len(blocks)-1}\x00'
    masked = _CODE_RE.sub(_stash, text)

    raw = [p.strip() for p in _SENT_RE.split(masked) if p.strip()]
    
    merged = []
    for part in raw:
        if merged and len(part) < MIN_CHUNK_LEN:
            merged[-1] = merged[-1] + ' ' + part
        else:
            merged.append(part)

    def _restore(s):
        return re.sub(r'\x00BLOCK(\d+)\x00', lambda m: blocks[int(m.group(1))], s)
    return [_restore(c) for c in merged]

def compute_delay_ms(chunk: str, speed: int, min_ms: int, max_ms: int) -> int:
    return max(min_ms, min(max_ms, len(chunk) * speed))


