CREATE TABLE file_path (extract TEXT, rel TEXT, kind TEXT, component_name TEXT);
INSERT INTO file_path VALUES
  ('sample-r19', 'Shop.Prices.component', 'component', 'Shop.Prices'),
  ('sample-r19', 'Main.b', 'jbc_source', NULL),
  ('sample-r19', 'WrongArity.b', 'jbc_source', NULL),
  ('sample-r19', 'WrongKind.b', 'jbc_source', NULL),
  ('sample-r19', 'PrivateAccess.b', 'jbc_source', NULL),
  ('sample-r19', 'ModuleAccess.b', 'jbc_source', NULL),
  ('sample-r19', 'VoidExpression.b', 'jbc_source', NULL);
