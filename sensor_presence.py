from source.devices.sensors.presence import PresenceSensor
from source.utils.rabbitmq import RabbitMQConnection

if __name__ == "__main__":
    connection = RabbitMQConnection()
    presence_sensor = PresenceSensor("presence_sensor", "Room Presence Sensor", 'door_actuator', connection)
    presence_sensor.start()
