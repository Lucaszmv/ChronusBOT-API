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
from modules.utils.utils_proxy_manager import ProxyManager

logger = logging.getLogger(__name__)

# Adiciona o diretório raiz do projeto ao PYTHONPATH
root_dir = str(Path(__file__).parent.parent.parent)
sys.path.append(root_dir)

# Inicializar o Colorama
init()

class SessionManager:
    """
    Gerenciador de sessões HTTP individuais para cada bot.
    """
    
    def __init__(self):
        self.sessions: Dict[int, requests.Session] = {}
        self.fingerprints: Dict[int, Dict[str, str]] = {}
        self.proxy_manager = ProxyManager()  # Inicializa uma única vez
        self.bot_proxies: Dict[int, str] = {}
        
    def get_session(self, bot_id: int) -> requests.Session:
        """
        Obtém ou cria uma sessão para um bot específico, sempre usando proxy.
        """
        backoff_time = 2
        
        while True:  # Loop infinito
            try:
                if bot_id not in self.sessions:
                    # Importações sob demanda para evitar circular import
                    from modules.core.core_fingerprint import get_fingerprint
                    
                    # Gera novo fingerprint
                    self.fingerprints[bot_id] = get_fingerprint()
                    
                    # Tenta obter proxy indefinidamente
                    proxy = None
                    while not proxy:
                        proxy = self.proxy_manager.get_proxy(bot_id)
                        if not proxy:
                            logger.warning(f"BOT {bot_id}: Aguardando proxy válido...")
                            time.sleep(backoff_time)
                    
                    self.bot_proxies[bot_id] = proxy
                    self.sessions[bot_id] = self.create_session(proxy)
                    
                    # Log detalhado da sessão
                    logger.info("", extra={
                        'session_details': {
                            'fingerprint': self.fingerprints[bot_id],
                            'proxy': proxy,
                            'user_agent': self.fingerprints[bot_id].get('User-Agent'),
                            'client_id': self.fingerprints[bot_id].get('Client-Id')
                        }
                    })
                    
                    logger.info(f"Nova sessão criada para bot {bot_id} com proxy {proxy}", extra={'terminal': False})
                    
                return self.sessions[bot_id]
                
            except Exception as e:
                logger.error(f"BOT {bot_id}: Erro ao obter sessão: {str(e)}")
                time.sleep(backoff_time)
                continue
    
    def get_fingerprint(self, bot_id: int) -> Dict[str, str]:
        """
        Obtém o fingerprint associado ao bot.
        
        Args:
            bot_id (int): ID do bot
            
        Returns:
            Dict[str, str]: Fingerprint do bot
        """
        return self.fingerprints.get(bot_id)
    
    def create_session(self, proxy: str) -> requests.Session:
        """
        Cria uma nova sessão com proxy obrigatório.
        """
        if not proxy:
            raise ValueError("Proxy é obrigatório para criar uma sessão")
        
        session = requests.Session()
        
        # Configura o proxy
        session.proxies = {
            'http': proxy,
            'https': proxy
        }
        
        # Desativa verificação SSL
        session.verify = False
        session.trust_env = False  # Impede uso de variáveis de ambiente (evita uso de proxy do sistema)
        session.timeout = (5, 10)
        
        # Suprime avisos SSL
        import urllib3
        urllib3.disable_warnings()
        
        return session
    
    def close_session(self, bot_id: int, release_proxy: bool = True):
        """
        Fecha a sessão de um bot específico e libera seu proxy.
        """
        if bot_id in self.sessions:
            self.sessions[bot_id].close()
            del self.sessions[bot_id]
            if release_proxy:
                self.proxy_manager.release_proxy(bot_id)
            
            if bot_id in self.bot_proxies:
                del self.bot_proxies[bot_id]
                
            logging.info(f"Sessão do bot {bot_id} fechada")
    
    def close_all(self):
        """
        Fecha todas as sessões ativas e libera seus proxies.
        """
        for bot_id in list(self.sessions.keys()):
            self.close_session(bot_id)
        logging.info("Todas as sessões foram fechadas")
    
    def get_proxy_info(self, bot_id: int) -> str:
        """
        Retorna informação do proxy atual do bot.
        
        Args:
            bot_id (int): ID do bot
            
        Returns:
            str: Informação do proxy ou 'Sem proxy' se não houver
        """
        if bot_id in self.bot_proxies:
            return self.bot_proxies[bot_id]
        return "Sem proxy"
    
    def create_session_with_data(self, bot_id: int, proxy: str, fingerprint: dict):
        """Cria uma nova sessão com proxy e fingerprint específicos."""
        self.fingerprints[bot_id] = fingerprint
        self.bot_proxies[bot_id] = proxy
        self.sessions[bot_id] = self.create_session(proxy)
        return self.sessions[bot_id]

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