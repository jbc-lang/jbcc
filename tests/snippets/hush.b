CRT 'before':
HUSH ON
HUSH ON
PRINT 'hidden'
CRT NEG('invalid')
EXECUTE "printf hidden"
EXECUTE "printf captured" CAPTURING VALUE
HUSH OFF
CRT VALUE
HUSH 1 + 1
CRT 'hidden'
HUSH 0
CRT 'restored'
IF 1 THEN HUSH ELSE NULL
CRT 'hidden'
HUSH
CRT 'after toggle'
