import matplotlib.pyplot as plt
import numpy as np

fig, ax = plt.subplots()
data = np.random.rand(10, 10) * 10
im = ax.imshow(data, vmin=0, vmax=10)
cbar = fig.colorbar(im, ax=ax)

# Cambiar los limites
im.set_clim(0, 100)
cbar.update_normal(im)

print(f"cbar ticks: {cbar.get_ticks()}")
