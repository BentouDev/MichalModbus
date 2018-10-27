import sys
from flask import Flask
from flask import request
from pymodbus.client.sync import ModbusTcpClient as ModbusClient
	
# Configure modbus client logging
import logging
FORMAT = ('%(asctime)-15s %(threadName)-15s '
          '%(levelname)-8s %(module)-15s:%(lineno)-8s %(message)s')
logging.basicConfig(format=FORMAT)
log = logging.getLogger()
log.setLevel(logging.DEBUG)

UNIT = 0x1

# Create flask server app
app = Flask(__name__)	

# Create modbus client var
client = object()

@app.route("/benis")
def benis():
    return "Not good!"
    
@app.route("/")
def hello():
    return "Hello World!"
    
@app.route("/connect")
def connect_to_server():
	global client
	if client is ModbusClient:
		disconnect_from_server()
	address = request.args.get('address')
	if address:
		client = ModbusClient(address, port=5020)
		if client.connect():
			return "Connected"
		return "Problem with connection! Check log on server"
		
	return "No address passed!"
	
@app.route("/disconnect")
def disconnect_from_server():
	global client
	if client is ModbusClient:
		client.close()
		client = object()
		return "Disconnected!"
	return "Nothing to disconnect!"

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')
