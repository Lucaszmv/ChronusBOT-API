"""
Testes para o módulo de geração de fingerprints.
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
    log_file = os.path.join(log_dir, f'test_fingerprint_{datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")}.log')

    logging.basicConfig(
        filename=log_file,
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    return log_file

def testar_geracao_fingerprint():
    """Testa a geração de fingerprints."""
    log_file = configurar_logging()
    
    try:
        print(f"{Fore.CYAN}Importando módulos...{Style.RESET_ALL}")
        
        # Importações necessárias
        from modules.core.core_fingerprint import (
            get_fingerprint,
            CLIENT_ID,
            get_platform_from_user_agent,
            get_browser_info,
            generate_client_version
        )
        print(f"{Fore.GREEN}✅ Módulos importados com sucesso{Style.RESET_ALL}")
        
        print(f"\n{Fore.CYAN}=== Teste de Geração de Fingerprints ==={Style.RESET_ALL}")
        print("=" * 70)
        
        # Teste 1: Verificar CLIENT_ID
        print(f"\n{Fore.CYAN}Teste 1: Verificando CLIENT_ID...{Style.RESET_ALL}")
        print(f"CLIENT_ID: {CLIENT_ID}")
        logging.info(f"CLIENT_ID verificado: {CLIENT_ID}")
        
        # Teste 2: Gerar múltiplos fingerprints
        print(f"\n{Fore.CYAN}Teste 2: Gerando múltiplos fingerprints...{Style.RESET_ALL}")
        num_fingerprints = int(input(f"{Fore.YELLOW}Digite o número de fingerprints para teste: {Style.RESET_ALL}"))
        
        for i in range(num_fingerprints):
            print(f"\n{Fore.GREEN}✅ Fingerprint {i+1} gerado:{Style.RESET_ALL}")
            fingerprint = get_fingerprint()
            
            # Testar e exibir cada componente do fingerprint
            for key, value in fingerprint.items():
                print(f"{Fore.YELLOW}{key}:{Style.RESET_ALL} {value}")
                logging.info(f"Fingerprint {i+1} - {key}: {value}")
            
            # Teste 3: Verificar plataforma
            platform = get_platform_from_user_agent(fingerprint['User-Agent'])
            print(f"\n{Fore.CYAN}Plataforma detectada:{Style.RESET_ALL} {platform}")
            
            # Teste 4: Verificar informações do navegador
            browser_info = get_browser_info(fingerprint['User-Agent'])
            print(f"{Fore.CYAN}Informações do navegador:{Style.RESET_ALL}")
            print(f"Browser: {browser_info[0]}")
            if browser_info[1]:
                print(f"Brand: {browser_info[1]}")
            if browser_info[2]:
                print(f"Engine: {browser_info[2]}")
            
            # Teste 5: Verificar client version
            client_version = generate_client_version()
            print(f"{Fore.CYAN}Client Version gerado:{Style.RESET_ALL} {client_version}")
            
            print("-" * 50)
            time.sleep(1)  # Pequena pausa entre gerações
        
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
    testar_geracao_fingerprint() 