#!/usr/bin/env python3
"""
Script simples para testar a funcionalidade de transcrição de áudio para texto.
"""

import os
import sys
import logging

# Configurar logging para ver os logs da transcrição
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Adicionar o diretório raiz do projeto ao path para importar os módulos
sys.path.insert(0, os.path.dirname(__file__))

from app.core.stt import transcribe_file

def test_transcription(audio_path: str):
    """
    Testa a transcrição de um arquivo de áudio.
    
    Args:
        audio_path: Caminho para o arquivo de áudio a ser transcrito
    """
    try:
        print(f"Testando transcrição do arquivo: {audio_path}")
        print("Isso pode levar alguns segundos na primeira execução (carregamento do modelo)...")
        
        # Verificar se o arquivo existe
        if not os.path.exists(audio_path):
            print(f"Erro: Arquivo não encontrado: {audio_path}")
            return
        
        # Transcrever o arquivo
        texto_transcrito = transcribe_file(audio_path, lang_hint="pt")
        
        print("\n=== RESULTADO DA TRANSCRIÇÃO ===")
        print(f"Arquivo: {audio_path}")
        print(f"Texto transcrito: '{texto_transcrito}'")
        print(f"Comprimento: {len(texto_transcrito)} caracteres")
        
        if not texto_transcrito:
            print("Atenção: Nenhum texto foi transcrito. Verifique se o áudio tem fala audível.")
        
        return texto_transcrito
        
    except Exception as e:
        print(f"Erro durante a transcrição: {e}")
        return None

def criar_audio_teste():
    """
    Cria um arquivo de áudio simples para teste usando TTS.
    """
    try:
        from app.core.tts import generate_audio
        
        texto_teste = "Olá, este é um teste de transcrição de áudio para texto."
        audio_path = "teste_audio.wav"
        
        print(f"Criando arquivo de áudio de teste: {audio_path}")
        generate_audio(texto_teste, audio_path)
        
        return audio_path
    except ImportError:
        print("Módulo TTS não encontrado. Você precisará fornecer um arquivo de áudio manualmente.")
        return None

if __name__ == "__main__":
    print("=== TESTE DE TRANSCRIÇÃO DE ÁUDIO ===")
    
    # Se não foi passado argumento, tentar criar áudio de teste
    if len(sys.argv) < 2:
        print("Nenhum arquivo de áudio especificado. Tentando criar áudio de teste...")
        audio_path = criar_audio_teste()
        if not audio_path:
            print("\nUso: python test_transcribe.py <caminho_para_arquivo_audio>")
            print("Formatos suportados: MP3, WAV, M4A, etc.")
            sys.exit(1)
    else:
        audio_path = sys.argv[1]
    
    # Executar o teste
    resultado = test_transcription(audio_path)
    
    if resultado:
        print("\n✅ Teste concluído com sucesso!")
    else:
        print("\n❌ Teste falhou.")