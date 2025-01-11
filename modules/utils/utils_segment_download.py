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

# Fila para garantir ordem sequencial dos segmentos
segmentos_fila = deque(maxlen=100)

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
        
        # Verifica se é o próximo segmento na sequência
        if len(segmentos_fila) > 0 and url != segmentos_fila[0]:
            logger.warning(f"BOT {bot_id}: Segmento fora de ordem, aguardando...")
            return False
            
        # Se já baixou, não precisa baixar novamente
        if url in segmentos_baixados:
            segmentos_fila.popleft()  # Remove da fila pois já foi processado
            return True
            
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

        response = session.get(url, headers=headers, timeout=5)
        if response.status_code == 200:
            segmentos_baixados.add(url)
            segmentos_fila.popleft()  # Remove da fila após download bem sucedido
            return True
        return False

    except Exception as e:
        logger.error(f"BOT {bot_id}: Erro ao baixar segmento: {str(e)}")
        return False

    finally:
        rate_limiter.release(bot_id, 'segment')

def processar_fila_download(fila_segmentos: deque, bot_id: int = None):
    """Processa a fila de download de segmentos."""
    # Tempos de espera base (em segundos)
    WAIT_NORMAL = lambda: random.uniform(0.10, 0.20)
    WAIT_FAST = lambda: random.uniform(0.02, 0.05)  # Tempo reduzido quando a fila está cheia
    
    while True:
        queue_size = len(fila_segmentos)
        
        if queue_size == 0:
            time.sleep(0.5)
            continue

        # Determina o tempo de espera baseado no tamanho da fila
        if queue_size > 50:  # 50% da capacidade
            logger.warning(f"BOT {bot_id}: Fila com {queue_size} segmentos. Acelerando downloads...")
            wait_time = WAIT_FAST()
        else:
            wait_time = WAIT_NORMAL()
            
        url = fila_segmentos[0]
        success = simular_download_segmento(url, bot_id)
        
        if success:
            segmentos_baixados.add(url)
            fila_segmentos.popleft()
        else:
            time.sleep(1)

        time.sleep(wait_time)

def iniciar_downloader(fila_segmentos: deque, bot_id: int = None):
    """Inicia o processamento da fila de download em uma thread separada."""
    import threading
    thread_downloader = threading.Thread(target=processar_fila_download, args=(fila_segmentos, bot_id))
    thread_downloader.daemon = True
    thread_downloader.start()

def adicionar_segmento_fila(url):
    """Adiciona um novo segmento à fila para download."""
    if url not in segmentos_baixados and url not in segmentos_fila:
        segmentos_fila.append(url)
