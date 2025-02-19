from source.utils.rabbitmq import RabbitMQConnection, RabbitMQConsumer

if __name__ == "__main__":

    connection = RabbitMQConnection()

    consumer = RabbitMQConsumer(
        connection=connection,
        exchange_name="sensors_exchange",
        # Dicionário de filas -  {queue_name: routing_keys}
        queues={
            "queue.temperature": "sensor.temperature",
            "queue.luminosity": "sensor.luminosity",
        }
    )

    consumer.add_queue("queue.presence", "sensor.presence")
    consumer.remove_queue("queue.presence")

    consumer.start()
    input("Pressione ENTER para encerrar...\n")
    connection.close()