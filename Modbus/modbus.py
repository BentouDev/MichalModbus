from pymodbus.client.sync import ModbusTcpClient as ModbusClient

def get_modbus(address):
	if not address:
		raise Exception("Unable to connect to modbus when no address!")
	else:
		modbus = ModbusClient(address, port=502, timeout=10)
		if not modbus.connect():
			raise Exception("Unable to connect to modbus, check log for errors")
	modbus
