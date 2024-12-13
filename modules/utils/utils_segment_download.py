"""
Módulo para download e gerenciamento de segmentos de stream da Twitch.
"""
import os
import sys
from pathlib import Path
import time
import random
import logging
import requests
from collections import deque
from colorama import Fore, Style, init
from datetime import datetime, timezone
from typing import Optional
from modules.utils.utils_rate_limiter import get_rate_limiter

# Adiciona o diretório raiz do projeto ao PYTHONPATH
root_dir = str(Path(__file__).parent.parent.parent)
sys.path.append(root_dir)

# Importações dos módulos core
try:
    from modules.core.core_session import session_manager
except ImportError as e:
    print(f"Erro ao importar módulos: {e}")
    sys.exit(1)

# Inicializa o Colorama
init()

# Configurações de cores
INFO_COLOR = Fore.CYAN
SUCCESS_COLOR = Fore.GREEN
WARNING_COLOR = Fore.YELLOW
ERROR_COLOR = Fore.RED
RESET = Style.RESET_ALL

# Configurações de buffer
WAIT_TIME = lambda: random.uniform(0.10, 0.20) 

# Conjunto para armazenar os segmentos já baixados
segmentos_baixados = set()

logger = logging.getLogger(__name__)

def simular_download_segmento(url, bot_id=None):
    """Simula o download de um segmento de stream."""
    rate_limiter = get_rate_limiter()
    
    try:
        if not rate_limiter.acquire(bot_id, 'segment'):
            logger.warning(f"BOT {bot_id}: Limite de downloads atingido, aguardando...")
            time.sleep(1)
            return False
            
        inicio = url.find('https://')
        if inicio == -1 or not url.endswith('.ts'):
            return False
            
        url = url[inicio:]
        session = session_manager.get_session(bot_id) if bot_id else requests.Session()
        fingerprint = session_manager.get_fingerprint(bot_id) if bot_id else {}
        
        headers = {
            'Accept': '*/*',
            'Accept-Encoding': fingerprint.get('Accept-Encoding'),
            'Accept-Language': fingerprint.get('Accept-Language'),
            'Connection': 'keep-alive',
            'Origin': 'https://www.twitch.tv',
            'Priority': 'u=4',
            'Referer': 'https://www.twitch.tv/',
            'Sec-Fetch-Dest': 'empty',
            'Sec-Fetch-Mode': 'cors',
            'Sec-Fetch-Site': 'cross-site',
            'User-Agent': fingerprint.get('User-Agent')
        }

        response = session.head(url, headers=headers, timeout=5)
        if response.status_code == 200:
            print(f"{SUCCESS_COLOR}BOT {bot_id}: Segmento baixado: {url[:70]}...{RESET}")
            return True
            
        print(f"{ERROR_COLOR}BOT {bot_id}: Falha ao baixar segmento (HTTP {response.status_code}): {url}{RESET}")
        return False

    except Exception as e:
        print(f"{ERROR_COLOR}BOT {bot_id}: Erro ao baixar segmento: {str(e)}{RESET}")
        return False

    finally:
        rate_limiter.release(bot_id, 'segment')

def processar_fila_download(fila_segmentos: deque, bot_id: int = None):
    """Processa a fila de download de segmentos."""
    segmentos_processados = 0
    
    while True:
        queue_size = len(fila_segmentos)
        
        if queue_size == 0:
            print(f"{WARNING_COLOR}BOT {bot_id}: Fila de segmentos vazia. Aguardando...{RESET}")
            time.sleep(0.5)
            continue

        url = fila_segmentos[0]
        print(f"{INFO_COLOR}BOT {bot_id}: Baixando: {url[:50]}...{RESET}")

        success = simular_download_segmento(url, bot_id)
        
        if success:
            segmentos_baixados.add(url)
            fila_segmentos.popleft()
            segmentos_processados += 1
            print(f"{Fore.WHITE}BOT {bot_id}: Segmentos processados: {segmentos_processados}{RESET}")
        else:
            print(f"{ERROR_COLOR}BOT {bot_id}: Falha ao baixar segmento{RESET}")
            time.sleep(1)

        wait_time = WAIT_TIME()
        print(f"{INFO_COLOR}BOT {bot_id}: Próximo download em: {wait_time:.2f}s | Fila: {queue_size} segmentos{RESET}")
        time.sleep(wait_time)

def iniciar_downloader(fila_segmentos: deque, bot_id: int = None):
    """Inicia o processamento da fila de download em uma thread separada."""
    import threading
    thread_downloader = threading.Thread(target=processar_fila_download, args=(fila_segmentos, bot_id))
    thread_downloader.daemon = True
    thread_downloader.start()
    print(f"{INFO_COLOR}BOT {bot_id}: Simulador de download iniciado em thread separada{RESET}")
