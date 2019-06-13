import socket
from threading import Thread, Lock
import time
import os
from sys import *
from os import system
#Global variables that are being used in functions
printing = True  # This is to stop the printing of the metric output
contentlength = 0 
content = False    # condition to check if the content is specified in the HEAD or not
acceptranges = False # condition to check if accept Ranges is specified in the HEAD or not
doneYet =0
Thread_object = {}
lock = Lock()
accept = []   # to check if all threads have terminated or not
urlparts = []
dirname = ''
file = '' # file name
extension = ''
Resume = False # condition to check if we have to resume or not
threads = 1   # number of threads
interval = 1 # time interval
url = ''
save = ''   # output location

# main function is call all other functions
def main(argv):
    arguments(argv)
    parsing()
    getHead()
    #if condition to check if the server allows us to download the file with multiple connection or not 
    if not (content and acceptranges):
        abc = Thread(target=Print_thread).start()
        time.sleep(1)
        singlefunction()
    else:
        callingthreads()
        waitingForThreads()
        WritingInFile()
        RemovingTempFiles()

# This function is taking arguments from command line as input and saving all the variable in global
# variables so that they can be used in other functions
def arguments(argv):
    for x in range(len(argv)):
        if argv[x] == "-r":
            global Resume
            Resume = True
        if argv[x] == "-n":
            global threads
            threads = int(argv[x+1])
        if argv[x] == "-i":
            global interval
            interval = float(argv[x+1])
        if argv[x] == "-f":
            global url
            url = argv[x+1]
        if argv[x] == "-o":
            global save
            save = argv[x+1]
            
# This function is parsing the url and saving it into dirname, file (filename), extension
def parsing():
    global urlparts,url, dirname, file, extension
    urlparts = url.split('/')
    dirname = '/'.join(urlparts[3:])
    file, extension = urlparts[len(urlparts)-1].split(".")
    
# this function is getting the HEAD from the server and setting content, contentlength and  acceptranges variables
def getHead():
    global urlparts, dirname
    s = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
    s.connect((urlparts[2],80))
    s.send(("HEAD /"+dirname+" HTTP/1.1\r\nHOST: "+urlparts[2]+"\r\n\r\n").encode('utf-8'))
    resp = s.recv(1024).decode('utf-8')
    print(resp)
    for line in resp.splitlines():
        if "Content-Length" in line:
            global contentlength,content
            contentlength =line[16:]
            if int(contentlength) == 0:
                content = False
            else:
                content = True
    if "Accept-Ranges: bytes" in resp:
        global acceptranges
        acceptranges = True
    s.close()

# this function will run if the server does not allow multiple connections to download
# this function will make a single connection and download the complete file with single GET request
def singlefunction():
    c = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
    c.connect((urlparts[2],80))
    c.send(("GET /"+dirname+" HTTP/1.1\r\nHost: "+urlparts[2]+"\r\n\r\n").encode('utf-8'))
    j = 0
    lock.acquire()
    chunk = 1
    global contentlength
    x = ThreadHandled(contentlength, chunk)
    d = {str(chunk) : x}
    lock.release()
    global Thread_object
    Thread_object.update(d)
    
    # this if condition is used to check if the output location exists or not if it does not exist then we are making a directory
    if len(save) > 2:
        file2 = save
        directory = os.path.dirname(file2)
        if not os.path.exists(directory):
            os.makedirs(directory)
        f2 = open(r""+save,'ab')
    else:    
        f2= open(urlparts[len(urlparts)-1],'ab')
    #we are calculating the time,speed, total bytes and bytes downloaded to be printed by the metric output thread and writing the bytes in the file
    time1 = time.perf_counter()
    time.sleep(0.005)
    resp = c.recv(1024)
    time2 = time.perf_counter()
    recieveTime = time2 - time1
    #we are splitting data in bytes because if we decode the data to string we will get error for media files so this line enables us to download files of any format
    string = resp.split(b'\r\n\r\n')[0]
    resp = resp[len(string)+4:len(resp)]
    j = len(resp)+j
    f2.write(resp)
    numr = float(j*8)
    denom = float(1000*recieveTime)
    speed = float(numr/denom)
    Thread_object.get(str(chunk)).AddRate(speed)
    Thread_object.get(str(chunk)).AddDone(j)
    # this loop will run until we are recieving data from the server
    while True:
        time1 = time.perf_counter()
        time.sleep(0.005)
        resp = c.recv(1024)
        time2 = time.perf_counter()
        recieveTime = time2 - time1
        # k is the size fo the file downloaded in this loop
        k =len(resp)
        numr = float(k*8)
        denom = float(1000*recieveTime)
        speed = float(numr/denom)
        # j is the total size downloaded of the file uptil now
        j = j + k
        f2.write(resp)
        # setting speed and size of the thread
        Thread_object.get(str(chunk)).AddRate(speed)
        Thread_object.get(str(chunk)).AddDone(j)
        if not resp: break
    f2.close()
    #we are telling the metric output file to stop by giving False as a value to printing variable
    global printing
    printing = False
    print("downloaded")
    
#this function is used in case we have to download the file with multiple connections
#this function will give chunk, range and total size of the chunk to the chunk thread which will run for each downloading thread
def callingthreads():
    global threads, contentlength, accept
    ranged = float(contentlength)/threads
    d=-1
    chunk =0
    abc = Thread(target=Print_thread).start()
    time.sleep(1)
    for x in range(0,threads):
        e = d
        d += int(ranged)
        e+=1
        ranges = str(e)+"-"+str(d)
        chunk += 1
        total = d - e
        total = total + 1
        if chunk == threads:
        	ranges = str(e)+"-" + contentlength
        	total = int(contentlength) - e
        accept.append(True)
        Thread(target=ChunkThread, args=(chunk, ranges, total,)).start()

# we did not use join or is alive function to wait for the downloading threads to terminate we made our own function
# this function will go into infinite loop until all the threads have been terminated
# accept is a list of boolean against all the running threads if threads have terminated then the list will change its value to false
def waitingForThreads():
    global accept, printing, threads
    for z in range(0, threads):
        while accept[z]:
            i=9
    printing = False

# this function enables us to print the metric output of the file that is being downloaded
def Print_thread():
    global printing,interval
    while printing:
        time.sleep(interval)
        #lock for only that current information
        lock.acquire()
        # system('cls') allows us to clear the screen so that we dont get a messy cmd
        system('cls')
        doneYet = 0
        totalSpeed = 0
        for k in Thread_object:
            doneYet += Thread_object.get(k).Done
            print("Connection"+str(Thread_object.get(k).Thread_id)+": "+str(Thread_object.get(k).Done)+"/"+str(Thread_object.get(k).Total)+", download speed: "+str(Thread_object.get(k).Rate)+" kb/s\n")
            totalSpeed += Thread_object.get(k).Rate
        if(len(Thread_object)>0):
            totalSpeed = totalSpeed/len(Thread_object)
        lock.release()
        print("Total: " +str(doneYet)+"/"+str(contentlength)+", download speed: "+str(totalSpeed)+" kb/s\n")

#now we are writing into the file
# we have created temporary files for each chunk thread so in this function we are appending the data of all temporary file into the output file
def WritingInFile():
    global urlparts, threads, extention, file, save
    if len(save) > 2:
        file2 = save
        directory = os.path.dirname(file2)
        if not os.path.exists(directory):
            os.makedirs(directory)
        f2 = open(r""+save,'ab')
    else:    
        f2= open(urlparts[len(urlparts)-1],'ab')
    for y in range(0, threads):
        d = file+str(y+1)+"."+extension
        print(d)
        f = open(d, "rb")
        e = f.read(os.path.getsize(d))
        f2.write(e)
    f2.close()
    print("\nfile downloaded waiting for process to complete\n")

# in this function we are deleting all the temporary files as user does not want irrelevant files
def RemovingTempFiles():
    global threads, files, extension
    for y in range(0,threads):
        d = file+str(y+1)+"."+extension
        os.remove(d)
    print("process completed\n")

#this function is run when we are downloading file with multiple connections
# this function is called as threads
def ChunkThread(chunk, ranges, total):
    # j is the size of the file that has been downloaded up till now
    j = 0
    lock.acquire()
    x = ThreadHandled(total, chunk)
    d = {str(chunk) : x}
    lock.release()
    global Thread_object, Resume
    Thread_object.update(d)
    # this is the if condition which will run when we have to resume, if we have to resume then we are getting the size of the temporary file
    # the range is being changed according to the file sie of the temporary file
    if Resume:
        k = file+str(chunk)+"."+extension
        j = os.path.getsize(k)
        e,f = ranges.split('-')
        e = int(e) + j
        ranges = str(e)+"-"+f
    c = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
    c.connect((urlparts[2],80))
    c.send(("GET /"+dirname+" HTTP/1.1\r\nHost: "+urlparts[2]+"\r\nRange: bytes="+ranges+"\r\n\r\n").encode('utf-8'))
    f = open(file+str(chunk)+"."+extension,"ab")
    d=0
    resp = c.recv(1024)
    #we are splitting data in bytes because if we decode the data to string we will get error for media files so this line enables us to download files of any format
    string = resp.split(b'\r\n\r\n')[0]
    resp = resp[len(string)+ 4 : len(resp)]
    j = len(resp) + j
    f.write(resp)
    # this loop is reacieving the bytes and will terminate when we have the downloaded size is equal to the total size of the chunk that was to be downloaded
    while True:
        time1 = time.perf_counter()
        time.sleep(0.005)
        resp = c.recv(1024)
        time2 = time.perf_counter()
        recieveTime = time2 - time1
        f.write(resp)
        k = len(resp)
        numr = float(k*8)
        denom = float(1000*recieveTime)
        speed = float(numr/denom)
        j = j + k
        Thread_object.get(str(chunk)).AddRate(speed)
        Thread_object.get(str(chunk)).AddDone(j)
        if j == total: break
    global accept
    f.close()
    accept[chunk-1] = False

# class for the connection. Where it sets its connection number, total bytes to download, bytes downloaded, and speed
class ThreadHandled:
    Thread_id = 0
    Total = 0
    Done = 0
    Rate = 0

    def __init__(self, Total, Thread_id):
        self.Thread_id = Thread_id
        self.Total = Total
        self.Done = 0

    def AddDone(self, Done):
        self.Done = Done

    def AddRate(self, Rate):
        self.Rate = Rate

if __name__ == '__main__':
    main(argv)
