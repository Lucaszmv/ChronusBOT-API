"""
Módulo para monitoramento do status dos bots.
"""
import logging
import threading
from typing import Dict
from datetime import datetime
from modules.utils.utils_logger import get_logger
from modules.utils.utils_proxy_manager import ProxyManager

logger = get_logger(__name__)

class BotStatus:
    """Status possíveis para os bots."""
    INICIANDO = "Iniciando"
    CONECTANDO = "Conectando"
    ASSISTINDO = "Assistindo"
    RECONECTANDO = "Reconectando"
    DESCONECTADO = "Desconectado"
    ERRO = "Erro"

class BotMonitor:
    """Monitora e registra o status dos bots."""
    
    def __init__(self):
        self.bot_status: Dict[int, dict] = {}
        self.lock = threading.Lock()

    def update_status(self, bot_id: int, status: str, details: str = ""):
        """
        Atualiza o status de um bot.
        """
        with self.lock:
            # Preserva o user_ip se já existir
            current_user_ip = None
            if bot_id in self.bot_status:
                current_user_ip = self.bot_status[bot_id].get('user_ip')
                start_time = self.bot_status[bot_id].get('start_time', datetime.now())
            else:
                start_time = datetime.now()
            
            # Atualiza informações do bot
            self.bot_status[bot_id] = {
                'status': status,
                'details': details,
                'last_update': datetime.now(),
                'start_time': start_time,
                'uptime': self._get_uptime(bot_id),
                'user_ip': current_user_ip  # Mantém o IP atual
            }
            
            # Log da mudança de status
            message = f"{status}"
            if details:
                message += f" | {details}"
            
            logger.info(message, extra={'bot_id': int(bot_id)})

    def _get_uptime(self, bot_id: int) -> str:
        """Calcula o uptime do bot."""
        if bot_id not in self.bot_status:
            return "0m"
            
        start_time = self.bot_status[bot_id].get('start_time', datetime.now())
        delta = datetime.now() - start_time
        
        hours = delta.seconds // 3600
        minutes = (delta.seconds % 3600) // 60
        
        if hours > 0:
            return f"{hours}h {minutes}m"
        return f"{minutes}m"

    def update_bot_ip(self, bot_id: int, ip: str):
        """Atualiza o IP do bot nas estatísticas."""
        with self.lock:
            if bot_id not in self.bot_status:
                self.bot_status[bot_id] = {
                    'status': 'ONLINE',
                    'details': '',
                    'last_update': datetime.now(),
                    'start_time': datetime.now(),
                    'uptime': '0m'
                }
            
            previous_ip = self.bot_status[bot_id].get('user_ip')
            self.bot_status[bot_id]['user_ip'] = ip
            
            logger.info("", extra={
                'ip_update': True,
                'bot_id': bot_id,
                'previous_ip': previous_ip,
                'new_ip': ip
            })

    def get_bot_status(self, bot_id: int) -> dict:
        """Retorna o status completo de um bot."""
        with self.lock:
            return self.bot_status.get(bot_id, {})

# Instância global do monitor
bot_monitor = BotMonitor()

def get_bot_monitor():
    """Retorna a instância global do monitor de bots."""
    return bot_monitor 