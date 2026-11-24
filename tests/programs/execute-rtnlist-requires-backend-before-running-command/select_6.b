DIM Rows(2)
RTNLIST = 'name'
IF 0 THEN EXECUTE 'touch child-ran' RTNLIST ELSE CRT RTNLIST
PERFORM 'touch child-ran' RTNLIST "7"
CRT 'after'
