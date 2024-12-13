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

class SessionManager:
    """
    Gerenciador de sessões HTTP individuais para cada bot.
    """
    
    def __init__(self):
        self.sessions: Dict[int, requests.Session] = {}
        self.fingerprints: Dict[int, Dict[str, str]] = {}
        self.proxy_manager = None  # Será inicializado sob demanda
        self.bot_proxies: Dict[int, str] = {}
        
    def get_session(self, bot_id: int) -> requests.Session:
        """
        Obtém ou cria uma sessão para um bot específico.
        
        Args:
            bot_id (int): ID único do bot
            
        Returns:
            requests.Session: Sessão HTTP para o bot
        """
        if bot_id not in self.sessions:
            # Importações sob demanda para evitar circular import
            from modules.core.core_fingerprint import get_fingerprint
            from modules.utils.utils_proxy_manager import create_proxy_manager
            
            # Inicializa proxy_manager se necessário
            if self.proxy_manager is None:
                self.proxy_manager = create_proxy_manager()
            
            # Gerar novo fingerprint para o bot
            self.fingerprints[bot_id] = get_fingerprint()
            
            # Obtém proxy do gerenciador
            proxy = self.proxy_manager.get_proxy(bot_id)
            if proxy:
                self.bot_proxies[bot_id] = proxy
                
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
        
        # Desativa verificação SSL
        session.verify = False
        session.trust_env = False
        session.timeout = (5, 10)
        
        # Suprime avisos SSL
        import urllib3
        urllib3.disable_warnings()
        
        return session
    
    def close_session(self, bot_id: int):
        """
        Fecha a sessão de um bot específico e libera seu proxy.
        """
        if bot_id in self.sessions:
            self.sessions[bot_id].close()
            del self.sessions[bot_id]
            del self.fingerprints[bot_id]
            if bot_id in self.bot_proxies:
                del self.bot_proxies[bot_id]
            self.proxy_manager.release_proxy(bot_id)
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