#!/usr/bin/python3
'''
An app I developed had a Firmware descriptor page which contained crc of the whole image. 
This script was used to calculate the crc and write it to the right place in the FwDescriptor.
'''

##### configuration #####
flashMemSize = 128
appMinAddress = 0x1D006000
fwDescriptorAddr = 0x1D01FFDC
polynom = 0xEB31D82E
##### end of configuration ####
fwDescriptor_CRC32_addr = fwDescriptorAddr + 0x1E
fwDescriptor_start_page_addr = fwDescriptorAddr + 0x14
fwDescriptor_end_page_addr = fwDescriptorAddr + 0x12

import os
from os.path import sys
import ctypes

print("Calculate hex file CRC32 and write it to firmware descriptor CRC32 field:")

if len(sys.argv) < 2:     
    sys.exit('Usage: %s  input_file_name.hex' % sys.argv[0])

if not os.path.exists(sys.argv[1]):
    sys.exit('ERROR: %s was not found!' % sys.argv[1])

filename = sys.argv[1]

   
 
#global variables 
minAddr = flashMemSize * 1024
maxAddr = 0
content = []
addrOffsets = []
memData = {}
fwDescCRC32_index = 0
fwDescCRC32_key = ""
startPage = 0
endPage = 0
startAddr = 0
endAddr = 0
totalBytes = 0


#convert integer to long so we can work with 32 bits
def to_ulong(i):
    return ctypes.c_ulong(i).value

#CRC32 calculation function
def crc32(data, acc):
    global totalBytes
    totalBytes += 1
    acc = to_ulong(~acc)    
    acc = acc ^ to_ulong(data)
    for i in range(0, 8):
        m = -(acc & 1)
        acc = (acc >> 1) ^ (polynom & m)        
    return ~acc
 
def calculateParity(stringLine):
    c_byte = 0
    for i in range(0, len(stringLine), 2):
        c_byte_str = stringLine[i: i+2]        
        c_byte += int(c_byte_str, 16)         
    c_byte = (~c_byte + 1) & 0xFF 
    return str.lower("%0.2X" % c_byte)
    
    
def getPageNumber(key):
    dataAddress = int(key, 16)
    pagenumber = int((dataAddress - 0x1D000000) / 0x400)
    return pagenumber
    
def getPageAddress(pageNum):
    return ((pageNum * 0x400) + 0x1D000000)   


def writeCRC32_toHex():
        
    fwDescData1 = content[fwDescCRC32_index]        #CRC32 starts at this line (big endian MSB)
    fwDescData2 = content[fwDescCRC32_index + 1]    #CRC32 ends at this line (big endian LSB)
     
    #form line to write to the hex file 
    lineToWrite = fwDescData1[1:37] + CRC32_String[6:8] + CRC32_String[4:6]
    
    lineToWrite += calculateParity(lineToWrite)
    #put the content in the right line and add semicolon
    print("Writing two bytes of CRC32 at line %d" % fwDescCRC32_index)
    content[fwDescCRC32_index] = ":" + lineToWrite
    
    #form line to write to the hex file
    lineToWrite = fwDescData2[1: 9] + CRC32_String[2:4] + CRC32_String[0:2] + fwDescData2[13: 17]
    
    lineToWrite += calculateParity(lineToWrite)
    #put the content in the right line and add semicolon
    print("Writing two bytes of CRC32 at line %d" % (fwDescCRC32_index + 1))
    content[fwDescCRC32_index + 1] = ":" + lineToWrite
 

def writeStartAndEndPageIndex_toHex():
    
    lineData = content[fwDescCRC32_index]       
    
    startPageStr = str.upper("%0.4X" % startPage)   
    endPageStr = str.upper("%0.4X" % endPage)  
    
    #form line to write to the hex file 
    lineToWrite = lineData[1:13] + endPageStr[2:4] + endPageStr[0:2] + startPageStr[2:4] + startPageStr[0:2] + lineData[21:41]    

    lineToWrite += calculateParity(lineToWrite)

    # put the content in the right line and add semicolon
    print("Writing fw_end_page and fw_start_page fields to line %d" % (fwDescCRC32_index))
    content[fwDescCRC32_index] = ":" + lineToWrite
       

# reading the contents of the hex file
f = open(filename, 'r') 
content = f.read().splitlines()
f.close()
          
# parsing the hex file content
for j in range(0, len(content)):       
    line = content[j]
    if line.startswith(':'):
        line = line[1:len(line)]                       
        reclen = int(line[0:2], 16)             
        addr = int(line[2:6], 16)
        rectype = int(line[6:8], 16)
        data = line[8: (8 + reclen*2)]
        
        if rectype == 4 :
            addrOffset = data[0: 4]
            
            if(addrOffset != "0000") and (addrOffset not in addrOffsets):  
                addrOffsets.append(addrOffset)
                
        for i in range(0, reclen):            
            temp = int(data[(i*2): (i*2 + 2)], 16) 
                       
            if rectype == 0:
                address = addr + i
                key = str.upper(addrOffset) + str.upper("%0.4X" % address) 
                memData[key] = temp
                                    
                # adjusting the minimum and maximum found address so we do not have to scan all possible addresses
                if address > maxAddr :
                    maxAddr = address
                if address < minAddr :
                    minAddr = address
                
                if key == str.upper("%0.8X" % fwDescriptorAddr):               
                    print("\nFound FW descriptor address: 0x" + key + " in line: %d " % j)  
                    
                if key == str.upper("%0.8X" % fwDescriptor_CRC32_addr):
                    fwDescCRC32_index = j     
                    fwDescCRC32_key = key          
                    print("Found CRC32 field at: 0x" + key + " in line: %d \n" % fwDescCRC32_index)


# only continue if firmware descriptor CRC32 field was found
if fwDescCRC32_index > 0:
    
    # The firmware descriptor contains only start and end page,
    # not start and end address, so we must align maxAddr and minAddr
    # to page boundary and calculate CRC32 from that
    maxAddr |= 0x3FF

    # more global variables
    crc32result = 0
    allOffsets = []    
    firmwareStartFound = False
    numberOfBlankBytes = 0
    lastDetectedDataAddr = 0
    
    # sorting address offsets
    for oneOffset in addrOffsets:        
        allOffsets.append(int(oneOffset, 16)) 
        allOffsets.sort()

    # search for minimum firmware address
    for addrOffset in allOffsets:         
        for dataAddr in range(minAddr, maxAddr + 1):
            key = str.upper("%0.4X" % addrOffset) + str.upper("%0.4X" % dataAddr) 
            if (int(key, 16) < fwDescriptorAddr) and (int(key, 16) >= appMinAddress):                                                                
                if (key in memData):                                         
                    firmwareStartFound = True
                    startPage = getPageNumber(key);      
                    startAddr = int(key,16) & 0xFFFFFC00
                    print("Firmware start found on page " + str("%d" % startPage) + " at: " + key)               
                    if dataAddr != (dataAddr & 0xFC00):     # if not page aligned
                        dataAddr = dataAddr & 0xFC00   # align to page boundary
                        print("Will start CRC32 calculation starting at: 0x" + str.upper("%0.8X" % startAddr))                    
                        break 
        if firmwareStartFound :
            break
                        
       
    # search for maximum firmware address
    for dataAddr in range(startAddr, fwDescriptorAddr):
        key = str.upper("%0.8X" % dataAddr) 
        if (key in memData):  
            lastDetectedDataAddr = dataAddr 
            
    
    endPage = getPageNumber(str("%0.8X" % lastDetectedDataAddr));  
    endAddr = getPageAddress(endPage + 1) - 1
    print("Firmware last data found on page " + str("%d" % endPage) + " at: 0x" + str.upper("%0.8X" % lastDetectedDataAddr )) 
    print("Firmware last page end address: 0x%0.8X" % endAddr)
    
    
    # write the first and last page address to data
    memData[str.upper("%0.8X" % fwDescriptor_end_page_addr)] = endPage & 0xFF
    memData[str.upper("%0.8X" % (fwDescriptor_end_page_addr + 1))] = endPage >> 8
    memData[str.upper("%0.8X" % fwDescriptor_start_page_addr)] = startPage & 0xFF
    memData[str.upper("%0.8X" % (fwDescriptor_start_page_addr + 1))] = startPage >> 8
    
    writeStartAndEndPageIndex_toHex()    

    # calculate CRC32
    print("Calculating CRC32 of the firmware pages")
    for dataAddr in range(startAddr, endAddr +1):
        # consider all locations except CRC32 field which is 4 bytes,
        # just in case the firmware spreads on to the last page
        if (dataAddr < fwDescriptor_CRC32_addr) or (dataAddr > (fwDescriptor_CRC32_addr + 3)):
            key = str.upper("%0.8X" % dataAddr)
            if (key in memData):
                crc32result = crc32(memData[key], crc32result)
            else:
                crc32result = crc32(0xFF, crc32result)  #account for blank bytes 

    # if the firmware does not reach the last page, we need to calculate the CRC32 of that page too
    # since the firmware descriptor is located there and is part of the firmware too
    
    if endAddr < fwDescriptorAddr:  
        print("Calculating CRC32 of the last page containing the FW descriptor")
        
        startAddr = getPageAddress(getPageNumber(str("%0.8X" % fwDescriptorAddr)))
        endAddr = startAddr + 0x400        
        
        for dataAddr in range(startAddr,endAddr):
            # consider all locations except CRC32 field which is 4 bytes
            if (dataAddr < fwDescriptor_CRC32_addr) or (dataAddr > (fwDescriptor_CRC32_addr + 3)):
                key = str.upper("%0.8X" % dataAddr)
                if key in memData:
                    crc32result = crc32(memData[key], crc32result)
                else:
                    crc32result = crc32(0xFF, crc32result)  #account for blank bytes 

    CRC32_String = str.lower("%0.8X" % to_ulong(crc32result))       
    print("calculated CRC32: 0x" + str.upper("%0.8X" % to_ulong(crc32result)) )
    print("total number of bytes: %d" % totalBytes)
    
    writeCRC32_toHex()
        
    # write the modified content back to the hex file
    f = open(filename, 'w')     
    for i in range(0, len(content)):
        f.write(content[i])
        f.write("\n")
    f.close()
   
    
else:    
    sys.exit("FW descriptor CRC32 field not found")