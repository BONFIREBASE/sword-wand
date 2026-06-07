import pygame
pygame.init()
path = r"c:\Users\Project\Sword-and-wand...-\assets\craftpix-net-926878-free-platformer-game-tileset-pixel-art\PNG\Tileset.png"
img = pygame.image.load(path)
print("Tileset dimensions:", img.get_size())
