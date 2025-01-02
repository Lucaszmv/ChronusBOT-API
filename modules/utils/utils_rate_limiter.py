"""
Módulo para controle de taxa de requisições e recursos com ajuste automático.
"""

import threading
import time
import logging
import math
from typing import Optional, Dict
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class AdaptiveRateLimiter:
    """
    Gerenciador de taxa de requisições com ajuste automático baseado no número de bots.
    """
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(AdaptiveRateLimiter, cls).__new__(cls)
        return cls._instance
    
    def __init__(self):
        if not hasattr(self, 'initialized'):
            self.active_bots = set()
            self.request_counts: Dict[int, Dict[str, int]] = {}
            self.last_request_time: Dict[int, Dict[str, datetime]] = {}
            
            # Semáforos dinâmicos
            self.playlist_semaphore = None
            self.segment_semaphore = None
            
            # Métricas de performance
            self.error_counts = {}
            self.last_adjustment = datetime.now()
            self.adjustment_interval = 30  # Ajusta a cada 30 segundos
            
            # Lock para ajustes
            self.adjust_lock = threading.Lock()
            
            self.initialized = True
            
            # Inicializa com valores padrão
            self._adjust_limits(1)
    
    def _calculate_limits(self, num_bots: int) -> tuple[int, int]:
        """
        Calcula limites ideais baseado no número de bots.
        """
        # Limite de playlist: raiz quadrada do número de bots, mínimo 5, máximo 50
        playlist_limit = min(max(int(math.sqrt(num_bots) * 2), 5), 50)
        
        # Limite de segmentos: número de bots / 2, mínimo 10, máximo 100
        segment_limit = min(max(int(num_bots / 2), 10), 100)
        
        return playlist_limit, segment_limit
    
    def _calculate_intervals(self, num_bots: int) -> tuple[float, float]:
        """
        Calcula intervalos ideais baseado no número de bots.
        """
        # Base: 0.2s + ajuste baseado no número de bots
        base_interval = 0.2 + (num_bots / 1000)
        
        # Playlist: intervalo maior
        playlist_interval = base_interval * 2
        
        # Segmentos: intervalo menor
        segment_interval = base_interval
        
        return playlist_interval, segment_interval
    
    def _adjust_limits(self, num_bots: int):
        """
        Ajusta limites e intervalos baseado no número de bots.
        """
        with self.adjust_lock:
            # Calcula novos limites
            playlist_limit, segment_limit = self._calculate_limits(num_bots)
            
            # Calcula novos intervalos
            self.playlist_interval, self.segment_interval = self._calculate_intervals(num_bots)
            
            # Atualiza semáforos
            self.playlist_semaphore = threading.Semaphore(playlist_limit)
            self.segment_semaphore = threading.Semaphore(segment_limit)
            
            logger.info(
                f"Limites ajustados para {num_bots} bots - "
                f"Playlist: {playlist_limit}, Segmentos: {segment_limit}"
            )
    
    def register_bot(self, bot_id: int):
        """
        Registra um novo bot no sistema.
        """
        if bot_id not in self.active_bots:
            self.active_bots.add(bot_id)
            self._adjust_limits(len(self.active_bots))
            
            # Inicializa contadores
            self.request_counts[bot_id] = {'playlist': 0, 'segment': 0}
            self.last_request_time[bot_id] = {'playlist': None, 'segment': None}
            self.error_counts[bot_id] = 0
    
    def unregister_bot(self, bot_id: int):
        """
        Remove um bot do sistema.
        """
        if bot_id in self.active_bots:
            self.active_bots.remove(bot_id)
            self._adjust_limits(len(self.active_bots))
    
    def acquire(self, bot_id: int, request_type: str = 'segment') -> bool:
        """
        Tenta adquirir permissão para fazer uma requisição.
        """
        # Registra bot se necessário
        if bot_id not in self.active_bots:
            self.register_bot(bot_id)
        
        # Seleciona semáforo e intervalo
        semaphore = (self.playlist_semaphore if request_type == 'playlist' 
                    else self.segment_semaphore)
        interval = (self.playlist_interval if request_type == 'playlist' 
                   else self.segment_interval)
        
        # Verifica intervalo
        last_time = self.last_request_time[bot_id][request_type]
        if last_time:
            elapsed = datetime.now() - last_time
            if elapsed.total_seconds() < interval:
                time.sleep(interval - elapsed.total_seconds())
        
        # Tenta adquirir semáforo
        timeout = 5 if request_type == 'playlist' else 2
        acquired = semaphore.acquire(timeout=timeout)
        
        if acquired:
            self.request_counts[bot_id][request_type] += 1
            self.last_request_time[bot_id][request_type] = datetime.now()
            logger.debug(
                f"Bot {bot_id}: Permissão concedida para {request_type} "
                f"(Total: {self.request_counts[bot_id][request_type]})"
            )
        else:
            logger.warning(f"Bot {bot_id}: Permissão negada para {request_type}")
            self.error_counts[bot_id] += 1
            
            # Verifica necessidade de ajuste
            if datetime.now() - self.last_adjustment > timedelta(seconds=self.adjustment_interval):
                self._adjust_for_errors()
        
        return acquired
    
    def _adjust_for_errors(self):
        """
        Ajusta limites baseado em erros recentes.
        """
        with self.adjust_lock:
            total_errors = sum(self.error_counts.values())
            num_bots = len(self.active_bots)
            
            if total_errors > num_bots * 0.2:  # Se mais de 20% dos bots têm erros
                # Aumenta intervalos
                self.playlist_interval *= 1.2
                self.segment_interval *= 1.2
                logger.info("Intervalos aumentados devido a erros")
            
            # Reset contadores
            self.error_counts.clear()
            self.last_adjustment = datetime.now()
    
    def release(self, bot_id: int, request_type: str = 'segment'):
        """
        Libera o recurso após uso.
        """
        semaphore = (self.playlist_semaphore if request_type == 'playlist' 
                    else self.segment_semaphore)
        semaphore.release()
        logger.debug(f"Bot {bot_id}: Recurso de {request_type} liberado")
    
    def get_stats(self, bot_id: int = None) -> Dict:
        """
        Retorna estatísticas de uso.
        """
        if bot_id is not None:
            return {
                'playlist_requests': self.request_counts[bot_id]['playlist'],
                'segment_requests': self.request_counts[bot_id]['segment'],
                'last_playlist': self.last_request_time[bot_id]['playlist'],
                'last_segment': self.last_request_time[bot_id]['segment'],
                'errors': self.error_counts.get(bot_id, 0)
            }
        else:
            return {
                'active_bots': len(self.active_bots),
                'playlist_interval': self.playlist_interval,
                'segment_interval': self.segment_interval,
                'total_errors': sum(self.error_counts.values())
            }

# Instância global do rate limiter
rate_limiter = AdaptiveRateLimiter()

def get_rate_limiter() -> AdaptiveRateLimiter:
    """Retorna a instância global do rate limiter."""
    return rate_limiter 