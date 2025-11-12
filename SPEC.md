
# SPEC — Motor Genérico de Aventura Conversacional

## Descrição geral
Motor determinístico, extensível por **pacotes YAML**, com **entrada por texto/voz** e **saída por texto/voz**. Integra Groq/OpenRouter para interpretação semântica opcional.

## Endpoints
- `GET /` — SPA.
- `GET /api/state` — estado corrente.
- `POST /api/command` — `form-data: cmd` → aplica no motor; devolve `output`, `state`, `tts_base64`.
- `POST /api/stt` — `form-data: file` (áudio) → transcrição via Fast Whisper.
- `POST /api/llm` — `form-data: prompt, provider (groq|openrouter)` → resposta LLM + TTS.

## Configuração
- `.env` (ver `.env.example`): `GROQ_API_KEY`, `OPEN_ROUTER_API_KEY`, `TTS_LANG`, `WHISPER_MODEL`.
- Requer **ffmpeg** instalado para STT (conversão para WAV).

## YAML do mundo (esquema)
```yaml
meta:
  title: "Título"
  start_location: "ID"
  start_money: 0
  start_items: []
  start_energy: 5
  capacity: 6

locations:
  - {id: "A01", x: 1, y: 1, name: "Nome"}

objects:
  - {id: "X01", name: "Item", location: "A01"}

npcs:
  - {id: "NPC1", name: "Nome", route: ["A01","A02"]}

verbs:
  mover: ["ir","norte","sul","este","oeste","n","s","e","o"]
  examinar: ["examinar","olhar"]
  usar: ["usar","utilizar"]
  # etc.

situations:
  - id: S01
    location: A01
    pre: {has_item: "X01", min_money: 2, flag: "abc", npc: "NPC1"}
    trigger: {verb: usar, args: {target: "corda"}}
    text: "Resultado narrativo."
    effects: {money_delta: 3, set_flags: ["ok"], give_items: ["X02"], transform_item: {from: "X01", to:"X03"}}
```

## Fluxo de testes com o demo
1. `examinar praia` → apanha **Corda**.
2. `este` → Base do Farol. Se **Guarda** presente, `falar`.
3. `sul` → Cabana → `examinar` → **Lanterna**.
4. `norte`, `norte` → Cais → `examinar` → **Chave**.
5. `oeste` → Escadaria → `usar corda` e `usar lanterna`.
6. `oeste` → Base → `abrir baú` → final.

## Extensão
- Novos **gamepacks** em `gamepacks/<nome>/world.yaml`.
- Alterar `WORLD_PATH` em `app/main.py` ou parametrizar por variável de ambiente.
- Para UI enriquecida, acrescentar minimapa e janelas de diálogo.

## Dependências
Ver `requirements.txt`. Instalação e execução:
```bash
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
python -m app.main
```
Abrir `http://127.0.0.1:8000`.
```
