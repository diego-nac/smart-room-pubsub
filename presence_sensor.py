from source.devices.sensors.presence import PresenceSensor
from source.utils.rabbitmq import RabbitMQConnection

if __name__ == "__main__":
    connection = RabbitMQConnection()
    presence_sensor = PresenceSensor("presence_sensor_01", "Room Presence Sensor", 'door', connection)
    presence_sensor.start()
