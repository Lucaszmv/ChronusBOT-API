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

class FileFormatter(logging.Formatter):
    """Formatador para arquivos de log."""
    
    def __init__(self):
        super().__init__()
        self.fmt = '%(asctime)s - %(levelname)s - %(message)s'
        self.datefmt = '%Y-%m-%d %H:%M:%S'

    def format(self, record):
        # Remove mensagens vazias
        if not record.msg.strip():
            return ""
            
        # Formata a mensagem com base no tipo
        if hasattr(record, 'session_details'):
            details = record.session_details
            return (
                f"{self.formatTime(record)} - INFO - Nova sessão criada para bot {details['bot_id']} "
                f"com proxy {details['proxy']}"
            )
            
        elif hasattr(record, 'token_response'):
            return (
                f"{self.formatTime(record)} - INFO - BOT {record.bot_id}: "
                f"Token obtido - IP: {record.user_ip}"
            )
            
        elif hasattr(record, 'ip_update'):
            return (
                f"{self.formatTime(record)} - INFO - BOT {record.bot_id}: "
                f"IP atualizado: {record.new_ip}"
            )
            
        elif hasattr(record, 'session_restart'):
            details = record.session_restart
            return (
                f"{self.formatTime(record)} - WARNING - BOT {details['bot_id']}: "
                f"Reiniciando sessão - Motivo: {details['reason']}"
            )
            
        # Mensagens padrão
        if record.levelname == 'INFO' and 'Limites ajustados' in record.msg:
            return (
                f"{self.formatTime(record)} - INFO - {record.msg}"
            )
            
        # Remove mensagens de debug e logs vazios
        if record.levelname == 'DEBUG' or not record.msg.strip():
            return ""
            
        return super().format(record)

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
        # Cria pasta de logs
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_dir = Path(__file__).parent.parent.parent / 'logs'
        log_dir.mkdir(parents=True, exist_ok=True)
        
        # Arquivo único de log
        log_file = log_dir / f'chronus_{timestamp}.log'
        
        # Configura logger raiz
        root_logger = logging.getLogger()
        root_logger.setLevel(logging.INFO)
        
        # Remove handlers existentes
        for handler in root_logger.handlers[:]:
            root_logger.removeHandler(handler)
        
        # Handler para arquivo
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setFormatter(FileFormatter())
        root_logger.addHandler(file_handler)
        
        # Handler para console com filtro
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(logging.Formatter('%(message)s'))
        
        class TerminalFilter(logging.Filter):
            def filter(self, record):
                return not (hasattr(record, 'terminal') and record.terminal is False)
                
        console_handler.addFilter(TerminalFilter())
        root_logger.addHandler(console_handler)
        
        return log_dir

def get_logger(name: str) -> logging.Logger:
    """Obtém um logger configurado."""
    LoggerManager()
    return logging.getLogger(name)

# Criar uma instância global do LoggerManager
logger_manager = LoggerManager() 