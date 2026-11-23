* The guide defines BYTELEN as the encoded byte count.
CRT BYTELEN('')
CRT BYTELEN('abc')
CRT BYTELEN('é漢😀')
CRT BYTELEN('é':@FM:@VM:@SM:'漢')
CRT BYTELEN(CHAR(255):CHAR(128))
