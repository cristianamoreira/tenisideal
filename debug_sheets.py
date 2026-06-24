import gspread
from google.oauth2.service_account import Credentials

SHEET_ID = "1SrOeEOwQsR5BcNcVni0W20c5npazOn5iKHpIr3Zy42Y"

creds = Credentials.from_service_account_file(
    'credenciais.json',
    scopes=['https://www.googleapis.com/auth/spreadsheets']
)
gc = gspread.authorize(creds)
sheet = gc.open_by_key(SHEET_ID)
ws = sheet.worksheets()[0]

print(f"Aba: {ws.title}\n")
print("PRIMEIRAS 3 LINHAS:\n")

all_values = ws.get_all_values()
for i, row in enumerate(all_values[:3]):
    print(f"Linha {i}: {row}\n")

print("\nCOLUNAS COM VALORES (primeiras 10):")
headers = all_values[0]
for i, h in enumerate(headers[:10]):
    print(f"  [{i}] '{h}'")
