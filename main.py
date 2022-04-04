import gspread
from oauth2client.service_account import ServiceAccountCredentials
from binance.client import Client
from binance.enums import *
import realkeys
import questionary
import time
import datetime as dt
from datetime import datetime as date
import json
from inputimeout import inputimeout, TimeoutOccurred
from pathlib import Path

# vars
test = False
time_out = 20
api_key = realkeys.apikey
api_secret = realkeys.secretkey
client = Client(api_key, api_secret)
custom_style = questionary.Style([
("question", "nobold"), ('answer', 'nobold')
])
today_int = dt.date.today().isoweekday()
today = date.today().strftime("%A")
# user_inputs = {}

temp_order_resp = {'symbol': 'BTCUSDT', 'orderId': 9277616436, 'orderListId': -1, 'clientOrderId': 'lakmd0AvoIBYHnYayhv7dv', 'transactTime': 1644092319454, 'price': '0.00000000', 'origQty': '0.00024000', 'executedQty': '0.00024000', 'cummulativeQuoteQty': '9.94113600', 'status': 'FILLED', 'timeInForce': 'GTC', 'type': 'MARKET', 'side': 'BUY', 'fills': [{'price': '41421.40000000', 'qty': '0.00024000', 'commission': '0.00000024', 'commissionAsset': 'BTC', 'tradeId': 1247402376}]}

# bot settings
def usersettings(enable_user_input):

    user_inputs = {}
    
    if enable_user_input == True:
        user_inputs['sheet_name'] = questionary.text('Enter google sheet name:', style=custom_style).ask()
        dca_coins = questionary.text('Enter coins (BTC, ETH, MATIC):', style=custom_style, instruction="Seperate coins by commas").ask().upper().split(",")
        user_inputs['dca_coins'] = [i.strip() for i in dca_coins]
        user_inputs['dca_details'], user_inputs = dca_details(user_inputs)
        user_inputs['base_currency'] = questionary.select(f'Base currency', style=custom_style, choices=['USDT', 'BUSD']).ask()
        user_inputs['risk_band_multiplier_step'] = float(questionary.text('Risk band multiplier step:', style=custom_style).ask())
    else:
        user_inputs['sheet_name'] = 'DCA Dashboard v1.0'
        user_inputs['dca_coins'] = ['BTC', 'ETH']
        user_inputs['dca_details'] = {'BTC': {'dca_amount': 20, 'dca_day': 'Monday', 'dca_day_int' : 1}, 'ETH': {'dca_amount': 30, 'dca_day': 'Friday', 'dca_day_int' : 5}}
        user_inputs['base_currency'] = 'USDT'
        user_inputs['risk_band_multiplier_step'] = 1
        
    return user_inputs

# dca amounts
def dca_details(user_inputs):
    
    dca_coins = user_inputs['dca_coins']
    user_inputs['dca_days'] = []
    
    dca_details = {}
    
    for i in dca_coins:
        dca_amount = questionary.text(f'DCA base amount for {i} in $', style=custom_style).ask().upper()
        dca_day = questionary.select(f'DCA day for {i}', style=custom_style, choices=['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']).ask().lower()
        dca_day_int = time.strptime(dca_day, "%A").tm_wday + 1
        dca_details.update({i : {'dca_amount' : float(dca_amount), 'dca_day' : dca_day, 'dca_day_int' : dca_day_int}})
        
        user_inputs['dca_days'].append(dca_day.capitalize())
    return dca_details, user_inputs

# print risk band settings
def print_dca_settings(user_inputs, enable_user_input):
    
    print("\nDCA Settings:\n")
    
    for k, v in user_inputs['dca_details'].items():
        
        base_amount = v['dca_amount']
        
        print(f'{k} DCA day is {v["dca_day"].capitalize()} for the following amounts:\n')
        print(f"0.4 - 0.5 = ${base_amount} (${base_amount} * 1)")
        print(f"0.3 - 0.4 = ${base_amount*(1+user_inputs['risk_band_multiplier_step'])} (${base_amount} * {(1+user_inputs['risk_band_multiplier_step'])})")
        print(f"0.2 - 0.3 = ${base_amount*(2+user_inputs['risk_band_multiplier_step'])} (${base_amount} * {(1+(user_inputs['risk_band_multiplier_step']*2))})")
        print(f"0.1 - 0.2 = ${base_amount*(3+user_inputs['risk_band_multiplier_step'])} (${base_amount} * {(1+(user_inputs['risk_band_multiplier_step']*3))})")
        print(f"0.0 - 0.1 = ${base_amount*(4+user_inputs['risk_band_multiplier_step'])} (${base_amount} * {(1+(user_inputs['risk_band_multiplier_step']*4))})\n")
    
    
    if enable_user_input == True:   
        confirm_settings = questionary.confirm("Save these settings and exit?", style=custom_style).ask()
        return confirm_settings

# setup dashboard
def sheetsetup(user_inputs):
    
    creds_path = Path('C:/Users/jamal/Documents/_trading/dca-bot/')
    creds_to_open = creds_path / 'creds.json'
    
    scope = ["https://spreadsheets.google.com/feeds",'https://www.googleapis.com/auth/spreadsheets',"https://www.googleapis.com/auth/drive.file","https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_name(creds_to_open, scope)
    gclient = gspread.authorize(creds)

    ss = gclient.open(user_inputs['sheet_name'])
    dashboard = ss.worksheet('Dashboard')
    
    return ss, dashboard

# calculate risks
def risk(dashboard, user_inputs):
    
    # create coin + risk dict
    for k, v in user_inputs['dca_details'].items():
        coin_cell = dashboard.find((k), in_column=0)
        coin_values = dashboard.row_values(coin_cell.row)
        
        try:
            user_inputs['dca_details'][k].update({"risk" : float(coin_values[dashboard.find('Risk').col-1])})
        except ValueError as e:
            print("Value Error: Check Google Sheet Risk Values")
            exit()
    
    return user_inputs['dca_details']
  
# calculate dca amounts based on risk and create dict
def dca_order_dict(user_inputs, today_int, today):
    
    for k, v in user_inputs['dca_details'].items():
        
        risk = v['risk']
        dca_base = v['dca_amount']
        
        if today_int == v['dca_day_int']:
            
            print(k)
            
            if risk >= 0.5:
                print(f"\n{k} is greater than or equal to 0.5 risk, skipping DCA.")
            elif 0.4 <= risk < 0.5:
                dca_amount = dca_base*1
                print(f"\n{k} Risk = {risk}\nBuying ${dca_amount} of {k}\n")
                user_inputs['dca_details'][k].update({'dca_amount' : dca_amount, 'base' : user_inputs['base_currency']})
            elif 0.3 <= risk < 0.4:
                dca_amount = dca_base*(1+user_inputs['risk_band_multiplier_step'])
                print(f"\n{k} Risk = {risk}\nBuying ${dca_amount} of {k}\n")
                user_inputs['dca_details'][k].update({'dca_amount' : dca_amount, 'base' : user_inputs['base_currency']})
            elif 0.2 <= risk < 0.3:
                dca_amount = dca_base*(2+user_inputs['risk_band_multiplier_step'])
                print(f"\n{k} Risk = {risk}\nBuying ${dca_amount} of {k}\n")
                user_inputs['dca_details'][k].update({'dca_amount' : dca_amount, 'base' : user_inputs['base_currency']})
            elif 0.1 <= risk < 0.2:
                dca_amount = dca_base*(3+user_inputs['risk_band_multiplier_step'])
                print(f"\n{k} Risk = {risk}\nBuying ${dca_amount} of {k}\n")
                user_inputs['dca_details'][k].update({'dca_amount' : dca_amount, 'base' : user_inputs['base_currency']})
            elif 0 <= risk < 0.1:
                dca_amount = dca_base*(4+user_inputs['risk_band_multiplier_step'])
                print(f"\n{k} Risk = {risk}\nBuying ${dca_amount} of {k}\n")
                user_inputs['dca_details'][k].update({'dca_amount' : dca_amount, 'base' : user_inputs['base_currency']})
        else:
            print(f'\n{k} DCA day is {v["dca_day"].capitalize()} today is {today}. Skipping {k} DCA.\n')

    return user_inputs['dca_details']

# buy coins
def dca_buy(api_key, api_secret, dca_order_details, client, temp_order_resp, test, today_int):
    
    orders = {}
    
    for k, v in dca_order_details.items():
        
        if today_int == v['dca_day_int']:
            
            symbol = k + v['base']
            dca_amount = v['dca_amount']
            
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
            
            print(f'\n{k} Buy Order:\n {buy_order}')
            
            order = {f'{k}' : {'id' : buy_order['orderId'],
                    'symbol' : buy_order['symbol'],
                    'price' : buy_order['fills'][0]['price'],
                    'qty' : buy_order['executedQty'],
                    'cost' : buy_order['cummulativeQuoteQty'],
                    'time' : buy_order['transactTime']}}
            
            orders.update(order)
        
    return orders

# update dca dashboard with order information
def sheet_update(orders, ss, dca_order_details):
    
    print(f'\nUpdating {ss.title}...')
    
    for k, v in orders.items():
        ws = ss.worksheet(f'DCA Tracker: {k}')
        
        # looks for empty row based on values appearing in 1st N columns
        def next_available_row(ws, cols_to_sample=2):
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
        ws.update_cell(row, cols['date_col'], date.utcfromtimestamp(orders[f'{k}']['time']/1000).strftime('%d/%M/%Y %H:%M:%S').split()[0])
        ws.update_cell(row, cols['time_col'], date.utcfromtimestamp(orders[f'{k}']['time']/1000).strftime('%d/%M/%Y %H:%M:%S').split()[1])
        ws.update_cell(row, cols['price_col'], orders[f'{k}']['price'])
        ws.update_cell(row, cols['risk_col'], dca_order_details[k]['risk'])
        ws.update_cell(row, cols['cost_col'], orders[f'{k}']['cost'])
        ws.update_cell(row, cols['qty_col'], orders[f'{k}']['qty'])
        
    print(f'\n{ss.title} updated. Exiting\n')

# validate sheet
def sheet_validate(ss, dashboard, user_inputs):

    for k in user_inputs['dca_details']:
        
        try:
            dashboard.findall(k)
        except:
            print(f"\nError: Create Dashboard Row {k}")
            exit()
        
        try:
            ss.worksheet(f'DCA Tracker: {k}')
        except:
            print(f"\nError: Create DCA Tracker Sheet {k}")
            exit()   

# check config
def check_for_config():

    # check if config exists
    try:
        config_path = Path('C:/Users/jamal/Documents/_trading/dca-bot/')
        file_to_open = config_path / 'config.json'
        config = open(file_to_open)
        enable_user_input = False
    except IOError:
        enable_user_input = True
        config = None
    
    return enable_user_input, config

# save config
def save_config(confirm_settings, user_inputs):
    
    # write settings if confirmed 
    if confirm_settings == True:
        with open ('config.json', 'w') as f:
            json.dump(user_inputs, f)
    else:
        run()    

# edit config
def edit_config(time_out, config):
    
    try:
        enable_user_input = False
        user_inputs = json.load(config)
        print_dca_settings(user_inputs, enable_user_input)
        edit = inputimeout(prompt=f"Edit settings? You have {time_out} seconds until continuing with current setttings [Y/N].", timeout=time_out)
    except TimeoutOccurred:
        edit = 'N'
    
    edit = edit.capitalize()
    
    if edit == 'Y':
        print('\nEdit settings & Exit...\n')
        enable_user_input = True
        user_inputs = set_settings(enable_user_input)
        print('\nExiting. Run the bot again to use these new settings.')
        exit()
    elif edit == 'N':
        print('\nUsing existing settings...\n')
    
    return user_inputs

# set settings
def set_settings(enable_user_input):
    user_inputs = usersettings(enable_user_input)
    confirm_settings = print_dca_settings(user_inputs, enable_user_input)
    save_config(confirm_settings, user_inputs)
    
    return user_inputs

# run bot
def run():

    enable_user_input, config = check_for_config()
    
    if enable_user_input == True:
        user_inputs = set_settings(enable_user_input)
    else:
        user_inputs = edit_config(time_out, config)

    if today in user_inputs['dca_days']:
        ss, dashboard = sheetsetup(user_inputs)
        sheet_validate(ss, dashboard, user_inputs)
        dca_order_details = risk(dashboard, user_inputs)
        dca_order_details = dca_order_dict(user_inputs, today_int, today)
        orders = dca_buy(api_key, api_secret, dca_order_details, client, temp_order_resp, test, today_int)
        sheet_update(orders, ss, dca_order_details)
    else:
        print('Today is not a DCA Day, DCA days are', end=" ")
        print(*user_inputs['dca_days'], sep=', ', end=" ")
        print(f'today is {today}.')
   
    exit()

print('\n===== DCA Bot 1.0 =====\n')  
run()