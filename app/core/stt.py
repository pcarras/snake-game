
from __future__ import annotations
import os, tempfile, subprocess
from faster_whisper import WhisperModel
from dotenv import load_dotenv
load_dotenv()
MODEL = os.getenv("WHISPER_MODEL","base")  # Mudado de 'small' para 'base' para evitar problemas de memória
_model = None
def _get():
    import logging
    logger = logging.getLogger(__name__)
    global _model
    if _model is None:
        try:
            logger.info(f"Carregando modelo Whisper '{MODEL}' pela primeira vez (isso pode demorar alguns segundos)...")
            logger.info("NOTA: Se o servidor travar aqui, o modelo pode estar muito grande para a memória disponível.")
            _model = WhisperModel(MODEL, device="cpu", compute_type="int8")
            logger.info("Modelo Whisper carregado com sucesso!")
        except Exception as e:
            logger.error(f"Erro ao carregar modelo Whisper: {e}", exc_info=True)
            raise Exception(f"Falha ao carregar modelo Whisper '{MODEL}': {str(e)}. Tente usar um modelo menor (base ou tiny) definindo WHISPER_MODEL=base ou WHISPER_MODEL=tiny no .env")
    return _model

def ensure_wav(path: str)->str:
    if path.lower().endswith(".wav"): return path
    out = path + ".wav"
    try:
        result = subprocess.run(["ffmpeg","-y","-i",path,"-ar","16000","-ac","1",out], 
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True, timeout=30)
    except subprocess.CalledProcessError as e:
        raise Exception(f"Erro ao converter áudio com ffmpeg: {e.stderr.decode('utf-8', errors='ignore')}")
    except FileNotFoundError:
        raise Exception("ffmpeg não encontrado. Por favor, instale o ffmpeg.")
    except subprocess.TimeoutExpired:
        raise Exception("Timeout ao converter áudio com ffmpeg.")
    return out

def transcribe_file(path: str, lang_hint="pt")->str:
    import logging
    logger = logging.getLogger(__name__)
    wav = None
    try:
        logger.info("Obtendo modelo Whisper...")
        m = _get()
        logger.info(f"Modelo Whisper carregado. Transcrevendo arquivo: {path}")
        
        logger.info("Convertendo áudio para WAV...")
        wav = ensure_wav(path)
        logger.info(f"Áudio convertido para WAV: {wav}")
        
        logger.info("Iniciando transcrição com Whisper...")
        segs, info = m.transcribe(wav, language=lang_hint)
        logger.info("Transcrição concluída, processando segmentos...")
        
        text = "".join(s.text for s in segs).strip()
        logger.info(f"Texto transcrito: '{text}' (comprimento: {len(text)})")
        if not text:
            logger.warning("Nenhum texto foi transcrito. Pode ser que o áudio esteja vazio ou muito baixo.")
        return text
    except MemoryError as e:
        logger.error(f"Erro de memória ao transcrever: {e}. O modelo pode ser muito grande.")
        raise Exception("Erro de memória. Tente usar um modelo menor (WHISPER_MODEL=base ou tiny)")
    except Exception as e:
        logger.error(f"Erro na transcrição: {e}", exc_info=True)
        raise
    finally:
        # Limpar arquivo WAV temporário se foi criado
        if wav and wav != path and os.path.exists(wav):
            try:
                os.remove(wav)
            except:
                pass
