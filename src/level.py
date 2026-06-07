import pygame
from src.config import TILE_SIZE
from src.entities import Player, Coin, Enemy, Spike, FlyingStone
from src import state

LEVELS = [
    [
        "XXXXXXXXXXXXXXXXXXXXXXXX",
        "X......................X",
        "X......................X",
        "X......................X",
        "X....P.................X",
        "X......................X",
        "X......................X",
        "X......................X",
        "X......................X",
        "X......................X",
        "X......................X",
        "X......................X",
        "X......................X",
        "X......................X",
        "XXXXXXXXXXXXXXXXXXXXXXXX",
    ],
    [
        "XXXXXXXXXXXXXXXXXXXXXXXX",
        "X......................X",
        "X......................X",
        "X......................X",
        "X......................X",
        "X......................X",
        "X......................X",
        "X......................X",
        "X......................X",
        "X......................X",
        "X......................X",
        "X....P.................X",
        "X......................X",
        "X......................X",
        "XXXXXXXXXXXXXXXXXXXXXXXX",
    ],
]

MAX_LEVEL = len(LEVELS)

player = None
platforms = []
coins_list = []
enemies = pygame.sprite.Group()
spikes_list = []
stones_list = []
current_level = 0


def load_level(level_index):
    global player, platforms, coins_list, enemies, spikes_list, stones_list, current_level
    current_level = level_index
    level_data = LEVELS[level_index]
    platforms = []
    coins_list = []
    enemies = pygame.sprite.Group()
    spikes_list = []
    stones_list = []
    player = None

    for row_idx, row in enumerate(level_data):
        for col_idx, char in enumerate(row):
            x = col_idx * TILE_SIZE
            y = row_idx * TILE_SIZE
            if char == "X":
                platforms.append(pygame.Rect(x, y, TILE_SIZE, TILE_SIZE))
            elif char == "C":
                coins_list.append(Coin(x + TILE_SIZE // 2, y + 10))
            elif char == "E":
                enemies.add(Enemy(x + 2, y + 2))
            elif char == "S":
                spikes_list.append(Spike(x + TILE_SIZE // 2, y + TILE_SIZE))
            elif char == "F":
                stones_list.append(FlyingStone(x + TILE_SIZE // 2, y + TILE_SIZE, hover_range=40))
            elif char == "P":
                player = Player(x, y, char_type=getattr(state, "selected_character", "GraveRobber"))

    if player is None:
        player = Player(100, 100, char_type=getattr(state, "selected_character", "GraveRobber"))

    state.player_hp = state.player_max_hp
    # Reset snap flags so game.py will snap coins/enemies to actual platforms
    for coin in coins_list:
        coin.snapped = False
    for enemy in enemies:
        enemy.snapped = False
