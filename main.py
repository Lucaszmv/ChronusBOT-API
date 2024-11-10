import sys
import os
import logging
from datetime import datetime, timezone
import time
from collections import deque
import threading
from colorama import Fore, Style, init

# Inicializa o Colorama
init()

# Configurações de cores
INFO_COLOR = Fore.CYAN
SUCCESS_COLOR = Fore.GREEN
WARNING_COLOR = Fore.YELLOW
ERROR_COLOR = Fore.RED
RESET = Style.RESET_ALL

def configurar_logging():
    """Configura o sistema de logging com formatação colorida."""
    log_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'logs')
    os.makedirs(log_dir, exist_ok=True)
    log_file = os.path.join(log_dir, f'main_{datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")}.log')

    # Formatador personalizado para console
    class ColoredFormatter(logging.Formatter):
        def format(self, record):
            if record.levelno == logging.INFO:
                record.msg = f"{INFO_COLOR}{record.msg}{RESET}"
            elif record.levelno == logging.WARNING:
                record.msg = f"{WARNING_COLOR}{record.msg}{RESET}"
            elif record.levelno == logging.ERROR:
                record.msg = f"{ERROR_COLOR}{record.msg}{RESET}"
            return super().format(record)

    # Configuração básica para arquivo
    logging.basicConfig(
        filename=log_file,
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )

    # Handler para console com cores
    console = logging.StreamHandler()
    console.setLevel(logging.INFO)
    console.setFormatter(ColoredFormatter('%(asctime)s - %(message)s'))
    logging.getLogger('').addHandler(console)

def print_header():
    """Imprime o cabeçalho do programa."""
    print(f"\n{INFO_COLOR}{'='*60}{RESET}")
    print(f"{INFO_COLOR}ChronusBOT-API - Twitch Stream Downloader{RESET}")
    print(f"{INFO_COLOR}{'='*60}{RESET}\n")

def main():
    configurar_logging()
    print_header()

    while True:
        try:
            canal_nome = input(f"{INFO_COLOR}Digite o nome do canal da Twitch: {RESET}")
            bot_id = 1
            
            print(f"{INFO_COLOR}Inicializando bot para o canal: {canal_nome}{RESET}")
            
            fingerprint = session_manager.get_fingerprint(bot_id)
            if not fingerprint:
                fingerprint = get_fingerprint()
            
            # Obtendo token de acesso
            token_data = obter_playback_access_token(canal_nome, fingerprint, bot_id)
            if token_data:
                print(f"{SUCCESS_COLOR}Token de acesso obtido com sucesso!{RESET}")
                
                # Obtendo playlist M3U8
                playlist = obter_playlist_m3u8(canal_nome, token_data, bot_id)
                if playlist:
                    print(f"{SUCCESS_COLOR}Playlist M3U8 obtida com sucesso!{RESET}")
                    print(f"{INFO_COLOR}Iniciando download dos segmentos...{RESET}")
                    
                    # Iniciar processo de atualização de playlist
                    print(f"{INFO_COLOR}Iniciando atualização contínua da playlist...{RESET}")
                    resultado = atualizar_playlist(canal_nome, token_data, bot_id)
                    
                    if not resultado:
                        print(f"{ERROR_COLOR}Falha ao atualizar playlist{RESET}")
                else:
                    print(f"{ERROR_COLOR}Falha ao obter playlist M3U8{RESET}")
            else:
                print(f"{ERROR_COLOR}Falha ao obter token de acesso{RESET}")

        except KeyboardInterrupt:
            print(f"\n{INFO_COLOR}Encerrando o programa...{RESET}")
            logging.info("Programa encerrado pelo usuário.")
            session_manager.close_all()
            break
        except Exception as e:
            print(f"{ERROR_COLOR}Erro durante a execução: {e}{RESET}")
            time.sleep(5)

if __name__ == "__main__":
    try:
        # Importações dos módulos
        from modules.core.core_fingerprint import get_fingerprint
        from modules.core.core_get_playlist import obter_playlist_m3u8
        from modules.core.core_token import obter_playback_access_token
        from modules.core.core_session import session_manager
        from modules.utils.utils_update_playlist import atualizar_playlist
        from modules.utils.utils_segment_download import iniciar_downloader
    except ImportError as e:
        print(f"{ERROR_COLOR}Erro ao importar módulos: {e}{RESET}")
        sys.exit(1)

    main()