# Air Quality with SGP40, SPS30 and SHTC3

Small project to use some Sensirion sensors and a Raspberry Pi to measure indoor air quality.

## Setup

- connect sensors according to their datasheets
- enable I2C on the raspberry
- sudo apt install -y python-smbus i2c-tools libgpiod2
- python -m venv env-pi && source env-pi/bin/activate
- pip install -r requirements.txt
