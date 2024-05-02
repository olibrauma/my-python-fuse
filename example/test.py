from silo import Silo

silo = Silo()

print(silo.stat('/test/sumo-chess.jpg'))

for crop in silo:
    print(crop)