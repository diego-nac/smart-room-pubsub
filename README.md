# **Smart Room - Sistema Distribuído com RabbitMQ e gRPC**

📌 **Repositório destinado ao segundo trabalho da disciplina de Sistemas Distribuídos (UFC).**

Este projeto simula um **ambiente inteligente** com sensores, atuadores e um  **Gateway central** , utilizando **RabbitMQ para comunicação assíncrona** e  **gRPC para controle remoto dos dispositivos** .

---

## 📖 **Descrição do Projeto**

O sistema é composto por três principais componentes:

1. **Sensores** → Publicam dados no **RabbitMQ** periodicamente.
2. **Gateway** → Atua como  **orquestrador** , consumindo dados dos sensores e enviando comandos aos atuadores via  **gRPC** .
3. **Atuadores** → Recebem comandos do **Gateway** para modificar o ambiente (exemplo: ligar lâmpadas, abrir portas).
4. **Cliente** → Interface que interage com o **Gateway** via **API REST** para monitoramento e controle do ambiente.

🔗 **Tecnologias Utilizadas:**

✅ **Python** → Backend do sistema

✅ **RabbitMQ** → Comunicação assíncrona (sensores → gateway)

✅ **gRPC** → Comunicação remota (gateway → atuadores)

✅ **Flask** → API REST para interação com o usuário

✅ **HTML** → Interface Gráfica

✅ **Multicast UDP (opcional)** → Descoberta dinâmica do RabbitMQ

---

## ⚙ **Arquitetura do Sistema**

📡 **Sensores (Publisher) → RabbitMQ → Gateway (Subscriber)**

🖥 **Gateway (Client) → gRPC → Atuadores (Server)**

🌍 **Cliente (Web/Desktop) → API REST → Gateway**

Cada sensor tem um atuador correspondente:

* **Sensor de Temperatura** 🔥 ➝ **Ar-condicionado** ❄
* **Sensor de Luminosidade** 💡 ➝ **Lâmpada Inteligente** 💡
* **Sensor de Presença** 🚶‍♂️ ➝ **Porta Inteligente** 🚪

---

## 📂 **Estrutura do Projeto**

```
smart-room-pubsub/
│── source/
│   ├── gateway/                  # Gateway Inteligente
│   │   ├── gateway.py             # Lógica principal
│   │   ├── grpc_client.py         # Comunicação com atuadores via gRPC
│   │   ├── rabbitmq_subscriber.py # Recebe dados dos sensores via RabbitMQ
│   │   ├── api/                   # API REST para interface cliente
│   │   ├── config.py              # Configurações gerais
│
│   ├── sensors/                   # Sensores publicando no RabbitMQ
│   │   ├── temperature_sensor.py  # Sensor de temperatura
│   │   ├── light_sensor.py        # Sensor de luminosidade
│   │   ├── motion_sensor.py       # Sensor de presença
│
│   ├── actuators/                 # Atuadores controlados via gRPC
│   │   ├── lamp.py                # Lâmpada inteligente
│   │   ├── air_conditioner.py     # Ar-condicionado
│   │   ├── smart_door.py          # Porta inteligente
│   │   ├── grpc_server.py         # Servidor gRPC dos atuadores
│   ├── client/                    # Aplicação Cliente (Web/Desktop)
│── requirements.txt                # Dependências do projeto
│── README.md                       # Documentação principal
```

---

## 🚀 **Instalação e Execução**

### **Instalar Dependências**

```bash
pip install -r requirements.txt
```

### **Iniciar os Serviços**

✅ **Iniciar o Gateway**

```bash
python src/gateway/gateway.py
```

✅ **Rodar Sensores**

```bash
python src/sensors/temperature_sensor.py
python src/sensors/light_sensor.py
python src/sensors/motion_sensor.py
```

✅ **Rodar Atuadores**

```bash
python src/actuators/grpc_server.py
```

✅ **Rodar Cliente**

```bash
python src/client/client.py
```

---

## 🛠 **Divisão das Tarefas**

**📌 Pessoa 1 - Atuadores <-> Gateway**
✔ Implementar os atuadores (lâmpada, ar-condicionado, porta).

✔ Receber comandos via gRPC e atualizar o estado no Gateway.

✔ Simular controle dos dispositivos.

**📌 Pessoa 2 - Sensores <-> Gateway**

✔ Implementar sensores (temperatura, luminosidade, presença).

✔ Publicar dados sensoriados no RabbitMQ em intervalos regulares.

✔ Implementar multicast UDP (opcional).

**📌 Pessoa 3 e 4 - Cliente <-> Gateway**

✔ Desenvolver a interface do cliente (Web/Desktop).

✔ Criar chamadas ao Gateway via REST.

✔ Implementar funcionalidades principais (listar dispositivos, ligar/desligar atuadores).

---



## 📜 **Licença**

Este projeto é licenciado sob a  **MIT License** .

---

## 📢 **Contribuições**

🔹 Para contribuir, **crie uma branch** seguindo o padrão:

📌 **Sensores:** `feature/sensors`

📌 **Atuadores:** `feature/device-control`

📌 **Gateway:** `feature/gateway-api`

📌 **Cliente:** `feature/client-ui`

🚀 **Pull Requests são bem-vindos!**

---

## 📞 **Contato**

📧 **Equipe:** Diego, Ryan, Yasmin e Jorge

📌 **Repositório:** [https://github.com/diego-nac/smart-room-pubsub](https://github.com/diego-nac/smart-room-pubsub)

🎯 **Bora codar! 🚀**
