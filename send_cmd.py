#!/usr/bin/env python

import socket, json, os, time, sys
from datetime import datetime
#from .gethosts import get_board_info
from time import sleep
from socket import error as SocketError
import errno

### General settings
BUF_SIZE = 8192
TIMEOUT = 10
timeout = TIMEOUT

### TCP/IP settings
IP_ADDR = None

CMD_PORT = 7359
IX_PORT = 5555
LOG_PORT = 5647
TLOG_PORT = 5648
IMG_SRVR_PORT = 4647


### Basic operations: first argument is the IP address, second argument is the timeout.
def build_up_connection_with_log_port(ipaddr, timeout=TIMEOUT):
    lp = build_up_connection_with_port(ipaddr, timeout, LOG_PORT)

    return lp


### Basic operations: first argument is the IP address, second argument is the timeout.
def build_up_connection_with_tlog_port(ipaddr, timeout=TIMEOUT):
    lp = build_up_connection_with_port(ipaddr, timeout, TLOG_PORT)

    return lp


### Basic operations: first argument is the IP address, second argument is the timeout, third is the port
def build_up_connection_with_port(ip_addr, timeout, PORT):
    lp = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    lp.connect((ip_addr, PORT))

    # Set timeout to seconds
    lp.settimeout(timeout)
    return lp


def build_up_connection(ip_addr, ixPort=None, cmdPort=None, boardName=None, timeout=TIMEOUT):
    cs = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    ix = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    if boardName is not None:
        # Dynamically find the ports if a board name is given
        boardObj = get_board_info(boardName)
        ixPort = boardObj.ixPort
        cmdPort = boardObj.tclPort

    if ixPort is None:
        ix.connect((ip_addr, IX_PORT))
    else:
        ix.connect((ip_addr, ixPort))
    if cmdPort is None:
        cs.connect((ip_addr, CMD_PORT))
    else:
        cs.connect((ip_addr, cmdPort))

    # set timeout to seconds
    cs.settimeout(timeout)
    ix.settimeout(timeout)
    return cs, ix


### Basic operations: first argument is the IP address, second argument is the timout.
def build_up_connection_img_server(*args):
    ### Make it flexible so it can take any IP and ports by using *args or **kwargs???
    if (len(args)):
        ip_addr = args[0]
    else:
        ip_addr = IP_ADDR

    # print("Connecting to IP address: %s" % ip_addr)
    imgsrvr = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    imgsrvr.connect((ip_addr, IMG_SRVR_PORT))

    # set timeout to seconds
    timeout = TIMEOUT
    if (len(args) == 2):
        timeout = args[1]
    imgsrvr.settimeout(timeout)
    return imgsrvr


def tranfer_image(imgServerObj, captureId, numbytes, filePath):
    start = datetime.now()
    d = {'id': captureId, 'length': numbytes}
    cont_json = json.dumps(d)
    imgServerObj.sendall((cont_json + ' \n').encode())

    fp = open(filePath, 'wb');
    while (True):
        try:
            resp = imgServerObj.recv(1024)
            fp.write(resp);
        except:
            break

    end = datetime.now()
    fp.seek(0, os.SEEK_END)
    fsize = fp.tell()
    print("Took {} seconds to transfer image".format((end - start)))
    fp.close()
    # Return False if the file is not equal to the expected number of bytes
    if (fsize != int(numbytes)):
        return False
    return True


def close_connection(cs, ix):
    cs.close()
    ix.close()


def reconnect(cs, ix):
    close_connection(cs, ix)
    return build_up_connection()


def read_tcl_cmd(socket):
    buf = ''
    try:
        buf += socket.recv(BUF_SIZE)
    except:
        if (buf == ''):
            return None
        else:
            return buf
    return buf


def send_tcl_cmd(socket, msg, *args):
    host, port = socket.getpeername()
    max_retry = 10
    sent_msg = msg
    for i in range(max_retry):
        try:
            tmp_to = socket.gettimeout()
            if (len(args)):
                if (type(args[0]) == bool):
                    retry = 3
                elif (type(args[0]) == int):
                    socket.settimeout(args[0])
                else:
                    sent_msg = msg + str(args[0]) + "\n"
            buf = ''
            if (socket.send((sent_msg + "\n").encode())):
                while (True):
                    # print(retry)
                    try:
                        rx = socket.recv(BUF_SIZE).decode('utf-8')
                        if len(rx) <= 0:
                            break
                        buf += rx
                    except SocketError as e:
                        if e.errno == errno.ECONNRESET:
                            raise
                        break
                    except:
                        break
                    # print(r'{}'.format(rx))

                socket.settimeout(tmp_to)
                if (buf == ''):
                    return None
                return buf
        except SocketError as e:
            if e.errno != errno.ECONNRESET:
                raise  # Not error we are looking for
            print(f"Connection error: {e} - Trial {i + 1} - Retrying")
            time.sleep(5)
            socket = build_up_connection_with_port(host, timeout, port)
        except:
            raise Exception
    print(f"Connection error: Maximum number of retries {max_retry} reached - Exiting")
    raise Exception


def send_cmd(socket, msg, timeout=TIMEOUT, printCmd=False):
    host, port = socket.getpeername()
    max_retry = 10
    for i in range(max_retry):
        try:
            if printCmd:
                print('\n{} IX CMD: {}'.format(datetime.now().strftime("%I:%M:%S:%f"), msg))
            # tmp_to = socket.gettimeout()
            # socket.settimeout(timeout)
            iteration_timeout = 0.5

            msgJson = json.loads(msg)
            cmd = msgJson["IxType"]
            ixIdIn = msgJson["IxID"]

            jstr = None
            socket.settimeout(iteration_timeout)

            socketResp = socket.send(msg.encode())
            if timeout == 0:
                socket.settimeout(timeout)
                return

            if (socketResp):
                rsp = ""
                jrsp = ""
                received_flag = False
                start_time = time.time()
                lapse_time = time.time() - start_time
                while lapse_time <= timeout:
                    try:
                        rx = socket.recv(BUF_SIZE).decode('utf-8')
                        rsp += rx
                    except:
                        lapse_time = time.time() - start_time

                    if rsp:
                        check_rsp = _check_jsons(rsp, ixIdIn)
                        received_flag = check_rsp[1]
                        if received_flag:
                            break

                if not rsp:
                    print('{} IX BAD RSP: No data received'.format(datetime.now().strftime("%I:%M:%S:%f")))
                    return None

                jstr = check_rsp[0]
                if received_flag:
                    if printCmd:
                        print('{} IX RSP: {}'.format(datetime.now().strftime("%I:%M:%S:%f"), jstr))
                    return jstr

                if printCmd:
                    print('{} IX BAD RSP: {}'.format(datetime.now().strftime("%I:%M:%S:%f"), rsp))
                return rsp
        except SocketError as e:
            if e.errno != errno.ECONNRESET:
                raise  # Not error we are looking for
            print(f"Connection error: {e} - Trial {i + 1} - Retrying")
            time.sleep(5)
            socket = build_up_connection_with_port(host, timeout, port)
        except:
            raise Exception
    print(f"Connection error: Maximum number of retries {max_retry} reached - Exiting")
    raise Exception


def receive_ix_notification(socket, notif_msg, timeout=TIMEOUT):
    jmsg = ""
    rsp = ""
    ix_type = ""

    # Set the internal socket iteration timeout
    iteration_timeout = 0.5
    socket.settimeout(iteration_timeout)
    tmp_to = socket.gettimeout()

    start_time = time.time()
    lapse_time = time.time() - start_time
    while lapse_time <= timeout:
        try:
            rsp += socket.recv(1024).decode('utf-8')
        # This exception is necessary when a send is executed right before
        # calling this function and the socket is still not ready for a read
        except BlockingIOError:
            pass

        except Exception as e:
            pass

        if rsp:
            check_rsp = _check_jsons(rsp, notif_msg, key='IxType')
            received_flag = check_rsp[1]
            if received_flag:
                break

        lapse_time = time.time() - start_time

    jstr = check_rsp[0]

    if not received_flag:
        print("{} IX BAD Notification: {}".format(datetime.now().strftime("%I:%M:%S:%f"), jstr))
        return jstr

    print("{} IX Notification: {}".format(datetime.now().strftime("%I:%M:%S:%f"), jstr))
    return jstr


def create_ix_cmd(cmd, *args, **kwargs):
    the_dict = {}
    ### default to the magic number
    the_dict["IxID"] = 65
    the_dict["IxType"] = cmd
    for key, value in kwargs.items():
        the_dict[key] = value
    return json.dumps(the_dict)


def grab_tlog(ix, tlog_name, timeout=TIMEOUT):
    # build connection with tlog port
    # getpeername() outputs a tuple with the first index being the object's ip address
    address = ix.getpeername()
    tl = build_up_connection_with_tlog_port(address[0], timeout)
    sleep(1)

    # replay the target name to the given socket
    ixcmdJson = create_ix_cmd('ix_tlog_replay_server', name=tlog_name)
    cmd_rsp = send_cmd(ix, ixcmdJson)
    data = grab_data_from_socket(tl)

    tl.close()
    return (data, cmd_rsp)


def grab_log(ix, log_name, timeout=TIMEOUT, out_format='0', maxrecs=0, minseqnum=0, only_new=False):
    # build connection with log port
    # getpeername() outputs a tuple with the first index being the object's ip address
    address = ix.getpeername()
    tl = build_up_connection_with_log_port(address[0], timeout)
    sleep(1)

    # replay the target name to the given socket
    ixcmdJson = create_ix_cmd('ix_log_replay_server', name=log_name,
                              format=out_format, maxrecs=maxrecs,
                              minseqnum=minseqnum,
                              only_new=only_new)
    cmd_rsp = send_cmd(ix, ixcmdJson)
    data = grab_data_from_socket(tl)

    tl.close()
    return (data, cmd_rsp)


def grab_data_from_socket(socket):
    log = b''
    try:
        while True:
            data = socket.recv(2048)
            if len(data) == 0:
                break
            log += data
    except Exception as e:
        return (log)

    return (log)


def _check_jsons(rsp, key_value, key='IxID'):
    # Set up variables
    rsp_out = ''
    bracket_count = 0
    idx_bracket_encountered = 0

    if len(rsp) == 0:
        return rsp, False

    for idx in range(len(rsp)):
        # All logic is based on a open and close bracket
        # where open bracket assumes a +1 point
        # and a closed bracket assumes a -1 point
        if rsp[idx] == '{':
            bracket_count += 1
        elif rsp[idx] == '}':
            bracket_count -= 1

        # If we encounter the end of a dictionary then add a variable to distinguish location
        if bracket_count == 0:
            rsp_out = rsp[idx_bracket_encountered:idx + 1]

            if rsp_out.endswith('}'):
                try:
                    json_out = json.loads(rsp_out)
                    if json_out[key] == key_value:
                        return json_out, True
                except:
                    pass

            idx_bracket_encountered = idx + 1

    return rsp, False


def netcat_json(host, port, cont_dict, retry=10):
    """ Send a dict (converted to JSON) to a port.  Useful for IX commands.  Received data is returned as a list of dicts.
    """
    out = ''
    if isinstance(cont_dict, dict):
        cont_json = json.dumps(cont_dict)
    else:
        cont_json = cont_dict

    err_count = 0

    # adding a wrapper here to try and catch a network error I was seeing.  This will retry 10 times before giving up, I Hope
    while out == '':
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            # s.settimeout(5)
            # print(s.gettimeout())
            s.connect((host, int(port)))
            s.sendall((cont_json + ' \n').encode())
            s.shutdown(socket.SHUT_WR)
            while True:
                # print("here")
                data = s.recv(4096)
                print(data)
                if not data:
                    break
                out += data.decode('utf-8')
            s.close()
        except OSError:
            err_count += 1
            print('Error', sys.exc_info()[0])
            print('Error Count = {}'.format(err_count))
            if err_count >= retry and retry != 0:
                print(f'More than {retry} errors, giving up')
                return []

            print('Trying to send again')

    return [json.loads((b + '}').replace('\n', '')) for b in out.split('}')[:-1]]
