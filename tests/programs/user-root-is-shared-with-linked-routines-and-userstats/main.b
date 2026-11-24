CRT '[':@USER.ROOT:']'
Before = @USERSTATS
CALL PUBLISH
Saved = @USER.ROOT
Published = @USERSTATS
@USER.ROOT = 'updated'
CRT '[':Before<28>:']', LEN(Saved), LEN(Published<28>), @USERSTATS<28>
CRT Saved = Published<28>
@USER.ROOT = ''
CRT '[':@USER.ROOT:']:[':@USERSTATS<28>:']'
