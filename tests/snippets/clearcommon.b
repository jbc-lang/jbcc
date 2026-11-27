* CLEARCOMMON as in T24 R19 session resets; values from the guide's example.
COMMON /MY.COMM/ global_var
COMMON gl_unnamed, gl_rows(2)
global_var = 1000
gl_unnamed = 1001
gl_rows(1) = 'a' ; gl_rows(2) = 'b'
CLEARCOMMON
CRT global_var
CRT gl_unnamed
CRT gl_rows(1), gl_rows(2)
gl_unnamed += 5
CRT gl_unnamed
