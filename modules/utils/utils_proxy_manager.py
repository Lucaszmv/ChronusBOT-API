"""
Módulo para gerenciamento de proxies do ChronusBOT com verificação de tempo de resposta.
"""

import os
import random
import logging
import requests
import time
from pathlib import Path
from typing import Optional, List, Dict
from colorama import Fore, Style, init

# Inicializa o colorama
init(autoreset=True)

# Configuração do logger
logger = logging.getLogger(__name__)

# Sites para teste de proxy (não relacionados à Twitch)
TEST_URLS = [
    'http://www.google.com',
    'http://www.cloudflare.com',
    'http://www.amazon.com',
    'http://www.microsoft.com'
]

class ProxyManager:
    def __init__(self, proxy_file: str = 'proxy.txt', max_response_time: float = 2.0):
        """
        Inicializa o gerenciador de proxies com verificação de tempo de resposta.
        
        Args:
            proxy_file (str): Nome do arquivo contendo a lista de proxies
            max_response_time (float): Tempo máximo de resposta aceitável em segundos
        """
        root_dir = str(Path(__file__).parent.parent.parent)
        self.proxy_file = os.path.join(root_dir, proxy_file)
        self.max_response_time = max_response_time
        self.proxies: List[str] = []
        self.bot_proxies: Dict[int, str] = {}
        self.load_proxies()

    def test_proxy(self, proxy: str) -> bool:
        """
        Testa se um proxy responde dentro do tempo limite.
        
        Args:
            proxy (str): Proxy no formato ip:porta ou ip:porta:usuario:senha
            
        Returns:
            bool: True se o proxy responder dentro do limite de tempo
        """
        formatted_proxy = self.format_proxy(proxy)
        if not formatted_proxy:
            return False

        proxies = {
            'http': formatted_proxy,
            'https': formatted_proxy
        }

        # Escolhe um site aleatório para teste
        test_url = random.choice(TEST_URLS)
        
        try:
            start_time = time.time()
            response = requests.get(
                test_url,
                proxies=proxies,
                timeout=self.max_response_time,
                verify=False
            )
            response_time = time.time() - start_time
            
            if response.status_code == 200 and response_time <= self.max_response_time:
                logger.info(f"{Fore.GREEN}Proxy válido: {proxy} - Tempo: {response_time:.2f}s{Style.RESET_ALL}")
                return True
                
        except Exception as e:
            logger.debug(f"{Fore.RED}Proxy inválido: {proxy} - Erro: {str(e)}{Style.RESET_ALL}")
        
        return False

    def load_proxies(self) -> None:
        """Carrega proxies e usa o primeiro que responder rapidamente."""
        try:
            if not os.path.exists(self.proxy_file):
                logger.warning(f"Arquivo de proxies não encontrado: {self.proxy_file}")
                return

            with open(self.proxy_file, 'r') as f:
                raw_proxies = [line.strip() for line in f if line.strip()]

            logger.info(f"{Fore.CYAN}Testando proxies até encontrar um rápido...{Style.RESET_ALL}")
            
            # Define tempo máximo de resposta como 1 segundo
            fast_response_time = 1.0
            
            for proxy in raw_proxies:
                # Testa o proxy atual
                formatted_proxy = self.format_proxy(proxy)
                if not formatted_proxy:
                    continue

                proxies = {
                    'http': formatted_proxy,
                    'https': formatted_proxy
                }

                # Escolhe um site aleatório para teste
                test_url = random.choice(TEST_URLS)
                
                try:
                    start_time = time.time()
                    response = requests.get(
                        test_url,
                        proxies=proxies,
                        timeout=fast_response_time,
                        verify=False
                    )
                    response_time = time.time() - start_time
                    
                    if response.status_code == 200 and response_time <= fast_response_time:
                        # Encontrou um proxy rápido, adiciona e para o teste
                        self.proxies = [proxy]
                        logger.info(f"{Fore.GREEN}Proxy rápido encontrado: {proxy} - Tempo: {response_time:.2f}s{Style.RESET_ALL}")
                        return
                        
                except Exception as e:
                    logger.debug(f"{Fore.RED}Proxy descartado: {proxy} - Erro: {str(e)}{Style.RESET_ALL}")
                    continue

            # Se nenhum proxy rápido foi encontrado, tenta novamente com tempo maior
            logger.warning(f"{Fore.YELLOW}Nenhum proxy rápido encontrado, testando com tempo maior...{Style.RESET_ALL}")
            
            for proxy in raw_proxies:
                if self.test_proxy(proxy):  # Usa o tempo padrão definido na classe
                    self.proxies = [proxy]
                    break

            if not self.proxies:
                logger.error(f"{Fore.RED}Nenhum proxy válido encontrado!{Style.RESET_ALL}")
            else:
                logger.info(f"{Fore.GREEN}Proxy válido encontrado e configurado{Style.RESET_ALL}")

        except Exception as e:
            logger.error(f"Erro ao carregar proxies: {e}")

    def format_proxy(self, proxy: str) -> Optional[str]:
        """Formata a string do proxy para o formato correto de URL."""
        try:
            if ':' in proxy:
                parts = proxy.split(':')
                if len(parts) == 2:
                    return f"http://{proxy}"
                elif len(parts) == 4:
                    return f"http://{parts[2]}:{parts[3]}@{parts[0]}:{parts[1]}"
            return None
        except Exception:
            return None

    def get_proxy(self, bot_id: int) -> Optional[str]:
        """Obtém um proxy aleatório para um bot específico."""
        if bot_id in self.bot_proxies:
            return self.format_proxy(self.bot_proxies[bot_id])

        if not self.proxies:
            return None

        proxy = random.choice(self.proxies)
        self.bot_proxies[bot_id] = proxy
        formatted = self.format_proxy(proxy)
        logger.info(f"Bot {bot_id} obteve proxy: {formatted}")
        return formatted

    def register_proxy_failure(self, bot_id: int) -> None:
        """Remove um proxy que falhou da lista."""
        if bot_id in self.bot_proxies:
            proxy = self.bot_proxies[bot_id]
            if proxy in self.proxies:
                self.proxies.remove(proxy)
                logger.warning(f"Proxy removido após falha do bot {bot_id}")
            self.release_proxy(bot_id)

    def release_proxy(self, bot_id: int) -> None:
        """Libera o proxy associado a um bot."""
        if bot_id in self.bot_proxies:
            del self.bot_proxies[bot_id]
            logger.debug(f"Proxy liberado pelo bot {bot_id}")

def create_proxy_manager(proxy_file: str = 'proxy.txt', max_response_time: float = 2.0) -> ProxyManager:
    """
    Factory function para criar uma nova instância do ProxyManager.
    
    Args:
        proxy_file (str): Nome do arquivo de proxies
        max_response_time (float): Tempo máximo de resposta aceitável em segundos
        
    Returns:
        ProxyManager: Nova instância configurada do gerenciador de proxies
    """
    return ProxyManager(proxy_file, max_response_time)