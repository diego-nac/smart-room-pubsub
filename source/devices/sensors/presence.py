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

    def __init__(self, device_id: str, device_name: str, related_device: str, connection: RabbitMQConnection):
        super().__init__(device_id, device_name, related_device, "presence", connection)
        self.status = False

    def generate_data(self) -> Dict[str, Any]:
        """Generates random presence data (True for presence, False for no presence)."""
        self.status = choice([True, False])
        self.timestamp = strftime("%Y-%m-%d %H:%M:%S", localtime())
        
        return {
            "id": self.id,                           
            "name": self.name,                       
            "type": "sensor",                        
            "subtype": self.type,                   
            "state": "on" if self.status else "off",  
            "timestamp": self.timestamp,                  
            "related_device": self.related_device    
        }


if __name__ == "__main__":
    connection = RabbitMQConnection()
    presence_sensor = PresenceSensor("presence_sensor_01", "Room Presence Sensor", connection)
    presence_sensor.start()
