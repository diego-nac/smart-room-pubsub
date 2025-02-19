import pika
from configs.envs import RABBITMQ_HOST, RABBITMQ_PORT, RABBITMQ_USER, RABBITMQ_PASSWORD

EXCHANGES = {
    "sensors_exchange": "topic",
    "commands_exchange": "topic",
}

SENSORS_ROUTING_KEYS = [
    "sensor.temperature",
    "sensor.luminosity",
    "sensor.presence",
]

COMMANDS_ROUTING_KEYS = [
    "command.lamp",
    "command.air_conditioner",
    "command.door",
]

QUEUES = {
    "queue.temperature": {"exchange": "sensors_exchange", "routing_key": "sensor.temperature.*"},
    "queue.luminosity": {"exchange": "sensors_exchange", "routing_key": "sensor.luminosity.*"},
    "queue.presence": {"exchange": "sensors_exchange", "routing_key": "sensor.presence.*"},
    "queue.gateway": {"exchange": "sensors_exchange", "routing_key": "sensor.#"},
    "queue.lamp": {"exchange": "commands_exchange", "routing_key": "command.lamp.*"},
    "queue.air_conditioner": {"exchange": "commands_exchange", "routing_key": "command.air_conditioner.*"},
    "queue.door": {"exchange": "commands_exchange", "routing_key": "command.door.*"},
}

def setup_rabbitmq():
    """Configures RabbitMQ with multiple exchanges, queues, and appropriate bindings."""
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

    print("RabbitMQ configuration completed successfully!")
    connection.close()

if __name__ == "__main__":
    setup_rabbitmq()
