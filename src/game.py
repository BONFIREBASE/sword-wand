import json
import os
import random
import pygame
from src.config import WIDTH, HEIGHT, GAME, GAME_OVER, VICTORY
from src.utils import get_font
from src import level, state
from src.entities import DamageNumber, Enemy, Coin, Spike, FlyingStone
from src.ui import draw_ui
import src.db as db

_TILESET_BASE = "assets/craftpix-net-926878-free-platformer-game-tileset-pixel-art/PNG"
_BG_BASE = os.path.join(_TILESET_BASE, "Background", "1920x1080")

_bg_layer_data = [
    (pygame.image.load(os.path.join(_BG_BASE, "Sky_1920x1080.png")),    0.05),
    (pygame.image.load(os.path.join(_BG_BASE, "Clouds_1920x1080.png")), 0.15),
    (pygame.image.load(os.path.join(_BG_BASE, "Flora1_1920x1080.png")), 0.35),
]

_bg_scaled_cache = {}

def _get_scaled_bgs(scr_w, scr_h):
    """Return pre‑scaled background surfaces, cached per resolution."""
    key = (scr_w, scr_h)
    if key not in _bg_scaled_cache:

        _bg_scaled_cache[key] = []
        for img, speed in _bg_layer_data:
            scaled = pygame.transform.scale(img, (scr_w, scr_h))
            if speed > 0:
                scaled = scaled.convert_alpha()
            else:
                scaled = scaled.convert()
            _bg_scaled_cache[key].append(scaled)
    return _bg_scaled_cache[key]

_tileset_img = pygame.image.load(
    os.path.join(_TILESET_BASE, "Tileset.png")
)

_TILE_NATIVE = 32
_TILE_SCALE  = 3
_TILE_RENDER = _TILE_NATIVE * _TILE_SCALE

def _extract_tile(col, row):
    """Cut a single 32×32 tile from the tileset and scale it up."""
    rect = pygame.Rect(col * _TILE_NATIVE, row * _TILE_NATIVE,
                       _TILE_NATIVE, _TILE_NATIVE)
    tile = _tileset_img.subsurface(rect).copy()
    return pygame.transform.scale(tile, (_TILE_RENDER, _TILE_RENDER))

_grass_tile = _extract_tile(3, 0)
_dirt_tile  = _extract_tile(3, 1)

_ground_strip_cache = {}

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

        _ground_strip_cache[key] = strip.convert_alpha()
    return _ground_strip_cache[key]

_plat_left  = _extract_tile(6, 4)
_plat_mid   = _extract_tile(7, 4)
_plat_right = _extract_tile(8, 4)

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

_plat_surfaces = {w: _build_platform_surface(w) for w in range(2, 6)}

_PLAT_CYCLE = 1600
_PLAT_START_X = 1600

_PLAT_PATTERN = [
    (100,   280,  3),
    (500,   280,  2),
    (1000,  280,  3),
    (250,   420,  4),
    (700,   420,  3),
    (1250,  420,  2),
    (450,   560,  2),
]

def _get_chunk_plat_rects(chunk_id, floor_y):
    """Return a randomised set of platform Rects for this chunk, seeded per chunk_id."""
    rng = _world_rng(chunk_id, seed_offset=1)
    base_x = chunk_id * _WORLD_CHUNK
    plats = []
    used_x_ranges = []

    heights = [260, 310, 370, 430, 490, 550]
    num_plats = rng.randint(3, 6)
    attempts = 0
    while len(plats) < num_plats and attempts < 40:
        attempts += 1
        w_tiles = rng.randint(2, 5)
        pw = w_tiles * _TILE_RENDER
        y_above = rng.choice(heights) + rng.randint(-20, 20)
        x_off = rng.randint(60, _WORLD_CHUNK - pw - 60)
        wx = base_x + x_off
        wy = floor_y - y_above
        overlaps = any(wx < ex + ew + 80 and wx + pw > ex - 80 for ex, ew in used_x_ranges)
        if overlaps:
            continue
        plats.append(pygame.Rect(wx, wy, pw, _TILE_RENDER))
        used_x_ranges.append((wx, pw))
    return plats

def _get_visible_platforms(camera_x, scr_w, floor_y):
    """Return (rects, draw_list) for all platforms visible on screen."""
    rects = []
    draw_list = []
    world_left  = camera_x - _TILE_RENDER * 2
    world_right = camera_x + scr_w + _TILE_RENDER * 2
    chunk_start = int(world_left // _WORLD_CHUNK) - 1
    chunk_end   = int(world_right // _WORLD_CHUNK) + 2
    for chunk_id in range(chunk_start, chunk_end):
        if chunk_id * _WORLD_CHUNK < _PLAT_START_X - _WORLD_CHUNK:
            continue
        for plat in _get_chunk_plat_rects(chunk_id, floor_y):
            if plat.right < world_left or plat.left > world_right:
                continue
            rects.append(plat)
            sx = plat.x - camera_x
            w_tiles = plat.width // _TILE_RENDER
            surf = _plat_surfaces.get(w_tiles, _build_platform_surface(w_tiles))
            draw_list.append((sx, plat.y, surf))
    return rects, draw_list

_player_spawned = False
_camera_x = 0.0
_left_wall_x = None
_damage_numbers = []
_damage_font = None
_player_death_timer = 0
_screen_shake = 0

_WORLD_CHUNK = 1600
_SPAWN_RADIUS_CHUNKS = 2
_SAFE_START_CHUNKS = 1
_world_enemies = {}
_world_coins = {}
_world_spikes = {}
_world_stones = {}
_spawned_chunks = set()
_killed_enemy_ids = set()
_next_enemy_id = 0

def _world_rng(chunk_id, seed_offset=0):
    """Return a seeded RNG for a given chunk so world is deterministic."""
    return random.Random(chunk_id * 9973 + seed_offset)

def _generate_chunk(chunk_id, floor_y, scr_w):
    """Procedurally populate one world chunk with enemies, chests, spikes, and stones."""
    global _next_enemy_id
    if chunk_id in _spawned_chunks:
        return
    _spawned_chunks.add(chunk_id)

    rng = _world_rng(chunk_id)
    base_x = chunk_id * _WORLD_CHUNK

    chunk_plats = _get_chunk_plat_rects(chunk_id, floor_y)

    stones_in_chunk = []
    if chunk_id >= _SAFE_START_CHUNKS:
        num_stones = rng.choices([0, 1, 2, 3], weights=[58, 30, 10, 2])[0]
        used_sx = []
        for _ in range(num_stones):
            for _attempt in range(15):
                sx = rng.randint(base_x + 80, base_x + _WORLD_CHUNK - 80)
                if any(abs(sx - ux) < 200 for ux in used_sx):
                    continue
                sy = floor_y - rng.randint(120, 500)
                speed = rng.uniform(0.25, 1.4)
                hover = rng.randint(16, 55)
                stone = FlyingStone(sx, sy, hover_range=hover, speed=speed)
                stones_in_chunk.append(stone)
                used_sx.append(sx)
                break
    _world_stones[chunk_id] = stones_in_chunk

    if chunk_id < _SAFE_START_CHUNKS:
        _world_enemies[chunk_id] = []
        _world_coins[chunk_id] = []
        _world_spikes[chunk_id] = []
        return

    enemies_in_chunk = []
    coins_in_chunk = []
    used_enemy_x = []

    hp_mult, dmg_mult, extra_enemies = get_difficulty(base_x)
    tier = max(0, int(base_x / 3200))
    max_enemies = 2 + extra_enemies
    spawn_chance = min(0.20 + extra_enemies * 0.10, 0.70)
    ground_chance = min(0.35 + extra_enemies * 0.10, 0.90)

    chaser_chance = min(0.20 + tier * 0.08, 0.75)
    aggro_min = min(300 + tier * 40, 600)
    aggro_max = min(500 + tier * 60, 900)

    def _make_enemy(ex, ey, patrol):
        e_hp  = max(2, int(2 * hp_mult))
        e_dmg = max(6, int(10 * dmg_mult))
        e_xp  = 10 + tier * 5
        import random as _r
        e = Enemy(ex, ey, patrol_range=patrol, hp=e_hp, damage=e_dmg,
                  enemy_id=_next_enemy_id, xp_value=e_xp)
        e.is_chaser    = _r.random() < chaser_chance
        e.aggro_range  = _r.randint(aggro_min, aggro_max)
        e.chase_speed  = e.speed * _r.uniform(1.5, 2.4)
        e.lose_aggro_dist = e.aggro_range * 2.5
        return e

    for plat in chunk_plats:
        if len(enemies_in_chunk) >= max_enemies:
            break
        if rng.random() < spawn_chance:
            margin = min(40, plat.width // 4)
            cx = rng.randint(plat.left + margin, max(plat.left + margin + 1, plat.right - margin))
            if any(abs(cx - ux) < 400 for ux in used_enemy_x):
                continue
            spawn_y = plat.top - 20
            patrol = max(20, (plat.width - margin * 2) // 2)
            e = _make_enemy(cx, spawn_y, patrol)
            _next_enemy_id += 1
            e.left_limit = plat.left + margin
            e.right_limit = plat.right - margin
            enemies_in_chunk.append(e)
            used_enemy_x.append(cx)

    if rng.random() < ground_chance and len(enemies_in_chunk) < max_enemies:
        gx = rng.randint(base_x + 120, base_x + _WORLD_CHUNK - 120)
        if not any(abs(gx - ux) < 400 for ux in used_enemy_x):
            patrol = rng.randint(80, 160)
            e = _make_enemy(gx, floor_y - 20, patrol)
            _next_enemy_id += 1
            e.left_limit = gx - patrol
            e.right_limit = gx + patrol
            enemies_in_chunk.append(e)
            used_enemy_x.append(gx)

    coins_in_chunk = []
    used_chest_x = []

    num_plat_chests = rng.choices([0, 1, 2], weights=[55, 38, 7])[0]
    plat_pool = list(chunk_plats)
    rng.shuffle(plat_pool)
    placed = 0
    for plat in plat_pool:
        if placed >= num_plat_chests:
            break
        if plat.width < 60:
            continue
        margin = max(20, plat.width // 6)
        cx = rng.randint(plat.left + margin, max(plat.left + margin + 1, plat.right - margin))
        if any(abs(cx - ux) < 200 for ux in used_chest_x):
            continue
        c = Coin(cx, plat.top)
        c.rect.bottom = plat.top
        c.snapped = True
        coins_in_chunk.append(c)
        used_chest_x.append(cx)
        placed += 1

    num_ground_chests = rng.choices([0, 1, 2], weights=[62, 33, 5])[0]
    for _ in range(num_ground_chests):
        for _attempt in range(10):
            gx = rng.randint(base_x + 80, base_x + _WORLD_CHUNK - 80)
            if any(abs(gx - ux) < 200 for ux in used_chest_x):
                continue
            c = Coin(gx, floor_y)
            c.rect.bottom = floor_y
            c.snapped = True
            coins_in_chunk.append(c)
            used_chest_x.append(gx)
            break

    for stone in stones_in_chunk:
        if rng.random() < 0.55:
            sx = stone.rect.centerx
            if not any(abs(sx - ux) < 120 for ux in used_chest_x):
                c = Coin(sx, stone.rect.top)
                c.rect.bottom = stone.rect.top
                c.snapped = True
                c.parent_stone = stone
                coins_in_chunk.append(c)
                used_chest_x.append(sx)

    total_chests = len(coins_in_chunk)
    total_stones = len(stones_in_chunk)
    is_cache = total_chests >= 2 and total_stones >= 1
    if is_cache:
        cache_cx = int(sum(used_chest_x) / len(used_chest_x))
        num_guards = rng.randint(3, 4)
        guard_hp  = max(4, int(4 * hp_mult))
        guard_dmg = max(8, int(10 * dmg_mult))
        guard_xp  = (10 + tier * 5) * 2
        for i in range(num_guards):
            for _attempt in range(15):
                gx = cache_cx + rng.randint(-320, 320)
                if any(abs(gx - ux) < 150 for ux in used_enemy_x):
                    continue
                e = Enemy(gx, floor_y - 20, patrol_range=60,
                          hp=guard_hp, damage=guard_dmg,
                          enemy_id=_next_enemy_id, xp_value=guard_xp)
                _next_enemy_id += 1
                e.left_limit = gx - 60
                e.right_limit = gx + 60
                e.is_chaser       = True
                e.aggro           = True
                e.aggro_range     = max(600, aggro_max)
                e.chase_speed     = e.speed * 2.2
                e.lose_aggro_dist = 1400
                enemies_in_chunk.append(e)
                used_enemy_x.append(gx)
                break

    _world_enemies[chunk_id] = enemies_in_chunk
    _world_coins[chunk_id] = coins_in_chunk

    spikes_in_chunk = []
    if rng.random() < 0.25:
        min_spikes = min(6, 3 + (chunk_id // 5))
        max_spikes = min(6, 4 + (chunk_id // 5))
        num_spikes = rng.randint(min_spikes, max_spikes)

        total_width = num_spikes * 48

        gx = rng.randint(base_x + 100, base_x + _WORLD_CHUNK - 100 - total_width)
        for i in range(num_spikes):
            s = Spike(gx + i * 48, floor_y)
            spikes_in_chunk.append(s)

    _world_spikes[chunk_id] = spikes_in_chunk

def _update_world_entities(camera_x, floor_y, scr_w):
    """Generate chunks in view range, return active enemies, coins, spikes & stones."""
    center_chunk = int((camera_x + scr_w // 2) // _WORLD_CHUNK)

    for cid in range(center_chunk - 1, center_chunk + _SPAWN_RADIUS_CHUNKS + 1):
        if cid >= 0:
            _generate_chunk(cid, floor_y, scr_w)

    active_enemies = []
    active_coins = []
    active_spikes = []
    active_stones = []
    for cid in range(center_chunk - 1, center_chunk + _SPAWN_RADIUS_CHUNKS + 1):
        if cid in _world_enemies:
            for e in _world_enemies[cid]:
                if e.enemy_id not in _killed_enemy_ids:
                    active_enemies.append(e)
        if cid in _world_coins:
            active_coins.extend(_world_coins[cid])
        if cid in _world_spikes:
            active_spikes.extend(_world_spikes[cid])
        if cid in _world_stones:
            active_stones.extend(_world_stones[cid])
    return active_enemies, active_coins, active_spikes, active_stones

def restart_game():
    global _player_spawned, _camera_x, _left_wall_x, _damage_numbers, _player_death_timer
    global _world_enemies, _world_coins, _world_spikes, _world_stones, _spawned_chunks, _killed_enemy_ids, _next_enemy_id

    db.init_db()
    stats = db.load_player_stats()
    state.score = stats["coins"]
    state.player_xp = stats["xp"]
    state.player_level = stats["level"]
    state.player_max_hp = stats["max_hp"]
    state.player_hp = state.player_max_hp
    state.lives = stats["lives"]
    state.has_double_dash = stats["has_double_dash"]
    state.has_regen = stats["has_regen"]
    state.has_cd_reduction = stats["has_cd_reduction"]
    state.has_extended_reach = stats.get("has_extended_reach", False)
    state.has_executioner = stats.get("has_executioner", False)
    state.has_spiked_armor = stats.get("has_spiked_armor", False)
    state.equipped_skills = stats.get("equipped_skills", [])

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
    _killed_enemy_ids = set()
    _next_enemy_id = 0
    level.load_level(0)
    state.state = GAME

def spawn_damage_number(x, y, amount, color=(255, 255, 100)):
    _damage_numbers.append(DamageNumber(x, y, amount, color))

def trigger_screen_shake(intensity=10):
    global _screen_shake
    _screen_shake = max(_screen_shake, intensity)

def get_player_damage(base_damage):
    """Scale damage with player level."""
    return base_damage + (state.player_level - 1)

def apply_kill_regen(kill_count, one_hit_kill_count):
    """Restore HP when player gets one-hit kills or multikills."""
    if kill_count == 0:
        return
    player = level.player
    heal = 0
    if one_hit_kill_count > 0:
        heal += 5
    if kill_count >= 2:
        heal += 3 * kill_count
    if heal > 0:
        player.hp = min(player.max_hp, player.hp + heal)
        state.player_hp = player.hp
        spawn_damage_number(player.rect.centerx, player.rect.top - 10, f"+{heal} HP", (60, 220, 100))

def get_difficulty(world_x):
    """Return (hp_mult, damage_mult, extra_enemies) based on world distance.
    Difficulty increases every ~3200px (2 chunks).
    HP scales aggressively. Damage scales very gently — enemies get tougher, not spikier.
    Enemy count and aggression increase the further the player goes."""
    tier = max(0, int(world_x / 3200))

    hp_mult   = 1 + tier * 2.5
    dmg_mult  = 1 + tier * 0.15

    extra = min(tier, 5)
    return hp_mult, dmg_mult, extra

def save_game():
    db.init_db()
    db.save_player_stats(
        coins=state.score,
        xp=state.player_xp,
        level=state.player_level,
        max_hp=state.player_max_hp,
        lives=state.lives,
        has_double_dash=state.has_double_dash,
        has_regen=state.has_regen,
        has_cd_reduction=state.has_cd_reduction,
        has_extended_reach=state.has_extended_reach,
        has_executioner=state.has_executioner,
        has_spiked_armor=state.has_spiked_armor,
        equipped_skills=state.equipped_skills
    )

def load_game():
    db.init_db()
    stats = db.load_player_stats()
    state.score = stats["coins"]
    state.player_xp = stats["xp"]
    state.player_level = stats["level"]
    state.player_max_hp = stats["max_hp"]
    state.player_hp = state.player_max_hp
    state.lives = stats["lives"]
    state.has_double_dash = stats["has_double_dash"]
    state.has_regen = stats["has_regen"]
    state.has_cd_reduction = stats["has_cd_reduction"]
    state.has_extended_reach = stats.get("has_extended_reach", False)
    state.has_executioner = stats.get("has_executioner", False)
    state.has_spiked_armor = stats.get("has_spiked_armor", False)
    state.equipped_skills = stats.get("equipped_skills", [])

    if stats["coins"] == 0 and stats["level"] == 1 and os.path.exists("save.json"):
        try:
            with open("save.json", "r") as f:
                data = json.load(f)
            level.current_level = data.get("level", 0)
            state.score = data.get("coins", 0)
            state.lives = data.get("lives", 3)
        except:
            level.current_level = 0
    else:

        level.current_level = 0

    level.load_level(level.current_level)

    global _player_spawned, _camera_x, _left_wall_x
    global _world_enemies, _world_coins, _world_spikes, _world_stones, _spawned_chunks, _killed_enemy_ids, _next_enemy_id
    _player_spawned = False
    _camera_x = 0.0
    _left_wall_x = None
    _world_enemies = {}
    _world_coins = {}
    _world_spikes = {}
    _world_stones = {}
    _spawned_chunks = set()
    _killed_enemy_ids = set()
    _next_enemy_id = 0

    state.state = GAME

def _draw_game_frame(screen, camera_x):
    """Render the full game frame (visual only — no physics)."""
    scr_h = screen.get_height()
    scr_w = screen.get_width()
    floor_y = scr_h - 20

    scaled_bgs = _get_scaled_bgs(scr_w, scr_h)
    for i, (_, speed) in enumerate(_bg_layer_data):
        bg = scaled_bgs[i]
        px = int(camera_x * speed) % scr_w
        screen.blit(bg, (-px, 0))
        if px > 0:
            screen.blit(bg, (scr_w - px, 0))

    strip = _get_ground_strip(scr_w, scr_h)
    grass_top_y = floor_y - _TILE_RENDER // 3
    tile_start_x = int(camera_x // _TILE_RENDER) * _TILE_RENDER
    for tx in range(tile_start_x - _TILE_RENDER,
                    tile_start_x + scr_w + _TILE_RENDER * 2,
                    _TILE_RENDER):
        sx = tx - camera_x
        screen.blit(strip, (sx, grass_top_y))

    _, draw_list = _get_visible_platforms(camera_x, scr_w, floor_y)
    for sx, wy, surf in draw_list:
        screen.blit(surf, (sx, wy))

    for stone in level.stones_list:
        stone.draw(screen, camera_x)
    for stone in _active_world_stones:
        stone.draw(screen, camera_x)

    for enemy in level.enemies:
        if enemy.enemy_id not in _killed_enemy_ids:
            enemy.draw(screen, camera_x)

    for coin in level.coins_list:
        coin.draw(screen, camera_x)

    for enemy in _active_world_enemies:
        enemy.draw(screen, camera_x)

    for coin in _active_world_coins:
        coin.draw(screen, camera_x)

    for spike in level.spikes_list:
        spike.draw(screen, camera_x)
    for spike in _active_world_spikes:
        spike.draw(screen, camera_x)

    level.player.draw(screen, camera_x)

_active_world_enemies = []
_active_world_coins = []
_active_world_spikes = []
_active_world_stones = []

def update_game(screen):
    scr_h = screen.get_height()
    scr_w = screen.get_width()
    floor_y = scr_h - 20

    global _player_spawned, _camera_x, _left_wall_x, _screen_shake
    global _active_world_enemies, _active_world_coins, _active_world_spikes, _active_world_stones
    if not _player_spawned:
        level.player.rect.bottom = floor_y
        level.player.spawn_timer = 15
        level.player.speed_boost_timer = 60
        _player_spawned = True

        _left_wall_x = level.player.rect.left

    target_x = level.player.rect.centerx - scr_w // 2

    _camera_x += (target_x - _camera_x) * 0.25

    shake_x = 0
    if _screen_shake > 0:
        import random as _rnd
        shake_x = _rnd.randint(-6, 6) * (_screen_shake / 10.0)
        _screen_shake -= 1
    camera_x = int(_camera_x + shake_x)

    (_active_world_enemies,
     _active_world_coins,
     _active_world_spikes,
     _active_world_stones) = _update_world_entities(camera_x, floor_y, scr_w)

    _draw_game_frame(screen, camera_x)

    floor = pygame.Rect(level.player.rect.x - 50000, floor_y, 100000, 20)
    plat_rects, _ = _get_visible_platforms(camera_x, scr_w, floor_y)
    all_surfaces = [floor] + plat_rects
    one_way_surfaces = plat_rects

    for coin in level.coins_list:
        if not coin.snapped:
            cx = coin.rect.centerx
            cy = coin.rect.centery
            best = None
            best_dist = None

            check_list = list(all_surfaces) + [s.rect for s in level.stones_list]
            for surf in check_list:
                if surf.top > cy:

                    if cx < surf.left:
                        dist = surf.left - cx
                    elif cx > surf.right:
                        dist = cx - surf.right
                    else:
                        dist = 0
                    if best is None or dist < best_dist or (dist == best_dist and surf.top < best.top):
                        best = surf
                        best_dist = dist
            if best is not None:
                coin.rect.bottom = best.top
                coin.rect.centerx = max(best.left + 20, min(best.right - 20, cx))

                for stone in level.stones_list:
                    if stone.rect == best:
                        coin.parent_stone = stone
                        break
                coin.snapped = True

    all_stone_rects = [s.rect for s in level.stones_list] + [s.rect for s in _active_world_stones]

    _enemy_surface_map = []
    for enemy in list(level.enemies) + list(_active_world_enemies):
        if enemy.snapped:
            continue
        ex = enemy.rect.centerx
        ey = enemy.rect.centery
        if enemy.flying:

            best = None
            best_dist = None
            for stone_rect in all_stone_rects:
                if ex < stone_rect.left:
                    dist = stone_rect.left - ex
                elif ex > stone_rect.right:
                    dist = ex - stone_rect.right
                else:
                    dist = 0
                if best is None or dist < best_dist:
                    best = stone_rect
                    best_dist = dist
            if best is not None:
                enemy.rect.centerx = max(best.left + 20, min(best.right - 20, ex))
                enemy.rect.bottom = best.top - 30
                enemy._hover_base_y = enemy.rect.y
                patrol = min(80, (best.width - 40) // 2)
                enemy.left_limit = enemy.rect.centerx - patrol
                enemy.right_limit = enemy.rect.centerx + patrol
                enemy.snapped = True
                _enemy_surface_map.append((enemy, best))
        else:

            best = None
            best_dist = None
            check_list = list(all_surfaces) + all_stone_rects
            for surf in check_list:
                if surf.top > ey:
                    if ex < surf.left:
                        dist = surf.left - ex
                    elif ex > surf.right:
                        dist = ex - surf.right
                    else:
                        dist = 0
                    if best is None or dist < best_dist or (dist == best_dist and surf.top < best.top):
                        best = surf
                        best_dist = dist
            if best is not None:
                enemy.rect.bottom = best.top
                enemy.rect.centerx = max(best.left + 30, min(best.right - 30, ex))
                pad = 40
                patrol = 800 if best.width > 5000 else min(best.width // 2 - pad, 120)
                enemy.left_limit = max(best.left + pad, enemy.rect.centerx - patrol)
                enemy.right_limit = min(best.right - pad, enemy.rect.centerx + patrol)
                enemy.snapped = True
                _enemy_surface_map.append((enemy, best))

    from collections import defaultdict
    surface_groups = defaultdict(list)
    for enemy, surf in _enemy_surface_map:
        if surf.width > 5000:
            continue
        key = (surf.left, surf.top, surf.width, surf.height)
        surface_groups[key].append((enemy, surf))
    for group in surface_groups.values():
        if len(group) <= 1:
            continue

        group.sort(key=lambda pair: pair[0].rect.centerx)
        surf = group[0][1]
        avail_w = surf.width - 60
        min_gap = 50
        count = len(group)
        needed = (count - 1) * min_gap
        if needed <= avail_w:

            start_x = surf.left + 30
            step = avail_w / (count - 1) if count > 1 else 0
            for i, (enemy, _) in enumerate(group):
                enemy.rect.centerx = int(start_x + step * i)
                patrol = min(60, avail_w // 4)
                enemy.left_limit = max(surf.left + 20, enemy.rect.centerx - patrol)
                enemy.right_limit = min(surf.right - 20, enemy.rect.centerx + patrol)
        else:

            start_x = surf.left + 30
            for i, (enemy, _) in enumerate(group):
                enemy.rect.centerx = int(start_x + min_gap * i)
                patrol = min(40, avail_w // 4)
                enemy.left_limit = max(surf.left + 15, enemy.rect.centerx - patrol)
                enemy.right_limit = min(surf.right - 15, enemy.rect.centerx + patrol)

    level.player.update(all_surfaces, one_way_surfaces)

    if _left_wall_x is not None and level.player.rect.left < _left_wall_x:
        level.player.rect.left = _left_wall_x

    for stone in level.stones_list:
        stone.update()

    for stone in _active_world_stones:
        stone.update()

    active_set = set(_active_world_enemies)
    for chunk_enemies in _world_enemies.values():
        for enemy in chunk_enemies:
            if enemy not in active_set and enemy.dying_timer > 0:
                enemy.dying_timer -= 1
                enemy.sprite.update()

    all_surfaces_with_stones = all_surfaces + [s.rect for s in level.stones_list] + [s.rect for s in _active_world_stones]

    for enemy in level.enemies:
        enemy.update(platforms=all_surfaces_with_stones, player_rect=level.player.rect)

    for enemy in _active_world_enemies:
        enemy.update(platforms=all_surfaces_with_stones, player_rect=level.player.rect)

    for spike in level.spikes_list:
        if level.player.rect.colliderect(spike.rect):
            level.player.take_damage(15)

    for spike in _active_world_spikes:
        if level.player.rect.colliderect(spike.rect):
            level.player.take_damage(15)

    for coin in level.coins_list:
        if coin.parent_stone is not None:
            coin.rect.bottom = coin.parent_stone.rect.top

    for coin in level.coins_list:
        if not coin.collected and level.player.rect.colliderect(coin.rect):
            coin.collected = True
            state.score += 1
            save_game()

    for coin in _active_world_coins:
        if not coin.collected and level.player.rect.colliderect(coin.rect):
            coin.collected = True
            state.score += 1
            save_game()

    all_stones = list(level.stones_list) + list(_active_world_stones)
    for stone in all_stones:
        if not stone.used and level.player.rect.colliderect(stone.rect):
            stone.used = True
            heal = stone.HEAL_AMOUNT
            player = level.player
            player.hp = min(player.max_hp, player.hp + heal)
            state.player_hp = player.hp

            _damage_numbers.append(DamageNumber(
                player.rect.centerx, player.rect.top - 10,
                f"+{heal}", (60, 220, 100)))

    for enemy in list(level.enemies):
        if enemy.dead:
            if enemy.enemy_id is not None:
                _killed_enemy_ids.add(enemy.enemy_id)
            level.enemies.remove(enemy)

    for chunk_enemies in _world_enemies.values():
        for enemy in chunk_enemies[:]:
            if enemy.dead:
                if enemy.enemy_id is not None:
                    _killed_enemy_ids.add(enemy.enemy_id)
                chunk_enemies.remove(enemy)

    global _damage_font
    if _damage_font is None:
        _damage_font = get_font("assets/font/Sekuya/Sekuya-Regular.ttf", 18)
    all_active_enemies = list(level.enemies) + _active_world_enemies
    for enemy in all_active_enemies:

        if enemy.dying_timer > 0 or enemy.hp <= 0 or enemy.dead:
            continue

        if enemy.attack_hit_done and level.player.invincible_timer == 0:
            if level.player.rect.colliderect(enemy.rect.inflate(20, 10)):
                level.player.take_damage(enemy.damage)
                _damage_numbers.append(DamageNumber(
                    level.player.rect.centerx, level.player.rect.top,
                    enemy.damage, (255, 60, 60)))

                if getattr(state, "has_spiked_armor", False):
                    enemy.take_damage(enemy.damage)
                    _damage_numbers.append(DamageNumber(
                        enemy.rect.centerx, enemy.rect.top - 20,
                        enemy.damage, (200, 100, 255)))

                enemy.attack_hit_done = False
                enemy.attack_cooldown = 60

        elif level.player.rect.colliderect(enemy.rect) and level.player.invincible_timer == 0 and enemy.attack_timer == 0:
            level.player.take_damage(enemy.damage)
            _damage_numbers.append(DamageNumber(
                level.player.rect.centerx, level.player.rect.top,
                enemy.damage, (255, 60, 60)))

            if getattr(state, "has_spiked_armor", False):
                enemy.take_damage(enemy.damage)
                _damage_numbers.append(DamageNumber(
                    enemy.rect.centerx, enemy.rect.top - 20,
                    enemy.damage, (200, 100, 255)))

    for dn in _damage_numbers[:]:
        dn.update()
        if dn.dead:
            _damage_numbers.remove(dn)

    for dn in _damage_numbers:
        dn.draw(screen, camera_x, _damage_font)

    draw_ui(screen)

    global _player_death_timer
    if _player_death_timer > 0:
        _player_death_timer -= 1
        level.player.sprite.set_state("death")
        level.player.sprite.update()
        if _player_death_timer <= 0:
            state.state = GAME_OVER
            save_game()
        return

    if level.player.rect.y > scr_h + 200 or level.player.hp <= 0:
        _player_death_timer = 24
        level.player.sprite.set_state("death")
        return

def get_all_enemies():
    """Return combined list of level tile-grid enemies + active world enemies (excluding killed)."""
    return [e for e in level.enemies if e.enemy_id not in _killed_enemy_ids] + [e for e in _active_world_enemies if e.enemy_id not in _killed_enemy_ids]
