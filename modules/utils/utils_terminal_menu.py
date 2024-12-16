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
        
    def get_center_padding(self) -> int:
        """Calcula o padding necessário para centralizar o menu."""
        terminal_width = os.get_terminal_size().columns
        menu_width = 80  # Largura total do menu
        return max(0, (terminal_width - menu_width) // 2)
        
    def centered_print(self, text: str):
        """Imprime texto centralizado no terminal."""
        padding = " " * self.get_center_padding()
        print(f"{padding}{text}")

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
        
        # Calcula o padding central
        padding = " " * self.get_center_padding()
        
        # Cabeçalho
        print(f"{padding}         ╔═════════════════════════════════════════════════════════╗")
        print(f"{padding}         ║               ChronusBOT-API - Twitch Stream Viewer     ║")
        print(f"{padding}         ╚═════════════════════════════════════════════════════════╝")
        
        # Estatísticas Gerais
        print(f"{padding}     ┌──────────┬───────────┬─────────┬─────────────┬─────────┬───────────┐")
        print(f"{padding}     │ Channels │ Total     │ Total   │ Runtime     │ Proxies │ Total Ads │")
        print(f"{padding}     │ Importes │ Completed │ Threads │ Elapsed     │ Loaded  │ Pre/Mid   │")
        print(f"{padding}     ├──────────┼───────────┼─────────┼─────────────┼─────────┼───────────┤")
        print(f"{padding}     │ {stats['channels']:<8} │ {stats['completed']:<9} │ {stats['threads']:<7} │ {self.get_runtime():<11} │ {stats['proxies']:<7} │ {stats['ads_per_hour']:<9} │")
        print(f"{padding}     └──────────┴───────────┴─────────┴─────────────┴─────────┴───────────┘")
        
        # Status dos Bots
        print(f"{padding}┌──────┬──────────────┬──────────────┬──────────────────┬─────────┬─────────────┐")
        print(f"{padding}│ BOT  │ STATUS       │ CHANNEL      │ USER IP          │ PRE/MID │ UPTIME      │")
        print(f"{padding}├──────┼──────────────┼──────────────┼──────────────────┼─────────┼─────────────┤")
        
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
            
            user_ip = bot.get('user_ip', 'Waiting IP...')
            if user_ip is None:
                user_ip = 'Waiting IP...'
            
            if len(user_ip) > 16:
                user_ip = user_ip[:13] + '...'
                
            channel = bot.get('channel', '')
            if len(channel) > 12:
                channel = channel[:9] + '...'
            else:
                channel = channel.ljust(12)
            
            print(f"{padding}│ {bot['id']:02d}   │ {status_color} {bot['status']:<10}{Style.RESET_ALL} │ {channel} │ {user_ip:<16} │ {bot['ads']:<7} │ {uptime:<11} │")
            
        print(f"{padding}└──────┴──────────────┴──────────────┴──────────────────┴─────────┴─────────────┘")

def create_terminal_menu() -> TerminalMenu:
    """Cria uma nova instância do menu do terminal."""
    return TerminalMenu() 