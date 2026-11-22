Text = 'north/west/east/south'
PRINT Text['/',2,1], Text['/',2,3]
PRINT Text['/',3,99], LEN(Text['/',5,1])
Record = 'head' : @FM : 'a::::ccc::d'
Sep = '::'
Start = 1
PRINT Record<2>[Sep,Start+1,2], Record<2>[Sep,3,1][2,2]
PRINT (Record['!',1,1])<1>, Record<2>[Sep,2,2] = FIELD(Record<2>,Sep,2,2)
