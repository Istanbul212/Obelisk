from audioop import add
import hashlib
import binascii
import rsa
from datetime import datetime
from os.path import exists
from sys import argv

# gets the hash of a file; from https://stackoverflow.com/a/44873382
def hashFile(filename):
    h = hashlib.sha256()
    with open(filename, 'rb', buffering=0) as f:
        for b in iter(lambda : f.read(128*1024), b''):
            h.update(b)
    return h.hexdigest()

# given an array of bytes, return a hex reprenstation of it
def bytesToString(data):
    return binascii.hexlify(data)

# given a hex reprensetation, convert it to an array of bytes
def stringToBytes(hexstr):
    return binascii.a2b_hex(hexstr)

# Load the wallet keys from a filename
def loadWallet(filename):
    with open(filename, mode='rb') as file:
        keydata = file.read()
    privkey = rsa.PrivateKey.load_pkcs1(keydata)
    pubkey = rsa.PublicKey.load_pkcs1(keydata)
    return pubkey, privkey

# save the wallet to a file
def saveWallet(pubkey, privkey, filename):
    # Save the keys to a key format (outputs bytes)
    pubkeyBytes = pubkey.save_pkcs1(format='PEM')
    privkeyBytes = privkey.save_pkcs1(format='PEM')
    # Convert those bytes to strings to write to a file (gibberish, but a string...)
    pubkeyString = pubkeyBytes.decode('ascii')
    privkeyString = privkeyBytes.decode('ascii')
    # Write both keys to the wallet file
    with open(filename, 'w') as file:
        file.write(pubkeyString)
        file.write(privkeyString)
    return

def genesis():
    quote = 'With great power, comes great responsibility.'
    with open('block_0.txt', mode='w') as file:
        file.write(quote)
    print("Genesis block created in 'block_0.txt'")
    return

def generate(filename):
    saveWallet(*rsa.newkeys(1024), filename)
    print("New wallet generated in '"+filename+"' with signature "+address(filename))
    return

def address(filename):
    pubkey, privkey = loadWallet(filename)
    h = hashlib.sha256()
    h.update(pubkey.save_pkcs1(format='PEM').decode('ascii').encode('utf-8'))
    return h.hexdigest()[:16]

def address_cmd(filename):
    pubkey, privkey = loadWallet(filename)
    h = hashlib.sha256()
    h.update(pubkey.save_pkcs1(format='PEM').decode('ascii').encode('utf-8'))
    print(h.hexdigest()[:16])
    return

def fund(dest_add, amt, filename):
    statement = 'From: Voldemort\nTo: '+dest_add+'\nAmount: '+amt+'\nDate: '+str(datetime.now())
    with open(filename, 'w') as file:
        file.write(statement)
    return

def transfer(from_name, to_address, amount, filename):
    time_now = str(datetime.now())
    statement = 'From: '+address(from_name)+'\nTo: '+to_address+'\nAmount: '+amount+'\nDate: '+time_now+'\n'
    signature = rsa.sign(statement.encode('utf-8'), loadWallet(from_name)[1], 'SHA-256')
    with open(filename, 'w') as file:
        file.write(statement)
        file.write('\n'+bytesToString(signature).decode('utf-8'))
    print('Transferred '+amount+' from '+from_name+' to '+to_address+" and the statement to '"+filename+"' on "+time_now)
    return

def balance(address):
    bal = 0
    i = 1
    filename = 'block_'+str(i)+'.txt'
    while exists(filename):
        with open(filename, mode='r') as file:
            lines = file.readlines()
        for l in lines[2:-2]:
            from_add, amt, to_add = l.split()[0:5:2]
            if from_add == address:
                bal -= float(amt)
            elif to_add == address:
                bal += float(amt)
        i += 1
        filename = 'block_'+str(i)+'.txt'
    if exists('ledger.txt'):
        with open('ledger.txt', mode='r') as file:
            lines = file.readlines()
        for l in lines:
            from_add, amt, to_add = l.split()[0:5:2]
            if from_add == address:
                bal -= float(amt)
            elif to_add == address:
                bal += float(amt)
    # print('The balance for wallet '+address+' is: '+str(bal))
    print(bal)
    return bal

def statement_to_record(statement):
    statement = statement.split()
    return statement[1]+' transferred '+statement[5]+' to '+statement[3]+' on '+''.join(statement[7:])+'\n'

def verify(filename, statement):
    with open(statement, mode='r') as file:
        lines = file.readlines()
    if lines[0].split()[1] == 'Voldemort' or (rsa.verify(''.join(lines[:4]).encode('utf-8'), stringToBytes(lines[-1]), loadWallet(filename)[0]) and balance(address(filename)) >= float(lines[2].split()[1])):
        with open('ledger.txt', mode='a') as file:
            file.write(statement_to_record(''.join(lines[:4])))
        print("The transaction in file '"+statement+"' with wallet '"+filename+"' is valid, and was written to the ledger")
    else:
        print('The transaction failed')

def mine(difficulty):
    target = '0'*difficulty
    nonce = 0
    cnt = 0

    while(exists('block_'+str(cnt)+'.txt')):
        cnt += 1
    
    with open('block_'+str((cnt-1))+'.txt', mode='r') as file:
        h = hashlib.sha256()
        h.update(file.read().encode('utf-8'))
    if exists('ledger.txt'):
        with open('ledger.txt', mode='r') as file:
            lines = file.read()
    else:
        lines = ''
    
    block = h.hexdigest()+'\n\n'+lines+'\n'*bool(lines)

    attempt = block+'nonce: '+str(nonce)
    h = hashlib.sha256()
    h.update(attempt.encode('utf-8'))

    while(h.hexdigest()[:difficulty] != target):
        nonce += 1
        attempt = block+'nonce: '+str(nonce)
        h = hashlib.sha256()
        h.update(attempt.encode('utf-8'))
    
    with open('block_'+str(cnt)+'.txt', mode='w') as file:
        file.write(attempt)
    with open('ledger.txt', mode='w') as file:
        pass

    print('Ledger transactions moved to block_'+str(cnt)+'.txt and mined with difficulty '+str(difficulty)+' and nonce '+str(nonce))
    return

def validate():
    block = 1
    with open('block_0.txt', mode='r') as file:
            h = hashlib.sha256()
            h.update(file.read().encode('utf-8'))
    while(exists('block_'+str(block)+'.txt')):
        with open('block_'+str(block)+'.txt', mode='r') as file:
            if h.hexdigest()+'\n' != file.readline():
                print('False')
                return
            file.seek(0)
            h = hashlib.sha256()
            h.update(file.read().encode('utf-8'))
        block += 1
    print('True')

def main():
    fc = argv[1]
    if fc == 'genesis':
        genesis()
    elif fc == 'generate':
        generate(argv[2])
    elif fc == 'address':
        address_cmd(argv[2])
    elif fc == 'fund':
        fund(argv[2], argv[3], argv[4])
    elif fc == 'transfer':
        transfer(argv[2], argv[3], argv[4], argv[5])
    elif fc == 'balance':
        balance(argv[2])
    elif fc == 'verify':
        verify(argv[2], argv[3])
    elif fc == 'mine':
        mine(int(argv[2]))
    elif fc == 'validate':
        validate()
    return

if __name__ == "__main__":
    main()