from pathlib import Path

CURRENT_DIR = Path(__file__).resolve().parent.parent  
RABBITMQ_HOST = "localhost"
RABBITMQ_PORT = 5672
RABBITMQ_USER = "guest"
RABBITMQ_PASSWORD = "guest"

SENSOR_DELAY = 1