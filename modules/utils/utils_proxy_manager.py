"""
Módulo para gerenciamento simples de proxies.

Este módulo contém a classe ProxyManager responsável por carregar
e distribuir proxies para os bots de forma rotativa.
"""

import os
import random
import logging
from typing import Optional, List, Dict
from colorama import Fore, Style, init

# Inicializa o colorama
init(autoreset=True)

logger = logging.getLogger(__name__)

class ProxyManager:
    def __init__(self, proxy_file: str = 'proxy.txt'):
        """
        Inicializa o gerenciador de proxies.
        
        Args:
            proxy_file (str): Caminho para o arquivo de proxies.
        """
        self.proxy_file = proxy_file
        self.proxies: List[str] = []
        self.bot_proxies: Dict[int, str] = {}  # Mapeia bot_id -> proxy
        self.load_proxies()

    def load_proxies(self) -> None:
        """Carrega lista de proxies do arquivo."""
        try:
            if not os.path.exists(self.proxy_file):
                logger.warning(f"{Fore.YELLOW}Arquivo de proxies não encontrado: {self.proxy_file}{Style.RESET_ALL}")
                return

            with open(self.proxy_file, 'r') as f:
                self.proxies = [line.strip() for line in f if line.strip()]
            
            logger.info(f"{Fore.GREEN}✅ {len(self.proxies)} proxies carregados{Style.RESET_ALL}")
            
        except Exception as e:
            logger.error(f"{Fore.RED}Erro ao carregar proxies: {e}{Style.RESET_ALL}")

    def format_proxy(self, proxy: str) -> Optional[str]:
        """
        Formata a string do proxy para o formato correto.
        
        Args:
            proxy (str): String do proxy (ip:porta ou ip:porta:usuario:senha)
            
        Returns:
            Optional[str]: Proxy formatado ou None se inválido
        """
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
        """
        Obtém um proxy para um bot específico.
        
        Args:
            bot_id (int): ID do bot solicitando o proxy
            
        Returns:
            Optional[str]: Proxy formatado ou None se nenhum disponível
        """
        if not self.proxies:
            return None

        # Se o bot já tem um proxy associado, retorna ele
        if bot_id in self.bot_proxies:
            return self.format_proxy(self.bot_proxies[bot_id])

        # Seleciona um novo proxy aleatório
        proxy = random.choice(self.proxies)
        self.bot_proxies[bot_id] = proxy
        
        formatted = self.format_proxy(proxy)
        if formatted:
            logger.info(f"{Fore.GREEN}Bot {bot_id} obteve proxy: {formatted}{Style.RESET_ALL}")
        return formatted

    def release_proxy(self, bot_id: int) -> None:
        """
        Libera o proxy associado a um bot.
        
        Args:
            bot_id (int): ID do bot liberando o proxy
        """
        if bot_id in self.bot_proxies:
            del self.bot_proxies[bot_id]
            logger.info(f"{Fore.CYAN}Proxy liberado pelo bot {bot_id}{Style.RESET_ALL}")

def create_proxy_manager(proxy_file: str = 'proxy.txt') -> ProxyManager:
    """Cria uma nova instância do gerenciador de proxies."""
    return ProxyManager(proxy_file)

# Código de teste
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    print(f"{Fore.YELLOW}\nTestando ProxyManager...{Style.RESET_ALL}")
    print("=" * 70)
    
    proxy_manager = create_proxy_manager()
    
    # Testa obtenção de proxies
    for bot_id in range(3):
        proxy = proxy_manager.get_proxy(bot_id)
        if proxy:
            print(f"{Fore.GREEN}✅ Bot {bot_id} obteve proxy: {proxy}{Style.RESET_ALL}")
        else:
            print(f"{Fore.RED}❌ Bot {bot_id} não conseguiu obter proxy{Style.RESET_ALL}")
    
    # Testa liberação
    print("\nTestando liberação de proxies...")
    for bot_id in range(3):
        proxy_manager.release_proxy(bot_id) 