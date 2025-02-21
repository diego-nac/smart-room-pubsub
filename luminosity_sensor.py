from source.devices.sensors.luminosity import LuminositySensor
from source.utils.rabbitmq.connection import RabbitMQConnection


if __name__ == "__main__":
    connection = RabbitMQConnection()
    luminosity_sensor = LuminositySensor("sensor_lum_1", "Room Luminosity Sensor", "lamp_1", connection)
    luminosity_sensor.start()
