import sqlite3 as sql
from datetime import datetime
from symtable import Symbol
from binance import Client
import binance_keys as bk
conn = sql.connect('crypto_trading.db')
c = conn.cursor()

client = Client(api_key=bk.API_KEY,api_secret=bk.SECRET_KEY)

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


## Last Update
c.execute('SELECT timestamp FROM last_update ORDER BY timestamp DESC LIMIT 1')
result = c.fetchone()
result = clean_up_sql_out(result,0)
time_now = datetime.now()
print(f'Last Update:{result}')
print(f'Time Now:{str(time_now)}')

print()


c.execute('SELECT Currency FROM position')
currencies = c.fetchall()
for curr in currencies:
    curr=clean_up_sql_out(curr,0)
    curr=curr.replace("'","")

    print(f'##### CURRENCY:{curr}')

    ## Position Open
    c.execute(f'SELECT position FROM position WHERE Currency="{curr}"')
    result = c.fetchall()
    for row in result:
        row = clean_up_sql_out(row,0)
        if row == 0:
            position = 'BUYING'
        else:
            position = 'SELLING'
        print(f'Position:{position}')

    ## Profitability
    c.execute(f'SELECT round(sum(case when market = "SELL" then price else price*-1 end),2) as profit FROM orders WHERE Currency="{curr}"')
    result = c.fetchall()
    print(f'Profit:{clean_up_sql_out(result,1)}')

    ## Stop Details
    c.execute('SELECT round(stop_price,2) FROM trailing_stop_loss ORDER BY market_date DESC LIMIT 1')
    result = c.fetchall()
    print(f'Last Stop Price:{clean_up_sql_out(result,1)}')

    ## Original Stop Details Est
    c.execute('SELECT round(price-(price * 0.03),2) FROM orders WHERE market = "BUY" ORDER BY market_date DESC LIMIT 1')
    result = c.fetchall()
    print(f'Original Stop Est:{clean_up_sql_out(result,1)}')

    price=client.get_symbol_ticker(symbol=curr)
    print(f'Current Price:{float(price["price"])}')


    ## Orders
    c.execute(f'SELECT * FROM orders WHERE Currency="{curr}" ORDER BY market_date DESC LIMIT 5')
    result = c.fetchall()
    for row in result:
        print(f'Orders:{clean_up_sql_out(row,1)}')


    print()
    ## Profitability
    c.execute(f'SELECT round(sum(case when market = "SELL" then price else price*-1 end),2) as profit FROM orders')
    result = c.fetchall()
    print(f'##### Total Profit Percentage:{clean_up_sql_out(result,1)}')