import pika
from configs.envs import RABBITMQ_HOST, RABBITMQ_PORT, RABBITMQ_USER, RABBITMQ_PASSWORD


EXCHANGES = {
    "sensors_exchange": "topic",    
    "commands_exchange": "topic",   
}


SENSORS_ROUTING_KEYS = [
    "sensor.temperatura",
    "sensor.luminosidade",
    "sensor.presenca",
]


COMMANDS_ROUTING_KEYS = [
    "command.lampada",
    "command.ar_condicionado",
    "command.porta",
]


QUEUES = {
    "queue.temperatura": {"exchange": "sensors_exchange", "routing_key": "sensor.temperatura.*"},
    "queue.luminosidade": {"exchange": "sensors_exchange", "routing_key": "sensor.luminosidade.*"},
    "queue.presenca": {"exchange": "sensors_exchange", "routing_key": "sensor.presenca.*"},
    "queue.gateway": {"exchange": "sensors_exchange", "routing_key": "sensor.#"},  
    "queue.lampada": {"exchange": "commands_exchange", "routing_key": "command.lampada.*"},
    "queue.ar_condicionado": {"exchange": "commands_exchange", "routing_key": "command.ar_condicionado.*"},
    "queue.porta": {"exchange": "commands_exchange", "routing_key": "command.porta.*"},
}


def setup_rabbitmq():
    """Configura o RabbitMQ com múltiplas exchanges, filas e bindings apropriados."""
    credentials = pika.PlainCredentials(RABBITMQ_USER, RABBITMQ_PASSWORD)
    connection = pika.BlockingConnection(
        pika.ConnectionParameters(host=RABBITMQ_HOST, port=RABBITMQ_PORT, credentials=credentials)
    )
    channel = connection.channel()

    
    for exchange_name, exchange_type in EXCHANGES.items():
        channel.exchange_declare(exchange=exchange_name, exchange_type=exchange_type, durable=True)

    
    for queue_name, config in QUEUES.items():
        exchange = config["exchange"]
        routing_key = config["routing_key"]

        channel.queue_declare(queue=queue_name, durable=True)
        channel.queue_bind(exchange=exchange, queue=queue_name, routing_key=routing_key)

    print("Configuração do RabbitMQ concluída com sucesso!")
    connection.close()


if __name__ == "__main__":
    setup_rabbitmq()
