* The MX mask, from the guide's FMT, ICONV and OCONV examples.
X = 'ABCDEF'
CRT FMT(X, 'MX')
CRT FMT(@FM, 'MX'), OCONV(@VM:@SM, 'MX')
CRT ICONV('4020412042', 'MX')
CRT ICONV('414243', 'MX'), ICONV('6a6B', 'MX'), '[':ICONV('', 'MX'):']', '[':OCONV('', 'MX'):']'
* The DG mask: YYYYMMDD, as in the guide's ICONV('20231031', 'DG') and as
* T24 R19 slices OCONV(date, "DG") into [1,4], [5,2] and [7,2].
Internal = ICONV('20231031', 'DG')
CRT Internal, OCONV(Internal, 'D4/E'), OCONV(Internal, 'DG')
UTCDate = OCONV(732, 'DG')
CRT UTCDate[1,4]:'-':UTCDate[5,2]:'-':UTCDate[7,2]
CRT OCONV(1, 'DG'), OCONV(-731, 'DG')
CRT OCONV(ICONV('20240229', 'DG'), 'DG')
