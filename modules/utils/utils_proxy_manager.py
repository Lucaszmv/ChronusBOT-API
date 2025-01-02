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
        """Testa se um proxy está funcionando."""
        try:
            # Formata o proxy se necessário
            formatted_proxy = self.format_proxy(proxy) if '://' not in proxy else proxy
            if not formatted_proxy:
                return False

            session = requests.Session()
            session.proxies = {
                'http': formatted_proxy,
                'https': formatted_proxy
            }
            
            # Tenta primeiro com HTTPS
            try:
                response = session.get(
                    'https://www.google.com',
                    timeout=10,
                    verify=False
                )
                if response.status_code == 200:
                    return True
            except:
                # Se falhar como SOCKS5, tenta como HTTP
                try:
                    http_proxy = formatted_proxy.replace('socks5://', 'http://')
                    session.proxies = {
                        'http': http_proxy,
                        'https': http_proxy
                    }
                    response = session.get(
                        'http://www.google.com',
                        timeout=10,
                        verify=False
                    )
                    if response.status_code == 200:
                        # Atualiza o proxy para HTTP se funcionou
                        if proxy in self.proxies:
                            idx = self.proxies.index(proxy)
                            self.proxies[idx] = http_proxy
                        return True
                except:
                    return False
                
        except Exception as e:
            logger.error(f"Erro ao testar proxy {proxy}: {str(e)}")
            return False

    def format_proxy(self, proxy: str) -> Optional[str]:
        """
        Formata a string do proxy para o formato correto.
        Aceita formato simplificado ip:port:user:pass
        """
        try:
            if not proxy:
                return None
            
            # Se já tem o protocolo, retorna como está
            if '://' in proxy:
                return proxy
            
            # Formato simplificado ip:port:user:pass
            parts = proxy.strip().split(':')
            if len(parts) == 4:
                ip, port, user, password = parts
                # Retorna como SOCKS5 por padrão
                return f"socks5://{user}:{password}@{ip}:{port}"
                
            logger.error(f"Formato de proxy inválido: {proxy}")
            return None
            
        except Exception as e:
            logger.error(f"Erro ao formatar proxy: {str(e)}")
            return None

    def get_proxy(self, bot_id: int) -> Optional[str]:
        """Obtém um proxy único para um bot."""
        with self.lock:
            if bot_id in self.bot_proxies:
                return self.bot_proxies[bot_id]

            max_attempts = 10
            for attempt in range(max_attempts):
                available_proxies = [p for p in self.proxies if p not in self.used_proxies]
                
                if not available_proxies:
                    self.used_proxies.clear()
                    available_proxies = self.proxies

                if not available_proxies:
                    logger.error(f"BOT {bot_id}: Nenhum proxy disponível")
                    return None

                proxy = random.choice(available_proxies)
                logger.info(f"BOT {bot_id}: Testando proxy {proxy}")
                
                formatted_proxy = self.format_proxy(proxy)
                if not formatted_proxy:
                    continue
                    
                if self.test_proxy(formatted_proxy):
                    self.bot_proxies[bot_id] = formatted_proxy
                    self.used_proxies.add(proxy)
                    logger.info(f"BOT {bot_id}: Proxy {formatted_proxy} funcionando")
                    return formatted_proxy
                else:
                    logger.warning(f"BOT {bot_id}: Proxy {proxy} falhou no teste")
                    
                time.sleep(1)
                
            logger.error(f"BOT {bot_id}: Não foi possível encontrar proxy válido após {max_attempts} tentativas")
            return None

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