from email.message import EmailMessage
msg = EmailMessage()
msg.set_content('text')
msg.add_alternative('<html><body><img src="cid:cen_value_logo"></body></html>', subtype='html')
msg.get_payload()[1].add_related(b'123', maintype='image', subtype='png', cid='<cen_value_logo>')
print(msg.as_string())
