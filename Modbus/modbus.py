from pymodbus.client.sync import ModbusTcpClient as ModbusClient
import numpy, struct

REGISTER_CACHE = numpy.array((1,1))

def get_modbus(address):
	if not address:
		raise Exception("Unable to connect to modbus when no address!")
	else:
		modbus = ModbusClient(address, port=502, timeout=10)
		if not modbus.connect():
			raise Exception("Unable to connect to modbus, check log for errors")
		return modbus
	return None

def send(modbus, UNIT):
	global REGISTER_CACHE
	print(" [Debug] raw modbus packet " + str(REGISTER_CACHE))
	rr = modbus.write_registers(0x0, REGISTER_CACHE, unit=UNIT)
	modbus.close()
	return rr

def ensure_cache(id):
	global REGISTER_CACHE
	if id > len(REGISTER_CACHE):
		numpy.resize(REGISTER_CACHE, (1,id))

def set_float(id, value):
	global REGISTER_CACHE
	ensure_cache(id + 4)

	encoded_float = struct.pack('f', value)

	for i in range(4):
		REGISTER_CACHE[id + i] = encoded_float[i]
		i = i + 1

def set_byte(id, value):
	global REGISTER_CACHE
	ensure_cache(id)
	REGISTER_CACHE[id] = value # Set as it is
	print (' [debug] set register [' + id + '] to ' + value)