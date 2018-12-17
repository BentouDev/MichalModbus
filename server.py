#!/usr/bin/python3
import sys
from flask import Flask
from flask import request
from flask import session
from flask import render_template
from flask_bootstrap import Bootstrap
import modbus as sm
import db as db
	
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

Bootstrap(app)

UNIT = 0x0

@app.route("/")
def hello():
	db_context = db.get_db()
	data = {'message':'Error, check log'}
	if 'address' in session:
            try:
                modbus = sm.get_modbus()
                if modbus:
                    data['message'] = "Connected to modbus at " + session['address'] + "! Awaiting commands."
            except Exception as error:
                    data['message'] = str(error)
	else:
		data['message'] = "Not connected..."
	
	cur = db_context.cursor()
	cur.execute ('SELECT * FROM widgets')
	data['widgets'] = cur.fetchall()
	
	return render_template('index.html', title='Modbus', data = data)

@app.route("/toggle_widget", methods=['GET', 'POST'])
def toggle_widget():
	widget_id = request.form['widget_id']
	if widget_id:
		return "toggled id " + widget_id + "!"
	else:
		return "no id passed!"

@app.route("/add_widget", methods=['GET', 'POST'])
def add_widget():
	return "addition!"

@app.route("/view_data")
def view_data():
	modbus = sm.get_modbus()
	if modbus :
		unit = request.args.get('unit')
		rr = None
		if unit :
			rr = modbus.write_registers(0, 1, unit=unit)
		else :
			rr = modbus.write_registers(0, 1, unit=UNIT)

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
	if 'address' in session :			
		session['address'] = None
		return "Disconnected!"
	return "Nothing to disconnect!"

def start():
	app.run(debug=True, host='0.0.0.0')

if __name__ == '__main__':
    start()
