### CRC Library
# Simple CRC library copied from https://stackoverflow.com/a/25259157
# 
# nm3210@gmail.com
# Date Created:  June 12th, 2021
# Last Modified: June 12th, 2021

_CRC_POLYNOMIAL = 0x1021
_CRC_PRESET = 0x1D0F

def _initial(c):
    crc = 0
    c = c << 8
    for j in range(8):
        if (crc ^ c) & 0x8000:
            crc = (crc << 1) ^ _CRC_POLYNOMIAL
        else:
            crc = crc << 1
        c = c << 1
    return crc

_crcTable = [ _initial(i) for i in range(256) ]

def _update_crc(crc, c):
    cc = 0xff & c
    tmp = (crc >> 8) ^ cc
    crc = (crc << 8) ^ _crcTable[tmp & 0xff]
    crc = crc & 0xffff
    return crc

def crc(strIn):
    crc = _CRC_PRESET
    for c in strIn:
        crc = _update_crc(crc, ord(c))
    return crc

def crcb(*i):
    crc = _CRC_PRESET
    for c in i:
        crc = _update_crc(crc, c)
    return crc
