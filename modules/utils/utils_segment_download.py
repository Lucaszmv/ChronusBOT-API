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
    max_tentativas = 3  # Número de tentativas antes de desistir
    tentativa = 0
    
    while tentativa < max_tentativas:
        try:
            if not rate_limiter.acquire(bot_id, 'segment'):
                logger.warning(f"BOT {bot_id}: Limite de downloads atingido, aguardando...")
                time.sleep(1)
                continue
                
            session = session_manager.get_session(bot_id)
            response = session.get(url, timeout=5)
            
            if response.status_code == 200:
                # Extrair apenas o nome do arquivo do segmento
                segment_name = url.split('/')[-1].split('?')[0]
                segment_name = segment_name.split('.ts')[0][-80:] + '.ts'
                # Adiciona timestamp
                timestamp = datetime.now().strftime("%H:%M:%S")
                print(f"[BOT {bot_id}][{timestamp}] Segmento baixado com sucesso: {segment_name}")
                # Log completo vai para o arquivo
                logger.debug(f"BOT {bot_id}: Segmento baixado com sucesso: {url}")
                segmentos_baixados.add(url)
                return True
                
        except requests.exceptions.Timeout:
            tentativa += 1
            wait_time = 2 ** tentativa  # Backoff exponencial: 2s, 4s, 8s
            logger.warning(f"BOT {bot_id}: Timeout ao baixar segmento (tentativa {tentativa}/{max_tentativas}). "
                         f"Aguardando {wait_time}s antes de tentar novamente...")
            time.sleep(wait_time)
            continue
            
        except Exception as e:
            tentativa += 1
            logger.error(f"BOT {bot_id}: Erro ao baixar segmento: {str(e)}")
            time.sleep(2)
            continue
            
        finally:
            rate_limiter.release(bot_id)
            
    # Só fecha a sessão se todas as tentativas falharem
    if tentativa >= max_tentativas:
        logger.error(f"BOT {bot_id}: Todas as tentativas de download falharam. Reiniciando sessão...")
        session_manager.close_session(bot_id)
        return False
        
    return True

def processar_fila_download(fila_segmentos: deque, bot_id: int = None):
    """Processa a fila de download de segmentos."""
    # Tempos de espera base (em segundos)
    WAIT_NORMAL = lambda: random.uniform(0.10, 0.20)
    WAIT_FAST = lambda: random.uniform(0.02, 0.05)
    
    while True:
        try:
            # Verifica se a fila está vazia
            if not fila_segmentos:
                time.sleep(0.5)
                continue

            # Determina o tempo de espera baseado no tamanho da fila
            queue_size = len(fila_segmentos)
            if queue_size > 50:
                logger.info(f"BOT {bot_id}: Fila com {queue_size} segmentos. Acelerando downloads...")
                wait_time = WAIT_FAST()
            else:
                wait_time = WAIT_NORMAL()
            
            # Tenta obter o primeiro elemento sem removê-lo
            try:
                url = fila_segmentos[0]
            except IndexError:
                time.sleep(0.5)
                continue
                
            success = simular_download_segmento(url, bot_id)
            
            if success:
                try:
                    # Remove o elemento apenas se ainda existir e for o mesmo
                    if fila_segmentos and fila_segmentos[0] == url:
                        fila_segmentos.popleft()
                        segmentos_baixados.add(url)
                except IndexError:
                    pass
            else:
                time.sleep(1)

            time.sleep(wait_time)
            
        except Exception as e:
            logger.error(f"BOT {bot_id}: Erro ao processar fila de download: {str(e)}")
            time.sleep(1)

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
