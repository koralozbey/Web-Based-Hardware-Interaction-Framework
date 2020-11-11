import subprocess

def ip_find():
    output = subprocess.check_output(['hostname','-I'])
    output = output.decode().split(' ')
    adress = None
    for ip in output:
        if ip != '\n':
            adress = ip
    if adress == None:
        while True:
            print("Error: IP adress not found close the program!")
            time.sleep(1)
    return adress
