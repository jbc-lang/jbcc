* Guide BITCHANGE example: bit 100 starts at zero.
OLD.VAL = BITCHANGE(100)
CRT OLD.VAL:BITCHECK(100):BITCHANGE(100):BITCHECK(100)
* Guide BITSET and BITRESET examples with bit 112.
CRT BITSET(112):BITSET(112):BITRESET(112):BITRESET(112)
* Guide BITLOAD example: bits beyond the 64th are reset.
X = BITSET(128)
VALUE.NEW = "0123456789ABCDEF"
VALUE.OLD = BITLOAD(VALUE.NEW)
CRT VALUE.OLD
CRT BITLOAD():' ':BITCHECK(8):BITCHECK(7):BITCHECK(128)
* Loading stops at a non-hexadecimal character.
X = BITLOAD("8z1")
CRT BITLOAD():' ':BITCHECK(1)
* Bit 0 sets or resets the whole table.
CRT BITSET(0):' ':BITLOAD()
CRT BITRESET(0):'[':BITLOAD():']'
* Codes -1 to -3 are kept as switches outside the table.
CRT BITSET(-1):BITCHECK(-1):BITCHANGE(-1):BITCHECK(-1):'[':BITLOAD():']'
