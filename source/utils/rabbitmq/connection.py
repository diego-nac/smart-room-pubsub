import pika
import time
from pika.exceptions import AMQPConnectionError, StreamLostError
from configs.envs import RABBITMQ_HOST, RABBITMQ_PORT, RABBITMQ_USER, RABBITMQ_PASSWORD


class RabbitMQConnection:
    def __init__(self, host=RABBITMQ_HOST, port=RABBITMQ_PORT, user=RABBITMQ_USER, password=RABBITMQ_PASSWORD):
        self._host = host
        self._port = port
        self._user = user
        self._password = password
        self._connect_with_retry()  # Reconexão automática

    def _connect_with_retry(self, retries=5, delay=5):
        """Tenta reconectar automaticamente ao RabbitMQ em caso de falhas."""
        attempt = 0
        while attempt < retries:
            try:
                print(f"[RabbitMQ] Tentando conectar ao broker ({self._host}:{self._port}) - Tentativa {attempt + 1}/{retries}")
                self._update_connection()
                print("[RabbitMQ] Conexão estabelecida com sucesso!")
                return
            except (AMQPConnectionError, StreamLostError) as e:
                attempt += 1
                print(f"[RabbitMQ] Falha ao conectar: {e}. Tentando novamente em {delay}s...")
                time.sleep(delay)

        raise ConnectionError(f"[RabbitMQ] Falha ao conectar após {retries} tentativas.")

    def _update_connection(self):
        """Atualiza a conexão e parâmetros sempre que necessário, com heartbeat configurado."""
        self._credentials = pika.PlainCredentials(self._user, self._password)
        self._connection_params = pika.ConnectionParameters(
            host=self._host,
            port=self._port,
            credentials=self._credentials,
            heartbeat=600,  # Mantém a conexão ativa
            blocked_connection_timeout=300  # Evita desconexão em operações prolongadas
        )
        # Fecha a conexão existente, se aberta
        if hasattr(self, '_connection') and self._connection.is_open:
            self.close()

        self._connection = pika.BlockingConnection(self._connection_params)
        self._channel = self._connection.channel()

    @property
    def host(self):
        return self._host

    @host.setter
    def host(self, value):
        self._host = value
        self._connect_with_retry()

    @property
    def port(self):
        return self._port

    @port.setter
    def port(self, value):
        self._port = value
        self._connect_with_retry()

    @property
    def user(self):
        return self._user

    @user.setter
    def user(self, value):
        self._user = value
        self._connect_with_retry()

    @property
    def password(self):
        return self._password

    @password.setter
    def password(self, value):
        self._password = value
        self._connect_with_retry()

    @property
    def channel(self):
        return self._channel

    def close(self):
        """Fecha a conexão e o canal com o RabbitMQ, se estiverem abertos."""
        try:
            if hasattr(self, '_channel') and self._channel.is_open:
                self._channel.close()
            if hasattr(self, '_connection') and self._connection.is_open:
                self._connection.close()
            print("[RabbitMQ] Conexão e canal fechados com sucesso.")
        except Exception as e:
            print(f"[RabbitMQ] Erro ao fechar a conexão: {e}")
