"""
Módulo para gerenciamento centralizado de logs.
"""
import os
import logging
from datetime import datetime, timezone
from pathlib import Path
from colorama import Fore, Style, init

# Inicializa o Colorama
init()

# Configurações de cores
INFO_COLOR = Fore.CYAN
SUCCESS_COLOR = Fore.GREEN
WARNING_COLOR = Fore.YELLOW
ERROR_COLOR = Fore.RED
RESET = Style.RESET_ALL

class LoggerManager:
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
        """Configura o sistema de logging com formatação mais concisa."""
        log_dir = os.path.join(Path(__file__).parent.parent.parent, 'logs')
        os.makedirs(log_dir, exist_ok=True)

        log_file = os.path.join(
            log_dir, 
            f'chronusbot_{datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")}.log'
        )

        # Formato mais conciso para arquivo
        file_formatter = logging.Formatter('%(asctime)s [%(levelname).1s] %(message).200s')
        
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(file_formatter)
        
        # Handler para console com cores e formato conciso
        console = logging.StreamHandler()
        console.setFormatter(self.ColoredFormatter())
        
        # Configurar logger raiz
        root_logger = logging.getLogger()
        root_logger.setLevel(logging.INFO)
        root_logger.addHandler(file_handler)
        root_logger.addHandler(console)

    class ColoredFormatter(logging.Formatter):
        def format(self, record):
            # Limita tamanho da mensagem
            record.msg = str(record.msg)[:200]
            
            if record.levelno == logging.INFO:
                record.msg = f"{INFO_COLOR}{record.msg}{RESET}"
            elif record.levelno == logging.WARNING:
                record.msg = f"{WARNING_COLOR}{record.msg}{RESET}"
            elif record.levelno == logging.ERROR:
                record.msg = f"{ERROR_COLOR}{record.msg}{RESET}"
            
            return f"[{record.levelname[0]}] {record.msg}"

def get_logger(name: str) -> logging.Logger:
    """
    Obtém um logger configurado com o nome especificado.
    
    Args:
        name (str): Nome do logger (geralmente __name__ do módulo)
        
    Returns:
        logging.Logger: Logger configurado
    """
    LoggerManager()  # Garante que o sistema de logging está configurado
    return logging.getLogger(name)

# Criar uma instância global do LoggerManager
logger_manager = LoggerManager() 