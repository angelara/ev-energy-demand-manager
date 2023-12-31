You can deploy this codebase on a Raspberry Pi. It works with the [Rasperry Pi Zero](https://www.raspberrypi.com/products/raspberry-pi-zero-w/), which is the less expensive version, up to the latest one. The next task is to get one of the smart-plugs available in your local hardware-store. We used a [TP-link tapo p110](https://www.bunnings.com.au/tp-link-tapo-p110-mini-energy-monitoring-smart-plug_p0367692), available in Bunnings. Finally, perhaps most importantly, you will need to change your retailer to Amber Electric to be able to use their API and be exposed to the electricity wholesale market price. Once you are set up as a customer, you must create an [API Token](https://app.amber.com.au/developers/).


# Setup 

install the following libraries 

```bash
sudo apt-get install libatlas-base-dev
pip install Flask gunicorn
pip install git+https://github.com/almottier/TapoP100.git@main
pip install amberelectric
pip install matplotlib
pip install python-daemon
pip install schedule
```

Install the following libraries as a superuser to allow the code to be initiated by the system. See below the settings for cron.

```bash
sudo pip install Flask gunicorn
sudo pip install git+https://github.com/almottier/TapoP100.git@main
sudo pip install amberelectric
sudo pip install schedule
sudo pip install python-daemon
```

# Service

Edit the setting.json file. It has the following variables needed to connect to your plug and connect to Amber. 

```json
{
    "configFile" : "<fullpath>/home-energy-demand-manager/webapp/config.json",
    "smartPlugIP" : "yourSmartPlugIP",
    "smartPlugUsername" : "yourUsername",
    "smartPlugPass": "yourPass",
    "amberToken": "yourAPItoken",
    "logFile" : "/tmp/amber_service.log"
}
```

The logFile will contain the result of each query to Amber's API, whether the smart plug has been switched off/on, and whether the threshold price has changed. This is an example of the log content:

```bash
2023-10-16 14:10:53,944 - INFO - NEM 2023-10-16 13:30 - Threshold 15 & current price is 9.08895 cents. The plug stateOn = True has not been changed
2023-10-16 14:20:55,866 - INFO - NEM 2023-10-16 13:30 - Threshold 15 & current price is 9.10343 cents. The plug stateOn = True has not been changed
2023-10-16 14:30:58,181 - INFO - NEM 2023-10-16 14:00 - Threshold 15 & current price is 9.47102 cents. The plug stateOn = True has not been changed
2023-10-16 14:37:48 - New Threshold has been set via the webapp with value 13
```

The logfile will be in the temporal folder and removed whenever your system restarts. If you want a persistent logFile, change it to another folder.


To run the scheduled jobs every 10 minutes

```bash 
python3 amber_service.py 
```

# Webserver

To run the webserver to monitor the service and update the threshold if needed

```bash
gunicorn -c gunicorn_config.py app:app
```

# Schedule as a Daemon (Cron on reboot)

To make sure the service runs when the raspberry pi starts, edit crontab as follows:

```bash
crontab -e
```

Add the following line, making sure the path points to where the script is located.

```bash
@reboot cd <fullpath>/home-energy-demand-manager/ && sudo python3 amber_service.py
@reboot cd <fullpath>/home-energy-demand-manager/webapp/ && sudo gunicorn -c gunicorn_config.py app:app
```

# Explore Amber's API

Check the [exploration python notebook](exploration.ipynb)
