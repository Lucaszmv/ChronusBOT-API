"""
Testes para o módulo de gerenciamento de sessões.
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
    log_file = os.path.join(log_dir, f'test_session_{datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")}.log')

    logging.basicConfig(
        filename=log_file,
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    return log_file

def testar_session_manager():
    """Testa as funcionalidades do SessionManager."""
    log_file = configurar_logging()
    bot_ids = []
    
    try:
        print(f"{Fore.CYAN}Importando módulos...{Style.RESET_ALL}")
        
        # Importações necessárias
        from modules.core.core_session import session_manager
        print(f"{Fore.GREEN}✅ session_manager importado{Style.RESET_ALL}")
        
        print(f"\n{Fore.CYAN}=== Teste do SessionManager ==={Style.RESET_ALL}")
        print("=" * 70)
        
        # Teste 1: Criar múltiplas sessões
        print(f"\n{Fore.CYAN}Teste 1: Criando múltiplas sessões...{Style.RESET_ALL}")
        num_sessoes = int(input(f"{Fore.YELLOW}Digite o número de sessões para teste: {Style.RESET_ALL}"))
        
        for i in range(num_sessoes):
            bot_id = i + 1
            bot_ids.append(bot_id)
            
            print(f"\n{Fore.CYAN}Criando sessão para bot {bot_id}...{Style.RESET_ALL}")
            session = session_manager.get_session(bot_id)
            fingerprint = session_manager.get_fingerprint(bot_id)
            
            print(f"{Fore.GREEN}✅ Sessão criada para bot {bot_id}{Style.RESET_ALL}")
            
            # Exibir informações da sessão
            print(f"\n{Fore.CYAN}Detalhes da Sessão:{Style.RESET_ALL}")
            print(f"Timeout: {session.timeout}")
            print(f"Verify SSL: {session.verify}")
            print(f"Trust Env: {session.trust_env}")
            
            # Exibir proxy se existir
            if session.proxies:
                proxy = session.proxies.get('http', 'Nenhum')
                print(f"{Fore.CYAN}Proxy:{Style.RESET_ALL} {proxy}")
            
            # Exibir fingerprint
            print(f"\n{Fore.CYAN}Fingerprint gerado:{Style.RESET_ALL}")
            for key, value in fingerprint.items():
                print(f"{Fore.YELLOW}{key}:{Style.RESET_ALL} {value}")
                logging.info(f"Bot {bot_id} - Fingerprint - {key}: {value}")
            
            print("-" * 50)
            time.sleep(1)  # Pequena pausa entre criações
        
        # Teste 2: Verificar reutilização de sessões
        print(f"\n{Fore.CYAN}Teste 2: Verificando reutilização de sessões...{Style.RESET_ALL}")
        for bot_id in bot_ids:
            session1 = session_manager.get_session(bot_id)
            session2 = session_manager.get_session(bot_id)
            
            if session1 is session2:
                print(f"{Fore.GREEN}✅ Sessão reutilizada corretamente para bot {bot_id}{Style.RESET_ALL}")
            else:
                print(f"{Fore.RED}❌ Falha na reutilização da sessão para bot {bot_id}{Style.RESET_ALL}")
        
        # Teste 3: Fechar sessões individuais
        print(f"\n{Fore.CYAN}Teste 3: Fechando sessões individuais...{Style.RESET_ALL}")
        for bot_id in bot_ids[:-1]:  # Fecha todas menos a última
            session_manager.close_session(bot_id)
            print(f"{Fore.GREEN}✅ Sessão do bot {bot_id} fechada{Style.RESET_ALL}")
        
        # Teste 4: Fechar todas as sessões
        print(f"\n{Fore.CYAN}Teste 4: Fechando todas as sessões restantes...{Style.RESET_ALL}")
        session_manager.close_all()
        print(f"{Fore.GREEN}✅ Todas as sessões fechadas{Style.RESET_ALL}")
        
        print("\n" + "=" * 70)
        print(f"{Fore.GREEN}✅ Todos os testes concluídos com sucesso!{Style.RESET_ALL}")
        
    except Exception as e:
        logging.error(f"Erro durante teste: {e}")
        print(f"\n{Fore.RED}❌ Erro durante o teste: {e}{Style.RESET_ALL}")
        print(f"\n{Fore.YELLOW}Detalhes do erro:{Style.RESET_ALL}")
        print(traceback.format_exc())
        
    finally:
        # Garantir que todas as sessões sejam fechadas
        session_manager.close_all()
        print(f"\n{Fore.GREEN}✅ Limpeza final realizada{Style.RESET_ALL}")
        print(f"Log file: {log_file}")
        print("=" * 70)

if __name__ == "__main__":
    testar_session_manager() 