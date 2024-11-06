"""
Módulo para detecção e processamento de anúncios da Twitch.

Este módulo contém a classe AdDetector responsável por identificar, rastrear
e processar anúncios em playlists M3U8 da Twitch, mantendo controle sobre
pods de anúncios e seus segmentos.

Classes:
    AdDetector: Gerencia a detecção e processamento de anúncios.

Functions:
    create_ad_detector: Factory function para criar uma instância de AdDetector.

Attributes:
    logger (Logger): Logger para registro de eventos do detector de anúncios.
"""

import logging
from typing import Dict
from colorama import Fore, Style, init
import time
import sys

init(autoreset=True)

logger = logging.getLogger(__name__)

class AdDetector:
    """
    Classe para detecção e processamento de anúncios em playlists M3U8.

    Esta classe mantém o estado dos anúncios sendo processados, incluindo
    contadores, assinaturas de pods e informações sobre breaks de anúncios.

    Attributes:
        ad_segments (list): Lista de segmentos de anúncios.
        last_segment (str): Último segmento processado.
        in_ad_break (bool): Indica se está em um break de anúncios.
        ad_start_time (float): Timestamp do início do anúncio atual.
        last_ad_pod_signature (str): Assinatura do último pod de anúncios.
        total_ads_viewed (int): Total de anúncios individuais visualizados.
        detected_ad_pods (set): Conjunto de pods de anúncios detectados.
        current_pod_info (dict): Informações sobre o pod atual.
        current_pod_ad_count (int): Contador de anúncios no pod atual.
        total_ad_pods_viewed (int): Total de pods de anúncios visualizados.
        max_ad_pods (int): Limite máximo de pods de anúncios.
    """

    def __init__(self, max_ad_pods):
        """
        Inicializa o detector de anúncios.

        Args:
            max_ad_pods (int): Número máximo de pods de anúncios a processar.
        """
        self.ad_segments = []
        self.last_segment = None
        self.in_ad_break = False
        self.ad_start_time = None
        self.last_ad_pod_signature = None  # Assinatura única para o último pod de anúncio
        self.total_ads_viewed = 0  # Novo contador cumulativo
        self.detected_ad_pods = set()  # Novo conjunto para rastrear pods de anúncios detectados
        self.current_pod_info = None  # Informações do pod atual
        self.current_pod_ad_count = 0  # Contador de anúncios no pod atual
        self.total_ad_pods_viewed = 0
        self.max_ad_pods = max_ad_pods  # Novo atributo para armazenar o limite

    def process_playlist(self, playlist_content: str):
        """
        Processa o conteúdo de uma playlist M3U8 para detectar anúncios.

        Analisa cada linha da playlist procurando por marcadores de anúncios,
        descontinuidades e segmentos, atualizando o estado interno do detector.

        Args:
            playlist_content (str): Conteúdo da playlist M3U8 a ser processada.
        """
        lines = playlist_content.split('\n')
        for i, line in enumerate(lines):
            if line.startswith('#EXT-X-DATERANGE:'):
                logger.debug(f"Processando linha: {line}")
                if 'CLASS="twitch-stitched-ad"' in line:
                    logger.debug("Anúncio detectado na linha")
                    ad_info = self.parse_ad_info(line)
                    pod_signature = self.generate_ad_pod_signature(ad_info)
                    
                    if pod_signature not in self.detected_ad_pods:
                        # Novo pod de anúncio
                        self.start_new_ad_pod(ad_info, pod_signature)
                    elif self.in_ad_break:
                        # Anúncio adicional no pod atual
                        self.process_additional_ad(ad_info)
            
            elif line.startswith('#EXT-X-DISCONTINUITY'):
                logger.debug("Descontinuidade detectada")
                if self.in_ad_break:
                    # Procura pela sequência de live nos próximos 5 segmentos
                    for j in range(i + 1, min(i + 6, len(lines))):
                        if lines[j].startswith('#EXT-X-TWITCH-LIVE-SEQUENCE'):
                            logger.debug("Sequência ao vivo detectada após anúncio")
                            self.check_ad_completion()
                            break
            
            elif not line.startswith('#') and line.strip():
                self.last_segment = line.strip()
                if self.in_ad_break:
                    self.ad_segments.append(line.strip())
                    logger.debug(f"Segmento de anúncio adicionado: {line.strip()}")

        logger.debug(f"Processamento da playlist concluído. In ad break: {self.in_ad_break}")

    def generate_ad_pod_signature(self, ad_info: Dict[str, str]) -> str:
        """
        Gera uma assinatura única para um pod de anúncios.

        Args:
            ad_info (Dict[str, str]): Informações do anúncio.

        Returns:
            str: Assinatura única do pod de anúncios.
        """
        # Cria uma assinatura única usando o horário de início e o número de anúncios
        start_date = ad_info.get('START-DATE', '')
        pod_length = ad_info.get('X-TV-TWITCH-AD-POD-LENGTH', '1')
        return f"{start_date}_{pod_length}"

    def start_new_ad_pod(self, ad_info: Dict[str, str], pod_signature: str):
        """
        Inicia um novo pod de anúncios.

        Args:
            ad_info (Dict[str, str]): Informações do anúncio.
            pod_signature (str): Assinatura única do pod.
        """
        self.detected_ad_pods.add(pod_signature)
        self.current_pod_info = ad_info
        self.current_pod_ad_count = 1
        self.in_ad_break = True
        self.ad_start_time = time.time()
        self.print_ad_start(ad_info)

    def process_additional_ad(self, ad_info: Dict[str, str]):
        self.current_pod_ad_count += 1
        logger.debug(f"Anúncio adicional detectado no pod atual. Total: {self.current_pod_ad_count}")

    def check_ad_completion(self):
        if self.in_ad_break:
            self.in_ad_break = False
            self.total_ad_pods_viewed += 1
            self.total_ads_viewed += self.current_pod_ad_count
            self.print_ad_viewed_success(self.last_segment)
            self.ad_start_time = None
            self.ad_segments = []
            self.current_pod_info = None
            self.current_pod_ad_count = 0
            
            # Verifica se atingiu o limite de pods de anúncios
            if self.total_ad_pods_viewed >= self.max_ad_pods:
                self.print_limit_reached()
                sys.exit(0)  # Encerra o programa

    def parse_ad_info(self, line: str) -> Dict[str, str]:
        ad_info = {}
        for item in line.split(','):
            if '=' in item:
                key, value = item.split('=', 1)
                ad_info[key.strip()] = value.strip('"')
        return ad_info

    def print_ad_start(self, ad_info: Dict[str, str]):
        pod_length = ad_info.get('X-TV-TWITCH-AD-POD-LENGTH', '?')
        roll_type = ad_info.get('X-TV-TWITCH-AD-ROLL-TYPE', '?')
        ad_format = ad_info.get('X-TV-TWITCH-AD-AD-FORMAT', '?')
        start_date = ad_info.get('START-DATE', '?')

        print(Fore.YELLOW + f"Novo pod de anúncios detectado: Início: {start_date}, {pod_length} anúncios {roll_type} - Formato: {ad_format}" + Style.RESET_ALL)
        logger.info(f"Novo pod de anúncios detectado: Início: {start_date}, {pod_length} anúncios {roll_type} - Formato: {ad_format}")

    def print_ad_viewed_success(self, last_segment: str):
        message = f"Pod de anúncios visualizado com sucesso! Último segmento: {last_segment}"
        print(Fore.GREEN + message + Style.RESET_ALL)
        logger.info(message)

        total_message = f"Total de pods de anúncios visualizados: {self.total_ad_pods_viewed}"
        print(Fore.CYAN + total_message + Style.RESET_ALL)
        logger.info(total_message)

        total_ads_message = f"Total de anúncios individuais visualizados: {self.total_ads_viewed}"
        print(Fore.CYAN + total_ads_message + Style.RESET_ALL)
        logger.info(total_ads_message)

        # Adicione esta linha para garantir que a mensagem seja exibida imediatamente
        sys.stdout.flush()

    def print_limit_reached(self):
        message = f"Limite de {self.max_ad_pods} pods de anúncios atingido. Encerrando o bot."
        print(Fore.RED + message + Style.RESET_ALL)
        logger.info(message)
        sys.stdout.flush()

def create_ad_detector(max_ad_pods=2):
    return AdDetector(max_ad_pods)
