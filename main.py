import sys
import os
import logging
from datetime import datetime, timezone
import time
from collections import deque
import threading
from colorama import Fore, Style, init
from modules.utils.utils_logger import get_logger

# Inicializa o Colorama
init()

# Configurações de cores
INFO_COLOR = Fore.CYAN
SUCCESS_COLOR = Fore.GREEN
WARNING_COLOR = Fore.YELLOW
ERROR_COLOR = Fore.RED
RESET = Style.RESET_ALL

# Criar logger para o módulo main
logger = get_logger(__name__)

def print_header():
    """Imprime o cabeçalho do programa."""
    print(f"\n{INFO_COLOR}{'='*60}{RESET}")
    print(f"{INFO_COLOR}ChronusBOT-API - Twitch Stream Downloader{RESET}")
    print(f"{INFO_COLOR}{'='*60}{RESET}\n")

def log_session_details(bot_id, fingerprint):
    """Loga os detalhes da sessão atual."""
    logger.info("=== DETALHES DA SESSÃO ===")
    logger.info(f"Bot ID: {bot_id}")
    logger.info("Fingerprint:")
    for key, value in fingerprint.items():
        logger.info(f"  {key}: {value}")
    logger.info("========================")

def log_request_details(action, headers, params=None):
    """Loga os detalhes de uma requisição."""
    logger.info(f"=== DETALHES DA REQUISIÇÃO: {action} ===")
    logger.info("Headers:")
    for key, value in headers.items():
        logger.info(f"  {key}: {value}")
    if params:
        logger.info("Parâmetros:")
        for key, value in params.items():
            logger.info(f"  {key}: {value}")
    logger.info("========================")

def main():
    logger.info("Iniciando ChronusBOT-API")
    print_header()

    while True:
        try:
            canal_nome = input(f"{INFO_COLOR}Digite o nome do canal da Twitch: {RESET}")
            logger.info(f"Canal solicitado: {canal_nome}")
            
            # Nova entrada para o limite de anúncios
            while True:
                try:
                    limite_anuncios = int(input(f"{INFO_COLOR}Digite quantos anúncios deseja assistir (total): {RESET}"))
                    if limite_anuncios > 0:
                        break
                    print(f"{ERROR_COLOR}Por favor, digite um número maior que zero.{RESET}")
                except ValueError:
                    print(f"{ERROR_COLOR}Por favor, digite um número válido.{RESET}")
            
            logger.info(f"Limite de anúncios definido: {limite_anuncios}")
            
            print(f"{INFO_COLOR}Verificando se o canal está online...{RESET}")
            if not verificar_canal_online(canal_nome):
                logger.warning(f"Canal {canal_nome} não está online")
                print(f"{ERROR_COLOR}O canal {canal_nome} não está online no momento.{RESET}")
                continue
                
            logger.info(f"Canal {canal_nome} está online")
            print(f"{SUCCESS_COLOR}Canal {canal_nome} está online!{RESET}")
            bot_id = 1
            
            logger.info(f"Inicializando bot {bot_id} para o canal: {canal_nome}")
            print(f"{INFO_COLOR}Inicializando bot para o canal: {canal_nome}{RESET}")
            
            sessao_tentativas = 0
            max_sessoes = 3
            sucesso = False
            
            while sessao_tentativas < max_sessoes and not sucesso:
                if sessao_tentativas > 0:
                    logger.info(f"Iniciando nova sessão ({sessao_tentativas + 1} de {max_sessoes})")
                    session_manager.close_session(bot_id)
                    fingerprint = get_fingerprint()
                else:
                    fingerprint = session_manager.get_fingerprint(bot_id)
                    if not fingerprint:
                        fingerprint = get_fingerprint()
                
                log_session_details(bot_id, fingerprint)
                
                tentativas_conexao = 0
                max_tentativas_conexao = 3
                
                while tentativas_conexao < max_tentativas_conexao and not sucesso:
                    try:
                        if tentativas_conexao > 0:
                            logger.info(f"Tentativa {tentativas_conexao + 1} de {max_tentativas_conexao}")
                            time.sleep(5)
                        
                        # Log da requisição do token
                        from modules.core.core_token import get_playback_access_token_headers
                        token_headers = get_playback_access_token_headers(fingerprint)
                        log_request_details("Obter Token", token_headers)
                        
                        token_data = obter_playback_access_token(canal_nome, fingerprint, bot_id)
                        if token_data:
                            logger.info("Token de acesso obtido com sucesso")
                            logger.debug(f"Token data: {token_data}")
                            
                            # Log da requisição da playlist
                            playlist_headers = {
                                "User-Agent": fingerprint.get('User-Agent'),
                                "Client-ID": fingerprint.get('Client-Id'),
                                "X-Device-Id": fingerprint.get('Device-Id')
                            }
                            playlist_params = {
                                "player": "twitchweb",
                                "token": token_data['value'],
                                "sig": token_data['signature'],
                                # ... outros parâmetros ...
                            }
                            log_request_details("Obter Playlist", playlist_headers, playlist_params)
                            
                            playlist = obter_playlist_m3u8(canal_nome, token_data, bot_id)
                            if playlist:
                                logger.info("Playlist M3U8 obtida com sucesso")
                                logger.debug(f"Primeira parte da playlist: {playlist[:500]}")
                                
                                # Log de duas atualizações de playlist
                                for i in range(2):
                                    logger.info(f"Atualizando playlist - Tentativa {i+1}")
                                    log_request_details(f"Atualizar Playlist {i+1}", playlist_headers, playlist_params)
                                    resultado = atualizar_playlist(canal_nome, token_data, bot_id, limite_anuncios=limite_anuncios)
                                    time.sleep(2)  # Espera entre atualizações
                                
                                if resultado:
                                    sucesso = True
                                else:
                                    raise Exception("Falha ao atualizar playlist")
                            else:
                                raise Exception("Falha ao obter playlist M3U8")
                        else:
                            raise Exception("Falha ao obter token de acesso")

                    except Exception as e:
                        logger.error(f"Erro na tentativa {tentativas_conexao + 1}: {str(e)}")
                        tentativas_conexao += 1
                
                if not sucesso:
                    sessao_tentativas += 1

            if not sucesso:
                logger.error(f"Falha após {max_sessoes} tentativas de sessão diferentes")

        except KeyboardInterrupt:
            logger.info("Programa encerrado pelo usuário")
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
        from modules.utils.utils_stream_checker import verificar_canal_online
        from modules.utils.utils_ads_detector import create_ad_detector
    except ImportError as e:
        print(f"{ERROR_COLOR}Erro ao importar módulos: {e}{RESET}")
        sys.exit(1)

    main()