import pika
import threading
from source.utils.rabbitmq.connection import RabbitMQConnection
from json import loads


def default_callback(body, exchange_name, routing_key, queue_name):
    """Callback padrão para processar mensagens recebidas."""
    try:
        message = loads(body)
        print(f"Corpo da mensagem: {message}\n")
    except Exception as e:
        print(f"Erro ao processar mensagem: {e}")


class RabbitMQConsumer:
    def __init__(self, connection: RabbitMQConnection, exchange_name, exchange_type="topic", queues=None):
        """
        :param connection: Conexão com o RabbitMQ
        :param exchange_name: Nome da exchange
        :param exchange_type: Tipo da exchange (padrão: topic)
        :param queues: Dicionário {queue_name: routing_key}
        """
        self._channel = connection.get_channel()
        self._exchange_name = exchange_name
        self._exchange_type = exchange_type
        self._queues = queues or {}
        self.setup_exchange()
        self.setup_queues()

    # Getters e Setters
    def get_exchange_name(self):
        return self._exchange_name

    def set_exchange_name(self, exchange_name):
        self._exchange_name = exchange_name
        self.setup_exchange()

    def get_queues(self):
        return self._queues

    def set_queues(self, queues):
        """Redefine todas as filas e realiza a nova configuração."""
        self._queues = queues
        self.setup_queues()

    # Configurações do broker
    def setup_exchange(self):
        self._channel.exchange_declare(
            exchange=self._exchange_name,
            exchange_type=self._exchange_type,
            durable=True
        )

    def setup_queues(self):
        """Configura todas as filas especificadas no dicionário self._queues."""
        for queue_name, routing_key in self._queues.items():
            self._declare_and_bind_queue(queue_name, routing_key)

    def _declare_and_bind_queue(self, queue_name, routing_key):
        """Declara e vincula uma fila à exchange."""
        self._channel.queue_declare(queue=queue_name, durable=True)
        self._channel.queue_bind(
            exchange=self._exchange_name,
            queue=queue_name,
            routing_key=routing_key
        )
        print(f"Inscrito na fila '{queue_name}' com routing key '{routing_key}'.")

    # Gerenciamento dinâmico de filas
    def add_queue(self, queue_name, routing_key):
        """Adiciona uma nova fila e a vincula à exchange, se ainda não existir."""
        if queue_name not in self._queues:
            self._queues[queue_name] = routing_key
            self._declare_and_bind_queue(queue_name, routing_key)
        else:
            print(f"A fila '{queue_name}' já existe. Use 'update_queue_routing_key' para atualizar a routing key.")

    def remove_queue(self, queue_name):
        """Remove uma fila da configuração atual."""
        if queue_name in self._queues:
            del self._queues[queue_name]
            print(f"A fila '{queue_name}' foi removida da configuração local.")
        else:
            print(f"A fila '{queue_name}' não existe na configuração atual.")

    def update_queue_routing_key(self, queue_name, new_routing_key):
        """Atualiza a routing key de uma fila existente."""
        if queue_name in self._queues:
            self._queues[queue_name] = new_routing_key
            self._channel.queue_bind(
                exchange=self._exchange_name,
                queue=queue_name,
                routing_key=new_routing_key
            )
            print(f"Routing key da fila '{queue_name}' atualizada para '{new_routing_key}'.")
        else:
            print(f"A fila '{queue_name}' não existe para atualização.")

    # Consumo de mensagens
    def _process_message(self, ch, method, properties, body, queue_name, callback_function):
        """Processa cada mensagem recebida chamando o callback fornecido."""
        try:
            print(f"\nMensagem recebida na fila '{queue_name}' (Routing Key: {method.routing_key})")
            print(f"Exchange: {method.exchange}")
            callback_function(body, method.exchange, method.routing_key, queue_name)
            ch.basic_ack(delivery_tag=method.delivery_tag)
        except Exception as e:
            print(f"Erro ao processar mensagem: {e}")

    def consume(self, callback_function=default_callback):
        """Inicia o consumo de todas as filas cadastradas."""
        for queue_name in self._queues:
            self._channel.basic_consume(
                queue=queue_name,
                on_message_callback=lambda ch, method, properties, body, q=queue_name: 
                    self._process_message(ch, method, properties, body, q, callback_function)
            )

        print(f"Consumindo mensagens das filas: {', '.join(self._queues.keys())}. Pressione CTRL+C para sair.")
        try:
            self._channel.start_consuming()
        except KeyboardInterrupt:
            print("Interrompido pelo usuário. Encerrando consumidor.")
            self._channel.stop_consuming()

    def start(self, callback_function=default_callback):
        """Inicia o consumo em uma thread separada."""
        consumer_thread = threading.Thread(target=self.consume, args=(callback_function,))
        consumer_thread.daemon = True
        consumer_thread.start()
        return consumer_thread


if __name__ == "__main__":
    connection = RabbitMQConnection()

    consumer = RabbitMQConsumer(
        connection=connection,
        exchange_name="sensors_exchange",
        queues={
            "queue.temperature": "sensor.temperature",
            "queue.luminosity": "sensor.luminosity",
        }
    )

    consumer.add_queue("queue.presence", "sensor.presence")
    consumer.start()

    input("Pressione ENTER para encerrar...\n")
    connection.close()
