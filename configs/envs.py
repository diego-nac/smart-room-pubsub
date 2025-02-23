from pathlib import Path

CURRENT_DIR = Path(__file__).resolve().parent.parent  
RABBITMQ_HOST = "localhost"
RABBITMQ_PORT = 5672
RABBITMQ_USER = "guest"
RABBITMQ_PASSWORD = "guest"

GRPC_LAMP_PORT = 50051
GRPC_SPLINKER_PORT = 50052

SENSOR_DELAY = 2
DEVICES_DELAY = 1