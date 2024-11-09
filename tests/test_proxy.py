"""
Testes para o módulo de gerenciamento de proxies.
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
    log_file = os.path.join(log_dir, f'test_proxy_{datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")}.log')
    
    logging.basicConfig(
        filename=log_file,
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    return log_file

def testar_proxy_manager():
    """Testa as funcionalidades do ProxyManager."""
    log_file = configurar_logging()
    
    try:
        print(f"{Fore.CYAN}Importando módulos...{Style.RESET_ALL}")
        from modules.utils.utils_proxy_manager import create_proxy_manager
        print(f"{Fore.GREEN}✅ Módulos importados com sucesso{Style.RESET_ALL}")
        
        print(f"\n{Fore.CYAN}=== Teste do Gerenciador de Proxies ==={Style.RESET_ALL}")
        print("=" * 70)
        
        # Criar instância do ProxyManager
        proxy_manager = create_proxy_manager()
        
        # Teste 1: Verificar carregamento de proxies
        print(f"\n{Fore.CYAN}Teste 1: Carregamento de Proxies{Style.RESET_ALL}")
        if proxy_manager.proxies:
            print(f"{Fore.GREEN}✅ {len(proxy_manager.proxies)} proxies carregados{Style.RESET_ALL}")
            logging.info(f"Carregados {len(proxy_manager.proxies)} proxies")
        else:
            print(f"{Fore.YELLOW}⚠️ Nenhum proxy carregado{Style.RESET_ALL}")
            logging.warning("Nenhum proxy carregado")
        print("-" * 50)
        
        # Teste 2: Obtenção de proxies para múltiplos bots
        print(f"\n{Fore.CYAN}Teste 2: Atribuição de Proxies{Style.RESET_ALL}")
        for bot_id in range(3):
            proxy = proxy_manager.get_proxy(bot_id)
            if proxy:
                print(f"{Fore.GREEN}✅ Bot {bot_id} obteve proxy: {proxy}{Style.RESET_ALL}")
                logging.info(f"Bot {bot_id} obteve proxy: {proxy}")
            else:
                print(f"{Fore.YELLOW}⚠️ Bot {bot_id} não obteve proxy{Style.RESET_ALL}")
                logging.warning(f"Bot {bot_id} não obteve proxy")
        print("-" * 50)
        
        # Teste 3: Verificar consistência de proxies
        print(f"\n{Fore.CYAN}Teste 3: Consistência de Proxies{Style.RESET_ALL}")
        for bot_id in range(3):
            proxy1 = proxy_manager.get_proxy(bot_id)
            proxy2 = proxy_manager.get_proxy(bot_id)
            if proxy1 == proxy2:
                print(f"{Fore.GREEN}✅ Bot {bot_id} manteve o mesmo proxy{Style.RESET_ALL}")
                logging.info(f"Bot {bot_id} manteve o mesmo proxy: {proxy1}")
            else:
                print(f"{Fore.RED}❌ Bot {bot_id} obteve proxies diferentes{Style.RESET_ALL}")
                logging.error(f"Bot {bot_id} obteve proxies diferentes: {proxy1} != {proxy2}")
        print("-" * 50)
        
        # Teste 4: Liberação de proxies
        print(f"\n{Fore.CYAN}Teste 4: Liberação de Proxies{Style.RESET_ALL}")
        for bot_id in range(3):
            proxy_manager.release_proxy(bot_id)
            if bot_id not in proxy_manager.bot_proxies:
                print(f"{Fore.GREEN}✅ Proxy do Bot {bot_id} liberado com sucesso{Style.RESET_ALL}")
                logging.info(f"Proxy do Bot {bot_id} liberado com sucesso")
            else:
                print(f"{Fore.RED}❌ Falha ao liberar proxy do Bot {bot_id}{Style.RESET_ALL}")
                logging.error(f"Falha ao liberar proxy do Bot {bot_id}")
        print("-" * 50)
        
        print("\n" + "=" * 70)
        print(f"{Fore.GREEN}✅ Todos os testes concluídos com sucesso!{Style.RESET_ALL}")
        
    except Exception as e:
        logging.error(f"Erro durante teste: {e}")
        print(f"\n{Fore.RED}❌ Erro durante o teste: {e}{Style.RESET_ALL}")
        print(f"\n{Fore.YELLOW}Detalhes do erro:{Style.RESET_ALL}")
        print(traceback.format_exc())
        
    finally:
        print(f"\nLog file: {log_file}")
        print("=" * 70)

if __name__ == "__main__":
    testar_proxy_manager() 