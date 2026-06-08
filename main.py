import pygame
import sys
import random
from src.config import WIDTH, HEIGHT, LOBBY, STORY, GAME, PAUSE, GAME_OVER, VICTORY
from src.lobby import draw_lobby, draw_options_modal, draw_shop_modal, draw_char_select_modal, draw_help_modal, draw_reset_confirm_modal
from src.ui import draw_story, draw_pause, draw_game_over, draw_victory
from src.game import update_game, load_game, restart_game, _draw_game_frame, spawn_damage_number, get_all_enemies, save_game, trigger_screen_shake, get_player_damage, apply_kill_regen
from src import state, level

pygame.init()
pygame.mixer.init()

import src.db as db
db.init_db()
stats = db.load_player_stats()
state.score = stats["coins"]
state.player_xp = stats["xp"]
state.player_level = stats["level"]
state.player_max_hp = stats["max_hp"]
state.player_hp = state.player_max_hp
state.lives = stats["lives"]
state.has_double_dash = stats.get("has_double_dash", False)
state.has_regen = stats.get("has_regen", False)
state.has_cd_reduction = stats.get("has_cd_reduction", False)
state.has_extended_reach = stats.get("has_extended_reach", False)
state.has_executioner = stats.get("has_executioner", False)
state.has_spiked_armor = stats.get("has_spiked_armor", False)
state.equipped_skills = stats.get("equipped_skills", [])

RESOLUTIONS = [(800, 600), (1000, 600), (1280, 720)]

screen = pygame.display.set_mode((1920, 1080), pygame.FULLSCREEN)
screen.fill((0, 0, 0))
pygame.display.flip()
pygame.display.set_caption("Sword & Wand")
icon = pygame.image.load("assets/images/game_logo.png")
pygame.display.set_icon(icon)

clock = pygame.time.Clock()

running = True
lobby_buttons = {}
lobby_options_open = False
lobby_shop_open = False
lobby_char_select_open = False
lobby_reset_confirm_open = False
lobby_help_open = False
options_buttons = {}
shop_buttons = {}
char_select_buttons = {}
reset_confirm_buttons = {}
help_buttons = {}
menu_buttons = {}
shop_warning_timer = 0
shop_warning_msg = ""

bgm_volume = 0.5
fullscreen = True

_current_bgm = None

def _switch_bgm(track):
    global _current_bgm
    if _current_bgm == track:
        return
    _current_bgm = track
    pygame.mixer.music.load(track)
    pygame.mixer.music.set_volume(bgm_volume)
    pygame.mixer.music.play(-1)

_switch_bgm("assets/bgm/lobby.mp3")
_prev_state = LOBBY

combo_sequence = []
last_combo_time = 0

import math

def _run_splash(screen, clock):
    """Blocking splash screen with logo reveal, title, particles, and fade-out."""
    W = screen.get_width()
    H = screen.get_height()

    logo_raw = pygame.image.load("assets/images/game_logo.png").convert_alpha()
    logo_size = min(int(200 * (H / 600)), W // 3)
    logo = pygame.transform.smoothscale(logo_raw, (logo_size, logo_size))
    font_path = "assets/font/Sekuya/Sekuya-Regular.ttf"
    try:
        title_font = pygame.font.Font(font_path, int(56 * (H / 600)))
        sub_font = pygame.font.Font(font_path, int(18 * (H / 600)))
    except Exception:
        title_font = pygame.font.SysFont(None, int(56 * (H / 600)))
        sub_font = pygame.font.SysFont(None, int(18 * (H / 600)))

    title_surf = title_font.render("SWORD & WAND", True, (240, 240, 240))
    sub_surf = sub_font.render("Press any key to continue", True, (120, 120, 120))

    import random
    particles = []
    for _ in range(60):
        particles.append({
            "x": random.uniform(0, W),
            "y": random.uniform(0, H),
            "r": random.uniform(1, 3) * (H / 600),
            "speed": random.uniform(0.3, 1.2),
            "alpha": random.randint(40, 120),
            "drift": random.uniform(-0.3, 0.3),
        })

    LOGO_FADE_IN = 30
    TITLE_FADE_IN = 50
    HOLD_START = 50
    AUTO_ADVANCE = 150
    FADE_OUT_FRAMES = 25

    frame = 0
    fading_out = False
    fade_out_alpha = 0
    splash_done = False

    while not splash_done:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if event.type == pygame.KEYDOWN or event.type == pygame.MOUSEBUTTONDOWN:
                if frame > 20 and not fading_out:
                    fading_out = True
                    fade_out_alpha = 0

        screen.fill((8, 8, 12))

        for p in particles:
            p["y"] -= p["speed"]
            p["x"] += p["drift"]
            if p["y"] < -10:
                p["y"] = H + 10
                p["x"] = random.uniform(0, W)

            breath = int(p["alpha"] + 20 * math.sin(frame * 0.05 + p["x"]))
            breath = max(20, min(180, breath))
            ps = pygame.Surface((int(p["r"] * 2), int(p["r"] * 2)), pygame.SRCALPHA)
            pygame.draw.circle(ps, (200, 180, 255, breath), (int(p["r"]), int(p["r"])), int(p["r"]))
            screen.blit(ps, (int(p["x"] - p["r"]), int(p["y"] - p["r"])))

        cx = W // 2
        cy = H // 2 - int(30 * (H / 600))

        if frame <= LOGO_FADE_IN:
            t = frame / LOGO_FADE_IN

            t_ease = 1 - (1 - t) ** 3
            alpha = int(255 * t_ease)
            scale_f = 0.7 + 0.3 * t_ease
            cur_size = int(logo_size * scale_f)
            logo_scaled = pygame.transform.smoothscale(logo, (cur_size, cur_size))
            logo_scaled.set_alpha(alpha)

            glow_r = int(cur_size * 0.7)
            glow_surf = pygame.Surface((glow_r * 2, glow_r * 2), pygame.SRCALPHA)
            glow_alpha = int(40 * t_ease)
            pygame.draw.circle(glow_surf, (180, 140, 255, glow_alpha), (glow_r, glow_r), glow_r)
            screen.blit(glow_surf, (cx - glow_r, cy - glow_r))
            screen.blit(logo_scaled, (cx - cur_size // 2, cy - cur_size // 2))
        else:

            pulse = 0.5 + 0.5 * math.sin(frame * 0.08)
            glow_r = int(logo_size * 0.7)
            glow_surf = pygame.Surface((glow_r * 2, glow_r * 2), pygame.SRCALPHA)
            glow_alpha = int(25 + 20 * pulse)
            pygame.draw.circle(glow_surf, (180, 140, 255, glow_alpha), (glow_r, glow_r), glow_r)
            screen.blit(glow_surf, (cx - glow_r, cy - glow_r))
            screen.blit(logo, (cx - logo_size // 2, cy - logo_size // 2))

        title_y = cy + logo_size // 2 + int(24 * (H / 600))
        if frame > LOGO_FADE_IN:
            t2 = min(1.0, (frame - LOGO_FADE_IN) / (TITLE_FADE_IN - LOGO_FADE_IN))
            t2_ease = 1 - (1 - t2) ** 2
            alpha2 = int(255 * t2_ease)
            title_copy = title_surf.copy()
            title_copy.set_alpha(alpha2)
            screen.blit(title_copy, (cx - title_surf.get_width() // 2, title_y))

            line_w = int(title_surf.get_width() * t2_ease)
            line_y = title_y + title_surf.get_height() + int(8 * (H / 600))
            line_surf = pygame.Surface((line_w, 2), pygame.SRCALPHA)
            line_surf.fill((180, 140, 255, int(100 * t2_ease)))
            screen.blit(line_surf, (cx - line_w // 2, line_y))

        if frame > TITLE_FADE_IN + 15:
            blink = int(120 + 60 * math.sin(frame * 0.1))
            sub_copy = sub_font.render("Press any key to continue", True, (blink, blink, blink))
            sub_y = title_y + title_surf.get_height() + int(30 * (H / 600))
            screen.blit(sub_copy, (cx - sub_copy.get_width() // 2, sub_y))

        if frame >= AUTO_ADVANCE and not fading_out:
            fading_out = True
            fade_out_alpha = 0

        if fading_out:
            fade_out_alpha = min(255, fade_out_alpha + (255 // FADE_OUT_FRAMES))
            fo_surf = pygame.Surface((W, H))
            fo_surf.fill((0, 0, 0))
            fo_surf.set_alpha(fade_out_alpha)
            screen.blit(fo_surf, (0, 0))
            if fade_out_alpha >= 255:
                splash_done = True

        pygame.display.flip()
        clock.tick(30)
        frame += 1

    for _ in range(6):
        screen.fill((0, 0, 0))
        pygame.display.flip()
        clock.tick(30)

_run_splash(screen, clock)

_lobby_fade_alpha = 255
_lobby_fade_speed = 10

_game_fade_alpha = 0
_game_fade_speed = 15

def _run_level_transition(screen, clock, char_name):
    """Premium transition from character select to gameplay."""
    W = screen.get_width()
    H = screen.get_height()
    font_path = "assets/font/Sekuya/Sekuya-Regular.ttf"
    try:
        title_font = pygame.font.Font(font_path, int(64 * (H / 600)))
        sub_font = pygame.font.Font(font_path, int(24 * (H / 600)))
    except:
        title_font = pygame.font.SysFont(None, int(64 * (H / 600)))
        sub_font = pygame.font.SysFont(None, int(24 * (H / 600)))

    bg_copy = screen.copy()

    for i in range(1, 21):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit(); sys.exit()

        screen.blit(bg_copy, (0, 0))

        w_cur = int((i / 20) * W)
        pygame.draw.rect(screen, (8, 8, 12), (0, 0, w_cur, H))
        pygame.display.flip()
        clock.tick(60)

    title_surf = title_font.render(char_name.upper(), True, (240, 240, 240))
    sub_surf = sub_font.render("ENTERING THE DUNGEON...", True, (200, 50, 50))
    cx, cy = W // 2, H // 2

    for i in range(90):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit(); sys.exit()

        screen.fill((8, 8, 12))

        progress = i / 90.0
        alpha = int(255 * math.sin(progress * math.pi))

        t_copy = title_surf.copy()
        t_copy.set_alpha(alpha)
        s_copy = sub_surf.copy()
        s_copy.set_alpha(alpha)

        line_w = int(400 * (H/600) * math.sin(progress * math.pi))
        line_surf = pygame.Surface((line_w, 2), pygame.SRCALPHA)
        line_surf.fill((100, 100, 100, alpha))

        screen.blit(line_surf, (cx - line_w//2, cy - int(40*(H/600))))
        screen.blit(t_copy, (cx - title_surf.get_width()//2, cy - title_surf.get_height()//2))
        screen.blit(line_surf, (cx - line_w//2, cy + int(40*(H/600))))

        screen.blit(s_copy, (cx - sub_surf.get_width()//2, cy + int(60*(H/600))))

        pygame.display.flip()
        clock.tick(30)

    global _game_fade_alpha
    _game_fade_alpha = 255

while running:
    if shop_warning_timer > 0:
        shop_warning_timer -= 1
        if shop_warning_timer == 0:
            shop_warning_msg = ""

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

        if event.type == pygame.KEYDOWN:
            if state.state == LOBBY and lobby_reset_confirm_open:
                if event.key == pygame.K_ESCAPE:
                    lobby_reset_confirm_open = False
            elif state.state == LOBBY and lobby_options_open:
                if event.key == pygame.K_ESCAPE:
                    lobby_options_open = False
            elif state.state == LOBBY and lobby_shop_open:
                if event.key == pygame.K_ESCAPE:
                    lobby_shop_open = False
            elif state.state == LOBBY and lobby_char_select_open:
                if event.key == pygame.K_ESCAPE:
                    lobby_char_select_open = False
            elif state.state == LOBBY and lobby_help_open:
                if event.key == pygame.K_ESCAPE:
                    lobby_help_open = False

            elif state.state == LOBBY:
                if event.key == pygame.K_ESCAPE:
                    running = False
                elif event.key == pygame.K_RETURN:
                    state.state = STORY
                elif event.key == pygame.K_l:
                    if load_game():
                        pass

            elif state.state == STORY:
                if event.key == pygame.K_RETURN:
                    restart_game()
                elif event.key == pygame.K_ESCAPE:
                    state.state = LOBBY

            elif state.state == GAME:
                if event.key == pygame.K_ESCAPE:
                    state.state = PAUSE
                elif event.key in (pygame.K_w, pygame.K_UP):
                    current_time = pygame.time.get_ticks()
                    if current_time - last_combo_time > 2000:
                        combo_sequence = []
                    combo_sequence.append('W')
                    last_combo_time = current_time
                elif event.key == pygame.K_SPACE:
                    attack_rect = level.player.attack()
                    if attack_rect:
                        current_time = pygame.time.get_ticks()
                        if current_time - last_combo_time > 2000:
                            combo_sequence = []
                        combo_sequence.append('SPACE')
                        last_combo_time = current_time

                        is_combo = False
                        if state.selected_character == "Woodcutter":
                            if combo_sequence[-4:] == ['W', 'E', 'Q', 'SPACE']:
                                is_combo = True
                                combo_sequence.clear()
                        else:
                            if combo_sequence[-4:] == ['SPACE', 'E', 'Q', 'SPACE']:
                                is_combo = True
                                combo_sequence.clear()

                        dmg = get_player_damage(1)
                        if is_combo:
                            dmg *= 5
                            trigger_screen_shake(15)
                            spawn_damage_number(level.player.rect.centerx, level.player.rect.top - 40, "COMBO!", (255, 50, 255))

                        kills = 0
                        one_hit_kills = 0
                        for enemy in get_all_enemies():
                            if enemy.dying_timer > 0:
                                continue
                            if attack_rect.colliderect(enemy.rect):
                                was_one_hit = enemy.hp <= dmg
                                dying = enemy.take_damage(dmg)
                                spawn_damage_number(enemy.rect.centerx, enemy.rect.top, dmg, (255, 255, 100))
                                if dying:
                                    kills += 1
                                    if was_one_hit:
                                        one_hit_kills += 1
                                    xp_gain = enemy.xp_value * 3 if is_combo else enemy.xp_value
                                    state.player_xp += xp_gain
                                    xp_needed = state.player_level * 100
                                    if state.player_xp >= xp_needed:
                                        state.player_xp -= xp_needed
                                        state.player_level += 1
                                        state.player_max_hp += 10
                                        state.player_hp = state.player_max_hp
                                        spawn_damage_number(level.player.rect.centerx, level.player.rect.top - 20, "LEVEL UP!", (100, 255, 100))
                                    save_game()
                        apply_kill_regen(kills, one_hit_kills)
                        if is_combo:
                            level.player.hp = min(level.player.max_hp, level.player.hp + 50)
                            state.player_hp = level.player.hp
                            spawn_damage_number(level.player.rect.centerx, level.player.rect.top - 25, "+50 HP", (60, 220, 100))
                elif event.key == pygame.K_q and state.player_level >= 4:
                    attack_rect = level.player.skill2()
                    if attack_rect:
                        current_time = pygame.time.get_ticks()
                        if current_time - last_combo_time > 2000:
                            combo_sequence = []
                        combo_sequence.append('Q')
                        last_combo_time = current_time

                        trigger_screen_shake(18)
                        spawn_damage_number(level.player.rect.centerx, level.player.rect.top - 50, "UNLEASHED!", (180, 80, 255))
                        dmg = get_player_damage(8)
                        kills = 0
                        one_hit_kills = 0
                        for enemy in get_all_enemies():
                            if enemy.dying_timer > 0:
                                continue
                            if attack_rect.colliderect(enemy.rect):
                                was_one_hit = enemy.hp <= dmg
                                dying = enemy.take_damage(dmg)
                                spawn_damage_number(enemy.rect.centerx, enemy.rect.top, dmg, (220, 100, 255))
                                if dying:
                                    kills += 1
                                    if was_one_hit:
                                        one_hit_kills += 1
                                    state.player_xp += enemy.xp_value
                                    xp_needed = state.player_level * 100
                                    if state.player_xp >= xp_needed:
                                        state.player_xp -= xp_needed
                                        state.player_level += 1
                                        state.player_max_hp += 10
                                        state.player_hp = state.player_max_hp
                                        spawn_damage_number(level.player.rect.centerx, level.player.rect.top - 20, "LEVEL UP!", (100, 255, 100))
                                    save_game()
                        apply_kill_regen(kills, one_hit_kills)
                elif event.key == pygame.K_e and state.player_level >= 2:
                    attack_rect = level.player.skill3()
                    if attack_rect:
                        current_time = pygame.time.get_ticks()
                        if current_time - last_combo_time > 2000:
                            combo_sequence = []
                        combo_sequence.append('E')
                        last_combo_time = current_time

                        dmg = get_player_damage(3)
                        kills = 0
                        one_hit_kills = 0
                        for enemy in get_all_enemies():
                            if enemy.dying_timer > 0:
                                continue
                            if attack_rect.colliderect(enemy.rect):
                                was_one_hit = enemy.hp <= dmg
                                dying = enemy.take_damage(dmg)
                                spawn_damage_number(enemy.rect.centerx, enemy.rect.top, dmg, (255, 80, 80))
                                if dying:
                                    kills += 1
                                    if was_one_hit:
                                        one_hit_kills += 1
                                    state.player_xp += enemy.xp_value
                                    xp_needed = state.player_level * 100
                                    if state.player_xp >= xp_needed:
                                        state.player_xp -= xp_needed
                                        state.player_level += 1
                                        state.player_max_hp += 10
                                        state.player_hp = state.player_max_hp
                                        spawn_damage_number(level.player.rect.centerx, level.player.rect.top - 20, "LEVEL UP!", (100, 255, 100))
                                    save_game()
                        apply_kill_regen(kills, one_hit_kills)

            elif state.state == PAUSE:
                if event.key == pygame.K_ESCAPE:
                    state.state = GAME
                elif event.key == pygame.K_r:
                    restart_game()
                elif event.key == pygame.K_m:
                    state.state = LOBBY

            elif state.state == GAME_OVER:
                if event.key == pygame.K_y:
                    restart_game()
                elif event.key == pygame.K_n:
                    state.state = LOBBY

            elif state.state == VICTORY:
                if event.key == pygame.K_RETURN:
                    state.state = LOBBY

        if event.type == pygame.MOUSEBUTTONDOWN:
            if state.state == LOBBY and lobby_reset_confirm_open:
                for btn_name, btn_rect in reset_confirm_buttons.items():
                    if btn_rect.collidepoint(event.pos):
                        if btn_name == "yes":
                            import src.db as db
                            db.reset_player_stats()
                            stats = db.load_player_stats()
                            state.score = stats["coins"]
                            state.player_xp = stats["xp"]
                            state.player_level = stats["level"]
                            state.player_max_hp = stats["max_hp"]
                            state.player_hp = state.player_max_hp
                            state.lives = stats["lives"]
                            state.has_double_dash = False
                            state.has_regen = False
                            state.has_cd_reduction = False
                            state.has_extended_reach = False
                            state.has_executioner = False
                            state.has_spiked_armor = False
                            state.equipped_skills = []
                            lobby_reset_confirm_open = False
                        elif btn_name == "no":
                            lobby_reset_confirm_open = False

            elif state.state == LOBBY and lobby_options_open:
                for btn_name, btn_rect in options_buttons.items():
                    if btn_rect.collidepoint(event.pos):
                        if btn_name == "close":
                            lobby_options_open = False
                        elif btn_name == "reset":
                            lobby_reset_confirm_open = True

                        elif btn_name == "bgm_minus":
                            bgm_volume = max(0.0, bgm_volume - 0.1)
                            pygame.mixer.music.set_volume(bgm_volume)
                        elif btn_name == "bgm_plus":
                            bgm_volume = min(1.0, bgm_volume + 0.1)
                            pygame.mixer.music.set_volume(bgm_volume)
                        elif btn_name == "bgm_slider":
                            bar_x = screen.get_width() // 2 - 120
                            bar_w = 240
                            rel_x = event.pos[0] - bar_x
                            bgm_volume = max(0.0, min(1.0, rel_x / bar_w))
                            pygame.mixer.music.set_volume(bgm_volume)

                        elif btn_name == "fullscreen":
                            fullscreen = not fullscreen
                            if fullscreen:
                                screen = pygame.display.set_mode((1920, 1080), pygame.FULLSCREEN)
                            else:
                                screen = pygame.display.set_mode((WIDTH, HEIGHT))

                        elif btn_name == "exit":
                            running = False

            elif state.state == LOBBY and lobby_shop_open:
                for btn_name, btn_rect in shop_buttons.items():
                    if btn_rect and btn_rect.collidepoint(event.pos):
                        if btn_name == "close":
                            lobby_shop_open = False
                        elif btn_name.startswith("buy_"):
                            skill_key = btn_name.replace("buy_", "")

                            owned = False
                            if skill_key == "double_dash" and state.has_double_dash: owned = True
                            elif skill_key == "regen" and state.has_regen: owned = True
                            elif skill_key == "cd_reduction" and state.has_cd_reduction: owned = True
                            elif skill_key == "reach" and state.has_extended_reach: owned = True
                            elif skill_key == "executioner" and state.has_executioner: owned = True
                            elif skill_key == "spiked_armor" and state.has_spiked_armor: owned = True

                            if owned:
                                if skill_key in state.equipped_skills:
                                    state.equipped_skills.remove(skill_key)
                                    save_game()
                                else:
                                    if len(state.equipped_skills) < 2:
                                        state.equipped_skills.append(skill_key)
                                        save_game()
                                    else:
                                        shop_warning_msg = "Max 2 skills equipped!"
                                        shop_warning_timer = 60
                            else:
                                price = 0
                                if skill_key == "double_dash": price = 50
                                elif skill_key == "regen": price = 25
                                elif skill_key == "cd_reduction": price = 100
                                elif skill_key == "reach": price = 50
                                elif skill_key == "executioner": price = 150
                                elif skill_key == "spiked_armor": price = 100

                                if state.score >= price:
                                    state.score -= price
                                    if skill_key == "double_dash": state.has_double_dash = True
                                    elif skill_key == "regen": state.has_regen = True
                                    elif skill_key == "cd_reduction": state.has_cd_reduction = True
                                    elif skill_key == "reach": state.has_extended_reach = True
                                    elif skill_key == "executioner": state.has_executioner = True
                                    elif skill_key == "spiked_armor": state.has_spiked_armor = True
                                    save_game()
                                else:
                                    shop_warning_msg = "Not enough coins!"
                                    shop_warning_timer = 60

            elif state.state == LOBBY and lobby_char_select_open:
                for btn_name, btn_rect in char_select_buttons.items():
                    if btn_rect and btn_rect.collidepoint(event.pos):
                        if btn_name == "close":
                            lobby_char_select_open = False
                        elif btn_name in ("GraveRobber", "Woodcutter"):
                            state.selected_character = btn_name
                            lobby_char_select_open = False
                            _run_level_transition(screen, clock, btn_name)
                            restart_game()

            elif state.state == LOBBY and lobby_help_open:
                for btn_name, btn_rect in help_buttons.items():
                    if btn_rect and btn_rect.collidepoint(event.pos):
                        if btn_name == "close":
                            lobby_help_open = False

            elif state.state == LOBBY:
                for btn_name, btn_rect in lobby_buttons.items():
                    if btn_rect.collidepoint(event.pos):
                        if btn_name == "play":
                            lobby_char_select_open = True
                        elif btn_name == "options":
                            lobby_options_open = True
                        elif btn_name == "shop":
                            lobby_shop_open = True
                        elif btn_name == "help":
                            lobby_help_open = True

            elif state.state in (STORY, PAUSE, GAME_OVER, VICTORY):
                for action, btn_rect in menu_buttons.items():
                    if btn_rect.collidepoint(event.pos):
                        if action == "begin":
                            restart_game()
                        elif action == "resume":
                            state.state = GAME
                        elif action == "restart":
                            restart_game()
                        elif action == "lobby":
                            state.state = LOBBY

    if state.state == LOBBY:
        lobby_buttons = draw_lobby(screen)
        if lobby_options_open:
            options_buttons = draw_options_modal(screen, bgm_volume, fullscreen)
            if lobby_reset_confirm_open:
                reset_confirm_buttons = draw_reset_confirm_modal(screen)
        elif lobby_shop_open:
            shop_buttons = draw_shop_modal(screen, state, shop_warning_msg if shop_warning_timer > 0 else "")
        elif lobby_char_select_open:
            char_select_buttons = draw_char_select_modal(screen)
        elif lobby_help_open:
            help_buttons = draw_help_modal(screen)
    elif state.state == STORY:
        menu_buttons = draw_story(screen)
    elif state.state == GAME:
        update_game(screen)

        if getattr(level.player, "pending_attack_rect", None):
            attack_rect = level.player.pending_attack_rect
            damage_type = getattr(level.player, "pending_attack_damage_type", 3)
            level.player.pending_attack_rect = None
            if damage_type == 4 and level.player.char_type == "GraveRobber":
                dmg = get_player_damage(8)
            else:
                dmg = get_player_damage(damage_type)
            kills = 0
            one_hit_kills = 0
            for enemy in get_all_enemies():
                if enemy.dying_timer > 0:
                    continue
                if attack_rect.colliderect(enemy.rect):

                    is_crit = False
                    final_dmg = dmg
                    if state.is_equipped("executioner") and random.random() < 0.20:
                        final_dmg *= 2
                        is_crit = True

                    was_one_hit = enemy.hp <= final_dmg
                    dying = enemy.take_damage(final_dmg)
                    color = (255, 200, 50) if is_crit else (255, 80, 80)
                    text_str = f"CRIT {final_dmg}!" if is_crit else str(final_dmg)
                    spawn_damage_number(enemy.rect.centerx, enemy.rect.top, text_str, color)
                    if dying:
                        kills += 1
                        if was_one_hit:
                            one_hit_kills += 1
                        state.player_xp += enemy.xp_value
                        xp_needed = state.player_level * 100
                        if state.player_xp >= xp_needed:
                            state.player_xp -= xp_needed
                            state.player_level += 1
                            state.player_max_hp += 10
                            state.player_hp = state.player_max_hp
                            spawn_damage_number(level.player.rect.centerx, level.player.rect.top - 20, "LEVEL UP!", (100, 255, 100))
                        save_game()
            apply_kill_regen(kills, one_hit_kills)
    elif state.state == PAUSE:
        camera_x = level.player.rect.centerx - screen.get_width() // 2
        _draw_game_frame(screen, camera_x)
        menu_buttons = draw_pause(screen)
    elif state.state == GAME_OVER:
        camera_x = level.player.rect.centerx - screen.get_width() // 2
        _draw_game_frame(screen, camera_x)
        menu_buttons = draw_game_over(screen)
    elif state.state == VICTORY:
        camera_x = level.player.rect.centerx - screen.get_width() // 2
        _draw_game_frame(screen, camera_x)
        menu_buttons = draw_victory(screen)

    if state.state != _prev_state:
        if state.state == GAME:
            _switch_bgm("assets/bgm/gameplay.mp3")
        elif state.state == LOBBY:
            _switch_bgm("assets/bgm/lobby.mp3")
        _prev_state = state.state

    if _lobby_fade_alpha > 0 and state.state == LOBBY:
        fade_surf = pygame.Surface((screen.get_width(), screen.get_height()))
        fade_surf.fill((0, 0, 0))
        fade_surf.set_alpha(_lobby_fade_alpha)
        screen.blit(fade_surf, (0, 0))
        _lobby_fade_alpha = max(0, _lobby_fade_alpha - _lobby_fade_speed)

    if _game_fade_alpha > 0 and state.state == GAME:
        fade_surf = pygame.Surface((screen.get_width(), screen.get_height()))
        fade_surf.fill((8, 8, 12))
        fade_surf.set_alpha(_game_fade_alpha)
        screen.blit(fade_surf, (0, 0))
        _game_fade_alpha = max(0, _game_fade_alpha - _game_fade_speed)

    pygame.display.flip()
    clock.tick(30)

pygame.quit()
sys.exit()
