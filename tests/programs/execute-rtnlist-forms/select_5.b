DIM Rows(2)
RTNLIST = 'name'
IF 0 THEN EXECUTE 'touch child-ran' RTNLIST ELSE CRT RTNLIST
EXECUTE 'touch child-ran' RTNLIST 2
CRT 'after'
