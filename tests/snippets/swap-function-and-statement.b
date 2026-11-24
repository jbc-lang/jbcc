Text = '::first::second::'
CRT SWAP(Text, '::', '|')
CRT Text
CRT SWAP('aaaaa', 'aa', 'b', 1), SWAP('aaaaa', 'aa', 'b', 1, 2)
CRT SWAP('tail', '', 'head:')
R = Text:@FM:'second'
SWAP '::' WITH '|' IN R<1>
CRT R<1>, R<2>
SWAP '|' TO '' IN R<1>
CRT R<1>
