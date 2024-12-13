"""
Módulo para gerenciamento de proxies do ChronusBOT com verificação de tempo de resposta.
"""

import os
import random
import logging
import requests
import time
from pathlib import Path
from typing import Optional, List, Dict, Set
from colorama import Fore, Style, init
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading

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
        self.available_proxies: Set[str] = set()
        self.adjust_lock = threading.Lock()
        self.total_bots = 0
        self.load_proxies()
        self.proxy_failures = {}  # Contador de falhas por proxy
        self.max_failures = 3     # Máximo de falhas antes de trocar o proxy

    def test_proxy(self, proxy: str) -> bool:
        """
        Testa se um proxy responde dentro do tempo limite.
        """
        formatted_proxy = self.format_proxy(proxy)
        if not formatted_proxy:
            return False

        proxies = {
            'http': formatted_proxy,
            'https': formatted_proxy
        }

        # Usa apenas um site de teste para ser mais rápido
        test_url = 'http://www.google.com'
        
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
        """Carrega e testa proxies até encontrar o número necessário."""
        try:
            if not os.path.exists(self.proxy_file):
                logger.warning(f"Arquivo de proxies não encontrado: {self.proxy_file}")
                return

            # Lê todos os proxies do arquivo
            with open(self.proxy_file, 'r') as f:
                all_proxies = [line.strip() for line in f if line.strip()]

            # Primeira tentativa: testa proxies não utilizados
            proxies_to_test = [p for p in all_proxies 
                              if p not in self.proxies 
                              and p not in self.available_proxies 
                              and p not in self.bot_proxies.values()]
            
            if not proxies_to_test:
                logger.warning("Todos os proxies já foram testados, tentando retestar todos")
                # Se não há novos proxies, testa todos exceto os em uso
                proxies_to_test = [p for p in all_proxies if p not in self.bot_proxies.values()]
                # Limpa proxies anteriormente testados
                self.available_proxies.clear()
                self.proxies.clear()
            
            # Randomiza a lista de proxies a testar
            random.shuffle(proxies_to_test)
            
            # Calcula quantos proxies ainda precisamos
            needed_proxies = max(self.total_bots - len(self.available_proxies), 1)
            logger.info(f"Precisamos de mais {needed_proxies} proxies válidos")
            
            # Testa todos os proxies disponíveis até encontrar o suficiente
            logger.info(f"{Fore.CYAN}Testando {len(proxies_to_test)} proxies para encontrar {needed_proxies} válidos...{Style.RESET_ALL}")
            
            valid_proxies = []
            max_workers = min(10, len(proxies_to_test))

            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                future_to_proxy = {
                    executor.submit(self.test_proxy, proxy): proxy 
                    for proxy in proxies_to_test
                }
                
                for future in as_completed(future_to_proxy):
                    proxy = future_to_proxy[future]
                    try:
                        is_valid = future.result()
                        if is_valid:
                            valid_proxies.append(proxy)
                            logger.info(f"{Fore.GREEN}Proxy válido encontrado: {proxy}{Style.RESET_ALL}")
                            
                            # Continua testando até ter proxies suficientes
                            if len(valid_proxies) >= needed_proxies:
                                # Cancela os testes restantes
                                for f in future_to_proxy:
                                    if not f.done():
                                        f.cancel()
                                break
                    except Exception as e:
                        logger.debug(f"Erro ao testar proxy {proxy}: {e}")

            with self.adjust_lock:
                # Adiciona apenas os novos proxies válidos
                for proxy in valid_proxies:
                    if proxy not in self.proxies and proxy not in self.available_proxies:
                        self.proxies.append(proxy)
                        self.available_proxies.add(proxy)
            
            logger.info(f"{Fore.GREEN}Proxies válidos carregados: {len(valid_proxies)}{Style.RESET_ALL}")
            logger.info(f"Total de proxies disponíveis agora: {len(self.available_proxies)}")

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
        """Obtém um proxy exclusivo para um bot."""
        if bot_id in self.bot_proxies:
            return self.format_proxy(self.bot_proxies[bot_id])

        max_attempts = 3
        attempt = 0
        
        while attempt < max_attempts:
            with self.adjust_lock:
                if not self.available_proxies:
                    # Se não há proxies disponíveis, tenta carregar mais
                    self.load_proxies()
                    
                    if not self.available_proxies:
                        attempt += 1
                        if attempt < max_attempts:
                            logger.warning(f"BOT {bot_id}: Tentativa {attempt}/{max_attempts} de obter proxy")
                            time.sleep(2)  # Aguarda antes de tentar novamente
                            continue
                        else:
                            logger.error(f"BOT {bot_id}: Falha ao obter proxy após {max_attempts} tentativas")
                            return None
                
                # Pega um proxy disponível e o remove da lista de disponíveis
                proxy = self.available_proxies.pop()
                self.bot_proxies[bot_id] = proxy
                logger.info(f"Bot {bot_id} obteve proxy exclusivo: {proxy}")
                return self.format_proxy(proxy)

    def register_proxy_failure(self, proxy: str):
        """Registra uma falha do proxy e retorna True se deve ser trocado"""
        with self.adjust_lock:
            self.proxy_failures[proxy] = self.proxy_failures.get(proxy, 0) + 1
            if self.proxy_failures[proxy] >= self.max_failures:
                logger.warning(f"Proxy {proxy} atingiu limite de falhas. Será trocado.")
                return True
        return False

    def release_proxy(self, bot_id: int):
        """Libera o proxy para uso por outros bots."""
        with self.adjust_lock:
            if bot_id in self.bot_proxies:
                proxy = self.bot_proxies[bot_id]
                del self.bot_proxies[bot_id]
                self.available_proxies.add(proxy)  # Devolve para lista de disponíveis
                logger.info(f"Bot {bot_id} liberou proxy: {proxy}")

    def set_total_bots(self, num_bots: int):
        """Define o número total de bots que precisarão de proxies."""
        self.total_bots = num_bots
        self.load_proxies()  # Carrega proxies baseado no número total de bots

    def rotate_proxy(self, bot_id: int) -> str:
        """Troca o proxy atual por um novo e força reinício da sessão"""
        with self.adjust_lock:
            old_proxy = self.bot_proxies.get(bot_id)
            if old_proxy:
                self.release_proxy(bot_id)
                # Remove o proxy com muitas falhas da lista de disponíveis
                if old_proxy in self.available_proxies:
                    self.available_proxies.remove(old_proxy)
                if old_proxy in self.proxies:
                    self.proxies.remove(old_proxy)
            return self.get_proxy(bot_id)

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