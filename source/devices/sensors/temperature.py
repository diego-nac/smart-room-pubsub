from source.utils.rabbitmq import RabbitMQConnection
from source.devices.sensors.abs.sensor_abs import SensorABS
from typing import Dict, Any
from random import uniform
from time import strftime, localtime


class TemperatureSensor(SensorABS):
    """
    Concrete implementation of a temperature sensor.
    Simulates temperature data generation between 18°C and 30°C.
    """

    def __init__(self, device_id: str, device_name: str, connection: RabbitMQConnection):
        super().__init__(device_id, device_name, "temperature", connection)

    def generate_data(self) -> Dict[str, Any]:
        """Generates random temperature data."""
        temperature_value = round(uniform(18.0, 30.0), 2)
        timestamp = strftime("%Y-%m-%d %H:%M:%S", localtime())
        return {
            "device_id": self.id,
            "device_name": self.name,
            "device_type": self.type,
            "timestamp": timestamp,
            "temperature": temperature_value
        }


if __name__ == "__main__":
    connection = RabbitMQConnection()
    temperature_sensor = TemperatureSensor("temp_sensor_01", "Room Temperature Sensor", connection)
    temperature_sensor.start()
