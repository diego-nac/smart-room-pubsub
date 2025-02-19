
from source.utils.rabbitmq import RabbitMQConnection
from source.devices.sensors.abs.sensor_abs import SensorABS
from typing import Dict, Any
from random import uniform
from time import strftime, localtime

class LuminositySensor(SensorABS):
    """
    Concrete implementation of a luminosity sensor.
    Simulates luminosity data generation between 0 and 1000 lux.
    """

    def __init__(self, device_id: str, device_name: str, connection: RabbitMQConnection):
        super().__init__(device_id, device_name, "luminosity", connection)

    def generate_data(self) -> Dict[str, Any]:
        """Generates random luminosity data."""
        luminosity_value = round(uniform(0.0, 1000.0), 2)
        timestamp = strftime("%Y-%m-%d %H:%M:%S", localtime())
        return {
            "device_id": self.id,
            "device_name": self.name,
            "device_type": self.type,
            "timestamp": timestamp,
            "luminosity": luminosity_value
        }
