from threading import Thread, Event
import time
from abc import ABC, abstractmethod
from typing import Dict, Any
import json
from configs.envs import SENSOR_DELAY
from source.utils.rabbitmq.connection import RabbitMQConnection
from source.utils.rabbitmq.publisher import RabbitMQPublisher
from source.utils.rabbitmq.consumer import RabbitMQConsumer
from pika.exceptions import StreamLostError, AMQPConnectionError
from time import strftime, localtime


class SensorABS(ABC):
    """Abstract class representing smart sensors communicating via RabbitMQ."""

    def __init__(self, device_id: str, device_name: str, related_device: str, device_type: str, connection: RabbitMQConnection):
        self._id = device_id
        self._name = device_name
        self._type = device_type
        self.timestamp = strftime("%Y-%m-%d %H:%M:%S", localtime())
        self._is_on = True
        self._shutdown_event = Event()  
        self.related_device = related_device
        self._publisher = RabbitMQPublisher(
            connection=connection,
            exchange_name="sensors_exchange",
            queue_name=f"queue.{self._type}",
            routing_key=f"sensor.{self._type}"
        )
        self._consumer = RabbitMQConsumer(
            connection=connection,
            exchange_name="commands_exchange",
            queues={f"queue.{self._id}": f"command.{self._id}"}
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
        """Publish sensor data with reconnection handling."""
        try:
            if self._is_on:
                self._publisher.publish_message(data)
        except (StreamLostError, AMQPConnectionError) as e:
            print(f"[RabbitMQ] Erro ao publicar: {e}. Tentando reconectar...")
            self._publisher.reconnect()  # Implementar reconexão segura no publisher
            self._publisher.publish_message(data)

    def listen_for_shutdown(self):
        """Listens for on/off commands with reconnection logic."""
        print(f"[RabbitMQ] {self._name} listening for commands...")

        def command_callback(body, exchange_name, routing_key, queue_name):
            message = json.loads(body)
            action = message.get("action")
            if action == "off":
                print(f"[RabbitMQ] OFF command received for {self._name}.")
                self._is_on = False
                self._shutdown_event.set()  # Encerra a thread principal
            elif action == "on":
                print(f"[RabbitMQ] ON command received for {self._name}.")
                self._is_on = True

        try:
            self._consumer.start(callback_function=command_callback)
        except (StreamLostError, AMQPConnectionError) as e:
            print(f"[RabbitMQ] Erro ao consumir: {e}. Tentando reconectar...")
            self._consumer.reconnect()
            self._consumer.start(callback_function=command_callback)

    @abstractmethod
    def generate_data(self) -> Dict[str, Any]:
        """Generate sensor-specific data."""
        pass

    def start(self):
        """Starts sensor threads and handles graceful shutdown."""
        print(f"Starting sensor {self._name} ({self._type})...")
        Thread(target=self._publish_periodically, daemon=True).start()
        # Thread(target=self.listen_for_shutdown, daemon=True).start()

        try:
            self._shutdown_event.wait()  # Mantém processo vivo sem ocupar CPU
            print(f"Sensor {self._name} has been shut down.")
        except KeyboardInterrupt:
            print(f"[Sensor] {self._name} interrompido manualmente.")
            self._shutdown_event.set()

    def _publish_periodically(self):
        """Periodically publishes data, handling reconnection errors."""
        while not self._shutdown_event.is_set() and self._is_on:
            try:
                data = self.generate_data()
                self.publish_data(data)
                print(f"[Publish] {self._name} published data: {data}")
                time.sleep(SENSOR_DELAY)
            except Exception as e:
                print(f"[Sensor] Erro durante publicação periódica: {e}")
                time.sleep(5)  # Aguarda antes de tentar novamente

    def __str__(self):
        state_str = "ON" if self.is_on else "OFF"
        return f"SensorABS(ID: {self._id}, Name: {self._name}, Type: {self._type}, State: {state_str})"
