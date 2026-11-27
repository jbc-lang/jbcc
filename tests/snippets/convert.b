Value = 'ABCDEFGHIJ'
CONVERT 'BJE' TO '^+!' IN Value
PRINT Value
Original = 'ab-cab'
PRINT CONVERT('ab-', 'ba', Original), Original
CONVERT '-' TO '' IN Original
PRINT Original
PRINT CONVERT('', 'xyz', 'abc'), CONVERT('aab', '1234', 'aba')
DIM Rows(2)
Rows(1) = 'left' : @FM : 'b|c' : @VM : 'd|e'
Rows(2) = 'untouched'
CONVERT '|' TO @SM IN Rows(1)<2,2>
PRINT Rows(1)<1>, Rows(1)<2,1>, Rows(1)<2,2,2>, Rows(2)
CONVERT @FM : @VM : @SM TO '/:;' IN Rows(1)
PRINT Rows(1)
Map = 'ab'
CONVERT Map TO 'xy' IN Map
PRINT Map
