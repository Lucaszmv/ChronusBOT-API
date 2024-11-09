"""
Módulo para gerenciamento de proxies do ChronusBOT.

Este módulo implementa um sistema de gerenciamento de proxies que permite:
- Carregar proxies de um arquivo texto
- Atribuir proxies específicos para cada bot
- Formatar strings de proxy para o formato correto
- Liberar proxies quando não mais necessários

Classes:
    ProxyManager: Gerenciador principal de proxies

Funções:
    create_proxy_manager: Factory function para criar instâncias do ProxyManager

Attributes:
    logger: Logger configurado para exibir mensagens formatadas
    PROXY_FILE (default='proxy.txt'): Arquivo contendo lista de proxies
"""

import os
import random
import logging
from pathlib import Path
from typing import Optional, List, Dict
from colorama import Fore, Style, init
import time

# Inicializa o colorama
init(autoreset=True)

# Configuração do logger
logger = logging.getLogger(__name__)
logger.propagate = False  # Evita duplicação de logs
formatter = logging.Formatter('%(message)s')  # Remove prefixos do log
console_handler = logging.StreamHandler()
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)

class ProxyManager:
    """
    Gerenciador de proxies para múltiplos bots.
    
    Esta classe gerencia a atribuição e liberação de proxies para diferentes bots,
    mantendo um registro de qual proxy está sendo usado por cada bot.

    Attributes:
        proxy_file (str): Caminho para o arquivo de proxies
        proxies (List[str]): Lista de todos os proxies disponíveis
        bot_proxies (Dict[int, str]): Mapeamento de bot_id para proxy
    """

    def __init__(self, proxy_file: str = 'proxy.txt'):
        """
        Inicializa o gerenciador de proxies.
        
        Args:
            proxy_file (str): Nome do arquivo contendo a lista de proxies.
                            Deve estar na raiz do projeto.
        """
        root_dir = str(Path(__file__).parent.parent.parent)
        self.proxy_file = os.path.join(root_dir, proxy_file)
        self.proxies: List[str] = []
        self.bot_proxies: Dict[int, str] = {}
        self.load_proxies()

    def load_proxies(self) -> None:
        """
        Carrega a lista de proxies do arquivo.
        
        O arquivo deve conter um proxy por linha no formato:
        - ip:porta
        - ip:porta:usuario:senha
        
        Raises:
            FileNotFoundError: Se o arquivo de proxies não for encontrado
            Exception: Para outros erros durante a leitura do arquivo
        """
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
        Formata a string do proxy para o formato correto de URL.
        
        Args:
            proxy (str): String do proxy no formato ip:porta ou ip:porta:usuario:senha

        Returns:
            Optional[str]: URL formatada do proxy (ex: http://ip:porta) ou
                         None se o formato for inválido

        Examples:
            >>> format_proxy("127.0.0.1:8080")
            "http://127.0.0.1:8080"
            >>> format_proxy("127.0.0.1:8080:user:pass")
            "http://user:pass@127.0.0.1:8080"
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
        
        Se o bot já possui um proxy atribuído, retorna o mesmo proxy.
        Caso contrário, atribui um novo proxy aleatório ao bot.

        Args:
            bot_id (int): Identificador único do bot

        Returns:
            Optional[str]: URL do proxy formatada ou None se nenhum proxy disponível
        """
        if not self.proxies:
            return None

        if bot_id in self.bot_proxies:
            return self.format_proxy(self.bot_proxies[bot_id])

        proxy = random.choice(self.proxies)
        self.bot_proxies[bot_id] = proxy
        
        formatted = self.format_proxy(proxy)
        if formatted:
            print(f"{Fore.GREEN}✅ Bot {bot_id} obteve proxy: {formatted}{Style.RESET_ALL}")
        return formatted

    def release_proxy(self, bot_id: int) -> None:
        """
        Libera o proxy associado a um bot.
        
        Remove a associação entre o bot e seu proxy atual,
        permitindo que o proxy seja reutilizado por outros bots.

        Args:
            bot_id (int): Identificador único do bot
        """
        if bot_id in self.bot_proxies:
            del self.bot_proxies[bot_id]
            print(f"{Fore.CYAN}Proxy liberado pelo bot {bot_id}{Style.RESET_ALL}")

def create_proxy_manager(proxy_file: str = 'proxy.txt') -> ProxyManager:
    """
    Factory function para criar uma nova instância do ProxyManager.
    
    Args:
        proxy_file (str): Nome do arquivo de proxies

    Returns:
        ProxyManager: Nova instância configurada do gerenciador de proxies
    """
    return ProxyManager(proxy_file)

# Código de teste
if __name__ == "__main__":
    logger.setLevel(logging.INFO)
    
    print(f"{Fore.YELLOW}\nTestando ProxyManager...{Style.RESET_ALL}")
    print("=" * 70)
    
    proxy_manager = create_proxy_manager()
    
    # Testa obtenção de proxies
    for bot_id in range(3):
        proxy_manager.get_proxy(bot_id)
    
    # Testa liberação
    print("\nTestando liberação de proxies...")
    for bot_id in range(3):
        proxy_manager.release_proxy(bot_id)
    
    time.sleep(60)