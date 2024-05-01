from silo import Silo

silo = Silo()

silo.pack('/hello', b'Hello World!', 0)
silo.store('/hello')

for crop in silo:
    print(crop)