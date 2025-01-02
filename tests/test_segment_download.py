"""
Testes para o módulo de download de segmentos de stream.
"""

import sys
import os
from pathlib import Path
import logging
from datetime import datetime, timezone
import time
import traceback
from collections import deque
import random
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
    log_file = os.path.join(log_dir, f'test_segment_download_{datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")}.log')
    
    logging.basicConfig(
        filename=log_file,
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    return log_file

def testar_segment_download():
    """Testa as funcionalidades do módulo de download de segmentos."""
    log_file = configurar_logging()
    
    try:
        print(f"{Fore.CYAN}Importando módulos...{Style.RESET_ALL}")
        from modules.core.core_session import session_manager
        from modules.core.core_token import obter_playback_access_token
        from modules.core.core_get_playlist import obter_playlist_m3u8
        from modules.utils.utils_segment_download import (
            obter_playlist_qualidade,
            simular_download_segmento,
            iniciar_downloader,
            segmentos_baixados
        )
        print(f"{Fore.GREEN}✅ Módulos importados com sucesso{Style.RESET_ALL}")
        
        print(f"\n{Fore.CYAN}=== Teste do Downloader de Segmentos ==={Style.RESET_ALL}")
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
        
        print(f"\n{Fore.CYAN}Teste 3: Obtenção de Playlist{Style.RESET_ALL}")
        playlist_principal = obter_playlist_m3u8(canal_nome, token_data, bot_id)
        if playlist_principal:
            print(f"{Fore.GREEN}✅ Playlist principal obtida com sucesso{Style.RESET_ALL}")
            logging.info("Playlist principal obtida com sucesso")
        else:
            raise Exception("Falha ao obter playlist principal")
        print("-" * 50)
        
        print(f"\n{Fore.CYAN}Teste 4: Seleção de Qualidade{Style.RESET_ALL}")
        links_qualidade = [linha for linha in playlist_principal.split('\n') 
                          if linha.startswith('https://') and '.m3u8' in linha]
        if links_qualidade:
            link_qualidade = random.choice(links_qualidade)
            print(f"{Fore.GREEN}✅ Qualidade selecionada: {link_qualidade}{Style.RESET_ALL}")
            logging.info(f"Qualidade selecionada: {link_qualidade}")
        else:
            raise Exception("Nenhuma qualidade disponível")
        print("-" * 50)
        
        print(f"\n{Fore.CYAN}Teste 5: Download de Segmentos{Style.RESET_ALL}")
        playlist_qualidade = obter_playlist_qualidade(link_qualidade, fingerprint, bot_id)
        if playlist_qualidade:
            segmentos = [linha for linha in playlist_qualidade.split('\n') 
                        if linha.startswith('http') and linha.endswith('.ts')]
            print(f"{Fore.GREEN}✅ {len(segmentos)} segmentos encontrados{Style.RESET_ALL}")
            
            # Criar fila de teste
            fila_teste = deque(segmentos[:5])  # Testa apenas 5 segmentos
            print(f"{Fore.GREEN}✅ Fila de teste criada com {len(fila_teste)} segmentos{Style.RESET_ALL}")
            
            # Iniciar downloader
            iniciar_downloader(fila_teste, bot_id)
            
            # Aguardar processamento
            tempo_espera = 0
            while len(fila_teste) > 0 and tempo_espera < 30:
                print(f"Segmentos restantes: {len(fila_teste)}")
                time.sleep(1)
                tempo_espera += 1
            
            if len(segmentos_baixados) > 0:
                print(f"{Fore.GREEN}✅ {len(segmentos_baixados)} segmentos baixados com sucesso{Style.RESET_ALL}")
                logging.info(f"{len(segmentos_baixados)} segmentos baixados com sucesso")
            else:
                print(f"{Fore.RED}❌ Nenhum segmento foi baixado{Style.RESET_ALL}")
        else:
            raise Exception("Falha ao obter playlist de qualidade")
        print("-" * 50)
        
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
    testar_segment_download() 