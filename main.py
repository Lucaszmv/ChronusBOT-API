import sys
import os
import logging
from datetime import datetime, timezone
import time
from collections import deque
import threading
from colorama import Fore, Style, init
from modules.utils.utils_logger import get_logger
from concurrent.futures import ThreadPoolExecutor
from threading import Lock
from modules.utils.utils_failure_manager import get_failure_manager

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

# Lock global para contagem de anúncios
anuncios_lock = Lock()
total_anuncios_global = 0
limite_anuncios_global = 0
should_stop = threading.Event()

def print_header():
    """Imprime o cabeçalho do programa."""
    print(f"\n{INFO_COLOR}{'='*60}{RESET}")
    print(f"{INFO_COLOR}ChronusBOT-API - Twitch Stream Downloader{RESET}")
    print(f"{INFO_COLOR}{'='*60}{RESET}\n")

def log_session_details(bot_id, fingerprint):
    """Loga os detalhes da sessão atual."""
    logger.info(f"=== DETALHES DA SESSÃO DO BOT {bot_id} ===")
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

def check_anuncios_limit(ads_viewed):
    """Verifica se o limite global de anúncios foi atingido."""
    global total_anuncios_global, limite_anuncios_global
    with anuncios_lock:
        antigo_total = total_anuncios_global
        total_anuncios_global += ads_viewed
        logger.info(f"Anúncios: {antigo_total} -> {total_anuncios_global} (+{ads_viewed})")
        
        # Cria o diretório de logs se não existir
        log_dir = os.path.join(os.path.dirname(__file__), 'logs')
        os.makedirs(log_dir, exist_ok=True)
        
        # Nome do arquivo com timestamp
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        log_file = os.path.join(log_dir, f'progresso_anuncios_{timestamp}.txt')
        
        # Salva o progresso no arquivo
        with open(log_file, 'a', encoding='utf-8') as f:
            progresso = f"Progresso: {total_anuncios_global}/{limite_anuncios_global} anúncios"
            f.write(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {progresso}\n")
        
        logger.info(f"Progresso: {total_anuncios_global}/{limite_anuncios_global} anúncios")
        
        if total_anuncios_global >= limite_anuncios_global:
            mensagem = f"Limite máximo de {limite_anuncios_global} anúncios atingido!"
            logger.warning(mensagem)
            with open(log_file, 'a', encoding='utf-8') as f:
                f.write(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {mensagem}\n")
            should_stop.set()
            return True
    return False

def bot_worker(canal_nome: str, bot_id: int):
    """Função que executa o trabalho de cada bot em sua própria thread."""
    logger.info(f"Iniciando BOT {bot_id} para o canal: {canal_nome}")
    
    sessao_tentativas = 0
    max_sessoes = 3
    sucesso = False
    failure_mgr = get_failure_manager()
    
    while sessao_tentativas < max_sessoes and not sucesso and not should_stop.is_set():
        try:
            if sessao_tentativas > 0 or failure_mgr.should_restart_session(bot_id):
                logger.info(f"BOT {bot_id}: Iniciando nova sessão ({sessao_tentativas + 1} de {max_sessoes})")
                session_manager.close_session(bot_id)
                fingerprint = get_fingerprint()
                failure_mgr.reset_stats(bot_id)
            else:
                fingerprint = session_manager.get_fingerprint(bot_id)
                if not fingerprint:
                    fingerprint = get_fingerprint()
            
            # Obtém token
            token_data = obter_playback_access_token(canal_nome, fingerprint, bot_id)
            if not token_data:
                if failure_mgr.register_failure(bot_id, "Falha ao obter token de acesso"):
                    continue
                time.sleep(5)
                continue
            
            # Log detalhado do token obtido
            logger.info(f"""
BOT {bot_id}: Token obtido com sucesso:
- Signature: {token_data['signature'][:30]}...
- Token Value: {token_data['value'][:30]}...
""")
            failure_mgr.register_success(bot_id)
            
            # Obtém playlist
            playlist = obter_playlist_m3u8(canal_nome, token_data, bot_id)
            if not playlist:
                if failure_mgr.register_failure(bot_id, "Falha ao obter playlist M3U8"):
                    continue
                time.sleep(5)
                continue
            
            # Log detalhado da playlist obtida
            playlist_lines = playlist.split('\n')
            logger.info(f"""
BOT {bot_id}: Playlist M3U8 obtida com sucesso:
- Total de linhas: {len(playlist_lines)}
- Primeiras linhas:
{chr(10).join(['  ' + line for line in playlist_lines[:5]])}
...
""")
            failure_mgr.register_success(bot_id)
            
            resultado = atualizar_playlist(canal_nome, token_data, bot_id, 
                                         limite_anuncios=None,
                                         check_limit_callback=check_anuncios_limit)
            
            if resultado:
                sucesso = True
                failure_mgr.register_success(bot_id)
            else:
                if failure_mgr.register_failure(bot_id, "Falha ao atualizar playlist"):
                    continue

        except Exception as e:
            if failure_mgr.register_failure(bot_id, str(e)):
                continue
            time.sleep(5)
        
        if not sucesso:
            sessao_tentativas += 1

    if not sucesso:
        logger.error(f"BOT {bot_id}: Falha após {max_sessoes} tentativas de sessão diferentes")
        logger.error(f"BOT {bot_id}: Resumo de falhas:\n{failure_mgr.get_failure_summary(bot_id)}")

def main():
    global limite_anuncios_global
    
    logger.info("Iniciando ChronusBOT-API")
    print_header()

    try:
        canal_nome = input(f"{INFO_COLOR}Digite o nome do canal da Twitch: {RESET}")
        logger.info(f"Canal solicitado: {canal_nome}")
        
        while True:
            try:
                num_bots = int(input(f"{INFO_COLOR}Digite o número de bots desejado: {RESET}"))
                if num_bots > 0:
                    break
                print(f"{ERROR_COLOR}Por favor, digite um número maior que zero.{RESET}")
            except ValueError:
                print(f"{ERROR_COLOR}Por favor, digite um número válido.{RESET}")
        
        while True:
            try:
                limite_anuncios_global = int(input(f"{INFO_COLOR}Digite o limite total de anúncios para todos os bots: {RESET}"))
                if limite_anuncios_global > 0:
                    break
                print(f"{ERROR_COLOR}Por favor, digite um número maior que zero.{RESET}")
            except ValueError:
                print(f"{ERROR_COLOR}Por favor, digite um número válido.{RESET}")
        
        print(f"{INFO_COLOR}Verificando se o canal está online...{RESET}")
        if not verificar_canal_online(canal_nome):
            logger.warning(f"Canal {canal_nome} não está online")
            print(f"{ERROR_COLOR}O canal {canal_nome} não está online no momento.{RESET}")
            return
        
        logger.info(f"Canal {canal_nome} está online")
        print(f"{SUCCESS_COLOR}Canal {canal_nome} está online!{RESET}")
        
        # Iniciar múltiplos bots em threads
        with ThreadPoolExecutor(max_workers=num_bots) as executor:
            futures = [executor.submit(bot_worker, canal_nome, bot_id) 
                      for bot_id in range(1, num_bots + 1)]
            
            # Aguardar todas as threads terminarem
            for future in futures:
                try:
                    future.result()
                except Exception as e:
                    logger.error(f"Erro em thread de bot: {str(e)}")

    except KeyboardInterrupt:
        logger.info("Programa encerrado pelo usuário")
        should_stop.set()
    finally:
        session_manager.close_all()

if __name__ == "__main__":
    try:
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