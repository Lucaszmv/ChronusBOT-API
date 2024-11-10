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
        """Configura o sistema de logging com formatação colorida e arquivo."""
        # Criar diretório de logs
        log_dir = os.path.join(Path(__file__).parent.parent.parent, 'logs')
        os.makedirs(log_dir, exist_ok=True)

        # Nome do arquivo de log com timestamp
        log_file = os.path.join(
            log_dir, 
            f'chronusbot_{datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")}.log'
        )

        # Configuração básica para arquivo
        logging.basicConfig(
            filename=log_file,
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )

        # Handler para console com cores
        console = logging.StreamHandler()
        console.setLevel(logging.INFO)
        console.setFormatter(self.ColoredFormatter())
        
        # Configurar logger raiz
        root_logger = logging.getLogger()
        root_logger.addHandler(console)

    class ColoredFormatter(logging.Formatter):
        """Formatador personalizado para colorir as mensagens de log."""
        def format(self, record):
            # Adicionar cores baseado no nível do log
            if record.levelno == logging.INFO:
                record.msg = f"{INFO_COLOR}{record.msg}{RESET}"
            elif record.levelno == logging.WARNING:
                record.msg = f"{WARNING_COLOR}{record.msg}{RESET}"
            elif record.levelno == logging.ERROR:
                record.msg = f"{ERROR_COLOR}{record.msg}{RESET}"
            elif record.levelno == logging.DEBUG:
                record.msg = f"{SUCCESS_COLOR}{record.msg}{RESET}"
                
            return super().format(record)

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