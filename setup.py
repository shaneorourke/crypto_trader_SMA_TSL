import sqlite3 as sql
conn = sql.connect('crypto_trading.db')
c = conn.cursor()

c.execute('CREATE TABLE IF NOT EXISTS position (Currency text, position boolean, quantity int)')
conn.commit()

c.execute('INSERT INTO position VALUES ("BTCUSDT",0,0.001)')
conn.commit()

c.execute('CREATE TABLE IF NOT EXISTS hourlydata ("Index" text, Time datetime, Open float, High float, Low float, Close float, FastSMA float, SlowSMA float)')
conn.commit()

c.execute('CREATE TABLE IF NOT EXISTS orders (Currency text, quantity float, market text, price float, trigger text, market_date timestamp DEFAULT current_date)')
conn.commit()

c.execute('CREATE TABLE IF NOT EXISTS trailing_stop_loss (Currency text, stop_price float, market_date timestamp DEFAULT current_date)')
conn.commit()

c.execute('CREATE TABLE IF NOT EXISTS last_update (timestamp DEFAULT current_date)')
conn.commit()

c.close()