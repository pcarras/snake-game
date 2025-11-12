import os, re, time, threading, queue
from dataclasses import dataclass, field
from typing import Dict, Callable, Any, Optional

# =========================
# CONFIGURAÇÃO BÁSICA
# =========================
LANG_HINT = "pt-PT"
FW_MODEL = os.getenv("FW_MODEL", "base")     # base | small | medium | large-v3
USE_LLM = bool(os.getenv("OPENAI_API_KEY"))  # usa LLM se houver chave
LLM_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
LLM_TEMPERATURE = 0.0
LLM_MAX_TOKENS = 120
KEYWORDS_ANY = ["IA", "inteligência artificial", "algoritmo"]  # pode ficar vazio

# =========================
# TTS (pyttsx3) – só lê respostas, nunca comandos
# =========================
def speak(text: str):
    try:
        import pyttsx3
        engine = pyttsx3.init()
        # tentar voz PT-PT
        for v in engine.getProperty('voices'):
            name = (v.name or "").lower()
            if "portugal" in name or "portuguese (portugal)" in name:
                engine.setProperty('voice', v.id)
                break
        engine.setProperty('rate', 175)
        engine.say(text)
        engine.runAndWait()
    except Exception:
        pass

# =========================
# STT (faster-whisper) com botão “premir e manter”
# =========================
class PTTRecorder:
    """Gravação simples enquanto o botão está premido; ao largar, transcreve."""
    def __init__(self, language="pt", model_size="base"):
        self.language = language
        self.model_size = model_size
        self._stream = None
        self._buf = []
        self._lock = threading.Lock()
        self._model = None

    def _ensure_model(self):
        if self._model is None:
            from faster_whisper import WhisperModel
            # CPU por omissão; ajustar conforme hardware
            self._model = WhisperModel(self.model_size, device="cpu", compute_type="int8")

    def start(self):
        import sounddevice as sd
        self._buf = []
        self._stream = sd.InputStream(
            channels=1, samplerate=16000, blocksize=1024,
            callback=lambda indata, frames, t, status: self._audio_cb(indata)
        )
        self._stream.start()

    def _audio_cb(self, indata):
        with self._lock:
            self._buf.append(indata.copy())

    def stop_and_transcribe(self) -> str:
        import numpy as np
        if self._stream:
            self._stream.stop()
            self._stream.close()
            self._stream = None
        with self._lock:
            if not self._buf:
                return ""
            audio = np.concatenate(self._buf, axis=0).astype("float32")
            self._buf = []
        # transcrever
        self._ensure_model()
        segments, _ = self._model.transcribe(audio, language=self.language, beam_size=1)
        text = "".join(s.text for s in segments).strip()
        return text

# =========================
# LLM (opcional) + fallback regex
# =========================
def llm_parse_intent(user_text: str) -> Dict[str, Any]:
    """
    Mapeia linguagem natural para {action, params}.
    Ações canónicas:
      - smoke_cigarette{qty}
      - drink_water{ml}
      - eat_apple{}
      - show_inventory{}
      - help{}
    """
    text = (user_text or "").strip().lower()

    # Fallback heurístico (opera sem LLM)
    m = re.search(r"(fum(ar)?|acender).*cigar", text)
    if m:
        q = 1
        m2 = re.search(r"(\d+)\s*cigar", text)
        if m2: q = max(1, int(m2.group(1)))
        return {"action":"smoke_cigarette","params":{"qty":q}}

    if re.search(r"(beber|tomar).*(água|garrafa|copo)", text):
        ml = 250
        m3 = re.search(r"(\d+)\s*ml", text)
        if m3: ml = max(50, int(m3.group(1)))
        return {"action":"drink_water","params":{"ml":ml}}

    if re.search(r"(comer|morder).*maçã", text):
        return {"action":"eat_apple","params":{}}

    if re.search(r"(inventário|mochila|bolsos?)", text):
        return {"action":"show_inventory","params":{}}

    if re.search(r"(ajuda|help|\?)", text):
        return {"action":"help","params":{}}

    # LLM (se disponível)
    if USE_LLM:
        try:
            from openai import OpenAI
            client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
            sys_prompt = (
                "Tarefa: extrair uma ação canónica e parâmetros de um comando em PT-PT.\n"
                "Ações válidas: [smoke_cigarette{qty:int}, drink_water{ml:int}, "
                "eat_apple{}, show_inventory{}, help{}]. Se não corresponder, devolve help.\n"
                "Responde apenas JSON minificado."
            )
            usr = f"Comando: {user_text}"
            r = client.chat.completions.create(
                model=LLM_MODEL, temperature=LLM_TEMPERATURE, max_tokens=LLM_MAX_TOKENS,
                messages=[{"role":"system","content":sys_prompt},
                          {"role":"user","content":usr}],
                response_format={"type":"json_object"}
            )
            import json
            obj = json.loads(r.choices[0].message.content)
            if "action" in obj:
                return obj
        except Exception:
            pass

    return {"action":"help","params":{}}

# =========================
# Núcleo do jogo
# =========================
@dataclass
class GameState:
    hp: int = 100
    hydration: int = 50  # 0..100
    inventory: Dict[str, int] = field(default_factory=lambda: {"cigarettes": 5, "matches": 3, "apple": 1, "water_ml": 500})
    log: list = field(default_factory=list)

    def add_log(self, msg: str):
        self.log.append(msg)

ActionFunc = Callable[[GameState, Dict[str, Any]], str]
ACTION_REGISTRY: Dict[str, ActionFunc] = {}

def action(name: str):
    def deco(fn: ActionFunc):
        ACTION_REGISTRY[name] = fn
        return fn
    return deco

@action("help")
def act_help(s: GameState, p: Dict[str, Any]) -> str:
    return ("Acções: smoke_cigarette {qty}, drink_water {ml}, eat_apple, show_inventory.\n"
            "Exemplos: «fuma um cigarro», «bebe 300 ml de água», «inventário».")

@action("show_inventory")
def act_show_inventory(s: GameState, p: Dict[str, Any]) -> str:
    inv = s.inventory
    return (f"Inventário: cigarros={inv.get('cigarettes',0)}, fósforos={inv.get('matches',0)}, "
            f"maçãs={inv.get('apple',0)}, água={inv.get('water_ml',0)} ml.")

@action("smoke_cigarette")
def act_smoke(s: GameState, p: Dict[str, Any]) -> str:
    qty = max(1, int(p.get("qty", 1)))
    have = s.inventory.get("cigarettes", 0)
    if have <= 0:
        return "Não tem cigarros. A acção falha."
    used = min(qty, have)
    s.inventory["cigarettes"] = have - used
    s.hydration = max(0, s.hydration - 2*used)
    s.hp = max(1, s.hp - 1*used)
    return f"Fuma {used} cigarro(s). Restam {s.inventory['cigarettes']}. Hidratação={s.hydration}, HP={s.hp}."

@action("drink_water")
def act_drink(s: GameState, p: Dict[str, Any]) -> str:
    ml = max(50, int(p.get("ml", 250)))
    have = s.inventory.get("water_ml", 0)
    if have <= 0:
        return "Não tem água suficiente."
    take = min(ml, have)
    s.inventory["water_ml"] = have - take
    s.hydration = min(100, s.hydration + take//50)
    return f"Bebe {take} ml de água. Restam {s.inventory['water_ml']} ml. Hidratação={s.hydration}."

@action("eat_apple")
def act_eat_apple(s: GameState, p: Dict[str, Any]) -> str:
    have = s.inventory.get("apple", 0)
    if have <= 0:
        return "Não tem maçãs."
    s.inventory["apple"] = have - 1
    s.hp = min(100, s.hp + 5)
    s.hydration = min(100, s.hydration + 3)
    return f"Come uma maçã. HP={s.hp}, Hidratação={s.hydration}. Restam {s.inventory['apple']} maçãs."

def dispatch(state: GameState, intent: Dict[str, Any]) -> str:
    act = intent.get("action", "help")
    fn = ACTION_REGISTRY.get(act, ACTION_REGISTRY["help"])
    out = fn(state, intent.get("params", {}))
    state.add_log(out)
    return out

# =========================
# GUI (PySimpleGUI)
# =========================
import PySimpleGUI as sg

def make_window():
    # Tema padrão - PySimpleGUI 5.x usa tema padrão automaticamente
    # sg.theme() pode não estar disponível em todas as versões
    try:
        if hasattr(sg, 'theme'):
            sg.theme("SystemDefaultForReal")
    except:
        pass
    layout = [
        [sg.Text("Jogo (PT-PT) — comandos por voz ou texto. Premir e manter para falar.")],
        [sg.Multiline(size=(80, 18), key="-LOG-", disabled=True, autoscroll=True, reroute_stdout=False)],
        [
            sg.Button("🎙️ Falar (premir e manter)", key="-PTT-", button_color=("white","#0070c0")),
            sg.Input(key="-INPUT-", size=(55,1), focus=True, enable_events=True),
            sg.Button("Enviar", key="-SEND-", bind_return_key=True),
        ],
        [sg.Checkbox("Ler respostas em voz alta (TTS)", key="-TTS-", default=True),
         sg.Text("Modelo STT:"), sg.Text(FW_MODEL, key="-FW-")]
    ]
    win = sg.Window("Game Agent (PTT + LLM + TTS)", layout, return_keyboard_events=True, finalize=True)
    # Bind para eventos de rato no botão (press/release)
    try:
        if hasattr(win["-PTT-"], 'Widget'):
            win["-PTT-"].Widget.bind("<ButtonPress-1>", lambda e: win.write_event_value("-PTT-+DOWN", None))
            win["-PTT-"].Widget.bind("<ButtonRelease-1>", lambda e: win.write_event_value("-PTT-+UP", None))
    except Exception:
        pass  # Se o binding não funcionar, o botão ainda pode ser usado normalmente
    return win

def append_log(window, text: str, speak_it: bool):
    window["-LOG-"].update(text + "\n", append=True)
    if speak_it and window["-TTS-"].get():
        # TTS só para respostas do jogo
        threading.Thread(target=speak, args=(text,), daemon=True).start()

def main():
    state = GameState()
    win = make_window()
    recorder = PTTRecorder(language="pt", model_size=FW_MODEL)

    def handle_command(cmd_text: str):
        cmd_text = cmd_text.strip()
        if not cmd_text:
            return
        # (1) NÃO LER o comando do utilizador em voz alta; apenas mostrar:
        win["-LOG-"].update(f"> {cmd_text}\n", append=True)
        # (2) Interpretar e despachar
        intent = llm_parse_intent(cmd_text)
        reply = dispatch(state, intent)
        # (3) LER apenas a resposta do jogo
        append_log(win, reply, speak_it=True)

    while True:
        ev, vals = win.read(timeout=100)
        if ev in (sg.WIN_CLOSED, "Escape:27"):
            break

        if ev == "-SEND-" or (ev == "-INPUT-" and ev.endswith("\r")):
            txt = vals["-INPUT-"]
            win["-INPUT-"].update("")
            handle_command(txt)

        # PTT: pressionar → começar a gravar
        if ev == "-PTT-+DOWN":
            try:
                recorder.start()
                win["-PTT-"].update("🎙️ A gravar… (largue para transcrever)", button_color=("white","#d9534f"))
            except Exception as e:
                append_log(win, f"[STT] Erro a iniciar microfone: {e}", speak_it=False)

        # PTT: largar → parar e transcrever
        if ev == "-PTT-+UP":
            try:
                win["-PTT-"].update("🎙️ a transcrever…", button_color=("white","#f0ad4e"))
                text = recorder.stop_and_transcribe()
                win["-PTT-"].update("🎙️ Falar (premir e manter)", button_color=("white","#0070c0"))
                if text:
                    handle_command(text)
                else:
                    append_log(win, "[STT] Sem áudio detectado.", speak_it=False)
            except Exception as e:
                append_log(win, f"[STT] Erro na transcrição: {e}", speak_it=False)
                win["-PTT-"].update("🎙️ Falar (premir e manter)", button_color=("white","#0070c0"))

    win.close()

if __name__ == "__main__":
    main()
