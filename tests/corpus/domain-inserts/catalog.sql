CREATE TABLE file_path (id INTEGER, extract TEXT, rel TEXT, kind TEXT, module TEXT, component TEXT, component_name TEXT);
CREATE TABLE domain_field (file_id INTEGER, domain TEXT, class TEXT, position INTEGER, name TEXT, type TEXT, many INTEGER, association INTEGER);
INSERT INTO file_path VALUES
  (1, 'sample-r19', 'Shop/Shop_Orders/Definition/Shop.OrderService.component', 'component', 'Shop', 'Shop_Orders', 'Shop.OrderService'),
  (2, 'sample-r19', 'Shop/Shop_Orders/Definition/OrderDomain.domain', 'domain', 'Shop', 'Shop_Orders', NULL),
  (3, 'sample-r19', 'Shop/Shop_Archive/Definition/Old.OrderService.component', 'component', 'Shop', 'Shop_Archive', 'Old.OrderService'),
  (4, 'sample-r19', 'Shop/Shop_Archive/Definition/ArchiveDomain.domain', 'domain', 'Shop', 'Shop_Archive', NULL),
  (5, 'sample-r19', 'Shop/Shop_Orders/Source/Private/Uses.b', 'jbc_source', 'Shop', 'Shop_Orders', NULL),
  (6, 'sample-r19', 'Shop/Shop_Orders/Source/Private/Missing.b', 'jbc_source', 'Shop', 'Shop_Orders', NULL),
  (7, 'sample-r19', 'Shop/Shop_Orders/Source/Private/Ambiguous.b', 'jbc_source', 'Shop', 'Shop_Orders', NULL),
  (8, 'sample-r19', 'Shop/Shop_Orders/Source/Public/I_OrderService_Header', 'jbc_include', 'Shop', 'Shop_Orders', NULL);
INSERT INTO domain_field VALUES
  (2, 'OrderDomain', 'Line', 1, 'sku', 'mml:string', 0, 0),
  (2, 'OrderDomain', 'Line', 2, 'quantity', 'mml:string', 0, 0),
  (2, 'OrderDomain', 'Line', 3, 'notes', 'mml:string', 1, 0),
  (2, 'OrderDomain', 'Line', 4, 'header', 'OrderDomain:Header', 0, 1),
  (2, 'OrderDomain', 'Header', 1, 'fromDomain', 'mml:string', 0, 0),
  (2, 'OrderDomain', 'Note', 1, 'text', 'mml:string', 0, 0),
  (4, 'ArchiveDomain', 'Note', 1, 'author', 'mml:string', 0, 0),
  (4, 'ArchiveDomain', 'Note', 2, 'text', 'mml:string', 0, 0);
