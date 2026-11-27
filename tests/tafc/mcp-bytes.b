* tafc-emulation: prime
* TAFC-CROSSCHECK.md section 4: MCP for bytes outside 32 to 126.
X = '.':CHAR(127):CHAR(31):' ~':CHAR(255):CHAR(251):CHAR(250):CHAR(128):@FM:@VM:@SM
CRT OCONV(X, 'MCP')
CRT OCONV(X, 'MCP_')
