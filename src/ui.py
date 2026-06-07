import pygame
from src.config import WIDTH, HEIGHT
from src import level, state

_FONT_PATH = "assets/font/Sekuya/Sekuya-Regular.ttf"


def _blur(surf, factor=4):
    """Cheap blur by downscaling then upscaling back."""
    w, h = surf.get_size()
    small = pygame.transform.smoothscale(surf, (w // factor, h // factor))
    return pygame.transform.smoothscale(small, (w, h))


def _draw_panel(screen, title_text, buttons, title_color=(255, 215, 0)):
    """Shared modal-style panel with blurred game backdrop and clickable buttons.
    buttons: list of (label, action_name) tuples."""
    W = screen.get_width()
    H = screen.get_height()
    cx = W // 2
    scale = H / 600

    # Blurred game backdrop
    blurred = _blur(screen.copy())
    screen.blit(blurred, (0, 0))

    # Dimming overlay
    dim = pygame.Surface((W, H))
    dim.set_alpha(100)
    dim.fill((0, 0, 0))
    screen.blit(dim, (0, 0))

    # Panel
    panel_w = min(int(500 * scale), int(W * 0.5))
    btn_count = len(buttons)
    panel_h = int((120 + btn_count * 68) * scale)
    panel_x = cx - panel_w // 2
    panel_y = H // 2 - panel_h // 2
    pygame.draw.rect(screen, (25, 22, 35), (panel_x, panel_y, panel_w, panel_h), border_radius=12)
    pygame.draw.rect(screen, (55, 50, 75), (panel_x, panel_y, panel_w, panel_h), 2, border_radius=12)

    # Title
    title_font = pygame.font.Font(_FONT_PATH, int(40 * scale))
    title = title_font.render(title_text, True, title_color)
    screen.blit(title, (cx - title.get_width() // 2, panel_y + int(24 * scale)))

    # Buttons
    btn_font = pygame.font.Font(_FONT_PATH, int(24 * scale))
    btn_rects = {}
    y = panel_y + int(80 * scale)
    for label, action in buttons:
        text = btn_font.render(label, True, (200, 200, 200))
        # Button background
        bw = text.get_width() + int(40 * scale)
        bh = text.get_height() + int(16 * scale)
        bx = cx - bw // 2
        by = y
        btn_rect = pygame.Rect(bx, by, bw, bh)
        pygame.draw.rect(screen, (40, 36, 55), btn_rect, border_radius=8)
        pygame.draw.rect(screen, (70, 65, 95), btn_rect, 1, border_radius=8)
        screen.blit(text, (cx - text.get_width() // 2, by + int(8 * scale)))
        btn_rects[action] = btn_rect
        y += int(68 * scale)

    return btn_rects


def draw_story(screen):
    return _draw_panel(screen,
        "The Legend Begins",
        [
            ("A / D — Move", ""),
            ("W — Jump", ""),
            ("Space — Attack", ""),
            ("Esc — Pause", ""),
            ("BEGIN", "begin"),
        ])


def draw_pause(screen):
    return _draw_panel(screen,
        "PAUSED",
        [
            ("Resume", "resume"),
            ("Restart", "restart"),
            ("Lobby", "lobby"),
        ])


def draw_game_over(screen):
    return _draw_panel(screen,
        "GAME OVER",
        [
            (f"Score: {state.score}", ""),
            (f"Lives: {state.lives}", ""),
            ("Restart", "restart"),
            ("Lobby", "lobby"),
        ],
        title_color=(255, 60, 60))


def draw_victory(screen):
    return _draw_panel(screen,
        "YOU WIN!",
        [
            (f"Final Score: {state.score}", ""),
            ("Lobby", "lobby"),
        ])


def draw_ui(screen):
    scale = screen.get_height() / 600
    font = pygame.font.Font(_FONT_PATH, int(22 * scale))
    hearts = "♥" * state.lives
    heart_text = font.render(hearts, True, (255, 0, 0))
    coin_text = font.render(f"Coins: {state.score}", True, (255, 215, 0))
    level_text = font.render(f"Level: {level.current_level + 1}/{level.MAX_LEVEL}", True, (200, 200, 200))

    screen.blit(heart_text, (int(20 * scale), int(20 * scale)))
    screen.blit(coin_text, (int(20 * scale), int(56 * scale)))
    screen.blit(level_text, (screen.get_width() - int(180 * scale), int(20 * scale)))

    # Health bar
    bar_w = int(200 * scale)
    bar_h = int(16 * scale)
    bar_x = int(20 * scale)
    bar_y = int(90 * scale)
    # Background
    pygame.draw.rect(screen, (40, 10, 10), (bar_x, bar_y, bar_w, bar_h), border_radius=4)
    # Fill
    hp_ratio = state.player_hp / state.player_max_hp
    fill_w = int(bar_w * hp_ratio)
    if fill_w > 0:
        if hp_ratio > 0.5:
            color = (50, 200, 50)
        elif hp_ratio > 0.25:
            color = (220, 180, 30)
        else:
            color = (220, 30, 30)
        pygame.draw.rect(screen, color, (bar_x, bar_y, fill_w, bar_h), border_radius=4)
    # Border
    pygame.draw.rect(screen, (80, 60, 60), (bar_x, bar_y, bar_w, bar_h), 2, border_radius=4)
    # HP text
    hp_text = font.render(f"HP: {state.player_hp}/{state.player_max_hp}", True, (255, 255, 255))
    screen.blit(hp_text, (bar_x, bar_y + bar_h + int(4 * scale)))
