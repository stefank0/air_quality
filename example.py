import csv
import os
import statistics
import time

os.environ['GPIOZERO_PIN_FACTORY'] = 'pigpio'

from gpiozero import LED

from sensirion_i2c_driver import LinuxI2cTransceiver, I2cConnection
from sensirion_i2c_sgp4x import Sgp40I2cDevice
from sensirion_i2c_sht.shtc3.device import Shtc3I2cDevice

from sps30 import SPS30


def need_to_write(data_rows):
    return len(data_rows) >= 60 * 24 or os.path.exists("write.tmp")


sps = None
led = LED(26)
is_red = False
latest_pm2_5_masses = [0.0, 0.0, 0.0]
pm_threshold = 15
retries = 0
is_enabled = True


print('starting measurements')


try:
    filename = os.path.join("air_quality", "data.csv")
    with open(filename, 'a', newline='') as f:
        writer = csv.writer(f)
        with LinuxI2cTransceiver('/dev/i2c-1') as i2c_transceiver:
            connection = I2cConnection(i2c_transceiver)
            sgp40 = Sgp40I2cDevice(connection)
            shtc3 = Shtc3I2cDevice(connection)
            rows = []
            data = {
              't': [],
              'rh': [],
              'voc': [],
              'pm2_5_mass': [],
              'pm2_5_count': [],
              'pm10_mass': [],
              'pm10_count': [],
              'pm_size': [],
            }
            while True:
                sleep_time = 1.0 - (time.time() % 1.0)		# wait remaining time of this second
                hour = time.localtime().tm_hour
                minute = time.localtime().tm_min
                is_measuring = is_enabled and ((minute < 3) or any(m > pm_threshold for m in latest_pm2_5_masses))
                try:
                    if sps is None:
                        if is_measuring:
                            sps = SPS30()
                            sps.start_measurement()
                    else:
                        if not is_measuring:
                            sps.close()
                            sps = None
                    retries = 0
                except Exception as e:
                    retries += 1
                    if retries > 1:     # for some reason the first attempt fails with i2c remote IO error, timeouts do not help
                        print(e)
                time.sleep(sleep_time)
                if sps is None:
                    pm2_5_mass = 0.0
                    pm2_5_count = 0.0
                    pm10_mass = 0.0
                    pm10_count = 0.0
                    pm_size = 0.0
                else:
                    pm = sps.get_measurement()['sensor_data']
                    pm2_5_mass = pm['mass_density']['pm2.5']
                    pm2_5_count = pm['particle_count']['pm2.5']
                    pm10_mass = pm['mass_density']['pm10']
                    pm10_count = pm['particle_count']['pm10']
                    pm_size = pm['particle_size']
                t, rh = shtc3.measure()
                # temperatuur lijkt ongeveer 2 graden te hoog (t.o.v. thermostaat)
                t = round(t.degrees_celsius - 2.0, 3)         # TODO: calibrate t and rh to another sensor
                # in Utrecht lijkt het regelmatig te vochtig te zijn
                rh = round(rh.percent_rh, 3)
                # 31000 is goed, 30500 is matig, lager dan 30000 is slecht
                voc = sgp40.measure_raw(relative_humidity=rh, temperature=t).ticks      # TODO: use Sensirion VOC algorithm?
                data['t'].append(t)
                data['rh'].append(rh)
                data['voc'].append(voc)
                data['pm2_5_mass'].append(pm2_5_mass)
                data['pm2_5_count'].append(pm2_5_count)
                data['pm10_mass'].append(pm10_mass)
                data['pm10_count'].append(pm10_count)
                data['pm_size'].append(pm_size)
                second = time.localtime().tm_sec
                if second == 55:
                    t = round(statistics.median(data['t']), 2)
                    rh = round(statistics.median(data['rh']), 2)
                    voc = round(statistics.median(data['voc']))
                    pm2_5_mass = round(statistics.median(data['pm2_5_mass']), 2)
                    pm2_5_count = round(statistics.median(data['pm2_5_count']), 2)
                    pm10_mass = round(statistics.median(data['pm10_mass']), 2)
                    pm10_count = round(statistics.median(data['pm10_count']), 2)
                    pm_size = round(statistics.median(data['pm_size']), 2)
                    data = {
                      't': [],
                      'rh': [],
                      'voc': [],
                      'pm2_5_mass': [],
                      'pm2_5_count': [],
                      'pm10_mass': [],
                      'pm10_count': [],
                      'pm_size': [],
                    }
                    if sps is not None:
                        latest_pm2_5_masses.append(pm2_5_mass)
                        latest_pm2_5_masses.pop(0)
                    if os.path.exists("measure.tmp"):
                        latest_pm2_5_masses[0] = 99.9
                    if (rh < 40) or (rh > 70) or (voc < 30000) or (pm2_5_mass > pm_threshold):
                        if not is_red:
                            led.on()
                            is_red = True
                    else:
                        if is_red:
                            led.off()
                            is_red = False
                    print(hour, minute, t, rh, voc, latest_pm2_5_masses[-1])
                    now = int(time.time())
                    row = [now, t, rh, voc, pm2_5_mass, pm2_5_count, pm10_mass, pm10_count, pm_size]
                    rows.append(row)
                    if need_to_write(rows):
                        print('write data to disk')
                        writer.writerows(rows)
                        f.flush()
                        rows.clear()
                        if os.path.exists("write.tmp"):
                            os.remove("write.tmp")
                    is_enabled = not os.path.exists("disable.tmp")
except Exception as e:
    if sps is not None:
        sps.close()
    print(e)
