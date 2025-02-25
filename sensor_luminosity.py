from source.devices.sensors.luminosity import LuminositySensor
from source.utils.rabbitmq.connection import RabbitMQConnection


if __name__ == "__main__":
    connection = RabbitMQConnection()
    luminosity_sensor = LuminositySensor("luminosity_sensor", "Room Luminosity Sensor", "lamp", connection)
    luminosity_sensor.start()
