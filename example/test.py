from silo import Silo

silo = Silo()

for crop in silo:
    print(crop)

silo.discard('/beer-girl.jpg')
print(silo.list())