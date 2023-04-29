import socket
import os
import math
import threading
import time
import random
import ntpath
from flags import flags

key = "1011"
chosen = None
max_size = None
role = None
ip_port = None
address_to = None
save_path = "."



pocet_prenesenych = 0


print("Sender / Reciever")
print("---------------------------------------------------------------------------------")
server_client = input("s/r -> ")


print("Zvolte ip adresu a port","(localhost: ","127.0.0.1",20001,")     reciever dava len 0 a port")
print("---------------------------------------------------------------------------------")
ip_port = input(" -> ")
ip_port = ip_port.split()
ip_port[1] = int(ip_port[1])
print(ip_port)

host = ip_port[0]
port = ip_port[1]
connection = socket.socket(family=socket.AF_INET, type=socket.SOCK_DGRAM)  


def sender_funkcia():
    global chosen,max_size
    print("Zvolte max velkost fragmentu v B","(mensie rovne ako 1452 na lan)")
    print("---------------------------------------------------------------------------------")
    max_size = input(" -> ")
    max_size = int(max_size)

    print("Zvolte subor ktory budete odosielat alebo zadajte absolutnu cestu")
    print("---------------------------------------------------------------------------------")
    files = [f for f in os.listdir('.') if os.path.isfile(f)]
    for f in files:
        print(f)

    print("---------------------------------------------------------------------------------")
    print("Na ukoncenie komunikacie napise \"q\" alebo \"swap\"")
    chosen = input("q/swap/cesta/sprava: -> ")

def reciever_funkcia():
    global save_path
    print("Zvolte cestu kde subor ulozite alebo swap alebo stlacte enter pre prijimanie sprav")
    print("---------------------------------------------------------------------------------")
    save_path = input(" -> ")

def bitstring_to_bytes(s):
    v = int(s, 2)
    b = bytearray()
    while v:
        b.append(v & 0xff)
        v >>= 8
    return bytearray(b[::-1])



def access_bit(data, num):
    base = int(num // 8)
    shift = int(num % 8)
    return str((data[base] >> shift) & 0x1)

def create_error(data):
    if random.randrange(0, 5) < 1:
        data = list(data)
        data[random.randrange(0, len(data))] = "1"

    return "".join(data)


def xor(a, b):
    result = []
    for i in range(1, len(b)):
        if a[i] == b[i]:
            result.append('0')
        else:
            result.append('1')
    return ''.join(result)


def mod2div(divident, divisor):
    pick = len(divisor)
    tmp = divident[0 : pick]
 
    while pick < len(divident):
 
        if tmp[0] == '1':
            tmp = xor(divisor, tmp) + divident[pick]
 
        else: 
            tmp = xor('0'*pick, tmp) + divident[pick]
 
        pick += 1
    if tmp[0] == '1':
        tmp = xor(divisor, tmp)
    else:
        tmp = xor('0'*pick, tmp)
    checkword = tmp
    return checkword


def encodeData(data, key):
    data_bits = "".join([access_bit(data,i) for i in range(len(data)*8)])
    data_bits = data_bits[::-1]
    l_key = len(key)

    appended_data = data_bits + '0'*(l_key-1)
    #appended_data = create_error(appended_data) # <------------------------------------ vytvaranie chyby
    remainder = mod2div(appended_data, key)
 
    return remainder


def decodeData(data, crc, key):
    data_bits = "".join([access_bit(data,i) for i in range(len(data)*8)])
    data_bits = data_bits[::-1]
    appended_data = data_bits + crc
    remainder = mod2div(appended_data, key)
 
    return remainder




class Sender:
    def __init__(self,file_path):
        self.file_path = file_path
        self.conn = None
        self.address = None

        self.timer = 6
        self.ka = None
        self.kill = False

    def start(self):
        global address_to,pocet_prenesenych
        self.conn = connection
        if address_to:
            self.conn.sendto(self.header(bytearray(),0,0,bytearray(int(0).to_bytes(1 , "little")),0),address_to)
        else:
            self.conn.sendto(self.header(bytearray(),0,0,bytearray(int(0).to_bytes(1 , "little")),0),(host, port)) 
        flag = 5
        pocet_prenesenych += 6
        while(flag == 5 or flag == 6):

            frag = self.conn.recvfrom(1460)

            flag =     int.from_bytes(frag[0][:1],"little")

            print(flags[flag])

        if flag == 0:
            pocet_prenesenych += 6
            self.timer = 20

            self.conn.sendto(self.header(bytearray(),0,0,bytearray(int(0).to_bytes(1 , "little")),2),frag[1])
            pocet_prenesenych += 6
            address_to = frag[1]
            self.address = frag[1]
            print("------------------> Conection created <------------------")
            self.ka_thread()
            if chosen[:7] == "sprava:":
                self.send_message(frag[1])
            else:
                self.send_file(frag[1])

        else:
            self.close()


    def swap(self):
        global role
        self.timer = 60000
        self.conn.sendto(self.header(bytearray(),0,0,bytearray(int(0).to_bytes(1 , "little")),6),self.address)
        reciever_funkcia()
        client = Reciever()
        role = client


    def close(self):
        self.kill = True
        self.conn.close()
        self.conn = None
        print("------------------> Conection closed  <------------------")


    def keep_alive(self):
        self.timer = 6
        self.ack_timer = 2
        odpocitavadlo = 5
        self.message_to_send_again = None
        while(self.timer > 1):
            if self.kill:
                return
            if self.ack_timer < 1:
                print("posielam lebo neprislo ack")
                self.conn.sendto(self.message_to_send_again,self.address) 
                self.ack_timer = 2
            odpocitavadlo -= 1
            if odpocitavadlo == 0:
                self.conn.sendto(self.header(bytearray(),0,0,bytearray(int(0).to_bytes(1 , "little")),5),self.address)
                odpocitavadlo = 5
            self.timer -= 1
            self.ack_timer -= 1
            time.sleep(1)
            
        self.close()

    def ka_thread(self):
        self.ka = threading.Thread(target=self.keep_alive)
        self.ka.start()

    def header(self,byte,sum_frag,frag,crc,flag):
        byte[0:0] = int(sum_frag).to_bytes(2 ,'little')
        byte[0:0] = int(frag).to_bytes(2 ,'little')
        byte[0:0] = crc
        byte[0:0] = int(flag).to_bytes(1, 'little')

        return byte

    def header_recieve(self,data):
        return int.from_bytes(data[0][:1],"little"),int.from_bytes(data[0][1:2],"little"),int.from_bytes(data[0][2:4],"little")

    def handshake(self,address):
        global pocet_prenesenych
        self.conn.sendto(self.header(bytearray(),0,0,bytearray(int(0).to_bytes(1 , "little")),4),address)
        pocet_prenesenych += 6

        
        data = self.conn.recv(1460)
        flag = int.from_bytes(data[:1],"little")

        while(flag != 4):
            data = self.conn.recv(1460)
            flag = int.from_bytes(data[:1],"little")

        print(flags[flag])
        pocet_prenesenych += 6
        if flag == 4:

            self.conn.sendto(self.header(bytearray(),0,0,bytearray(int(0).to_bytes(1 , "little")),2),address)
            pocet_prenesenych += 6
            data = self.conn.recv(1460)
            flag = int.from_bytes(data[:1],"little")

            print(flags[flag])

            if flag == 2:
                pocet_prenesenych += 6
                self.timer = 500
                print("------------------> Sending succsessfull <------------------")
                print(chosen)
                data = self.conn.recv(1460)
                pocet_prenesenych += 6
                flag = int.from_bytes(data[:1],"little")
                while(True):
                    if flag == 2:
                        break
                    if flag == 6:
                        self.swap()
                        return

                    data = self.conn.recv(1460)
                    flag = int.from_bytes(data[:1],"little")
                    print(flags[flag])
                sender_funkcia()
                if chosen == "q":
                    self.close()
                elif chosen == "swap":
                    self.kill = True
                    self.swap()
                elif chosen[:7] == "sprava:":
                    role.send_message(address)
                else:
                    role.send_file(address)
                

    def send_message(self,address):
        global pocet_prenesenych
        self.timer = 6
        i = 0
        message = chosen[7:]
        flag = 5
        while(len(message)>(i+1)*max_size):
            if flag == 5:
                self.timer = 6
                print(flags[flag])
            self.ack_timer = 5
            self.conn.sendto(self.header(bytearray(str(message[i*max_size:(i+1)*max_size]).encode()),math.ceil(len(message)/max_size),i + 1,int(0).to_bytes(1 ,'little'),7),address)
            pocet_prenesenych += 6
            data = self.conn.recvfrom(1460)
            flag,crc,frag_num = self.header_recieve(data)
            if flag == 2 and frag_num > 0:
                pocet_prenesenych += 6
                print(flags[flag],frag_num)
                i += 1
        self.ack_timer = 5000000
        self.handshake(address)



    def send_file(self,address):
        global pocet_prenesenych
        flag = 1

        self.timer = 300
        fileR = open(chosen, "rb")
        
        frag = 1

        fileR.seek(0, os.SEEK_END)
        size_of_file = fileR.tell()
        sum_frag = math.ceil(size_of_file / max_size) + 1
        print("We will send", sum_frag, "fragments")
        fileR.seek(0)

        byte = bytearray(fileR.read(max_size))
        

        while byte:
            if flag == 5:
                self.timer = 300
            else:
                message = byte.copy()

                crc = encodeData(message,key)
                bytes_crc = bitstring_to_bytes(crc)

                
                bytes_crc.extend(int(0).to_bytes(1-len(bytes_crc) ,'little'))
                pridat = 0
                # if random.randrange(0,10) == 1: -------------------------------------------------------------- > zle poradove cislo
                #     pridat = 1

                message = self.header(message,sum_frag,frag + pridat,bytes_crc,1)
                self.message_to_send_again = message
                self.conn.sendto(message,address) 
                pocet_prenesenych += 6 

            try:
                data = self.conn.recvfrom(1460)
            except:
                None
            flag,crc,frag_num = self.header_recieve(data)


            if flag == 2:
                pocet_prenesenych += 6   
                self.ack_timer = 3
                print(flags[flag],frag,"         ",math.floor(frag/sum_frag * 100),"%          ",len(message) * frag,"/",size_of_file," Bytes              ", len(message) + 8 + 34," Bytes")             
                
                byte = bytearray(fileR.read(max_size))
                
            
                frag += 1

            elif flag == 3:
                print(flags[flag],frag)

            else:
                print(flags[flag])

        self.ack_timer = 1000
        fileR.close()
        self.conn.sendto(self.header(bytearray(ntpath.basename(chosen).encode()),sum_frag,frag,int(0).to_bytes(1 ,'little'),1),address)
        pocet_prenesenych += 6 
        data = self.conn.recvfrom(1460)
        frag_num = int.from_bytes(data[0][2:4],"little")
        print(flags[flag],frag_num)
        self.handshake(address)


################################################################################################################################################################
################################################################################################################################################################
################################################################################################################################################################
################################################################################################################################################################
################################################################################################################################################################
################################################################################################################################################################
################################################################################################################################################################



class Reciever:
    def __init__(self):
        self.file_path = "ERROR"
        self.conn = None
        self.export_file = bytearray()
        self.kill = False
        self.swap = 0

    def start(self):
        global address_to,pocet_prenesenych
        self.conn  = connection

        flag = 5
        while(flag == 5):
            frag = self.conn.recvfrom(1460)
            flag =     int.from_bytes(frag[0][:1],"little")
            print(flags[flag])
            self.address = frag[1]
            address_to = frag[1]

        if flag == 0:
            pocet_prenesenych += 6
            self.conn.sendto(self.header(bytearray(),0,0,0,0),self.address) 
            pocet_prenesenych += 6
            frag = self.conn.recvfrom(1460)
            flag =     int.from_bytes(frag[0][:1],"little")
            
            if flag == 2:
                print(flags[flag])
                pocet_prenesenych += 6
                print("------------------> Conection created <------------------")
                self.ka_thread()
                self.recieve_file(self.address)
            else:
                self.close()
        else:
            self.close()



        

    def close(self):
        global chosen
        self.kill = True
        self.conn.close()
        self.conn = None
        chosen = "q"
        print("------------------> Conection closed  <------------------")




    def keep_alive(self):
        self.timer = 20
        while(self.timer > 1):
            self.timer -= 1
            if self.kill:
                return
            time.sleep(1)

            

        self.close()
        
    def ka_thread(self):
        self.ka = threading.Thread(target=self.keep_alive)
        self.ka.start()

    def header(self,byte,sum_frag,frag,crc,flag):
        byte[0:0] = int(sum_frag).to_bytes(2 ,'little')
        byte[0:0] = int(frag).to_bytes(2 ,'little')
        byte[0:0] = int(crc).to_bytes(1 ,'little')
        byte[0:0] = int(flag).to_bytes(1, 'little')

        return byte



    def handshake(self,address):
        global pocet_prenesenych
        self.timer = 200 #------------------------------------------------------------> toto nastav vyssie
        self.conn.sendto(self.header(bytearray(),0,0,0,4),address) 
        pocet_prenesenych += 6
        data = self.conn.recv(1460)
        pocet_prenesenych += 6
        flag = int.from_bytes(data[:1],"little")
        if flag == 2:
            print(flags[flag])
            self.conn.sendto(self.header(bytearray(),0,0,0,2),address)
            pocet_prenesenych += 6
            pocet_prenesenych += 6
            print("------------------> Sending succssesfull <------------------")
            if self.slovo:
                print("Sprava: ",self.slovo)
            else:
                print(save_path + "\\" + self.file_path)
            reciever_funkcia()
            if save_path == "swap":
                self.swap = 6
            else:
                self.conn.sendto(self.header(bytearray(),0,0,0,2),address)
            role.recieve_file(address)



    def recieve_file(self,address):
        global role,pocet_prenesenych
        last_frame_num = 0
        self.slovo = ""
        
        while(self.conn):
            
            try:
                frag = self.conn.recv(1460)
            except:
                None

            flag =     int.from_bytes(frag[:1],"little")
            crc  =     "".join([access_bit(frag[1:2],i) for i in range(len(frag[1:2])*8)])
            crc = crc[::-1]
            crc = crc[len(crc)-len(key)+1:]
            frag_num = int.from_bytes(frag[2:4],"little")
            frag_sum = int.from_bytes(frag[4:6],"little")
            data =     frag[6:]

            if flag == 1:
                pocet_prenesenych += 6
                pocet_prenesenych += 6
                if frag_num == frag_sum and last_frame_num+1 == frag_num:
                    self.file_path = data.decode()
                    if self.file_path[:7] == "sprava:":
                        print(flags[flag],frag_num,"            ",math.floor(frag_num/frag_sum * 100),"%                ", len(frag) * frag_num ,"/",len(frag) * frag_sum," Bytes              ", len(frag) + 8 + 34," Bytes")
                        self.file_path = self.file_path[7:]
                        self.conn.sendto(self.header(bytearray(),0,frag_num,0,2),address)
                    else:
                        print(flags[flag],frag_num,"            ",math.floor(frag_num/frag_sum * 100),"%                ", len(frag) * frag_num ,"/",len(frag) * frag_sum," Bytes              ", len(frag) + 8 + 34," Bytes")
                        self.conn.sendto(self.header(bytearray(),0,frag_num,0,2),address)
                        file = open(save_path + "\\" + self.file_path,"wb")
                        file.write(self.export_file)
                        file.close()
                        self.export_file = bytearray()
                else:
                    if int(decodeData(data,crc,key)) == 0 and last_frame_num+1 == frag_num:
                        last_frame_num = frag_num
                        self.export_file.extend(data)
                        print(flags[flag],frag_num,"            ",math.floor(frag_num/frag_sum * 100),"%                ", len(frag) * frag_num ,"/", len(frag) * frag_sum," Bytes              ", len(frag) + 8 + 34," Bytes")
                        
                        # if random.randrange(0,90) != 0:
                        #     self.conn.sendto(self.header(bytearray(),0,frag_num,0,2),address)
                        # else:
                        #     print("neposlal som ACK",frag_num)

                        self.conn.sendto(self.header(bytearray(),0,frag_num,0,2),address)
                    elif frag_num < last_frame_num+1:
                        self.conn.sendto(self.header(bytearray(),0,frag_num,0,2),address)
                    else:
                        self.conn.sendto(self.header(bytearray(),0,last_frame_num,0,3),address)

            if flag == 4:
                print(flags[flag])
                self.handshake(address)
                break


            if flag == 5 and self.conn:
                self.timer = 20
                print(flags[flag])
                try:
                    self.conn.sendto(self.header(bytearray(),0,0,0,5),address)
                except:
                    None

            if self.swap == 6:
                self.conn.sendto(self.header(bytearray(),0,0,0,6),address)
                sender_funkcia()
                self.kill = True
                server = Sender(chosen)
                role = server
                break

            if flag == 6:
                sender_funkcia()
                self.kill = True
                server = Sender(chosen)
                role = server
               
                break

                
            if flag == 7:
                print(flags[flag],frag_num,"            ",math.floor(frag_num/frag_sum * 100),"%                ", len(frag) * frag_num ,"/", len(frag) * frag_sum," Bytes              ", len(frag) + 8 + 34," Bytes")
                self.conn.sendto(self.header(bytearray(),0,frag_num,0,2),address)
                pocet_prenesenych += 6
                pocet_prenesenych += 6
                self.slovo+= data.decode()



if server_client == "s":
    sender_funkcia()
    server = Sender(chosen)
    role = server

elif server_client == "r":
    connection.bind(("", port))  
    reciever_funkcia()
    client = Reciever()
    role = client

while(chosen != "q"):
    type(role)
    role.start() 











