"""Original 0x43b570 shared vehicle-control/drive-efficiency predicate."""


def vehicle_control_mode(flags,is_local_vehicle,setting):
    if type(flags) is not int or not 0<=flags<=0xffffffff or type(setting) is not int or not 0<=setting<=0xffffffff:
        raise ValueError('uint32 vehicle flags and control-mode setting required')
    if type(is_local_vehicle) is not bool:raise ValueError('explicit local-vehicle identity required')
    if flags&0x212:return 1
    return setting if is_local_vehicle else 0
