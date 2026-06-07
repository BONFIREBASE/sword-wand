import math
import os
import random
import pygame
from src.sprites import SpriteSheet, SequenceSheet, AnimatedSprite
from src import state

FRAME_W, FRAME_H = 48, 48  # pixels per frame — adjust if sprites look stretched
SCALE = 3  # scale up pixel art (48 -> 144px tall)


class Player:
    def __init__(self, x, y, char_type="GraveRobber"):
        self.char_type = char_type
        self.rect = pygame.Rect(x, y, 40 * SCALE, 50 * SCALE)
        
        # Base stats depend on character
        if self.char_type == "Woodcutter":
            self.speed = 6  # Nerfed from 12
            self.jump_power = -40
            self.gravity = 3.5
        else: # GraveRobber
            self.speed = 8  # Nerfed from 16
            self.jump_power = -44
            self.gravity = 3.2

        self.vel_y = 0
        self.on_ground = False
        self.facing_right = True
        self.attack_timer = 0
        self.attack_cooldown = 0
        self.skill2_timer = 0
        self.skill2_cooldown = 0
        self.skill3_timer = 0
        self.skill3_cooldown = 0
        self.invincible_timer = 0
        self._was_on_ground = True
        self.spawn_timer = 0  # set by game.py on level load
        self.coyote_timer = 0   # grace frames after leaving ground
        self.jump_buffer = 0    # buffered jump input before landing
        self._jump_was_pressed = False  # require release between jumps
        self.jump_count = 0
        self.air_dash_timer = 0
        self.air_dash_cooldown = 0
        self.idle_regen_timer = 0
        self.leap_strike_active = False
        self.leap_strike_phase = 0
        self.rage_timer = 0
        self.rage_smash_phase = 0
        self.speed_boost_timer = 0
        self.pending_attack_rect = None
        self.hp = state.player_max_hp
        self.max_hp = state.player_max_hp
        self.damage_flash_timer = 0

        # Determine path
        if self.char_type == "Woodcutter":
            char_path = "assets/characters/1 Woodcutter/Woodcutter"
        else:
            char_path = "assets/characters/2 GraveRobber/GraveRobber"

        def _make_anim_local(suffix, fps):
            return SpriteSheet(f"{char_path}_{suffix}.png", FRAME_W, FRAME_H, SCALE), fps

        if self.char_type == "Woodcutter":
            skill2_anim = _make_anim_local("attack3", 14)
            skill3_anim = _make_anim_local("attack1", 16)
        else:
            skill2_anim = _make_anim_local("attack2", 20)
            skill3_anim = _make_anim_local("attack3", 18)

        # Build animated sprite
        self.sprite = AnimatedSprite({
            "idle": _make_anim_local("idle", 8),
            "run": _make_anim_local("run", 20),
            "jump": _make_anim_local("jump", 16),
            "attack": _make_anim_local("attack1", 24),
            "skill2": skill2_anim,
            "skill3": skill3_anim,
            "hurt": _make_anim_local("hurt", 12),
            "death": _make_anim_local("death", 12),
        }, default_state="idle")

    def update(self, platforms):
        keys = pygame.key.get_pressed()
        moving = False

        if self.spawn_timer > 0:
            self.spawn_timer -= 1

        if self.speed_boost_timer > 0:
            self.speed_boost_timer -= 1

        current_speed = self.speed * 2 if self.speed_boost_timer > 0 else self.speed

        # Movement (disabled during Rampage)
        if self.rage_timer == 0:
            if keys[pygame.K_LEFT] or keys[pygame.K_a]:
                self.rect.x -= current_speed
                self.facing_right = False
                moving = True
            if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
                self.rect.x += current_speed
                self.facing_right = True
                moving = True

            # Jump input: require key release between jumps to prevent spam
            jump_pressed = keys[pygame.K_w] or keys[pygame.K_UP]
            if jump_pressed and not self._jump_was_pressed:
                if self.on_ground or self.coyote_timer > 0:
                    self.vel_y = self.jump_power
                    self.on_ground = False
                    self.coyote_timer = 0
                    self.jump_buffer = 0
                    self.jump_count = 1
                elif self.jump_count == 1 and state.has_double_dash and self.air_dash_cooldown == 0:
                    self.vel_y = self.jump_power * 0.3
                    self.air_dash_timer = 10  # Nerfed from 15
                    self.air_dash_cooldown = 90  # 3 seconds at 30 fps
                    self.jump_count = 2
                    self.jump_buffer = 0
                else:
                    # Buffer the jump so it fires as soon as we land
                    self.jump_buffer = 3
            if self.jump_buffer > 0:
                self.jump_buffer -= 1
            self._jump_was_pressed = jump_pressed

        # Remember where feet were before gravity, for one-way platform check
        prev_bottom = self.rect.bottom

        if self.air_dash_cooldown > 0:
            self.air_dash_cooldown -= 1

        if self.air_dash_timer > 0:
            self.air_dash_timer -= 1
            self.vel_y = 0
            dash_speed = 22  # Nerfed from 30
            if self.facing_right:
                self.rect.x += dash_speed
            else:
                self.rect.x -= dash_speed
        else:
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

        # Leap Strike (Woodcutter E): Two-stage jump with forward momentum and mid-air chop
        if self.leap_strike_active:
            # Move forward slightly during the leap
            forward_speed = 8
            if self.facing_right:
                self.rect.x += forward_speed
            else:
                self.rect.x -= forward_speed
                
            if self.leap_strike_phase == 1 and self.vel_y >= 0:
                # Reached apex of first jump, trigger second higher jump
                self.vel_y = self.jump_power * 1.1  # Nerfed from 1.5
                self.on_ground = False
                self.leap_strike_phase = 2
                
            elif self.leap_strike_phase == 2 and self.vel_y > 15:
                # Started falling very fast, trigger chop animation right before landing
                self.leap_strike_phase = 3
                self.skill3_timer = 20  # Start chop animation mid-air
                
            elif (self.leap_strike_phase == 3 or self.leap_strike_phase == 2) and self.on_ground:
                # Landed! Execute damage
                self.leap_strike_active = False
                self.leap_strike_phase = 0
                self.skill3_timer = 10  # Finish off the chop animation upon landing
                hitbox_w = 250
                # Center the damage exactly where he lands so the user can aim to land on enemies
                self.pending_attack_rect = pygame.Rect(self.rect.centerx - hitbox_w // 2, self.rect.bottom - 60, hitbox_w, 60)
                self.pending_attack_damage_type = 3
                # Screen shake effect
                import src.game
                src.game._screen_shake = 12

        # Rage Smash (Woodcutter Q): Rampage for 4 seconds
        if self.rage_timer > 0:
            self.rage_timer -= 1
            if self.rage_timer == 0:
                self.speed_boost_timer = 60  # 2 seconds speed boost after Rampage
            
            if self.on_ground and self.rage_smash_phase == 0:
                self.vel_y = self.jump_power * 1.0
                self.on_ground = False
                self.rage_smash_phase = 1
                
            elif self.rage_smash_phase == 1 and self.vel_y >= 0:
                # Reached apex of jump, start falling
                self.rage_smash_phase = 2
                self.skill2_timer = 20  # Start attack3 chop animation mid-air
                
            elif self.rage_smash_phase == 2 and self.on_ground:
                # Landed! Execute smash
                self.rage_smash_phase = 0
                self.skill2_timer = 15  # Play the chop animation
                self.facing_right = not self.facing_right  # Flip direction front and back!
                hitbox_w = 400
                hitbox_h = 400  # Make it extremely tall to hit airborne enemies!
                # Zone covers front, back, and way up into the air
                self.pending_attack_rect = pygame.Rect(self.rect.centerx - hitbox_w // 2, self.rect.bottom - hitbox_h, hitbox_w, hitbox_h)
                self.pending_attack_damage_type = 4
                # Screen shake effect gets bigger as rampage goes on
                shake_intensity = 15 + int(15 * (1.0 - (self.rage_timer / 120.0)))
                import src.game
                src.game._screen_shake = shake_intensity

        # GraveRobber Q (Ultimate AoE Spin): Continuous damage around her
        if self.char_type == "GraveRobber" and self.skill2_timer > 0:
            if self.skill2_timer % 10 == 0:
                rad_w = 260
                if getattr(state, "has_extended_reach", False):
                    rad_w = int(rad_w * 1.3)
                self.pending_attack_rect = pygame.Rect(self.rect.centerx - rad_w // 2, self.rect.y - 30, rad_w, self.rect.height + 60)
                self.pending_attack_damage_type = 4

        if self.on_ground:
            self.jump_count = 0

        # Coyote time: allow jumping briefly after walking off an edge
        if self.on_ground:
            self.coyote_timer = 3  # 3 frames ≈ 100ms grace
            # Buffered jump auto-fires on landing
            if self.jump_buffer > 0:
                self.vel_y = self.jump_power
                self.on_ground = False
                self.jump_buffer = 0
                self.jump_count = 1
        elif self.coyote_timer > 0:
            self.coyote_timer -= 1

        if self.attack_timer > 0:
            self.attack_timer -= 1
        if self.attack_cooldown > 0:
            self.attack_cooldown -= 1
        if self.skill2_timer > 0:
            self.skill2_timer -= 1
        if self.skill2_cooldown > 0:
            self.skill2_cooldown -= 1
        if self.skill3_timer > 0:
            self.skill3_timer -= 1
        if self.skill3_cooldown > 0:
            self.skill3_cooldown -= 1
        if self.invincible_timer > 0:
            self.invincible_timer -= 1
        if self.damage_flash_timer > 0:
            self.damage_flash_timer -= 1

        # Animation state — skip frame 0 (wind-up) on jump/attack for instant feedback
        self.sprite.facing_right = self.facing_right
        if self.air_dash_timer > 0:
            self.sprite.set_state("skill3", start_frame=1)
        elif self.skill3_timer > 0:
            self.sprite.set_state("skill3", start_frame=1)
        elif self.skill2_timer > 0:
            self.sprite.set_state("skill2", start_frame=1)
        elif self.attack_timer > 0:
            self.sprite.set_state("attack", start_frame=1)
        elif not self.on_ground:
            self.sprite.set_state("jump", start_frame=1)
        elif moving:
            self.sprite.set_state("run")
        else:
            self.sprite.set_state("idle")
        self.sprite.update()

        # Idle Regen Logic (500ms = 15 frames at 30 FPS)
        is_idle = (not moving) and self.on_ground and (self.attack_timer == 0) and (self.skill2_timer == 0) and (self.skill3_timer == 0) and (self.air_dash_timer == 0)
        if is_idle and getattr(state, "has_regen", False):
            self.idle_regen_timer += 1
            if self.idle_regen_timer >= 15:
                self.idle_regen_timer = 0
                if self.hp < self.max_hp:
                    self.hp += 1
                    state.player_hp = self.hp
                    from src.game import spawn_damage_number
                    spawn_damage_number(self.rect.centerx, self.rect.top - 15, "+1 HP", (60, 220, 100))
        else:
            self.idle_regen_timer = 0

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
        if self.rage_timer > 0: return None
        if self.attack_timer == 0 and self.attack_cooldown == 0:
            if self.char_type == "Woodcutter":
                self.attack_timer = 10
                self.attack_cooldown = 40  # Slower attack
                width = 80  # Wider arc
            else:
                self.attack_timer = 6
                self.attack_cooldown = 30
                width = 60
            
            if getattr(state, "has_extended_reach", False):
                width = int(width * 1.3)
            
            if self.facing_right:
                return pygame.Rect(self.rect.right, self.rect.y, width, self.rect.height)
            else:
                return pygame.Rect(self.rect.left - width, self.rect.y, width, self.rect.height)
        return None

    def skill2(self):
        if self.rage_timer > 0: return None
        if self.skill2_timer == 0 and self.skill2_cooldown == 0:
            if self.char_type == "Woodcutter":
                base_cd = 300  # 10 seconds at 30 fps
                self.skill2_cooldown = base_cd // 2 if getattr(state, "has_cd_reduction", False) else base_cd
                # Ultimate Rage Smash: Enter rampage mode for 4 seconds
                self.rage_timer = 120
                self.rage_smash_phase = 0
                self._skill2_is_smash = True
                return None
            else:
                base_cd = 300
                self.skill2_timer = 30
                self.skill2_cooldown = base_cd // 2 if getattr(state, "has_cd_reduction", False) else base_cd
                # Ultimate AoE spin
                self._skill2_slash_angles = [0, 72, 144, 216, 288]
                return pygame.Rect(self.rect.centerx - 130, self.rect.y - 30, 260, self.rect.height + 60)
        return None

    def skill3(self):
        if self.rage_timer > 0: return None
        if self.skill3_timer == 0 and self.skill3_cooldown == 0:
            if self.char_type == "Woodcutter":
                base_cd = 210
                self.skill3_cooldown = base_cd // 2 if getattr(state, "has_cd_reduction", False) else base_cd
                # First jump is a little low
                self.vel_y = self.jump_power * 0.6  # Nerfed from 0.8
                self.on_ground = False
                self.leap_strike_active = True
                self.leap_strike_phase = 1
                return None
            else:
                self.skill3_timer = 16
                base_cd = 60
                lunge_dist = 130
                hitbox_w = 80
            
                self.skill3_cooldown = base_cd // 2 if getattr(state, "has_cd_reduction", False) else base_cd
                
                if self.facing_right:
                    self.rect.x += lunge_dist
                    return pygame.Rect(self.rect.left - 20, self.rect.y, hitbox_w, self.rect.height)
                else:
                    self.rect.x -= lunge_dist
                    return pygame.Rect(self.rect.right - hitbox_w + 20, self.rect.y, hitbox_w, self.rect.height)
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

        # Skill2 ultimate slash VFX — spinning arcs
        # Skill2 ultimate slash VFX
        if self.skill2_timer > 0:
            if getattr(self, '_skill2_is_smash', False):
                # Timber Smash VFX
                progress = 1.0 - (self.skill2_timer / 20.0)
                if progress > 0:
                    # Rampage progress scales from 0.0 to 1.0
                    rampage_progress = 1.0
                    if self.rage_timer > 0:
                        rampage_progress = 1.0 - (self.rage_timer / 120.0)
                    
                    # Effect gets larger as the rampage goes on
                    base_r = 100 + (rampage_progress * 150)
                    
                    shock_alpha = max(0, min(255, int(255 * (1.0 - progress) * 1.5)))
                    shock_color = (255, 100 + int(100 * (1.0 - rampage_progress)), 50, shock_alpha)
                    shock_r = int(base_r * progress * 2)
                    sx = x
                    sy = y
                    pygame.draw.ellipse(screen, shock_color, (sx - shock_r, sy - shock_r // 3, shock_r * 2, shock_r // 1.5), max(2, int(10 * (1.0 - progress))))
            elif hasattr(self, '_skill2_slash_angles'):
                progress = 1.0 - (self.skill2_timer / 22.0)
                for base_angle in self._skill2_slash_angles:
                    # Each slash rotates over time
                    angle = math.radians(base_angle + progress * 360)
                    arc_r = int(80 + progress * 40)
                    # Draw a thick arc
                    arc_points = []
                    arc_span = 60  # degrees
                    for s in range(12):
                        a = angle - math.radians(arc_span / 2) + s * math.radians(arc_span / 11)
                        px = x + int(arc_r * math.cos(a))
                        py = y - 60 + int(arc_r * math.sin(a) * 0.6)
                        arc_points.append((px, py))
                    if len(arc_points) >= 2:
                        alpha_slash = int(200 * (1.0 - progress))
                        color_slash = (255, 200, 60, alpha_slash) if alpha_slash > 0 else (255, 200, 60, 0)
                        pygame.draw.lines(screen, (255, 200, 60), False, arc_points, max(2, int(4 * (1.0 - progress))))

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
# Random enemy — picks from available monster assets
# ---------------------------------------------------------------------------
_ENEMY_SCALE = 0.4
_enemy_anim_cache = {}

_ENEMY_TYPES = [
    {"name": "Monster_1",  "path": "assets/enemy/Monster_1/PNG/PNG Sequences",  "walk": "Fly",    "idle_fps": 10, "walk_fps": 12, "attack_fps": 14, "dying_fps": 12, "flying": False},
    {"name": "Monster_2",  "path": "assets/enemy/Monster_2/PNG/PNG Sequences",  "walk": "Fly",    "idle_fps": 10, "walk_fps": 12, "attack_fps": 14, "dying_fps": 12, "flying": True},
    {"name": "Monster_3",  "path": "assets/enemy/Monster_3/PNG/PNG Sequences",  "walk": "Fly",    "idle_fps": 10, "walk_fps": 12, "attack_fps": 14, "dying_fps": 12, "flying": True},
    {"name": "Monster_4",  "path": "assets/enemy/Monster_4/PNG/PNG Sequences",  "walk": "Fly",    "idle_fps": 10, "walk_fps": 12, "attack_fps": 14, "dying_fps": 12, "flying": True},
    {"name": "Monster_10", "path": "assets/enemy/Monster_10/PNG/PNG Sequences", "walk": "Walking", "idle_fps": 10, "walk_fps": 14, "attack_fps": 16, "dying_fps": 14, "flying": False},
]


def _get_enemy_anim(base_path, folder_name, fps):
    key = (base_path, folder_name, _ENEMY_SCALE)
    if key not in _enemy_anim_cache:
        path = os.path.join(base_path, folder_name)
        _enemy_anim_cache[key] = (SequenceSheet(path, _ENEMY_SCALE), fps)
    return _enemy_anim_cache[key]


class Enemy(pygame.sprite.Sprite):
    def __init__(self, x, y, patrol_range=80, hp=2, damage=10, enemy_id=None, xp_value=10):
        super().__init__()
        import random
        self.enemy_id = enemy_id
        self.xp_value = xp_value
        self.monster = random.choice(_ENEMY_TYPES)
        base = self.monster["path"]
        self.sprite = AnimatedSprite({
            "idle": _get_enemy_anim(base, "Idle", self.monster["idle_fps"]),
            "walk": _get_enemy_anim(base, self.monster["walk"], self.monster["walk_fps"]),
            "attack": _get_enemy_anim(base, "Attack", self.monster["attack_fps"]),
            "dying": _get_enemy_anim(base, "Dying", self.monster["dying_fps"]),
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
        self.flying = self.monster["flying"]
        # Physics
        self.vel_y = 0
        self.gravity = 2.5
        self.on_ground = False
        # Hover for flying enemies
        self._hover_timer = 0
        # Attack state
        self.attack_timer = 0
        self.attack_cooldown = 0
        self.attack_hit_done = False
        # Use first idle frame to size the rect
        first_frame = self.sprite.anims["idle"][0].frames[0]
        self.rect = first_frame.get_rect(midbottom=(x, y))
        self._hover_base_y = self.rect.y  # must use rect.y (top), NOT y (midbottom)
        self.image = first_frame

    def update(self, platforms=None, player_rect=None):
        if self.dying_timer > 0:
            self.dying_timer -= 1
            self.sprite.update()
            return
        if self.hp <= 0:
            return

        # --- Attack cooldown tick ---
        if self.attack_cooldown > 0:
            self.attack_cooldown -= 1

        # --- Attack state handling ---
        if self.attack_timer > 0:
            self.attack_timer -= 1
            self.sprite.update()
            # Deal damage roughly mid-attack (when anim is ~halfway)
            if not self.attack_hit_done and player_rect is not None:
                attack_frames = len(self.sprite.anims["attack"][0].frames)
                if self.sprite.frame_index >= attack_frames // 2:
                    if self.rect.colliderect(player_rect.inflate(20, 10)):
                        self.attack_hit_done = True
                        # damage is applied by game.py after checking this flag
            # End attack
            if self.attack_timer <= 0 or self.sprite.is_finished():
                self.attack_timer = 0
                self.attack_cooldown = 60  # Cooldown applies even if attack misses
                self.sprite.set_state("idle")
            if self.flash_timer > 0:
                self.flash_timer -= 1
            return

        if self.flying:
            # --- Flying patrol (no gravity, gentle hover) ---
            self._hover_timer += 1
            hover_offset = int(4 * __import__('math').sin(self._hover_timer * 0.08))
            self.rect.y = self._hover_base_y + hover_offset
            # Flying enemies always patrol horizontally
            if player_rect is not None:
                dx = player_rect.centerx - self.rect.centerx
                dy = player_rect.centery - self.rect.centery
                if abs(dx) < 150 and abs(dy) < 180 and self.attack_cooldown == 0:
                    self.direction = 1 if dx > 0 else -1
                    self.sprite.facing_right = (self.direction > 0)
                    self.sprite.set_state("attack", oneshot=True)
                    attack_frames = len(self.sprite.anims["attack"][0].frames)
                    self.attack_timer = int(30 / self.sprite.anims["attack"][1] * attack_frames) + 2
                    self.attack_hit_done = False
                    self.sprite.update()
                    return
                elif abs(dx) < 300 and abs(dy) < 250:
                    self.direction = 1 if dx > 0 else -1

            self.rect.x += self.speed * self.direction
            if self.rect.centerx <= self.left_limit:
                self.direction = 1
                self.rect.centerx = self.left_limit
            elif self.rect.centerx >= self.right_limit:
                self.direction = -1
                self.rect.centerx = self.right_limit
        else:
            # --- Ground enemy: Gravity & vertical physics ---
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
                # Face player if close
                if player_rect is not None:
                    dx = player_rect.centerx - self.rect.centerx
                    dy = player_rect.centery - self.rect.centery
                    if abs(dx) < 150 and abs(dy) < 120 and self.attack_cooldown == 0:
                        # Start attack!
                        self.direction = 1 if dx > 0 else -1
                        self.sprite.facing_right = (self.direction > 0)
                        self.sprite.set_state("attack", oneshot=True)
                        attack_frames = len(self.sprite.anims["attack"][0].frames)
                        self.attack_timer = int(30 / self.sprite.anims["attack"][1] * attack_frames) + 2
                        self.attack_hit_done = False
                        self.sprite.update()
                        return
                    elif abs(dx) < 300 and abs(dy) < 200:
                        # Face toward player while patrolling
                        self.direction = 1 if dx > 0 else -1

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
        self.sprite.set_state("walk" if (self.on_ground or self.flying) else "idle")
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
        # Damage flash — red tint when hit
        if self.flash_timer > 0:
            flash_frame = frame.copy()
            flash_frame.fill((255, 80, 80), special_flags=pygame.BLEND_RGBA_MULT)
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
