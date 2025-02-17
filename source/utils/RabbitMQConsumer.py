import pika
import threading
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
    def __init__(self, host="localhost", port=5672, user="guest", password="guest"):
        self._host = host
        self._port = port
        self._user = user
        self._pass = password
        self._credentials = pika.PlainCredentials(self._user, self._pass)
        self._connection_params = pika.ConnectionParameters(host=self._host, port=self._port, credentials=self._credentials)
        self._connection = pika.BlockingConnection(self._connection_params)
        self._channel = self._connection.channel()

    def setup_exchange(self, exchange_name, exchange_type="topic"):
        self._channel.exchange_declare(exchange=exchange_name, exchange_type=exchange_type, durable=True)

    def setup_queue(self, queue_name, exchange_name, routing_key):
        self._channel.queue_declare(queue=queue_name, durable=True)
        self._channel.queue_bind(exchange=exchange_name, queue=queue_name, routing_key=routing_key)

    def consume(self, queue_name, callback_function):
        def wrapped_callback(ch, method, properties, body):
            try:
                print(f"Mensagem recebida na fila {queue_name}")
                exchange_name = method.exchange
                routing_key = method.routing_key
                print(f"Mensagem recebida da exchange {exchange_name} com routing key {routing_key}")
                callback_function(body, exchange_name, routing_key)
                ch.basic_ack(delivery_tag=method.delivery_tag)  
            except Exception as e:
                print(f"Erro ao processar mensagem: {e}")
        self._channel.basic_consume(queue=queue_name, on_message_callback=wrapped_callback)

        print(f"Consumindo mensagens da fila '{queue_name}'. Pressione CTRL+C para sair.")
        try:
            self._channel.start_consuming()
        except KeyboardInterrupt:
            print("\nInterrompido pelo usuário. Encerrando consumidor.")
            self._channel.stop_consuming()
            self._connection.close()

    def start(self, queue_name, callback_function=default_callback):
        consumer_thread = threading.Thread(target=self.consume, args=(queue_name, callback_function))
        consumer_thread.daemon = True
        consumer_thread.start()
        return consumer_thread


if __name__ == "__main__":
    consumer = RabbitMQConsumer()
    exchange_name = "sensors_exchange"
    queue_name = "queue.gateway"
    routing_key = "sensor.*"
    consumer.setup_exchange(exchange_name)
    consumer.setup_queue(queue_name, exchange_name, routing_key)

    consumer.start(queue_name)

    input("Pressione ENTER para encerrar...\n")
