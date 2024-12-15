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
            "%(asctime)s | "
            "%(levelname)-7s | "
            "%(bot_id)s"
            "%(message)s"
        )
        self.datefmt = '%H:%M:%S'

    def format(self, record):
        # Formata bot_id se existir
        if not hasattr(record, 'bot_id'):
            record.bot_id = ''
        elif record.bot_id:
            try:
                bot_id = int(record.bot_id)
                record.bot_id = f"BOT {bot_id:02d} | "
            except (ValueError, TypeError):
                record.bot_id = ''

        # Formata detalhes técnicos
        if hasattr(record, 'request_details'):
            details = record.request_details
            record.msg = (
                f"\n{'='*80}\n"
                f"TOKEN REQUEST\n"
                f"{'='*80}\n"
                f"URL.........: {details.get('url')}\n"
                f"Method......: {details.get('method')}\n"
                f"\nHEADERS ENVIADOS:\n{self._format_dict(details.get('headers_sent', {}))}\n"
                f"\nHEADERS RECEBIDOS:\n{self._format_dict(details.get('headers_received', {}))}\n"
                f"\nRESPONSE:\n"
                f"Status......: {details.get('status_code')} {details.get('reason')}\n"
                f"Body........: {details.get('response', '')[:200]}...\n"
                f"{'='*80}\n"
            )
        elif hasattr(record, 'playlist_details'):
            details = record.playlist_details
            record.msg = (
                f"\n{'='*80}\n"
                f"PLAYLIST REQUEST\n"
                f"{'='*80}\n"
                f"URL.........: {details.get('url')}\n"
                f"Method......: {details.get('method')}\n"
                f"\nHEADERS ENVIADOS:\n{self._format_dict(details.get('headers_sent', {}))}\n"
                f"\nHEADERS RECEBIDOS:\n{self._format_dict(details.get('headers_received', {}))}\n"
                f"\nRESPONSE:\n"
                f"Status......: {details.get('status_code')} {details.get('reason')}\n"
                f"Playlist....: \n{self._format_m3u8(details.get('response', ''))}\n"
                f"{'='*80}\n"
            )
        elif hasattr(record, 'session_details'):
            details = record.session_details
            record.msg = (
                f"\n{'='*80}\n"
                f"NOVA SESSÃO INICIADA\n"
                f"{'='*80}\n"
                f"Bot ID......: {details.get('bot_id')}\n"
                f"Proxy.......: {details.get('proxy')}\n"
                f"User-Agent..: {details.get('user_agent')}\n"
                f"Client-ID...: {details.get('client_id')}\n"
                f"{'='*80}\n"
            )

        # Formata a mensagem final
        self._style._fmt = self.fmt
        formatted_msg = super().format(record) if record.msg else ""
        return formatted_msg.strip() or ""

    def _format_dict(self, d, indent=2):
        """Formata dicionário de forma legível"""
        return '\n'.join(f"{' '*indent}{k:<30}: {v}" for k, v in d.items())

    def _format_m3u8(self, content, max_lines=10):
        """Formata conteúdo M3U8 de forma legível"""
        if not content:
            return "Vazio"
        lines = content.split('\n')
        formatted = '\n'.join(f"    {line}" for line in lines[:max_lines])
        if len(lines) > max_lines:
            formatted += f"\n    ... (+{len(lines) - max_lines} linhas)"
        return formatted

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
        # Configura o logger raiz para não mostrar nada no console
        root_logger = logging.getLogger()
        root_logger.setLevel(logging.CRITICAL)
        
        # Remove todos os handlers existentes
        for handler in root_logger.handlers[:]:
            root_logger.removeHandler(handler)
        
        # Cria pasta da sessão
        base_log_dir = Path(__file__).parent.parent.parent / 'logs'
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        session_dir = base_log_dir / f'session_{timestamp}'
        session_dir.mkdir(parents=True, exist_ok=True)
        
        # Handler para arquivo (mantém logs normalmente)
        session_log = session_dir / 'session.log'
        session_handler = logging.handlers.RotatingFileHandler(
            session_log,
            maxBytes=10*1024*1024,
            backupCount=5,
            encoding='utf-8'
        )
        session_handler.setFormatter(FileFormatter())
        session_handler.setLevel(logging.INFO)
        
        # Handler para proxy (mantém logs normalmente)
        proxy_log = session_dir / 'proxy.log'
        proxy_handler = logging.handlers.RotatingFileHandler(
            proxy_log,
            maxBytes=10*1024*1024,
            backupCount=5,
            encoding='utf-8'
        )
        proxy_handler.setFormatter(ProxyFormatter())
        proxy_handler.setLevel(logging.INFO)
        
        # Não adiciona console handler
        
        # Configura filtros
        proxy_handler.addFilter(ProxyFilter())
        session_handler.addFilter(SessionFilter())
        
        # Adiciona apenas os handlers de arquivo
        root_logger.addHandler(session_handler)
        root_logger.addHandler(proxy_handler)
        
        # Configura todos os loggers existentes para não mostrarem nada no console
        for name in logging.root.manager.loggerDict:
            logger = logging.getLogger(name)
            logger.setLevel(logging.CRITICAL)
            # Remove qualquer console handler existente
            for handler in logger.handlers[:]:
                if isinstance(handler, logging.StreamHandler) and not isinstance(handler, logging.FileHandler):
                    logger.removeHandler(handler)
        
        self.session_dir = session_dir

def get_logger(name: str) -> logging.Logger:
    """Obtém um logger configurado."""
    LoggerManager()
    return logging.getLogger(name)

# Criar uma instância global do LoggerManager
logger_manager = LoggerManager() 