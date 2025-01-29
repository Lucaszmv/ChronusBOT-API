import socket
import threading
import time
import logging
from typing import Dict, Optional
from dataclasses import dataclass
from datetime import datetime

logger = logging.getLogger(__name__)

@dataclass
class ChatConnection:
    socket: socket.socket
    channel: str
    oauth_token: str
    username: str
    connected: bool = False
    last_ping: float = 0.0
    
class TwitchChatManager:
    def __init__(self):
        self.connections: Dict[int, ChatConnection] = {}
        self.TWITCH_HOST = "irc.chat.twitch.tv"
        self.TWITCH_PORT = 6667
        
    def connect_chat(self, bot_id: int, channel: str, oauth_token: str, username: str) -> bool:
        """
        Conecta ao chat da Twitch.
        
        Args:
            bot_id: ID do bot
            channel: Nome do canal
            oauth_token: Token OAuth da conta
            username: Nome de usuário da conta
        """
        try:
            sock = socket.socket()
            sock.connect((self.TWITCH_HOST, self.TWITCH_PORT))
            
            # Envia comandos de autenticação
            sock.send(f"PASS oauth:{oauth_token}\n".encode('utf-8'))
            sock.send(f"NICK {username}\n".encode('utf-8'))
            sock.send(f"JOIN #{channel}\n".encode('utf-8'))
            
            # Cria conexão e inicia thread de monitoramento
            conn = ChatConnection(sock, channel, oauth_token, username)
            self.connections[bot_id] = conn
            
            # Inicia thread para manter conexão viva
            threading.Thread(target=self._keep_alive, args=(bot_id,), daemon=True).start()
            
            logger.info(f"BOT {bot_id}: Conectado ao chat do canal {channel}")
            return True
            
        except Exception as e:
            logger.error(f"BOT {bot_id}: Erro ao conectar ao chat: {str(e)}")
            return False
            
    def disconnect_chat(self, bot_id: int):
        """Desconecta do chat."""
        if bot_id in self.connections:
            try:
                conn = self.connections[bot_id]
                conn.socket.close()
                conn.connected = False
                del self.connections[bot_id]
                logger.info(f"BOT {bot_id}: Desconectado do chat")
            except:
                pass
                
    def _keep_alive(self, bot_id: int):
        """Mantém a conexão viva enviando PING periodicamente."""
        backoff_time = 2
        
        while True:  # Loop infinito
            try:
                if not self.connections.get(bot_id) or not self.connections[bot_id].connected:
                    logger.info(f"BOT {bot_id}: Reconectando ao chat...")
                    self.reconnect_chat(bot_id)
                    time.sleep(1)
                    continue
                    
                conn = self.connections.get(bot_id)
                if not conn:
                    return
                    
                current_time = time.time()
                if current_time - conn.last_ping >= 60:
                    conn.socket.send("PING :tmi.twitch.tv\n".encode('utf-8'))
                    conn.last_ping = current_time
                    
                # Lê respostas do servidor
                data = conn.socket.recv(2048).decode('utf-8')
                if data.startswith('PING'):
                    conn.socket.send("PONG :tmi.twitch.tv\n".encode('utf-8'))
                    
            except Exception as e:
                logger.error(f"BOT {bot_id}: Erro no keep-alive: {str(e)}")
                time.sleep(backoff_time)
                continue
                
            time.sleep(1)
            
    def send_message(self, bot_id: int, message: str):
        """Envia mensagem para o chat."""
        conn = self.connections.get(bot_id)
        if conn and conn.connected:
            try:
                conn.socket.send(f"PRIVMSG #{conn.channel} :{message}\n".encode('utf-8'))
                logger.info(f"BOT {bot_id}: Mensagem enviada: {message}")
            except Exception as e:
                logger.error(f"BOT {bot_id}: Erro ao enviar mensagem: {str(e)}")

    def reconnect_chat(self, bot_id: int):
        while True:  # Tenta reconectar indefinidamente
            try:
                if bot_id in self.connections:
                    self.disconnect_chat(bot_id)
                
                success = self.connect_chat(bot_id)
                if success:
                    logger.info(f"BOT {bot_id}: Reconectado ao chat com sucesso")
                    return
                    
            except Exception as e:
                logger.error(f"BOT {bot_id}: Erro ao reconectar: {str(e)}")
                time.sleep(5)

# Instância global
chat_manager = TwitchChatManager()

def get_chat_manager() -> TwitchChatManager:
    return chat_manager 