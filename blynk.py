import BlynkLib
import time

BLYNK_AUTH = 'a36002672f60424d9e420fcd22bc3b6a'

blynk = BlynkLib.Blynk(BLYNK_AUTH)

@blynk.VIRTUAL_WRITE(1)
def WriteHandler(value):
	print ('Hue {}', value)
	
@blynk.VIRTUAL_READ(2)
def ReadHandler():
	blynk.virtual_write(2, time.ticks_ms() / 1000)
	
blynk.run()
