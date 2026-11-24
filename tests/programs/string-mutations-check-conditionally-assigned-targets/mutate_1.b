GET(ARG.) Key
LOCATE Key IN 'found' SETTING Pos THEN
    Value = 'left':@FM:'aabb'
END
CONVERT 'a' TO 'x' IN Value
Value := '!'
CRT Value<1>, Value<2>
