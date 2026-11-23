* The guide wraps at spaces, splits long words and treats zero as one.
CRT CONVERT(FOLD('Words grow longer', 5), @FM, '^')
CRT CONVERT(FOLD('  ab  cd   ef ', 7), @FM, '^')
CRT CONVERT(FOLD('xx extraordinary', 5), @FM, '^')
CRT CONVERT(FOLD('ab cd', 0), @FM, '^')
CRT CONVERT(FOLD('wide   gap', 1000000000), @FM, '^')
CRT CONVERT(FOLD('abcd':@FM:@FM:'ef', 2), @FM, '^')
CRT '[':FOLD('', 4):'][':FOLD('   ', 4):']'
