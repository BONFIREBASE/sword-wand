import pygame
import sys
pygame.init()
screen = pygame.display.set_mode((1, 1))

base = "assets/characters/2 GraveRobber/GraveRobber_"
names = ["idle", "run", "jump", "attack1", "hurt", "death"]

for n in names:
    path = base + n + ".png"
    img = pygame.image.load(path).convert_alpha()
    w, h = img.get_size()
    print(f"{n}: {w}x{h}  (cols@48={w//48}, rows@48={h//48})")

pygame.quit()
