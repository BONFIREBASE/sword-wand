import math
import os
import random
import pygame
from src.sprites import SpriteSheet, SequenceSheet, AnimatedSprite
from src import state

# GraveRobber sprite config — adjust if frames look wrong
CHAR_PATH = "assets/characters/2 GraveRobber/GraveRobber"
FRAME_W, FRAME_H = 48, 48  # pixels per frame — adjust if sprites look stretched
SCALE = 3  # scale up pixel art (48 -> 144px tall)


def _make_anim(suffix, fps):
    return SpriteSheet(f"{CHAR_PATH}_{suffix}.png", FRAME_W, FRAME_H, SCALE), fps


class Player:
    def __init__(self, x, y):
        self.rect = pygame.Rect(x, y, 40 * SCALE, 50 * SCALE)
        self.speed = 16
        self.jump_power = -44
        self.vel_y = 0
        self.gravity = 3.2
        self.on_ground = False
        self.facing_right = True
        self.attack_timer = 0
        self.invincible_timer = 0
        self._was_on_ground = True
        self.spawn_timer = 0  # set by game.py on level load
        self.coyote_timer = 0   # grace frames after leaving ground
        self.jump_buffer = 0    # buffered jump input before landing
        self.hp = state.player_max_hp
        self.max_hp = state.player_max_hp
        self.damage_flash_timer = 0

        # Build animated sprite
        self.sprite = AnimatedSprite({
            "idle": _make_anim("idle", 8),
            "run": _make_anim("run", 20),
            "jump": _make_anim("jump", 16),
            "attack": _make_anim("attack1", 24),
            "hurt": _make_anim("hurt", 12),
            "death": _make_anim("death", 12),
        }, default_state="idle")

    def update(self, platforms):
        keys = pygame.key.get_pressed()
        moving = False

        if self.spawn_timer > 0:
            self.spawn_timer -= 1

        # Movement
        if keys[pygame.K_LEFT] or keys[pygame.K_a]:
            self.rect.x -= self.speed
            self.facing_right = False
            moving = True
        if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
            self.rect.x += self.speed
            self.facing_right = True
            moving = True

        # Jump input: buffer if pressed mid-air, execute if on ground or coyote time
        jump_pressed = keys[pygame.K_w] or keys[pygame.K_UP]
        if jump_pressed:
            if self.on_ground or self.coyote_timer > 0:
                self.vel_y = self.jump_power
                self.on_ground = False
                self.coyote_timer = 0
                self.jump_buffer = 0
            else:
                # Buffer the jump so it fires as soon as we land
                self.jump_buffer = 3
        if self.jump_buffer > 0:
            self.jump_buffer -= 1

        # Remember where feet were before gravity, for one-way platform check
        prev_bottom = self.rect.bottom

        self.vel_y += self.gravity
        self.rect.y += self.vel_y

        self.on_ground = False
        for plat in platforms:
            if self.rect.colliderect(plat):
                if self.vel_y >= 0 and prev_bottom <= plat.top + 2:
                    # Landing from above — one-way platform behavior
                    self.rect.bottom = plat.top
                    self.vel_y = 0
                    self.on_ground = True
                # NOTE: no head-bump (vel_y < 0) — player passes through
                # platforms from below, which is standard platformer behavior.

        # Ground-proximity check: prevents on_ground flickering caused by
        # sub-pixel gravity when standing still (vel_y rounds to 0 pixels).
        if not self.on_ground and 0 <= self.vel_y < 2:
            feet = pygame.Rect(self.rect.x, self.rect.bottom,
                               self.rect.width, 2)
            for plat in platforms:
                if feet.colliderect(plat):
                    self.rect.bottom = plat.top
                    self.vel_y = 0
                    self.on_ground = True
                    break

        # Coyote time: allow jumping briefly after walking off an edge
        if self.on_ground:
            self.coyote_timer = 3  # 3 frames ≈ 100ms grace
            # Buffered jump auto-fires on landing
            if self.jump_buffer > 0:
                self.vel_y = self.jump_power
                self.on_ground = False
                self.jump_buffer = 0
        elif self.coyote_timer > 0:
            self.coyote_timer -= 1

        if self.attack_timer > 0:
            self.attack_timer -= 1
        if self.invincible_timer > 0:
            self.invincible_timer -= 1
        if self.damage_flash_timer > 0:
            self.damage_flash_timer -= 1

        # Animation state — skip frame 0 (wind-up) on jump/attack for instant feedback
        self.sprite.facing_right = self.facing_right
        if self.attack_timer > 0:
            self.sprite.set_state("attack", start_frame=1)
        elif not self.on_ground:
            self.sprite.set_state("jump", start_frame=1)
        elif moving:
            self.sprite.set_state("run")
        else:
            self.sprite.set_state("idle")
        self.sprite.update()

    def take_damage(self, amount):
        if self.invincible_timer > 0 or self.spawn_timer > 0:
            return
        self.hp -= amount
        self.invincible_timer = 60  # 2 sec grace at 30fps
        self.damage_flash_timer = 8
        state.player_hp = self.hp
        if self.hp <= 0:
            self.hp = 0
            state.player_hp = 0

    def attack(self):
        if self.attack_timer == 0:
            self.attack_timer = 6  # shorter lockout = more responsive
            if self.facing_right:
                return pygame.Rect(self.rect.right, self.rect.y, 60, self.rect.height)
            else:
                return pygame.Rect(self.rect.left - 60, self.rect.y, 60, self.rect.height)
        return None

    def draw(self, screen, camera_x=0):
        x = self.rect.centerx - camera_x
        y = self.rect.bottom

        # Spawn animation effect (15 frames at 30fps)
        if self.spawn_timer > 0:
            progress = 1.0 - (self.spawn_timer / 15.0)

            # Pixelated left-to-right sweep overlay
            sw = screen.get_width()
            sh = screen.get_height()
            block = 8  # pixel block size
            cols = (sw + block - 1) // block
            rows = (sh + block - 1) // block
            filled_cols = max(0, int(cols * progress))
            if filled_cols > 0:
                low = pygame.Surface((filled_cols, rows), pygame.SRCALPHA)
                low.fill((255, 255, 255, 60))
                sweep = pygame.transform.scale(low, (filled_cols * block, sh))
                screen.blit(sweep, (0, 0))

            # Pixelated rightward chevrons, fading out
            arrow_alpha = max(0, min(255, int(255 * (1.0 - progress))))
            if arrow_alpha > 0:
                color = (255, 215, 0)
                ch_w, ch_h = 8, 6
                ch_small = pygame.Surface((ch_w, ch_h), pygame.SRCALPHA)
                for py in range(ch_h):
                    mid = ch_h // 2
                    if py <= mid:
                        start = py
                    else:
                        start = ch_h - 1 - py
                    for px in range(start, ch_w):
                        ch_small.set_at((px, py), (*color, arrow_alpha))
                ch_big = pygame.transform.scale(ch_small, (ch_w * 4, ch_h * 4))
                for i in range(3):
                    ax = x + 30 + i * 32
                    ay = y - 80
                    screen.blit(ch_big, (ax, ay))

            # Teleport beam coming down
            beam_width = int(40 * (1.0 - progress))
            if beam_width > 0:
                beam_rect = pygame.Rect(x - beam_width // 2, 0, beam_width, y)
                beam_surf = pygame.Surface((beam_width, y), pygame.SRCALPHA)
                beam_surf.fill((100, 200, 255, int(150 * (1.0 - progress))))
                screen.blit(beam_surf, beam_rect.topleft)

            # Expanding energy rings on the floor
            ring_radius = int(progress * 100)
            ring_thickness = max(1, int(5 * (1.0 - progress)))
            pygame.draw.ellipse(screen, (100, 200, 255),
                                (x - ring_radius, y - ring_radius // 4, ring_radius * 2, ring_radius // 2),
                                ring_thickness)

            # Character fades in
            alpha = int(progress * 255)
        else:
            alpha = 255

        # Damage flash: tint red briefly
        if self.damage_flash_timer > 0 and self.damage_flash_timer % 2 == 0:
            flash_alpha = min(alpha, 128)
        else:
            flash_alpha = alpha
        self.sprite.draw(screen, x, y, alpha=flash_alpha)


# ---------------------------------------------------------------------------
# Coin / collectible sprite  (chest.png — 6‑frame animated chest)
# Loaded lazily because entities.py is imported before the display is created.
# ---------------------------------------------------------------------------
_CHEST_PATH = "assets/craftpix-net-926878-free-platformer-game-tileset-pixel-art/PNG/chest.png"
_chest_frames = None  # lazy‑loaded on first use


def _load_chest_frames():
    global _chest_frames
    if _chest_frames is not None:
        return
    _chest_frames = []
    if not os.path.exists(_CHEST_PATH):
        return
    sheet = pygame.image.load(_CHEST_PATH).convert_alpha()
    sw, sh = sheet.get_size()
    fw = sw // 6
    for i in range(6):
        frame = sheet.subsurface((i * fw, 0, fw, sh)).copy()
        frame = pygame.transform.scale(frame, (int(fw * 2), int(sh * 2)))
        _chest_frames.append(frame)


class Coin:
    def __init__(self, x, y):
        self.rect = pygame.Rect(x, y, 40, 40)
        self.collected = False
        self._anim_timer = 0
        self._frame_idx = 0
        self.parent_stone = None
        self.snapped = False

    def draw(self, screen, camera_x):
        if self.collected:
            return
        _load_chest_frames()
        if _chest_frames:
            # Animate at ~4 fps (tick every 7-8 frames at 30 fps)
            self._anim_timer += 1
            if self._anim_timer >= 8:
                self._anim_timer = 0
                self._frame_idx = (self._frame_idx + 1) % len(_chest_frames)
            frame = _chest_frames[self._frame_idx]
            sx = self.rect.centerx - camera_x - frame.get_width() // 2
            sy = self.rect.bottom - frame.get_height()
            screen.blit(frame, (sx, sy))
        else:
            # Fallback to old circles
            pygame.draw.circle(screen, (255, 215, 0),
                               (self.rect.centerx - camera_x, self.rect.centery), 10)
            pygame.draw.circle(screen, (255, 255, 100),
                               (self.rect.centerx - camera_x - 2,
                                self.rect.centery - 2), 4)


# ---------------------------------------------------------------------------
# Monster_10 enemy — skeleton warrior with full animation set
# ---------------------------------------------------------------------------
_ENEMY_BASE = "assets/enemy/Monster_10/PNG/PNG Sequences"
_ENEMY_SCALE = 0.4
_enemy_anim_cache = {}


def _get_enemy_anim(folder_name, fps):
    key = (folder_name, _ENEMY_SCALE)
    if key not in _enemy_anim_cache:
        path = os.path.join(_ENEMY_BASE, folder_name)
        _enemy_anim_cache[key] = (SequenceSheet(path, _ENEMY_SCALE), fps)
    return _enemy_anim_cache[key]


class Enemy(pygame.sprite.Sprite):
    def __init__(self, x, y, patrol_range=80, hp=2, damage=10):
        super().__init__()
        self.sprite = AnimatedSprite({
            "idle": _get_enemy_anim("Idle", 10),
            "walk": _get_enemy_anim("Walking", 14),
            "attack": _get_enemy_anim("Attack", 16),
            "dying": _get_enemy_anim("Dying", 14),
        }, default_state="idle")
        self.sprite.facing_right = False
        self.speed = 2          # slightly slower so player can dodge
        self.direction = 1
        self.left_limit = x - patrol_range
        self.right_limit = x + patrol_range
        self.hp = hp
        self.max_hp = hp
        self.damage = damage
        self.flash_timer = 0
        self.dying_timer = 0
        self.snapped = False
        # Physics
        self.vel_y = 0
        self.gravity = 2.5
        self.on_ground = False
        # Use first idle frame to size the rect
        first_frame = self.sprite.anims["idle"][0].frames[0]
        self.rect = first_frame.get_rect(midbottom=(x, y))
        self.image = first_frame

    def update(self, platforms=None):
        if self.dying_timer > 0:
            self.dying_timer -= 1
            self.sprite.update()
            return

        # --- Gravity & vertical physics ---
        self.vel_y += self.gravity
        prev_bottom = self.rect.bottom
        self.rect.y += int(self.vel_y)

        self.on_ground = False
        if platforms:
            for plat in platforms:
                if self.rect.colliderect(plat):
                    if self.vel_y >= 0 and prev_bottom <= plat.top + 4:
                        self.rect.bottom = plat.top
                        self.vel_y = 0
                        self.on_ground = True
                        break

        # --- Horizontal patrol (only move when on a surface) ---
        if self.on_ground:
            self.rect.x += self.speed * self.direction
            # Clamp to patrol limits and reverse at edges
            if self.rect.centerx <= self.left_limit:
                self.direction = 1
                self.rect.centerx = self.left_limit
            elif self.rect.centerx >= self.right_limit:
                self.direction = -1
                self.rect.centerx = self.right_limit

        if self.flash_timer > 0:
            self.flash_timer -= 1
        self.sprite.facing_right = (self.direction > 0)
        self.sprite.set_state("walk" if self.on_ground else "idle")
        self.sprite.update()

    def take_damage(self, amount):
        if self.dying_timer > 0:
            return False
        self.hp -= amount
        self.flash_timer = 6
        if self.hp <= 0:
            self.dying_timer = 18
            self.sprite.set_state("dying")
            return True
        return False

    @property
    def dead(self):
        return self.hp <= 0 and self.dying_timer <= 0

    def draw(self, screen, camera_x):
        frame = self.sprite.get_frame()
        # Damage flash
        if self.flash_timer > 0 and self.flash_timer % 2 == 0:
            flash_frame = frame.copy()
            flash_frame.fill((255, 255, 255, 100), special_flags=pygame.BLEND_RGBA_ADD)
            frame = flash_frame
        sx = self.rect.centerx - camera_x - frame.get_width() // 2
        sy = self.rect.bottom - frame.get_height()
        screen.blit(frame, (sx, sy))
        # Health bar above enemy
        if self.max_hp > 1 and self.dying_timer == 0:
            bar_w = frame.get_width()
            bar_h = 4
            bar_x = self.rect.centerx - camera_x - bar_w // 2
            bar_y = sy - 8
            pygame.draw.rect(screen, (60, 0, 0), (bar_x, bar_y, bar_w, bar_h))
            fill_w = int(bar_w * (self.hp / self.max_hp))
            if fill_w > 0:
                pygame.draw.rect(screen, (220, 30, 30), (bar_x, bar_y, fill_w, bar_h))


# ---------------------------------------------------------------------------
# Spike hazard  (Spikes.png — static trap sprite)
# ---------------------------------------------------------------------------
_SPIKE_PATH = "assets/craftpix-net-926878-free-platformer-game-tileset-pixel-art/PNG/Spikes.png"
_spike_img = None


def _load_spike():
    global _spike_img
    if _spike_img is not None:
        return
    if not os.path.exists(_SPIKE_PATH):
        return
    sheet = pygame.image.load(_SPIKE_PATH).convert_alpha()
    # Use the tall spike at x=192, y=2, w=31, h=49
    spike = sheet.subsurface((192, 2, 31, 49)).copy()
    _spike_img = pygame.transform.scale(spike, (48, 72))


class Spike:
    def __init__(self, x, y):
        _load_spike()
        if _spike_img:
            self.rect = _spike_img.get_rect(midbottom=(x, y))
        else:
            self.rect = pygame.Rect(x, y, 48, 48)

    def draw(self, screen, camera_x):
        _load_spike()
        if _spike_img:
            sx = self.rect.x - camera_x
            sy = self.rect.y
            screen.blit(_spike_img, (sx, sy))
        else:
            pygame.draw.rect(screen, (150, 150, 150),
                             (self.rect.x - camera_x, self.rect.y, 48, 48))


# ---------------------------------------------------------------------------
# Flying stone platform  (Flying_stone.png — floating rock platform)
# ---------------------------------------------------------------------------
_STONE_PATH = "assets/craftpix-net-926878-free-platformer-game-tileset-pixel-art/PNG/Flying_stone.png"
_stone_img = None


def _load_stone():
    global _stone_img
    if _stone_img is not None:
        return
    if not os.path.exists(_STONE_PATH):
        return
    sheet = pygame.image.load(_STONE_PATH).convert_alpha()
    # Frame at x=58, y=31, w=28, h=51
    stone = sheet.subsurface((58, 31, 28, 51)).copy()
    _stone_img = pygame.transform.scale(stone, (84, 153))


class FlyingStone:
    HEAL_AMOUNT = 20   # HP restored when player touches this stone

    def __init__(self, x, y, hover_range=30, speed=1):
        _load_stone()
        if _stone_img:
            self.rect = _stone_img.get_rect(midbottom=(x, y))
        else:
            self.rect = pygame.Rect(x, y, 84, 20)
        self.base_y = y
        self.hover_range = hover_range
        self.speed = speed
        self._phase = 0
        self.used = False          # True after player has collected the heal

    def update(self):
        self._phase += self.speed * 0.10
        self.rect.y = self.base_y + int(self.hover_range * (1 + math.sin(self._phase)) / 2)

    def draw(self, screen, camera_x):
        _load_stone()
        if _stone_img:
            sx = self.rect.x - camera_x
            sy = self.rect.y
            if self.used:
                # Draw dimmed to show the stone is spent
                dim = _stone_img.copy()
                dim.set_alpha(60)
                screen.blit(dim, (sx, sy))
            else:
                screen.blit(_stone_img, (sx, sy))
                # Soft green glow aura to hint it's a heal pickup
                glow_w = self.rect.width + 16
                glow_h = 18
                glow = pygame.Surface((glow_w, glow_h), pygame.SRCALPHA)
                glow.fill((60, 220, 100, 55))
                screen.blit(glow, (sx - 8, sy + self.rect.height - 6))
        else:
            color = (60, 120, 60) if not self.used else (50, 50, 50)
            pygame.draw.rect(screen, color,
                             (self.rect.x - camera_x, self.rect.y, self.rect.width, 20))


# ---------------------------------------------------------------------------
# Floating damage number
# ---------------------------------------------------------------------------
class DamageNumber:
    def __init__(self, x, y, amount, color=(255, 60, 60)):
        self.x = x
        self.y = y
        self.amount = amount
        self.color = color
        self.life = 20
        self.vy = -3

    def update(self):
        self.y += self.vy
        self.vy += 0.15
        self.life -= 1

    @property
    def dead(self):
        return self.life <= 0

    def draw(self, screen, camera_x, font):
        alpha = min(255, int(255 * (self.life / 20)))
        text = font.render(str(self.amount), True, self.color)
        text.set_alpha(alpha)
        sx = self.x - camera_x - text.get_width() // 2
        screen.blit(text, (sx, self.y))
