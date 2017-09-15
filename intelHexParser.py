"""
Created on 17.06.2015.
@author: Rada Berar
written for python 3 grammar

TODO: change the mem lest into an oredered dictionary
"""

from builtins import int, str
import sys
import os

# global defines
deleted_string = "Deleted"


class AddressError(Exception):
    def __init__(self, value):
        self.value = value

    def __str__(self):
        return repr(self.value)


def calculate_parity(string_line):
    """
    Calculates the parity for a line of bytes in an Intel hex file.
    Returns the text representation of the parity value in hex form.
    """
    c_byte = 0
    for i in range(0, len(string_line), 2):
        c_byte_str = string_line[i: i+2]
        c_byte += int(c_byte_str, 16)         
    c_byte = (~c_byte + 1) & 0xFF 
    return str.lower("%0.2X" % c_byte)


class ByteData:
    """
    Stores address, value, row and column of a byte found in an Intel hex file
    """
    def __init__(self, address, value, row, column):
        self.address = address
        self.value = value
        self.row = row
        self.column = column


class HexParser:
    """
    Parses an Intel hex file and saves the contents in a list of byteData objects.
    Also provides methods for fetching and altering data as well as writing to the hex file.   
    Usage: 
        <object name> = hexParser(<input hex file name>)
    """
    
    def __init__(self, in_file_name, page_size):
        self.inFileName = in_file_name
        self.content = []
        self.memData = []
        self.address_mem = {}
        self.minAddr = 0xFFFFFFFF
        self.maxAddr = 0
        self.page_size = page_size

        if not os.path.exists(in_file_name):
            sys.exit('ERROR: %s was not found!' % in_file_name)

        # reading the contents of the hex file
        f = open(self.inFileName, 'r') 
        self.content = f.read().splitlines()
        f.close()
        
        current_address_offset = ""
        # parsing the hex file content
        for lineNumber in range(0, len(self.content)):
            line = self.content[lineNumber]

            if line.startswith(':'):
                line = line[1:len(line)]                       
                reclen = int(line[0:2], 16)             
                addr = int(line[2:6], 16)
                rectype = int(line[6:8], 16)
                data = line[8: (8 + reclen*2)]
                
                if rectype == 1:
                    # end of record reached
                    break
                
                if rectype == 4:
                    addr_offset = data[0: 4]

                    if addr_offset != "0000":
                        current_address_offset = addr_offset

                for i in range(0, reclen):
                    column = 9 + i*2
                                
                    value = int(data[(i*2): (i*2 + 2)], 16) 
                               
                    if rectype == 0:
                        address = addr + i
                        data_addr = (int(current_address_offset, 16) << 16) + address

                        self.memData.append(ByteData(data_addr, value, lineNumber, column))
                        self.address_mem["%0.8X" % data_addr] = 1

                        # adjusting the minimum and maximum found address
                        if data_addr > self.maxAddr:
                            self.maxAddr = data_addr
                            # print("%0.8X" % data_addr)
                        if data_addr < self.minAddr:
                            self.minAddr = data_addr

    def write_to_hex(self, out_file_name):
        """
        hexParser method for writing the content to a hex file.
        usage:
            <obj name>.writeToHex(<output hex file name>)
        """
        global deleted_string

        f = open(out_file_name, 'w')
        for line in self.content:
            if line != deleted_string:
                f.write(line)
                f.write("\n")
        f.close()

    def get_byte(self, address):
        """
        hexParser method for getting the value of a oneByte at the specified address.
        usage:
            <object name>.getByte(<address>)
        returns:
            8 bit value if the address was found,
            string "ERROR" otherwise
        """
        try:
            temp = self.address_mem["%0.8X" % address]
        except:
            raise AddressError("Address not found! 0x%0.8X" % address)
        for oneByte in self.memData:
            if oneByte.address == address:
                return oneByte.value        
                break

    def get16(self, address):
        """
        hexParser method for getting the value of two consecutive bytes starting 
        at the specified address in big endian format (MSB first)
        usage:
            <object name>.get16(<address>)
        returns:
            16 bit value if two consecutive requested addresses were found,
            string "ERROR" otherwise
        """

        return (self.get_byte(address + 1) << 8) + self.get_byte(address)
            
    def get32(self, address):
        """
        hexParser method for getting the value of 4 consecutive bytes starting 
        at the specified address in big endian format (MSB first).
        usage:
            <object name>.get32(<address>)
        returns:
            32 bit value if 4 consecutive requested addresses were found,
            string "ERROR" otherwise
        """
        retVal = 0
        for i in range(0, 4):
            retVal += self.get_byte(address + i) << (i*8)

        return retVal
    
    def set_byte(self, address, value):
        """
        hexParser method for altering the value of a oneByte at a specific address.
        usage:
            <object name>.setByte(<address>, <value>)
        returns: 
            True if the address was found, 
            False otherwise.
        """
        
        addr_found_flag = False
        
        for oneByte in self.memData:
            if oneByte.address == address:
                oneByte.value = value
                addr_found_flag = True
                # change content of the hex
                line = self.content[oneByte.row][1:len(self.content[oneByte.row])]
                
                modified_line = line[0:(oneByte.column-1)] + str.lower("%0.2X" % oneByte.value) + line[(oneByte.column + 1):len(line) - 2]
                modified_line += calculate_parity(modified_line)
                self.content[oneByte.row] = ':' + modified_line
                break                
        
        return addr_found_flag
    
    def set16(self, address, value):
        """
        hexParser method for altering the value of 2 bytes at the specified 
        address in big endian format (MSB first).
        usage:
            <object name>.set16(<address>, <value>)
        returns: 
            True if the address was found,
            False otherwise.
        """
                
        if not self.set_byte((address + 1), (value >> 8) & 0xFF):
            return False
        
        return self.set_byte(address, value & 0xFF)
                   
    def set32(self, address, value):
        """
        hexParser method for altering the value of 4 consecutive bytes at 
        the specified address in big endian format (MSB first).
        usage:
            <object name>.set32(<address>, <value>)
        returns: 
            True if the address was found,
            False otherwise.
        """

        if self.set_byte(address + 3, value & 0xFF):
            if self.set_byte((address + 2), (value >> 8) & 0xFF):
                if self.set_byte((address + 1), (value >> 16) & 0xFF):
                    return self.set_byte(address, (value >> 24) & 0xFF)
                        
        return False
          
    def get_start_addr(self):
        return self.minAddr
    
    def get_end_addr(self):
        return self.maxAddr

    def get_same_page_min_addr(self, address):
        """
        :param address:
        :return: Minimum address in the same address segment (Program flash or boot flash)
        """
        min_address = self.maxAddr

        for sample in self.memData:
            if (sample.address // self.page_size) == (address // self.page_size):
                if min_address > sample.address:
                    min_address = sample.address

        return min_address

    def get_same_page_max_addr(self, address):
        """
        :param address:
        :return: Maximum address in the same address segment (Program flash or boot flash)
        """
        max_address = self.minAddr

        for sample in self.memData:
            # print("0x%0.8X" % sample.address)
            if (sample.address // self.page_size) == (address // self.page_size):

                if max_address < sample.address:
                    max_address = sample.address

        return max_address

    def get_page_start_address(self, address):
        return (address // self.page_size) * self.page_size

    def delete_row(self, row):
        global deleted_string
        self.content[row] = deleted_string
