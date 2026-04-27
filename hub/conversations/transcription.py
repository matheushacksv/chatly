import base64
from groq import Groq
from django.conf import settings
from io import BytesIO


def transcribe_audio(file_url: str) -> str:
    import httpx
    from urllib.parse import urlsplit, urlunsplit

    # Remove query string (pre-signed URLs expiradas ficam acessíveis sem assinatura
    # quando o bucket tem ACL public-read)
    parts = urlsplit(file_url)
    clean_url = urlunsplit((parts.scheme, parts.netloc, parts.path, '', ''))

    response = httpx.get(clean_url, timeout=30.0)
    response.raise_for_status()
    audio_bytes = response.content

    client = Groq(api_key=settings.GROQ_API_KEY)

    transcription = client.audio.transcriptions.create(
        file=("audio.ogg", BytesIO(audio_bytes)),
        model="whisper-large-v3",
    )

    return transcription.text
