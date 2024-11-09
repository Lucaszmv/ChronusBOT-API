"""
Módulo para geração de fingerprints de navegador para a API da Twitch.

Este módulo contém constantes e funções para gerar fingerprints de navegador
utilizados em toda a aplicação para interagir com a API da Twitch.

Functions:
    gerar_device_id: Gera um ID de dispositivo aleatório.
    get_platform_from_user_agent: Detecta a plataforma a partir do User-Agent.
    get_browser_info: Obtém informações do navegador a partir do User-Agent.
    generate_client_version: Gera um client-version no formato UUID.
    generate_fingerprint: Gera um fingerprint completo com headers.
    get_fingerprint: Retorna um novo fingerprint gerado.
    set_fingerprint: Define um novo fingerprint.

Attributes:
    CLIENT_ID (str): ID do cliente para a API da Twitch.
    ua (UserAgent): Instância do UserAgent para gerar User-Agents aleatórios.
"""

import random
import string
import uuid
import time
from typing import Dict, Tuple
from fake_useragent import UserAgent
from colorama import Fore, Style, init

# Inicializar o Colorama
init()

# Configurações globais
CLIENT_ID: str = "kimne78kx3ncx6brgo4mv6wki5h1ko"

# Inicializar o UserAgent
ua = UserAgent(browsers=['chrome', 'edge', 'firefox'])

def gerar_device_id() -> str:
    """
    Gera um ID de dispositivo aleatório.

    Returns:
        str: Uma string de 32 caracteres alfanuméricos.
    """
    caracteres = string.ascii_letters + string.digits
    return ''.join(random.choice(caracteres) for _ in range(32))

def get_platform_from_user_agent(user_agent: str) -> str:
    """
    Detecta a plataforma a partir do User-Agent.

    Args:
        user_agent (str): String do User-Agent.

    Returns:
        str: Nome da plataforma detectada entre aspas duplas.
    """
    user_agent = user_agent.lower()
    if 'win' in user_agent:
        return '"Windows"'
    elif 'mac' in user_agent:
        return '"macOS"'
    elif 'linux' in user_agent:
        return '"Linux"'
    elif 'android' in user_agent:
        return '"Android"'
    elif 'iphone' in user_agent or 'ipad' in user_agent:
        return '"iOS"'
    else:
        return '"Unknown"'

def get_browser_info(user_agent: str) -> Tuple[str, str, str]:
    """
    Obtém informações do navegador a partir do User-Agent.

    Args:
        user_agent (str): String do User-Agent.

    Returns:
        Tuple[str, str, str]: Tupla contendo nome do navegador, marca e engine.
    """
    ua_lower = user_agent.lower()
    if 'chrome' in ua_lower:
        version = random.randint(90, 130)
        return (f'"Google Chrome";v="{version}"', f'"Not=A?Brand";v="{random.randint(8, 99)}"', f'"Chromium";v="{version}"')
    elif 'firefox' in ua_lower:
        version = random.randint(90, 120)
        return (f'"Firefox";v="{version}"', '', '')
    elif 'safari' in ua_lower:
        version = f"{random.randint(13, 16)}.{random.randint(0, 9)}"
        return (f'"Safari";v="{version}"', '', '')
    elif 'edge' in ua_lower:
        version = random.randint(90, 130)
        return (f'"Microsoft Edge";v="{version}"', f'"Not=A?Brand";v="{random.randint(8, 99)}"', f'"Chromium";v="{version}"')
    else:
        return ('"Unknown"', '', '')

def generate_client_version() -> str:
    """
    Gera um client-version no formato UUID v4.
    
    Returns:
        str: Client-version no formato UUID v4.
    """
    return str(uuid.uuid4())

def generate_fingerprint() -> Dict[str, str]:
    """
    Gera um fingerprint completo com todos os headers necessários.

    Returns:
        Dict[str, str]: Dicionário contendo todos os headers do fingerprint.
    """
    user_agent = ua.random
    platform = get_platform_from_user_agent(user_agent)
    browser_info = get_browser_info(user_agent)
    is_mobile = '?1' if 'mobile' in user_agent.lower() else '?0'
    
    return {
        'Accept': random.choice([
            "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8",
            "application/json, text/plain, */*",
            "*/*"
        ]),
        'Accept-Encoding': random.choice([
            "gzip, deflate, br",
            "gzip, deflate",
            "br",
            "identity"
        ]),
        'Accept-Language': random.choice([
            "en-US,en;q=0.9",
            "es-ES,es;q=0.9",
            "fr-FR,fr;q=0.9",
            "pt-BR,pt;q=0.9",
            "de-DE,de;q=0.9"
        ]),
        'Referer': random.choice([
            "https://www.twitch.tv/",
            "https://www.twitch.tv/directory",
            "https://www.twitch.tv/directory/all",
            "https://www.twitch.tv/game"
        ]),
        'User-Agent': user_agent,
        'Sec-Ch-Ua': ', '.join(filter(None, browser_info)),
        'Sec-Ch-Ua-Mobile': is_mobile,
        'Sec-Ch-Ua-Platform': platform,
        'Client-Id': CLIENT_ID,
        'Device-Id': gerar_device_id(),
        'Client-Version': generate_client_version()
    }

def get_fingerprint() -> Dict[str, str]:
    """
    Retorna um novo fingerprint gerado.

    Returns:
        Dict[str, str]: Novo fingerprint gerado.
    """
    return generate_fingerprint()

def set_fingerprint(fingerprint: Dict[str, str]):
    """
    Define um novo fingerprint (mantida para compatibilidade).

    Args:
        fingerprint (Dict[str, str]): Novo fingerprint a ser definido.
    """
    pass  # Não armazena mais globalmente

if __name__ == "__main__":
    print(Fore.YELLOW + "\n⏳ Gerando 3 fingerprints diferentes para teste:" + Style.RESET_ALL)
    print("=" * 70)
    
    for i in range(3):
        print(f"\n{Fore.GREEN}✅ Fingerprint {i+1} gerado com sucesso{Style.RESET_ALL}:\n")
        fingerprint = get_fingerprint()
        for key, value in fingerprint.items():
            print(f"{key}: {value}")
        print("=" * 70)
    
    time.sleep(60)