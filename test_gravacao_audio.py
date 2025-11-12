#!/usr/bin/env python3
"""
Script simples para demonstrar gravação de áudio com botão "premir e manter".
Grava áudio enquanto o botão estiver pressionado e salva em arquivo quando soltar.
"""

import os
import sys
import threading
import time
import numpy as np
import sounddevice as sd
from pathlib import Path

# Adicionar o diretório raiz do projeto ao path para importar os módulos
sys.path.insert(0, os.path.dirname(__file__))

try:
    import PySimpleGUI as sg
except ImportError:
    print("PySimpleGUI não instalado. Instale com: pip install PySimpleGUI")
    sys.exit(1)

class AudioRecorder:
    """Gravador de áudio simples com botão premir e manter."""
    
    def __init__(self, samplerate=16000, channels=1):
        self.samplerate = samplerate
        self.channels = channels
        self._stream = None
        self._recording = False
        self._audio_data = []
        self._lock = threading.Lock()
    
    def start_recording(self):
        """Inicia a gravação de áudio."""
        if self._recording:
            return
        
        self._recording = True
        self._audio_data = []
        
        def audio_callback(indata, frames, time, status):
            if self._recording:
                with self._lock:
                    self._audio_data.append(indata.copy())
        
        try:
            self._stream = sd.InputStream(
                samplerate=self.samplerate,
                channels=self.channels,
                callback=audio_callback,
                blocksize=1024
            )
            self._stream.start()
            print("🎙️ Gravação iniciada...")
        except Exception as e:
            print(f"Erro ao iniciar gravação: {e}")
            self._recording = False
    
    def stop_recording_and_save(self, filename="gravacao.wav"):
        """Para a gravação e salva o áudio em arquivo."""
        if not self._recording:
            return None
        
        self._recording = False
        
        if self._stream:
            self._stream.stop()
            self._stream.close()
            self._stream = None
        
        with self._lock:
            if not self._audio_data:
                print("Nenhum áudio gravado.")
                return None
            
            # Concatenar todos os chunks de áudio
            audio = np.concatenate(self._audio_data, axis=0)
            self._audio_data = []
        
        try:
            # Salvar como WAV
            import scipy.io.wavfile
            scipy.io.wavfile.write(filename, self.samplerate, (audio * 32767).astype(np.int16))
            print(f"✅ Áudio salvo em: {filename}")
            print(f"   Duração: {len(audio) / self.samplerate:.2f} segundos")
            return filename
        except ImportError:
            print("scipy não instalado. Instale com: pip install scipy")
            return None
        except Exception as e:
            print(f"Erro ao salvar áudio: {e}")
            return None

def criar_interface_gui():
    """Cria a interface gráfica com o botão de gravação."""
    
    # Configurar tema
    try:
        sg.theme("SystemDefaultForReal")
    except:
        pass
    
    layout = [
        [sg.Text("Gravador de Áudio - Premir e manter para gravar", font=("Arial", 12, "bold"))],
        [sg.Text("Status:", size=(10, 1)), sg.Text("Pronto", key="-STATUS-", size=(30, 1))],
        [sg.Button("🎙️ Gravar Áudio (premir e manter)", 
                  key="-RECORD-", 
                  button_color=("white", "#0070c0"),
                  size=(35, 2))],
        [sg.Text("Arquivo salvo:", key="-FILE-", size=(50, 1))],
        [sg.Button("Testar Transcrição", key="-TRANSCRIBE-", disabled=True),
         sg.Button("Sair", key="-EXIT-")],
        [sg.HorizontalSeparator()],
        [sg.Multiline(key="-RESULT-", size=(60, 8), disabled=True, autoscroll=True)]
    ]
    
    window = sg.Window("Gravador de Áudio", layout, finalize=True)
    
    # Bind para eventos de pressionar e soltar o botão
    try:
        window["-RECORD-"].Widget.bind("<ButtonPress-1>", lambda e: window.write_event_value("-RECORD-+DOWN", None))
        window["-RECORD-"].Widget.bind("<ButtonRelease-1>", lambda e: window.write_event_value("-RECORD-+UP", None))
    except Exception as e:
        sg.popup_error(f"Erro ao configurar eventos do botão: {e}")
        return
    
    return window

def main():
    """Função principal."""
    print("Iniciando gravador de áudio...")
    
    # Verificar se scipy está instalado
    try:
        import scipy.io.wavfile
    except ImportError:
        sg.popup_error("scipy não instalado. Instale com: pip install scipy")
        return
    
    recorder = AudioRecorder()
    window = criar_interface_gui()
    arquivo_atual = None
    
    while True:
        event, values = window.read(timeout=100)
        
        if event in (sg.WIN_CLOSED, "-EXIT-"):
            break
        
        # Botão pressionado - iniciar gravação
        if event == "-RECORD-+DOWN":
            try:
                recorder.start_recording()
                window["-STATUS-"].update("🎙️ Gravando... (solte para parar)")
                window["-RECORD-"].update("🎙️ Gravando... (solte)", button_color=("white", "#d9534f"))
            except Exception as e:
                window["-STATUS-"].update(f"Erro: {e}")
        
        # Botão solto - parar gravação e salvar
        if event == "-RECORD-+UP":
            try:
                timestamp = time.strftime("%Y%m%d_%H%M%S")
                filename = f"gravacao_{timestamp}.wav"
                
                window["-STATUS-"].update("💾 Salvando...")
                window["-RECORD-"].update("💾 Salvando...", button_color=("white", "#f0ad4e"))
                
                # Salvar em thread separada para não travar a UI
                def save_audio():
                    nonlocal arquivo_atual
                    arquivo_atual = recorder.stop_recording_and_save(filename)
                    if arquivo_atual:
                        window.write_event_value("-SAVE-DONE", arquivo_atual)
                    else:
                        window.write_event_value("-SAVE-ERROR", None)
                
                threading.Thread(target=save_audio, daemon=True).start()
                
            except Exception as e:
                window["-STATUS-"].update(f"Erro: {e}")
                window["-RECORD-"].update("🎙️ Gravar Áudio (premir e manter)", button_color=("white", "#0070c0"))
        
        # Salvamento concluído
        if event == "-SAVE-DONE":
            filename = values[event]
            window["-FILE-"].update(filename)
            window["-STATUS-"].update("✅ Salvo com sucesso")
            window["-RECORD-"].update("🎙️ Gravar Áudio (premir e manter)", button_color=("white", "#0070c0"))
            window["-TRANSCRIBE-"].update(disabled=False)
        
        # Erro no salvamento
        if event == "-SAVE-ERROR":
            window["-STATUS-"].update("❌ Erro ao salvar")
            window["-RECORD-"].update("🎙️ Gravar Áudio (premir e manter)", button_color=("white", "#0070c0"))
        
        # Testar transcrição
        if event == "-TRANSCRIBE-" and arquivo_atual:
            try:
                window["-RESULT-"].update("Transcrevendo...\n", append=True)
                window["-TRANSCRIBE-"].update("Transcrevendo...", disabled=True)
                
                def transcribe_audio():
                    try:
                        from app.core.stt import transcribe_file
                        texto = transcribe_file(arquivo_atual, lang_hint="pt")
                        window.write_event_value("-TRANSCRIBE-DONE", texto)
                    except Exception as e:
                        window.write_event_value("-TRANSCRIBE-ERROR", str(e))
                
                threading.Thread(target=transcribe_audio, daemon=True).start()
                
            except Exception as e:
                window["-RESULT-"].update(f"Erro ao transcrever: {e}\n", append=True)
        
        # Transcrição concluída
        if event == "-TRANSCRIBE-DONE":
            texto = values[event]
            window["-RESULT-"].update(f"Texto transcrito:\n{texto}\n", append=True)
            window["-TRANSCRIBE-"].update("Testar Transcrição", disabled=False)
        
        # Erro na transcrição
        if event == "-TRANSCRIBE-ERROR":
            erro = values[event]
            window["-RESULT-"].update(f"Erro na transcrição: {erro}\n", append=True)
            window["-TRANSCRIBE-"].update("Testar Transcrição", disabled=False)
    
    window.close()

if __name__ == "__main__":
    main()