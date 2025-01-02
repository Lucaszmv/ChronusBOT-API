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
from modules.utils.utils_logger import get_logger
from modules.utils.utils_proxy_manager import ProxyManager
import random
from urllib.parse import urlparse

logger = get_logger(__name__)

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
        Obtém ou cria uma sessão para um bot específico.
        
        Args:
            bot_id (int): ID único do bot
            
        Returns:
            requests.Session: Sessão HTTP para o bot
        """
        if bot_id not in self.sessions:
            # Importações sob demanda para evitar circular import
            from modules.core.core_fingerprint import get_fingerprint
            
            # Adiciona apenas estas 3 linhas de delay
            wait_time = random.uniform(5, 10)
            logger.info(f"BOT {bot_id}: Aguardando {wait_time:.1f}s antes de iniciar nova sessão...")
            time.sleep(wait_time)
            
            # Gerar novo fingerprint para o bot
            self.fingerprints[bot_id] = get_fingerprint()
            
            # Obtém proxy do gerenciador - MODIFICAÇÃO AQUI
            proxy = None
            max_attempts = 3
            attempt = 0
            
            while attempt < max_attempts:
                proxy = self.proxy_manager.get_proxy(bot_id)
                if proxy:
                    break
                attempt += 1
                time.sleep(2)
                
            if not proxy:
                logger.error(f"BOT {bot_id}: Falha ao obter proxy após {max_attempts} tentativas")
                return None
                
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
        Suporta proxies HTTP, HTTPS, SOCKS4 e SOCKS5.
        """
        if not proxy:
            logger.error("Tentativa de criar sessão sem proxy")
            return None
        
        session = requests.Session()
        
        try:
            # Parse do proxy para identificar o protocolo
            if '://' not in proxy:
                # Se não tem protocolo, assume http://
                proxy = 'http://' + proxy
                
            parsed = urlparse(proxy)
            protocol = parsed.scheme.lower()
            
            # Configura o proxy de acordo com o protocolo
            if protocol in ('http', 'https'):
                proxy_dict = {
                    'http': proxy,
                    'https': proxy
                }
            elif protocol in ('socks4', 'socks5'):
                # Para SOCKS, usamos o mesmo proxy para HTTP e HTTPS
                proxy_dict = {
                    'http': proxy,
                    'https': proxy
                }
                # Força o uso do protocolo SOCKS
                session.proxies = proxy_dict
            else:
                logger.error(f"Protocolo de proxy não suportado: {protocol}")
                return None
            
            session.proxies = proxy_dict
            
            # Força o uso do proxy
            session.trust_env = False  # Desabilita variáveis de ambiente
            session.verify = False
            session.timeout = (5, 10)
            
            # Adiciona um adaptador personalizado para forçar uso do proxy
            session.mount('http://', requests.adapters.HTTPAdapter(max_retries=3))
            session.mount('https://', requests.adapters.HTTPAdapter(max_retries=3))
            
            # Suprime avisos SSL
            import urllib3
            urllib3.disable_warnings()
            
            return session
            
        except Exception as e:
            logger.error(f"Erro ao criar sessão com proxy {proxy}: {str(e)}")
            return None
    
    def close_session(self, bot_id: int):
        """
        Fecha a sessão de um bot específico e libera seu proxy.
        """
        if bot_id in self.sessions:
            self.sessions[bot_id].close()
            del self.sessions[bot_id]
            del self.fingerprints[bot_id]
            
            # Libera o proxy através do ProxyManager
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