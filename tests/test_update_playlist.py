"""
Testes para o módulo de atualização de playlists.
"""

import sys
import os
from pathlib import Path
import logging
from datetime import datetime, timezone
import time
import traceback
from collections import deque
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
    log_file = os.path.join(log_dir, f'test_playlist_updater_{datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")}.log')
    
    logging.basicConfig(
        filename=log_file,
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    return log_file

def testar_playlist_updater():
    """Testa as funcionalidades do módulo de atualização de playlists."""
    log_file = configurar_logging()
    
    try:
        print(f"{Fore.CYAN}Importando módulos...{Style.RESET_ALL}")
        from modules.core.core_session import session_manager
        from modules.core.core_token import obter_playback_access_token
        from modules.utils.utils_update_playlist import atualizar_playlist
        print(f"{Fore.GREEN}✅ Módulos importados com sucesso{Style.RESET_ALL}")
        
        print(f"\n{Fore.CYAN}=== Teste do Atualizador de Playlist ==={Style.RESET_ALL}")
        print("=" * 70)
        
        # Criar sessão de teste
        bot_id = 999  # ID específico para testes
        session = session_manager.get_session(bot_id)
        fingerprint = session_manager.get_fingerprint(bot_id)
        
        print(f"\n{Fore.CYAN}Teste 1: Configuração da Sessão{Style.RESET_ALL}")
        print(f"{Fore.GREEN}✅ Sessão criada com bot_id: {bot_id}{Style.RESET_ALL}")
        if session.proxies:
            proxy_info = session.proxies.get('http', 'Nenhum proxy configurado')
            print(f"{Fore.GREEN}✅ Proxy configurado: {proxy_info}{Style.RESET_ALL}")
        print("-" * 50)
        
        # Solicitar canal para teste
        canal_nome = input(f"{Fore.YELLOW}Digite o nome do canal da Twitch para testar: {Style.RESET_ALL}")
        
        print(f"\n{Fore.CYAN}Teste 2: Obtenção de Token{Style.RESET_ALL}")
        token_data = obter_playback_access_token(canal_nome, fingerprint, bot_id)
        if token_data:
            print(f"{Fore.GREEN}✅ Token de acesso obtido com sucesso{Style.RESET_ALL}")
            logging.info("Token de acesso obtido com sucesso")
        else:
            raise Exception("Falha ao obter token de acesso")
        print("-" * 50)
        
        print(f"\n{Fore.CYAN}Teste 3: Atualização de Playlist{Style.RESET_ALL}")
        print(f"{Fore.YELLOW}Iniciando processo de atualização (limitado a 2 atualizações)...{Style.RESET_ALL}")
        
        resultado = atualizar_playlist(canal_nome, token_data, bot_id, max_atualizacoes=2)
        
        if resultado:
            print("\n" + "=" * 50)
            print(f"{Fore.CYAN}Resumo da Atualização:{Style.RESET_ALL}")
            print(f"{Fore.GREEN}✅ {resultado['atualizacoes']}/{2} atualizações realizadas{Style.RESET_ALL}")
            print(f"- Segmentos únicos encontrados: {resultado['segmentos_encontrados']}")
            print(f"- Tentativas necessárias: {resultado['tentativas']}")
            
            print(f"\n{Fore.YELLOW}Última playlist obtida (primeiras 10 linhas):{Style.RESET_ALL}")
            linhas = resultado['ultima_playlist'].split('\n')[:10]
            for i, linha in enumerate(linhas, 1):
                print(f"   {i}: {linha}")
            
            if len(resultado['ultima_playlist'].split('\n')) > 10:
                print(f"   ... ({len(resultado['ultima_playlist'].split('\n')) - 10} linhas omitidas)")
            print("=" * 50)
        else:
            raise Exception("Falha no processo de atualização")
        
        # Fechar a sessão
        session_manager.close_session(bot_id)
        print(f"{Fore.GREEN}✅ Sessão de teste fechada{Style.RESET_ALL}")
        
        print("\n" + "=" * 70)
        print(f"{Fore.GREEN}✅ Todos os testes concluídos com sucesso!{Style.RESET_ALL}")
        
    except Exception as e:
        logging.error(f"Erro durante teste: {e}")
        print(f"\n{Fore.RED}❌ Erro durante o teste: {e}{Style.RESET_ALL}")
        print(f"\n{Fore.YELLOW}Detalhes do erro:{Style.RESET_ALL}")
        print(traceback.format_exc())
        
    finally:
        if 'bot_id' in locals():
            session_manager.close_session(bot_id)
        print(f"\nLog file: {log_file}")
        print("=" * 70)

if __name__ == "__main__":
    testar_playlist_updater()