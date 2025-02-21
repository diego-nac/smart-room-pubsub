from flask import Flask, render_template, request
from source.utils.rabbitmq.connection import RabbitMQConnection
from source.utils.rabbitmq.consumer import RabbitMQConsumer
from source.utils.rabbitmq.publisher import RabbitMQPublisher
from json import loads
from time import sleep
import threading

app = Flask(__name__)
app.config['JSON_SORT_KEYS'] = False

# Lista dinâmica de dispositivos coletada exclusivamente do RabbitMQ
disp = []

# Conexão persistente para publicação
rabbitmq_connection = RabbitMQConnection()
publisher_lock = threading.Lock()

def add_or_update_device(device_data):
    """Adiciona um novo dispositivo ou atualiza se já existir."""
    global disp
    device_id = device_data.get('id')
    for device in disp:
        if device['id'] == device_id:
            device.update(device_data)
            print(f"Dispositivo atualizado: {device_data}")
            return
    disp.append(device_data)
    print(f"Novo dispositivo adicionado: {device_data}")

def custom_callback(body, exchange_name, routing_key, queue_name):
    """Callback para processar mensagens e atualizar o disp."""
    try:
        message = loads(body)
        print(f"Mensagem recebida ({queue_name}): {message}")
        add_or_update_device(message)
    except Exception as e:
        print(f"Erro ao processar mensagem: {e}")

def start_rabbitmq_consumers():
    """Inicia o consumidor RabbitMQ utilizando a classe RabbitMQConsumer."""
    consumer = RabbitMQConsumer(
        connection=rabbitmq_connection,
        exchange_name="sensors_exchange",
        queues={
            "queue.temperature": "sensor.temperature",
            "queue.luminosity": "sensor.luminosity",
            "queue.presence": "sensor.presence",
            "queue.lamp": "command.lamp.*",
            "queue.air_conditioner": "command.air_conditioner.*",
            "queue.door": "command.door.*",
        }
    )
    threading.Thread(target=consumer.start, args=(custom_callback,), daemon=True).start()

def publish_command(device_id, action, parameters=None):
    """Publica um comando no RabbitMQ para alterar o estado do dispositivo de forma thread-safe."""
    try:
        with publisher_lock:
            routing_key = f"command.{device_id}"
            publisher = RabbitMQPublisher(
                connection=rabbitmq_connection,
                exchange_name="commands_exchange",
                queue_name=f"queue.{device_id}",
                routing_key=routing_key
            )
            message = {"device_id": device_id, "action": action}
            if parameters:
                message["parameters"] = parameters
            publisher.publish_message(message)
            print(f"[Publicação] Comando enviado para {device_id}: {message}")
    except Exception as e:
        print(f"[Erro na Publicação] Falha ao enviar comando: {e}")

# Rotas unificadas (sem subdivisão entre API e visualização)
@app.route('/listdevice', methods=['GET'])
def listdevice():
    return render_template("listdevice.html", devices=disp)

@app.route('/device_status', methods=['GET', 'POST'])
def device_status():
    device_info = None
    if request.method == 'POST':
        device_id = request.form.get('device_id')
        device_info = next((device for device in disp if device['id'] == device_id), None)
    return render_template("device_status.html", device_info=device_info)

@app.route('/device_toggle', methods=['GET', 'POST'])
def device_toggle():
    device_info = None
    if request.method == 'POST':
        device_id = request.form.get('device_id')
        new_state = request.form.get('state')
        if device_id and new_state:
            publish_command(device_id, new_state)
            device_info = next((device for device in disp if device['id'] == device_id), None)
    return render_template("device_toggle.html", device_info=device_info)

@app.route('/device_config', methods=['GET', 'POST'])
def device_config():
    device_info = None
    if request.method == 'POST':
        device_id = request.form.get('device_id')
        brightness = request.form.get('brightness')
        temperature = request.form.get('temperature')
        parameters = {}
        if brightness:
            parameters['brightness'] = brightness
        if temperature:
            parameters['temperature'] = temperature
        if device_id:
            publish_command(device_id, 'config', parameters)
            device_info = next((device for device in disp if device['id'] == device_id), None)
    return render_template("device_config.html", device_info=device_info)

@app.route('/')
def home():
    return render_template("home.html")

if __name__ == "__main__":
    start_rabbitmq_consumers()
    try:
        app.run(debug=True, host='0.0.0.0', port=8080)
    finally:
        rabbitmq_connection.close()