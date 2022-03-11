from ntpath import join
from binance import Client
import pandas as pd
import binance_keys as bk
import sqlite3 as sql
from time import sleep
from datetime import datetime
import csv
import os

conn = sql.connect('crypto_trading.db')
c = conn.cursor()

client = Client(api_key=bk.API_KEY,api_secret=bk.SECRET_KEY)

postframe = pd.read_sql('SELECT * FROM position',conn)

stop_loss_percentage = 0.03

today = datetime.now().date()
today = str(today).replace('-','')

replace = ['(',')',',','./data/','csv','.']
replace_number = ['(',')',',']

def clean_up_sql_out(text,isnumber):
    if isnumber == 1:
        for s in replace_number:
            text = str(text).replace(s,'')
    else:
        for s in replace:
            text = str(text).replace(s,'')
    return text

def round_float(value):
    value = round(float(value),2)
    return value

def last_update():
    c.execute(f'DELETE FROM last_update')
    c.execute(f'INSERT INTO last_update VALUES("{datetime.now()}")')
    conn.commit()

def write_to_file(log_file_name,text):
    if not os.path.exists('logs'):
        os.mkdir('logs')
    file_path = os.path.join('logs',today)
    if not os.path.exists(file_path):
        os.mkdir(file_path)
    file_name = os.path.join(file_path,log_file_name)
    text = str(datetime.now()) + '||' + str(text)
    with open(f'{file_name}', 'a', encoding='UTF8') as f:
        writer = csv.writer(f)
        writer.writerow([text])
        f.close()

def changepos(curr, buy=True):
    if buy:
        c.execute(f'UPDATE position SET position = True WHERE Currency="{curr}"')
    else:
        c.execute(f'UPDATE position SET position = False WHERE Currency="{curr}"')
    conn.commit()
        
def check_position(curr):
    c.execute(f'SELECT position FROM position WHERE Currency="{curr}"')
    result = c.fetchone()
    result = clean_up_sql_out(result,1)
    return result

def get_stop_loss(curr):
    c.execute(f'SELECT stop_price FROM trailing_stop_loss WHERE Currency="{curr}" ORDER BY market_date DESC LIMIT 1')
    result = c.fetchone()
    result = clean_up_sql_out(result,1)
    return result

def update_stop_loss(curr,stop):
    c.execute(f'UPDATE trailing_stop_loss SET stop_price = {stop} WHERE Currency="{curr}"')
    conn.commit()

def insert_stop_loss(curr,stop):
    c.execute(f'INSERT INTO trailing_stop_loss VALUES("{curr}",{stop},"{datetime.now()}")')
    conn.commit()

def gethourlydata(symbol):
    frame = pd.DataFrame(client.get_historical_klines(symbol,'1h','25 hours ago UTC'))
    frame = frame.iloc[:,:5]
    frame.columns = ['Time','Open','High','Low','Close']
    frame[['Open','High','Low','Close']] = frame[['Open','High','Low','Close']].astype(float)
    frame.Time = pd.to_datetime(frame.Time, unit='ms')
    return frame

def applytechnicals(df):
    df['FastSMA'] = df.Close.rolling(7).mean()
    df['SlowSMA'] = df.Close.rolling(25).mean()
    #df.to_sql(name='hourlydata',con=conn,if_exists='append')


def market_order(curr,qty,buy=True,binance_buy=False,price=float,trigger=str):
    if buy:
        side='BUY'
    else:
        side='SELL'
    if binance_buy:    
        order = client.create_order(symbol=curr,side=side,type='MARKET',quantity=qty)
        order = f'INSERT INTO orders VALUES("{curr}",{qty},"{side}",{price},"{trigger}","{datetime.now()}")'
    else:
        order = f'INSERT INTO orders VALUES("{curr}",{qty},"{side}",{price},"{trigger}","{datetime.now()}")'
        c.execute(order)
    write_to_file(f'{curr}',order)

def get_buy_value(curr):
    c.execute(f'SELECT price FROM orders WHERE Currency = "{curr}" order by market_date desc LIMIT 1')
    result = c.fetchone()
    result = clean_up_sql_out(result,1)
    return result

def get_last_order_sell_reason(curr):
    c.execute(f'SELECT trigger FROM orders WHERE Currency = "{curr}" order by market_date desc LIMIT 1')
    result = c.fetchone()
    result = clean_up_sql_out(result,0)
    return result

def waiting_for_next_entry(curr):
    c.execute(f'SELECT waiting FROM waiting_for_entry WHERE Currency = "{curr}"')
    result = c.fetchone()
    result = clean_up_sql_out(result,1)
    return result

def update_waiting_for_next_entry(curr,waiting):
    c.execute(f'UPDATE waiting_for_entry SET waiting = {waiting} WHERE Currency = "{curr}"')
    conn.commit()

def trader(curr):
    qty = postframe[postframe.Currency == curr].quantity.values[0]
    df = gethourlydata(curr)
    applytechnicals(df)
    lastrow = df.iloc[-1]
    position = check_position(curr)
    write_to_file(f'{curr}',f'Currency:{curr}')
    write_to_file(f'{curr}',f'Position:{position}')
    if get_last_order_sell_reason(curr) == 'stop':
        write_to_file(f'{curr}',f'STOPPED WAITING FOR TRIGGER TO RESET')
        if lastrow.FastSMA > lastrow.SlowSMA:
            update_waiting_for_next_entry(curr,1)
            write_to_file(f'{curr}',f'CONTINUING WAITING FOR TRIGGER TO RESET')
        if not lastrow.FastSMA > lastrow.SlowSMA:
            write_to_file(f'{curr}',f'WAITING TRIGGER RESET')
            update_waiting_for_next_entry(curr,0)
    waiting = waiting_for_next_entry(curr)
    write_to_file(f'{curr}',f'WAITING:{waiting}')
    if waiting == False or waiting == 'None':
        if int(position) == 0:
            write_to_file(f'{curr}','Looking for BUY')
            if lastrow.FastSMA > lastrow.SlowSMA:
                write_to_file(f'{curr}','BUY Conditions MET')
                market_order(curr,qty,True,False,lastrow.Close,'buy')
                changepos(curr, buy=True)
                stop = float(lastrow.Close) - (float(lastrow.Close) * stop_loss_percentage)
                insert_stop_loss(curr,stop)
            else:
                write_to_file(f'{curr}','BUY Conditions NOT MET YET')
                write_to_file(f'{curr}',f'Close:{float(lastrow.Close)}')
                write_to_file(f'{curr}',f'SMA Difference:{round(lastrow.FastSMA - lastrow.SlowSMA,2)} || Positive Triggers BUY')
                write_to_file(f'{curr}',f'FastSMA:{float(round(lastrow.FastSMA))}') 
                write_to_file(f'{curr}',f'SlowSMA:{float(round(lastrow.SlowSMA,2))}')
        else:
            write_to_file(f'{curr}','Looking for SELL')
            buy_price = get_buy_value(curr)
            stop_loss = get_stop_loss(curr)
            stop_loss = float(stop_loss)
            stop_loss_current = lastrow.Close - (lastrow.Close * stop_loss_percentage)
            write_to_file(f'{curr}',f'Buy Price:{float(buy_price)}')
            write_to_file(f'{curr}',f'Strenght:{float(round(float(lastrow.Close)-float(buy_price),2))}')
            write_to_file(f'{curr}',f'Close:{float(lastrow.Close)}')
            write_to_file(f'{curr}',f'Stop Loss:{float(round(stop_loss,2))}')
            write_to_file(f'{curr}',f'SMA Difference:{round(lastrow.SlowSMA - lastrow.FastSMA,2)} || Positive Triggers SELL')
            write_to_file(f'{curr}',f'FastSMA:{float(round(lastrow.FastSMA))}') 
            write_to_file(f'{curr}',f'SlowSMA:{float(round(lastrow.SlowSMA,2))}')
            if float(stop_loss_current) > stop_loss:
                write_to_file(f'{curr}','Increase STOP LOSS')
                stop_loss = stop_loss_current
                update_stop_loss(curr,stop_loss)
            if lastrow.Close <= stop_loss:
                write_to_file(f'{curr}','STOP LOSS TRIGGERED SALE')
                market_order(curr,qty,False,False,lastrow.Close,'stop')
                changepos(curr,buy=False)
            elif lastrow.SlowSMA > lastrow.FastSMA:
                write_to_file(f'{curr}','SMA Triggered SELL')
                market_order(curr,qty,False,False,lastrow.Close,'SMA')
                changepos(curr,buy=False)

for coin in postframe.Currency:
    trader(coin)
    last_update()
    write_to_file(f'{coin}','')