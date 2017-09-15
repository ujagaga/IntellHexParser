#!/usr/bin/python3.4

from os.path import sys
import os
from intelHexParser import HexParser


# configuration
bytesPerPage = 1024
# end of configuration

in_filename = "test.hex"


lines = HexParser(in_filename, page_size=bytesPerPage)

address = 0x1D020000 - 4

print("0x%0.2X " %lines.get_byte(address))

lines.set_byte(address, 0)
lines.write_to_hex("result.hex")
