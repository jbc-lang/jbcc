* STATUS after ICONVS and OCONVS: TAFC PB201214 reports 1 in nearly every
* case here; jbcc keeps the guide's rules (TAFC-CROSSCHECK.md section 5).
* Valid elements are formatted, and invalid elements retain original text.
A = @FM:0:@VM:@SVM:'invalid':@FM:62
CRT OCONVS(A, 'MTS')
CRT STATUS()
CRT OCONVS(0:@VM:1, 'D4/')
CRT STATUS()
* Chained codes work left to right. A failing stage restores the input element.
CRT OCONVS(0:@VM:1, 'DD':@VM:'MTS')
CRT STATUS()
CRT OCONVS('0000':@VM:'0010', 'MTS':@VM:'D')
CRT STATUS()
CRT '[':OCONVS('', 'D'):']'
CRT STATUS()
CRT '[':OCONVS('1', 'D':@VM:'DUMMY'):']'
CRT STATUS()
