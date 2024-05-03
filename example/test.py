from silo import Silo

silo = Silo()

print(silo.stat('/test/sumo-chess.jpg'))

for crop in silo:
    print(crop)

path = '/folder1/folder2/file'

path1 = silo._backtrack(path, 0)
path2 = silo._backtrack(path, 1)
path3 = silo._backtrack(path, 2)
path4 = silo._backtrack(path, 3)
path5 = silo._backtrack(path, 4)

print(path1)
print(path2)
print(path3)
print(path4)
print(path5)