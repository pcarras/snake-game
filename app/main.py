
import os, tempfile, warnings
warnings.filterwarnings("ignore", message=".*pkg_resources is deprecated.*")
from fastapi import FastAPI, UploadFile, File, Form
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from app.core.engine import Engine, load_world
from app.core.tts import text_to_speech_base64
from app.core.stt import transcribe_file
from app.core.llm import groq_chat, openrouter_chat

ROOT = os.path.dirname(os.path.dirname(__file__))
WORLD_PATH = os.path.join(ROOT,"gamepacks","demo_farol","world.yaml")
WORLD = load_world(WORLD_PATH)
ENG = Engine(WORLD)

app = FastAPI(title="RPG Engine Genérico")
app.mount("/static", StaticFiles(directory=os.path.join(ROOT,"static")), name="static")

@app.get("/", response_class=HTMLResponse)
def index():
    with open(os.path.join(ROOT,"static","index.html"),"r",encoding="utf-8") as f:
        return HTMLResponse(f.read())

@app.get("/api/state")
def state(): return JSONResponse(ENG.state.to_public())

@app.post("/api/command")
async def command(cmd: str = Form(...)):
    try:
        res = ENG.run(cmd)
        tts = ""
        try:
            if res.get("output"):
                tts = text_to_speech_base64(res["output"])
        except Exception as e:
            import logging
            logging.getLogger(__name__).error(f"Erro ao gerar TTS: {e}", exc_info=True)
        return JSONResponse({"output":res["output"], "state": res["state"], "tts_base64": tts})
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JSONResponse({"output": f"Erro: {str(e)}", "state": {}, "tts_base64": ""}, status_code=500)

@app.post("/api/stt")
async def stt(file: UploadFile = File(...)):
    import logging
    logger = logging.getLogger(__name__)
    path = None
    wav_path = None
    try:
        logger.info(f"Recebendo arquivo de áudio: {file.filename}, tipo: {file.content_type}")
        file_content = await file.read()
        logger.info(f"Arquivo recebido: {len(file_content)} bytes")
        
        with tempfile.NamedTemporaryFile(delete=False, suffix=".webm") as tmp:
            tmp.write(file_content)
            path = tmp.name
        logger.info(f"Arquivo temporário criado: {path}")
        
        logger.info("Iniciando transcrição...")
        text = transcribe_file(path, lang_hint="pt")
        logger.info(f"Transcrição concluída: '{text}'")
        return JSONResponse({"text": text, "error": None})
    except Exception as e:
        import traceback
        error_msg = str(e)
        logger.error(f"Erro no STT: {error_msg}", exc_info=True)
        traceback.print_exc()
        return JSONResponse({"text": "", "error": error_msg}, status_code=500)
    finally:
        try:
            if path and os.path.exists(path):
                os.remove(path)
            if wav_path and os.path.exists(wav_path):
                os.remove(wav_path)
        except: pass

@app.post("/api/llm")
async def llm(prompt: str = Form(...), provider: str = Form("groq")):
    out = groq_chat(prompt) if provider=="groq" else openrouter_chat(prompt)
    tts = text_to_speech_base64(out)
    return JSONResponse({"text": out, "tts_base64": tts})

if __name__ == "__main__":
    import uvicorn
    import logging
    logging.basicConfig(level=logging.INFO)
    uvicorn.run(
        app, 
        host="127.0.0.1", 
        port=8000,
        log_level="info",
        access_log=True,
        reload=False  # Desabilitar reload para evitar problemas
    )
