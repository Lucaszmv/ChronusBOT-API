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

# Obtém o caminho absoluto do diretório raiz
root_dir = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(root_dir))

# Agora podemos importar os módulos do projeto
try:
    from modules.core.core_token import obter_playback_access_token
    from modules.core.core_get_playlist import obter_playlist_m3u8
    from modules.core.core_session import session_manager
except ImportError as e:
    print(f"Erro ao importar módulos: {e}")
    sys.exit(1)

# Configurar o logger para não duplicar mensagens
logger = logging.getLogger(__name__)
logger.propagate = False
console_handler = logging.StreamHandler()
logger.addHandler(console_handler)

# Conjunto para armazenar os segmentos já baixados
segmentos_baixados = set()

# Configurações de buffer
BUFFER_MIN = 1
BUFFER_MAX = 5
WAIT_TIME_MIN = random.uniform(0.40, 0.50)
WAIT_TIME_MAX = random.uniform(1.90, 2.10) 

def obter_playlist_qualidade(url: str, fingerprint: dict, bot_id: int = None) -> Optional[str]:
    """
    Obtém a playlist de uma qualidade específica da stream.
    Implementação específica para testes de download, mantida aqui para evitar
    dependências circulares e permitir testes independentes do módulo.

    Args:
        url (str): URL completa da playlist de qualidade desejada.
        fingerprint (dict): Dicionário contendo os dados de fingerprint do navegador.
        bot_id (int, optional): Identificador único do bot para gerenciamento de sessão.

    Returns:
        Optional[str]: Conteúdo da playlist M3U8 se bem sucedido, None se ocorrer erro.
    """
    session = session_manager.get_session(bot_id) if bot_id else requests.Session()
    
    headers = {
        "User-Agent": fingerprint.get('User-Agent'),
        "Client-ID": fingerprint.get('Client-Id'),
        "X-Device-Id": fingerprint.get('Device-Id'),
        "Accept": "application/x-mpegURL, application/vnd.apple.mpegurl, application/json, text/plain",
        "Accept-Language": "pt-BR,pt;q=0.8,en-US;q=0.5,en;q=0.3",
        "Accept-Encoding": "gzip, deflate, br",
        "Origin": "https://www.twitch.tv",
        "Referer": "https://www.twitch.tv/",
    }

    try:
        response = session.get(url, headers=headers)
        response.raise_for_status()
        return response.text
    except requests.exceptions.RequestException as e:
        logging.error(f"Erro ao obter playlist de qualidade: {e}")
        return None

def simular_download_segmento(url, bot_id=None):
    """
    Simula o download de um segmento de stream da Twitch.
    Faz uma requisição HTTP real para o segmento, mas não salva o conteúdo.
    Útil para testes e validação do processo de download.

    Args:
        url (str): URL do segmento .ts a ser baixado.
        bot_id (int, optional): ID do bot para usar sua sessão específica.

    Returns:
        bool: True se o download foi simulado com sucesso, False caso contrário.
    """
    try:
        # Procura por uma URL válida na string
        inicio = url.find('https://')
        if inicio == -1 or not url.endswith('.ts'):
            return False
            
        # Extrai apenas a URL
        url = url[inicio:]
            
        # Usar a sessão do session_manager
        session = session_manager.get_session(bot_id) if bot_id else requests.Session()
        fingerprint = session_manager.get_fingerprint(bot_id) if bot_id else {}
        
        headers = {
            'User-Agent': fingerprint.get('User-Agent'),
            'Accept': fingerprint.get('Accept'),
            'Client-ID': fingerprint.get('Client-Id'),
        }

        response = session.get(url, headers=headers, timeout=5)
        if response.status_code == 200:
            logger.info(Fore.GREEN + f"Segmento baixado com sucesso: {url[:70]}..." + Style.RESET_ALL)
            return True
            
        logger.error(Fore.RED + f"Falha ao baixar segmento (HTTP {response.status_code}): {url}" + Style.RESET_ALL)
        return False

    except Exception as e:
        logger.error(Fore.RED + f"Erro ao baixar segmento: {str(e)}" + Style.RESET_ALL)
        return False

def processar_fila_download(fila_segmentos: deque, bot_id: int = None):
    """
    Processa continuamente a fila de segmentos para download.
    Implementa um sistema de buffer dinâmico que ajusta o tempo de espera
    entre downloads baseado no tamanho atual da fila.

    Args:
        fila_segmentos (deque): Fila contendo as URLs dos segmentos a serem baixados.
        bot_id (int, optional): ID do bot para usar sua sessão específica.

    Note:
        - O tempo de espera é menor quando a fila está mais cheia
        - Segmentos baixados com sucesso são adicionados ao conjunto segmentos_baixados
        - Em caso de falha, há uma espera antes de tentar novamente
    """
    while True:
        queue_size = len(fila_segmentos)
        
        if queue_size == 0:
            logger.info(Fore.YELLOW + "Fila de segmentos vazia. Aguardando..." + Style.RESET_ALL)
            time.sleep(1)
            continue

        url = fila_segmentos[0]
        logger.info(Fore.CYAN + f"Processando segmento: {url[:70]}..." + Style.RESET_ALL)

        success = simular_download_segmento(url, bot_id)
        
        if success:
            segmentos_baixados.add(url)
            fila_segmentos.popleft()
            logger.info(Fore.GREEN + f"Segmentos processados até agora: {len(segmentos_baixados)}" + Style.RESET_ALL)
        else:
            logger.error(Fore.RED + f"Falha ao simular download do segmento: {url}" + Style.RESET_ALL)
            time.sleep(1)  # Espera um pouco antes de tentar novamente

        # Ajusta o tempo de espera com base no tamanho da fila
        # Quanto maior a fila, menor o tempo de espera
        if queue_size >= BUFFER_MAX:
            wait_time = WAIT_TIME_MIN
        else:
            wait_time = min(
                WAIT_TIME_MAX,
                max(
                    WAIT_TIME_MIN,
                    WAIT_TIME_MIN + (WAIT_TIME_MAX - WAIT_TIME_MIN) * (1 - queue_size / BUFFER_MAX)
                )
            )
            
        logger.info(Fore.MAGENTA + f"Tamanho da fila: {queue_size}, Tempo de espera: {wait_time:.2f}s" + Style.RESET_ALL)
        time.sleep(wait_time)

def iniciar_downloader(fila_segmentos: deque, bot_id: int = None):
    """
    Inicia o processamento da fila de download em uma thread separada.
    Isso permite que o download dos segmentos ocorra em background sem
    bloquear a thread principal.

    Args:
        fila_segmentos (deque): Fila contendo as URLs dos segmentos a serem baixados.
        bot_id (int, optional): ID do bot para usar sua sessão específica.

    Note:
        A thread é iniciada em modo daemon, o que significa que ela será
        encerrada quando a thread principal terminar.
    """
    import threading
    thread_downloader = threading.Thread(target=processar_fila_download, args=(fila_segmentos, bot_id))
    thread_downloader.daemon = True
    thread_downloader.start()
    logger.info(Fore.CYAN + "Simulador de download de segmentos iniciado em uma thread separada." + Style.RESET_ALL)

def main():
    """
    Função principal para teste do módulo de download de segmentos.
    Demonstra o fluxo completo de:
    1. Configuração de sessão e logging
    2. Obtenção de token de acesso
    3. Obtenção da playlist principal
    4. Seleção de qualidade
    5. Obtenção da playlist de qualidade
    6. Extração e download dos segmentos
    7. Monitoramento do processo

    Note:
        - Usa bot_id=999 para testes
        - Registra todas as operações em arquivo de log
        - Exibe feedback visual do progresso no console
    """
    # Configurar logging
    log_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'logs')
    os.makedirs(log_dir, exist_ok=True)
    log_file = os.path.join(log_dir, f'segment_downloader_{datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")}.log')

    logging.basicConfig(filename=log_file, level=logging.INFO,
                       format='%(asctime)s - %(levelname)s - %(message)s')

    try:
        print(f"{Fore.YELLOW}Testando Downloader de Segmentos...{Style.RESET_ALL}")
        print("=" * 70)
        
        canal_nome = input(f"{Fore.YELLOW}Digite o nome do canal da Twitch: {Style.RESET_ALL}")
        logging.info(f"Iniciando teste para o canal: {canal_nome}")
        
        # Criar sessão de teste
        bot_id = 999  # ID específico para testes
        session = session_manager.get_session(bot_id)
        fingerprint = session_manager.get_fingerprint(bot_id)
        
        print(f"\n{Fore.CYAN}Sessão de teste criada com bot_id: {bot_id}{Style.RESET_ALL}")
        print(f"{Fore.CYAN}Fingerprint gerado:{Style.RESET_ALL}")
        for key, value in fingerprint.items():
            print(f"{Fore.YELLOW}{key}:{Style.RESET_ALL} {value}")
        print("=" * 70)
        
        # Exibir informações do proxy
        if session.proxies:
            proxy_info = session.proxies.get('http', 'Nenhum proxy configurado')
            print(f"{Fore.CYAN}Proxy em uso: {proxy_info}{Style.RESET_ALL}")
        print("=" * 70)
        
        # Obter token
        print(f"{Fore.CYAN}Obtendo token de acesso...{Style.RESET_ALL}")
        token_data = obter_playback_access_token(canal_nome, fingerprint, bot_id)
        
        if not token_data:
            print(f"{Fore.RED}❌ Falha ao obter token de acesso{Style.RESET_ALL}")
            return

        print(f"{Fore.GREEN}✅ Token de acesso obtido com sucesso{Style.RESET_ALL}")
        
        # Obter playlist principal
        playlist_principal = obter_playlist_m3u8(canal_nome, token_data, bot_id)
        if not playlist_principal:
            print(f"{Fore.RED}❌ Falha ao obter playlist principal{Style.RESET_ALL}")
            return
            
        # Extrair e selecionar qualidade
        links_qualidade = [linha for linha in playlist_principal.split('\n') 
                          if linha.startswith('https://') and '.m3u8' in linha]
        if not links_qualidade:
            print(f"{Fore.RED}❌ Nenhuma qualidade disponível{Style.RESET_ALL}")
            return
            
        link_qualidade = random.choice(links_qualidade)
        print(f"{Fore.CYAN}Qualidade selecionada: {link_qualidade}{Style.RESET_ALL}")
        
        # Obter playlist de qualidade usando a função importada
        print(f"{Fore.CYAN}Obtendo playlist de qualidade...{Style.RESET_ALL}")
        playlist_qualidade = obter_playlist_qualidade(link_qualidade, fingerprint, bot_id)
        if not playlist_qualidade:
            print(f"{Fore.RED}❌ Falha ao obter playlist de qualidade{Style.RESET_ALL}")
            return

        print(f"{Fore.GREEN}✅ Playlist de qualidade obtida com sucesso{Style.RESET_ALL}")

        # Extrair e adicionar segmentos à fila
        segmentos = [linha for linha in playlist_qualidade.split('\n') 
                    if linha.startswith('http') and linha.endswith('.ts')]
        
        print(f"{Fore.CYAN}Adicionando {len(segmentos)} segmentos à fila...{Style.RESET_ALL}")
        
        # Criar fila de teste
        fila_teste = deque()
        
        # Adicionar segmentos à fila primeiro
        for segmento in segmentos:
            fila_teste.append(segmento)
            print(f"{Fore.GREEN}Segmento adicionado: {segmento[:70]}...{Style.RESET_ALL}")
            time.sleep(0.1)  # Reduzir tempo entre adições
        
        # Iniciar downloader depois que a fila já tem segmentos
        print(f"\n{Fore.CYAN}Iniciando downloader...{Style.RESET_ALL}")
        iniciar_downloader(fila_teste, bot_id)

        # Aguardar processamento
        print(f"\n{Fore.CYAN}Aguardando processamento dos segmentos...{Style.RESET_ALL}")
        while len(fila_teste) > 0:
            print(f"Segmentos restantes: {len(fila_teste)}")
            time.sleep(1)

        # Aguardar um pouco mais para garantir que todos os segmentos foram processados
        time.sleep(2)

        print(f"\n{Fore.GREEN}✅ Teste concluído!")
        print(f"Total de segmentos processados: {len(segmentos_baixados)}")
        print(f"Tamanho atual da fila: {len(fila_teste)}{Style.RESET_ALL}")
        
        # Fechar a sessão
        session_manager.close_session(bot_id)
        print(f"{Fore.GREEN}✅ Sessão de teste fechada{Style.RESET_ALL}")
        
        print("=" * 70)
        print(f"Todos os dados foram registrados no arquivo de log: {log_file}")
        print("=" * 70)

    except Exception as e:
        logging.error(f"Erro durante a execução: {e}")
        print(f"{Fore.RED}❌ Ocorreu um erro durante a execução: {e}")
        print(f"Verifique o arquivo de log: {log_file}{Style.RESET_ALL}")

if __name__ == "__main__":
    main()
