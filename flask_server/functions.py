import os
import glob

ALLOWED_EXTENSIONS = {'ipynb', 'pdf', 'png'}

def ip_find():
    #output = subprocess.check_output(['hostname','-I']).decode().split(' ')
    output = os.popen('hostname -I').read().split(' ')
    adress = None
    for ip in output:
        if ip != '\n':
            adress = ip
    if adress == None:
        while True:
            print("Error: IP adress not found close the program!")
            time.sleep(1)
    return adress
    
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.',1)[1].lower() in ALLOWED_EXTENSIONS

def setup_infos(usbport):
    try:
        os.stat(usbport)
    except OSError:
        return -1,-1
    
    #output1 = subprocess.check_output(f"udevadm info -a -n /dev/{usbport}".split(' ')).decode()
    output1 = os.popen(f"udevadm info -a -n {usbport}").read()
    look = output1.find('looking')
    blocks = []

    while look != -1:
        output1 = output1[look+1:]
        look = output1.find('looking')
        if look != -1:
            blocks.append(output1[:look])
            
    if blocks == []:
        return -1, -1

    product_id,product_serial = -1, -1
    for block in blocks:
        if block.find('ATTRS{manufacturer}=="Arduino') != -1:
            start = block.find('ATTRS{idProduct}=="') + len('ATTRS{idProduct}=="')
            end = block.find('"',start)
            product_id = block[start:end]
            start = block.find('ATTRS{serial}=="') + len('ATTRS{serial}=="')
            end = block.find('"',start)
            product_serial = block[start:end]
    
    return product_id,product_serial
    
def tty_ports():
    ports = []
    for name in glob.glob('/dev/ttyACM*'):
        ports.append(name)
    return ports
