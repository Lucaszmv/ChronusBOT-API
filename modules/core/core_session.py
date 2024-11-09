"""
Módulo para gerenciamento de sessões HTTP.
"""

import sys
import os
import time
import logging
import requests
from pathlib import Path
from typing import Dict
from colorama import Fore, Style, init

# Adiciona o diretório raiz do projeto ao PYTHONPATH
root_dir = str(Path(__file__).parent.parent.parent)
sys.path.append(root_dir)

# Inicializar o Colorama
init()

try:
    from modules.core.core_fingerprint import get_fingerprint
    from modules.utils.utils_proxy_manager import create_proxy_manager
except ImportError as e:
    logging.error(f"Erro ao importar módulos: {e}")
    print(f"Erro ao importar módulos. Verifique o arquivo de log.")
    sys.exit(1)

class SessionManager:
    """
    Gerenciador de sessões HTTP individuais para cada bot.
    """
    
    def __init__(self):
        self.sessions: Dict[int, requests.Session] = {}
        self.fingerprints: Dict[int, Dict[str, str]] = {}
        self.proxy_manager = create_proxy_manager()
        
    def get_session(self, bot_id: int) -> requests.Session:
        """
        Obtém ou cria uma sessão para um bot específico.
        
        Args:
            bot_id (int): ID único do bot
            
        Returns:
            requests.Session: Sessão HTTP para o bot
        """
        if bot_id not in self.sessions:
            # Gerar novo fingerprint para o bot
            self.fingerprints[bot_id] = get_fingerprint()
            
            # Obtém proxy do gerenciador
            proxy = self.proxy_manager.get_proxy(bot_id)
                
            self.sessions[bot_id] = self.create_session(proxy)
            logging.info(f"Nova sessão criada para bot {bot_id}")
        return self.sessions[bot_id]
    
    def get_fingerprint(self, bot_id: int) -> Dict[str, str]:
        """
        Obtém o fingerprint associado ao bot.
        
        Args:
            bot_id (int): ID do bot
            
        Returns:
            Dict[str, str]: Fingerprint do bot
        """
        return self.fingerprints.get(bot_id)
    
    def create_session(self, proxy: str = None) -> requests.Session:
        """
        Cria uma nova sessão com configurações personalizadas.
        """
        session = requests.Session()
        
        if proxy:
            session.proxies = {
                'http': proxy,
                'https': proxy
            }
        
        session.verify = True
        session.trust_env = False
        session.timeout = (5, 10)
        
        return session
    
    def close_session(self, bot_id: int):
        """
        Fecha a sessão de um bot específico e libera seu proxy.
        """
        if bot_id in self.sessions:
            self.sessions[bot_id].close()
            del self.sessions[bot_id]
            del self.fingerprints[bot_id]
            self.proxy_manager.release_proxy(bot_id)
            logging.info(f"Sessão do bot {bot_id} fechada")
    
    def close_all(self):
        """
        Fecha todas as sessões ativas e libera seus proxies.
        """
        for bot_id in list(self.sessions.keys()):
            self.close_session(bot_id)
        logging.info("Todas as sessões foram fechadas")

# Instância global do gerenciador de sessões
session_manager = SessionManager()

def get_session(bot_id: int) -> requests.Session:
    """
    Função auxiliar para obter uma sessão para um bot.
    """
    return session_manager.get_session(bot_id)

def get_bot_fingerprint(bot_id: int) -> Dict[str, str]:
    """
    Função auxiliar para obter o fingerprint de um bot.
    """
    return session_manager.get_fingerprint(bot_id)

# Código de teste
if __name__ == "__main__":
    try:
        # Configuração do logging
        from datetime import datetime, timezone
        
        log_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'logs')
        os.makedirs(log_dir, exist_ok=True)
        log_file = os.path.join(log_dir, f'session_manager_{datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")}.log')
        
        logging.basicConfig(filename=log_file, level=logging.INFO,
                          format='%(asctime)s - %(levelname)s - %(message)s')

        print(f"{Fore.YELLOW}Testando SessionManager...{Style.RESET_ALL}")
        print("=" * 100)
        
        # Criar algumas sessões de teste
        for i in range(3):
            session = get_session(i)
            fingerprint = get_bot_fingerprint(i)
            print(f"\n{Fore.GREEN}✅ Sessão {i} criada com sucesso{Style.RESET_ALL}")
            
            # Mostrar status do proxy primeiro
            if session.proxies:
                print(f"{Fore.CYAN}Proxy obtido: {session.proxies.get('http', 'Nenhum')}{Style.RESET_ALL}")
            else:
                print(f"{Fore.YELLOW}⚠️ Nenhum proxy configurado para o bot {i}{Style.RESET_ALL}")
            
            print(f"{Fore.CYAN}Fingerprint completo do bot {i}:{Style.RESET_ALL}\n")
            
            # Mostrar cada detalhe do fingerprint
            for key, value in fingerprint.items():
                print(f"{Fore.YELLOW}{key}:{Style.RESET_ALL} {value}")
            
            # Mostrar detalhes da sessão
            print(f"\n{Fore.CYAN}Detalhes da Sessão {i}:{Style.RESET_ALL}")
            print(f"Timeout: {session.timeout}")
            print(f"Verify SSL: {session.verify}")
            print(f"Trust Env: {session.trust_env}")
            
            print("=" * 100)
        
        # Fechar todas as sessões
        session_manager.close_all()
        print(f"\n{Fore.GREEN}✅ Todas as sessões fechadas com sucesso{Style.RESET_ALL}")
        
        print(f"\nTodos os dados foram registrados no arquivo de log: {log_file}")
        print("=" * 100)
        time.sleep(60)
    except Exception as e:
        logging.error(f"Erro durante os testes: {e}")
        print(f"{Fore.RED}❌ Erro durante a execução. Verifique o arquivo de log: {log_file}{Style.RESET_ALL}")