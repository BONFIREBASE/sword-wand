import pygame
import sys
import random
from src.config import WIDTH, HEIGHT, LOBBY, STORY, GAME, PAUSE, GAME_OVER, VICTORY
from src.lobby import draw_lobby, draw_options_modal, draw_shop_modal, draw_char_select_modal
from src.ui import draw_story, draw_pause, draw_game_over, draw_victory
from src.game import update_game, load_game, restart_game, _draw_game_frame, spawn_damage_number, get_all_enemies, save_game, trigger_screen_shake, get_player_damage, apply_kill_regen
from src import state, level

pygame.init()
pygame.mixer.init()

# Load initial stats so Lobby shop reflects accurate data before playing
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

RESOLUTIONS = [(800, 600), (1000, 600), (1280, 720)]

screen = pygame.display.set_mode((1920, 1080), pygame.FULLSCREEN)
pygame.display.set_caption("Sword & Wand")
icon = pygame.image.load("assets/images/game_logo.png")
pygame.display.set_icon(icon)

clock = pygame.time.Clock()

running = True
lobby_buttons = {}
lobby_options_open = False
lobby_shop_open = False
lobby_char_select_open = False
options_buttons = {}
shop_buttons = {}
char_select_buttons = {}
menu_buttons = {}
shop_warning_timer = 0

# Settings
bgm_volume = 0.5
fullscreen = True

# BGM
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

while running:
    if shop_warning_timer > 0:
        shop_warning_timer -= 1

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

        if event.type == pygame.KEYDOWN:
            if state.state == LOBBY and lobby_options_open:
                if event.key == pygame.K_ESCAPE:
                    lobby_options_open = False
            elif state.state == LOBBY and lobby_shop_open:
                if event.key == pygame.K_ESCAPE:
                    lobby_shop_open = False
            elif state.state == LOBBY and lobby_char_select_open:
                if event.key == pygame.K_ESCAPE:
                    lobby_char_select_open = False

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
                elif event.key == pygame.K_SPACE:
                    attack_rect = level.player.attack()
                    if attack_rect:
                        current_time = pygame.time.get_ticks()
                        if current_time - last_combo_time > 2000:
                            combo_sequence = []
                        combo_sequence.append('SPACE')
                        last_combo_time = current_time
                        
                        is_combo = False
                        if combo_sequence[-4:] == ['SPACE', 'E', 'Q', 'SPACE']:
                            is_combo = True
                            combo_sequence.clear()
                            
                        dmg = get_player_damage(1)
                        if is_combo:
                            dmg *= 5
                            trigger_screen_shake(15)
                            spawn_damage_number(level.player.rect.centerx, level.player.rect.top - 40, "COMBO!", (255, 50, 255))
                            level.player.skill2_cooldown = 0
                            level.player.skill3_cooldown = 0

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

                        trigger_screen_shake(8)
                        dmg = get_player_damage(4)
                        kills = 0
                        one_hit_kills = 0
                        for enemy in get_all_enemies():
                            if enemy.dying_timer > 0:
                                continue
                            if attack_rect.colliderect(enemy.rect):
                                was_one_hit = enemy.hp <= dmg
                                dying = enemy.take_damage(dmg)
                                spawn_damage_number(enemy.rect.centerx, enemy.rect.top, dmg, (255, 180, 50))
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
            if state.state == LOBBY and lobby_options_open:
                for btn_name, btn_rect in options_buttons.items():
                    if btn_rect.collidepoint(event.pos):
                        if btn_name == "close":
                            lobby_options_open = False

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
                        elif btn_name == "buy_double_dash":
                            if not state.has_double_dash:
                                if state.score >= 50:
                                    state.score -= 50
                                    state.has_double_dash = True
                                    save_game()
                                else:
                                    shop_warning_timer = 60
                        elif btn_name == "buy_regen":
                            if not state.has_regen:
                                if state.score >= 25:
                                    state.score -= 25
                                    state.has_regen = True
                                    save_game()
                                else:
                                    shop_warning_timer = 60
                        elif btn_name == "buy_cd_reduction":
                            if not state.has_cd_reduction:
                                if state.score >= 100:
                                    state.score -= 100
                                    state.has_cd_reduction = True
                                    save_game()
                                else:
                                    shop_warning_timer = 60
                        elif btn_name == "buy_reach":
                            if not state.has_extended_reach:
                                if state.score >= 50:
                                    state.score -= 50
                                    state.has_extended_reach = True
                                    save_game()
                                else:
                                    shop_warning_timer = 60
                        elif btn_name == "buy_executioner":
                            if not state.has_executioner:
                                if state.score >= 150:
                                    state.score -= 150
                                    state.has_executioner = True
                                    save_game()
                                else:
                                    shop_warning_timer = 60
                        elif btn_name == "buy_spiked_armor":
                            if not state.has_spiked_armor:
                                if state.score >= 100:
                                    state.score -= 100
                                    state.has_spiked_armor = True
                                    save_game()
                                else:
                                    shop_warning_timer = 60

            elif state.state == LOBBY and lobby_char_select_open:
                for btn_name, btn_rect in char_select_buttons.items():
                    if btn_rect and btn_rect.collidepoint(event.pos):
                        if btn_name == "close":
                            lobby_char_select_open = False
                        elif btn_name in ("GraveRobber", "Woodcutter"):
                            state.selected_character = btn_name
                            lobby_char_select_open = False
                            restart_game()

            elif state.state == LOBBY:
                for btn_name, btn_rect in lobby_buttons.items():
                    if btn_rect.collidepoint(event.pos):
                        if btn_name == "play":
                            lobby_char_select_open = True
                        elif btn_name == "options":
                            lobby_options_open = True
                        elif btn_name == "shop":
                            lobby_shop_open = True

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
        elif lobby_shop_open:
            shop_buttons = draw_shop_modal(screen, state, shop_warning_timer > 0)
        elif lobby_char_select_open:
            char_select_buttons = draw_char_select_modal(screen)
    elif state.state == STORY:
        menu_buttons = draw_story(screen)
    elif state.state == GAME:
        update_game(screen)
        
        # Process delayed attacks (Woodcutter E and Q)
        if getattr(level.player, "pending_attack_rect", None):
            attack_rect = level.player.pending_attack_rect
            damage_type = getattr(level.player, "pending_attack_damage_type", 3)
            level.player.pending_attack_rect = None
            dmg = get_player_damage(damage_type)
            kills = 0
            one_hit_kills = 0
            for enemy in get_all_enemies():
                if enemy.dying_timer > 0:
                    continue
                if attack_rect.colliderect(enemy.rect):
                    # Executioner's Blow
                    is_crit = False
                    final_dmg = dmg
                    if getattr(state, "has_executioner", False) and random.random() < 0.20:
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

    # BGM switching on state change
    if state.state != _prev_state:
        if state.state == GAME:
            _switch_bgm("assets/bgm/gameplay.mp3")
        elif state.state == LOBBY:
            _switch_bgm("assets/bgm/lobby.mp3")
        _prev_state = state.state

    pygame.display.flip()
    clock.tick(30)

pygame.quit()
sys.exit()
