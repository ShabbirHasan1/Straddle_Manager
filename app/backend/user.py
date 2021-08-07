from kiteconnect import KiteConnect
from flask import jsonify
import logging
import db, server
import csv

logging.basicConfig(level= logging.DEBUG)

def holdings():
    holdings = server.kite.holdings()
    logging.debug("Length Of Holdings is : " + str(len(holdings)))
    logging.debug("Holdings are :" + str(holdings))

def positions():
    positions = server.kite.positions()
    logging.debug("Length of Positions : " + str(len(positions)))
    logging.debug("Positions are : " + str(positions))

