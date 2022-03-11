#!/bin/bash
. /home/pi/.bashrc

cd /home/pi/Documents/git/crypto_trader_SMA_TSL &&
source /home/pi/Documents/git/crypto_trader_SMA_TSL/trader/bin/activate &&
python /home/pi/Documents/git/crypto_trader_SMA_TSL/trader_no_console_cron.py