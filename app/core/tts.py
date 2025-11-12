
from __future__ import annotations
from gtts import gTTS
import io, base64, os
from dotenv import load_dotenv
load_dotenv()
LANG = os.getenv("TTS_LANG","pt")

def text_to_speech_base64(text: str, lang: str|None=None)->str:
    import logging
    logger = logging.getLogger(__name__)
    try:
        if not text or not text.strip():
            logger.warning("Texto vazio para TTS")
            return ""
        logger.info(f"Gerando TTS para texto: '{text[:50]}...' (lang={lang or LANG})")
        tts = gTTS(text=text, lang=lang or LANG)
        buf = io.BytesIO()
        tts.write_to_fp(buf)
        buf.seek(0)
        audio_data = buf.read()
        base64_data = base64.b64encode(audio_data).decode("utf-8")
        logger.info(f"TTS gerado com sucesso. Tamanho: {len(audio_data)} bytes, Base64: {len(base64_data)} chars")
        return base64_data
    except Exception as e:
        logger.error(f"Erro ao gerar TTS: {e}", exc_info=True)
        raise
