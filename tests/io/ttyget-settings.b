P = GETENV('JBCC_TEST_PTY')
OPENDEV P TO F ELSE ABORT
TTYGET Settings FROM F SETTING S ELSE ABORT
CRT S:':':STATUS()
CRT Settings<1,1>:':':Settings<1,2>:':':Settings<1,3>
CRT Settings<7,1>:':':Settings<10,2>:':':Settings<10,3>
CRT Settings<10,4>:':':Settings<10,5>:':':Settings<11,1>:':':Settings<11,3>
CLOSESEQ F
