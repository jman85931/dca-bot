import gspread
from oauth2client.service_account import ServiceAccountCredentials
from binance.client import Client
from binance.enums import *
import realkeys

# vars
test = True
api_key = realkeys.apikey
api_secret = realkeys.secretkey
client = Client(api_key, api_secret)
user_data_stream_res = {}

temp_order_resp = {'symbol': 'BTCUSDT', 'orderId': 9277616436, 'orderListId': -1, 'clientOrderId': 'lakmd0AvoIBYHnYayhv7dv', 'transactTime': 1644092319454, 'price': '0.00000000', 'origQty': '0.00024000', 'executedQty': '0.00024000', 'cummulativeQuoteQty': '9.94113600', 'status': 'FILLED', 'timeInForce': 'GTC', 'type': 'MARKET', 'side': 'BUY', 'fills': [{'price': '41421.40000000', 'qty': '0.00024000', 'commission': '0.00000024', 'commissionAsset': 'BTC', 'tradeId': 1247402376}]}

# bot settings
def usersettings():
    
    user_inputs = {}
    
    user_inputs['dca_base_amount'] = 20
    user_inputs['dca_coins'] = ["BTC", "ETH", "MATIC"]
    user_inputs['base_currency'] = "USDT"
    user_inputs['risk_band_multiplier_step'] = 1
    user_inputs['sheet_name'] = 'DCA Dashboard v1.0'
    
    return user_inputs

# print risk band settings
def print_dca_settings(user_inputs):
    
    print("\nRisk Band DCA Amounts:\n")
    
    print(f"Base Amount = ${user_inputs['dca_base_amount']}\n")
    
    print(f"0.4 - 0.5 = ${user_inputs['dca_base_amount']} (${user_inputs['dca_base_amount']}*1)")
    print(f"0.3 - 0.4 = ${user_inputs['dca_base_amount']*(1+user_inputs['risk_band_multiplier_step'])} (${user_inputs['dca_base_amount']}*{(1+user_inputs['risk_band_multiplier_step'])})")
    print(f"0.2 - 0.3 = ${user_inputs['dca_base_amount']*(2+user_inputs['risk_band_multiplier_step'])} (${user_inputs['dca_base_amount']}*{(2+user_inputs['risk_band_multiplier_step'])})")
    print(f"0.1 - 0.2 = ${user_inputs['dca_base_amount']*(3+user_inputs['risk_band_multiplier_step'])} (${user_inputs['dca_base_amount']}*{(3+user_inputs['risk_band_multiplier_step'])})")
    print(f"0.0 - 0.1 = ${user_inputs['dca_base_amount']*(4+user_inputs['risk_band_multiplier_step'])} (${user_inputs['dca_base_amount']}*{(4+user_inputs['risk_band_multiplier_step'])})")

# setup dashboard
def sheetsetup(user_inputs):
    scope = ["https://spreadsheets.google.com/feeds",'https://www.googleapis.com/auth/spreadsheets',"https://www.googleapis.com/auth/drive.file","https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_name("creds.json", scope)
    gclient = gspread.authorize(creds)

    ss = gclient.open(user_inputs['sheet_name'])
    dashboard = ss.worksheet('Dashboard')
    
    return ss, dashboard, gclient 

# calculate risks
def risk(dashboard, user_inputs):
    risk_dict = {}
    
    # create coin + risk dict
    for i in user_inputs['dca_coins']:
        coin_cell = dashboard.find((i), in_column=0)
        coin_values = dashboard.row_values(coin_cell.row)
        
        try:
            risk_dict.update({i+"_RISK" : float(coin_values[dashboard.find('Risk').col-1])})
        except ValueError as e:
            print("Value Error: Check Google Sheet Risk Values")
            exit()
    
    return risk_dict
  
# calculate dca amounts based on risk and create dict
def dca_order_dict(risk_dict, user_inputs):
    
    qty_dict = {}
    
    for k, v in risk_dict.items():
        
        coin = k[:-5]
        
        if v >= 0.5:
            print(f"\n{coin}\n{coin} is greater than or equal to 0.5 risk, skipping DCA.")
        elif 0.4 <= v < 0.5:
            dca_amount = user_inputs['dca_base_amount']*1
            print(f"\n{coin}\n\n{coin} Risk = {v}\nBuying ${dca_amount} of {coin}")
            qty_dict.update({f'{coin}': dca_amount})
        elif 0.3 <= v < 0.4:
            dca_amount = user_inputs['dca_base_amount']*(1+user_inputs['risk_band_multiplier_step'])
            print(f"\n{coin}\n\n{coin} Risk = {v}\nBuying ${dca_amount} of {coin}")
            qty_dict.update({f'{coin}': dca_amount})
        elif 0.2 <= v < 0.3:
            dca_amount = user_inputs['dca_base_amount']*(2+user_inputs['risk_band_multiplier_step'])
            print(f"\n{coin}\n\n{coin} Risk = {v}\nBuying ${dca_amount} of {coin}")
            qty_dict.update({f'{coin}': dca_amount})
        elif 0.1 <= v < 0.2:
            dca_amount = user_inputs['dca_base_amount']*(3+user_inputs['risk_band_multiplier_step'])
            print(f"\n{coin}\n\n{coin} Risk = {v}\nBuying ${dca_amount} of {coin}")
            qty_dict.update({f'{coin}': dca_amount})
        elif 0 <= v < 0.1:
            dca_amount = user_inputs['dca_base_amount']*(4+user_inputs['risk_band_multiplier_step'])
            print(f"\n{coin}\n\n{coin} Risk = {v}\nBuying ${dca_amount} of {coin}")
            qty_dict.update({f'{coin}': dca_amount})

    return qty_dict

# buy coins
def dca_buy(api_key, api_secret, qty_dict, user_inputs, client, temp_order_resp, test):
    
    orders = {}
    base_currency = user_inputs['base_currency']

    for k, v in qty_dict.items():
        symbol = k + base_currency
        dca_amount = v
        
        if test == True:
            buy_order = client.create_test_order(
                symbol=symbol,
                side=SIDE_BUY,
                type=ORDER_TYPE_MARKET,
                quoteOrderQty=dca_amount)
            temp_order_resp['symbol'] = symbol
            buy_order = temp_order_resp
        else:
            buy_order = client.create_order(
                symbol=symbol,
                side=SIDE_BUY,
                type=ORDER_TYPE_MARKET,
                quoteOrderQty=dca_amount)
        
        order = {f'{k}' : {'id' : buy_order['orderId'],
                           'symbol' : buy_order['symbol'],
                           'price' : buy_order['fills'][0]['price'],
                           'qty' : buy_order['executedQty'],
                           'cost' : buy_order['cummulativeQuoteQty'],
                           'time' : buy_order['transactTime']}}
        orders.update(order)
    
    return orders

# update dca dashboard with order information
def sheet_update(orders, ss, risk_dict):
    for k, v in orders.items():
        ws = ss.worksheet(f'DCA Tracker: {k}')
        
        def next_available_row(ws, cols_to_sample=2):
            # looks for empty row based on values appearing in 1st N columns
            cols = ws.range(1, 1, ws.row_count, cols_to_sample)
            return max([cell.row for cell in cols if cell.value]) + 1
        
        row =  next_available_row(ws, cols_to_sample=2)
        
        cols = {'id_col' : ws.find('ID').col,
            'date_col' : ws.find('Date').col,
            'time_col' : ws.find('Time').col,
            'price_col' : ws.find('Price').col,
            'risk_col' : ws.find('Risk').col,
            'cost_col' : ws.find('Cost').col,
            'qty_col' : ws.find('Qty').col}
        
        # update cells
        ws.update_cell(row, cols['id_col'], orders[f'{k}']['id'])
        ws.update_cell(row, cols['date_col'], orders[f'{k}']['time'])
        ws.update_cell(row, cols['time_col'], orders[f'{k}']['time'])
        ws.update_cell(row, cols['price_col'], orders[f'{k}']['price'])
        ws.update_cell(row, cols['risk_col'], risk_dict[f'{k}_RISK'])
        ws.update_cell(row, cols['cost_col'], orders[f'{k}']['cost'])
        ws.update_cell(row, cols['qty_col'], orders[f'{k}']['qty'])

# validate sheet
def sheet_validate(ss, dashboard, user_inputs):
    
    coins = user_inputs['dca_coins']
    
    for i in coins:
        try:
            dashboard.findall(i)
        except:
            print(f"\nError: Create Dashboard Row {i}")
            exit()
        
        try:
            ss.worksheet(f'DCA Tracker: {i}')
        except:
            print(f"\nError: Create DCA Tracker Sheet {i}")
            exit()
            
# run bot
def run():
    
    print('\n===== DCA Bot 1.0 =====')            
    
    user_inputs = usersettings()
    ss, dashboard, gclient = sheetsetup(user_inputs)
    sheet_validate(ss, dashboard, user_inputs)
    print_dca_settings(user_inputs)
    risk_dict = risk(dashboard, user_inputs)
    qty_dict = dca_order_dict(risk_dict, user_inputs)
    orders = dca_buy(api_key, api_secret, qty_dict, user_inputs, client, temp_order_resp, test)
    sheet_update(orders, ss, risk_dict)
    
    print(f'\n{ss.title} updated. Exiting\n')
    
    exit()

run()