"""
Módulo para gerenciamento simplificado de proxies.
"""

import os
import random
import logging
import requests
import time
from pathlib import Path
from typing import Optional, List, Dict, Set
import threading

logger = logging.getLogger(__name__)

class ProxyManager:
    _instance = None
    
    def __new__(cls, proxy_file: str = 'proxy.txt'):
        if cls._instance is None:
            cls._instance = super(ProxyManager, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self, proxy_file: str = 'proxy.txt'):
        if not self._initialized:
            root_dir = str(Path(__file__).parent.parent.parent)
            self.proxy_file = os.path.join(root_dir, proxy_file)
            self.proxies: List[str] = []
            self.bot_proxies: Dict[int, str] = {}
            self.used_proxies: Set[str] = set()
            self.lock = threading.Lock()
            self.load_proxies()
            self._initialized = True

    def load_proxies(self) -> None:
        """Carrega a lista de proxies do arquivo."""
        try:
            if not os.path.exists(self.proxy_file):
                logger.warning(f"Arquivo de proxies não encontrado: {self.proxy_file}")
                return

            with open(self.proxy_file, 'r') as f:
                self.proxies = [line.strip() for line in f if line.strip()]
                
            logger.info("", extra={
                'proxy_load': {
                    'total_proxies': len(self.proxies),
                    'proxy_file': self.proxy_file
                }
            })

        except Exception as e:
            logger.error(f"Erro ao carregar proxies: {e}")

    def test_proxy(self, proxy: str) -> bool:
        """
        Testa se um proxy está funcionando.
        
        Args:
            proxy (str): Endereço do proxy para testar
            
        Returns:
            bool: True se o proxy está funcionando, False caso contrário
        """
        formatted_proxy = self.format_proxy(proxy)
        if not formatted_proxy:
            return False

        proxies = {
            'http': formatted_proxy,
            'https': formatted_proxy
        }

        try:
            response = requests.get(
                'http://www.google.com',
                proxies=proxies,
                timeout=5,
                verify=False
            )
            return response.status_code == 200
        except:
            return False

    def format_proxy(self, proxy: str) -> Optional[str]:
        """Formata a string do proxy para o formato correto."""
        try:
            if ':' in proxy:
                parts = proxy.split(':')
                if len(parts) == 2:
                    return f"http://{proxy}"
                elif len(parts) == 4:
                    return f"http://{parts[2]}:{parts[3]}@{parts[0]}:{parts[1]}"
            return None
        except:
            return None

    def get_proxy(self, bot_id: int) -> Optional[str]:
        """
        Obtém um proxy único para um bot. Continua tentando até encontrar um proxy válido.
        """
        with self.lock:
            if bot_id in self.bot_proxies:
                return self.format_proxy(self.bot_proxies[bot_id])

            while True:  # Loop infinito até encontrar um proxy válido
                available_proxies = [p for p in self.proxies if p not in self.used_proxies]
                
                if not available_proxies:
                    logger.warning("Resetando lista de proxies usados")
                    self.used_proxies.clear()
                    available_proxies = self.proxies

                if not available_proxies:
                    logger.error("Nenhum proxy disponível. Aguardando 5 segundos...")
                    time.sleep(5)
                    continue

                proxy = random.choice(available_proxies)
                available_proxies.remove(proxy)
                
                if self.test_proxy(proxy):
                    self.bot_proxies[bot_id] = proxy
                    self.used_proxies.add(proxy)
                    return self.format_proxy(proxy)
                
                logger.warning(f"Proxy {proxy} inválido, tentando outro...", extra={'terminal': False})
                time.sleep(2)  # Pequena pausa antes de tentar outro proxy

    def release_proxy(self, bot_id: int):
        """Libera o proxy usado por um bot."""
        with self.lock:
            if bot_id in self.bot_proxies:
                proxy = self.bot_proxies[bot_id]
                del self.bot_proxies[bot_id]
                self.used_proxies.remove(proxy)
                logger.info(f"Bot {bot_id} liberou proxy: {proxy}")

    def close_all(self):
        """Libera todos os proxies e limpa as estruturas de dados."""
        with self.lock:
            self.bot_proxies.clear()
            self.used_proxies.clear()

def create_proxy_manager(proxy_file: str = 'proxy.txt') -> ProxyManager:
    """Factory function para criar uma nova instância do ProxyManager."""
    return ProxyManager(proxy_file)