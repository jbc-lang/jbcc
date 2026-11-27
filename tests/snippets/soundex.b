* SOUNDEX follows the guide's table. It keeps the first letter, ignores
* other characters and reads a repeated letter once.
CRT SOUNDEX('Robert'):' ':SOUNDEX('rupert'):' ':SOUNDEX('Tymczak')
CRT SOUNDEX('Lee'):' ':SOUNDEX('Ashcraft'):' ':SOUNDEX('Pfister')
CRT '[':SOUNDEX('123'):'] ':SOUNDEX(' 9x')
