"""
Módulo para gerenciamento do menu do terminal.
"""
import os
import time
from datetime import datetime, timedelta
from typing import List, Dict
from colorama import Fore, Back, Style, init

# Inicializa o colorama
init()

class TerminalMenu:
    def __init__(self):
        self.start_time = datetime.now()
        self.events: List[Dict] = []
        self.max_events = 5
        
    def add_event(self, bot_id: int, message: str, event_type: str = 'info'):
        """Adiciona um novo evento à lista."""
        self.events.insert(0, {
            'time': datetime.now(),
            'bot_id': bot_id,
            'message': message,
            'type': event_type
        })
        if len(self.events) > self.max_events:
            self.events.pop()

    def get_runtime(self) -> str:
        """Calcula o tempo de execução total desde o início do programa."""
        delta = datetime.now() - self.start_time
        total_seconds = int(delta.total_seconds())
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        seconds = total_seconds % 60
        return f"{hours:02d}h {minutes:02d}m {seconds:02d}s"

    def get_status_color(self, status: str) -> str:
        """Retorna a cor apropriada para cada status."""
        status_colors = {
            'ONLINE': Fore.GREEN + '●',
            'RECONECT': Fore.YELLOW + '⚠',
            'ERRO': Fore.RED + '✕'
        }
        return status_colors.get(status, Fore.WHITE + '○')

    def get_event_color(self, event_type: str) -> str:
        """Retorna a cor apropriada para cada tipo de evento."""
        event_colors = {
            'success': Fore.GREEN,
            'warning': Fore.YELLOW,
            'error': Fore.RED,
            'info': Fore.CYAN
        }
        return event_colors.get(event_type, Fore.WHITE)

    def clear_screen(self):
        """Limpa a tela do terminal."""
        os.system('cls' if os.name == 'nt' else 'clear')

    def render(self, stats: Dict, bot_status: List[Dict]):
        """Renderiza o menu completo."""
        self.clear_screen()
        
        # Remove qualquer linha em branco no início
        print(end='', flush=True)
        
        # Cabeçalho
        print("  ╔═════════════════════════════════════════════════════════╗")
        print("  ║               ChronusBOT-API - Twitch Stream Viewer     ║")
        print("  ╚═════════════════════════════════════════════════════════╝")
        
        # Estatísticas Gerais
        print("  ┌──────────┬───────────┬─────────┬─────────────┬─────────┬───────────┐")
        print("  │ Channels │ Total     │ Total   │ Runtime     │ Proxies │ Total Ads │")
        print("  │ Importes │ Completed │ Threads │ Elapsed     │ Loaded  │ Pre/Mid   │")
        print("  ├──────────┼───────────┼─────────┼─────────────┼─────────┼───────────┤")
        print(f"  │ {stats['channels']:<8} │ {stats['completed']:<9} │ {stats['threads']:<7} │ {self.get_runtime():<11} │ {stats['proxies']:<7} │ {stats['ads_per_hour']:<9} │")
        print("  └──────────┴───────────┴─────────┴─────────────┴─────────┴───────────┘")
        
        # Status dos Bots
        print("  ┌──────────┬───────────┬───────────┬─────────┬─────────────┐")
        print("  │ BOT      │ STATUS    │ CHANNEL   │ PRE/MID │ UPTIME      │")
        print("  ├──────────┼───────────┼───────────┼─────────┼─────────────┤")
        
        for bot in bot_status:
            status_color = self.get_status_color(bot['status'])
            if 'start_time' in bot:
                delta = datetime.now() - bot['start_time']
                total_seconds = int(delta.total_seconds())
                hours = total_seconds // 3600
                minutes = (total_seconds % 3600) // 60
                seconds = total_seconds % 60
                uptime = f"{hours:02d}h {minutes:02d}m {seconds:02d}s"
            else:
                uptime = bot['uptime']
            
            print(f"  │ BOT {bot['id']:02d}   │ {status_color} {bot['status']:<7}{Style.RESET_ALL} │ {bot['channel']:<9} │ {bot['ads']:<7} │ {uptime:<11} │")
            
        print("  └──────────┴───────────┴───────────┴─────────┴─────────────┘")
        
def create_terminal_menu() -> TerminalMenu:
    """Cria uma nova instância do menu do terminal."""
    return TerminalMenu() 