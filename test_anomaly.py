import math, time, argparse
from threading import Thread
import os
import json
import paho.mqtt.client as mqtt

mqtt_address = "147.83.159.195"
mqtt_port = 24183


client = mqtt.Client()
client.connect(mqtt_address, mqtt_port, 60)
# Crea un mensaje JSON
mensaje = {	"id_car": 	10,
        	"order": 	1,
            "route":	0}

# recibido de mapas
route = {"coordinates" : "[[2.176148,41.421548],[2.16762,41.412775],[2.166726,41.412418],[2.167433,41.411434],[2.178958,41.397453],[2.178529,41.397777]]",
         "type": "LineString"}

mensaje["route"] = route["coordinates"]

# Codifica el mensaje JSON a una cadena
mensaje_json = json.dumps(mensaje)

# Publica el mensaje en el topic "PTIN2023/A1/CAR"
client.publish("PTIN2023/CAR/STARTROUTE", mensaje_json)

# Crea un mensaje JSON
mensaje = {	"id_car": 	10,
            "hehe":	0}

mensaje["hehe"] = input("Escriu l'anomalia que vols testejar: ")

# Codifica el mensaje JSON a una cadena
mensaje_json = json.dumps(mensaje)
print(mensaje_json)

# Publica el mensaje en el topic "PTIN2023/A1/CAR"
client.publish("PTIN2023/CAR/ANOMALIA", mensaje_json)

# Cierra la conexión MQTT
client.disconnect()