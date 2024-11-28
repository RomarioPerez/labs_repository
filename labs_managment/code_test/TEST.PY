str = "10,2,5,a,c, *4"
list_arg = str.split(",")
list_arg = [int(elemento) for elemento in list_arg if elemento.isdigit() and int(elemento) < 30]
for arg in list_arg:
  if int(arg) <30 and int(arg)>0:
    print("Enviado a ", arg)
