import pygame
from src.config import WIDTH, HEIGHT
from src.utils import get_font
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

    blurred = _blur(screen.copy())
    screen.blit(blurred, (0, 0))

    dim = pygame.Surface((W, H))
    dim.set_alpha(100)
    dim.fill((0, 0, 0))
    screen.blit(dim, (0, 0))

    panel_w = min(int(500 * scale), int(W * 0.5))
    btn_count = len(buttons)
    panel_h = int((120 + btn_count * 68) * scale)
    panel_x = cx - panel_w // 2
    panel_y = H // 2 - panel_h // 2
    pygame.draw.rect(screen, (25, 22, 35), (panel_x, panel_y, panel_w, panel_h), border_radius=12)
    pygame.draw.rect(screen, (55, 50, 75), (panel_x, panel_y, panel_w, panel_h), 2, border_radius=12)

    title_font = pygame.font.Font(_FONT_PATH, int(40 * scale))
    title = title_font.render(title_text, True, title_color)
    screen.blit(title, (cx - title.get_width() // 2, panel_y + int(24 * scale)))

    btn_font = pygame.font.Font(_FONT_PATH, int(24 * scale))
    btn_rects = {}
    y = panel_y + int(80 * scale)
    for label, action in buttons:
        text = btn_font.render(label, True, (200, 200, 200))

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
    import math
    scale = screen.get_height() / 600
    font_lg = get_font(_FONT_PATH, int(22 * scale))
    font_sm = get_font(_FONT_PATH, int(14 * scale))
    font_cd = get_font(_FONT_PATH, int(16 * scale))

    pad = int(16 * scale)
    panel_w = int(240 * scale)
    panel_h = int(110 * scale)

    hud_surf = pygame.Surface((panel_w, panel_h), pygame.SRCALPHA)
    pygame.draw.rect(hud_surf, (20, 20, 25, 180), (0, 0, panel_w, panel_h), border_radius=8)
    screen.blit(hud_surf, (pad, pad))

    coin_text = font_lg.render(f"Coins: {state.score}", True, (240, 200, 80))
    screen.blit(coin_text, (pad + panel_w - coin_text.get_width() - 12 * scale, pad + 10 * scale))

    bar_w = panel_w - int(24 * scale)
    bar_h = int(10 * scale)
    bar_x = pad + int(12 * scale)

    lvl_text = font_sm.render(f"Lv {state.player_level}", True, (200, 200, 200))
    screen.blit(lvl_text, (bar_x, pad + 42 * scale))

    hp_text = font_sm.render(f"{state.player_hp}/{state.player_max_hp} HP", True, (255, 255, 255))
    screen.blit(hp_text, (bar_x + bar_w - hp_text.get_width(), pad + 42 * scale))

    hp_y = pad + int(62 * scale)
    pygame.draw.rect(screen, (40, 20, 20), (bar_x, hp_y, bar_w, bar_h), border_radius=4)
    hp_ratio = state.player_hp / state.player_max_hp
    if hp_ratio > 0:
        fill_w = int(bar_w * hp_ratio)
        color = (80, 220, 80) if hp_ratio > 0.5 else ((220, 180, 50) if hp_ratio > 0.25 else (220, 60, 60))
        pygame.draw.rect(screen, color, (bar_x, hp_y, fill_w, bar_h), border_radius=4)

    xp_needed = state.player_level * 100
    xp_text = font_sm.render(f"{state.player_xp}/{xp_needed} XP", True, (150, 200, 255))
    screen.blit(xp_text, (bar_x + bar_w - xp_text.get_width(), hp_y + bar_h + int(4 * scale)))

    xp_y = hp_y + bar_h + int(22 * scale)
    pygame.draw.rect(screen, (20, 30, 40), (bar_x, xp_y, bar_w, bar_h), border_radius=4)
    xp_ratio = state.player_xp / xp_needed
    if xp_ratio > 0:
        fill_w = int(bar_w * xp_ratio)
        pygame.draw.rect(screen, (80, 180, 240), (bar_x, xp_y, fill_w, bar_h), border_radius=4)

    stage_text = font_sm.render(f"STAGE {level.current_level + 1} / {level.MAX_LEVEL}", True, (220, 220, 220))
    stage_w = stage_text.get_width() + int(32 * scale)
    stage_h = stage_text.get_height() + int(16 * scale)
    stage_surf = pygame.Surface((stage_w, stage_h), pygame.SRCALPHA)
    pygame.draw.rect(stage_surf, (20, 20, 25, 180), (0, 0, stage_w, stage_h), border_radius=8)

    stage_x = screen.get_width() - stage_w - pad
    screen.blit(stage_surf, (stage_x, pad))
    screen.blit(stage_text, (stage_x + int(16 * scale), pad + int(8 * scale)))

    player = level.player
    scr_w = screen.get_width()
    scr_h = screen.get_height()
    radius = int(24 * scale)
    spacing = int(58 * scale)
    circle_x = pad + radius + int(6 * scale)

    char_type = getattr(player, "char_type", "GraveRobber")
    atk_cd = 40 if char_type == "Woodcutter" else 30
    q_cd = 120 if char_type == "Woodcutter" else 90
    e_cd = 210 if char_type == "Woodcutter" else 60

    core_skills = [
        (player.attack_cooldown, atk_cd, (255, 255, 100), "slash", 0, "SPC"),
        (player.skill2_cooldown, q_cd, (255, 180, 50), "spin", 4, "Q"),
        (player.skill3_cooldown, e_cd, (255, 80, 80), "dash", 2, "E"),
    ]

    addon_skills = []
    if state.is_equipped("double_dash"):
        addon_skills.append(((100, 255, 255), "double_dash"))
    if state.is_equipped("regen"):
        addon_skills.append(((220, 80, 80), "regen"))
    if state.is_equipped("cd_reduction"):
        addon_skills.append(((100, 200, 255), "cd_reduction"))

    start_y = pad + panel_h + int(50 * scale)

    for i, (cd, cd_max, color, icon_type, req_level, key_label) in enumerate(core_skills):
        if icon_type in ("spin", "dash") and state.is_equipped("cd_reduction"):
            cd_max = max(1, cd_max // 2)

        cx = circle_x
        cy = start_y + i * spacing
        locked = state.player_level < req_level

        bg_color = (25, 25, 35) if not locked else (35, 20, 20)
        pygame.draw.circle(screen, bg_color, (cx, cy), radius)
        border_color = (50, 50, 65) if not locked else (80, 40, 40)
        pygame.draw.circle(screen, border_color, (cx, cy), radius, 2)

        if not locked and cd > 0:
            ratio = cd / cd_max
            angle_end = 2 * math.pi * ratio
            points = [(cx, cy)]
            steps = max(1, int(angle_end / (2 * math.pi) * 60))
            for s in range(steps + 1):
                a = -math.pi / 2 + (s / steps) * angle_end
                px = cx + int(radius * math.cos(a))
                py = cy + int(radius * math.sin(a))
                points.append((px, py))
            if len(points) > 2:
                pygame.draw.polygon(screen, (*color, 120), points)

        icon_s = int(14 * scale)
        if locked:

            lock_y = cy - icon_s // 2
            pygame.draw.rect(screen, (180, 60, 60), (cx - icon_s // 3, lock_y, int(icon_s * 0.7), icon_s), border_radius=2)
            pygame.draw.rect(screen, (180, 60, 60), (cx - icon_s // 2, lock_y + icon_s // 2, icon_s, int(icon_s * 0.6)), border_radius=2)
        elif icon_type == "slash":

            bx, by = cx, cy - icon_s
            tx, ty = cx, cy + icon_s
            pygame.draw.line(screen, (220, 220, 220), (bx, by), (tx, ty), max(2, int(3 * scale)))
            pygame.draw.line(screen, (220, 220, 220), (cx - icon_s // 2, cy - icon_s // 3), (cx + icon_s // 2, cy - icon_s // 3), max(2, int(3 * scale)))
        elif icon_type == "spin":

            for a_off in (0, math.pi):
                pts = []
                for s in range(8):
                    a = a_off + s * math.pi / 7
                    r = icon_s * (s / 7)
                    pts.append((cx + int(r * math.cos(a)), cy + int(r * math.sin(a))))
                if len(pts) >= 2:
                    pygame.draw.lines(screen, (220, 220, 220), False, pts, max(2, int(2 * scale)))
        elif icon_type == "dash":

            ax = cx + icon_s // 2
            pygame.draw.polygon(screen, (220, 220, 220), [
                (ax, cy),
                (ax - icon_s, cy - icon_s),
                (ax - icon_s // 2, cy),
                (ax - icon_s, cy + icon_s),
            ])

        label_surf = font_cd.render(key_label, True, (255, 255, 255) if not locked else (180, 60, 60))
        lx = cx - label_surf.get_width() // 2
        ly = cy - radius - int(20 * scale)

        pill_pad = int(4 * scale)
        pill_rect = pygame.Rect(lx - pill_pad, ly - pill_pad, label_surf.get_width() + pill_pad * 2, label_surf.get_height() + pill_pad * 2)
        pygame.draw.rect(screen, (15, 15, 22, 200), pill_rect, border_radius=int(6 * scale))
        screen.blit(label_surf, (lx, ly))

        if locked:
            cd_text = font_cd.render(f"Lv{req_level}", True, (180, 60, 60))
            screen.blit(cd_text, (cx - cd_text.get_width() // 2, cy - cd_text.get_height() // 2))
        elif cd > 0:
            secs = max(0.1, cd / 30.0)
            cd_text = font_cd.render(f"{secs:.1f}", True, (255, 255, 255))
            screen.blit(cd_text, (cx - cd_text.get_width() // 2, cy - cd_text.get_height() // 2))

    if addon_skills:
        addon_radius = int(20 * scale)
        addon_spacing = int(46 * scale)

        addon_start_x = pad + addon_radius + int(6 * scale)
        addon_start_y = scr_h - pad - addon_radius - int(20 * scale)

        for i, (color, icon_type) in enumerate(addon_skills):
            cx = addon_start_x + i * addon_spacing
            cy = addon_start_y

            addon_surf = pygame.Surface((addon_radius * 2 + 4, addon_radius * 2 + 4), pygame.SRCALPHA)
            local_cx = addon_radius + 2
            local_cy = addon_radius + 2

            pygame.draw.circle(addon_surf, (25, 25, 35, 178), (local_cx, local_cy), addon_radius)
            pygame.draw.circle(addon_surf, (50, 50, 65, 178), (local_cx, local_cy), addon_radius, 2)

            icon_s = int(12 * scale)
            if icon_type == "double_dash":

                ay = local_cy + int(icon_s * 0.8)
                spacing = int(icon_s * 0.6)
                for j in range(2):
                    y_off = ay - j * spacing
                    pygame.draw.lines(addon_surf, (220, 220, 220, 178), False, [
                        (local_cx - icon_s//2, y_off),
                        (local_cx, y_off - icon_s//2),
                        (local_cx + icon_s//2, y_off)
                    ], max(2, int(2 * scale)))

                if player.air_dash_cooldown > 0:
                    ratio = player.air_dash_cooldown / 90.0
                    angle_end = 2 * math.pi * ratio
                    points = [(local_cx, local_cy)]
                    steps = max(1, int(angle_end / (2 * math.pi) * 30))
                    for s in range(steps + 1):
                        a = -math.pi / 2 + (s / steps) * angle_end
                        px = local_cx + int(addon_radius * math.cos(a))
                        py = local_cy + int(addon_radius * math.sin(a))
                        points.append((px, py))
                    if len(points) > 2:
                        pygame.draw.polygon(addon_surf, (100, 255, 255, 120), points)
            elif icon_type == "regen":

                pw = int(4 * scale)
                pl = int(14 * scale)
                pygame.draw.rect(addon_surf, (220, 80, 80, 178), (local_cx - pw//2, local_cy - pl//2, pw, pl))
                pygame.draw.rect(addon_surf, (220, 80, 80, 178), (local_cx - pl//2, local_cy - pw//2, pl, pw))
            elif icon_type == "cd_reduction":

                hw = int(12 * scale)
                hh = int(16 * scale)
                pygame.draw.polygon(addon_surf, (100, 200, 255, 178), [
                    (local_cx - hw//2, local_cy - hh//2),
                    (local_cx + hw//2, local_cy - hh//2),
                    (local_cx, local_cy),
                    (local_cx + hw//2, local_cy + hh//2),
                    (local_cx - hw//2, local_cy + hh//2),
                    (local_cx, local_cy)
                ], max(2, int(2 * scale)))

            screen.blit(addon_surf, (cx - local_cx, cy - local_cy))
