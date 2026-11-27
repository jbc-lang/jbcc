CREATE TABLE file_path (extract TEXT, rel TEXT, kind TEXT, module TEXT, component TEXT);
INSERT INTO file_path VALUES
  ('sample-r19', 'AA/Account/Private/Main.b', 'jbc_source', 'AA', 'Account'),
  ('sample-r19', 'AA/Account/Private/Missing.b', 'jbc_source', 'AA', 'Account'),
  ('sample-r19', 'AA/Account/Private/Ambiguous.b', 'jbc_source', 'AA', 'Account'),
  ('sample-r19', 'AA/Account/Private/Twin.b', 'jbc_source', 'AA', 'Account'),
  ('sample-r19', 'AA/Account/Private/I_Local', 'jbc_include', 'AA', 'Account'),
  ('sample-r19', 'AA/Account/Public/I_Choice', 'jbc_include', 'AA', 'Account'),
  ('sample-r19', 'BB/Billing/Public/I_Choice', 'jbc_include', 'BB', 'Billing'),
  ('sample-r19', 'BB/Billing/Public/I_Global', 'jbc_include', 'BB', 'Billing'),
  ('sample-r19', 'BB/Billing/Public/I_Tied', 'jbc_include', 'BB', 'Billing'),
  ('sample-r19', 'Flat/I_Tied', 'jbc_include', NULL, NULL),
  ('sample-r19', 'BB/Billing/Public/I_Twin', 'jbc_include', 'BB', 'Billing'),
  ('sample-r19', 'Flat/I_Twin', 'jbc_include', NULL, NULL),
  ('sample-r19', 'AA/Account/Private/Fixture.tut', 'jbc_test', 'AA', 'Account');
