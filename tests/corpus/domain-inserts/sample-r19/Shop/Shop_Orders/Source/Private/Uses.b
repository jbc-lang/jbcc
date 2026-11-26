* Field positions come from the generated I_OrderService_Line, built from
* the Line class: sku, quantity, notes (multi-valued) and the header
* association. I_OrderService_Header exists in the extract and wins.
SUBROUTINE Uses(Line)
$INSERT I_OrderService_Line
$INSERT I_OrderService_Header
Line<Line.quantity> = Line<Line.sku> : Line<Line.header, 1, Header.number>
RETURN
END
