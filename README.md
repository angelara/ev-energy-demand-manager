You can deploy this codebase on a raspberry-pi and buy one of the smart-plugs available in your local hardware-store. We used a [TP-link tapo p110](https://www.bunnings.com.au/tp-link-tapo-p110-mini-energy-monitoring-smart-plug_p0367692), available in Bunnings.

You will need to change your retailer to Ammber Electric to be able to use their API and be exposed to the electricity wholesale market price. Once you are set up as a costumer, you'll need to create a an [API Token](https://app.amber.com.au/developers/).


# Setup 

install the following libraries 

```bash
sudo apt-get install libatlas-base-dev
pip install Flask gunicorn
pip install PyP100
pip install amberelectric
pip install matplotlib
pip install python-daemon
pip install schedule
```

Install the following libraries as a superuser to allow the code to be initiated by the system. See below the settings for cron.

```bash
sudo pip install Flask gunicorn
sudo pip install PyP100
sudo pip install amberelectric
sudo pip install schedule
sudo pip install python-daemon
```

# Service

Edit the setting.json file. It has the following variables needed to connect to your plug, and connect to Amber. 

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

The logFile will contain the result of each query to Amber's API, whether the smart plug has been switched off/on, and the threshold price has changed. This is an example of the log content:

```bash
2023-10-16 14:10:53,944 - INFO - NEM 2023-10-16 13:30 - Threshold 15 & current price is 9.08895 cents. The plug stateOn = True has not been changed
2023-10-16 14:20:55,866 - INFO - NEM 2023-10-16 13:30 - Threshold 15 & current price is 9.10343 cents. The plug stateOn = True has not been changed
2023-10-16 14:30:58,181 - INFO - NEM 2023-10-16 14:00 - Threshold 15 & current price is 9.47102 cents. The plug stateOn = True has not been changed
2023-10-16 14:37:48 - New Threshold has been set via the webapp with value 13
```

The logfile will is located in the temporal folder, and will be removed everytime your system restarts. If you want a persistent logFile, change it to another folder.


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

And add the following line, making sure the path points to where the script is located

```bash
@reboot sudo python3 <fullpath>/home-energy-demand-manager/amber_service.py
@reboot cd <fullpath>/home-energy-demand-manager/webapp/ && sudo gunicorn -c gunicorn_config.py app:app
```

# Explore Amber's API

Check the [exploration python notebook](exploration.ipynb)