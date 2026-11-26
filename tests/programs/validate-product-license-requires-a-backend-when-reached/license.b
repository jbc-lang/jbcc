* VALIDATE_PRODUCT_LICENSE as in T24 R13 DM.GENERATE.ERWIN. The local
* jbccom 201015.001 reference lowers it to a TAFC licence check.
Product = 'DM_EXPORT'
IF 0 THEN CRT VALIDATE_PRODUCT_LICENSE(Product)
CRT 'before'
IF NOT(VALIDATE_PRODUCT_LICENSE(Product)) THEN CRT 'unlicensed'
CRT 'after'
