import grpc
from concurrent import futures
import time
import json
import argparse
import threading
from .proto.actuators_pb2 import Response
from .proto.actuators_pb2_grpc import ActuatorServiceServicer, add_ActuatorServiceServicer_to_server
from source.utils.rabbitmq.connection import RabbitMQConnection
from configs.envs import DEVICES_DELAY, GRPC_DOOR_PORT

class DoorActuatorServer(ActuatorServiceServicer):
    """
    Serviço gRPC para controle da porta.
    Publica seu status via RabbitMQ no seguinte formato:
      {
          "id": "<device_id>",
          "type": "door",
          "state": "open" ou "closed"
      }
    """

    def __init__(self, device_id, grpc_port, rabbitmq_host='localhost'):
        self.device_id = device_id
        self.grpc_port = grpc_port
        self.rabbitmq_host = rabbitmq_host
        self.open = False  # Porta inicia fechada
        print(f"[DEVICE INFO] Porta '{self.device_id}' inicializada com state='closed'.")
        self.publish_status()

    def publish_status(self):
        try:
            connection = RabbitMQConnection(host=self.rabbitmq_host)
            channel = connection.channel
            channel.exchange_declare(
                exchange='sensors_exchange',
                exchange_type='topic',
                durable=True
            )
            message = {
                "id": self.device_id,
                "type": "door",
                "state": "open" if self.open else "closed"
            }
            routing_key = f"command.door.{self.device_id}"
            channel.basic_publish(
                exchange='sensors_exchange',
                routing_key=routing_key,
                body=json.dumps(message)
            )
            connection.close()
            print(f"[DEVICE SUCCESS] Status da porta '{self.device_id}' publicado: {message}")
        except Exception as e:
            print(f"[DEVICE ERROR] Erro ao publicar status da porta '{self.device_id}': {e}")

    def controlDoor(self, request, context):
        """
        Atualiza o estado da porta conforme a requisição gRPC.
        """
        print("[DEVICE DEBUG] Requisição gRPC para porta recebida:")
        print(f"         is_open: {request.is_open}")  # Use is_open!
        self.open = request.is_open              # Atualiza com is_open
        print(f"[DEVICE INFO] Porta '{self.device_id}' atualizada para: {'open' if self.open else 'closed'}")
        self.publish_status()
        return Response(success=True, error_message="")


    def _periodic_publish(self, interval=60):
        while True:
            self.publish_status()
            time.sleep(DEVICES_DELAY)

    def start(self):
        print("[DEVICE INFO] Iniciando thread de publicação periódica para porta...")
        periodic_thread = threading.Thread(target=self._periodic_publish, args=(10,), daemon=True)
        periodic_thread.start()
        print("[DEVICE INFO] Thread de publicação iniciada para porta.")

        print("[DEVICE INFO] Criando servidor gRPC para porta...")
        server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
        add_ActuatorServiceServicer_to_server(self, server)
        server.add_insecure_port(f'[::]:{self.grpc_port}')
        server.start()
        print(f"[DEVICE INFO] Porta '{self.device_id}' ouvindo na porta {self.grpc_port}")

        try:
            server.wait_for_termination()
        except KeyboardInterrupt:
            server.stop(0)
            print("[DEVICE INFO] Servidor gRPC da porta encerrado.")

    @classmethod
    def run(cls):
        parser = argparse.ArgumentParser(description="Servidor gRPC para DoorActuator")
        parser.add_argument('--device_id', type=str, default='door_actuator', help='ID da porta')
        parser.add_argument('--grpc_port', type=int, default=GRPC_DOOR_PORT, help='Porta do servidor gRPC')
        parser.add_argument('--rabbitmq_host', type=str, default='localhost', help='Host do RabbitMQ')
        args = parser.parse_args()
        print(f"[DEVICE INFO] Iniciando servidor para porta '{args.device_id}' na porta {args.grpc_port}...")
        server_instance = cls(args.device_id, args.grpc_port, args.rabbitmq_host)
        server_instance.start()

if __name__ == '__main__':
    DoorActuatorServer.run()
