from flask import Flask, render_template, request
from bd import disp

app = Flask(__name__)
app.config['JSON_SORT_KEYS'] = False

@app.route('/listdevice', methods = ['GET'])
def listdevice():
    return render_template("listdevice.html", devices=disp)

@app.route('/device_status', methods=['GET', 'POST'])
def device_status():
    device_info = None
    if request.method == 'POST':
        device_id = request.form.get('device_id')
        # Procura o dispositivo pelo ID
        device_info = next((device for device in disp if device['id'] == device_id), None)
    return render_template("device_status.html", device_info=device_info)


@app.route('/device_toggle', methods=['GET', 'POST'])
def device_toggle():
    device_info = None
    if request.method == 'POST':
        device_id = request.form.get('device_id')  # Pega o ID do dispositivo do formulário
        new_state = request.form.get('state')  # Pega o novo estado (on ou off)

        # Procura o dispositivo pelo ID
        device_info = next((device for device in disp if device['id'] == device_id), None)

        if device_info:
            # Altera o estado do dispositivo
            device_info['state'] = new_state

    return render_template("device_toggle.html", device_info=device_info)


@app.route('/device_config', methods=['GET', 'POST'])
def device_config():
    device_info = None
    if request.method == 'POST':
        device_id = request.form.get('device_id')  # Pega o ID do dispositivo do formulário
        # Verifica se a configuração de brilho ou temperatura foi fornecida
        brightness = request.form.get('brightness')
        temperature = request.form.get('temperature')

        # Procura o dispositivo pelo ID
        device_info = next((device for device in disp if device['id'] == device_id), None)

        if device_info:
            # Atualiza o brilho ou a temperatura, dependendo do tipo do dispositivo
            if brightness and device_info['type'] == 'lamp':
                device_info['brightness'] = int(brightness)
            if temperature and device_info['type'] == 'ac':
                device_info['temperature'] = int(temperature)

    return render_template("device_config.html", device_info=device_info)


@app.route('/')
def home():
    return render_template("home.html")  # Página inicial com links para as funcionalidades


if __name__ == "__main__":
    app.run(debug=True)