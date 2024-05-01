from silo import Silo

silo = Silo()

for crop in silo:
    print(crop)

silo.stat('/beer-girl.jpg')
silo.list()