import pygame
import os
import sys

pygame.init()

base = r"c:\Users\Project\Sword-and-wand...-\assets\characters\1 Woodcutter"
out_path = r"c:\Users\Project\Sword-and-wand...-\sprite_dims.txt"

files = [
    "Woodcutter_idle.png",
    "Woodcutter_run.png",
    "Woodcutter_attack1.png",
    "Woodcutter_jump.png",
    "Woodcutter_death.png",
]

with open(out_path, "w") as out:
    out.write("START\n")
    for fname in files:
        path = os.path.join(base, fname)
        out.write(f"Trying {path}... ")
        try:
            img = pygame.image.load(path)
            w, h = img.get_size()
            out.write(f"OK {w}x{h}\n")
        except Exception as e:
            out.write(f"ERROR {e}\n")
    out.write("END\n")
