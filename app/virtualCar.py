import math, time, argparse
from threading import Thread
# ---------------------------- #
import json
import paho.mqtt.client as mqtt
# ------------------------------------------------------------------------------ #

parser = argparse.ArgumentParser()
parser.add_argument('--id', dest = 'id', help = 'CAR ID')
args = parser.parse_args()

ID = int(args.id)
# ------------------------------------------------------------------------------ #

status_car = {
    1 : "loading",
    2 : "unloading", 
    3 : "delivering",
    4 : "returning",
    5 : "waits",
    6 : "repairing",
    7 : "alert"
}

status_desc = {
    1 : "loading - se encuentra en el almacén cargando paquetes.",
    2 : "unloading - es troba en la colmena descarregant.", 
    3 : "delivering - camí cap a la colmena.",
    4 : "returning - tornada al magatzem.",
    5 : "waits - no fa res.",
    6 : "repairing - en taller per revisió o avaria.",
    7 : "alert - possible avaria de camí o qualsevol situació anormal."
}

clientS = mqtt.Client()

car_return = False
coordinates = None
start_coordinates = False

# Initialize the battery level and the autonomy
autonomy = 2000
battery_level = 100

# ------------------------------------------------------------------------------ #

def get_angle(x1, y1, x2, y2):
    dx = x2 - x1
    dy = y2 - y1
    return math.atan2(dy, dx)

# Function to control the car movement based on the angle
def move_car(angle, distance, battery_level, autonomy):
    
    # Calculate the distance traveled by the car
    distance_traveled = math.sqrt(distance[0]**2 + distance[1]**2)

    # Calculate the battery usage based on the distance traveled
    battery_usage = distance_traveled / 0.10  # Assuming the car uses 0.10 units of battery per meter
    
    # Update the battery level
    battery_level -= battery_usage

    # Update the autonomy based on the distance traveled and the battery usage
    autonomy -= distance_traveled / 100 * battery_level * 20

    stats = "Battery level: %.2f | Autonomy: %.2f | " % (battery_level, autonomy)

    # Send signal to the car to move in the appropriate direction based on the angle
    if angle > math.pi/4 and angle < 3*math.pi/4:
        # Move forward
        print(stats + "Moving forward")
    
    elif angle > -3*math.pi/4 and angle < -math.pi/4:
        # Move backward
        print(stats + "Moving backward")
    
    elif angle >= 3*math.pi/4 or angle <= -3*math.pi/4:
        # Turn left
        print(stats + "Turning left")
    
    else:
        # Turn right
        print(stats + "Turning right")
    
    return battery_level, autonomy

def start_car():
    
    global car_return
    
    global autonomy
    global battery_level

    x1, y1 = coordinates[0][0], coordinates[0][1]

    # Loop through each coordinate
    for i in range(1, len(coordinates)):
        x2, y2 = coordinates[i][0], coordinates[i][1]

        # Calculate the distance between the current point and the next point
        distance = (x2 - x1, y2 - y1)

        # Calculate the angle between the current point and the next point
        angle = get_angle(x1, y1, x2, y2)

        # Control the car movement based on the angle and update the battery level and the autonomy
        battery_level, autonomy = move_car(angle, distance, battery_level, autonomy)

        # Send the car position to Cloud
        send_location(ID, coordinates[i], 4 if car_return else 3, battery_level, autonomy)

        # Update the current point
        x1, y1 = x2, y2

        # Add some delay to simulate the car movement
        time.sleep(2)

    car_return = not car_return
    coordinates.reverse()

# ------------------------------------------------------------------------------ #

def send_location(id, location, status, battery, autonomy):

    # Connect to MQTT server
    clientS.connect("147.83.159.195", 24183, 60)

    # JSON
    msg = {	"id_car": 	        id,
            "location_act": 	{
                "latitude":     location[0],
                "longitude":    location[1]
            },
            "status_num":       status,
            "status":           status_car[status],
            "battery":          battery,
            "autonomy":         autonomy}

    # Code the JSON message as a string
    mensaje_json = json.dumps(msg)

    # Publish in "PTIN2023/CAR"
    clientS.publish("PTIN2023/CAR/UPDATELOCATION", mensaje_json)

    # Close MQTT connection
    clientS.disconnect()

def update_status(id, status):

    # Connect to MQTT server
    clientS.connect("147.83.159.195", 24183, 60)

    # JSON
    msg = {	"id_car":       id,
            "status_num":   status,
            "status":       status_car[status] }

    # Code the JSON message as a string
    mensaje_json = json.dumps(msg)

    # Publish in "PTIN2023/CAR"
    clientS.publish("PTIN2023/CAR/UPDATESTATUS", mensaje_json)

    print("CAR: " + str(id) + " | STATUS:  " + status_desc[status])

    # Close MQTT connection
    clientS.disconnect()

# ------------------------------------------------------------------------------ #

def is_json(data):
    try:
        json.loads(data)
        return True
    except json.decoder.JSONDecodeError:
        return False

def on_connect(client, userdata, flags, rc):

    global ID
    if rc == 0:
        print(f"CAR {ID} | Cloud connectat amb èxit.")
    client.subscribe("PTIN2023/#")
    
def on_message(client, userdata, msg):
    
    if msg.topic == "PTIN2023/CAR/STARTROUTE":	

        global ID
        global coordinates    
        if(is_json(msg.payload.decode('utf-8'))):
            
            payload = json.loads(msg.payload.decode('utf-8'))
            needed_keys = ["id_car", "order", "route"]

            if all(key in payload for key in needed_keys):                
                if ID == payload[needed_keys[0]] and payload[needed_keys[1]] == 1:
                    coordinates = json.loads(payload[needed_keys[2]])
                    print("RECEIVED ROUTE: " + str(coordinates[0]) + " -> " + str(coordinates[-1]))
            else:
                print("FORMAT ERROR! --> PTIN2023/CAR/STARTROUTE")        
        else:
            print("Message: " + msg.payload.decode('utf-8'))

def start():

    clientR = mqtt.Client()
    clientR.on_connect = on_connect
    clientR.on_message = on_message

    clientR.connect("147.83.159.195", 24183, 60)
    clientR.loop_forever()

# ------------------------------------------------------------------------------ #

def control():
    
    global car_return
    global coordinates
    global start_coordinates
    
    while True:

        if coordinates != None and not start_coordinates:
            start_coordinates = True

            # En proceso de carga ~ 10s
            update_status(ID, 1) # update_status(ID, 1, 0)
            time.sleep(10)

            # En reparto
            update_status(ID, 3) # update_status(ID, 3, 3)
            start_car()

        time.sleep(0.25)

        if start_coordinates:
                            
            if car_return:
                # En proceso de descarga ~ 10s
                update_status(ID, 2) # update_status(ID, 2, 0)
                time.sleep(5)

                # Vuelta al almacén
                update_status(ID, 4) # update_status(ID, 4, 0)
                start_car()
                            
            else:
                # En espera
                update_status(ID, 5) # update_status(ID, 5, 0)
                start_coordinates = False

                car_return = False
                coordinates = None


if __name__ == '__main__':

    API = Thread(target=start)
    CTL = Thread(target=control)

    CTL.start()
    API.start()

    CTL.join()
    API.join()
