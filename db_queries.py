import sqlite3 as sql
from datetime import datetime
from time import strptime
conn = sql.connect('crypto_trading.db')
c = conn.cursor()

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

## Position Open
c.execute('SELECT Currency, position FROM position')
result = c.fetchall()
for row in result:
    print(f'Position:{clean_up_sql_out(row,0)}')

print()

## Profitability
c.execute('SELECT sum(case when market = "buy" then price else price*-1 end) as profit FROM orders')
result = c.fetchall()
for row in result:
    print(f'Profit:{clean_up_sql_out(row,1)}')

print()

## Orders
c.execute('SELECT * FROM orders ORDER BY market_date DESC LIMIT 5')
result = c.fetchall()
for row in result:
    print(f'Orders:{clean_up_sql_out(row,1)}')

print()

## Stop Details

c.execute('SELECT Currency, stop_price FROM trailing_stop_loss ORDER BY market_date DESC LIMIT 1')
result = c.fetchall()
for row in result:
    print(f'Last Stop Price:{clean_up_sql_out(row,1)}')