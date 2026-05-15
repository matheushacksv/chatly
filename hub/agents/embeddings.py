import logging
from django.conf import settings
from openai import OpenAI

logger = logging.getLogger(__name__)

EMBED_MODEL = 'text-embedding-3-small'
EMBED_DIM = 1536
_BATCH = 100

_client = None

def _get_client():
    global _client
    if _client is None:
        _client = OpenAI(api_key=settings.OPENAI_API_KEY)
    return _client

def chunk_text(text, size=1800, overlap=200):
    '''Quebra texto em pedaços ~size chars, com sobreposição. Respeita paragráfos'''
    text = (text or '').strip()
    if not text:
        return []
    
    paragraphs = [p.strip() for p in text.split('\n\n') if p.strip()]
    chunks = []
    buf = ''

    for para in paragraphs:
        if len(para) > size:
            if buf:
                chunks.append(buf)
                buf = ''
            for i in range(0, len(para), size - overlap):
                chunks.append(para[i:i + size])
            continue
        
        if len(buf) + len(para) + 2 > size:
            chunks.append(buf)
            buf = (buf[-overlap:] + '\n\n' + para) if overlap else para
        else:
            buf = (buf + '\n\n' + para) if buf else para
    
    if buf:
        chunks.append(buf)
    return [c.strip() for c in chunks if c.strip()]

def embed_texts(texts):
    '''Lista de strings -> lista de vetores (1536 dim). Batched'''
    if not texts:
        return []
    out = []
    client = _get_client()
    for i in range(0, len(texts), _BATCH):
        batch = texts[i:i + _BATCH]
        resp = client.embeddings.create(model=EMBED_MODEL, input=batch)
        out.extend(d.embedding for d in resp.data)
    return out

def embed_query(text):
    '''Uma string -> um vetor'''
    return embed_texts([text or ''])[0]
