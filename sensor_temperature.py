from source.devices.sensors.temperature import TemperatureSensor
from source.utils.rabbitmq import RabbitMQConnection

if __name__ == "__main__":
    connection = RabbitMQConnection()
    temperature_sensor = TemperatureSensor("temp_sensor_01", "Room Temperature Sensor", 'ac_1', connection)
    temperature_sensor.start()