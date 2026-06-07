import pygame
import math

_lobby_bg_raw = pygame.image.load("assets/images/374fa55b-d1d2-41d7-9be6-270f2f245367.jpg")
_sekuya_font_path = "assets/font/Sekuya/Sekuya-Regular.ttf"
lobby_buttons = {}


def draw_lobby(screen):
    t = pygame.time.get_ticks() / 1000.0
    WIDTH = screen.get_width()
    HEIGHT = screen.get_height()
    scale = HEIGHT / 600  # reference height

    # Scale to fill width while preserving aspect ratio, then crop/pad to fit height
    bg_w, bg_h = _lobby_bg_raw.get_size()
    scale_w = WIDTH / bg_w
    scale_h = HEIGHT / bg_h
    # Use scale that fills width and shows bottom (floor)
    scale_factor = max(scale_w, scale_h)
    new_w = int(bg_w * scale_factor)
    new_h = int(bg_h * scale_factor)
    lobby_bg = pygame.transform.scale(_lobby_bg_raw, (new_w, new_h))
    # Anchor to bottom center so floor stays visible
    blit_x = (WIDTH - new_w) // 2
    blit_y = HEIGHT - new_h
    screen.blit(lobby_bg, (blit_x, blit_y))

    cx = WIDTH // 2

    # Text elements
    title_font = pygame.font.Font(_sekuya_font_path, int(72 * scale))
    btn_font = pygame.font.Font(_sekuya_font_path, int(44 * scale))
    opt_font = pygame.font.Font(_sekuya_font_path, int(36 * scale))

    title_text = title_font.render("SWORD & WAND", True, (40, 20, 10))
    play_text = btn_font.render("PLAY", True, (40, 20, 10))
    options_text = opt_font.render("Options", True, (40, 20, 10))

    title_h = title_text.get_height()
    play_h = play_text.get_height()
    options_h = options_text.get_height()

    gap_title_play = int(60 * scale)
    gap_play_options = int(40 * scale)

    block_h = title_h + gap_title_play + play_h + gap_play_options + options_h
    start_y = HEIGHT // 2 - block_h // 2

    # Title centered
    title_rect = title_text.get_rect(center=(cx, start_y + title_h // 2))
    screen.blit(title_text, title_rect)

    # PLAY centered below title
    play_center_y = start_y + title_h + gap_title_play + play_h // 2
    play_rect = play_text.get_rect(center=(cx, play_center_y))
    lobby_buttons["play"] = play_rect
    screen.blit(play_text, play_rect)

    # Options centered below PLAY
    options_center_y = play_center_y + play_h // 2 + gap_play_options + options_h // 2
    options_rect = options_text.get_rect(center=(cx, options_center_y))
    lobby_buttons["options"] = options_rect
    screen.blit(options_text, options_rect)

    # Ground strip
    ground_h = int(40 * scale)
    pygame.draw.rect(screen, (60, 40, 20), (0, HEIGHT - ground_h, WIDTH, ground_h))
    tile = int(40 * scale)
    for gx in range(0, WIDTH, tile):
        pygame.draw.rect(screen, (40, 25, 10), (gx, HEIGHT - ground_h, int(38 * scale), ground_h))
        pygame.draw.rect(screen, (30, 60, 20), (gx + int(2 * scale), HEIGHT - ground_h - int(2 * scale), int(34 * scale), int(6 * scale)))

    return lobby_buttons


def draw_options_modal(screen, bgm_vol, fullscreen):
    WIDTH = screen.get_width()
    HEIGHT = screen.get_height()
    cx = WIDTH // 2
    scale = HEIGHT / 600

    # Semi-transparent overlay
    overlay = pygame.Surface((WIDTH, HEIGHT))
    overlay.set_alpha(180)
    overlay.fill((0, 0, 0))
    screen.blit(overlay, (0, 0))

    # Minimalist modal panel — scale with screen
    panel_w = min(int(420 * scale), int(WIDTH * 0.5))
    panel_h = int(380 * scale)
    panel_x = cx - panel_w // 2
    panel_y = max(int(60 * scale), HEIGHT // 2 - panel_h // 2)
    pygame.draw.rect(screen, (25, 22, 35), (panel_x, panel_y, panel_w, panel_h), border_radius=12)
    pygame.draw.rect(screen, (55, 50, 75), (panel_x, panel_y, panel_w, panel_h), 2, border_radius=12)

    title_font = pygame.font.Font(_sekuya_font_path, int(36 * scale))
    body_font = pygame.font.Font(_sekuya_font_path, int(20 * scale))
    small_font = pygame.font.Font(_sekuya_font_path, int(16 * scale))
    btn_font = pygame.font.Font(_sekuya_font_path, int(22 * scale))

    y = panel_y + int(24 * scale)

    # Title
    title = title_font.render("OPTIONS", True, (255, 215, 0))
    screen.blit(title, (cx - title.get_width() // 2, y))
    y += int(55 * scale)

    def draw_slider(label_text, val, y_pos):
        label = body_font.render(label_text, True, (200, 200, 200))
        screen.blit(label, (cx - label.get_width() // 2, y_pos))

        bar_w = int(240 * scale)
        bar_h = max(6, int(8 * scale))
        bar_x = cx - bar_w // 2
        bar_y = y_pos + int(26 * scale)
        pygame.draw.rect(screen, (55, 55, 65), (bar_x, bar_y, bar_w, bar_h), border_radius=4)
        fill_w = int(bar_w * val)
        pygame.draw.rect(screen, (220, 190, 0), (bar_x, bar_y, fill_w, bar_h), border_radius=4)
        knob_x = bar_x + fill_w
        knob_y = bar_y + bar_h // 2
        pygame.draw.circle(screen, (255, 255, 255), (knob_x, knob_y), max(6, int(8 * scale)))

        pct_text = small_font.render(f"{int(val * 100)}%", True, (160, 160, 170))
        screen.blit(pct_text, (cx - pct_text.get_width() // 2, bar_y + int(16 * scale)))

        # Minimal minus
        minus_text = btn_font.render("-", True, (180, 180, 180))
        minus_rect = minus_text.get_rect(center=(bar_x - int(22 * scale), knob_y))
        screen.blit(minus_text, minus_rect)

        # Minimal plus
        plus_text = btn_font.render("+", True, (180, 180, 180))
        plus_rect = plus_text.get_rect(center=(bar_x + bar_w + int(22 * scale), knob_y))
        screen.blit(plus_text, plus_rect)

        pad = int(8 * scale)
        slider_rect = pygame.Rect(bar_x - pad, bar_y - int(12 * scale), bar_w + pad * 2, bar_h + int(24 * scale))
        return minus_rect, plus_rect, slider_rect

    # BGM Volume
    bgm_minus, bgm_plus, bgm_slider = draw_slider("BGM Volume", bgm_vol, y)
    y += int(100 * scale)

    # Fullscreen toggle — centered single row
    fs_label = body_font.render("Fullscreen", True, (200, 200, 200))
    label_x = cx - int(60 * scale)
    screen.blit(fs_label, (label_x - fs_label.get_width() // 2, y + int(2 * scale)))

    fs_color = (80, 200, 100) if fullscreen else (200, 80, 80)
    fs_text = btn_font.render("ON" if fullscreen else "OFF", True, fs_color)
    fs_rect = fs_text.get_rect(center=(cx + int(60 * scale), y + int(12 * scale)))
    screen.blit(fs_text, fs_rect)
    y += int(80 * scale)

    # Bottom buttons — simple text, no boxes
    exit_text = btn_font.render("Exit", True, (200, 90, 90))
    exit_rect = exit_text.get_rect(center=(cx - int(70 * scale), y))
    screen.blit(exit_text, exit_rect)

    close_text = btn_font.render("Close", True, (160, 160, 170))
    close_rect = close_text.get_rect(center=(cx + int(70 * scale), y))
    screen.blit(close_text, close_rect)

    return {
        "bgm_minus": bgm_minus,
        "bgm_plus": bgm_plus,
        "bgm_slider": bgm_slider,
        "fullscreen": fs_rect,
        "exit": exit_rect,
        "close": close_rect,
    }
