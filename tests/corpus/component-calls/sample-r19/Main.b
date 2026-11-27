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
Shop.Prices.clearItems()
Shop.Prices.clearCurrent()
* Declaration forms from R19: a result type before the parameters
* (EB.API.setException), an external service method with domain types
* (ST.CustomerService.getRecord) and newline-separated parameters
* (TF.ErrorHandling.setException).
Shop.Prices.Tally("label")
CRT Shop.Prices.Tally("label")
Shop.Prices.lookupItem("item", Item)
Shop.Prices.Note("code", "text")
CALL Shop.Prices.Clear()
Shop.Prices.Reset()
Record = Shop.Prices.Prices.Read("item", Error)
Record = Shop.Prices.Prices.CacheRead("item", "")
Record<Shop.Prices.Prices.UnitPrice> = 25
Shop.Prices.Prices.Write("item", Record)
Shop.Prices.Prices.WriteNau("draft", Record)
Shop.Prices.Prices.WriteHis("archived", Record)
Shop.Prices.Prices.Delete("item")
Record = Shop.Prices.Prices.ReadU("item", Error, "")
Shop.Prices.Prices.ReadU("item", Error, "")
Record = Shop.Prices.Prices.ReadUNau("draft", Error, "")
Record = Shop.Prices.Prices.ReadHis("item;1", Error)
Record = Shop.Prices.Prices.ReadUHis("item;1", Error, "")
Record = Shop.Prices.tablePrices("item", Error)
Shop.Prices.Prices.DeleteNau("draft")
Shop.Prices.Prices.DeleteHis("archived")
CRT Shop.Prices.Ledger.ReadNau("item", Error)
Shop.Shared.setQuantity(1)
CRT Record<Shop.Shared.Items.Cost> : Shop.Shared.getQuantity()
* As in R19 IN getBICfromIBAN: IF UNASSIGNED(IN.Config.getBicDetails()) THEN
IF UNASSIGNED(Shop.Shared.getQuantity()) THEN CRT "unassigned"
CRT ASSIGNED(Shop.Prices.getItems(1))
* Interfaces, as in R19 AA.ActivityHook.checkValidateRoutine(methodName, ...)
Shop.Prices.priceCheck("PRICE.CHECK", "item", "A":@VM:"B")
CRT Shop.Prices.adjustedPrice("ADJUSTED.PRICE", "item")
* Matrix properties with a rank, as in R19 FX.Contract.getMatLeg(LEG, FLD.NO)
Shop.Prices.setGrid(1, 2, "cell")
CRT Shop.Prices.getGrid(1, 2), Shop.Prices.getRates(3)
Shop.Prices.setDynArrayToGrid(Shop.Prices.getDynArrayFromGrid())
* A placeholder scalar for a matrix parameter, as in R19
* ST.CompanyCreation.EbReadParameter(file, lock, DIM.REC, R.REC, ...)
Placeholder = ""
CRT Shop.Prices.Format("label", Placeholder), Placeholder
* A table the export does not declare, as in PP.SODEODGUI.PptSodeodjoblist.Read
Record = Shop.Prices.Archive.Read("item", Error)
Shop.Prices.Archive.Write("item", Record)
