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
            
            # Verifica se o canal está online
            print(f"{INFO_COLOR}Verificando se o canal está online...{RESET}")
            if not verificar_canal_online(canal_nome):
                print(f"{ERROR_COLOR}O canal {canal_nome} não está online no momento.{RESET}")
                continue
                
            print(f"{SUCCESS_COLOR}Canal {canal_nome} está online!{RESET}")
            bot_id = 1
            
            print(f"{INFO_COLOR}Inicializando bot para o canal: {canal_nome}{RESET}")
            
            sessao_tentativas = 0
            max_sessoes = 3  # Número máximo de sessões diferentes a tentar
            sucesso = False
            
            while sessao_tentativas < max_sessoes and not sucesso:
                # Inicializa ou reinicializa sessão
                if sessao_tentativas > 0:
                    print(f"{WARNING_COLOR}Iniciando nova sessão ({sessao_tentativas + 1} de {max_sessoes})...{RESET}")
                    session_manager.close_session(bot_id)
                    fingerprint = get_fingerprint()
                else:
                    fingerprint = session_manager.get_fingerprint(bot_id)
                    if not fingerprint:
                        fingerprint = get_fingerprint()
                
                # Tenta 3 vezes com a mesma sessão
                tentativas_conexao = 0
                max_tentativas_conexao = 3
                
                while tentativas_conexao < max_tentativas_conexao and not sucesso:
                    try:
                        if tentativas_conexao > 0:
                            print(f"{WARNING_COLOR}Tentativa {tentativas_conexao + 1} de {max_tentativas_conexao} com a sessão atual...{RESET}")
                            time.sleep(5)
                        
                        token_data = obter_playback_access_token(canal_nome, fingerprint, bot_id)
                        if token_data:
                            print(f"{SUCCESS_COLOR}Token de acesso obtido com sucesso!{RESET}")
                            
                            playlist = obter_playlist_m3u8(canal_nome, token_data, bot_id)
                            if playlist:
                                print(f"{SUCCESS_COLOR}Playlist M3U8 obtida com sucesso!{RESET}")
                                print(f"{INFO_COLOR}Iniciando download dos segmentos...{RESET}")
                                
                                print(f"{INFO_COLOR}Iniciando atualização contínua da playlist...{RESET}")
                                resultado = atualizar_playlist(canal_nome, token_data, bot_id)
                                
                                if resultado:
                                    sucesso = True
                                else:
                                    raise Exception("Falha ao atualizar playlist")
                            else:
                                raise Exception("Falha ao obter playlist M3U8")
                        else:
                            raise Exception("Falha ao obter token de acesso")

                    except Exception as e:
                        tentativas_conexao += 1
                        if tentativas_conexao < max_tentativas_conexao:
                            print(f"{WARNING_COLOR}Erro: {e}. Tentando novamente...{RESET}")
                        else:
                            print(f"{ERROR_COLOR}Todas as tentativas falharam com a sessão atual. Último erro: {e}{RESET}")
                
                if not sucesso:
                    sessao_tentativas += 1

            if not sucesso:
                print(f"{ERROR_COLOR}Não foi possível estabelecer conexão após tentar com {max_sessoes} sessões diferentes.{RESET}")
                time.sleep(2)

        except KeyboardInterrupt:
            print(f"\n{INFO_COLOR}Encerrando o programa...{RESET}")
            logging.info("Programa encerrado pelo usuário.")
            session_manager.close_all()
            break

if __name__ == "__main__":
    try:
        # Importações dos módulos
        from modules.core.core_fingerprint import get_fingerprint
        from modules.core.core_get_playlist import obter_playlist_m3u8
        from modules.core.core_token import obter_playback_access_token
        from modules.core.core_session import session_manager
        from modules.utils.utils_update_playlist import atualizar_playlist
        from modules.utils.utils_segment_download import iniciar_downloader
        from modules.utils.twitch_stream_checker import verificar_canal_online
    except ImportError as e:
        print(f"{ERROR_COLOR}Erro ao importar módulos: {e}{RESET}")
        sys.exit(1)

    main()