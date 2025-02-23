import grpc
from concurrent import futures
import time
import pika
import json
import argparse
from actuators_pb2 import Response
from actuators_pb2_grpc import ActuatorServiceServicer, add_ActuatorServiceServicer_to_server

class AirConditionerActuator(ActuatorServiceServicer):
    def __init__(self, device_id, grpc_port, rabbitmq_host='localhost'):
        self.device_id = device_id
        self.grpc_port = grpc_port
        self.active = False
        self.temperature = 22.0  # Temperatura padrão
        self.rabbitmq_host = rabbitmq_host
        self.publish_status()  # Registro inicial

    def publish_status(self):
        connection = pika.BlockingConnection(pika.ConnectionParameters(self.rabbitmq_host))
        channel = connection.channel()
        channel.exchange_declare(exchange='sensors_exchange', exchange_type='topic', durable=True)
        
        message = {
            'id': self.device_id,
            'type': 'actuator',          # Campo type do HTML
            'subtype': 'air-conditioner',           # Novo campo subtype
            'state': 'on' if self.active else 'off',  # Estado traduzido
            'brightness': 100 if self.active else 0,  # Simula brilho
            'grpc_host': 'localhost',
            'grpc_port': self.grpc_port,
            'temperature': self.temperature,         # Placeholder
            'luminosity': None,          # Placeholder
            'related_device': None       # Placeholder
        }
        
        routing_key = f"command.air_conditioner.{self.device_id}"
        channel.basic_publish(
            exchange='sensors_exchange',
            routing_key=routing_key,
            body=json.dumps(message)
        )
        connection.close()

    def controlAC(self, request, context):
        self.active = request.active
        self.temperature = request.temperature
        self.publish_status()  # Atualiza estado no RabbitMQ
        return Response(success=True, error_message="")

def serve(device_id='ac_1', grpc_port=50052):
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    add_ActuatorServiceServicer_to_server(AirConditionerActuator(device_id, grpc_port), server)
    server.add_insecure_port(f'[::]:{grpc_port}')
    server.start()
    print(f"Ar-Condicionado {device_id} ouvindo em {grpc_port}")
    try:
        while True:
            time.sleep(86400)
    except KeyboardInterrupt:
        server.stop(0)

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--device_id', type=str, default='ac_1')
    parser.add_argument('--grpc_port', type=int, default=50052)
    args = parser.parse_args()
    serve(args.device_id, args.grpc_port)