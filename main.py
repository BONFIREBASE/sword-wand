import pygame
import sys
from src.config import WIDTH, HEIGHT, LOBBY, STORY, GAME, PAUSE, GAME_OVER, VICTORY
from src.lobby import draw_lobby, draw_options_modal
from src.ui import draw_story, draw_pause, draw_game_over, draw_victory
from src.game import update_game, load_game, restart_game, _draw_game_frame, spawn_damage_number, get_all_enemies
from src import state, level

pygame.init()
pygame.mixer.init()

RESOLUTIONS = [(800, 600), (1000, 600), (1280, 720)]

screen = pygame.display.set_mode((1920, 1080), pygame.FULLSCREEN)
pygame.display.set_caption("Sword & Wand")
icon = pygame.image.load("assets/images/game_logo.png")
pygame.display.set_icon(icon)

clock = pygame.time.Clock()

running = True
lobby_buttons = {}
lobby_options_open = False
options_buttons = {}
menu_buttons = {}

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

while running:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

        if event.type == pygame.KEYDOWN:
            if state.state == LOBBY and lobby_options_open:
                if event.key == pygame.K_ESCAPE:
                    lobby_options_open = False

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
                        for enemy in get_all_enemies():
                            if enemy.dying_timer > 0:
                                continue
                            if attack_rect.colliderect(enemy.rect):
                                dying = enemy.take_damage(1)
                                spawn_damage_number(enemy.rect.centerx, enemy.rect.top, 1, (255, 255, 100))

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

            elif state.state == LOBBY:
                for btn_name, btn_rect in lobby_buttons.items():
                    if btn_rect.collidepoint(event.pos):
                        if btn_name == "play":
                            restart_game()
                        elif btn_name == "options":
                            lobby_options_open = True

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
    elif state.state == STORY:
        menu_buttons = draw_story(screen)
    elif state.state == GAME:
        update_game(screen)
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
