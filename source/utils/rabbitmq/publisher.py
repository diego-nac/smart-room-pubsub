import pika
import json

from source.utils.rabbitmq.connection import RabbitMQConnection

class RabbitMQPublisher:
    def __init__(self, connection: RabbitMQConnection, exchange_name, exchange_type="topic", queue_name=None, routing_key=None):
        self._channel = connection.get_channel()
        self._exchange_name = exchange_name
        self._exchange_type = exchange_type
        self._queue_name = queue_name
        self._routing_key = routing_key
        self.setup_exchange()
        if self._queue_name and self._routing_key:
            self.setup_queue()

    # Getters
    def get_exchange_name(self):
        return self._exchange_name

    def get_exchange_type(self):
        return self._exchange_type

    def get_queue_name(self):
        return self._queue_name

    def get_routing_key(self):
        return self._routing_key

    # Setters
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

    def publish_message(self, message_body: dict):
        body_str = json.dumps(message_body)
        self._channel.basic_publish(
            exchange=self._exchange_name,
            routing_key=self._routing_key,
            body=body_str,
            properties=pika.BasicProperties(delivery_mode=2)
        )
        print(f"Mensagem publicada no Exchange '{self._exchange_name}' "
              f"com routing_key '{self._routing_key}': {message_body}")

if __name__ == "__main__":
    connection = RabbitMQConnection()
    publisher = RabbitMQPublisher(
        connection=connection,
        exchange_name="sensors_exchange",
        queue_name="sensors_queue",
        routing_key="sensor.*"
    )

    publisher.publish_message({"ola": "mundo"})
    connection.close()