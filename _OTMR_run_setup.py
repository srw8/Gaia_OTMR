import _OTMR_runtime_utilities as utl
import gethosts as get

with open("OTMR_TEST.txt", "a") as f:
    board_objs = get.get_boards_ips()   
    
    for b in board_objs: f.write(f'{b.boardName}, {b.board_ip}')


#utl.OTMR_LLD_init()
#utl.clean_lld_dir