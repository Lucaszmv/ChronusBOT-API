"""
Módulo para geração de fingerprints de navegador para a API da Twitch.

Este módulo gera headers específicos necessários para simular um navegador real
ao fazer requisições para a API da Twitch. Inclui headers como User-Agent,
Sec-Ch-Ua e outros necessários para autenticação.
"""

import random
import string
import uuid
from typing import Dict, Tuple
from fake_useragent import UserAgent

# ID do cliente oficial da Twitch Web App
CLIENT_ID: str = "kimne78kx3ncx6brgo4mv6wki5h1ko"

# Inicializar o UserAgent apenas com os navegadores mais comuns e suportados
ua = UserAgent(browsers=['chrome', 'edge', 'firefox'], fallback='chrome')

def gerar_device_id() -> str:
    """
    Gera um ID de dispositivo aleatório para identificação do cliente.
    
    A Twitch usa este ID para rastrear dispositivos únicos. O formato é uma
    string aleatória de 32 caracteres (letras e números).

    Returns:
        str: ID de dispositivo aleatório com 32 caracteres
    """
    caracteres = string.ascii_letters + string.digits
    return ''.join(random.choice(caracteres) for _ in range(32))

def get_platform_from_user_agent(user_agent: str) -> str:
    """
    Detecta a plataforma do sistema operacional a partir do User-Agent.
    
    Este valor é usado no header Sec-Ch-Ua-Platform, que indica a plataforma
    do navegador para a API da Twitch.

    Args:
        user_agent (str): String do User-Agent gerado pelo fake-useragent

    Returns:
        str: Nome da plataforma entre aspas duplas (ex: "Windows", "macOS", "Linux")
    """
    ua_lower = user_agent.lower()
    
    if 'windows' in ua_lower:
        return '"Windows"'
    elif 'macintosh' in ua_lower or 'mac os' in ua_lower:
        return '"macOS"'
    elif 'linux' in ua_lower:
        return '"Linux"'
    
    return '"Windows"'

def get_browser_info(user_agent: str) -> Tuple[str, str, str]:
    """
    Obtém informações para o header Sec-Ch-Ua a partir do User-Agent.
    
    O Sec-Ch-Ua é um header específico que indica a marca do navegador em um formato próprio:
    - Firefox: "Firefox";v="120"
    - Chrome: "Google Chrome";v="120", "Not=A?Brand";v="8", "Chromium";v="120"
    - Edge: "Microsoft Edge";v="120", "Not=A?Brand";v="8", "Chromium";v="120"
    
    Args:
        user_agent (str): String do User-Agent gerado pelo fake-useragent

    Returns:
        Tuple[str, str, str]: Tupla contendo os componentes do Sec-Ch-Ua
    """
    ua_lower = user_agent.lower()
    version = random.randint(90, 130)
    
    if 'firefox' in ua_lower:
        return (f'"Firefox";v="{version}"', '', '')
    elif 'edge' in ua_lower:
        return (f'"Microsoft Edge";v="{version}"', f'"Not=A?Brand";v="{random.randint(8, 99)}"', f'"Chromium";v="{version}"')
    else:  # chrome ou fallback
        return (f'"Google Chrome";v="{version}"', f'"Not=A?Brand";v="{random.randint(8, 99)}"', f'"Chromium";v="{version}"')

def generate_client_version() -> str:
    """
    Gera um identificador de versão do cliente no formato UUID.
    
    A Twitch usa este valor para identificar diferentes versões do cliente web.
    É gerado um novo UUID v4 a cada requisição.

    Returns:
        str: UUID v4 como string
    """
    return str(uuid.uuid4())

def generate_fingerprint() -> Dict[str, str]:
    """
    Gera um conjunto completo de headers (fingerprint) para a API da Twitch.
    
    O fingerprint inclui todos os headers necessários para simular um navegador real:
    - Accept: Tipos de conteúdo aceitos
    - Accept-Encoding: Métodos de compressão suportados
    - Accept-Language: Idiomas aceitos
    - Referer: Página de origem
    - User-Agent: Identificação do navegador
    - Sec-Ch-Ua: Marca e versão do navegador
    - Sec-Ch-Ua-Mobile: Indicador de dispositivo móvel
    - Sec-Ch-Ua-Platform: Sistema operacional
    - Client-Id: ID do cliente Twitch
    - Device-Id: ID único do dispositivo
    - Client-Version: Versão do cliente

    Returns:
        Dict[str, str]: Dicionário com todos os headers necessários
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
        ]).strip(),
        'Accept-Encoding': random.choice([
            "gzip, deflate, br",
            "gzip, deflate",
            "br",
            "identity"
        ]).strip(),
        'Accept-Language': random.choice([
            "en-US,en;q=0.9",
            "es-ES,es;q=0.9",
            "fr-FR,fr;q=0.9",
            "pt-BR,pt;q=0.9",
            "de-DE,de;q=0.9"
        ]).strip(),
        'Referer': random.choice([
            "https://www.twitch.tv/",
            "https://www.twitch.tv/directory",
            "https://www.twitch.tv/directory/all",
            "https://www.twitch.tv/game"
        ]).strip(),
        'User-Agent': user_agent.strip(),
        'Sec-Ch-Ua': ', '.join(filter(None, browser_info)).strip(),
        'Sec-Ch-Ua-Mobile': is_mobile,
        'Sec-Ch-Ua-Platform': platform,
        'Client-Id': CLIENT_ID,
        'Device-Id': gerar_device_id(),
        'Client-Version': generate_client_version()
    }

def get_fingerprint() -> Dict[str, str]:
    """
    Função auxiliar que retorna um novo fingerprint gerado.
    
    Esta é a função principal que deve ser chamada por outros módulos
    para obter um novo conjunto de headers.

    Returns:
        Dict[str, str]: Novo fingerprint com todos os headers
    """
    return generate_fingerprint()

def set_fingerprint(fingerprint: Dict[str, str]):
    """
    Função mantida para compatibilidade com versões anteriores.
    Não tem efeito no comportamento atual do módulo.

    Args:
        fingerprint (Dict[str, str]): Fingerprint a ser definido (ignorado)
    """
    pass