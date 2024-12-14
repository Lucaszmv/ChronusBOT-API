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
        # Ignora mensagens de proxy desnecessárias
        if 'proxy' in record.name.lower():
            msg = record.msg.replace('[32m', '').replace('[36m', '').replace('[0m', '')
            if "Testando" in msg or "Precisamos" in msg:
                return ""
        
        # Limita tamanho da mensagem
        record.msg = str(record.msg)[:200]
        
        # Adiciona cores
        if record.levelno == logging.INFO:
            record.msg = f"{INFO_COLOR}{record.msg}{RESET}"
        elif record.levelno == logging.WARNING:
            record.msg = f"{WARNING_COLOR}{record.msg}{RESET}"
        elif record.levelno == logging.ERROR:
            record.msg = f"{ERROR_COLOR}{record.msg}{RESET}"
        
        formatted = f"[{record.levelname[0]}] {record.msg}"
        
        # Retorna apenas se houver conteúdo
        if formatted and formatted.strip():
            return formatted
        return ""

class ProxyFormatter(logging.Formatter):
    """Formatador específico para logs de proxy."""
    
    def __init__(self):
        super().__init__()
        self.last_test_id = 0
        self.current_test = {}
    
    def format(self, record):
        if hasattr(record, 'proxy_details'):
            details = record.proxy_details
            
            # Se é um novo teste
            if not self.current_test or self.current_test.get('needed') != details.get('needed'):
                self.last_test_id += 1
                self.current_test = {
                    'id': self.last_test_id,
                    'total': details.get('total'),
                    'needed': details.get('needed'),
                    'valid_proxies': [],
                    'start_time': time.time()
                }
                record.msg = (
                    f"\n{'='*80}\n"
                    f"TESTE DE PROXIES #{self.current_test['id']}\n"
                    f"{'='*80}\n"
                    f"Objetivo: {self.current_test['needed']} proxies válidos de {self.current_test['total']} disponíveis\n"
                )
            else:
                # Atualiza lista de proxies válidos
                new_proxies = details.get('valid_proxies', [])
                if new_proxies:
                    for proxy in new_proxies:
                        if proxy not in self.current_test['valid_proxies']:
                            self.current_test['valid_proxies'].append(proxy)
                            record.msg = f"✓ {proxy['address']} - {proxy['time']:.2f}s"
                
                # Se é o último log do teste (tem total_time)
                if details.get('total_time'):
                    record.msg = (
                        f"\nRESUMO FINAL:\n"
                        f"Proxies válidos encontrados: {len(self.current_test['valid_proxies'])}\n"
                        f"Tempo total de teste......: {details['total_time']:.2f}s\n"
                        f"{'='*80}\n"
                    )
                    self.current_test = {}  # Limpa teste atual
            
        elif hasattr(record, 'proxy_allocation'):
            details = record.proxy_allocation
            record.msg = (
                f"\n{'='*80}\n"
                f"PROXY ALOCADO\n"
                f"Bot {details.get('bot_id'):02d} ➜ {details.get('proxy')}\n"
                f"Pool atual: {details.get('pool_size')} proxies disponíveis\n"
                f"{'='*80}\n"
            )
        
        return record.msg.strip() or ""

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
        root_logger = logging.getLogger()
        for handler in root_logger.handlers[:]:
            root_logger.removeHandler(handler)
            
        root_logger.setLevel(logging.INFO)
        
        # Cria pasta da sessão
        base_log_dir = Path(__file__).parent.parent.parent / 'logs'
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        session_dir = base_log_dir / f'session_{timestamp}'
        session_dir.mkdir(parents=True, exist_ok=True)
        
        # Handler para log de sessão (detalhes técnicos)
        session_log = session_dir / 'session.log'
        session_handler = logging.handlers.RotatingFileHandler(
            session_log,
            maxBytes=10*1024*1024,
            backupCount=5,
            encoding='utf-8'
        )
        session_handler.setFormatter(FileFormatter())
        
        # Handler para log de proxy
        proxy_log = session_dir / 'proxy.log'
        proxy_handler = logging.handlers.RotatingFileHandler(
            proxy_log,
            maxBytes=10*1024*1024,
            backupCount=5,
            encoding='utf-8'
        )
        proxy_handler.setFormatter(ProxyFormatter())
        
        # Handler para console
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(ConsoleFormatter())
        
        # Configura filtros para cada handler
        class ProxyFilter(logging.Filter):
            def filter(self, record):
                return 'proxy' in record.name.lower()
            
        class SessionFilter(logging.Filter):
            """Filtra mensagens relacionadas a requisições HTTP e detalhes de sessão."""
            def filter(self, record):
                return (hasattr(record, 'session_details') or 
                        hasattr(record, 'request_details') or 
                        hasattr(record, 'playlist_details') or
                        hasattr(record, 'segment_details'))
        
        proxy_handler.addFilter(ProxyFilter())
        session_handler.addFilter(SessionFilter())
        
        # Adiciona handlers
        root_logger.addHandler(session_handler)
        root_logger.addHandler(proxy_handler)
        root_logger.addHandler(console_handler)
        
        # Salva informações da sessão
        self.session_dir = session_dir

def get_logger(name: str) -> logging.Logger:
    """Obtém um logger configurado."""
    LoggerManager()
    return logging.getLogger(name)

# Criar uma instância global do LoggerManager
logger_manager = LoggerManager() 