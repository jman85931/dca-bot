import gspread
from oauth2client.service_account import ServiceAccountCredentials
from pprint import pprint

def usersettings():
    
    user_inputs = {}
    
    user_inputs['dca_base_amount'] = 100
    user_inputs['dca_coins'] = ["BTC", "ETH", "MATIC"]
    user_inputs['dca_percentage_splits'] = [50, 50]
    user_inputs['risk_band_multiplier'] = 1.2
    
    return user_inputs

def sheetsetup():
    scope = ["https://spreadsheets.google.com/feeds",'https://www.googleapis.com/auth/spreadsheets',"https://www.googleapis.com/auth/drive.file","https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_name("creds.json", scope)
    client = gspread.authorize(creds)

    sheet = client.open("DCA Dashboard v1.0").sheet1
    
    return sheet

def buy(coin):
    print(f'Market Buying: {coin}')
    
user_inputs = usersettings()
sheet = sheetsetup()

for i in user_inputs['dca_coins']:
    coin_cell = sheet.find((i), in_column=0)
    coin_row = coin_cell.row
    print(sheet.row_values(coin_row))
