import grpc
from concurrent import futures
import time
import json
import argparse
import threading
from .actuators_pb2 import Response
from .actuators_pb2_grpc import ActuatorServiceServicer, add_ActuatorServiceServicer_to_server
from source.utils.rabbitmq.connection import RabbitMQConnection


class AirConditionerServer(ActuatorServiceServicer):
    """
    Classe que implementa o serviço gRPC para controle do ar-condicionado,
    gerencia a publicação periódica de status via RabbitMQ e inicia o servidor.

    O formato da mensagem publicada deve ser:
      {
          "id": "<device_id>",
          "type": "ac",
          "state": "on" or "off",
          "temperature": <valor>
      }
    """

    def __init__(self, device_id, grpc_port, rabbitmq_host='localhost'):
        self.device_id = device_id
        self.grpc_port = grpc_port
        self.rabbitmq_host = rabbitmq_host

        # Estado inicial do ar-condicionado
        self.active = False
        self.temperature = 22.0  # Temperatura padrão

        print(f"[INFO] Ar-condicionado '{self.device_id}' inicializado.")
        self.publish_status()  # Publica o status inicial

    def publish_status(self):
        """
        Publica o status atual do ar-condicionado no RabbitMQ utilizando a conexão robusta.
        """
        try:
            print(f"[INFO] Conectando ao RabbitMQ em {self.rabbitmq_host}...")
            connection = RabbitMQConnection(host=self.rabbitmq_host)
            channel = connection.channel

            # Declara o exchange 'sensors_exchange'
            channel.exchange_declare(
                exchange='sensors_exchange', exchange_type='topic', durable=True
            )

            # Formata a mensagem conforme o padrão desejado
            message = {
                "id": self.device_id,
                "type": "ac",
                "state": "on" if self.active else "off",
                "temperature": self.temperature
            }
            routing_key = f"command.air_conditioner.{self.device_id}"

            print(f"[INFO] Publicando mensagem no RabbitMQ:")
            print(f"       Exchange: 'sensors_exchange'")
            print(f"       Routing Key: '{routing_key}' (Fila associada: 'queue.ac')")
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

    def controlAC(self, request, context):
        """
        Atualiza o estado do ar-condicionado conforme a requisição gRPC e publica o status atualizado.
        Espera que o request possua os atributos 'active' e 'temperature'.
        """
        self.active = request.active
        self.temperature = request.temperature
        print(f"[INFO] Estado do ar-condicionado alterado para: {'ON' if self.active else 'OFF'} com temperatura: {self.temperature}")
        self.publish_status()
        return Response(success=True, error_message="")

    def _periodic_publish(self, interval=60):
        """
        Método interno que publica periodicamente o status do ar-condicionado.
        """
        print(f"[INFO] Iniciando publicação periódica a cada {interval} segundos...\n")
        while True:
            self.publish_status()
            time.sleep(interval)

    def start(self):
        """
        Inicializa a thread de publicação periódica e o servidor gRPC.
        """
        # Inicia a thread para publicação periódica (intervalo ajustado para 10 segundos para testes)
        periodic_thread = threading.Thread(
            target=self._periodic_publish, args=(10,), daemon=True
        )
        periodic_thread.start()

        # Cria e configura o servidor gRPC
        server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
        add_ActuatorServiceServicer_to_server(self, server)
        server.add_insecure_port(f'[::]:{self.grpc_port}')
        server.start()
        print(f"[INFO] Ar-condicionado '{self.device_id}' ouvindo na porta {self.grpc_port}\n")

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
        parser = argparse.ArgumentParser(description="Servidor gRPC para AirConditionerActuator")
        parser.add_argument('--device_id', type=str, default='ac_1', help='ID do dispositivo ar-condicionado')
        parser.add_argument('--grpc_port', type=int, default=50052, help='Porta para o servidor gRPC')
        parser.add_argument('--rabbitmq_host', type=str, default='localhost', help='Host do RabbitMQ')
        args = parser.parse_args()

        print(f"[INFO] Iniciando servidor para dispositivo '{args.device_id}' na porta {args.grpc_port}...")
        server_instance = cls(args.device_id, args.grpc_port, args.rabbitmq_host)
        server_instance.start()


if __name__ == '__main__':
    AirConditionerServer.run()
