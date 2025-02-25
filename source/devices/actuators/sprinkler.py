import grpc
from concurrent import futures
import time
import json
import argparse
import threading
from .proto.actuators_pb2 import Response
from .proto.actuators_pb2_grpc import ActuatorServiceServicer, add_ActuatorServiceServicer_to_server
from source.utils.rabbitmq.connection import RabbitMQConnection
from configs.envs import RABBITMQ_HOST, GRPC_SPLINKER_PORT

class SprinklerServer(ActuatorServiceServicer):
    """
    Classe que implementa o serviço gRPC para controle do sprinkler,
    gerencia a publicação periódica de status via RabbitMQ e inicia o servidor.
    """

    def __init__(self, device_id, grpc_port =GRPC_SPLINKER_PORT, rabbitmq_host=RABBITMQ_HOST):
        self.device_id = device_id
        self.grpc_port = grpc_port
        self.rabbitmq_host = rabbitmq_host
        self.active = False
        print(f"[INFO] Sprinkler '{self.device_id}' inicializado.")
        self.publish_status()  # Publica o status inicial

    def publish_status(self):
        """
        Publica o status atual do sprinkler no RabbitMQ utilizando a conexão robusta.
        """
        try:
            print(f"[INFO] Conectando ao RabbitMQ em {self.rabbitmq_host}...")
            connection = RabbitMQConnection(host=self.rabbitmq_host)
            channel = connection.channel

            # Declara o exchange 'sensors_exchange'
            channel.exchange_declare(
                exchange='sensors_exchange', exchange_type='topic', durable=True
            )

            message = {
                'id': self.device_id,
                'type': 'actuator',
                'subtype': 'sprinkler',
                'state': 'on' if self.active else 'off',
                'grpc_host': 'localhost',
                'grpc_port': self.grpc_port,
                'temperature': None,
                'luminosity': None,
                'related_device': None
            }
            routing_key = f"command.sprinkler.{self.device_id}"

            # Supondo que o gateway esteja inscrito em filas que recebam
            # mensagens com routing key "command.sprinkler.*",
            # a mensagem será encaminhada para a fila "queue.sprinkler.{device_id}".
            print(f"[INFO] Publicando mensagem no RabbitMQ:")
            print(f"       Exchange: 'sensors_exchange'")
            print(f"       Routing Key: '{routing_key}' (Fila associada: 'queue.sprinkler')")
            print(f"       Mensagem: {json.dumps(message, indent=2)}")

            channel.basic_publish(
                exchange='sensors_exchange',
                routing_key=routing_key,
                body=json.dumps(message)
            )
            connection.close()
            print(f"[SUCCESS] Status publicado com sucesso no RabbitMQ.\n")
        except Exception as e:
            print(f"[ERROR] Falha ao publicar no RabbitMQ: {str(e)}\n")

    def controlSprinkler(self, request, context):
        """
        Atualiza o estado do sprinkler conforme a requisição gRPC e publica o status atualizado.
        """
        self.active = request.active
        print(f"[INFO] Estado do sprinkler alterado para: {'ON' if self.active else 'OFF'}")
        self.publish_status()
        return Response(success=True, error_message="")

    def _periodic_publish(self, interval=60):
        """
        Método interno que publica periodicamente o status do sprinkler.
        """
        print(f"[INFO] Iniciando publicação periódica a cada {interval} segundos...\n")
        while True:
            self.publish_status()
            time.sleep(interval)

    def start(self):
        """
        Inicializa a thread de publicação periódica e o servidor gRPC.
        """
        # Inicia a thread para publicação periódica
        periodic_thread = threading.Thread(
            target=self._periodic_publish, args=(10,), daemon=True
        )
        periodic_thread.start()

        # Cria e configura o servidor gRPC
        server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
        add_ActuatorServiceServicer_to_server(self, server)
        server.add_insecure_port(f'[::]:{self.grpc_port}')
        server.start()
        print(f"[INFO] Sprinkler '{self.device_id}' ouvindo na porta {self.grpc_port}\n")

        try:
            while True:
                time.sleep(86400)
        except KeyboardInterrupt:
            server.stop(0)
            print("[INFO] Servidor gRPC encerrado.\n")

    @classmethod
    def run(cls):
        """
        Processa os argumentos e inicia o servidor.
        """
        parser = argparse.ArgumentParser(description="Servidor gRPC para SprinklerActuator")
        parser.add_argument('--device_id', type=str, default='sprinkler_1', help='ID do dispositivo sprinkler')
        parser.add_argument('--grpc_port', type=int, default=50053, help='Porta para o servidor gRPC')
        parser.add_argument('--rabbitmq_host', type=str, default='localhost', help='Host do RabbitMQ')
        args = parser.parse_args()

        print(f"[INFO] Iniciando servidor para dispositivo '{args.device_id}' na porta {args.grpc_port}...")
        server_instance = cls(args.device_id, args.grpc_port, args.rabbitmq_host)
        server_instance.start()


if __name__ == '__main__':
    SprinklerServer.run()
