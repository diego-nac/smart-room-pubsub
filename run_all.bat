@echo off
echo Iniciando gateway...
start python gateway.py

echo Iniciando sensor_temperature...
start python sensor_temperature.py
echo Iniciando actuator_air_conditioner...
start python actuator_air_conditioner.py

echo Iniciando sensor_presence...
start python sensor_presence.py
echo Iniciando actuator_door...
start python actuator_door.py

echo Iniciando sensor_luminosity...
start python sensor_luminosity.py
echo Iniciando actuator_light...
start python actuator_light.py

echo Todos os dispositivos foram iniciados.
pause
