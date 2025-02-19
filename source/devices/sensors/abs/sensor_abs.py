from threading import Thread
import time
from abc import ABC, abstractmethod
from typing import Dict, Any
import json
from configs.envs import SENSOR_DELAY
from source.utils.rabbitmq.connection import RabbitMQConnection
from source.utils.rabbitmq.publisher import RabbitMQPublisher
from source.utils.rabbitmq.consumer import RabbitMQConsumer

class SensorABS(ABC):
    """
    Abstract class representing smart sensors.
    All sensors will only communicate via RabbitMQ using JSON format:
    - Sensors publish data periodically.
    - Sensors listen for shutdown commands from a specific queue.
    """

    def __init__(self, device_id: str, device_name: str, device_type: str, connection: RabbitMQConnection):
        self._id = device_id
        self._name = device_name
        self._type = device_type
        self._is_on = True
        self._publisher = RabbitMQPublisher(
            connection=connection,
            exchange_name="sensors_exchange",
            queue_name=f"queue.{self._type}",
            routing_key=f"sensor.{self._type}"
        )
        self._consumer = RabbitMQConsumer(
            connection=connection,
            exchange_name="shutdown_exchange",
            queues={f"shutdown_{self._id}": f"shutdown.{self._id}"}
        )

    @property
    def id(self) -> str:
        return self._id

    @property
    def name(self) -> str:
        return self._name

    @property
    def type(self) -> str:
        return self._type

    @property
    def is_on(self) -> bool:
        return self._is_on

    def publish_data(self, data: Dict[str, Any]):
        """Publish sensor data to RabbitMQ in JSON format."""
        if self._is_on:
            self._publisher.publish_message(data)

    def listen_for_shutdown(self):
        """Listens for shutdown commands from RabbitMQ."""
        print(f"[RabbitMQ] {self._name} listening for shutdown commands...")

        def shutdown_callback(body, exchange_name, routing_key, queue_name):
            message = json.loads(body)
            if message.get("command") == "shutdown":
                print(f"[RabbitMQ] Shutdown command received for {self._name}.")
                self._is_on = False
            if message.get("command") == "shutdown":
                print(f"[RabbitMQ] Shutdown command received for {self._name}.")
                self._is_on = False

        self._consumer.start(callback_function=shutdown_callback)

    @abstractmethod
    def generate_data(self) -> Dict[str, Any]:
        """Generate sensor-specific data."""
        pass

    def start(self):
        """
        Starts the sensor:
        - One thread for periodic data publishing.
        - Another thread for listening to shutdown commands via RabbitMQ.
        """
        print(f"Starting sensor {self._name} ({self._type})...")
        Thread(target=self._publish_periodically, daemon=True).start()
        Thread(target=self.listen_for_shutdown, daemon=True).start()

        while self._is_on:
            time.sleep(1)
        print(f"Sensor {self._name} has been shut down.")

    def _publish_periodically(self):
        """Periodically publishes generated data every 10 seconds."""
        while self._is_on:
            data = self.generate_data()
            self.publish_data(data)
            print(f"[Publish] {self._name} published data: {data}")
            time.sleep(SENSOR_DELAY)

    def __str__(self):
        state_str = "ON" if self.is_on else "OFF"
        return f"SensorABS(ID: {self._id}, Name: {self._name}, Type: {self._type}, State: {state_str})"
