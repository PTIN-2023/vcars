import math, time, argparse
from threading import Thread
import os
# ---------------------------- #
import json
import paho.mqtt.client as mqtt
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

mqtt_address = os.environ.get('MQTT_ADDRESS')
mqtt_port = int(os.environ.get('MQTT_PORT'))
num_cars = int(os.environ.get('NUM_CARS'))
car_speed = float(os.environ.get('CAR_SPEED'))
delta_time = 0.33

# ------------------------------------------------------------------------------ #

def get_angle(x1, y1, x2, y2):
    dx = x2 - x1
    dy = y2 - y1
    return math.atan2(dy, dx)

def is_json(data):
    try:
        json.loads(data)
        return True
    except json.decoder.JSONDecodeError:
        return False
# ------------------------------------------------------------------------------ #

class vcar:
    def __init__(self, id) -> None:
        self.clientS = mqtt.Client()

        self.ID = id

        # State variables
        self.car_return = False
        self.coordinates = None
        self.start_coordinates = False
        self.interpolation_val = 0

        # Initialize the battery level and the autonomy
        self.autonomy = 2000
        self.battery_level = 100

    # Function to control the car movement based on the angle
    def move_car(self, angle, distance, battery_level, autonomy):
        
        # Calculate the distance traveled by the car
        distance_traveled = math.sqrt(distance[0]**2 + distance[1]**2)

        # Calculate the battery usage based on the distance traveled
        battery_usage = distance_traveled / 0.10  # Assuming the car uses 0.10 units of battery per meter
        
        # Update the battery level
        battery_level -= battery_usage

        # Update the autonomy based on the distance traveled and the battery usage
        autonomy -= distance_traveled / 100 * battery_level * 20

        stats = "CAR: %d | Battery level: %.2f | Autonomy: %.2f | " % (self.ID, battery_level, autonomy)

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

    def interpolation_to_coord(self):
        # Get current 
        base_coord_index = min(math.floor(self.interpolation_val), len(self.coordinates) - 1)
        next_coord_index = min(base_coord_index + 1, len(self.coordinates) - 1)

        # Compute interpolated position
        remainder_interpolation = self.interpolation_val % 1
        latitude = self.coordinates[base_coord_index][1]*(1-remainder_interpolation) + self.coordinates[next_coord_index][1]*remainder_interpolation
        longitude = self.coordinates[base_coord_index][0]*(1-remainder_interpolation) + self.coordinates[next_coord_index][0]*remainder_interpolation

        return (latitude, longitude)
    
    def interpolation_to_next_coord(self):
        # Get current
        base_coord_index = min(math.floor(self.interpolation_val), len(self.coordinates) - 1)
        next_coord_index = min(base_coord_index + 1, len(self.coordinates) - 1)

        # Compute interpolated position
        remainder_interpolation = self.interpolation_val % 1
        latitude = self.coordinates[base_coord_index][1]*(1-remainder_interpolation) + self.coordinates[next_coord_index][1]*remainder_interpolation
        longitude = self.coordinates[base_coord_index][0]*(1-remainder_interpolation) + self.coordinates[next_coord_index][0]*remainder_interpolation

        # Check if we are at the end
        if base_coord_index == next_coord_index:
            return (latitude, longitude, len(self.coordinates) - 1)

        # Compute direction unit vector
        latitude_distance = self.coordinates[next_coord_index][1] - self.coordinates[base_coord_index][1]
        longitude_distance = self.coordinates[next_coord_index][0] - self.coordinates[base_coord_index][0]
        modulo = max(math.sqrt(latitude_distance*latitude_distance + longitude_distance*longitude_distance), 0.001)

        latitude_uv = latitude_distance/modulo
        longitude_uv = longitude_distance/modulo

        print("CAR: " + str(self.ID) + " | DIRECTION: " + str(latitude_uv) + " " + str(longitude_uv))

        # Compute next pos
        latitude = latitude + latitude_uv*car_speed*delta_time
        longitude = longitude + longitude_uv*car_speed*delta_time

        # Compute interpolation value
        interpolation_val = base_coord_index + ((latitude - self.coordinates[base_coord_index][1]) / (self.coordinates[next_coord_index][1] - self.coordinates[base_coord_index][1]))

        # Make sure we didn't overshoot
        if(next_coord_index < interpolation_val):
            latitude = self.coordinates[next_coord_index][1]
            longitude = self.coordinates[next_coord_index][0]
            interpolation_val = next_coord_index

        return (latitude, longitude, interpolation_val)

    def start_car(self):
        while self.interpolation_val < len(self.coordinates) - 1:
            print("CAR: " + str(self.ID) + " | -------------------------------------------------")
            print("CAR: " + str(self.ID) + " | INTERPOLATION VAR: " + str(self.interpolation_val))
            x1, y1 = self.interpolation_to_coord()
            print("CAR: " + str(self.ID) + " | POSITION: " + str(x1) + " " + str(y1))
            x2, y2, interpolation_val = self.interpolation_to_next_coord()
            print("CAR: " + str(self.ID) + " | NEW POS: " + str(x2) + " " + str(y2))
            print("CAR: " + str(self.ID) + " | NEW INTERPOLATION VAR: " + str(interpolation_val))

            # Calculate the distance between the current point and the next point
            distance = (x2 - x1, y2 - y1)

            # Calculate the angle between the current point and the next point
            angle = get_angle(x1, y1, x2, y2)

            # Control the car movement based on the angle and update the battery level and the autonomy
            self.battery_level, self.autonomy = self.move_car(angle, distance, self.battery_level, self.autonomy)

            # Send the car position to Cloud
            self.send_location(self.ID, (x2, y2), 4 if self.car_return else 3, self.battery_level, self.autonomy)

            # Update the current interpolation_val
            self.interpolation_val = interpolation_val

            # Add some delay to simulate the car movement
            time.sleep(car_speed)

        self.car_return = not self.car_return
        self.coordinates.reverse()

    def send_location(self, id, pos, status, battery, autonomy):
        latitude, longitude = pos

        # Connect to MQTT server
        self.clientS.connect(mqtt_address, mqtt_port, 60)

        # JSON
        msg = {	"id_car": 	        id,
                "location_act": 	{
                    "latitude":     latitude,
                    "longitude":    longitude
                },
                "status_num":       status,
                "status":           status_car[status],
                "battery":          battery,
                "autonomy":         autonomy}

        # Code the JSON message as a string
        mensaje_json = json.dumps(msg)

        # Publish in "PTIN2023/CAR"
        self.clientS.publish("PTIN2023/CAR/UPDATELOCATION", mensaje_json)

        # Close MQTT connection
        self.clientS.disconnect()

    def update_status(self, id, status):

        # Connect to MQTT server
        self.clientS.connect(mqtt_address, mqtt_port, 60)

        # JSON
        msg = {	"id_car":       id,
                "status_num":   status,
                "status":       status_car[status] }

        # Code the JSON message as a string
        mensaje_json = json.dumps(msg)

        # Publish in "PTIN2023/CAR"
        self.clientS.publish("PTIN2023/CAR/UPDATESTATUS", mensaje_json)

        print("CAR: " + str(id) + " | STATUS:  " + status_desc[status])

        # Close MQTT connection
        self.clientS.disconnect()

# ------------------------------------------------------------------------------ #

    def on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            print(f"CAR {self.ID} | Cloud connectat amb èxit.")
        client.subscribe("PTIN2023/#")
        
    def on_message(self, client, userdata, msg):
        
        if msg.topic == "PTIN2023/CAR/STARTROUTE":	
  
            if(is_json(msg.payload.decode('utf-8'))):
                
                payload = json.loads(msg.payload.decode('utf-8'))
                needed_keys = ["id_car", "order", "route"]

                if all(key in payload for key in needed_keys):                
                    if self.ID == payload[needed_keys[0]] and payload[needed_keys[1]] == 1:
                        self.coordinates = json.loads(payload[needed_keys[2]])
                        print("RECEIVED ROUTE: " + str(self.coordinates[0]) + " -> " + str(self.coordinates[-1]))
                else:
                    print("FORMAT ERROR! --> PTIN2023/CAR/STARTROUTE")        
            else:
                print("Message: " + msg.payload.decode('utf-8'))

    def start(self):

        clientR = mqtt.Client()
        clientR.on_connect = self.on_connect
        clientR.on_message = self.on_message

        clientR.connect(mqtt_address, mqtt_port, 60)
        clientR.loop_forever()

# ------------------------------------------------------------------------------ #

    def control(self):
        while True:
            if self.coordinates != None and not self.start_coordinates:
                self.start_coordinates = True

                # En proceso de carga ~ 10s
                self.update_status(self.ID, 1) # update_status(ID, 1, 0)
                time.sleep(10)

                # En reparto
                self.update_status(self.ID, 3) # update_status(ID, 3, 3)
                self.start_car()

            time.sleep(0.25)

            if self.start_coordinates:
                                
                if self.car_return:
                    # En proceso de descarga ~ 10s
                    self.update_status(self.ID, 2) # update_status(ID, 2, 0)
                    time.sleep(5)

                    # Vuelta al almacén
                    self.update_status(self.ID, 4) # update_status(ID, 4, 0)
                    self.start_car()
                                
                else:
                    # En espera
                    self.update_status(self.ID, 5) # update_status(ID, 5, 0)
                    self.start_coordinates = False

                    self.car_return = False
                    self.coordinates = None

# ------------------------------------------------------------------------------ #
# ------------------------------------------------------------------------------ #

if __name__ == '__main__':

    threads = []

    for i in range(1, num_cars+1):
        car = vcar(i)
        API = Thread(target=car.start)
        CTL = Thread(target=car.control)
        threads.append(API)
        threads.append(CTL)
        API.start()
        CTL.start()

    for t in threads:
        t.join()
