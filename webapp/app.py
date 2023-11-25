from flask import Flask, render_template, request, jsonify

import json
import datetime  # Import datetime module
import time
from PyP100 import PyP110
import amberelectric
from amberelectric.api import amber_api
from amberelectric.model.channel import ChannelType
import logging


app = Flask(__name__)


# Define a global variable to store the current threshold price
current_threshold_price = 0

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

    # Read theshold price in cents/kWh from json configuration file or the value updated by the slider
    global current_threshold_price
    
    with open('../settings.json', 'r') as config_file:
        dataSettings = json.load(config_file)

    #Creates a P100 plug object
    p110 = PyP110.P110( dataSettings['smartPlugIP'], dataSettings['smartPlugUsername'], dataSettings['smartPlugPass']) 

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
        plugIsOn = p110.getDeviceInfo()["device_on"]

        if currentPriceDataGeneral.per_kwh > current_threshold_price and plugIsOn:
            p110.turnOff()
            logger.info("NEM " + currentPriceDataGeneral.nem_time.strftime('%Y-%m-%d %H:%M') + 
                        " - current price is: %s > %s cents and the plug has been turned OFF", currentPriceDataGeneral.per_kwh, current_threshold_price)
            
        elif currentPriceDataGeneral.per_kwh <= current_threshold_price and plugIsOn is False:
            p110.turnOn() 
            logger.info("NEM " + currentPriceDataGeneral.nem_time.strftime('%Y-%m-%d %H:%M')  + \
                        " - current price is: %s < %s cents and the plug has been turned ON", currentPriceDataGeneral.per_kwh, current_threshold_price)
        else:
            logger.info("NEM " + currentPriceDataGeneral.nem_time.strftime('%Y-%m-%d %H:%M')  + \
                        " - Threshold %s & current price is %s cents. The plug stateOn = %s has not been changed", current_threshold_price, currentPriceDataGeneral.per_kwh, plugIsOn)
            
    except Exception as e:
            logger.error("\t Exception: Failed Turn On/Off %s\n" % e)

def initialize_logger():

    with open('../settings.json', 'r') as config_file:
        dataSettings = json.load(config_file)
        
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
    return logger 

# cron examples
def job():
    logger = initialize_logger()

    # Call the query_api function with the logger
    query_api(logger)

@app.route('/query_api', methods=['POST'])
def query_api_endpoint():
    global current_threshold_price  # Access the global threshold price variable
    logger = initialize_logger()  # Initialize the logger as needed

    new_threshold_price = int(request.form.get('thresholdPrice'))
    current_threshold_price = new_threshold_price  # Update the global threshold price

    # Call the query_api function with the logger
    query_api(logger)

    # Return a response (if needed)
    return jsonify({'message': 'Query API executed successfully'})


@app.route('/')
def index():
    with open('config.json', 'r') as config_file:
        config_data = json.load(config_file)
    threshold_price = config_data.get('thresholdPrice', 0)
    
    global current_threshold_price
    current_threshold_price = threshold_price  # Update the global threshold price

    with open('../settings.json', 'r') as config_file:
        dataSettings = json.load(config_file)

    # Load content from /tmp/amber_service.log
    try:
        with open(dataSettings['logFile'], 'r') as log_file:
            log_lines = log_file.readlines()
            log_lines.reverse()  # Reverse the list of lines
            log_content = ''.join(log_lines)  # Join the lines back into a single string
    except FileNotFoundError:
        log_content = 'Log file not found.'
    
    return render_template('index.html', threshold_price=threshold_price, log_content=log_content)

@app.route('/get_log', methods=['GET'])
def get_log_content():
    with open('../settings.json', 'r') as config_file:
        dataSettings = json.load(config_file)
    
    try:
        with open(dataSettings['logFile'], 'r') as log_file:
            log_lines = log_file.readlines()
            log_lines.reverse()  # Reverse the list of lines
            log_content = ''.join(log_lines)  # Join the lines back into a single string
    except FileNotFoundError:
        log_content = 'Log file not found.'
    return jsonify({'log_content': log_content})

@app.route('/save', methods=['POST'])
def save_threshold_price():
    new_threshold_price = int(request.form.get('thresholdPrice'))
    with open('config.json', 'r') as config_file:
        config_data = json.load(config_file)
        config_data['thresholdPrice'] = new_threshold_price
    with open('config.json', 'w') as config_file:
        json.dump(config_data, config_file, indent=4)

    # Add a log entry with the current time
    current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_message = f"{current_time} - New Threshold has been set via the webapp with value {new_threshold_price}"

    with open('../settings.json', 'r') as config_file:
        dataSettings = json.load(config_file)

    with open(dataSettings['logFile'], 'a') as log_file:
        log_file.write(log_message + '\n')

    # Return the updated log content
    try:
        with open(dataSettings['logFile'], 'r') as log_file:
            log_lines = log_file.readlines()
            log_lines.reverse()
            log_content = ''.join(log_lines)
    except FileNotFoundError:
        log_content = 'Log file not found.'

    return jsonify({'log_content': log_content})

if __name__ == '__main__':
    app.run(debug=False)

 