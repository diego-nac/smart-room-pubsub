import pika
import json

class RabbitMQPublisher:
    def __init__(self, host="localhost", port=5672, user="guest", password="guest"):
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

    def setup_exchange(self, exchange_name, exchange_type="topic"):
        """
        Declara (cria) o Exchange se ainda não existir, 
        configurando o tipo (topic, fanout, direct, etc.).
        """
        self._channel.exchange_declare(
            exchange=exchange_name, 
            exchange_type=exchange_type, 
            durable=True
        )

    def setup_queue(self, queue_name, exchange_name, routing_key):
        """
        Declara a fila com durabilidade e a liga (bind) ao Exchange,
        usando a routing_key desejada.
        """
        self._channel.queue_declare(queue=queue_name, durable=True)
        self._channel.queue_bind(
            exchange=exchange_name,
            queue=queue_name,
            routing_key=routing_key
        )

    def publish_message(self, exchange_name, routing_key, message_body: dict):
        """
        Publica a mensagem (como JSON) no Exchange especificado,
        usando a routing_key fornecida.
        """
        # Converte o dicionário em JSON
        body_str = json.dumps(message_body)

        self._channel.basic_publish(
            exchange=exchange_name,
            routing_key=routing_key,
            body=body_str,
            properties=pika.BasicProperties(delivery_mode=2)  # Ex: persistência
        )

        print(f"Mensagem publicada no Exchange '{exchange_name}' "
              f"com routing_key '{routing_key}': {message_body}")

    def close(self):
        """
        Fecha a conexão de forma limpa quando não precisar mais publicar mensagens.
        """
        if self._connection and self._connection.is_open:
            self._connection.close()


if __name__ == "__main__":
    # Exemplo de uso

    publisher = RabbitMQPublisher(host="localhost", port=5672, user="guest", password="guest")

    # Supondo que nosso exchange seja o mesmo do consumer
    exchange_name = "sensors_exchange"
    queue_name = "queue.gateway"
    routing_key = "sensor.*"

    # 1. Configura o Exchange e a Fila
    publisher.setup_exchange(exchange_name, exchange_type="topic")
    publisher.setup_queue(queue_name, exchange_name, routing_key)

    # 2. Publica uma mensagem de teste
    publisher.publish_message(
        exchange_name=exchange_name,
        routing_key="sensor.10",  # Exemplo de routing_key concreta
        message_body={"ola": "mundo"}
    )

    # 3. Fecha a conexão (opcional, pode ficar aberta se for publicar mais)
    publisher.close()
