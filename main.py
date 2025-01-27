import sys
import os
import logging
from datetime import datetime, timezone
import time
from collections import deque
import threading
from colorama import Fore, Style, init
from concurrent.futures import ThreadPoolExecutor
from threading import Lock
from modules.utils.utils_failure_manager import get_failure_manager
from modules.utils.utils_bot_monitor import get_bot_monitor, BotStatus
from modules.core.core_session import session_manager
from modules.utils.utils_proxy_manager import ProxyManager
import json
from pathlib import Path
import questionary
from questionary import Style as QuestionaryStyle
from typing import Optional
from modules.core.core_chat_manager import get_chat_manager
from modules.core.core_auth_manager import get_auth_manager

# Inicializa o Colorama
init()

# Configurações de cores
INFO_COLOR = Fore.CYAN
SUCCESS_COLOR = Fore.GREEN
WARNING_COLOR = Fore.YELLOW
ERROR_COLOR = Fore.RED
RESET = Style.RESET_ALL

def setup_global_logger():
    """Configura um logger global único para todo o programa"""
    # Cria o diretório de logs se não existir
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    
    # Remove TODOS os handlers existentes do logger raiz
    root_logger = logging.getLogger()
    root_logger.handlers.clear()  # Limpa todos os handlers
    
    # Cria um nome de arquivo baseado na data/hora atual
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = log_dir / f"chronus_{timestamp}.log"
    
    # Configura o logger raiz
    root_logger.setLevel(logging.INFO)
    
    # Handler para arquivo único - mantém todos os logs
    file_handler = logging.FileHandler(log_file, encoding='utf-8')
    file_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
    root_logger.addHandler(file_handler)
    
    # Handler para console - filtra mensagens com terminal=False
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(logging.Formatter('%(message)s'))
    
    class TerminalFilter(logging.Filter):
        def filter(self, record):
            return not (hasattr(record, 'terminal') and record.terminal is False)
            
    console_handler.addFilter(TerminalFilter())
    root_logger.addHandler(console_handler)
    
    return root_logger

# Configura o logger global ANTES de importar outros módulos
logger = setup_global_logger()

# Lock global para contagem de anúncios
anuncios_lock = Lock()
total_anuncios_global = 0
limite_anuncios_global = 0
should_stop = threading.Event()

# Variáveis globais para estatísticas
stats_lock = threading.Lock()
global_stats = {
    'channels': 0,
    'completed': '0/0',
    'threads': 0,
    'proxies': 0,
    'ads_per_hour': 0.0
}
bot_stats = []

# Adicione estas variáveis globais no início do arquivo
preroll_anuncios = 0
midroll_anuncios = 0
anuncios_lock = Lock()

# Adicione estas variáveis globais para cada bot
bot_anuncios = {}  # Dicionário para armazenar contadores de cada bot

# Adicione estas variáveis globais no início do arquivo, após as importações existentes
current_channel_index = 0
channels_list = []

# Defina o estilo personalizado
custom_style = QuestionaryStyle([
    ('qmark', 'fg:#000000'),  # ? em preto (praticamente invisível)
    ('question', 'fg:#ff0000 bold'),  # Pergunta em vermelho
    ('answer', 'fg:#ff5733 bold'),
    ('pointer', 'fg:#ff0000 bold'),
    ('highlighted', 'fg:#ff0000 bold'),
    ('selected', 'fg:#00ff00'),
    ('text', 'fg:#ffffff'),
    ('instruction', 'fg:#ffffff'),
    ('disabled', 'fg:#858585 italic')
])

def update_bot_ip(bot_id: int, ip: str):
    """Atualiza o IP do bot nas estatísticas."""
    with stats_lock:
        for bot in bot_stats:
            if bot['id'] == bot_id:
                bot['proxy_ip'] = ip
                logger.info("", extra={
                    'bot_id': bot_id,
                    'message': f"IP atualizado para: {ip}"
                })
                return

def print_header():
    """Imprime o cabeçalho do programa."""
    pass  # Removido pois agora usamos o menu

def log_session_details(bot_id, session):
    """Loga detalhes completos da sessão."""
    logger.info("", extra={
        'session_details': {
            'fingerprint': session.fingerprint,
            'proxy': session.proxy,
            'user_agent': session.headers.get('User-Agent'),
            'client_id': session.headers.get('Client-ID')
        }
    })

def log_request_details(method, url, headers_sent, response):
    """Loga detalhes completos da requisição e resposta."""
    logger.info("", extra={
        'request_details': {
            'method': method,
            'url': url,
            'headers_sent': headers_sent,
            'headers_received': dict(response.headers),
            'status_code': response.status_code,
            'reason': response.reason,
            'response': response.text
        }
    })

def get_next_channel() -> Optional[str]:
    """
    Obtém o próximo canal da lista de canais.
    
    Returns:
        Optional[str]: Próximo canal ou None se não houver mais canais
    """
    global current_channel_index, channels_list
    
    # Carrega a lista de canais se estiver vazia
    if not channels_list:
        config = load_config()
        channels_list = [canal for canal in config['channels'] if canal and isinstance(canal, str)]
    
    # Verifica se há mais canais disponíveis
    if current_channel_index >= len(channels_list):
        # Não reinicia mais o índice, retorna None para indicar que acabou
        return None
        
    canal = channels_list[current_channel_index]
    current_channel_index += 1
    return canal

def check_anuncios_limit(num_anuncios: int, is_preroll: bool, bot_id: int) -> bool:
    """
    Callback para verificar limite de anúncios.
    """
    global total_anuncios_global
    
    with anuncios_lock:
        # Atualiza contadores do bot
        if is_preroll:
            bot_anuncios[bot_id]['preroll'] += num_anuncios
        else:
            bot_anuncios[bot_id]['midroll'] += num_anuncios
            
        # Atualiza contadores globais
        total_anuncios_global += num_anuncios
        
        # Atualiza estatísticas do bot no menu
        with stats_lock:
            for bot in bot_stats:
                if bot['id'] == bot_id:
                    bot['ads'] = f"{bot_anuncios[bot_id]['preroll']}/{bot_anuncios[bot_id]['midroll']}"
                    break
                    
        # Verifica se atingiu o limite global
        config = load_config()
        if total_anuncios_global >= config['ads_limit']:
            logger.info(f"Limite global de {config['ads_limit']} anúncios atingido!")
            
            # Sinaliza para todos os bots pararem
            should_stop.set()
            
            # Atualiza status de todos os bots para FINALIZADO
            with stats_lock:
                for bot in bot_stats:
                    bot['status'] = 'FINALIZADO'
                    session_manager.close_session(bot['id'])
            
            # Libera todos os recursos
            session_manager.close_all()
            ProxyManager().close_all()
            
            # Força saída do programa
            logger.info("Encerrando programa...")
            os._exit(0)
            
            return True
            
    return False

def check_and_change_channel():
    """Função auxiliar para gerenciar a mudança sincronizada de canal."""
    # Tenta obter próximo canal
    next_channel = get_next_channel()
    if next_channel:
        logger.info(f"Mudando todos os bots para o canal: {next_channel}")
        
        # Reseta contadores globais
        global total_anuncios_global
        total_anuncios_global = 0
        
        # Limpa contadores por bot
        bot_anuncios.clear()
        
        # Lista para armazenar resultados das operações de token
        token_results = []
        
        # Primeiro, fecha todas as sessões antigas e reseta status
        with stats_lock:
            for bot in bot_stats:
                session_manager.close_session(bot['id'])
                bot['status'] = 'RECONECT'
                bot['channel'] = next_channel
                bot['ads'] = '0/0'
                bot['user_ip'] = 'Waiting IP...'
        
        return 2
    else:
        # Modificação aqui: Encerramento mais controlado e definitivo
        logger.info("Não há mais canais para processar. Iniciando encerramento controlado...")
        
        # Define o evento de parada antes de qualquer outra operação
        should_stop.set()
        
        # Atualiza status dos bots para finalizado e fecha todas as sessões
        with stats_lock:
            for bot in bot_stats:
                bot['status'] = 'FINALIZADO'
                session_manager.close_session(bot['id'])
                
        # Libera todos os proxies
        ProxyManager().close_all()
        
        # Força uma última atualização do menu
        time.sleep(1)
        
        # Encerra todas as threads em execução
        for thread in threading.enumerate():
            if thread != threading.current_thread():
                try:
                    thread.join(timeout=1)
                except:
                    pass
        
        # Encerra o programa completamente
        logger.info("Programa finalizado com sucesso.")
        os._exit(0)  # Força o encerramento imediato do programa

def setup_new_session(bot_id: int, channel: str) -> bool:
    """Configura nova sessão e token para um bot."""
    try:
        # Obtém nova sessão com novo fingerprint e proxy
        session = session_manager.get_session(bot_id)
        fingerprint = session_manager.get_fingerprint(bot_id)
        
        # Obtém novo token para o novo canal
        token_data = obter_playback_access_token(channel, fingerprint, bot_id)
        if token_data:
            # Atualiza o status para ONLINE somente após obter token com sucesso
            with stats_lock:
                for bot in bot_stats:
                    if bot['id'] == bot_id:
                        bot['status'] = 'ONLINE'
                        break
            return True
        else:
            logger.error(f"BOT {bot_id}: Falha ao obter token para canal {channel}")
            return False
    except Exception as e:
        logger.error(f"BOT {bot_id}: Erro ao configurar nova sessão: {str(e)}")
        return False

def update_menu():
    """Thread para atualizar o menu periodicamente"""
    while not should_stop.is_set():
        try:
            # Verifica se o canal está online
            config = load_config()
            canal_nome = config['channels'][-1]
            
            online, mensagem = verificar_canal_online(canal_nome)
            if not online:
                print(f"\n{Fore.RED}{mensagem}. Encerrando bots...{Style.RESET_ALL}")
                should_stop.set()
                break
                
            time.sleep(30)  # Verifica a cada 30 segundos
            
        except Exception as e:
            logger.error(f"Erro ao atualizar status: {str(e)}")
            time.sleep(5)

def bot_worker(canal_nome: str, bot_id: int):
    """Função que executa o trabalho de cada bot em sua própria thread."""
    monitor = get_bot_monitor()
    failure_mgr = get_failure_manager()
    chat_mgr = get_chat_manager()
    auth_mgr = get_auth_manager()
    
    # Carrega configurações
    config = load_config()
    ads_limit = config['ads_limit']
    
    # Inicializa contadores para este bot
    bot_anuncios[bot_id] = {'preroll': 0, 'midroll': 0}
    
    try:
        # Se for o primeiro bot, limpa a tela e mostra a logo
        if bot_id == 1:
            mostrar_cabecalho()
            # Adiciona timestamp na mensagem de conexão com cores
            timestamp = datetime.now().strftime("%H:%M:%S")
            print(f"{Fore.WHITE}[BOT][{timestamp}] {Fore.GREEN}Conectado com sucesso na transmissão de {Fore.WHITE}{canal_nome}{Fore.GREEN} com {Fore.WHITE}{config['bots']}{Fore.GREEN} Threads.{Style.RESET_ALL}")
            print() # Linha em branco para separar
        
        # Primeira configuração da sessão
        if not reiniciar_sessao("Iniciando bot", bot_id):
            time.sleep(5)
            return
            
        # Obtém token
        fingerprint = session_manager.get_fingerprint(bot_id)
        token_data = None
        max_token_tentativas = 3
        token_tentativas = 0
        
        while token_data is None and token_tentativas < max_token_tentativas:
            token_data = obter_playback_access_token(canal_nome, fingerprint, bot_id)
            if not token_data:
                token_tentativas += 1
                time.sleep(2)
        
        if not token_data:
            logger.error(f"BOT {bot_id}: Falha ao obter token após {max_token_tentativas} tentativas")
            return
            
        # Tenta baixar o primeiro segmento para confirmar que está tudo funcionando
        resultado = atualizar_playlist(canal_nome, token_data, bot_id, 
                                     limite_anuncios=ads_limit,
                                     check_limit_callback=check_anuncios_limit,
                                     primeiro_segmento=True)
        
        if resultado is True:
            # Obtém o proxy e extrai apenas o IP
            proxy_full = session_manager.get_proxy_info(bot_id)
            # Extrai o IP do formato "http://user:pass@IP:PORT" ou "IP:PORT"
            proxy_ip = proxy_full.split('@')[-1].split(':')[0] if '@' in proxy_full else proxy_full.split(':')[0]
            # Adiciona timestamp
            timestamp = datetime.now().strftime("%H:%M:%S")
            print(f"{Fore.WHITE}[BOT {bot_id}][{timestamp}] {Fore.MAGENTA}Assistindo a transmissão de {Fore.WHITE}{canal_nome}{Fore.MAGENTA} com {Fore.WHITE}{config['bots']}{Fore.MAGENTA} Threads - {proxy_ip}{Style.RESET_ALL}")
            
            # Agora inicia o loop principal
            while not should_stop.is_set():
                try:
                    resultado = atualizar_playlist(canal_nome, token_data, bot_id,
                                              limite_anuncios=ads_limit,
                                              check_limit_callback=check_anuncios_limit)
                    
                    if resultado == 2:  # Mudança de canal
                        session_manager.close_session(bot_id)
                        break
                    elif resultado is True:  # Limite de anúncios atingido
                        logger.info(f"BOT {bot_id}: Limite de {ads_limit} anúncios atingido, encerrando...")
                        should_stop.set()  # Sinaliza para todos os bots pararem
                        break
                    elif resultado is False:
                        reiniciar_sessao("Fila vazia persistente após tentativas de recuperação", bot_id)
                        break
                    
                    time.sleep(1)
                    
                except Exception as e:
                    logger.error(f"BOT {bot_id}: Erro na atualização: {str(e)}")
                    time.sleep(5)
                
    except Exception as e:
        logger.error(f"BOT {bot_id}: Erro: {str(e)}")
        
    finally:
        # Desconecta do chat e libera a conta
        chat_mgr.disconnect_chat(bot_id)
        auth_mgr.release_account(bot_id)
        session_manager.close_session(bot_id)

def obter_entrada_canal() -> str:
    """Obtém e valida o nome do canal."""
    config = load_config()
    # Filtra valores nulos ou vazios da lista de canais
    canais_salvos = [canal for canal in config['channels'] if canal and isinstance(canal, str)]
    
    if canais_salvos:
        canal = questionary.select(
            "\nSelecione um canal ou digite um novo:",
            choices=[*canais_salvos, "Novo canal", "Voltar"],
            style=custom_style
        ).ask()
        
        if canal == "Voltar":
            return None
        
        if canal == "Novo canal":
            mostrar_cabecalho()  # Limpa a tela e mostra o cabeçalho novamente
            canal = questionary.text(
                "\nDigite o nome do novo canal:",
                style=custom_style
            ).ask()
    else:
        canal = questionary.text(
            "\nDigite o nome do canal:",
            style=custom_style
        ).ask()
    
    return canal

def obter_numero_bots() -> int:
    """Obtém e valida o número de bots."""
    config = load_config()
    valor_padrao = config['bots']
    
    while True:
        try:
            entrada = questionary.text(
                f"\nDigite o número de bots [{valor_padrao}]:",
                style=custom_style
            ).ask()
            
            if not entrada:
                return valor_padrao
                
            num_bots = int(entrada)
            if 1 <= num_bots <= 50:
                return num_bots
            
            print(f"{Fore.RED}Erro: O número deve estar entre 1 e 50.{Style.RESET_ALL}")
            
        except ValueError:
            print(f"{Fore.RED}Erro: Digite um número válido.{Style.RESET_ALL}")

def obter_limite_anuncios() -> int:
    """Obtém e valida o limite de anúncios."""
    config = load_config()
    valor_padrao = config['ads_limit']
    
    while True:
        try:
            entrada = questionary.text(
                f"\nDigite o limite total de anúncios [{valor_padrao}]:",
                style=custom_style
            ).ask()
            
            if not entrada:
                return valor_padrao
                
            limite = int(entrada)
            if limite > 0:
                return limite
            
            print(f"{Fore.RED}Erro: O limite deve ser maior que zero.{Style.RESET_ALL}")
            
        except ValueError:
            print(f"{Fore.RED}Erro: Digite um número válido.{Style.RESET_ALL}")

def exibir_configuracoes(canal: str, num_bots: int, limite_anuncios: int):
    """Exibe um resumo das configurações."""
    print(f"\n{Fore.CYAN}RESUMO DAS CONFIGURAÇÕES{Style.RESET_ALL}")
    
    print(f"\n{Fore.WHITE}Canal: {Fore.RED}{canal}")
    print(f"{Fore.WHITE}Número de Bots: {Fore.RED}{num_bots}")
    print(f"{Fore.WHITE}Limite de Anúncios: {Fore.RED}{limite_anuncios}{Style.RESET_ALL}")
    
    print(f"\n{Fore.YELLOW}Pressione ENTER para iniciar ou CTRL+C para cancelar...{Style.RESET_ALL}")
    input()

def load_config() -> dict:
    """
    Carrega as configurações do arquivo config.json.
    Se o arquivo não existir, cria com valores padrão.
    
    Returns:
        dict: Configurações carregadas
    """
    config_path = Path("configs/config.json")
    
    # Cria o diretório configs se não existir
    config_path.parent.mkdir(exist_ok=True)
    
    # Configurações padrão
    default_config = {
        "channels": [],
        "bots": 5,
        "ads_limit": 1000
    }
    
    # Se o arquivo não existe, cria com configurações padrão
    if not config_path.exists():
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(default_config, f, indent=4)
        return default_config
        
    # Carrega configurações existentes
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Erro ao carregar configurações: {e}")
        return default_config

def save_config(config: dict):
    """
    Salva as configurações no arquivo config.json.
    
    Args:
        config (dict): Configurações a serem salvas
    """
    config_path = Path("configs/config.json")
    try:
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=4)
    except Exception as e:
        logger.error(f"Erro ao salvar configurações: {e}")

def add_channel_to_config(channel: str):
    """
    Adiciona um canal à lista de canais nas configurações.
    
    Args:
        channel (str): Nome do canal a ser adicionado
    """
    config = load_config()
    if channel not in config['channels']:
        config['channels'].append(channel)
        save_config(config)

def exibir_menu_principal():
    """Exibe o menu principal e retorna a opção selecionada."""
    # Limpa a tela
    os.system('cls' if os.name == 'nt' else 'clear')
    
    # Calcula o padding para centralização
    terminal_width = os.get_terminal_size().columns
    padding = " " * ((terminal_width - 80) // 2)
    
    # Cabeçalho com título em negrito e branco
    print(f"\n")
    print(f"{padding}                                     {Style.BRIGHT}{Fore.WHITE}CHRONUS{Style.RESET_ALL}")
    print(f"{padding}                  {Fore.RED}────────────────────────────────────────────{Style.RESET_ALL}")
    print(f"{padding}                              Made by: {Fore.RED}Velbots{Style.RESET_ALL}")
    print(f"{padding}                  {Fore.RED}─────────────────────────────────────────────{Style.RESET_ALL}")
    print(f"\n")
    
    opcoes = {
        'Iniciar': 1,
        'Alterar configurações': 2
    }
    
    escolha = questionary.select(
        '\nEscolha uma opção:',
        choices=list(opcoes.keys()),
        style=custom_style
    ).ask()
    
    return opcoes[escolha]

def mostrar_cabecalho():
    """Mostra o cabeçalho padrão do programa."""
    # Limpa a tela
    os.system('cls' if os.name == 'nt' else 'clear')
    
    # Mostra o cabeçalho
    terminal_width = os.get_terminal_size().columns
    padding = " " * ((terminal_width - 80) // 2)
    print(f"\n")
    print(f"{padding}                                     {Style.BRIGHT}{Fore.WHITE}CHRONUS{Style.RESET_ALL}")
    print(f"{padding}                  {Fore.RED}────────────────────────────────────────────{Style.RESET_ALL}")
    print(f"{padding}                              Made by: {Fore.RED}Velbots{Style.RESET_ALL}")
    print(f"{padding}                  {Fore.RED}─────────────────────────────────────────────{Style.RESET_ALL}")
    print(f"\n")

def reiniciar_sessao(motivo: str, bot_id: int = None) -> bool:
    """Reinicia a sessão do bot."""
    try:
        # Adiciona extra={'terminal': False} para não mostrar no terminal
        logger.warning(f"BOT {bot_id}: Reiniciando sessão - Motivo: {motivo}", extra={
            'session_restart': {
                'bot_id': bot_id,
                'reason': motivo
            },
            'terminal': False
        })
        
        # Fecha sessão atual
        session_manager.close_session(bot_id)
        
        # Cria nova sessão (que já vai obter novo proxy)
        session = session_manager.get_session(bot_id)
        if not session:
            logger.error(f"BOT {bot_id}: Falha ao criar nova sessão")
            return False
            
        return True
        
    except Exception as e:
        logger.error(f"BOT {bot_id}: Erro ao reiniciar sessão: {str(e)}")
        return False

def monitor_bots_health():
    """Thread para monitorar a saúde dos bots e reiniciar os que estiverem travados."""
    while not should_stop.is_set():
        try:
            with stats_lock:
                current_time = time.time()
                for bot in bot_stats:
                    if 'last_status_change' not in bot:
                        bot['last_status_change'] = current_time
                        continue

                    status_duration = current_time - bot['last_status_change']
                    
                    # Se estiver em RECONECT por mais de 2 minutos
                    if bot['status'] == 'RECONECT' and status_duration > 120:
                        logger.warning(f"BOT {bot['id']}: Preso em RECONECT por {int(status_duration)}s, forçando reinício")
                        force_bot_restart(bot['id'])
                    
                    # Se estiver em ERRO ou outro status problemático por mais de 2 minutos
                    elif bot['status'] in ['ERRO', 'DESCONECTADO'] and status_duration > 120:
                        logger.warning(f"BOT {bot['id']}: Em {bot['status']} por {int(status_duration)}s, verificando estado")
                        check_bot_state(bot['id'])
                    
                    # Se estiver ONLINE, apenas verifica a cada 10 minutos
                    elif bot['status'] == 'ONLINE' and status_duration > 600:
                        logger.info(f"BOT {bot['id']}: Verificação de rotina após {int(status_duration)}s")
                        check_bot_state(bot['id'])
                        
                    # NOVO: Se estiver com "Waiting IP..." por mais de 4 minutos
                    elif bot.get('user_ip') == 'Waiting IP...' and status_duration > 240:
                        logger.warning(f"BOT {bot['id']}: Preso em 'Waiting IP...' por {int(status_duration)}s, forçando reinício")
                        force_bot_restart(bot['id'])

            time.sleep(30)  # Verifica a cada 30 segundos
            
        except Exception as e:
            logger.error(f"Erro no monitor de saúde: {str(e)}")
            time.sleep(5)

def force_bot_restart(bot_id: int):
    """Força o reinício de um bot travado."""
    try:
        # Fecha a sessão atual
        session_manager.close_session(bot_id)
        
        # Atualiza status do bot
        with stats_lock:
            for bot in bot_stats:
                if bot['id'] == bot_id:
                    bot['status'] = 'RECONECT'
                    bot['last_status_change'] = time.time()
                    bot['user_ip'] = 'Waiting IP...'
                    break
        
        # Força uma nova sessão com novo proxy
        if setup_new_session(bot_id, bot['channel']):
            logger.info(f"BOT {bot_id}: Reiniciado com sucesso")
        else:
            logger.error(f"BOT {bot_id}: Falha ao reiniciar")
            
    except Exception as e:
        logger.error(f"Erro ao forçar reinício do bot {bot_id}: {str(e)}")

def check_bot_state(bot_id: int):
    """Verifica o estado atual do bot e toma ação se necessário."""
    try:
        with stats_lock:
            bot_info = next((bot for bot in bot_stats if bot['id'] == bot_id), None)
            if not bot_info:
                return

            # 1. Verifica se a sessão existe
            session = session_manager.get_session(bot_id)
            if not session:
                logger.warning(f"BOT {bot_id}: Sessão inexistente, forçando reinício")
                force_bot_restart(bot_id)
                return

            # 2. Verifica se o token ainda é válido
            if not verify_token_valid(bot_id):
                logger.warning(f"BOT {bot_id}: Token expirado, forçando reinício")
                force_bot_restart(bot_id)
                return

            # 3. Testa conectividade do proxy
            try:
                response = session.get('https://www.google.com', timeout=5)
                if response.status_code != 200:
                    raise Exception("Falha na conexão")
            except:
                logger.warning(f"BOT {bot_id}: Falha na verificação de conexão, forçando reinício")
                force_bot_restart(bot_id)
                return

            # 4. Verifica se consegue obter a playlist
            try:
                playlist = obter_playlist_m3u8(bot_info['channel'], session, bot_id)
                if not playlist:
                    logger.warning(f"BOT {bot_id}: Falha ao obter playlist, forçando reinício")
                    force_bot_restart(bot_id)
                    return
            except:
                logger.warning(f"BOT {bot_id}: Erro ao obter playlist, forçando reinício")
                force_bot_restart(bot_id)
                return

            # 5. Verifica se consegue baixar um segmento de teste
            try:
                segments = playlist.segments[:1]  # Pega primeiro segmento para teste
                if segments and not test_segment_download(segments[0], session, bot_id):
                    logger.warning(f"BOT {bot_id}: Falha ao baixar segmento, forçando reinício")
                    force_bot_restart(bot_id)
                    return
            except:
                logger.warning(f"BOT {bot_id}: Erro ao testar download de segmento, forçando reinício")
                force_bot_restart(bot_id)
                return

            # Se chegou aqui, passou em todas as verificações
            bot_info['last_status_change'] = time.time()
            if bot_info['status'] != 'ONLINE':
                bot_info['status'] = 'ONLINE'
                logger.info(f"BOT {bot_id}: Restaurado para ONLINE após todas as verificações")

    except Exception as e:
        logger.error(f"Erro ao verificar estado do bot {bot_id}: {str(e)}")
        force_bot_restart(bot_id)

def test_segment_download(segment, session, bot_id: int) -> bool:
    """Testa o download de um segmento."""
    try:
        response = session.get(segment.uri, timeout=5)
        return response.status_code == 200 and len(response.content) > 0
    except:
        return False

def verify_token_valid(bot_id: int) -> bool:
    """Verifica se o token do bot ainda é válido."""
    try:
        session = session_manager.get_session(bot_id)
        if not session or not session.token_data:
            return False
            
        # Verifica se o token expirou (normalmente 1 hora)
        token_age = time.time() - session.token_timestamp
        return token_age < 3300  # 55 minutos (dá margem de segurança antes da 1 hora)
        
    except Exception:
        return False

def main():
    global limite_anuncios_global
    
    try:
        # Carrega configurações
        config = load_config()
        
        while True:
            opcao = exibir_menu_principal()
            
            if opcao == 1:  # Iniciar
                # Verifica se há canais salvos
                if not config['channels']:
                    print(f"\n{Fore.RED}Erro: Nenhum canal configurado. Configure um canal primeiro.{Style.RESET_ALL}")
                    input(f"\n{Fore.YELLOW}Pressione ENTER para continuar...{Style.RESET_ALL}")
                    continue
                
                # Usa o último canal adicionado
                canal_nome = config['channels'][-1]
                num_bots = config['bots']  # Usa valor salvo
                limite_anuncios_global = config['ads_limit']  # Usa valor salvo
                
                # Verifica se o canal está online
                online, mensagem = verificar_canal_online(canal_nome)
                if not online:
                    print(f"\n{Fore.RED}Erro: {mensagem}{Style.RESET_ALL}")
                    input(f"\n{Fore.YELLOW}Pressione ENTER para continuar...{Style.RESET_ALL}")
                    continue
                
                # Inicia thread de monitoramento de saúde
                health_monitor = threading.Thread(target=monitor_bots_health)
                health_monitor.daemon = True
                health_monitor.start()

                # Iniciar múltiplos bots em threads
                with ThreadPoolExecutor(max_workers=num_bots) as executor:
                    futures = [executor.submit(bot_worker, canal_nome, bot_id) 
                              for bot_id in range(1, num_bots + 1)]
                    
                    for future in futures:
                        try:
                            future.result()
                        except Exception as e:
                            logger.error(f"Erro em thread de bot: {str(e)}")
                break
                
            else:  # Alterar configurações
                # Limpa a tela
                os.system('cls' if os.name == 'nt' else 'clear')
                
                # Calcula o padding para centralização
                terminal_width = os.get_terminal_size().columns
                padding = " " * ((terminal_width - 80) // 2)
                
                # Logo
                print(f"\n")
                print(f"{padding}                                     {Style.BRIGHT}{Fore.WHITE}CHRONUS{Style.RESET_ALL}")
                print(f"{padding}                  {Fore.RED}────────────────────────────────────────────{Style.RESET_ALL}")
                print(f"{padding}                              Made by: {Fore.RED}Velbots{Style.RESET_ALL}")
                print(f"{padding}                  {Fore.RED}─────────────────────────────────────────────{Style.RESET_ALL}")
                print(f"\n") 
                opcoes = [
                    f"Número de Bots: {config['bots']}",
                    f"Limite de Anúncios: {config['ads_limit']}",
                    "Gerenciar Canais",
                    "Voltar"
                ]
                
                escolha = questionary.select(
                    '\nEscolha uma opção:',
                    choices=opcoes,
                    style=custom_style
                ).ask()
                
                if "Número de Bots" in escolha:
                    mostrar_cabecalho()
                    config['bots'] = obter_numero_bots()
                    save_config(config)
                elif "Limite de Anúncios" in escolha:
                    mostrar_cabecalho()
                    config['ads_limit'] = obter_limite_anuncios()
                    save_config(config)
                elif "Gerenciar Canais" in escolha:
                    mostrar_cabecalho()
                    acao = questionary.select(
                        '\nO que deseja fazer?',
                        choices=[
                            'Adicionar canal',
                            'Remover canal',
                            'Voltar'
                        ],
                        style=custom_style
                    ).ask()
                    
                    if acao == 'Adicionar canal':
                        mostrar_cabecalho()  # Limpa a tela antes de mostrar o menu de seleção
                        canal_nome = obter_entrada_canal()
                        if canal_nome:  # Só adiciona se não for None (não escolheu Voltar)
                            add_channel_to_config(canal_nome)
                            mostrar_cabecalho()  # Limpa a tela e mostra o cabeçalho
                            # Recarrega a configuração para ter a lista atualizada
                            config = load_config()
                    elif acao == 'Remover canal':
                        mostrar_cabecalho()  # Limpa a tela antes de mostrar o menu de remoção
                        # Recarrega a configuração para ter a lista mais atual
                        config = load_config()
                        if not config['channels']:
                            print(f"{Fore.RED}Não há canais para remover.{Style.RESET_ALL}")
                            input(f"\n{Fore.YELLOW}Pressione ENTER para continuar...{Style.RESET_ALL}")
                            continue
                            
                        # Garante que todos os canais válidos sejam listados
                        canais_validos = []
                        for canal in config['channels']:
                            if canal and isinstance(canal, str):
                                canais_validos.append(canal)
                        
                        canal_remover = questionary.select(
                            '\nSelecione o canal para remover:',
                            choices=[*canais_validos, 'Voltar'],
                            style=custom_style
                        ).ask()
                        
                        if canal_remover != 'Voltar':
                            config['channels'].remove(canal_remover)
                            save_config(config)
                            print(f"{Fore.GREEN}Canal {canal_remover} removido com sucesso!{Style.RESET_ALL}")
                elif "Voltar" in escolha:
                    continue
                
                print(f"\n{Fore.WHITE}Configurações salvas! Voltando ao menu principal...{Style.RESET_ALL}")
                time.sleep(3)

    except KeyboardInterrupt:
        logger.info("Programa encerrado pelo usuário")
        should_stop.set()
    finally:
        session_manager.close_all()

if __name__ == "__main__":
    try:
        from modules.core.core_fingerprint import get_fingerprint
        from modules.core.core_get_playlist import obter_playlist_m3u8
        from modules.core.core_token import obter_playback_access_token
        from modules.core.core_session import session_manager
        from modules.utils.utils_update_playlist import atualizar_playlist
        from modules.utils.utils_segment_download import iniciar_downloader
        from modules.utils.utils_stream_checker import verificar_canal_online
        from modules.utils.utils_ads_detector import create_ad_detector
    except ImportError as e:
        print(f"{ERROR_COLOR}Erro ao importar módulos: {e}{RESET}")
        sys.exit(1)

    main()