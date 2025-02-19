from source.utils.rabbitmq import RabbitMQConnection
from source.devices.sensors.abs.sensor_abs import SensorABS
from typing import Dict, Any
from random import choice
from time import strftime, localtime


class PresenceSensor(SensorABS):
    """
    Concrete implementation of a presence sensor.
    Simulates presence detection by randomly determining if someone is present or not.
    """

    def __init__(self, device_id: str, device_name: str, connection: RabbitMQConnection):
        super().__init__(device_id, device_name, "presence", connection)

    def generate_data(self) -> Dict[str, Any]:
        """Generates random presence data (True for presence, False for no presence)."""
        presence_detected = choice([True, False])
        timestamp = strftime("%Y-%m-%d %H:%M:%S", localtime())
        return {
            "device_id": self.id,
            "device_name": self.name,
            "device_type": self.type,
            "timestamp": timestamp,
            "presence": presence_detected
        }


if __name__ == "__main__":
    connection = RabbitMQConnection()
    presence_sensor = PresenceSensor("presence_sensor_01", "Room Presence Sensor", connection)
    presence_sensor.start()
