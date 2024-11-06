import sys
import os
import logging
from datetime import datetime, timezone
import json
import time

# Adiciona o diretório atual ao sys.path
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)

try:
    # Importações dos módulos core
    from modules.core.core_fingerprint import get_fingerprint
    from modules.core.core_get_playlist import obter_playlist_m3u8
    from modules.core.core_token import obter_playback_access_token
    from modules.core.core_session import session
    
    # Importações dos módulos utils
    from modules.utils.utils_update_playlist import atualizar_playlist
    from modules.utils.utils_ads_detector import create_ad_detector
except ImportError as e:
    logging.error(f"Erro ao importar módulos locais: {e}")
    print(f"Erro ao importar módulos. Verifique o arquivo de log.")
    sys.exit(1)

# Configuração do logging
log_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'logs')
os.makedirs(log_dir, exist_ok=True)
log_file = os.path.join(log_dir, f'main_{datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")}.log')

logging.basicConfig(filename=log_file, level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')

def process_playlist(playlist_content):
    for line in playlist_content.splitlines():
        if line.startswith('#EXT-X-DATERANGE') and 'twitch-stitched-ad' in line:
            ad_info = parse_ad_info(line)
            logging.info(f"Anúncio detectado: {ad_info}")
        
        # ... (resto do processamento da playlist) ...

def parse_ad_info(ad_line):
    ad_info = {}
    for item in ad_line.split(','):
        if '=' in item:
            key, value = item.split('=', 1)
            ad_info[key.strip()] = value.strip('"')
    return ad_info

def download_segment(segment_url):
    # ... (código existente) ...
    
    if 'stitched-ad' in segment_url:
        logging.info(f"Baixando segmento de anúncio: {segment_url}")
    
    # ... (resto do código de download) ...

def main():
    configurar_logging()

    while True:
        try:
            canal_nome = input("Digite o nome do canal da Twitch: ")
            fingerprint = get_fingerprint()
            token_data = obter_playback_access_token(canal_nome, fingerprint)

            if token_data:
                logging.info(f"Token de acesso obtido com sucesso para o canal {canal_nome}")
                atualizar_playlist(canal_nome, token_data, fingerprint)
            else:
                logging.error("Falha ao obter o token de acesso.")
                continue  # Adicionamos um continue aqui para voltar ao início do loop

            while True:
                try:
                    response = obter_playlist_m3u8(canal_nome, token_data, fingerprint)
                    playlist_content = response.text
                    logging.info(f"Playlist M3U8 completa para o canal {canal_nome}:\n{playlist_content}")

                    # Adicione esta linha para processar a playlist
                    process_playlist(playlist_content)

                    break
                except Exception as e:
                    logging.error(f"Erro ao processar a playlist: {str(e)}")
                    time.sleep(5)
        except KeyboardInterrupt:
            logging.info("Programa encerrado pelo usuário.")
            break
        except Exception as e:
            logging.error(f"Erro durante a execução: {e}")

def configurar_logging():
    log_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'logs')
    os.makedirs(log_dir, exist_ok=True)
    log_file = os.path.join(log_dir, f'main_{datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")}.log')

    logging.basicConfig(filename=log_file, level=logging.INFO,
                        format='%(asctime)s - %(levelname)s - %(message)s')

    # Adicionar um handler para exibir logs no console
    console = logging.StreamHandler()
    console.setLevel(logging.INFO)
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    console.setFormatter(formatter)
    logging.getLogger('').addHandler(console)

if __name__ == "__main__":
    main()
