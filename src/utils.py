import pygame
from functools import lru_cache

@lru_cache(maxsize=32)
def get_font(path, size):
    try:
        return pygame.font.Font(path, int(size))
    except Exception as e:
        print(f"Failed to load font {path}: {e}")
        return pygame.font.SysFont(None, int(size))
