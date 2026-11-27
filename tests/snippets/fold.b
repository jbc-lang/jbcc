* The guide wraps at spaces, splits long words and treats zero as one.
CRT CONVERT(@FM, '^', FOLD('Words grow longer', 5))
CRT CONVERT(@FM, '^', FOLD('  ab  cd   ef ', 7))
CRT CONVERT(@FM, '^', FOLD('xx extraordinary', 5))
CRT CONVERT(@FM, '^', FOLD('ab cd', 0))
CRT CONVERT(@FM, '^', FOLD('wide   gap', 1000000000))
CRT CONVERT(@FM, '^', FOLD('abcd':@FM:@FM:'ef', 2))
CRT '[':FOLD('', 4):'][':FOLD('   ', 4):']'
