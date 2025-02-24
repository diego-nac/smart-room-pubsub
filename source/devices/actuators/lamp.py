import grpc
from concurrent import futures
import time
import json
import argparse
import threading
from .proto.actuators_pb2 import Response
from .proto.actuators_pb2_grpc import ActuatorServiceServicer, add_ActuatorServiceServicer_to_server
from source.utils.rabbitmq.connection import RabbitMQConnection
from configs.envs import RABBITMQ_HOST, GRPC_LAMP_PORT, DEVICES_DELAY


class LightBulbServer(ActuatorServiceServicer):
    """
    Classe que implementa o serviço gRPC para controle da lâmpada,
    gerencia a publicação periódica de status via RabbitMQ e inicia o servidor.
    
    A lâmpada possui os seguintes atributos:
      - active: indica se a lâmpada está ligada (True) ou desligada (False)
      - brightness: nível de brilho da lâmpada (valor inteiro, ex: 0 a 100)
      - luminosity: valor que pode representar a luminosidade ambiente (opcional)
    """

    def __init__(self, device_id, grpc_port = GRPC_LAMP_PORT, rabbitmq_host=RABBITMQ_HOST):
        self.device_id = device_id
        self.grpc_port = grpc_port
        self.rabbitmq_host = rabbitmq_host

        # Estado inicial da lâmpada
        self.active = False
        self.brightness = 100    # brilho padrão quando ligada

        print(f"[INFO] Lâmpada '{self.device_id}' inicializada.")
        self.publish_status()  # Publica o status inicial

    def publish_status(self):
        """
        Publica o status atual da lâmpada no RabbitMQ utilizando a conexão robusta.
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
                'subtype': 'lamp',
                'state': 'on' if self.active else 'off',
                'brightness': self.brightness if self.active else 0,
                'grpc_host': 'localhost',
                'grpc_port': self.grpc_port,
                'temperature': None,         # Placeholder
                'luminosity': self.brightness if self.active else 0,
                'related_device': None       # Placeholder
            }
            routing_key = f"command.lamp.{self.device_id}"

            # Supondo que o gateway esteja inscrito em filas que recebam mensagens
            # com routing key "command.lamp.*", a mensagem será encaminhada para a
            # fila associada, por exemplo, "queue.lamp".
            print(f"[INFO] Publicando mensagem no RabbitMQ:")
            print(f"       Exchange: 'sensors_exchange'")
            print(f"       Routing Key: '{routing_key}' (Fila associada: 'queue.lamp')")
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

    def controlLightBulb(self, request, context):
        """
        Atualiza o estado da lâmpada conforme a requisição gRPC e publica o status atualizado.
        
        Se o request possuir um atributo 'brightness', atualiza o nível de brilho.
        """
        self.active = request.active
        # Atualiza brilho se presente no request; caso contrário, mantém o valor atual.
        if hasattr(request, 'brightness'):
            self.brightness = request.brightness
        else:
            # Se a lâmpada for ligada e nenhum valor de brilho foi enviado, mantém o padrão.
            self.brightness = 100 if self.active else 0

        print(f"[INFO] Estado da lâmpada alterado para: {'ON' if self.active else 'OFF'} "
              f"com brilho: {self.brightness}")
        self.publish_status()
        return Response(success=True, error_message="")

    def _periodic_publish(self, interval=DEVICES_DELAY):
        """
        Método interno que publica periodicamente o status da lâmpada.
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
            target=self._periodic_publish, args=(DEVICES_DELAY,), daemon=True
        )
        periodic_thread.start()

        # Cria e configura o servidor gRPC
        server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
        add_ActuatorServiceServicer_to_server(self, server)
        server.add_insecure_port(f'[::]:{self.grpc_port}')
        server.start()
        print(f"[INFO] Lâmpada '{self.device_id}' ouvindo na porta {self.grpc_port}\n")

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
        parser = argparse.ArgumentParser(description="Servidor gRPC para LightBulbActuator")
        parser.add_argument('--device_id', type=str, default='lamp_1', help='ID do dispositivo lâmpada')
        parser.add_argument('--grpc_port', type=int, default=50051, help='Porta para o servidor gRPC')
        parser.add_argument('--rabbitmq_host', type=str, default='localhost', help='Host do RabbitMQ')
        args = parser.parse_args()

        print(f"[INFO] Iniciando servidor para dispositivo '{args.device_id}' na porta {args.grpc_port}...")
        server_instance = cls(args.device_id, args.grpc_port, args.rabbitmq_host)
        server_instance.start()


if __name__ == '__main__':
    LightBulbServer.run()
