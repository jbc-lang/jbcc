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
Record = Shop.Prices.Prices.Read("item", Error)
Record = Shop.Prices.Prices.CacheRead("item", "")
Record<Shop.Prices.Prices.UnitPrice> = 25
Shop.Prices.Prices.Write("item", Record)
Shop.Prices.Prices.WriteNau("draft", Record)
Shop.Prices.Prices.WriteHis("archived", Record)
Shop.Prices.Prices.Delete("item")
CRT Shop.Prices.Ledger.ReadNau("item", Error)
Shop.Shared.setQuantity(1)
CRT Record<Shop.Shared.Items.Cost> : Shop.Shared.getQuantity()
