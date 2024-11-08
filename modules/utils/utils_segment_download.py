"""
Módulo para download e gerenciamento de segmentos de stream da Twitch.

Este módulo contém funções para simular e gerenciar o download de segmentos
de stream, incluindo controle de buffer e processamento de fila de download.

Functions:
    simular_download_segmento: Simula o download de um segmento individual.
    processar_fila_download: Processa a fila de segmentos para download.
    iniciar_downloader: Inicia o processamento da fila em thread separada.

Attributes:
    logger (Logger): Logger para registro de eventos do downloader.
    segmentos_baixados (set): Conjunto de segmentos já baixados.
    BUFFER_MIN (int): Tamanho mínimo do buffer de segmentos.
    BUFFER_MAX (int): Tamanho máximo do buffer de segmentos.
    WAIT_TIME_MIN (float): Tempo mínimo de espera entre downloads.
    WAIT_TIME_MAX (float): Tempo máximo de espera entre downloads.
"""
import logging
import time
from collections import deque
from concurrent.futures import ThreadPoolExecutor, as_completed
from colorama import Fore, Style, init
import requests
from modules.core.core_fingerprint import get_fingerprint
import random

# Inicializa o colorama
init(autoreset=True)

# Configurar o logger para não duplicar mensagens
logger = logging.getLogger(__name__)
logger.propagate = False
console_handler = logging.StreamHandler()
logger.addHandler(console_handler)

# Conjunto para armazenar os segmentos já baixados
segmentos_baixados = set()

# Configurações de buffer
BUFFER_MIN = 3
BUFFER_MAX = 5
WAIT_TIME_MIN = random.uniform(0.40, 0.50)  # Gera valor aleatório entre 0.4 e 0.5
WAIT_TIME_MAX = random.uniform(1.90, 2.10)  # Gera valor aleatório entre 0.6 e 0.7

def simular_download_segmento(url):
    """
    Realiza o download real de um segmento de stream.
    """
    try:
        # Procura por uma URL válida na string
        inicio = url.find('https://')
        if inicio == -1 or not url.endswith('.ts'):
            return False
            
        # Extrai apenas a URL
        url = url[inicio:]
            
        # Tenta baixar o segmento
        fingerprint = get_fingerprint()
        headers = {
            'User-Agent': fingerprint['User-Agent'],
            'Accept': fingerprint['Accept'],
        }

        response = requests.get(url, headers=headers, timeout=5)
        if response.status_code == 200:
            logger.info(Fore.GREEN + f"Segmento baixado com sucesso: {url[:70]}..." + Style.RESET_ALL)
            return True
            
        logger.error(Fore.RED + f"Falha ao baixar segmento (HTTP {response.status_code}): {url}" + Style.RESET_ALL)
        return False

    except Exception as e:
        logger.error(Fore.RED + f"Erro ao baixar segmento: {str(e)}" + Style.RESET_ALL)
        return False

def processar_fila_download(fila_segmentos: deque):
    """
    Processa a fila de download dos segmentos.

    Gerencia o download dos segmentos mantendo um buffer adequado e
    controlando a velocidade de processamento com base no tamanho da fila.

    Args:
        fila_segmentos (deque): Fila contendo as URLs dos segmentos a serem baixados.
    """
    while True:
        queue_size = len(fila_segmentos)
        
        if queue_size < BUFFER_MIN:
            logger.info(Fore.BLUE + f"Aguardando buffer mínimo. Tamanho atual da fila: {queue_size}" + Style.RESET_ALL)
            time.sleep(0.5)
            continue

        url = fila_segmentos[0]

        # Se for metadata que não é prefetch, ignora
        if url.startswith('#') and not url.startswith('#EXT-X-TWITCH-PREFETCH:'):
            fila_segmentos.popleft()
            continue

        # Remove o prefixo do prefetch para comparação
        url_comparacao = url.replace('#EXT-X-TWITCH-PREFETCH:', '') if url.startswith('#EXT-X-TWITCH-PREFETCH:') else url

        if url_comparacao in segmentos_baixados:
            logger.info(Fore.CYAN + f"Segmento já baixado anteriormente: {url_comparacao[:90]}..." + Style.RESET_ALL)
            fila_segmentos.popleft()
            continue

        success = simular_download_segmento(url)
        
        if success:
            # Armazena a URL sem o prefixo do prefetch
            segmentos_baixados.add(url_comparacao)
            fila_segmentos.popleft()
        else:
            logger.error(Fore.RED + f"Falha ao simular download do segmento: {url}" + Style.RESET_ALL)

        # Ajusta o tempo de espera com base no tamanho da fila
        if queue_size > BUFFER_MAX:
            wait_time = WAIT_TIME_MIN
        elif queue_size < BUFFER_MIN:
            wait_time = WAIT_TIME_MAX
        else:
            wait_time = WAIT_TIME_MIN + (WAIT_TIME_MAX - WAIT_TIME_MIN) * (BUFFER_MAX - queue_size) / (BUFFER_MAX - BUFFER_MIN)
        
        logger.info(Fore.MAGENTA + f"Tamanho da fila: {queue_size}, Tempo de espera: {wait_time:.2f}s" + Style.RESET_ALL)

        time.sleep(wait_time)

def iniciar_downloader(fila_segmentos: deque):
    """
    Inicia o processo de download dos segmentos em uma thread separada.

    Cria e inicia uma thread daemon para processar a fila de download
    de segmentos em segundo plano.

    Args:
        fila_segmentos (deque): Fila contendo as URLs dos segmentos a serem baixados.
    """
    import threading
    thread_downloader = threading.Thread(target=processar_fila_download, args=(fila_segmentos,))
    thread_downloader.daemon = True
    thread_downloader.start()
    logger.info(Fore.CYAN + "Simulador de download de segmentos iniciado em uma thread separada." + Style.RESET_ALL)
