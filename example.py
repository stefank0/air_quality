import csv
import time
from datetime import datetime

from sensirion_i2c_driver import LinuxI2cTransceiver, I2cConnection
from sensirion_i2c_sgp4x import Sgp40I2cDevice
from sensirion_i2c_sht.shtc3.device import Shtc3I2cDevice

from sps30 import SPS30


sps = SPS30()

try:
	with open('data.csv', 'a', newline='') as f:
		writer = csv.writer(f)
		sps.start_measurement()
		with LinuxI2cTransceiver('/dev/i2c-1') as i2c_transceiver:
			connection = I2cConnection(i2c_transceiver)
			sgp40 = Sgp40I2cDevice(connection)
			shtc3 = Shtc3I2cDevice(connection)
			rows = []
			i = 0
			while True:
				i += 1
				sleep_time = 1.0 - (time.time() % 1.0)		# wait remaining time of this second
				if sleep_time < 0.5:
					print(f'sleep_time: {sleep_time}')
				time.sleep(sleep_time)
				pm = sps.get_measurement()['sensor_data']
				pm2_5_mass = pm['mass_density']['pm2.5']
				pm2_5_count = pm['particle_count']['pm2.5']
				pm10_mass = pm['mass_density']['pm10']
				pm10_count = pm['particle_count']['pm10']
				pm_size = pm['particle_size']
				t, rh = shtc3.measure()
				t = round(t.degrees_celsius, 3)
				rh = round(rh.percent_rh, 3)
				voc = sgp40.measure_raw(relative_humidity=rh, temperature=t).ticks
				if i % 60 == 0:
					now = datetime.now().strftime("%Y-%m-%d %H:%M")
					row = [now, t, rh, voc, pm2_5_mass, pm2_5_count, pm10_mass, pm10_count, pm_size]
					rows.append(row)
					if i % 600 == 0:
						print(*row, sep='\t')
				if len(rows) >= 120:
					writer.writerows(rows)
					f.flush()
					rows.clear()
except Exception as e:
	print('Closing')
	sps.close()
	print('Closed')
	print(e)
