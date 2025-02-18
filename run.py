from source.utils.rabbitmq import setup_rabbitmq, RabbitMQConnection, RabbitMQConsumer

if __name__ == "__main__":
    # setup_rabbitmq()
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
