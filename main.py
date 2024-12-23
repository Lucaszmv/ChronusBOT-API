import sys
import os
import logging
from datetime import datetime, timezone
import time
from collections import deque
import threading
from colorama import Fore, Style, init
from modules.utils.utils_logger import get_logger
from concurrent.futures import ThreadPoolExecutor
from threading import Lock
from modules.utils.utils_failure_manager import get_failure_manager
from modules.utils.utils_bot_monitor import get_bot_monitor, BotStatus
from modules.core.core_session import session_manager
from modules.utils.utils_proxy_manager import ProxyManager
from modules.utils.utils_terminal_menu import create_terminal_menu
import json
from pathlib import Path
import questionary
from questionary import Style as QuestionaryStyle
from typing import Optional

# Inicializa o Colorama
init()

# Configurações de cores
INFO_COLOR = Fore.CYAN
SUCCESS_COLOR = Fore.GREEN
WARNING_COLOR = Fore.YELLOW
ERROR_COLOR = Fore.RED
RESET = Style.RESET_ALL

# Criar logger para o módulo main
logger = get_logger(__name__)

# Lock global para contagem de anúncios
anuncios_lock = Lock()
total_anuncios_global = 0
limite_anuncios_global = 0
should_stop = threading.Event()

# Variáveis globais para estatísticas
menu = create_terminal_menu()
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

def check_anuncios_limit(ads_viewed, is_preroll=False, bot_id=None):
    """Verifica se o limite global de anúncios foi atingido e atualiza contadores por bot."""
    global total_anuncios_global, limite_anuncios_global
    
    with anuncios_lock:
        # Inicializa contadores para o bot se não existirem
        if bot_id not in bot_anuncios:
            bot_anuncios[bot_id] = {'preroll': 0, 'midroll': 0}
        
        # Calcula o total após adicionar os novos anúncios
        novo_total = total_anuncios_global + ads_viewed
        
        # Se o novo total ultrapassaria o limite, não incrementa e força mudança de canal
        if novo_total > limite_anuncios_global:
            logger.info(f"Limite de {limite_anuncios_global} anúncios atingido. Iniciando mudança sincronizada de canal.")
            return check_and_change_channel()
            
        # Atualiza contadores do bot específico
        if is_preroll:
            bot_anuncios[bot_id]['preroll'] += ads_viewed
        else:
            bot_anuncios[bot_id]['midroll'] += ads_viewed
            
        # Atualiza total global
        total_anuncios_global = novo_total
        
        # Atualiza o status do bot com seus próprios valores
        for bot in bot_stats:
            if bot['id'] == bot_id:
                bot['ads'] = f"{bot_anuncios[bot_id]['preroll']}/{bot_anuncios[bot_id]['midroll']}"
                break
        
        # Se atingiu exatamente o limite, inicia mudança de canal
        if total_anuncios_global == limite_anuncios_global:
            logger.info(f"Limite exato de {limite_anuncios_global} anúncios atingido. Iniciando mudança sincronizada de canal.")
            return check_and_change_channel()
            
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
            logger.info(f"BOT {bot_id}: Novo token obtido para canal {channel}")
            
            # Atualiza o status e IP somente após obter o token com sucesso
            with stats_lock:
                for bot in bot_stats:
                    if bot['id'] == bot_id:
                        bot['status'] = 'ONLINE'
                        # O IP será atualizado automaticamente pela função update_menu
                        # quando a conexão estiver estabelecida
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
    monitor = get_bot_monitor()
    last_update = time.time()
    last_stats_update = time.time()
    
    while not should_stop.is_set():
        try:
            current_time = time.time()
            
            # Atualiza o menu a cada 1 segundo
            if current_time - last_update >= 1:
                with stats_lock:
                    # Atualiza IPs dos bots apenas se não estiverem em RECONECT ou FINALIZADO
                    for bot in bot_stats:
                        if bot['status'] not in ['RECONECT', 'FINALIZADO']:
                            bot_status = monitor.get_bot_status(bot['id'])
                            if bot_status and bot_status.get('user_ip'):
                                bot['user_ip'] = bot_status['user_ip']
                    
                    # Renderiza o menu
                    menu.render(global_stats, bot_stats)
                    last_update = current_time
            
            # Atualiza estatísticas globais a cada 5 segundos
            if current_time - last_stats_update >= 5:
                with stats_lock:
                    # Calcula o total de pre/mid rolls de todos os bots
                    total_preroll = sum(bot_anuncios[bot_id]['preroll'] for bot_id in bot_anuncios)
                    total_midroll = sum(bot_anuncios[bot_id]['midroll'] for bot_id in bot_anuncios)
                    
                    # Atualiza estatísticas globais
                    config = load_config()
                    total_channels = len([canal for canal in config['channels'] if canal and isinstance(canal, str)])
                    
                    global_stats.update({
                        'channels': total_channels,
                        'completed': f"{total_anuncios_global}/{limite_anuncios_global}",
                        'threads': len(bot_stats),
                        'proxies': len(ProxyManager().proxies),
                        'ads_per_hour': f"{total_preroll}/{total_midroll}"
                    })
                    last_stats_update = current_time
            
            # Pequena pausa para reduzir uso de CPU
            time.sleep(0.1)
            
        except Exception as e:
            logger.error(f"Erro ao atualizar menu: {str(e)}")
            time.sleep(1)

def bot_worker(canal_nome: str, bot_id: int):
    """Função que executa o trabalho de cada bot em sua própria thread."""
    monitor = get_bot_monitor()
    failure_mgr = get_failure_manager()
    erros_consecutivos = 0
    last_status_update = time.time()
    
    # Inicializa contadores para este bot
    bot_anuncios[bot_id] = {'preroll': 0, 'midroll': 0}
    
    # Adiciona estatísticas iniciais do bot
    with stats_lock:
        bot_stats.append({
            'id': bot_id,
            'status': 'ONLINE',
            'channel': canal_nome,
            'ads': '0/0',
            'uptime': '0h 00m',
            'start_time': datetime.now(),
            'user_ip': 'Waiting IP...'
        })
    
    def update_bot_status(status: str, ads: str = None):
        """Atualiza o status do bot no menu"""
        nonlocal last_status_update
        current_time = time.time()
        
        # Limita atualizações de status para no máximo uma vez por segundo
        if current_time - last_status_update >= 1:
            with stats_lock:
                for bot in bot_stats:
                    if bot['id'] == bot_id:
                        bot['status'] = status
                        if ads:
                            bot['ads'] = ads
                        break
            last_status_update = current_time

    def check_and_update_ip():
        """Verifica e atualiza o IP periodicamente"""
        with stats_lock:
            bot_status = monitor.get_bot_status(bot_id)
            if bot_status.get('user_ip'):
                for bot in bot_stats:
                    if bot['id'] == bot_id:
                        bot['user_ip'] = bot_status['user_ip']
                        break

    def add_bot_event(message: str, event_type: str = 'info'):
        """Adiciona um evento do bot ao menu"""
        menu.add_event(bot_id, message, event_type)
    
    def reiniciar_sessao(motivo: str):
        """Função interna para reiniciar a sessão completamente"""
        logger.warning(f"BOT {bot_id}: Reiniciando sessão - Motivo: {motivo}")
        monitor.update_status(bot_id, "Reiniciando sessão", motivo)
        
        # Fecha sessão atual
        session_manager.close_session(bot_id)
        
        # Gera novo fingerprint
        fingerprint = get_fingerprint()
        
        # Cria nova sessão (que já vai obter novo proxy)
        session = session_manager.get_session(bot_id)
        if not session:
            logger.error(f"BOT {bot_id}: Falha ao criar nova sessão")
            return False
            
        # Reseta contadores de erro
        failure_mgr.reset_stats(bot_id)
        return True

    while not should_stop.is_set():
        try:
            # Obtém o canal atual do bot
            current_channel = None
            with stats_lock:
                for bot in bot_stats:
                    if bot['id'] == bot_id:
                        current_channel = bot['channel']
                        break
            
            if not current_channel:
                time.sleep(5)
                continue

            update_bot_status('ONLINE')
            
            # Primeira configuração da sessão
            if not reiniciar_sessao("Iniciando bot"):
                time.sleep(5)
                continue
                
            # Obtém token
            fingerprint = session_manager.get_fingerprint(bot_id)
            token_data = None
            max_token_tentativas = 3
            token_tentativas = 0
            
            while token_data is None and token_tentativas < max_token_tentativas:
                token_data = obter_playback_access_token(current_channel, fingerprint, bot_id)
                if not token_data:
                    token_tentativas += 1
                    time.sleep(2)
            
            if not token_data:
                logger.error(f"BOT {bot_id}: Falha ao obter token após {max_token_tentativas} tentativas")
                continue
            
            # Loop principal de atualização
            while not should_stop.is_set():
                try:
                    monitor.update_status(bot_id, BotStatus.ASSISTINDO, f"Canal: {current_channel}")
                    
                    resultado = atualizar_playlist(current_channel, token_data, bot_id,
                                                 limite_anuncios=None,
                                                 check_limit_callback=check_anuncios_limit)
                    
                    if resultado == 2:  # Mudança de canal
                        update_bot_status('RECONECT')
                        add_bot_event("Mudando de canal", 'warning')
                        session_manager.close_session(bot_id)  # Força fechamento da sessão atual
                        break  # Sai do loop interno para reiniciar com novo canal
                    elif resultado is True:  # Finalização
                        should_stop.set()
                        break
                    elif resultado is False:
                        update_bot_status('RECONECT')
                        add_bot_event("Reiniciando sessão", 'warning')
                        reiniciar_sessao("Fila vazia persistente após tentativas de recuperação")
                        break
                    
                    time.sleep(1)
                    
                except Exception as e:
                    update_bot_status('ERRO')
                    add_bot_event(f"Erro: {str(e)}", 'error')
                    logger.error(f"BOT {bot_id}: Erro na atualização: {str(e)}")
                    erros_consecutivos += 1
                    
        except Exception as e:
            if should_stop.is_set():
                break
            update_bot_status('ERRO')
            add_bot_event(f"Erro: {str(e)}", 'error')
            logger.error(f"BOT {bot_id}: Erro crítico: {str(e)}")
            time.sleep(5)
    
    # Garante que a sessão seja fechada ao sair
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
    print(f"{padding}                  {Fore.RED}───────────────────────────────────────────{Style.RESET_ALL}")
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
                
                # Verifica se o canal est online
                if not verificar_canal_online(canal_nome):
                    print(f"\n{Fore.RED}Erro: Canal offline ou não encontrado.{Style.RESET_ALL}")
                    input(f"\n{Fore.YELLOW}Pressione ENTER para continuar...{Style.RESET_ALL}")
                    continue
                
                # Inicia thread do menu
                menu_thread = threading.Thread(target=update_menu)
                menu_thread.daemon = True
                menu_thread.start()
                
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
                print(f"{padding}                  {Fore.RED}─────────────────────────────────────────────{Style.RESET_ALL}")
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