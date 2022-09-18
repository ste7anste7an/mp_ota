import time, app.secrets as secrets, network
from mqtt import MQTTClient
import ubinascii
import machine
import micropython
import network
import esp
import gc
import ntptime
import json
from neopixel import NeoPixel
from machine import Pin

def do_connect():
    import network
    sta_if = network.WLAN(network.STA_IF)
    if not sta_if.isconnected():
        print('connecting to network...')
        sta_if.active(True)
        sta_if.connect(secrets.WIFI_SSID, secrets.WIFI_PASSWORD)
        while not sta_if.isconnected():
            pass
    print('network config:', sta_if.ifconfig())

# initialization
esp.osdebug(None)
gc.collect()
do_connect()
ntptime.settime()
np=NeoPixel(Pin(21),3)

sta_if = network.WLAN(network.STA_IF)
def show_time(tns):
    ts=time.localtime(int(tns//1000000000))
    tus=(tns%1000000000)/1000
    print(ts,tus)
    
mqtt_server = secrets.MQTT_SERVER
# unique client ID based on mac address
client_id = ubinascii.hexlify(machine.unique_id())
topic_cmd_sub = b'robot/'+client_id+b'/cmd'
topic_pub = b'robot/'+client_id

last_message = 0
message_interval = 5
counter = 0

# cmds
# "status"
# "network"
# {'neopixel':{"nr":1,"rgb":[10,0,0]}}


def sub_cb(topic, msg):
  print((topic, msg))
  js_msg=None
  try:
      js_msg=json.loads(msg)
      print('received js_msg',js_msg)
  except ValueError as err:
      print("ValueError: {0}".format(err))
      # <TO DO> send a status report back to MQTT server
  if topic == topic_cmd_sub:
      if js_msg == 'status':
          client.publish(topic_pub+b'/battery', ("%d perc"%95).encode('utf-8'))
      elif js_msg == 'network':
          if sta_if.isconnected():
              client.publish(topic_pub+b'/network', (str(sta_if.ifconfig())).encode('utf-8'))
      elif 'neopixel' in js_msg:
          neo=js_msg['neopixel']
          np[neo['nr']]=neo['rgb']
          np.write()
          print("neopixel",neo["nr"],neo["rgb"])
  #if topic == b'robot/notification' and msg == b'time':
  #  client.publish(topic_pub+b'/time', ("%d"%((time.time_ns()%1000000000)//1000000)).encode('utf-8'))

def connect_and_subscribe():
  global client_id, mqtt_server, topic_sub
  client = MQTTClient(client_id, mqtt_server)
  client.set_callback(sub_cb)
  client.connect()
  client.subscribe(topic_cmd_sub)
  print('Connected to %s MQTT broker, subscribed to %s topic' % (mqtt_server, topic_cmd_sub))
  return client

def restart_and_reconnect():
  print('Failed to connect to MQTT broker. Reconnecting...')
  time.sleep(10)
  #machine.reset()

try:
  client = connect_and_subscribe()
except OSError as e:
  restart_and_reconnect()

while True:
  try:
    client.check_msg()
    if (time.time() - last_message) > message_interval:
      msg = b'Hello #%d' % counter
      client.publish(topic_pub+b'/counter/', msg)
      last_message = time.time()
      counter += 1
  except OSError as e:
    restart_and_reconnect()
