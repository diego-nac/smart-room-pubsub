import pika
from configs.envs import RABBITMQ_HOST, RABBITMQ_PORT, RABBITMQ_USER, RABBITMQ_PASSWORD

class RabbitMQConnection:
    def __init__(self, host=RABBITMQ_HOST, port=RABBITMQ_PORT, user=RABBITMQ_USER, password=RABBITMQ_PASSWORD):
        self._host = host
        self._port = port
        self._user = user
        self._password = password
        self._update_connection()

    def _update_connection(self):
        """Atualiza a conexão e parâmetros sempre que necessário."""
        self._credentials = pika.PlainCredentials(self._user, self._password)
        self._connection_params = pika.ConnectionParameters(
            host=self._host,
            port=self._port,
            credentials=self._credentials
        )
        if hasattr(self, '_connection') and self._connection.is_open:
            self._connection.close()
        self._connection = pika.BlockingConnection(self._connection_params)
        self._channel = self._connection.channel()

    @property
    def host(self):
        return self._host

    @host.setter
    def host(self, value):
        self._host = value
        self._update_connection()

    @property
    def port(self):
        return self._port

    @port.setter
    def port(self, value):
        self._port = value
        self._update_connection()

    @property
    def user(self):
        return self._user

    @user.setter
    def user(self, value):
        self._user = value
        self._update_connection()

    @property
    def password(self):
        return self._password

    @password.setter
    def password(self, value):
        self._password = value
        self._update_connection()

    @property
    def channel(self):
        return self._channel

    def close(self):
        """Fecha a conexão com o RabbitMQ, se estiver aberta."""
        if self._connection and self._connection.is_open:
            self._connection.close()
