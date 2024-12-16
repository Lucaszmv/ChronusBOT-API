"""
Módulo para gerenciamento centralizado de logs.
"""

import os
import logging
import logging.handlers
from datetime import datetime, timezone
from pathlib import Path
from colorama import Fore, Style, init
import time

# Inicializa o Colorama
init()

# Configurações de cores para o terminal
INFO_COLOR = Fore.CYAN
SUCCESS_COLOR = Fore.GREEN
WARNING_COLOR = Fore.YELLOW
ERROR_COLOR = Fore.RED
RESET = Style.RESET_ALL

class ProxyFilter(logging.Filter):
    def filter(self, record):
        return 'proxy' in record.name.lower()
        
class SessionFilter(logging.Filter):
    def filter(self, record):
        return (hasattr(record, 'session_details') or 
                hasattr(record, 'request_details') or 
                hasattr(record, 'playlist_details') or
                hasattr(record, 'segment_details'))

class FileFormatter(logging.Formatter):
    """Formatador para arquivos de log."""
    
    def __init__(self):
        super().__init__()
        self.fmt = (
            "[%(asctime)s] "
            "%(levelname)-8s "
            "%(message)s"
        )
        self.datefmt = '%Y-%m-%d %H:%M:%S'

    def format(self, record):
        # Formata a mensagem com base no tipo de log
        if hasattr(record, 'token_response'):
            # Log específico para resposta do token
            record.msg = (
                f"\nTOKEN RESPONSE - BOT {record.bot_id}:\n"
                f"Response: {record.token_response}\n"
                f"Extracted IP: {record.user_ip}\n"
                f"{'='*80}"
            )
        elif hasattr(record, 'ip_update'):
            # Log específico para atualização de IP
            record.msg = (
                f"BOT {record.bot_id}: "
                f"IP Update - Previous: {record.previous_ip}, "
                f"New: {record.new_ip}"
            )
        
        return super().format(record)

class ConsoleFormatter(logging.Formatter):
    """Mantém o formato original para console com cores."""
    
    def format(self, record):
        # Não exibe nenhuma mensagem no console
        return ""

class ProxyFormatter(logging.Formatter):
    """Formatador específico para logs de proxy."""
    
    def __init__(self):
        super().__init__()
    
    def format(self, record):
        if hasattr(record, 'proxy_load'):
            details = record.proxy_load
            return (
                f"\n{'='*82}\n"
                f"SISTEMA DE PROXY INICIADO\n"
                f"{'='*82}\n"
                f"Total de Proxies Carregados: {details.get('total_proxies')}\n"
                f"Arquivo: {details.get('proxy_file')}\n"
                f"{'='*82}\n"
            )
        elif hasattr(record, 'proxy_allocation'):
            details = record.proxy_allocation
            return (
                f"{'='*82}\n"
                f"{datetime.now().strftime('%H:%M:%S')} | "
                f"INFO    | BOT {details.get('bot_id')} usando proxy: {details.get('proxy')}\n"
                f"Proxies Disponíveis: {details.get('pool_size')}\n"
                f"{'='*82}"
            )
        elif record.msg:
            return record.msg
        return ""

class LoggerManager:
    """Gerenciador centralizado de logs do sistema."""
    
    _instance = None
    _initialized = False
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(LoggerManager, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        if not LoggerManager._initialized:
            self.setup_logging()
            LoggerManager._initialized = True

    def setup_logging(self):
        """Configura o sistema de logging."""
        # Cria pasta da sessão
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_dir = Path(__file__).parent.parent.parent / 'logs' / f'session_{timestamp}'
        log_dir.mkdir(parents=True, exist_ok=True)
        
        # Arquivo de sessão
        session_handler = logging.FileHandler(
            log_dir / 'session.log',
            mode='a',
            encoding='utf-8'
        )
        session_handler.setFormatter(FileFormatter())
        session_handler.setLevel(logging.INFO)
        
        # Arquivo de proxy
        proxy_handler = logging.FileHandler(
            log_dir / 'proxy.log',
            mode='a',
            encoding='utf-8'
        )
        proxy_handler.setFormatter(FileFormatter())
        proxy_handler.setLevel(logging.INFO)
        
        # Configura logger raiz
        root_logger = logging.getLogger()
        root_logger.setLevel(logging.INFO)
        
        # Remove handlers existentes
        for handler in root_logger.handlers[:]:
            root_logger.removeHandler(handler)
        
        # Adiciona os novos handlers
        root_logger.addHandler(session_handler)
        root_logger.addHandler(proxy_handler)
        
        return log_dir

def get_logger(name: str) -> logging.Logger:
    """Obtém um logger configurado."""
    LoggerManager()
    return logging.getLogger(name)

# Criar uma instância global do LoggerManager
logger_manager = LoggerManager() 