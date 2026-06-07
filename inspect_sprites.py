import pygame
pygame.init()

files = [
    "assets/characters/1 Woodcutter/Woodcutter_idle.png",
    "assets/characters/1 Woodcutter/Woodcutter_run.png",
    "assets/characters/1 Woodcutter/Woodcutter_attack1.png",
    "assets/characters/1 Woodcutter/Woodcutter_jump.png",
    "assets/characters/1 Woodcutter/Woodcutter_death.png",
]

for f in files:
    try:
        img = pygame.image.load(f)
        print(f"{f}: {img.get_size()}")
    except Exception as e:
        print(f"{f}: ERROR - {e}")
