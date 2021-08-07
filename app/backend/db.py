import csv
import logging, coloredlogs
import server,data
from datetime import datetime

logger = logging.getLogger(__name__)
coloredlogs.install(level= 'DEBUG')

def write_csv(contents, filename):
    keys = contents[0].keys()
    file = open(filename , "w", newline= '')
    file.truncate()
    dict_writer = csv.DictWriter(file, keys)
    dict_writer.writeheader()
    dict_writer.writerows(contents)
    file.close()

def write_instruments(instruments):
    logger.debug("Inserting The instrument Dump Into Csv File")
    write_csv(instruments, 'instruments.csv')
    logger.debug("Inserted The Instrument Into Csv Successfully")

def write_qoutes(qoute_data):
    for tick in qoute_data:
        tick_dict = {"instrument_token" : tick["instrument_token"],
        "data" : tick}
        server.mongo.db.qoute.update(tick_dict)

"""
Straddle entries will be here
Only 2 entries at max
"""
def write_order(order_data, type):
    logger.debug("Writing Order : {} into order_executed DB".format(order_data))
    symbol_data = server.call_symbol_data
    if type == "PE":
        symbol_data = server.put_symbol_data
    order_entry = {
        "type": type,
        "order" : order_data,
        "symbol_data" : symbol_data.to_dict()
    }
    server.mongo.db["order_executed"].insert_one(order_entry)
    logger.debug("Order Written Into order_executed Db")

def remove_order(type):
    server.mongo.db["order_executed"].delete_many({"type" : type})
    
"""
First checks if all data is there in volatile memory
If not fetches data from db and sets the volatile variables and subscribes for their tick data
"""
def check_in_position(type):
    if type == "CE" and server.in_call_position:
        return
    if type == "PE" and server.in_put_position:
        return
    cursor = server.mongo.db["order_executed"].find({})
    for document in cursor:
        if document["type"] == "CE":
            server.call_order_id = document["order"]["order_id"]
            server.call_average_price = document["order"]["average_price"]
            server.in_call_position = True
            server.call_symbol_data = document["symbol_data"]
        if document["type"] == "PE":
            server.put_order_id = document["order"]["order_id"]
            server.put_average_price = document["order"]["average_price"]
            server.in_put_position = True
            server.put_symbol_data = document["symbol_data"]
    return False

def write_option_chain(option_data):
    for idx, val in enumerate(option_data):
        option_data[idx]["strike"] = data.get_strike(val["instrument_token"])[0]
        option_data[idx]["type"] = data.get_strike(val["instrument_token"])[1]

    doc = {"date" : str(datetime.now()),
    "data" : option_data}
    server.mongo_option_chain.db["option_chain"].insert_one(doc)