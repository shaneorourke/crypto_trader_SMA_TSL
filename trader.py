from binance import Client
import pandas as pd
import binance_keys as bk
import sqlite3 as sql
from rich.console import Console
from rich.theme import Theme
from time import sleep

conn = sql.connect('crypto_trading.db')
c = conn.cursor()

customer_theme = Theme({'info':"bold green italic",'integer':'blue bold','pos_warning':'yellow bold italic','neg_warning':'red bold'})
console = Console(color_system='auto',theme=customer_theme)

client = Client(api_key=bk.API_KEY,api_secret=bk.SECRET_KEY)

postframe = pd.read_sql('SELECT * FROM position',conn)

stop_loss_percentage = 0.03


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

def changepos(curr, buy=True):
    if buy:
        c.execute(f'UPDATE position SET position = True WHERE Currency="{curr}"')
    else:
        c.execute(f'UPDATE position SET position = True WHERE Currency="{curr}"')
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
    c.execute(f'INSERT INTO trailing_stop_loss VALUES("{curr}",{stop},NULL)')
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


def market_order(curr,qty,buy=True,binance_buy=False,price=float):
    if buy:
        side='BUY'
    else:
        side='SELL'
    if binance_buy:    
        order = client.create_order(symbol=curr,side=side,type='MARKET',quantity=qty)
        order = f'INSERT INTO orders VALUES("{curr}",{qty},"{side}",{price},NULL)'
    else:
        order = f'INSERT INTO orders VALUES("{curr}",{qty},"{side}",{price},NULL)'
        console.print(order)
        c.execute(order)
    console.print(order)

def get_buy_value(curr):
    c.execute(f'SELECT price FROM orders WHERE Currency = "{curr}" order by market_date desc LIMIT 1')
    result = c.fetchone()
    result = clean_up_sql_out(result,1)
    return result



def trader(curr):
    qty = postframe[postframe.Currency == curr].quantity.values[0]
    df = gethourlydata(curr)
    applytechnicals(df)
    lastrow = df.iloc[-1]
    position = check_position(curr)
    console.print(f'[info]Currency:[/info]{curr}')
    console.print(f'[info]Position:[/info]{position}')
    if int(position) == 0:
        console.print('[info]Looking for BUY[/info]')
        if lastrow.FastSMA > lastrow.SlowSMA:
            console.print('[pos_warning]BUY Conditions MET[/pos_warning]')
            market_order(curr,qty,True,False,lastrow.Close)
            changepos(curr, buy=True)
            stop = float(lastrow.Close) - (float(lastrow.Close) * stop_loss_percentage)
            insert_stop_loss(curr,stop)
        else:
            console.print('[pos_warning]BUY Conditions NOT MET YET[/pos_warning]')
            console.print(f'[info]Close:[/info][integer]{float(lastrow.Close)}[/integer]')
            console.print(f'[info]SMA Difference:[/info][integer]{round(lastrow.SlowSMA - lastrow.FastSMA,2)}[/integer] || Positive Triggers SELL')
            console.print(f'[info]FastSMA:[/info][integer]{float(round(lastrow.FastSMA))}[/integer]') 
            console.print(f'[info]SlowSMA:[/info][integer]{float(round(lastrow.SlowSMA,2))}[/integer]')
    else:
        console.print('[info]Looking for SELL[/info]')
        buy_price = get_buy_value(curr)
        stop_loss = get_stop_loss(curr)
        stop_loss = float(stop_loss)
        stop_loss_current = lastrow.Close - (lastrow.Close * stop_loss_percentage)
        console.print(f'[info]Buy Price:[/info][integer]{float(buy_price)}[/integer]')
        console.print(f'[info]Strenght:[/info][integer]{float(round(float(lastrow.Close)-float(buy_price),2))}[/integer]')
        console.print(f'[info]Close:[/info][integer]{float(lastrow.Close)}[/integer]')
        console.print(f'[info]Stop Loss:[/info][integer]{float(round(stop_loss,2))}[/integer]')
        console.print(f'[info]SMA Difference:[/info][integer]{round(lastrow.SlowSMA - lastrow.FastSMA,2)}[/integer] || Positive Triggers SELL')
        console.print(f'[info]FastSMA:[/info][integer]{float(round(lastrow.FastSMA))}[/integer]') 
        console.print(f'[info]SlowSMA:[/info][integer]{float(round(lastrow.SlowSMA,2))}[/integer]')
        if float(stop_loss_current) > stop_loss:
            console.print('[pos_warning]Increase STOP LOSS[/pos_warning]')
            stop_loss = stop_loss_current
            update_stop_loss(curr,stop_loss)
        if lastrow.Close <= stop_loss:
            console.print('[neg_warning]STOP LOSS TRIGGERED SALE[/neg_warning]')
            market_order(curr,qty,False,False,lastrow.Close)
            changepos(curr,buy=False)
        elif lastrow.SlowSMA > lastrow.FastSMA:
            console.print('[neg_warning]SMA Triggered SELL[/neg_warning]')
            market_order(curr,qty,False,False,lastrow.Close)
            changepos(curr,buy=False)
running=True
while running:
    for coin in postframe.Currency:
        trader(coin)
    console.print()
    sleep(1)