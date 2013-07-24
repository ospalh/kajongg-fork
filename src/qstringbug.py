import sip
sip.setapi('QString', 2)
from PyKDE4.kdeui import KConfigSkeleton
a = KConfigSkeleton()
name = 'tilesetName'
value = 'I am a value'
print('value:',value)
s = a.addItemString(name, value)
print('now we get the bug:')
print(s.value() )
