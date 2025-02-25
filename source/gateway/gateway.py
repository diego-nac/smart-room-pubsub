import grpc
import threading
from flask import Flask, render_template, request, jsonify
from json import loads
from time import sleep

# Import utilitários RabbitMQ
from configs.envs import DEVICES_DELAY, GRPC_AIR_PORT, GRPC_DOOR_PORT
from source.utils.rabbitmq.connection import RabbitMQConnection
from source.utils.rabbitmq.consumer import RabbitMQConsumer
from source.utils.rabbitmq.publisher import RabbitMQPublisher

# Import dos módulos gRPC gerados
from source.devices.actuators.proto import actuators_pb2
from source.devices.actuators.proto import actuators_pb2_grpc

# Constante de limiar para o sensor de temperatura
# No início do gateway.py (após SENSOR_THRESHOLD)
HIGH_TEMP_THRESHOLD = 25.0  # Limiar superior para ligar o ar
LOW_TEMP_THRESHOLD = 12.0   # Limiar inferior para desligar o ar
LUMINOSITY_THRESHOLD_LOW = 300.0  # Limiar para ligar a lâmpada
LUMINOSITY_THRESHOLD_HIGH = 700.0 # Limiar para desligar a lâmpada

app = Flask(__name__)
app.config['JSON_SORT_KEYS'] = False

# Lista dinâmica de dispositivos (armazenada no gateway)
disp = []

# Conexão persistente para publicação
rabbitmq_connection = RabbitMQConnection()
publisher_lock = threading.Lock()

def add_or_update_device(device_data):
    global disp
    device_id = device_data.get('id')
    if device_data.get('type') == 'ac':
        if not device_data.get('grpc_port'):
            device_data['grpc_port'] = GRPC_AIR_PORT
            print(f"[GATEWAY] grpc_port não especificada para '{device_id}', usando {GRPC_AIR_PORT}.")
        if not device_data.get('grpc_host'):
            device_data['grpc_host'] = 'localhost'
            print(f"[GATEWAY] grpc_host não especificado para '{device_id}', usando 'localhost'.")
    elif device_data.get('type') == 'door':
        if not device_data.get('grpc_port'):
            device_data['grpc_port'] = GRPC_DOOR_PORT  # Agora será 50053
            print(f"[GATEWAY] grpc_port não especificada para '{device_id}', usando {GRPC_DOOR_PORT}.")
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
        elif actuator_type == 'door':
            desired_open = True if action == 'open' else False
            request_message = actuators_pb2.RequestDoor(
                type=actuator_type,
                id=device_info['id'],
                is_open=desired_open
            )
            print(f"[GATEWAY] Enviando comando para porta '{device_info['id']}': {'open' if desired_open else 'closed'}")
            response = stub.controlDoor(request_message)
        else:
            error_msg = "[GATEWAY ERROR] Tipo não suportado."
            print(error_msg)
            return False, error_msg

        if response.success:
            device_info['state'] = 'open' if (actuator_type == 'door' and action == 'open') else \
                                   ('closed' if actuator_type == 'door' else action)
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
    message = None
    message_type = None
    
    if request.method == 'POST':
        device_id = request.form.get('device_id')
        new_state = request.form.get('state')
        
        print(f"[GATEWAY] Toggle requisitado para dispositivo '{device_id}' para o estado '{new_state}'")
        
        if device_id and new_state:
            device_info = next((d for d in disp if d['id'] == device_id), None)
            
            if device_info:
                device_type = device_info.get('subtype') or device_info.get('type')
                
                if device_type in ['lamp', 'ac', 'sprinkler']:
                    success, error = send_grpc_command(device_info, new_state)
                    
                    if success:
                        device_info['state'] = new_state
                        message = f"Dispositivo '{device_id}' atualizado para '{new_state}'."
                        message_type = "success"
                    else:
                        message = f"Erro ao atualizar dispositivo '{device_id}': {error}"
                        message_type = "error"
                else:
                    message = f"Tipo de dispositivo '{device_type}' não suportado."
                    message_type = "error"
            else:
                message = f"Dispositivo '{device_id}' não encontrado."
                message_type = "error"
    
    return render_template(
        "device_toggle.html",
        device_info=device_info,
        message=message,
        message_type=message_type
    )

@app.route('/device_config', methods=['GET', 'POST'])
def device_config():
    device_info = None
    if request.method == 'POST':
        device_id = request.form.get('device_id')
        # Para AC, o formulário envia 'temperature'
        temperature = request.form.get('temperature')
        # Para door, o formulário envia 'status'
        status = request.form.get('status')
        
        print(f"[GATEWAY] Configuração requisitada para dispositivo '{device_id}' - "
              f"temperatura: '{temperature}' / status: '{status}'")
        
        device_info = next((d for d in disp if d['id'] == device_id), None)
        if device_info:
            if device_info.get('type') == 'ac' and temperature:
                success, error = send_grpc_command(device_info, 'config', {'temperature': float(temperature)})
                if success:
                    device_info['temperature'] = temperature
                    print(f"[GATEWAY] Temperatura do dispositivo '{device_id}' atualizada para {temperature}.")
                else:
                    print(f"[GATEWAY ERROR] Erro ao configurar dispositivo '{device_id}': {error}")
            elif device_info.get('type') == 'door' and status:
                # Para a porta, o campo 'status' deve ser 'open' ou 'closed'
                if status.lower() in ['open', 'closed']:
                    success, error = send_grpc_command(device_info, status.lower())
                    if success:
                        device_info['state'] = status.lower()
                        print(f"[GATEWAY] Status da porta '{device_id}' atualizado para {status.lower()}.")
                    else:
                        print(f"[GATEWAY ERROR] Erro ao configurar dispositivo '{device_id}': {error}")
                else:
                    print(f"[GATEWAY ERROR] Valor inválido para status da porta: {status}")
            else:
                print(f"[GATEWAY] Dispositivo '{device_id}' não suporta alteração de configuração via este formulário.")
    return render_template("device_config.html", device_info=device_info)


@app.route('/')
def home():
    print("[GATEWAY] Página inicial acessada.")
    return render_template("home.html")

def evaluate_sensor_values():
    """
    Avalia periodicamente os valores dos sensores e ajusta os atuadores.
    """
    while True:
        for device in disp:
            # Controle do Ar-Condicionado (já existente)...
            if device.get('subtype') == 'temperature' and 'temperature' in device and 'related_device' in device:
                sensor_temp = device
                related_id = sensor_temp['related_device']
                ac = next((d for d in disp if d['id'] == related_id), None)
                if ac:
                    temp_value = float(sensor_temp['temperature'])
                    if temp_value > HIGH_TEMP_THRESHOLD:
                        desired_state = 'on'
                        desired_temp = 22.0
                    elif temp_value < LOW_TEMP_THRESHOLD:
                        desired_state = 'off'
                        desired_temp = 22.0
                    else:
                        desired_state = 'off'
                        desired_temp = 22.0

                    if (ac.get('state') != desired_state) or (desired_state == 'on' and float(ac.get('temperature', 22.0)) != desired_temp):
                        success, error = send_grpc_command(ac, 'config', {'temperature': desired_temp})
                        if success:
                            ac['state'] = desired_state
                            ac['temperature'] = desired_temp

            # Controle da Lâmpada baseado em luminosidade (já existente)...
            if device.get('subtype') == 'luminosity' and 'luminosity' in device and 'related_device' in device:
                sensor_lum = device
                related_id = sensor_lum['related_device']
                lamp = next((d for d in disp if d['id'] == related_id), None)
                if lamp:
                    lum_value = float(sensor_lum['luminosity'])
                    if lum_value < LUMINOSITY_THRESHOLD_LOW:
                        desired_state = 'on'
                    elif lum_value > LUMINOSITY_THRESHOLD_HIGH:
                        desired_state = 'off'
                    else:
                        desired_state = lamp.get('state', 'off')
                    if desired_state != lamp.get('state'):
                        success, error = send_grpc_command(lamp, desired_state)
                        if success:
                            lamp['state'] = desired_state
            if device.get('subtype') == 'presence' and 'related_device' in device:
                sensor_presence = device
                related_id = sensor_presence['related_device']
                # Se o sensor indicar "door", remapeia para "door_actuator"
                door = next((d for d in disp if d['id'] == related_id), None)
                if door:
                    # Se o sensor estiver "on", a porta deve ficar open; se "off", closed.
                    desired_state = 'open' if sensor_presence.get('state') == 'on' else 'closed'
                    if door.get('state') != desired_state:
                        success, error = send_grpc_command(door, desired_state)
                        if success:
                            door['state'] = desired_state



        sleep(DEVICES_DELAY)


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
