"""
Módulo para monitoramento do status dos bots.
"""
import os
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict
import threading
from colorama import Fore, Style
import time

class BotMonitor:
    def __init__(self):
        self.lock = threading.Lock()
        self.bot_status: Dict[int, str] = {}
        
        # Criar diretório de logs se não existir
        self.log_dir = os.path.join(Path(__file__).parent.parent.parent, 'logs')
        os.makedirs(self.log_dir, exist_ok=True)
        
        # Nome do arquivo com timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.log_file = os.path.join(self.log_dir, f'bot_status_{timestamp}.log')
        
        # Configurar logger específico
        self.logger = logging.getLogger('bot_monitor')
        self.logger.setLevel(logging.INFO)
        
        # Handler para arquivo
        file_handler = logging.FileHandler(self.log_file, encoding='utf-8')
        file_handler.setFormatter(
            logging.Formatter('%(asctime)s - %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
        )
        self.logger.addHandler(file_handler)
        
        # Adicionar atualização mais frequente
        self.last_update = time.time()
        self.update_interval = 1  # Atualiza a cada 1 segundo
    
    def update_status(self, bot_id: int, status: str, details: str = ""):
        """Atualiza o status de um bot e registra no log."""
        with self.lock:
            self.bot_status[bot_id] = status
            
            message = f"BOT {bot_id:02d} | {status}"
            if details:
                message += f" | {details}"
            
            self.logger.info(message)
            
            # Força atualização do resumo sempre
            self._update_summary()
            self.last_update = time.time()
    
    def _update_summary(self):
        """Atualiza arquivo de resumo com status atual de todos os bots."""
        summary_file = os.path.join(self.log_dir, 'bots_status_atual.txt')
        with open(summary_file, 'w', encoding='utf-8', buffering=1) as f:  # buffering=1 para forçar flush
            f.write(f"=== Status dos Bots === {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            for bot_id in sorted(self.bot_status.keys()):
                status = self.bot_status[bot_id]
                f.write(f"BOT {bot_id:02d}: {status}\n")
            f.write("\n===================\n")
            f.flush()  # Força a escrita no arquivo
            os.fsync(f.fileno())  # Força o sistema operacional a escrever no disco

# Instância global do monitor
bot_monitor = BotMonitor()

def get_bot_monitor():
    """Retorna a instância global do monitor de bots."""
    return bot_monitor 