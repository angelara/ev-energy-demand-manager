import pathlib

import time
import schedule
from datetime import date, timedelta
import daemon
import json
from PyP100 import PyP110
import amberelectric
from amberelectric.api import amber_api
from amberelectric.model.channel import ChannelType

import logging

settingsFile = str(pathlib.Path().resolve())+'/settings.json'

def extractCurrentPriceByChannel( data, value = ChannelType.GENERAL, returnFirst = True  ):
    currentPrice = [d.per_kwh for d in data if d.channel_type == value]
    if returnFirst:
        return currentPrice[0]
    else:
        return currentPrice

def extractDataByChannel( data, value = ChannelType.GENERAL, returnFirst = True ):
    filteredData = [d for d in data if d.channel_type == value]
    if returnFirst:
        return filteredData[0]
    else:
        return filteredData

def query_api(logger):
    thresholdPrice = 0

    # Read settings
    with open( settingsFile ) as json_file:
       dataSettings = json.load(json_file)
       configFile = dataSettings['configFile']

    # Read theshold price in cents/kWh from json configuration file
    with open( configFile ) as json_file:
       data = json.load(json_file)
       thresholdPrice = data['thresholdPrice']

    #Creates a P100 plug object
    p110 = PyP110.P110( dataSettings['smartPlugIP'], dataSettings['smartPlugUsername'], dataSettings['smartPlugPass']) 

    #If connection fails, retry every 30 seconds
    p110Connected = False
    while p110Connected is False:
        try:
            #Creates the cookies required for further methods
            p110.handshake() 

            #Sends credentials to the plug and creates AES Key and IV for further methods
            p110.login()
            
            p110Connected = True
        except Exception as e:
            logger.error("\t Exception: Failed on Handshake/login %s\n" % e)
            time.sleep(30)

    # Insert the API token you created at https://app.amber.com.au/developers
    configuration = amberelectric.Configuration(
        access_token = dataSettings['amberToken']
    )

    # Create an API instance
    api = amber_api.AmberApi.create(configuration)

    # Get the current NMI (national meter identifier) and the site ID
    site_id = None
    try:
        sites = api.get_sites()
        site_id = sites[0].id
    except amberelectric.ApiException as e:
        logger.error("\t Exception: %s\n" % e)
    
    # Get the current price
    try:
        currentPriceData = api.get_current_price(site_id)
    except amberelectric.ApiException as e:
        logger.error("\t Exception: %s\n" % e)

    currentPriceDataGeneral = extractDataByChannel(currentPriceData, ChannelType.GENERAL)

    try:
        # Turn on/off the plug based on the current price and the state of the plug
        plugIsOn = p110.getDeviceInfo()["result"]["device_on"]

        if currentPriceDataGeneral.per_kwh > thresholdPrice and plugIsOn:
            p110.turnOff()
            logger.info("NEM " + currentPriceDataGeneral.nem_time.strftime('%Y-%m-%d %H:%M') + 
                        " - current price is: %s > %s cents and the plug has been turned OFF", currentPriceDataGeneral.per_kwh, thresholdPrice)
            
        elif currentPriceDataGeneral.per_kwh <= thresholdPrice and plugIsOn is False:
            p110.turnOn() 
            logger.info("NEM " + currentPriceDataGeneral.nem_time.strftime('%Y-%m-%d %H:%M')  + \
                        " - current price is: %s < %s cents and the plug has been turned ON", currentPriceDataGeneral.per_kwh, thresholdPrice)
        else:
            logger.info("NEM " + currentPriceDataGeneral.nem_time.strftime('%Y-%m-%d %H:%M')  + \
                        " - Threshold %s & current price is %s cents. The plug stateOn = %s has not been changed", thresholdPrice, currentPriceDataGeneral.per_kwh, plugIsOn)
            
    except Exception as e:
            logger.error("\t Exception: Failed Turn On/Off %s\n" % e)

def main_program():

    # Read settings to find the location of the log file
    with open( settingsFile ) as json_file:
       dataSettings = json.load(json_file)

    # create logger
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.DEBUG)

    # create file handler
    handler = logging.FileHandler(dataSettings['logFile'])
    handler.setLevel(logging.DEBUG)

    # create formatter
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)

    # add handler to logger
    logger.addHandler(handler)
    
    # Schedule the task to run every hour when the minute marker 10 min
    schedule.every().hour.at(":00").do(query_api, logger)
    schedule.every().hour.at(":10").do(query_api, logger)
    schedule.every().hour.at(":20").do(query_api, logger)
    schedule.every().hour.at(":30").do(query_api, logger)
    schedule.every().hour.at(":40").do(query_api, logger)
    schedule.every().hour.at(":50").do(query_api, logger)

    while True:
        schedule.run_pending()
        time.sleep(60)


with daemon.DaemonContext():
     main_program()

## if you want to run it without detaching the process from the terminal, 
## comment the  2 lines above and uncomment the line below

# main_program()
