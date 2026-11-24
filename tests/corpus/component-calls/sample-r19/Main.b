$PACKAGE Shop.Prices
DIM Shop.Prices.Local(2)
MAT Shop.Prices.Local = 2
Shop.Prices.Caption = "unit"
Shop.Prices.setCurrent(Shop.Prices.Separator)
CRT Shop.Prices.Caption : Shop.Prices.GetCurrent()[Shop.Prices.Separator,1,1]
CRT SHOP.PRICES.FORMAT(Shop.Prices.Local(1), MAT Shop.Prices.Local)
CRT Shop.Prices.Format("empty matrix", "")
Shop.Prices.setItems(1, "unit")
CRT Shop.Prices.getItems(1)
Shop.Prices.setDynArrayToItems(Shop.Prices.getDynArrayFromItems())
CALL Shop.Prices.Clear()
Shop.Prices.Reset()
