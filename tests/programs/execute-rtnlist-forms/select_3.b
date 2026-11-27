DIM Rows(2)
RTNLIST = 'name'
IF 0 THEN EXECUTE 'touch child-ran' RTNLIST ELSE CRT RTNLIST
EXEC 'touch child-ran' RTNLIST CAPTURING Out RETURNING Status
CRT 'after'
