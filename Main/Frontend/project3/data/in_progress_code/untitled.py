# -*- coding: utf-8 -*-
"""Untitled.ipynb

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/1GsPQt7I7fPvCsbcFr5KLnYWooYIoxFdL
"""

# import dependencies
import math
import json
import pymongo
import requests
import numpy as np
import pandas as pd
from config import api_key
from pymongo import MongoClient
from datetime import date, datetime, timedelta
from sklearn.preprocessing import MinMaxScaler
from keras.models import Sequential
from keras.layers import Dense, LSTM
import matplotlib.pyplot as plt
import plotly.express as px
plt.style.use('fivethirtyeight')

# Pull NASDAQ 100 information from nasdaq_constituent API 
# Set url
url = "https://financialmodelingprep.com/api/v3/nasdaq_constituent?apikey="+ api_key


# Create connection to mongoDB
client = MongoClient('mongodb://localhost:27017')
# Connect to stock_df database in mongoDB
db = client.stock_db ###################

# Get response using requests.request("GET", url).json()
response = requests.request("GET", url).json()

# Create empty list for global variables
stock_symbols = []
stock_date = []
close = []

# for loop through response to append symbol data
for r in response:
    # Isolate symbol data
    collect_symbols = r['symbol']
    # .append() collect_symbols to global variable stock_symbols
    stock_symbols.append(collect_symbols)
# Print symbol update to server    
print('Symbol data collected')

for stock in stock_symbols:
    # Retrive data
    one_stock = db.stock_data.find_one({'symbol': stock}) ########################3

    # Isolate symbol and historical data
    symbol = one_stock['symbol']
    historical_data = one_stock['historical']



    for h in historical_data:
        
        collect_dates = h['date']
        stock_date.append(collect_dates)
        
        collect_close = h['close']
        close.append(collect_close)

    # Create date variables for API request
    # Set variable for current date 
    current_date = date.today()
    # print(current_date)
    # Retrive last date stored in MongoDB
    last_date = max(stock_date)
    # print(last_date)

    #Create new_start_date to be a day after the last date
    date = datetime.strptime(last_date, '%Y-%m-%d') 
    # print(date)
    modified_date = date + timedelta(days=1)
    # print(modified_date)
    new_start_date = datetime.strftime(modified_date, '%Y-%m-%d')
    # print(new_start_date)

    # print(new_start_date)

    # Set new url to update data
    url = f"https://financialmodelingprep.com/api/v3/historical-price-full/{stock}?from={new_start_date}&to={current_date}&apikey={api_key}"
    # url

    # conditional statement to determine if an update query is needed
    # based on if last_data in MongDb < current_date being requested
    if str(last_date) < str(current_date):
        print(f"Last date in MongoDB is: {last_date}")
        # if so send new request fro url with new start and end date
        new_results = requests.request("GET", url).json()
        #print(new_results)
        
        if new_results == False:
            print("not null")
            # Isolate historical data
            historical_update = new_results['historical']
            #for loop through historacal_update to retrive updated data
            for h in historical_update:
                # Retrieve new date and close data
                date_update = h['date']
                close_update = h['close']
                #print(f"Date update {date_update}")
                #print(f"Close update {close_update}")
                # Send update to MongoDb and push tp historical list
                db.stock_data.update_one({'symbol': stock}, {'$push': {'historical': {'date': date_update, 'close': close_update}}})
                print("Update day complete")   
        else:
            print("Data up to date")

    # Retrive data
    one_stock = db.stock_data.find_one({'symbol': stock}) ########################3

    # Isolate symbol and historical data
    symbol = one_stock['symbol']
    historical_data = one_stock['historical']

    stock_date = []
    close = []

    for h in historical_data:
        
        collect_dates = h['date']
        stock_date.append(collect_dates)
        
        collect_close = h['close']
        close.append(collect_close)

    df = pd.DataFrame({'Date': stock_date,
                    'close': close})
    # df.head()

    df['Date'] = pd.to_datetime(df['Date'])
    # df.dtypes

    new_df = df.set_index('Date')
    new_df.head()

    new_df.shape

    # plt.figure(figsize =(16, 8))
    # plt.title('Closing Price History')
    # plt.plot(new_df['close'])
    # plt.xlabel('Date', fontsize=18)
    # plt.ylabel('Close Prize USD ($)', fontsize=18)
    # plt.show()

    # Create new df with only the 'Close' column
    data = new_df.filter(['close'])

    # Convert df to a numpy array
    dataset = data.values

    # Get the number of rows to train the model on
    training_data_len = math.ceil(len(dataset) * .8)

    # training_data_len

    # Scale the data to apply preprocessing scaling before presenting to nueral network
    scaler = MinMaxScaler(feature_range=(0,1))
    scaled_data = scaler.fit_transform(dataset)

    # Show scaled data representing values between 0-1
    # scaled_data

    # Create the training dataset 
    # Create the scaled training dataset
    train_data = scaled_data[0:training_data_len , :]

    # Split the data into x_train and y_train data sets
    # x_train will be the independent training variables
    # y_train will be the dependent variables
    x_train = []
    y_train = []

    for i in range(60, len(train_data)):
    # Append past 60 values to x_train
    # contains 60 vals index from position 0 to position 59
        x_train.append(train_data[i-60:i, 0])

    #y_train will contain the 61st value 
        y_train.append(train_data[i,0])

    # Run below to visualize the x & y trains. x should be an array of 60 values and y should be 1 value being the 61st
    # Changing to if i<=61 will provide a 2nd pass through
        if i<=60:
            print(x_train)
            print(y_train)

    # Convert x_train & y_train to numpy arrays  so we can use them for training the LSTM model
    x_train, y_train = np.array(x_train), np.array(y_train)

    # Reshape the data because LSTM network expects input to be 3 dimensional and as of now our x_train is 2D
    # number of sample(rows), timesteps(columns), and features(closing price)
    x_train = np.reshape(x_train, (x_train.shape[0], x_train.shape[1], 1))
    x_train.shape

    # Build LSTM model
    model = Sequential()
    # add LSTM with 50 neurons 
    model.add(LSTM(50, return_sequences=True, input_shape=(x_train.shape[1], 1)))
    model.add(LSTM(50, return_sequences=False))
    model.add(Dense(25))
    model.add(Dense(1))

    # Compile the model
    model.compile(optimizer='adam', loss='mean_squared_error')

    # Train the model
    model.fit(x_train, y_train, batch_size=1, epochs=1)

    # Create testing dataset
    # Create new array containing scaled values from index 2057 to 2646
    test_data = scaled_data[training_data_len - 60: , :]

    # Create the data sets x_test and y_test
    x_test = []
    # y_test contains actual 61st values (not scaled)
    y_test = dataset[training_data_len: , :]

    for i in range(60, len(test_data)):
        x_test.append(test_data[i-60:i, 0])

    # Convert data to numpy array to use is LSTM model
    x_test = np.array(x_test)

    # Reshape the data because data is 2D and we need 3D for LSTM
    # number of samples(rows), timesteps(col), features(closing price)
    x_test = np.reshape(x_test, (x_test.shape[0], x_test.shape[1], 1))

    # Get the models predicted price values for x_test dataset
    predictions = model.predict(x_test)
    predictions = scaler.inverse_transform(predictions)

    # Get the root mean squared error. Closer to 0 the better
    # rmse = np.sqrt(np.mean(predictions - y_test) **2)


    # Plot the data
    train = data[:training_data_len]
    valid = data[training_data_len:]
    valid['Predictions'] = predictions

    # Visualize the model
    # plt.figure(figsize=(16,8))
    # plt.title('Model')
    # plt.xlabel('Date', fontsize=18)
    # plt.ylabel('Close Price USD ($)', fontsize=18)
    # plt.plot(train['close'])
    # plt.plot(valid[['close', 'Predictions']])
    # plt.legend(['Train', 'Validation', 'Predictions'], loc='lower right')
    # plt.show()

    # Blue will indicate what the model was trained on
    # Red is actual closing values
    # Yellow is the prediction

    index_valid = valid.reset_index()
    index_valid_df = pd.DataFrame(index_valid)
    index_valid_df.head()

    stock_date = index_valid_df['Date']
    stock_date_list = []

    for stock in stock_date:
        collect_dates = stock
        clean_dates = datetime.strftime(collect_dates, '%Y-%m-%d')
        stock_date_list.append(clean_dates)
        
    #print(stock_date_list)

    close_data = index_valid_df['close']
    close_data_list = []

    for close in close_data:
        collect_close = close
        close_data_list.append(collect_close)
        
    #close_data_list

    predictions_data = index_valid_df['Predictions']
    predicted_data_list = []

    for predict in predictions_data:
        collect_predict = predict
        predicted_data_list.append(collect_predict)
        
    #predicted_data_list

    prediction_data = {
        'Date': stock_date_list,
        'Actual Close': close_data_list,
        'Predictions': predicted_data_list
    }
    print("Predictons done...")

    #prediction_data
    current_date = date.today().strftime('%Y-%m-%d')
    # print(current_date)

    db.stock_data.update_one({'symbol': stock}, {'$push': {'prediction': {'date': current_date, 'prediction_data': prediction_data}}})

    print("Upload done")