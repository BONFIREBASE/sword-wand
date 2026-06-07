import json
import os
import random
import pygame
from src.config import WIDTH, HEIGHT, GAME, GAME_OVER, VICTORY
from src import level, state
from src.entities import DamageNumber, Enemy, Coin, Spike, FlyingStone
from src.ui import draw_ui

# ---------------------------------------------------------------------------
# Asset paths
# ---------------------------------------------------------------------------
_TILESET_BASE = "assets/craftpix-net-926878-free-platformer-game-tileset-pixel-art/PNG"
_BG_BASE = os.path.join(_TILESET_BASE, "Background", "1920x1080")

# ---------------------------------------------------------------------------
# Parallax background layers  (image, scroll‑speed)
# Flora2 removed — it's too dense and covers the player.
# ---------------------------------------------------------------------------
_bg_layer_data = [
    (pygame.image.load(os.path.join(_BG_BASE, "Sky_1920x1080.png")),    0.05),
    (pygame.image.load(os.path.join(_BG_BASE, "Clouds_1920x1080.png")), 0.15),
    (pygame.image.load(os.path.join(_BG_BASE, "Flora1_1920x1080.png")), 0.35),
]

# Pre‑scaled background cache  (avoids scaling 3 large images every frame)
_bg_scaled_cache = {}  # key: (w, h)  value: list[Surface]


def _get_scaled_bgs(scr_w, scr_h):
    """Return pre‑scaled background surfaces, cached per resolution."""
    key = (scr_w, scr_h)
    if key not in _bg_scaled_cache:
        _bg_scaled_cache[key] = [
            pygame.transform.scale(img, (scr_w, scr_h))
            for img, _ in _bg_layer_data
        ]
    return _bg_scaled_cache[key]


# ---------------------------------------------------------------------------
# Ground tiles — Tileset.png is a 32×32 native grid  (544×384 = 17×12 tiles)
# ---------------------------------------------------------------------------
_tileset_img = pygame.image.load(
    os.path.join(_TILESET_BASE, "Tileset.png")
)

_TILE_NATIVE = 32
_TILE_SCALE  = 3          # 32 × 3 = 96px rendered tiles (bigger & chunkier)
_TILE_RENDER = _TILE_NATIVE * _TILE_SCALE


def _extract_tile(col, row):
    """Cut a single 32×32 tile from the tileset and scale it up."""
    rect = pygame.Rect(col * _TILE_NATIVE, row * _TILE_NATIVE,
                       _TILE_NATIVE, _TILE_NATIVE)
    tile = _tileset_img.subsurface(rect).copy()
    return pygame.transform.scale(tile, (_TILE_RENDER, _TILE_RENDER))


# Row 0 = top‑surface tiles (grass);  Row 1 = inner fill (dirt/rock)
_grass_tile = _extract_tile(3, 0)
_dirt_tile  = _extract_tile(3, 1)

# Pre‑build a single‑row ground strip image (one screen width + padding)
# that we can just blit in one go instead of tile‑by‑tile each frame.
_ground_strip_cache = {}  # key: (scr_w, scr_h)


def _get_ground_strip(scr_w, scr_h):
    """Return a pre‑rendered ground strip surface, cached per resolution."""
    key = (scr_w, scr_h)
    if key not in _ground_strip_cache:
        strip_w = _TILE_RENDER
        floor_y = scr_h - 20
        ground_h = scr_h - floor_y + _TILE_RENDER
        strip = pygame.Surface((strip_w, ground_h), pygame.SRCALPHA)
        strip.blit(_grass_tile, (0, 0))
        for ry in range(_TILE_RENDER, ground_h, _TILE_RENDER):
            strip.blit(_dirt_tile, (0, ry))
        _ground_strip_cache[key] = strip
    return _ground_strip_cache[key]


# ---------------------------------------------------------------------------
# Platform tiles — additional edge tiles for floating platforms
# ---------------------------------------------------------------------------
_plat_left  = _extract_tile(6, 4)   # left edge with grass
_plat_mid   = _extract_tile(7, 4)   # middle flat grass
_plat_right = _extract_tile(8, 4)   # right edge with grass


def _build_platform_surface(width_tiles):
    """Pre‑render a platform surface of a given tile width."""
    surf = pygame.Surface((width_tiles * _TILE_RENDER, _TILE_RENDER),
                          pygame.SRCALPHA)
    if width_tiles == 1:
        surf.blit(_plat_mid, (0, 0))
    else:
        surf.blit(_plat_left, (0, 0))
        for i in range(1, width_tiles - 1):
            surf.blit(_plat_mid, (i * _TILE_RENDER, 0))
        surf.blit(_plat_right, ((width_tiles - 1) * _TILE_RENDER, 0))
    return surf


# Pre‑build platform surfaces for common widths (2–5 tiles)
_plat_surfaces = {w: _build_platform_surface(w) for w in range(2, 6)}


# ---------------------------------------------------------------------------
# Floating platform layout — repeating pattern
# (x_offset, y_above_floor, width_in_tiles)
# Pattern repeats every _PLAT_CYCLE pixels along the world x‑axis.
# Player is 150px tall, platform tile is 96px.
# Walk‑under requires y_above > 246.  Jump power = -22 → max jump ≈ 302px.
# ---------------------------------------------------------------------------
_PLAT_CYCLE = 1600  # repeat distance
_PLAT_PATTERN = [
    # Low tier — player can walk under these (280 > 246 ✓)
    (100,   280,  3),   # low left
    (500,   280,  2),   # low center
    (1000,  280,  3),   # low far right
    # Mid tier — reachable from low platforms
    (250,   420,  4),   # mid wide
    (700,   420,  3),   # mid right
    (1250,  420,  2),   # mid far right
    # High tier — reachable from mid platforms
    (450,   560,  2),   # high center
]


_PLAT_START_X = 1600  # platforms only appear after this world X — spawn area is clean ground


def _get_visible_platforms(camera_x, scr_w, floor_y):
    """Return (rects, draw_list) for all platforms visible on screen."""
    rects = []
    draw_list = []  # (screen_x, screen_y, surface)
    world_left  = camera_x - _TILE_RENDER * 2
    world_right = camera_x + scr_w + _TILE_RENDER * 2
    cycle_start = int(world_left // _PLAT_CYCLE) - 1
    cycle_end   = int(world_right // _PLAT_CYCLE) + 2
    for cycle in range(cycle_start, cycle_end):
        base_x = cycle * _PLAT_CYCLE
        for x_off, y_above, w_tiles in _PLAT_PATTERN:
            wx = base_x + x_off
            pw = w_tiles * _TILE_RENDER
            # Don't show platforms before the safe start distance
            if wx < _PLAT_START_X:
                continue
            # Quick off-screen check
            if wx + pw < world_left or wx > world_right:
                continue
            wy = floor_y - y_above
            # Collision rect
            rects.append(pygame.Rect(wx, wy, pw, _TILE_RENDER))
            # Draw info
            sx = wx - camera_x
            surf = _plat_surfaces.get(w_tiles, _build_platform_surface(w_tiles))
            draw_list.append((sx, wy, surf))
    return rects, draw_list


_player_spawned = False
_camera_x = 0.0  # smoothed camera position
_left_wall_x = None  # world X for the invisible wall at start
_damage_numbers = []
_damage_font = None
_player_death_timer = 0

# ---------------------------------------------------------------------------
# Dynamic world entity manager — generates enemies/chests per world chunk
# ---------------------------------------------------------------------------
_WORLD_CHUNK = 1600          # same as _PLAT_CYCLE so chunks align with platforms
_SPAWN_RADIUS_CHUNKS = 2     # chunks ahead to keep alive (2 = ~one screen ahead)
_SAFE_START_CHUNKS = 1       # chunk 0 empty — entities start appearing from x≈1600
_world_enemies = {}          # chunk_id -> list[Enemy]
_world_coins = {}            # chunk_id -> list[Coin]
_world_spikes = {}           # chunk_id -> list[Spike]
_world_stones = {}           # chunk_id -> list[FlyingStone]
_spawned_chunks = set()      # which chunks have been generated


def _world_rng(chunk_id, seed_offset=0):
    """Return a seeded RNG for a given chunk so world is deterministic."""
    return random.Random(chunk_id * 9973 + seed_offset)


def _generate_chunk(chunk_id, floor_y, scr_w):
    """Procedurally populate one world chunk with enemies, chests, spikes, and stones."""
    if chunk_id in _spawned_chunks:
        return
    _spawned_chunks.add(chunk_id)

    rng = _world_rng(chunk_id)
    base_x = chunk_id * _WORLD_CHUNK

    # Collect platform tops for this chunk (matches _get_visible_platforms pattern)
    chunk_plats = []
    for x_off, y_above, w_tiles in _PLAT_PATTERN:
        wx = base_x + x_off
        pw = w_tiles * _TILE_RENDER
        wy = floor_y - y_above
        chunk_plats.append(pygame.Rect(wx, wy, pw, _TILE_RENDER))

    # --- Flying stones: respect safe zone, 20% chance per chunk ---
    stones_in_chunk = []
    if chunk_id >= _SAFE_START_CHUNKS and rng.random() < 0.20:
        sx = rng.randint(base_x + 150, base_x + _WORLD_CHUNK - 150)
        sy = floor_y - rng.randint(180, 420)
        speed = rng.uniform(0.4, 1.0)
        stone = FlyingStone(sx, sy, hover_range=28, speed=speed)
        stones_in_chunk.append(stone)
    _world_stones[chunk_id] = stones_in_chunk

    # --- Safe zone: no enemies, chests, or spikes in early chunks ---
    if chunk_id < _SAFE_START_CHUNKS:
        _world_enemies[chunk_id] = []
        _world_coins[chunk_id] = []
        _world_spikes[chunk_id] = []
        return

    enemies_in_chunk = []
    coins_in_chunk = []

    # --- Spawn enemies on platforms (15% chance each) ---
    for plat in chunk_plats:
        if rng.random() < 0.15:
            margin = min(40, plat.width // 4)
            cx = rng.randint(plat.left + margin, max(plat.left + margin + 1, plat.right - margin))
            spawn_y = plat.top - 20
            patrol = max(20, (plat.width - margin * 2) // 2)
            e = Enemy(cx, spawn_y, patrol_range=patrol, hp=2, damage=10)
            e.left_limit = plat.left + margin
            e.right_limit = plat.right - margin
            enemies_in_chunk.append(e)

        # 15% chance a chest on this platform
        if rng.random() < 0.15:
            margin = 20
            cx = rng.randint(plat.left + margin, max(plat.left + margin + 1, plat.right - margin))
            c = Coin(cx, plat.top)
            c.rect.bottom = plat.top
            c.snapped = True
            coins_in_chunk.append(c)

    # --- 35% chance of one ground enemy per chunk ---
    if rng.random() < 0.35:
        gx = rng.randint(base_x + 120, base_x + _WORLD_CHUNK - 120)
        patrol = rng.randint(60, 120)
        e = Enemy(gx, floor_y - 20, patrol_range=patrol, hp=2, damage=10)
        e.left_limit = gx - patrol
        e.right_limit = gx + patrol
        enemies_in_chunk.append(e)

    # --- 10% chance of one ground chest per chunk ---
    if rng.random() < 0.10:
        gx = rng.randint(base_x + 80, base_x + _WORLD_CHUNK - 80)
        c = Coin(gx, floor_y)
        c.rect.bottom = floor_y
        c.snapped = True
        coins_in_chunk.append(c)

    _world_enemies[chunk_id] = enemies_in_chunk
    _world_coins[chunk_id] = coins_in_chunk

    # --- Spikes: GROUND ONLY (25% chance per chunk) ---
    spikes_in_chunk = []
    if rng.random() < 0.25:
        gx = rng.randint(base_x + 100, base_x + _WORLD_CHUNK - 100)
        s = Spike(gx, floor_y)
        spikes_in_chunk.append(s)

    _world_spikes[chunk_id] = spikes_in_chunk


def _update_world_entities(camera_x, floor_y, scr_w):
    """Generate chunks in view range, return active enemies, coins, spikes & stones."""
    center_chunk = int((camera_x + scr_w // 2) // _WORLD_CHUNK)
    # Generate chunks: 1 behind + center + RADIUS ahead
    for cid in range(center_chunk - 1, center_chunk + _SPAWN_RADIUS_CHUNKS + 1):
        if cid >= 0:
            _generate_chunk(cid, floor_y, scr_w)

    # Collect active entities only in the visible window
    active_enemies = []
    active_coins = []
    active_spikes = []
    active_stones = []
    for cid in range(center_chunk - 1, center_chunk + _SPAWN_RADIUS_CHUNKS + 1):
        if cid in _world_enemies:
            active_enemies.extend(_world_enemies[cid])
        if cid in _world_coins:
            active_coins.extend(_world_coins[cid])
        if cid in _world_spikes:
            active_spikes.extend(_world_spikes[cid])
        if cid in _world_stones:
            active_stones.extend(_world_stones[cid])
    return active_enemies, active_coins, active_spikes, active_stones


def restart_game():
    global _player_spawned, _camera_x, _left_wall_x, _damage_numbers, _player_death_timer
    global _world_enemies, _world_coins, _world_spikes, _world_stones, _spawned_chunks
    _player_spawned = False
    _camera_x = 0.0
    _left_wall_x = None
    _damage_numbers = []
    _player_death_timer = 0
    _world_enemies = {}
    _world_coins = {}
    _world_spikes = {}
    _world_stones = {}
    _spawned_chunks = set()
    state.lives = 3
    state.score = 0
    state.player_hp = state.player_max_hp
    level.load_level(0)
    state.state = GAME


def spawn_damage_number(x, y, amount, color=(255, 255, 100)):
    _damage_numbers.append(DamageNumber(x, y, amount, color))


def save_game():
    data = {"level": level.current_level, "coins": state.score, "lives": state.lives}
    with open("save.json", "w") as f:
        json.dump(data, f)


def load_game():
    if os.path.exists("save.json"):
        with open("save.json", "r") as f:
            data = json.load(f)
        level.current_level = data.get("level", 0)
        state.score = data.get("coins", 0)
        state.lives = data.get("lives", 3)
        level.load_level(level.current_level)

        global _player_spawned, _camera_x, _left_wall_x
        global _world_enemies, _world_coins, _world_spikes, _world_stones, _spawned_chunks
        _player_spawned = False
        _camera_x = 0.0
        _left_wall_x = None
        _world_enemies = {}
        _world_coins = {}
        _world_spikes = {}
        _world_stones = {}
        _spawned_chunks = set()

        state.state = GAME
        return True
    return False


# ---------------------------------------------------------------------------
# Rendering
# ---------------------------------------------------------------------------
def _draw_game_frame(screen, camera_x):
    """Render the full game frame (visual only — no physics)."""
    scr_h = screen.get_height()
    scr_w = screen.get_width()
    floor_y = scr_h - 20

    # --- Parallax background layers (pre‑scaled, cached) ---
    scaled_bgs = _get_scaled_bgs(scr_w, scr_h)
    for i, (_, speed) in enumerate(_bg_layer_data):
        bg = scaled_bgs[i]
        px = int(camera_x * speed) % scr_w
        screen.blit(bg, (-px, 0))
        if px > 0:
            screen.blit(bg, (scr_w - px, 0))

    # --- Tiled ground (visual only — collision rect is separate) ---
    strip = _get_ground_strip(scr_w, scr_h)
    grass_top_y = floor_y - _TILE_RENDER // 3
    tile_start_x = int(camera_x // _TILE_RENDER) * _TILE_RENDER
    for tx in range(tile_start_x - _TILE_RENDER,
                    tile_start_x + scr_w + _TILE_RENDER * 2,
                    _TILE_RENDER):
        sx = tx - camera_x
        screen.blit(strip, (sx, grass_top_y))

    # --- Floating platforms ---
    _, draw_list = _get_visible_platforms(camera_x, scr_w, floor_y)
    for sx, wy, surf in draw_list:
        screen.blit(surf, (sx, wy))

    # --- Flying stones: level tile-grid + world dynamic ---
    for stone in level.stones_list:
        stone.draw(screen, camera_x)
    for stone in _active_world_stones:
        stone.draw(screen, camera_x)

    # --- Level enemies (tile-grid) ---
    for enemy in level.enemies:
        enemy.draw(screen, camera_x)

    # --- Level coins (tile-grid) ---
    for coin in level.coins_list:
        coin.draw(screen, camera_x)

    # --- World enemies (dynamic) ---
    for enemy in _active_world_enemies:
        enemy.draw(screen, camera_x)

    # --- World coins/chests (dynamic) ---
    for coin in _active_world_coins:
        coin.draw(screen, camera_x)

    # --- Spikes: level tile-grid + world dynamic ---
    for spike in level.spikes_list:
        spike.draw(screen, camera_x)
    for spike in _active_world_spikes:
        spike.draw(screen, camera_x)

    # --- Player (drawn on top) ---
    level.player.draw(screen, camera_x)


# Module-level active entity lists (updated each frame by _update_world_entities)
_active_world_enemies = []
_active_world_coins = []
_active_world_spikes = []
_active_world_stones = []


def update_game(screen):
    scr_h = screen.get_height()
    scr_w = screen.get_width()
    floor_y = scr_h - 20

    global _player_spawned, _camera_x, _left_wall_x
    global _active_world_enemies, _active_world_coins, _active_world_spikes, _active_world_stones
    if not _player_spawned:
        level.player.rect.bottom = floor_y
        level.player.spawn_timer = 15
        _player_spawned = True
        # Set left-wall position to player's initial left edge so player can't move left of spawn
        _left_wall_x = level.player.rect.left

    # Camera target: center player on screen
    target_x = level.player.rect.centerx - scr_w // 2
    # Snappy lerp — camera catches up fast (0.25 = ~4 frames)
    _camera_x += (target_x - _camera_x) * 0.25
    camera_x = int(_camera_x)

    # Update dynamic world entities (stream in/out chunks)
    (_active_world_enemies,
     _active_world_coins,
     _active_world_spikes,
     _active_world_stones) = _update_world_entities(camera_x, floor_y, scr_w)

    _draw_game_frame(screen, camera_x)

    # Build collision surfaces: floor (infinite) + floating platforms
    floor = pygame.Rect(level.player.rect.x - 50000, floor_y, 100000, 20)
    plat_rects, _ = _get_visible_platforms(camera_x, scr_w, floor_y)
    all_surfaces = [floor] + plat_rects

    # Snap floating coins and enemies to nearest surface below them
    for coin in level.coins_list:
        if not coin.snapped:
            cx = coin.rect.centerx
            cy = coin.rect.centery
            best = None
            best_dist = None
            # Check all surfaces (floor + platforms + stones)
            check_list = list(all_surfaces) + [s.rect for s in level.stones_list]
            for surf in check_list:
                if surf.top > cy:
                    # Horizontal distance to nearest edge of surface
                    if cx < surf.left:
                        dist = surf.left - cx
                    elif cx > surf.right:
                        dist = cx - surf.right
                    else:
                        dist = 0  # directly above
                    if best is None or dist < best_dist or (dist == best_dist and surf.top < best.top):
                        best = surf
                        best_dist = dist
            if best is not None:
                coin.rect.bottom = best.top
                coin.rect.centerx = max(best.left + 20, min(best.right - 20, cx))
                # Track if parented to a stone
                for stone in level.stones_list:
                    if stone.rect == best:
                        coin.parent_stone = stone
                        break
                coin.snapped = True



    level.player.update(all_surfaces)
    # Enforce invisible wall at spawn: clamp player's left edge to _left_wall_x
    if _left_wall_x is not None and level.player.rect.left < _left_wall_x:
        level.player.rect.left = _left_wall_x

    # Update level enemies (with physics platforms) and stones
    for stone in level.stones_list:
        stone.update()
    # Update world stones (hover physics)
    for stone in _active_world_stones:
        stone.update()

    # Build extended surfaces including world stones for enemy physics
    all_surfaces_with_stones = all_surfaces + [s.rect for s in level.stones_list] + [s.rect for s in _active_world_stones]

    for enemy in level.enemies:
        enemy.update(platforms=all_surfaces_with_stones)

    # Update world enemies with full physics (including stone platforms)
    for enemy in _active_world_enemies:
        enemy.update(platforms=all_surfaces_with_stones)

    # Spike damage — level spikes
    for spike in level.spikes_list:
        if level.player.rect.colliderect(spike.rect):
            level.player.take_damage(15)

    # Spike damage — world spikes
    for spike in _active_world_spikes:
        if level.player.rect.colliderect(spike.rect):
            level.player.take_damage(15)

    # Coins on stones follow the stone's hover
    for coin in level.coins_list:
        if coin.parent_stone is not None:
            coin.rect.bottom = coin.parent_stone.rect.top

    # Coin collection (level coins)
    for coin in level.coins_list:
        if not coin.collected and level.player.rect.colliderect(coin.rect):
            coin.collected = True
            state.score += 1

    # Coin collection (world coins)
    for coin in _active_world_coins:
        if not coin.collected and level.player.rect.colliderect(coin.rect):
            coin.collected = True
            state.score += 1

    # Flying stone heal — player touches an unused stone to restore HP
    all_stones = list(level.stones_list) + list(_active_world_stones)
    for stone in all_stones:
        if not stone.used and level.player.rect.colliderect(stone.rect):
            stone.used = True
            heal = stone.HEAL_AMOUNT
            player = level.player
            player.hp = min(player.max_hp, player.hp + heal)
            state.player_hp = player.hp
            # Green floating "+HP" number
            _damage_numbers.append(DamageNumber(
                player.rect.centerx, player.rect.top - 10,
                f"+{heal}", (60, 220, 100)))

    # Remove fully dead level enemies
    for enemy in list(level.enemies):
        if enemy.dead:
            level.enemies.remove(enemy)

    # Remove dead world enemies from their chunk list
    for chunk_enemies in _world_enemies.values():
        for enemy in chunk_enemies[:]:
            if enemy.dead:
                chunk_enemies.remove(enemy)

    # Enemy collision damage (skip dying enemies)
    global _damage_font
    if _damage_font is None:
        _damage_font = pygame.font.Font("assets/font/Sekuya/Sekuya-Regular.ttf", 18)
    all_active_enemies = list(level.enemies) + _active_world_enemies
    for enemy in all_active_enemies:
        if enemy.dying_timer > 0:
            continue
        if level.player.rect.colliderect(enemy.rect) and level.player.invincible_timer == 0:
            level.player.take_damage(enemy.damage)
            _damage_numbers.append(DamageNumber(
                level.player.rect.centerx, level.player.rect.top,
                enemy.damage, (255, 60, 60)))

    # Update damage numbers
    for dn in _damage_numbers[:]:
        dn.update()
        if dn.dead:
            _damage_numbers.remove(dn)

    # Draw damage numbers
    for dn in _damage_numbers:
        dn.draw(screen, camera_x, _damage_font)

    # Draw UI (health bar, lives, coins)
    draw_ui(screen)

    # Player death animation
    global _player_death_timer
    if _player_death_timer > 0:
        _player_death_timer -= 1
        level.player.sprite.set_state("death")
        level.player.sprite.update()
        if _player_death_timer <= 0:
            state.lives -= 1
            if state.lives <= 0:
                state.state = GAME_OVER
                return
            state.player_hp = state.player_max_hp
            level.load_level(level.current_level)
        return

    # Fall death or HP death
    if level.player.rect.y > scr_h + 200 or level.player.hp <= 0:
        _player_death_timer = 24
        level.player.sprite.set_state("death")
        return


def get_all_enemies():
    """Return combined list of level tile-grid enemies + active world enemies."""
    return list(level.enemies) + list(_active_world_enemies)
