CREATE TABLE file (extract TEXT, rel TEXT, kind TEXT);
CREATE VIEW file_path AS SELECT extract, rel, kind FROM file;
INSERT INTO file VALUES
    ('sample-r07', 'GLOBUS.BP/Constants.h', 'jbc_include'),
    ('sample-r07', 'GLOBUS.BP/I_Unit', 'jbc_source'),
    ('sample-r07', 'GLOBUS.BP/Main.b', 'jbc_source'),
    ('sample-r07', 'GLOBUS.BP/Native.h', 'c_header'),
    ('other-extract', 'GLOBUS.BP/Constants.h', 'c_header'),
    ('other-extract', 'GLOBUS.BP/Native.h', 'jbc_source');
