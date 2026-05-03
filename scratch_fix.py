with open('views/entry_form.py', 'r', encoding='utf-8') as f:
    content = f.read()

target = '        "owner_name": owner_name,\n        "tax_code": tax_code,'
if target not in content:
    target = '        "owner_name": owner_name,\r\n        "tax_code": tax_code,'

replacement = '        "owner_name": owner_name,\n        "owner_address": owner_address,\n        "owner_citizen_id": citizen_id,\n        "tax_code": tax_code,'

if target in content:
    content = content.replace(target, replacement)
    with open('views/entry_form.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print("Success")
else:
    print("Not found")
