from silo import Silo
silo = Silo()

people = [{'name': 'taro', 'age': 12}, {'name': 'jiro', 'age': 8}]

adults = filter(lambda p: p['age'] >= 18, people)
names = list(map(lambda p: p['name'], people))
print(names)