* As TAFC PB201214 runs it: each element sets STATUS() as ICONV or OCONV
* would, so the last element decides (tests/tafc/conversion-chains.b).
* MT and MTS convert times to values measured in seconds since midnight.
CRT ICONV('00:01:02', 'MTS')
CRT ICONV('1:00 PM', 'MT')
* The guide preserves empty elements and reports invalid data through STATUS.
A = @FM:'9:00':@VM:@SVM:'23:59:59':@FM
CRT ICONVS(A, 'MT')
CRT STATUS()
CRT ICONVS('19671231':@VM:'19680101', 'D4')
CRT STATUS()
CRT '[':ICONVS('', 'D'):']'
CRT STATUS()
CRT '[':ICONVS('00:00':@VM:'25:00', 'MT'):']'
CRT STATUS()
CRT '[':ICONVS('19671231', 'D':@VM:'D4'):']'
CRT STATUS()
CRT ICONVS(@FM:@VM, 'D':@VM:'MT')
CRT STATUS()
CRT '[':ICONVS('01:00', 'DUMMY'):']'
CRT STATUS()
