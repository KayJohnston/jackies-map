# Riedquat (68.84375, 69.75, 48.75)
# Reorte (75.75, 75.15625, 48.75)

Ri = (68.84375, 69.75, 48.75)
Re = (75.75, 75.15625, 48.75)

Slope = (Re[0] - Ri[0], Re[1] - Ri[1], Re[2] - Ri[2])

print('Riedquat:',Ri)
print('Reorte:',Re)
print()
print('Slope:',Slope)

ratio = Slope[1] / Slope[0]

print('Ratio (y = nx):',ratio)

Ri_base = Ri[0] * ratio

print('Ri_base:',Ri_base)

constant = Ri[1] - Ri_base

print('Constant (y = nx + k):',constant)
print()

Zu = (-9529.4375,-7428.4375,-64.5)
