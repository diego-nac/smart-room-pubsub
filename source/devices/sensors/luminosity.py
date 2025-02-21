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

    def __init__(self, device_id: str, device_name: str, related_device: str, connection: RabbitMQConnection):
        super().__init__(device_id, device_name, related_device, "luminosity", connection)
        self.value = 0.0

    def generate_data(self) -> Dict[str, Any]:
        """Generates random luminosity data following the expected format by the Gateway."""
        self.value = round(uniform(0.0, 1000.0), 2)
        self.timestamp = strftime("%Y-%m-%d %H:%M:%S", localtime())
        return {
            "id": self.id,                           
            "name": self.name,                       
            "type": "sensor",                        
            "subtype": self.type,                 
            "luminosity": self.value,          
            "state": "on" if self.is_on else "off",  
            "timestamp": self.timestamp,                  
            "related_device": self.related_device    
        }


if __name__ == "__main__":
    
    connection = RabbitMQConnection()
    luminosity_sensor = LuminositySensor("sensor_lum_1", "Room Luminosity Sensor", "lamp_1", connection)
    luminosity_sensor.start()
