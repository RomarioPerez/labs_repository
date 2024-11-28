import bcrypt

texto = "insert password"
x = bcrypt.hashpw(texto.encode('utf8'),bcrypt.gensalt())
print(f"[{x}]")
y = bcrypt.hashpw(texto.encode('utf8'),bcrypt.gensalt(10))
print(f"[{y}]")

if (x == y):
    print(True)
else:
    print(False)