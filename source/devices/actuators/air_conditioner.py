import grpc
from concurrent import futures
import time
import json
import argparse
import threading
from .proto.actuators_pb2 import Response
from .proto.actuators_pb2_grpc import ActuatorServiceServicer, add_ActuatorServiceServicer_to_server
from source.utils.rabbitmq.connection import RabbitMQConnection

class AirConditionerServer(ActuatorServiceServicer):
    """
    Implementa o serviço gRPC para controle do ar-condicionado.
    Publica seu status periodicamente via RabbitMQ com o seguinte formato:
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

        # Estado inicial
        self.active = False
        self.temperature = 22.0

        print(f"[DEVICE INFO] Ar-condicionado '{self.device_id}' inicializado com state=OFF e temperatura=22.0.")
        self.publish_status()

    def publish_status(self):
        """
        Publica o status atual no RabbitMQ.
        """
        try:
            print(f"[DEVICE] Tentando estabelecer conexão com RabbitMQ em {self.rabbitmq_host}...")
            connection = RabbitMQConnection(host=self.rabbitmq_host)
            print("[DEVICE] Conexão estabelecida com sucesso.")
            channel = connection.channel
            print("[DEVICE] Canal obtido com sucesso.")

            print("[DEVICE] Declarando exchange 'sensors_exchange' (tipo: topic, durável)...")
            channel.exchange_declare(
                exchange='sensors_exchange',
                exchange_type='topic',
                durable=True
            )
            print("[DEVICE] Exchange declarado com sucesso.")

            message = {
                "id": self.device_id,
                "type": "actuator",  # Tipo como "actuator"
                "subtype": "ac",    # Subtipo como "ac"
                "state": "on" if self.active else "off",
                "temperature": self.temperature,
                "grpc_host": "localhost",  # Adiciona o host gRPC
                "grpc_port": self.grpc_port  # Adiciona a porta gRPC
            }
            routing_key = f"command.air_conditioner.{self.device_id}"

            print(f"[DEVICE] Publicando mensagem:")
            print(f"         Exchange: 'sensors_exchange'")
            print(f"         Routing Key: '{routing_key}' (Fila associada: 'queue.ac')")
            print(f"         Mensagem: {json.dumps(message, indent=2)}")
            channel.basic_publish(
                exchange='sensors_exchange',
                routing_key=routing_key,
                body=json.dumps(message)
            )
            print("[DEVICE] Mensagem enviada. Fechando conexão com RabbitMQ...")
            connection.close()
            print("[DEVICE SUCCESS] Status publicado e conexão fechada.\n")
        except Exception as e:
            print(f"[DEVICE ERROR] Erro ao publicar status: {e}\n")

    def controlAC(self, request, context):
        """
        Atualiza o estado do ar-condicionado conforme a requisição gRPC.
        """
        print("[DEVICE DEBUG] Requisição gRPC recebida:")
        print(f"         active: {request.active}")
        print(f"         temperature: {request.temperature}")

        self.active = request.active
        self.temperature = request.temperature
        print(f"[DEVICE INFO] Estado atualizado para: {'ON' if self.active else 'OFF'} com temperatura: {self.temperature}")
        self.publish_status()
        print("[DEVICE INFO] Retornando resposta gRPC.\n")
        return Response(success=True, error_message="")

    def _periodic_publish(self, interval=60):
        """
        Publica periodicamente o status.
        """
        print(f"[DEVICE INFO] Iniciando loop de publicação periódica a cada {interval} segundos...\n")
        while True:
            print("[DEVICE INFO] Publicação periódica acionada.")
            self.publish_status()
            print(f"[DEVICE INFO] Aguardando {interval} segundos para a próxima publicação...\n")
            time.sleep(interval)

    def start(self):
        """
        Inicializa a thread de publicação periódica e o servidor gRPC.
        """
        print("[DEVICE INFO] Inicializando thread de publicação periódica...")
        periodic_thread = threading.Thread(target=self._periodic_publish, args=(10,), daemon=True)
        periodic_thread.start()
        print("[DEVICE INFO] Thread de publicação periódica iniciada.")

        print("[DEVICE INFO] Criando servidor gRPC...")
        server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
        add_ActuatorServiceServicer_to_server(self, server)
        server.add_insecure_port(f'[::]:{self.grpc_port}')
        server.start()
        print(f"[DEVICE INFO] Ar-condicionado '{self.device_id}' está ouvindo na porta {self.grpc_port}\n")

        try:
            print("[DEVICE INFO] Listener gRPC ativo, aguardando chamadas...")
            server.wait_for_termination()
        except KeyboardInterrupt:
            print("[DEVICE INFO] Interrupção detectada. Encerrando servidor gRPC...")
            server.stop(0)
            print("[DEVICE INFO] Servidor gRPC encerrado.\n")

    @classmethod
    def run(cls):
        """
        Processa os argumentos de linha de comando e inicia o servidor.
        """
        parser = argparse.ArgumentParser(description="Servidor gRPC para AirConditionerActuator")
        parser.add_argument('--device_id', type=str, default='ac_1', help='ID do ar-condicionado')
        parser.add_argument('--grpc_port', type=int, default=50052, help='Porta para o servidor gRPC')
        parser.add_argument('--rabbitmq_host', type=str, default='localhost', help='Host do RabbitMQ')
        args = parser.parse_args()

        print(f"[DEVICE INFO] Iniciando servidor para '{args.device_id}' na porta {args.grpc_port}...")
        server_instance = cls(args.device_id, args.grpc_port, args.rabbitmq_host)
        server_instance.start()


if __name__ == '__main__':
    AirConditionerServer.run()
