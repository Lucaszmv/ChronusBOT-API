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
from modules.utils.utils_bot_monitor import get_bot_monitor, BotStatus
from modules.core.core_session import session_manager
from modules.utils.utils_proxy_manager import ProxyManager
from modules.utils.utils_terminal_menu import create_terminal_menu

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

# Variáveis globais para estatísticas
menu = create_terminal_menu()
stats_lock = threading.Lock()
global_stats = {
    'channels': 0,
    'completed': '0/0',
    'threads': 0,
    'proxies': 0,
    'ads_per_hour': 0.0
}
bot_stats = []

# Adicione estas variáveis globais no início do arquivo
preroll_anuncios = 0
midroll_anuncios = 0
anuncios_lock = Lock()

# Adicione estas variáveis globais para cada bot
bot_anuncios = {}  # Dicionário para armazenar contadores de cada bot

def update_bot_ip(bot_id: int, ip: str):
    """Atualiza o IP do bot nas estatísticas."""
    with stats_lock:
        for bot in bot_stats:
            if bot['id'] == bot_id:
                bot['proxy_ip'] = ip
                logger.info("", extra={
                    'bot_id': bot_id,
                    'message': f"IP atualizado para: {ip}"
                })
                return

def print_header():
    """Imprime o cabeçalho do programa."""
    pass  # Removido pois agora usamos o menu

def log_session_details(bot_id, session):
    """Loga detalhes completos da sessão."""
    logger.info("", extra={
        'session_details': {
            'fingerprint': session.fingerprint,
            'proxy': session.proxy,
            'user_agent': session.headers.get('User-Agent'),
            'client_id': session.headers.get('Client-ID')
        }
    })

def log_request_details(method, url, headers_sent, response):
    """Loga detalhes completos da requisição e resposta."""
    logger.info("", extra={
        'request_details': {
            'method': method,
            'url': url,
            'headers_sent': headers_sent,
            'headers_received': dict(response.headers),
            'status_code': response.status_code,
            'reason': response.reason,
            'response': response.text
        }
    })

def check_anuncios_limit(ads_viewed, is_preroll=False, bot_id=None):
    """Verifica se o limite global de anúncios foi atingido e atualiza contadores por bot."""
    global total_anuncios_global, limite_anuncios_global
    
    with anuncios_lock:
        # Inicializa contadores para o bot se não existirem
        if bot_id not in bot_anuncios:
            bot_anuncios[bot_id] = {'preroll': 0, 'midroll': 0}
        
        # Atualiza contadores do bot específico
        if is_preroll:
            bot_anuncios[bot_id]['preroll'] += ads_viewed
        else:
            bot_anuncios[bot_id]['midroll'] += ads_viewed
            
        # Atualiza total global
        total_anuncios_global += ads_viewed
        
        # Atualiza o status do bot com seus próprios valores
        for bot in bot_stats:
            if bot['id'] == bot_id:
                bot['ads'] = f"{bot_anuncios[bot_id]['preroll']}/{bot_anuncios[bot_id]['midroll']}"
                break
        
        if total_anuncios_global >= limite_anuncios_global:
            should_stop.set()
            return True
    return False

def update_menu():
    """Thread para atualizar o menu periodicamente"""
    monitor = get_bot_monitor()
    
    while not should_stop.is_set():
        with stats_lock:
            # Atualiza IPs dos bots
            for bot in bot_stats:
                bot_status = monitor.get_bot_status(bot['id'])
                if bot_status.get('user_ip'):
                    bot['user_ip'] = bot_status['user_ip']
            
            # Calcula o total de pre/mid rolls de todos os bots
            total_preroll = sum(bot['preroll'] for bot in bot_anuncios.values())
            total_midroll = sum(bot['midroll'] for bot in bot_anuncios.values())
            
            global_stats.update({
                'channels': 1,
                'completed': f"{total_anuncios_global}/{limite_anuncios_global}",
                'threads': len(bot_stats),
                'proxies': len(ProxyManager().proxies),
                'ads_per_hour': f"{total_preroll}/{total_midroll}"
            })
            
            menu.render(global_stats, bot_stats)
        
        time.sleep(1)

def bot_worker(canal_nome: str, bot_id: int):
    """Função que executa o trabalho de cada bot em sua própria thread."""
    monitor = get_bot_monitor()
    failure_mgr = get_failure_manager()
    
    # Inicializa contadores para este bot
    bot_anuncios[bot_id] = {'preroll': 0, 'midroll': 0}
    
    # Adiciona estatísticas iniciais do bot
    with stats_lock:
        bot_stats.append({
            'id': bot_id,
            'status': 'ONLINE',
            'channel': canal_nome,
            'ads': '0/0',  # Formato preroll/midroll
            'uptime': '0h 00m',
            'start_time': datetime.now(),
            'user_ip': 'Waiting IP...'  # Inicializa com Waiting IP...
        })
    
    def update_bot_status(status: str, ads: str = None):
        """Atualiza o status do bot no menu"""
        with stats_lock:
            for bot in bot_stats:
                if bot['id'] == bot_id:
                    bot['status'] = status
                    if ads:
                        bot['ads'] = ads
                    
                    # Obtém status atual do monitor
                    bot_status = monitor.get_bot_status(bot_id)
                    if bot_status.get('user_ip'):
                        bot['user_ip'] = bot_status['user_ip']
                    break

    def check_and_update_ip():
        """Verifica e atualiza o IP periodicamente"""
        with stats_lock:
            bot_status = monitor.get_bot_status(bot_id)
            if bot_status.get('user_ip'):
                for bot in bot_stats:
                    if bot['id'] == bot_id:
                        bot['user_ip'] = bot_status['user_ip']
                        break

    def add_bot_event(message: str, event_type: str = 'info'):
        """Adiciona um evento do bot ao menu"""
        menu.add_event(bot_id, message, event_type)
    
    def reiniciar_sessao(motivo: str):
        """Função interna para reiniciar a sessão completamente"""
        logger.warning(f"BOT {bot_id}: Reiniciando sessão - Motivo: {motivo}")
        monitor.update_status(bot_id, "Reiniciando sessão", motivo)
        
        # Fecha sessão atual
        session_manager.close_session(bot_id)
        
        # Gera novo fingerprint
        fingerprint = get_fingerprint()
        
        # Cria nova sessão (que já vai obter novo proxy)
        session = session_manager.get_session(bot_id)
        if not session:
            logger.error(f"BOT {bot_id}: Falha ao criar nova sessão")
            return False
            
        # Reseta contadores de erro
        failure_mgr.reset_stats(bot_id)
        return True

    while not should_stop.is_set():
        try:
            update_bot_status('ONLINE')
            check_and_update_ip()  # Verifica IP
            
            # Primeira configuração da sessão
            if not reiniciar_sessao("Iniciando bot"):
                time.sleep(5)
                continue
                
            # Obtém token
            fingerprint = session_manager.get_fingerprint(bot_id)
            token_data = obter_playback_access_token(canal_nome, fingerprint, bot_id)
            if token_data:
                check_and_update_ip()  # Verifica IP após obter token
            
            # Loop principal de atualização
            while not should_stop.is_set():
                try:
                    monitor.update_status(bot_id, BotStatus.ASSISTINDO, f"Canal: {canal_nome}")
                    
                    resultado = atualizar_playlist(canal_nome, token_data, bot_id,
                                                 limite_anuncios=None,
                                                 check_limit_callback=check_anuncios_limit)
                    
                    if resultado is False:  # Se retornou False, precisa reiniciar sessão
                        update_bot_status('RECONECT')
                        add_bot_event("Reiniciando sessão", 'warning')
                        reiniciar_sessao("Fila vazia persistente após tentativas de recuperação")
                        break
                    elif resultado is None:  # Se retornou None, teve erro
                        erros_consecutivos += 1
                        time.sleep(2)
                        continue
                    
                    # Sucesso - reseta contadores
                    erros_consecutivos = 0
                    ultima_atualizacao = time.time()
                    failure_mgr.register_success(bot_id)
                    
                    time.sleep(1)
                    
                except Exception as e:
                    update_bot_status('ERRO')
                    add_bot_event(f"Erro: {str(e)}", 'error')
                    logger.error(f"BOT {bot_id}: Erro na atualização: {str(e)}")
                    erros_consecutivos += 1
                    
        except Exception as e:
            update_bot_status('ERRO')
            add_bot_event(f"Erro: {str(e)}", 'error')
            logger.error(f"BOT {bot_id}: Erro crítico: {str(e)}")
            time.sleep(5)

def main():
    global limite_anuncios_global
    
    try:
        canal_nome = input("Digite o nome do canal da Twitch: ")
        logger.info(f"Canal solicitado: {canal_nome}")
        
        while True:
            try:
                num_bots = int(input("Digite o número de bots desejado: "))
                if num_bots > 0:
                    break
                print("Por favor, digite um número maior que zero.")
            except ValueError:
                print("Por favor, digite um número válido.")
        
        while True:
            try:
                limite_anuncios_global = int(input("Digite o limite total de anúncios para todos os bots: "))
                if limite_anuncios_global > 0:
                    break
                print("Por favor, digite um número maior que zero.")
            except ValueError:
                print("Por favor, digite um número válido.")
        
        if not verificar_canal_online(canal_nome):
            return
        
        # Inicia thread do menu
        menu_thread = threading.Thread(target=update_menu)
        menu_thread.daemon = True
        menu_thread.start()
        
        # Iniciar múltiplos bots em threads
        with ThreadPoolExecutor(max_workers=num_bots) as executor:
            futures = [executor.submit(bot_worker, canal_nome, bot_id) 
                      for bot_id in range(1, num_bots + 1)]
            
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