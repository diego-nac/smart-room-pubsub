from source.utils.rabbitmq import RabbitMQConnection, RabbitMQPublisher

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