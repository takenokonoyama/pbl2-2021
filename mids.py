# -*- coding: utf-8 -*-
# mids.py

from socket import *
import sys
import client
import threading  # for Thread()

BUFSIZE = 1024 # 受け取る最大のファイルサイズ
rec_file_name = 'received_data.dat' # 受け取ったデータを書き込むファイル

server_name = sys.argv[1] # サーバのホスト名
server_port =  int(sys.argv[2]) # サーバのポート

def interact_with_client_TCP(soc):
    print(soc)

def interact_with_client_UDP(soc):
    print(soc)

def main_TCP():
    server_socket = socket(AF_INET, SOCK_STREAM) #TCP
    server_socket.bind(('', server_port))
    server_socket.listen(5) #TCP
    print('The server is ready to receive by TCP')
    connection_socket, addr = server_socket.accept() #TCP    
    client_handler = threading.Thread(target=interact_with_client_TCP, args=(connection_socket,)) #TCP
    client_handler.start()  # スレッドを開始

def main_UDP():
    server_socket = socket(AF_INET, SOCK_DGRAM) #UDP
    server_socket.bind(('', server_port))
    print('The server is ready to receive by UDP')
    interact_with_client_UDP(server_socket)

if __name__ == '__main__':
    key = int (input("Use TCP 1, UDP 2 :"))
    while True :
        if key == 1 :
            main_TCP()
        elif key == 2 :
            main_UDP()
        else :
            print("You can't use")