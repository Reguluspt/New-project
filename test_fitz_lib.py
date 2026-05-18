import fitz
print(f"fitz version: {fitz.version}")
doc = fitz.open()
page = doc.new_page()
page.insert_text((100, 100), "Hello World")
doc.save("test_fitz.pdf")
doc.close()
print("Success")
