#!/bin/bash
echo "Iniciando gateway..."
nohup python3 gateway.py > gateway.log 2>&1 &

echo "Iniciando sensor_temperature..."
nohup python3 sensor_temperature.py > sensor_temperature.log 2>&1 &

echo "Iniciando actuator_air_conditioner..."
nohup python3 actuator_air_conditioner.py > actuator_air_conditioner.log 2>&1 &

echo "Iniciando sensor_presence..."
nohup python3 sensor_presence.py > sensor_presence.log 2>&1 &

echo "Iniciando actuator_door..."
nohup python3 actuator_door.py > actuator_door.log 2>&1 &

echo "Iniciando sensor_luminosity..."
nohup python3 sensor_luminosity.py > sensor_luminosity.log 2>&1 &

echo "Iniciando actuator_light..."
nohup python3 actuator_light.py > actuator_light.log 2>&1 &

echo "Todos os dispositivos foram iniciados."