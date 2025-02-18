import pika
import threading
from source.utils.rabbitmq.connection import RabbitMQConnection
from json import loads

def default_callback(body, exchange_name, routing_key):
    try:
        message = loads(body)
        print('Mensagem processada com sucesso')
        print(f"Exchange: {exchange_name}")
        print(f"Routing Key: {routing_key}")
        print(f"Corpo da mensagem: {message}")
    except Exception as e:
        print(f"Erro ao processar mensagem: {e}")

class RabbitMQConsumer:
    def __init__(self, connection: RabbitMQConnection, exchange_name, exchange_type="topic", queue_name=None, routing_key=None):
        self._channel = connection.get_channel()
        self._exchange_name = exchange_name
        self._exchange_type = exchange_type
        self._queue_name = queue_name
        self._routing_key = routing_key
        self.setup_exchange()
        if self._queue_name and self._routing_key:
            self.setup_queue()

    # Getters e Setters
    def get_exchange_name(self):
        return self._exchange_name

    def get_exchange_type(self):
        return self._exchange_type

    def get_queue_name(self):
        return self._queue_name

    def get_routing_key(self):
        return self._routing_key

    def set_exchange_name(self, exchange_name):
        self._exchange_name = exchange_name
        self.setup_exchange()

    def set_exchange_type(self, exchange_type):
        self._exchange_type = exchange_type
        self.setup_exchange()

    def set_queue_name(self, queue_name):
        self._queue_name = queue_name
        if self._routing_key:
            self.setup_queue()

    def set_routing_key(self, routing_key):
        self._routing_key = routing_key
        if self._queue_name:
            self.setup_queue()

    def setup_exchange(self):
        self._channel.exchange_declare(
            exchange=self._exchange_name,
            exchange_type=self._exchange_type,
            durable=True
        )

    def setup_queue(self):
        self._channel.queue_declare(queue=self._queue_name, durable=True)
        self._channel.queue_bind(
            exchange=self._exchange_name,
            queue=self._queue_name,
            routing_key=self._routing_key
        )

    def consume(self, callback_function=default_callback):
        def wrapped_callback(ch, method, properties, body):
            try:
                print(f"Mensagem recebida na fila {self._queue_name}")
                exchange_name = method.exchange
                routing_key = method.routing_key
                print(f"Mensagem recebida da exchange {exchange_name} com routing key {routing_key}")
                callback_function(body, exchange_name, routing_key)
                ch.basic_ack(delivery_tag=method.delivery_tag)
            except Exception as e:
                print(f"Erro ao processar mensagem: {e}")

        self._channel.basic_consume(queue=self._queue_name, on_message_callback=wrapped_callback)

        print(f"Consumindo mensagens da fila '{self._queue_name}'. Pressione CTRL+C para sair.")
        try:
            self._channel.start_consuming()
        except KeyboardInterrupt:
            print("\nInterrompido pelo usuário. Encerrando consumidor.")
            self._channel.stop_consuming()

    def start(self, callback_function=default_callback):
        consumer_thread = threading.Thread(target=self.consume, args=(callback_function,))
        consumer_thread.daemon = True
        consumer_thread.start()
        return consumer_thread


if __name__ == "__main__":
    connection = RabbitMQConnection()

    consumer = RabbitMQConsumer(
        connection=connection,
        exchange_name="sensors_exchange",
        queue_name="sensors_queue",
        routing_key="sensor.*"
    )
    consumer.start()

    input("Pressione ENTER para encerrar...\n")
    connection.close()
