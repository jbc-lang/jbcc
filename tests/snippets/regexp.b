* Guide REGEXP examples.
String = "jBASE Software Inc."
CRT REGEXP(String, 'S[^t]*')
CRT REGEXP('051', '^(050|5001|051|053|265|4007|5007|037|060|098)$')
CRT REGEXP('05123', '^(050|5001|051|053|265|4007|5007|037|060|098)$')
CRT REGEXP('036', '(0[0-24-9][0-9]|0[0-9][0-68-9]|[1-9][0-9][0-9])')
CRT REGEXP('037', '(0[0-24-9][0-9]|0[0-9][0-68-9]|[1-9][0-9][0-9])')
CRT REGEXP('137', '(0[0-24-9][0-9]|0[0-9][0-68-9]|[1-9][0-9][0-9])')
CRT REGEXP('RS', '([A-QS-Z][A-Z]|[R][A-RT-Z])')
CRT REGEXP('RU', '([A-QS-Z][A-Z]|[R][A-RT-Z])')
* An invalid expression returns -1.
CRT REGEXP('bar', '"^(?!.*?bar).*"')
