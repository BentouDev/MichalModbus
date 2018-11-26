from flask import current_app, g, session
from flask.cli import with_appcontext
from pymodbus.client.sync import ModbusTcpClient as ModbusClient

def get_modbus():
	if 'modbus' not in g:
		if 'address' not in session:
			raise Exception("Unable to connect to modbus when no address!")
		else:
			g.modbus = ModbusClient(session['address'], port=502, timeout=10)
			if not g.modbus.connect():
				raise Exception("Unable to connect to modbus, check log for errors")
	return g.modbus

def disconnect_modbus():
	modbus = g.pop('modbus', None)
	if modbus is not None:
		modbus.close()

def init_app(app):
	app.teardown_appcontext(disconnect_modbus)
	app.cli.add_command(init_modbus_cmd)
