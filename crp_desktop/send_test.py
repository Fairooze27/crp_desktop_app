import serial
import time

packet = b"\x02! 6.3\n2 4.5\n3 13.1\nK 0.7\n$FB DEMO\n$FE V1\n\x03"

ser = serial.Serial("COM11", 9600)
time.sleep(1)
ser.write(packet)
ser.close()

print("Test packet sent!")
