* tafc-emulation: prime
* TAFC-CROSSCHECK.md section 5: MCPN and MCNP.
X = 'a':@FM:'b':CHAR(1):CHAR(200):'_.~':CHAR(127)
CRT OCONV(X, 'MCPN')
CRT OCONV(X, 'MCPN~')
CRT OCONV(OCONV('a.FEb.7E', 'MCNP'), 'MX')
CRT OCONV(OCONV('a~FEb~4', 'MCNP~'), 'MX')
CRT OCONV(OCONV('a_FEb', 'MCNP'), 'MX')
