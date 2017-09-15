#!/usr/bin/python3
'''
Creates a c file with arrays of bytes from memory locations in the hex file.
The purpose is to embed an image into your new project. I used it to embed a bootloader into image of the application.
'''

from os.path import sys
import os
from intelHexParser import HexParser


# configuration
outputFileName = "hex_to_c.c"   # default output file name
bytesPerPage = 2048
max_valid_address = 0x1FC00BF0     # 0x2A800*2
# end of configuration


if len(sys.argv) < 2:
    sys.exit('Usage: %s  <input_file_name.hex> [<output_file_name.c>]' % sys.argv[0])

if not os.path.exists(sys.argv[1]):
    sys.exit('ERROR: %s was not found!' % sys.argv[1])

in_filename = sys.argv[1]

out_fileName = "hex_to_c.c"
if len(sys.argv) > 2:
    out_fileName = sys.argv[2]


lines = HexParser(in_filename, page_size=bytesPerPage)
firstAddress = lines.get_start_addr()
lastAddress = lines.get_end_addr()

print("first address: 0x%0.6X" % firstAddress)
print("last address detected: 0x%0.6X" % lastAddress)

if lastAddress > max_valid_address:
    lastAddress = max_valid_address
    print("last address considered: 0x%0.6X" % lastAddress)

print("\nWriting " + outputFileName)
f = open(outputFileName, 'w')
f.write("#include \"hex_to_c.h\"\n\n")

byteDataFinished = False
dataToWrite = []
pageAddressMSW = []
pageNumber = []


# write program flash data (byte arrays)
for page_addr in range(firstAddress, lastAddress, bytesPerPage):
    blank_counter = 0

    for dataAddr in range(page_addr, page_addr + bytesPerPage):
        try:
            lines.get_byte(dataAddr)
        except:
            blank_counter += 1

    if blank_counter < bytesPerPage:
        print("writing page: %d" %(page_addr / bytesPerPage))
        # if the whole page is not empty
        process = False
        phantom_byte_index = 0  # used to locate the phantom bytes within the hex file(every fourth)
        for dataAddr in range(page_addr, page_addr + bytesPerPage):

            if byteDataFinished:
                dataToWrite.append(",\n")
                byteDataFinished = False

            if not process:
                process = True
                pageAddressMSW.append("%0.4X" % (page_addr >> 16))
                pageNumber.append(page_addr / bytesPerPage)
                dataToWrite = ["const uint8_t fData" + str(len(pageAddressMSW)-1) + "[] =\n", "{\n"]

            try:
                value = lines.get_byte(dataAddr)
                phantom_byte_index += 1
                if phantom_byte_index < 4:
                    dataToWrite.append("    0x%0.2X" % value)
                    byteDataFinished = True
                else:
                    phantom_byte_index = 0
                    if value > 0:
                        # not a phantom byte, so an error occurred
                        sys.exit("Error aligning the bytes")
            except:
                phantom_byte_index += 1
                if phantom_byte_index < 4:
                    dataToWrite.append("    0xFF")
                    byteDataFinished = True
                else:
                    phantom_byte_index = 0


        dataToWrite.append("\n};\n\n")
        f.writelines(dataToWrite)
        dataToWrite.clear()

    # else:
    #     print("page number: %d is blank" % (page_addr/bytesPerPage))

# Group byte arrays in page structure
f.write("const hexToC_t hexToC[] =\n{\n")
pageDataFinished = False
for i in range(0, len(pageAddressMSW)):
    if pageDataFinished:
        f.write(",\n")
        pageDataFinished = False

    f.write("    {\n")
    f.write("        " + str("%d" % pageNumber[i]) + ",\n")
    f.write("        fData" + str(i) + "\n")
    f.write("    }")
    pageDataFinished = True
f.write("\n};\n\n")
f.write("uint16_t hexToCLength = sizeof(hexToC)/sizeof(hexToC_t);\n")

f.close()
