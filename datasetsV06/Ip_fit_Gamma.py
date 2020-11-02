from scipy.stats import gamma
from pathlib import Path
from numpy import genfromtxt


path = Path.cwd() / 'datasetsV06' / 'Ip_stage2.csv'
x = genfromtxt(path, delimiter=',')
a, loc, scale = gamma.fit(x)

print(a, loc, scale)