from matplotlib.pyplot import *


prices = [(4.29, 1.4),
          (6.99, 2.4),
          (11.29, 4),
          (17.69, 8)]

for price, amount in prices:
    print(price / amount)


cf = [(amount, price / amount) for price, amount in prices]



f, ax = subplots(1)
xdata, ydata = zip(*cf)
ax.plot(xdata, ydata, "bo")
ax.set_ylim(bottom=0)
show()
