"""
Módulo para gerenciamento de falhas e recuperação de erros.

Este módulo fornece classes e funções para monitorar, registrar e gerenciar
falhas durante a execução do bot, incluindo estratégias de recuperação.
"""

import logging
import time
from dataclasses import dataclass
from typing import Optional, Callable
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

@dataclass
class FailureStats:
    """Estatísticas de falhas para um bot específico."""
    consecutive_failures: int = 0
    total_failures: int = 0
    last_failure_time: Optional[datetime] = None
    last_success_time: Optional[datetime] = None
    last_error_message: str = ""

class FailureManager:
    """
    Gerenciador de falhas para monitorar e controlar erros dos bots.
    
    Attributes:
        max_consecutive_failures (int): Número máximo de falhas consecutivas permitidas
        bot_stats (dict): Dicionário mantendo estatísticas de falha por bot
        recovery_callback (callable): Função opcional chamada quando recuperação é necessária
    """
    
    def __init__(self, max_consecutive_failures: int = 5):
        self.max_consecutive_failures = max_consecutive_failures
        self.bot_stats: dict[int, FailureStats] = {}
        self.recovery_callback: Optional[Callable] = None
    
    def get_stats(self, bot_id: int) -> FailureStats:
        """Obtém ou cria estatísticas para um bot específico."""
        if bot_id not in self.bot_stats:
            self.bot_stats[bot_id] = FailureStats()
        return self.bot_stats[bot_id]
    
    def register_failure(self, bot_id: int, error_message: str) -> bool:
        """Registra uma falha e retorna True se atingiu o limite de falhas."""
        stats = self.get_stats(bot_id)
        stats.consecutive_failures += 1
        stats.total_failures += 1
        stats.last_failure_time = datetime.now(timezone.utc)
        stats.last_error_message = error_message
        
        logger.warning(
            f"BOT {bot_id}: Falha registrada (Consecutivas: {stats.consecutive_failures}, "
            f"Total: {stats.total_failures}) - {error_message}"
        )
        
        return stats.consecutive_failures >= self.max_consecutive_failures
    
    def register_success(self, bot_id: int):
        """Registra uma operação bem-sucedida, resetando o contador de falhas consecutivas."""
        stats = self.get_stats(bot_id)
        if stats.consecutive_failures > 0:
            logger.info(f"BOT {bot_id}: Recuperado após {stats.consecutive_failures} falhas consecutivas")
        
        stats.consecutive_failures = 0
        stats.last_success_time = datetime.now(timezone.utc)
    
    def should_restart_session(self, bot_id: int) -> bool:
        """Verifica se deve reiniciar baseado no número de falhas consecutivas."""
        stats = self.get_stats(bot_id)
        return stats.consecutive_failures >= self.max_consecutive_failures
    
    def reset_stats(self, bot_id: int):
        """Reseta todas as estatísticas para um bot específico."""
        self.bot_stats[bot_id] = FailureStats()
        logger.info(f"BOT {bot_id}: Estatísticas de falha resetadas")
    
    def get_failure_summary(self, bot_id: int) -> str:
        """Retorna um resumo das falhas do bot."""
        stats = self.get_stats(bot_id)
        return (
            f"Falhas consecutivas: {stats.consecutive_failures}\n"
            f"Total de falhas: {stats.total_failures}\n"
            f"Última falha: {stats.last_failure_time}\n"
            f"Último sucesso: {stats.last_success_time}\n"
            f"Última mensagem de erro: {stats.last_error_message}"
        )

# Instância global do gerenciador de falhas
failure_manager = FailureManager()

def get_failure_manager() -> FailureManager:
    """Retorna a instância global do gerenciador de falhas."""
    return failure_manager
