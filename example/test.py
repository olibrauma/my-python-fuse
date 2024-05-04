from silo import Silo
silo = Silo()

def func(**kw):
    print(kw)

a = {'key': 'value'}
func(**a)