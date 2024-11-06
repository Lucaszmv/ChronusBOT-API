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
WAIT_TIME_MIN = 0.1
WAIT_TIME_MAX = 1.0

def simular_download_segmento(url):
    """
    Simula o download de um segmento de stream.

    Realiza uma simulação do processo de download de um segmento,
    aguardando um tempo fixo para simular a latência de rede.

    Args:
        url (str): URL do segmento a ser "baixado".

    Returns:
        bool: True se o download foi simulado com sucesso, False caso contrário.
    """
    time.sleep(0.1)  # Simula o tempo de download
    return True

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

        url = fila_segmentos[0]  # Pega o primeiro segmento da fila sem removê-lo

        if url in segmentos_baixados:
            logger.info(Fore.CYAN + f"Segmento já baixado anteriormente: {url}" + Style.RESET_ALL)
            fila_segmentos.popleft()  # Remove o segmento da fila
            continue

        success = simular_download_segmento(url)
        
        if success:
            segmentos_baixados.add(url)
            fila_segmentos.popleft()  # Remove o segmento da fila apenas após o download bem-sucedido
            mensagem = f"Segmento baixado com sucesso: @{url[:70]}... - Tamanho atual da fila de segmentos: {len(fila_segmentos)}"
            logger.info(Fore.GREEN + mensagem + Style.RESET_ALL)
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
