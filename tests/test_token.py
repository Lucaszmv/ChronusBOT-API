"""
Testes para o módulo de token.
"""

import sys
import os
from pathlib import Path
import logging
from datetime import datetime, timezone
import time
import json
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
    log_file = os.path.join(log_dir, f'test_token_{datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")}.log')

    logging.basicConfig(
        filename=log_file,
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    return log_file

def testar_obter_token():
    """Testa a obtenção de token de acesso."""
    log_file = configurar_logging()
    bot_id = None
    
    try:
        print(f"{Fore.CYAN}Importando módulos...{Style.RESET_ALL}")
        
        # Importações necessárias
        from modules.core.core_session import session_manager
        print(f"{Fore.GREEN}✅ session_manager importado{Style.RESET_ALL}")
        
        from modules.core.core_token import obter_playback_access_token
        print(f"{Fore.GREEN}✅ core_token importado{Style.RESET_ALL}")
        
        print(f"\n{Fore.CYAN}=== Teste de Obtenção de Token ==={Style.RESET_ALL}")
        print("=" * 70)
        
        # Obtém informações do usuário
        canal_nome = input(f"{Fore.YELLOW}Digite o nome do canal da Twitch: {Style.RESET_ALL}")
        logging.info(f"Iniciando teste para o canal: {canal_nome}")
        
        # Cria sessão e obtém fingerprint
        bot_id = 999  # ID específico para testes
        session = session_manager.get_session(bot_id)
        fingerprint = session_manager.get_fingerprint(bot_id)
        
        print(f"\n{Fore.CYAN}Fingerprint gerado:{Style.RESET_ALL}")
        for key, value in fingerprint.items():
            print(f"{Fore.YELLOW}{key}:{Style.RESET_ALL} {value}")
            logging.info(f"Fingerprint - {key}: {value}")
        print("=" * 70)
        
        # Obtém token de acesso
        print(f"\n{Fore.CYAN}Obtendo token de acesso...{Style.RESET_ALL}")
        inicio = time.time()
        token = obter_playback_access_token(canal_nome, fingerprint, bot_id)
        tempo_total = time.time() - inicio
        
        if not token:
            raise Exception("Falha ao obter token de acesso")
        
        print(f"{Fore.GREEN}✅ Token obtido com sucesso em {tempo_total:.2f} segundos:{Style.RESET_ALL}")
        print(f"\nDetalhes do token:")
        print(f"{Fore.CYAN}Signature:{Style.RESET_ALL} {token.get('signature', 'N/A')}")
        print(f"{Fore.CYAN}Value:{Style.RESET_ALL}")
        try:
            value_dict = json.loads(token.get('value', '{}'))
            for key, value in value_dict.items():
                print(f"  {Fore.YELLOW}{key}:{Style.RESET_ALL} {value}")
        except json.JSONDecodeError:
            print(f"  {token.get('value', 'N/A')}")
        
        print("\n" + "=" * 70)
        
    except Exception as e:
        logging.error(f"Erro durante teste: {e}")
        print(f"\n{Fore.RED}❌ Erro durante o teste: {e}{Style.RESET_ALL}")
        print(f"\n{Fore.YELLOW}Detalhes do erro:{Style.RESET_ALL}")
        print(traceback.format_exc())
        
    finally:
        if bot_id is not None:
            session_manager.close_session(bot_id)
            print(f"\n{Fore.GREEN}✅ Sessão de teste encerrada{Style.RESET_ALL}")
        print(f"Log file: {log_file}")
        print("=" * 70)

if __name__ == "__main__":
    testar_obter_token()