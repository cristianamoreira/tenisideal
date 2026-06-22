import gspread
import unicodedata
import re
import hashlib
from google.oauth2.service_account import Credentials

SHEET_ID = "1SrOeEOwQsR5BcNcVni0W20c5npazOn5iKHpIr3Zy42Y"
CRED_PATH = "credenciais.json"

# List of stores to map
STORES = ["amazon", "nike", "adidas", "mizuno", "olympikus", "netshoes"]

def slugify(marca: str, nome: str, versao: str = "") -> str:
    base = f"{marca} {nome} {versao}".strip()
    s = unicodedata.normalize('NFKD', base).encode('ASCII', 'ignore').decode().lower()
    s = re.sub(r'[^a-z0-9]+', '-', s).strip('-')
    # Use MD5 hash suffix to ensure uniqueness
    suffix = hashlib.md5(s.encode()).hexdigest()[:4]
    return f"{s}-{suffix}"

def migrate():
    print("Connecting to Google Sheets...")
    creds = Credentials.from_service_account_file(
        CRED_PATH,
        scopes=["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"],
    )
    client = gspread.authorize(creds)
    
    try:
        spreadsheet = client.open_by_key(SHEET_ID)
        worksheet = spreadsheet.sheet1
        print(f"Connected to sheet: {spreadsheet.title} -> {worksheet.title}")
    except Exception as e:
        print(f"Error connecting: {e}")
        return

    # Load existing rows including header
    all_values = worksheet.get_all_values()
    if not all_values:
        print("Sheet is empty.")
        return
    
    print(f"First row (row 1): {all_values[0][:10]}")
    if len(all_values) > 1:
        print(f"Second row (row 2): {all_values[1][:10]}")
    
    # We determine the header row:
    is_two_row_header = False
    if len(all_values) > 1:
        row2_lower = [str(x).lower().strip() for x in all_values[1]]
        # Check for typical headers in Row 2
        two_row_indicators = ["gender", "marca", "nome do tênis", "url_imagem", "preco_oficial", "preco_netshoes"]
        if any(indicator in row2_lower for indicator in two_row_indicators):
            is_two_row_header = True

    if is_two_row_header:
        header = all_values[1]
        rows = all_values[2:]
        print("Detected two-row header! Using Row 2 as the column headers.")
    else:
        header = all_values[0]
        rows = all_values[1:]
        print("Using Row 1 as the column headers.")

    print(f"Loaded {len(rows)} existing rows. Original columns: {header}")

    # Build mapping from column name to index
    col_map = {name.strip().lower(): idx for idx, name in enumerate(header)}

    # Define the new ordered schema
    base_cols = [
        "product_id", "ativo", "marca", "nome", "versao", 
        "sexo", "img", "emoji", "tags", "budget", 
        "levels", "pisadas", "terrenos", "priors", "reason"
    ]
    
    store_cols = []
    for store in STORES:
        store_cols.extend([
            f"link_{store}",
            f"preco_{store}",
            f"preco_pix_{store}",
            f"parcelas_{store}"
        ])
    
    new_schema = base_cols + store_cols
    print(f"New schema has {len(new_schema)} columns.")

    new_rows = []
    # Map each row to the new schema
    for row in rows:
        # Pad row with empty strings if it has fewer elements than headers
        if len(row) < len(header):
            row += [""] * (len(header) - len(row))
            
        def get_val(col_names):
            if isinstance(col_names, str):
                col_names = [col_names]
            for col_name in col_names:
                key = col_name.strip().lower()
                if key in col_map:
                    idx = col_map[key]
                    if idx < len(row):
                        return row[idx].strip()
            return ""

        # Base metadata mapping with correct aliases
        sexo = get_val(["gender", "sexo"]) or "unissex"
        marca = get_val(["brand", "marca"])
        nome = get_val(["name", "nome", "nome do tênis"])
        versao = get_val("versao")
        img = get_val(["images", "img", "url_imagem"])
        emoji = get_val("emoji") or "👟"
        tags = get_val("tags")
        budget = get_val("budget")
        levels = get_val("levels")
        pisadas = get_val("pisadas")
        terrenos = get_val("terrenos")
        priors = get_val("priors")
        reason = get_val("reason")
        
        ativo = "sim"
        product_id = slugify(marca, nome, versao)

        # Build raw row matching the new_schema order
        row_dict = {col: "" for col in new_schema}
        row_dict["product_id"] = product_id
        row_dict["ativo"] = ativo
        row_dict["marca"] = marca
        row_dict["nome"] = nome
        row_dict["versao"] = versao
        row_dict["sexo"] = sexo
        row_dict["img"] = img
        row_dict["emoji"] = emoji
        row_dict["tags"] = tags
        row_dict["budget"] = budget
        row_dict["levels"] = levels
        row_dict["pisadas"] = pisadas
        row_dict["terrenos"] = terrenos
        row_dict["priors"] = priors
        row_dict["reason"] = reason

        # Map links
        row_dict["link_amazon"] = get_val(["amazon_link", "link_amazon"])
        row_dict["link_netshoes"] = get_val(["netshoes_link", "link_netshoes"])
        
        # Mapeamento do link oficial
        oficial_link = get_val(["awin_link", "link_oficial"])
        brand_lower = str(marca).lower()
        if brand_lower in STORES and brand_lower != "amazon" and brand_lower != "netshoes":
            row_dict[f"link_{brand_lower}"] = oficial_link

        # Map prices
        # Amazon price
        row_dict["preco_amazon"] = get_val(["price", "preco_amazon"])
        row_dict["preco_netshoes"] = get_val(["preco_netshoes"])
        
        # Official price and installments -> mapped to brand's store
        main_price = get_val(["price", "preco_oficial"])
        if brand_lower in STORES and brand_lower != "amazon" and brand_lower != "netshoes":
            row_dict[f"preco_{brand_lower}"] = main_price
            row_dict[f"parcelas_{brand_lower}"] = get_val("parcelas_oficial")

        # Create row list in new_schema order
        new_row_list = [row_dict[col] for col in new_schema]
        new_rows.append(new_row_list)

    # 1️⃣ Unmerge all cells in the sheet to prevent empty header columns
    print("Unmerging all cells in the sheet...")
    unmerge_body = {
        "requests": [
            {
                "unmergeCells": {
                    "range": {
                        "sheetId": worksheet.id,
                        "startRowIndex": 0,
                        "endRowIndex": 1000,
                        "startColumnIndex": 0,
                        "endColumnIndex": 50
                    }
                }
            }
        ]
    }
    try:
        spreadsheet.batch_update(unmerge_body)
        print("Successfully unmerged all cells.")
    except Exception as e:
        print(f"Warning: could not unmerge: {e}")

    # 2️⃣ Clear sheet and write flat values
    print("Clearing sheet and writing new schema...")
    values = [new_schema] + new_rows
    worksheet.clear()
    worksheet.update("A1", values)
    print("Planilha migrada com sucesso!")

if __name__ == "__main__":
    migrate()
