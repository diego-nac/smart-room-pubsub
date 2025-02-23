from flask import Flask, render_template, request, jsonify
import grpc
import threading
from json import loads
from time import sleep

# Import das classes utilitárias do RabbitMQ
from source.utils.rabbitmq.connection import RabbitMQConnection
from source.utils.rabbitmq.consumer import RabbitMQConsumer
from source.utils.rabbitmq.publisher import RabbitMQPublisher

from source.devices.actuators import actuators_pb2
from source.devices.actuators import actuators_pb2_grpc

app = Flask(__name__)
app.config['JSON_SORT_KEYS'] = False

# Lista dinâmica de dispositivos coletada exclusivamente do RabbitMQ
disp = []

# Conexão persistente para publicação
rabbitmq_connection = RabbitMQConnection()
publisher_lock = threading.Lock()

@app.route('/register', methods=['POST'])
def register_device():
    device_data = request.get_json()
    add_or_update_device(device_data)
    return jsonify({"success": True}), 200

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
            "queue.splinker": "command.sprinkler.*",
        }
    )
    threading.Thread(target=consumer.start, args=(custom_callback,), daemon=True).start()

def send_grpc_command(device_info, action, parameters=None):
    try:
        actuator_type = device_info.get('subtype')  # Utiliza 'subtype'
        grpc_host = device_info.get('grpc_host', 'localhost')
        grpc_port = device_info.get('grpc_port')
        
        if not grpc_port:
            return False, "Porta gRPC não especificada"
        
        channel = grpc.insecure_channel(f"{grpc_host}:{grpc_port}")
        stub = actuators_pb2_grpc.ActuatorServiceStub(channel)
        
        if actuator_type == 'lamp':
            active = (action == 'on')
            request_message = actuators_pb2.RequestLightBulb(
                type=actuator_type,
                id=device_info['id'],
                active=active
            )
            response = stub.controlLightBulb(request_message)
        elif actuator_type == 'ac':
            active = (action in ['on', 'config'])
            temperature = parameters.get('temperature', device_info.get('temperature', 22.0)) if parameters else 22.0
            request_message = actuators_pb2.RequestAC(
                type=actuator_type,
                id=device_info['id'],
                temperature=float(temperature),
                active=active
            )
            response = stub.controlAC(request_message)
        elif actuator_type == 'sprinkler':
            active = (action == 'on')
            request_message = actuators_pb2.RequestSprinkler(
                type=actuator_type,
                id=device_info['id'],
                active=active
            )
            response = stub.controlSprinkler(request_message)
        else:
            return False, "Tipo não suportado"
        
        if response.success:
            device_info['active'] = active
            if actuator_type == 'ac' and parameters and 'temperature' in parameters:
                device_info['temperature'] = parameters['temperature']
            return True, ""
        else:
            return False, response.error_message
    except Exception as e:
        return False, str(e)

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
            device_info = next((d for d in disp if d['id'] == device_id), None)
            if device_info and device_info.get('subtype') in ['lamp', 'ac', 'sprinkler']:
                success, error = send_grpc_command(device_info, 'on' if new_state == 'on' else 'off')
                if success:
                    device_info['state'] = new_state
    return render_template("device_toggle.html", device_info=device_info)

@app.route('/device_config', methods=['GET', 'POST'])
def device_config():
    device_info = None
    if request.method == 'POST':
        device_id = request.form.get('device_id')
        temperature = request.form.get('temperature')
        device_info = next((d for d in disp if d['id'] == device_id), None)
        if device_info and device_info.get('type') == 'ac' and temperature:
            success, error = send_grpc_command(device_info, 'config', {'temperature': float(temperature)})
            if success:
                device_info['temperature'] = temperature
    return render_template("device_config.html", device_info=device_info)

@app.route('/')
def home():
    return render_template("home.html")

def evaluate_sensor_values():
    """
    Avalia periodicamente os valores dos sensores e aciona o sprinkler de acordo.
    Supondo que os sensores enviem um campo 'value' com a leitura.
    """
    LIMIAR_TEMPERATURA = 18.0  # Exemplo de limiar; ajuste conforme necessário

    while True:
        # Procura pelo sensor de temperatura e pelo sprinkler
        sensor_temp = next((d for d in disp if d.get('subtype') == 'temperature' and 'value' in d), None)
        sprinkler = next((d for d in disp if d.get('subtype') == 'sprinkler'), None)
        
        if sensor_temp and sprinkler:
            temperature = sensor_temp.get('value')
            desired_state = 'on' if temperature < LIMIAR_TEMPERATURA else 'off'
            
            if sprinkler.get('state') != desired_state:
                print(f"Detectado sensor de temperatura = {temperature}. Atualizando sprinkler para {desired_state}.")
                success, error = send_grpc_command(sprinkler, desired_state)
                if success:
                    sprinkler['state'] = desired_state
                    print("Sprinkler atualizado com sucesso.")
                else:
                    print("Erro ao atualizar sprinkler:", error)
        sleep(10)

def main():
    """
    Função principal que consolida a execução do gateway:
    - Inicializa os consumidores RabbitMQ.
    - Inicia a thread para avaliação dos sensores.
    - Inicia o servidor Flask.
    """
    start_rabbitmq_consumers()
    sensor_thread = threading.Thread(target=evaluate_sensor_values, daemon=True)
    sensor_thread.start()
    try:
        app.run(debug=True, host='0.0.0.0', port=8080)
    finally:
        rabbitmq_connection.close()

if __name__ == "__main__":
    main()
