import pika
from configs.envs import RABBITMQ_HOST, RABBITMQ_PORT, RABBITMQ_USER, RABBITMQ_PASSWORD
class RabbitMQConnection:
    def __init__(self, host=RABBITMQ_HOST, port=RABBITMQ_PORT, user=RABBITMQ_USER, password=RABBITMQ_PASSWORD):
        self._host = host
        self._port = port
        self._user = user
        self._password = password
        self._credentials = pika.PlainCredentials(self._user, self._password)
        self._connection_params = pika.ConnectionParameters(
            host=self._host,
            port=self._port,
            credentials=self._credentials
        )
        self._connection = pika.BlockingConnection(self._connection_params)
        self._channel = self._connection.channel()

    # Getters e Setters
    def get_host(self):
        return self._host

    def set_host(self, host):
        self._host = host

    def get_port(self):
        return self._port

    def set_port(self, port):
        self._port = port

    def get_user(self):
        return self._user

    def set_user(self, user):
        self._user = user

    def get_password(self):
        return self._password

    def set_password(self, password):
        self._password = password

    def get_channel(self):
        return self._channel

    def close(self):
        if self._connection and self._connection.is_open:
            self._connection.close()
