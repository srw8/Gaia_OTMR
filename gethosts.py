'''
library to access fw boards networking details
'''
import time
import re
import json
import socket
import subprocess
from time import sleep
import netifaces as ni


IX_PORT = 5555
FW_SIM_IX_PORT = 6666
LOOPBACK_IP = "127.0.0.1"
BROADCAST_IP = "255.255.255.255"


def get_boards_ips(fw_sim=False, retry=True):
    """
    Function to get a list of all Board objects from boards available or ini file
    The idea here is for this function to make decision about what to return,
    actual data vs ini file data. Th decision relies on wheter or not a fwsim
    file with the path to iniFile has been created before calling this function
    """

    # Proceed with normal execution if no fwsim file is found
    attempts = 3
    # Attempts to get the boards broadcast (AKA: list-of-embedded-systems)
    # This code will retry 3 times just in case list_embedded() does not return
    # success
    while attempts != 0:
        attempts -= 1
        board_list = list_embedded(fw_sim)
        if not retry:
            break
        if board_list:
            break
        sleep(3)

    if (attempts == 0 and not board_list) or len(board_list) == 0:
        return None

    # Create board objects
    boards = create_board_objects(board_list, fw_sim)

    if not boards:
        return None

    return boards


def get_boardsObjs(fw_sim=False, retry=True):
    """
    Function to get present boards object. This is basically the same as
    get_board_info but in a different structure, dict instead of list.
    This is used in conftest.py to pass the dict to tests. Having a dict with
    board names as keys avoids a for loop to find the right board.
    Returned dict has the following format: {board_name: boardObj,..}
    """
    board_objs = {}
    ips = get_boards_ips(fw_sim, retry)
    if not ips or ips is None:
        return None

    for obj in ips:
        board_objs[obj.boardName] = obj

    return board_objs


def get_board_info(boardInfo, fw_sim=False):
    """
    Function to get the Board object of an specific board
    """

    board_objs = get_boards_ips(fw_sim)
    for board in board_objs:
        if boardInfo == board.boardName or boardInfo == board.board_ip:
            return board

    return None


def create_board_objects(boardList, fw_sim=False):
    """
    This function will create the board objects using output from list_embedded function
    """

    boards = []

    # Iterate through each item containing a dictionary with info broadcasted
    # by FW board
    for board in boardList:

        # Get the project name
        project_name = _find_project(board)
        if project_name is None:
            return None

        board_ip = board["board_ip"]
        board_file_name = board["project"]
        ix_port = board["ix_port"]
        tcl_port = board["tcl2_port"]
        board_name = board["hostname"]

        # Parse the boardName assuming the following format: projectName_<boardname>__x_y
        # Where x could be side A/B or proto version
        # where y anything
        # if re.search fails to get the pattern it will return None
        board_simple_name = re.search(r"^\s*{}_(\w*)_(\w*)_(\w*)".format(project_name), board_name)

        if not board_simple_name:
            # Parse the boardName assuming the following format: projectName_<boardname>__x
            # Where x could be side A/B or random number larger than lenght 1
            board_simple_name = re.search(r"^\s*{}_(\w*)_(\w*)".format(project_name), board_name)

            # Assuming following format: projectName_<boardname>__x
            # if len(x) is greater than 1 then its not a board side version then we just get the
            # board name

            if board_simple_name:
                if len(board_simple_name.group(2)) > 1:
                    board_simple_name = board_simple_name.group(1)
                # When len(x) is not greater than 1, then it is the board side version and we group
                # it together
                else:
                    board_simple_name = re.search(r"^\s*{}_(\w*)".format(project_name), board_name)
                    board_simple_name = board_simple_name.group(1)
            # when boardSimpleName is none, then we come on to the following search below and get
            # the second group
            else:
                board_simple_name = re.search(r"^\s*{}_(\w*)".format(project_name), board_name)
                board_simple_name = board_simple_name.group(1)
        else:
            board_simple_name = board_simple_name.group(1)

        if '_' in board_simple_name:
            board_simple_name = board_simple_name.replace('_', '')

        # Create boards objects and append to return at end of function
        board_obj = Board(
            board_ip,
            board_file_name,
            board_simple_name,
            ix_port,
            tcl_port,
            project_name,
            fw_sim=fw_sim,
        )
        boards.append(board_obj)

    if not boards:
        return None

    return boards


def _poll_board(boardId, timeout=30, fw_sim=False):
    """
    Function to find out if a board is up and running
    """
    found_board = False
    while timeout != 0:
        board_list = get_boards_ips(fw_sim)

        if not board_list:
            continue

        for present_board in board_list:
            if boardId == present_board.board_ip or boardId == present_board.boardName:
                return True
            timeout -= 1
            time.sleep(1)

    return found_board


def _get_list_of_embedded_systems():
    '''
    Function gets the output of the program 'list-embedded-systems'
    Deprecated method: use function list_embedded
    '''
    data_output = subprocess.Popen(
        '/home/ilmnadmin/list-embedded-systems',
        stdout=subprocess.PIPE,
        stdin=subprocess.PIPE,
        shell=True,
        encoding='utf8'
    ).communicate('q\n')[0]

    return data_output


def _find_project(board_dict):
    """
    Function to find out which project is being called
    """
    project_name = None

    # if no boards collected from list embedded then exit code
    if not board_dict:
        print("Board dict is empty")
        return None

    # parse for the project name using the boards hostname
    hostname = board_dict["hostname"]

    project_name = re.search(r"(\w*?)_", hostname).group().replace("_", "")

    if not project_name:
        return None

    return project_name


def list_embedded(fw_sim=False):
    """
    Function to listen to 169. broadcast messages from FW boards.
    Returns a list with each item being a dictionary with the information broadcasted by FW board
    """

    board_list = []
    discovery_msg = b'{"query":true}'
    # Get the name of all interfaces
    interfaces_names = ni.interfaces()

    # Iterate through each interface and get IP address in the AF_NET family
    for interface_name in interfaces_names:
        try:
            ip_interface = ni.ifaddresses(interface_name)[
                ni.AF_INET][0]['addr']
        except KeyError:
            ip_interface = ''

        if fw_sim:
            broadcast = ip_interface.startswith("127.")
        else:
            broadcast = ip_interface.startswith("169.")

        # The idea here is to broadcast on all 169. interfaces, just in case
        # multiple 169 interfaces are present
        if broadcast:
            # Open a Tx socket to send the query message
            try:
                # txSock.bind will throw an exception if some other process
                # is using the broadcast interface. The idea is to return
                # and have the calling process retry after a few seconds
                tx_sock = socket.socket(
                    socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
                tx_sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
                tx_sock.bind((ip_interface, 0))
            except socket.error as error:
                print(error)
                tx_sock.close()
                return board_list

            # Open a Rx socket to receive responses from boards
            try:
                # The same thing as above is done here for completeness.
                rx_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                rx_sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
                rx_sock.settimeout(0.1)
                if fw_sim:
                    rx_sock.bind((LOOPBACK_IP, IX_PORT))
                else:
                    rx_sock.bind(("0.0.0.0", IX_PORT))
            except socket.error as error:
                print(error)
                tx_sock.close()
                rx_sock.close()
                return board_list

            # Send query msg
            if fw_sim:
                discovery_ip = LOOPBACK_IP
                board_port = FW_SIM_IX_PORT
            else:
                discovery_ip = BROADCAST_IP
                board_port = IX_PORT
            tx_sock.sendto(discovery_msg, (discovery_ip, board_port))
            tx_sock.close()

            # we receive each board dict one at at time, that's why can process each dict as it's
            # received
            while True:
                board_dict = {}
                try:
                    data, addr = rx_sock.recvfrom(4096)
                except socket.timeout:
                    break

                # convert str to dict
                board_dict = json.loads(data)
                # print(board_dict)
                # the original query message is also received, this is expected since it is
                # broadcasted to all 169. interfaces
                # Do not include the original query message in the received
                # list
                if board_dict['query'] is True:
                    continue

                # adding board ip to data dict
                # the ip of the board that responded to the query message is not contained in the
                # data, but is available as a return parameter of the recvfrom
                # function.
                board_dict["board_ip"] = addr[0]

                # the received dict contains all ports within a list as a value:
                # {'ports': [{tlog_port: 5648}, {}, {'ix_port': 5555}...]
                # this code extracts that info into simple key:value pairs
                # get the value of the 'ports' key and remove from original
                # dict
                ports_info = board_dict.pop('ports')
                # insert individual port dict into the received dict
                for port in ports_info:
                    board_dict[list(port.keys())[0]] = list(port.values())[0]

                # Add board dict to list
                board_list.append(board_dict)

            # Close rx port
            try:
                rx_sock.close()
            except socket.error:
                pass

    return board_list


class Board:
    """
    class for boards
    Args:
        board_ip (str): IP of board
        filename (str): filename of board on list embedded systems,
                             generically as <project_name>_<board_name> ,ex: lightning_xyb
        boardName (str): name of board with side, if applicable. ex: chm, ttc, rbaa, flua
        ixPort (int): port for ix communication, 5555 on apollo
        tclPort (int): port for TCL communication, 7360 on apollo
        get_fw_logs (bool): Flag to collect fw logs if a test fails
    """

    def __init__(
        self, ip, filename, boardName, ixPort, tclPort, project, get_fw_logs=False, fw_sim=False
    ):
        self.board_ip = ip
        self.filename = filename
        self.boardName = boardName
        self.ixPort = ixPort
        self.tclPort = tclPort
        self.project = project
        self.get_fw_logs = get_fw_logs
        self.fw_sim = fw_sim

if __name__ == "__main__":
    boards = get_boards_ips()
    if not boards:
        print("No boards were found")
        exit(-1)
    for board in boards:
        print(f"{board.boardName}\t\t{board.board_ip}")