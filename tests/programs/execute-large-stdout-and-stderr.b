EXECUTE "awk 'BEGIN {for(i=0;i<65536;i++) print 1}' >&2; cat" RETURNING R CAPTURING O
CRT R
CRT O:
