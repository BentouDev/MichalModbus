import sys
from flask import Flask
from flask import request
from flask import session
import modbus as sm
	
# Configure modbus client logging
import logging
FORMAT = ('%(asctime)-15s %(threadName)-15s '
          '%(levelname)-8s %(module)-15s:%(lineno)-8s %(message)s')
logging.basicConfig(format=FORMAT)
log = logging.getLogger()
log.setLevel(logging.DEBUG)

UNIT = 0x1

server = None

# Create flask server app
app = Flask(__name__)
app.secret_key = b')xDEADBEEF'

UNIT = 0x0

@app.route("/")
def hello():
	address = session['address']
	if address:
		return "Connected to modbus at " + address + "! Awaiting commands."
	return "Not connected..."

@app.route("/view_data")
def view_data():
	modbus = sm.get_modbus()
	if modbus :
		rr = modbus.read_coils(0, 1, unit=UNIT)
		if rr.isError() :
			return "Error occured"
		return rr
	return "Unable to connect"

@app.route("/connect")
def connect_to_server():
	address = request.args.get('address')
	if address:
		session['address'] = address
		try:
			sm.get_modbus()
			return "Connected"
		except Exception as error:
			return 'Caught error: ' + str(error)

	return "No address passed!"
		
@app.route("/disconnect")
def disconnect_from_server():
	if session['address'] :			
		session['address'] = None
		return "Disconnected!"
	return "Nothing to disconnect!"

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')
