import grpc
import threading
from flask import Flask, render_template, request, jsonify
from json import loads
from time import sleep

# Import utilitários RabbitMQ
from source.utils.rabbitmq.connection import RabbitMQConnection
from source.utils.rabbitmq.consumer import RabbitMQConsumer
from source.utils.rabbitmq.publisher import RabbitMQPublisher

# Import dos módulos gRPC gerados
from source.devices.actuators.proto import actuators_pb2
from source.devices.actuators.proto import actuators_pb2_grpc

# Constante de limiar para o sensor de temperatura
SENSOR_THRESHOLD = 25.0

app = Flask(__name__)
app.config['JSON_SORT_KEYS'] = False

# Lista dinâmica de dispositivos (armazenada no gateway)
disp = []

# Conexão persistente para publicação
rabbitmq_connection = RabbitMQConnection()
publisher_lock = threading.Lock()

def add_or_update_device(device_data):
    """
    Adiciona ou atualiza dispositivo na lista.
    Se for 'ac' e faltar grpc_port/host, define valores padrão.
    """
    global disp
    device_id = device_data.get('id')
    if device_data.get('type') == 'ac':
        if not device_data.get('grpc_port'):
            device_data['grpc_port'] = 50052
            print(f"[GATEWAY] grpc_port não especificada para '{device_id}', usando 50052.")
        if not device_data.get('grpc_host'):
            device_data['grpc_host'] = 'localhost'
            print(f"[GATEWAY] grpc_host não especificado para '{device_id}', usando 'localhost'.")
    for device in disp:
        if device['id'] == device_id:
            device.update(device_data)
            print(f"[GATEWAY] Dispositivo atualizado: {device_data}")
            return
    disp.append(device_data)
    print(f"[GATEWAY] Novo dispositivo adicionado: {device_data}")

@app.route('/register', methods=['POST'])
def register_device():
    device_data = request.get_json()
    add_or_update_device(device_data)
    print(f"[GATEWAY] Registro recebido: {device_data}")
    return jsonify({"success": True}), 200

def custom_callback(body, exchange_name, routing_key, queue_name):
    """
    Processa mensagens recebidas e atualiza a lista de dispositivos.
    """
    try:
        message = loads(body)
        print(f"[GATEWAY] Mensagem recebida na fila '{queue_name}' (Routing Key: {routing_key}): {message}")
        add_or_update_device(message)
    except Exception as e:
        print(f"[GATEWAY ERROR] Erro ao processar mensagem da fila '{queue_name}': {e}")

def start_rabbitmq_consumers():
    """
    Inicia os consumidores do RabbitMQ.
    """
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
            "queue.sprinkler": "command.sprinkler.*",
        }
    )
    threading.Thread(target=consumer.start, args=(custom_callback,), daemon=True).start()
    print("[GATEWAY] Consumidores RabbitMQ iniciados.")

def send_grpc_command(device_info, action, parameters=None):
    """
    Envia comando via gRPC para o dispositivo e exibe logs detalhados.
    Usa 'subtype' ou, se não existir, 'type' para identificar o dispositivo.
    """
    try:
        actuator_type = device_info.get('subtype') or device_info.get('type')
        grpc_host = device_info.get('grpc_host', 'localhost')
        grpc_port = device_info.get('grpc_port')

        if not grpc_port:
            error_msg = "[GATEWAY ERROR] Porta gRPC não especificada."
            print(error_msg)
            return False, error_msg

        print(f"[GATEWAY] Estabelecendo canal gRPC para {actuator_type} '{device_info['id']}' em {grpc_host}:{grpc_port}...")
        channel = grpc.insecure_channel(f"{grpc_host}:{grpc_port}")
        stub = actuators_pb2_grpc.ActuatorServiceStub(channel)

        if actuator_type == 'lamp':
            active = (action == 'on')
            request_message = actuators_pb2.RequestLightBulb(
                type=actuator_type,
                id=device_info['id'],
                active=active
            )
            print(f"[GATEWAY] Enviando comando para lâmpada '{device_info['id']}': {'ON' if active else 'OFF'}")
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
            print(f"[GATEWAY] Enviando comando para ar-condicionado '{device_info['id']}': "
                  f"{'ON' if active else 'OFF'} com temperatura {temperature}")
            response = stub.controlAC(request_message)
        elif actuator_type == 'sprinkler':
            active = (action == 'on')
            request_message = actuators_pb2.RequestSprinkler(
                type=actuator_type,
                id=device_info['id'],
                active=active
            )
            print(f"[GATEWAY] Enviando comando para sprinkler '{device_info['id']}': {'ON' if active else 'OFF'}")
            response = stub.controlSprinkler(request_message)
        else:
            error_msg = "[GATEWAY ERROR] Tipo não suportado."
            print(error_msg)
            return False, error_msg

        if response.success:
            device_info['active'] = active
            if actuator_type == 'ac' and parameters and 'temperature' in parameters:
                device_info['temperature'] = parameters['temperature']
            print(f"[GATEWAY] Comando para '{device_info['id']}' enviado com sucesso.\n")
            return True, ""
        else:
            print(f"[GATEWAY ERROR] Erro na resposta gRPC: {response.error_message}\n")
            return False, response.error_message
    except Exception as e:
        print(f"[GATEWAY EXCEPTION] Exceção ao enviar comando para '{device_info['id']}': {e}\n")
        return False, str(e)

@app.route('/listdevice', methods=['GET'])
def listdevice():
    print("[GATEWAY] Listagem de dispositivos requisitada.")
    return render_template("listdevice.html", devices=disp)

@app.route('/device_status', methods=['GET', 'POST'])
def device_status():
    device_info = None
    if request.method == 'POST':
        device_id = request.form.get('device_id')
        device_info = next((d for d in disp if d['id'] == device_id), None)
        print(f"[GATEWAY] Status solicitado para dispositivo '{device_id}': {device_info}")
    return render_template("device_status.html", device_info=device_info)

@app.route('/device_toggle', methods=['GET', 'POST'])
def device_toggle():
    device_info = None
    if request.method == 'POST':
        device_id = request.form.get('device_id')
        new_state = request.form.get('state')
        print(f"[GATEWAY] Toggle requisitado para dispositivo '{device_id}' para o estado '{new_state}'")
        if device_id and new_state:
            device_info = next((d for d in disp if d['id'] == device_id), None)
            if device_info and (device_info.get('subtype') or device_info.get('type')) in ['lamp', 'ac', 'sprinkler']:
                success, error = send_grpc_command(device_info, 'on' if new_state == 'on' else 'off')
                if success:
                    device_info['state'] = new_state
                    print(f"[GATEWAY] Dispositivo '{device_id}' atualizado para '{new_state}'.")
                else:
                    print(f"[GATEWAY ERROR] Erro ao atualizar dispositivo '{device_id}': {error}")
    return render_template("device_toggle.html", device_info=device_info)

@app.route('/device_config', methods=['GET', 'POST'])
def device_config():
    device_info = None
    if request.method == 'POST':
        device_id = request.form.get('device_id')
        temperature = request.form.get('temperature')
        print(f"[GATEWAY] Configuração requisitada para dispositivo '{device_id}' com temperatura '{temperature}'")
        device_info = next((d for d in disp if d['id'] == device_id), None)
        if device_info and device_info.get('type') == 'ac' and temperature:
            success, error = send_grpc_command(device_info, 'config', {'temperature': float(temperature)})
            if success:
                device_info['temperature'] = temperature
                print(f"[GATEWAY] Temperatura do dispositivo '{device_id}' atualizada para {temperature}.")
            else:
                print(f"[GATEWAY ERROR] Erro ao configurar dispositivo '{device_id}': {error}")
    return render_template("device_config.html", device_info=device_info)

@app.route('/')
def home():
    print("[GATEWAY] Página inicial acessada.")
    return render_template("home.html")

def evaluate_sensor_values():
    """
    Avalia periodicamente os valores dos sensores e ajusta o ar-condicionado.
    A leitura do sensor deve conter os campos 'temperature' e 'related_device',
    que indica o id do dispositivo atuador.
    Se o sensor indicar um valor maior que SENSOR_THRESHOLD, liga o ar-condicionado
    e define a temperatura para 22; caso contrário, desliga-o.
    """
    while True:
        sensor_temp = next(
            (d for d in disp if d.get('subtype') == 'temperature' and d.get('temperature') and d.get('related_device')), None
        )
        if sensor_temp:
            related_id = sensor_temp.get('related_device')
            print(f"[GATEWAY] Sensor '{sensor_temp.get('id')}' indica que o dispositivo relacionado é '{related_id}'.")
            ac = next((d for d in disp if d['id'] == related_id), None)
        else:
            ac = None

        if sensor_temp and ac:
            sensor_value = float(sensor_temp.get('temperature'))
            if sensor_value > SENSOR_THRESHOLD:
                desired_state = 'on'
                desired_temp = 22.0
            else:
                desired_state = 'off'
                desired_temp = 22.0

            print(f"[GATEWAY] Sensor de temperatura: {sensor_value}. "
                  f"Estado desejado para ar-condicionado '{ac['id']}': {desired_state} com temperatura {desired_temp}.")

            if (ac.get('state') != desired_state) or (desired_state == 'on' and float(ac.get('temperature', 22.0)) != desired_temp):
                print(f"[GATEWAY] Atualizando ar-condicionado '{ac['id']}' para estado '{desired_state}' e temperatura {desired_temp}.")
                success, error = send_grpc_command(ac, 'config', {'temperature': desired_temp})
                if success:
                    ac['state'] = desired_state
                    ac['temperature'] = desired_temp
                    print(f"[GATEWAY] Ar-condicionado '{ac['id']}' atualizado com sucesso.")
                else:
                    print(f"[GATEWAY ERROR] Erro ao atualizar ar-condicionado '{ac['id']}': {error}")
        sleep(10)

def main():
    """
    Função principal do gateway:
      - Inicializa os consumidores RabbitMQ.
      - Inicia a thread de avaliação dos sensores.
      - Inicia o servidor Flask.
    """
    print("[GATEWAY] Inicializando consumidores RabbitMQ...")
    start_rabbitmq_consumers()

    print("[GATEWAY] Iniciando thread de avaliação de sensores...")
    sensor_thread = threading.Thread(target=evaluate_sensor_values, daemon=True)
    sensor_thread.start()

    try:
        print("[GATEWAY] Iniciando servidor Flask na porta 8080...")
        app.run(debug=True, host='0.0.0.0', port=8080)
    finally:
        rabbitmq_connection.close()
        print("[GATEWAY] Conexão RabbitMQ encerrada.")

if __name__ == "__main__":
    main()
