* As TAFC PB201214 runs it: each element sets STATUS() as ICONV or OCONV
* would, so the last element decides (tests/tafc/conversion-chains.b).
* Valid elements are formatted, and invalid elements retain original text.
A = @FM:0:@VM:@SVM:'invalid':@FM:62
CRT OCONVS(A, 'MTS')
CRT STATUS()
CRT OCONVS(0:@VM:1, 'D4/')
CRT STATUS()
* Chained codes work left to right. A D code takes the rest of the chain,
* and one TAFC cannot read gives the value back.
CRT OCONVS(0:@VM:1, 'DD':@VM:'MTS')
CRT STATUS()
CRT OCONVS('0000':@VM:'0010', 'MTS':@VM:'D')
CRT STATUS()
CRT '[':OCONVS('', 'D'):']'
CRT STATUS()
CRT '[':OCONVS('1', 'D':@VM:'DUMMY'):']'
CRT STATUS()
