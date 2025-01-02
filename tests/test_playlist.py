"""
Testes para o módulo de obtenção de playlists M3U8 da Twitch.
"""

import sys
import os
from pathlib import Path
import logging
from datetime import datetime, timezone
import time
import traceback
from colorama import Fore, Style, init

# Adiciona o diretório raiz ao PYTHONPATH
root_dir = str(Path(__file__).parent.parent)
sys.path.append(root_dir)

# Inicializa o colorama
init(autoreset=True)

def configurar_logging():
    """Configura o sistema de logging para testes."""
    log_dir = os.path.join(root_dir, 'logs')
    os.makedirs(log_dir, exist_ok=True)
    log_file = os.path.join(log_dir, f'test_playlist_{datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")}.log')
    
    logging.basicConfig(
        filename=log_file,
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    return log_file

def testar_obter_playlist():
    """Testa a obtenção de playlist M3U8 para um canal."""
    log_file = configurar_logging()
    
    try:
        print(f"{Fore.CYAN}Importando módulos...{Style.RESET_ALL}")
        from modules.core.core_session import session_manager
        from modules.core.core_token import obter_playback_access_token
        from modules.core.core_get_playlist import obter_playlist_m3u8
        print(f"{Fore.GREEN}✅ Módulos importados com sucesso{Style.RESET_ALL}")
        
        print(f"\n{Fore.CYAN}=== Teste de Obtenção de Playlist M3U8 ==={Style.RESET_ALL}")
        print("=" * 70)
        
        # Criar uma sessão de teste
        bot_id = 999  # ID específico para testes
        session = session_manager.get_session(bot_id)
        fingerprint = session_manager.get_fingerprint(bot_id)
        
        print(f"{Fore.CYAN}Sessão de teste criada com bot_id: {bot_id}{Style.RESET_ALL}")
        print(f"{Fore.CYAN}Fingerprint gerado:{Style.RESET_ALL}")
        for key, value in fingerprint.items():
            print(f"{Fore.YELLOW}{key}:{Style.RESET_ALL} {value}")
        print("=" * 70)
        
        # Exibir informações do proxy
        if session.proxies:
            proxy_info = session.proxies.get('http', 'Nenhum proxy configurado')
            print(f"{Fore.CYAN}Proxy em uso: {proxy_info}{Style.RESET_ALL}")
        else:
            print(f"{Fore.YELLOW}⚠️ Nenhum proxy configurado{Style.RESET_ALL}")
        print("=" * 70)
        
        # Solicitar canal para teste
        canal_teste = input(f"{Fore.YELLOW}Digite o nome do canal da Twitch para testar: {Style.RESET_ALL}")
        
        # Obter token de acesso
        token_data = obter_playback_access_token(canal_teste, fingerprint, bot_id)
        if not token_data:
            raise Exception(f"Não foi possível obter o token de acesso para o canal {canal_teste}")
        
        print(f"{Fore.GREEN}✅ Token de acesso obtido com sucesso{Style.RESET_ALL}")
        
        # Obter playlist
        playlist = obter_playlist_m3u8(canal_teste, token_data, bot_id)
        if not playlist:
            raise Exception(f"Não foi possível obter a playlist M3U8 para o canal {canal_teste}")
        
        print(f"{Fore.GREEN}✅ Playlist M3U8 obtida com sucesso{Style.RESET_ALL}")
        print("=" * 70)
        print(f"{Fore.YELLOW}Primeiras 10 linhas da Playlist M3U8:{Style.RESET_ALL}")
        print("\n".join(playlist.split("\n")[:10]))
        
        # Fechar a sessão de teste
        session_manager.close_session(bot_id)
        print(f"\n{Fore.GREEN}✅ Sessão de teste fechada{Style.RESET_ALL}")
        
        print("\n" + "=" * 70)
        print(f"{Fore.GREEN}✅ Todos os testes concluídos com sucesso!{Style.RESET_ALL}")
        
    except Exception as e:
        logging.error(f"Erro durante teste: {e}")
        print(f"\n{Fore.RED}❌ Erro durante o teste: {e}{Style.RESET_ALL}")
        print(f"\n{Fore.YELLOW}Detalhes do erro:{Style.RESET_ALL}")
        print(traceback.format_exc())
        
    finally:
        # Garantir que a sessão seja fechada
        if 'bot_id' in locals():
            session_manager.close_session(bot_id)
        print(f"\nLog file: {log_file}")
        print("=" * 70)

if __name__ == "__main__":
    testar_obter_playlist() 