import pygame
import math
import os
from src.sprites import SpriteSheet

from src.utils import get_font
_lobby_bg_raw = pygame.image.load("assets/images/374fa55b-d1d2-41d7-9be6-270f2f245367.jpg")
_cached_lobby_bg = None
_cached_lobby_size = None
_bg_images = []
_bg_loaded = False
_sekuya_font_path = "assets/font/Sekuya/Sekuya-Regular.ttf"
_gr_idle_anim = None
_wc_idle_anim = None

def _get_char_img(char_type):
    global _gr_idle_anim, _wc_idle_anim
    current_time = pygame.time.get_ticks()

    if char_type == "GraveRobber":
        if _gr_idle_anim is None:
            path = os.path.join("assets", "characters", "2 GraveRobber", "GraveRobber_idle.png")
            if os.path.exists(path):

                sheet = SpriteSheet(path, 48, 48, 4)
                _gr_idle_anim = sheet.frames
        if _gr_idle_anim:

            frame_idx = ((current_time + 300) // 125) % len(_gr_idle_anim)
            return _gr_idle_anim[frame_idx]

    elif char_type == "Woodcutter":
        if _wc_idle_anim is None:
            path = os.path.join("assets", "characters", "1 Woodcutter", "Woodcutter_idle.png")
            if os.path.exists(path):

                sheet = SpriteSheet(path, 48, 48, 4)
                _wc_idle_anim = sheet.frames
        if _wc_idle_anim:
            frame_idx = (current_time // 125) % len(_wc_idle_anim)
            return _wc_idle_anim[frame_idx]

    return None

lobby_buttons = {}

def draw_lobby(screen):
    t = pygame.time.get_ticks() / 1000.0
    WIDTH = screen.get_width()
    HEIGHT = screen.get_height()
    scale = HEIGHT / 600

    bg_w, bg_h = _lobby_bg_raw.get_size()
    scale_w = WIDTH / bg_w
    scale_h = HEIGHT / bg_h

    scale_factor = max(scale_w, scale_h)
    new_w = int(bg_w * scale_factor)
    new_h = int(bg_h * scale_factor)

    global _cached_lobby_bg, _cached_lobby_size
    if _cached_lobby_size != (new_w, new_h):
        _cached_lobby_bg = pygame.transform.scale(_lobby_bg_raw, (new_w, new_h)).convert()
        _cached_lobby_size = (new_w, new_h)

    blit_x = (WIDTH - new_w) // 2
    blit_y = HEIGHT - new_h
    screen.blit(_cached_lobby_bg, (blit_x, blit_y))

    cx = WIDTH // 2

    title_font = get_font(_sekuya_font_path, int(72 * scale))
    btn_font = get_font(_sekuya_font_path, int(44 * scale))

    title_text = title_font.render("SWORD & WAND", True, (40, 20, 10))
    title_h = title_text.get_height()

    gap_title_play = int(60 * scale)
    btn_spacing = int(25 * scale)

    start_y = HEIGHT // 2 - (title_h + gap_title_play + 3 * int(44 * scale) + 2 * btn_spacing) // 2

    title_rect = title_text.get_rect(center=(cx, start_y + title_h // 2))
    screen.blit(title_text, title_rect)

    def draw_menu_btn(text, center_y, name):
        mouse_pos = pygame.mouse.get_pos()

        base_surf = btn_font.render(text, True, (40, 20, 10))
        btn_rect = base_surf.get_rect(center=(cx, center_y))

        is_hover = btn_rect.collidepoint(mouse_pos)

        if is_hover:
            hover_font = get_font(_sekuya_font_path, int(50 * scale))
            text_surf = hover_font.render(text, True, (80, 40, 20))
        else:
            text_surf = btn_font.render(text, True, (40, 20, 10))

        screen.blit(text_surf, text_surf.get_rect(center=btn_rect.center))

        lobby_buttons[name] = btn_rect
        return btn_rect.bottom + btn_spacing

    next_y = title_rect.bottom + gap_title_play
    next_y = draw_menu_btn("PLAY", next_y + int(22 * scale), "play")
    next_y = draw_menu_btn("SHOP", next_y + int(22 * scale), "shop")
    next_y = draw_menu_btn("OPTIONS", next_y + int(22 * scale), "options")
    next_y = draw_menu_btn("HELP", next_y + int(22 * scale), "help")

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

    overlay = pygame.Surface((WIDTH, HEIGHT))
    overlay.set_alpha(180)
    overlay.fill((0, 0, 0))
    screen.blit(overlay, (0, 0))

    panel_w = min(int(420 * scale), int(WIDTH * 0.5))
    panel_h = int(380 * scale)
    panel_x = cx - panel_w // 2
    panel_y = max(int(60 * scale), HEIGHT // 2 - panel_h // 2)
    pygame.draw.rect(screen, (25, 22, 35), (panel_x, panel_y, panel_w, panel_h), border_radius=12)
    pygame.draw.rect(screen, (55, 50, 75), (panel_x, panel_y, panel_w, panel_h), 2, border_radius=12)

    title_font = get_font(_sekuya_font_path, int(36 * scale))
    body_font = get_font(_sekuya_font_path, int(20 * scale))
    small_font = get_font(_sekuya_font_path, int(16 * scale))
    btn_font = get_font(_sekuya_font_path, int(22 * scale))

    y = panel_y + int(24 * scale)

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

        minus_text = btn_font.render("-", True, (180, 180, 180))
        minus_rect = minus_text.get_rect(center=(bar_x - int(22 * scale), knob_y))
        screen.blit(minus_text, minus_rect)

        plus_text = btn_font.render("+", True, (180, 180, 180))
        plus_rect = plus_text.get_rect(center=(bar_x + bar_w + int(22 * scale), knob_y))
        screen.blit(plus_text, plus_rect)

        pad = int(8 * scale)
        slider_rect = pygame.Rect(bar_x - pad, bar_y - int(12 * scale), bar_w + pad * 2, bar_h + int(24 * scale))
        return minus_rect, plus_rect, slider_rect

    bgm_minus, bgm_plus, bgm_slider = draw_slider("BGM Volume", bgm_vol, y)
    y += int(100 * scale)

    fs_label = body_font.render("Fullscreen", True, (200, 200, 200))
    label_x = cx - int(60 * scale)
    screen.blit(fs_label, (label_x - fs_label.get_width() // 2, y + int(2 * scale)))

    fs_color = (80, 200, 100) if fullscreen else (200, 80, 80)
    fs_text = btn_font.render("ON" if fullscreen else "OFF", True, fs_color)
    fs_rect = fs_text.get_rect(center=(cx + int(60 * scale), y + int(12 * scale)))
    screen.blit(fs_text, fs_rect)
    y += int(110 * scale)

    mouse_pos = pygame.mouse.get_pos()

    exit_base_surf = btn_font.render("Exit", True, (200, 90, 90))
    exit_rect = exit_base_surf.get_rect(center=(cx - int(80 * scale), y))
    if exit_rect.collidepoint(mouse_pos):
        hover_font = get_font(_sekuya_font_path, int(26 * scale))
        exit_surf = hover_font.render("Exit", True, (250, 120, 120))
    else:
        exit_surf = exit_base_surf
    exit_rect = exit_surf.get_rect(center=(cx - int(80 * scale), y))
    screen.blit(exit_surf, exit_rect)

    # Reset Button
    reset_base_surf = btn_font.render("Reset Data", True, (220, 80, 80))
    reset_rect = reset_base_surf.get_rect(center=(cx, y - int(55 * scale)))
    if reset_rect.collidepoint(mouse_pos):
        hover_font = get_font(_sekuya_font_path, int(26 * scale))
        reset_surf = hover_font.render("Reset Data", True, (255, 100, 100))
    else:
        reset_surf = reset_base_surf
    reset_rect = reset_surf.get_rect(center=(cx, y - int(55 * scale)))
    screen.blit(reset_surf, reset_rect)

    # Close Button
    close_base_surf = btn_font.render("Close", True, (160, 160, 170))
    close_rect = close_base_surf.get_rect(center=(cx + int(80 * scale), y))
    if close_rect.collidepoint(mouse_pos):
        hover_font = get_font(_sekuya_font_path, int(26 * scale))
        close_surf = hover_font.render("Close", True, (220, 220, 240))
    else:
        close_surf = close_base_surf
    close_rect = close_surf.get_rect(center=(cx + int(80 * scale), y))
    screen.blit(close_surf, close_rect)

    version_text = small_font.render("v1.0.0", True, (80, 80, 90))
    screen.blit(version_text, (panel_x + panel_w - version_text.get_width() - int(12 * scale), panel_y + panel_h - version_text.get_height() - int(10 * scale)))

    bsit_text = small_font.render("BSIT 1D", True, (80, 80, 90))
    screen.blit(bsit_text, (panel_x + int(12 * scale), panel_y + panel_h - bsit_text.get_height() - int(10 * scale)))

    return {
        "bgm_minus": bgm_minus,
        "bgm_plus": bgm_plus,
        "bgm_slider": bgm_slider,
        "fullscreen": fs_rect,
        "reset": reset_rect,
        "exit": exit_rect,
        "close": close_rect,
}

def draw_reset_confirm_modal(screen):
    WIDTH = screen.get_width()
    HEIGHT = screen.get_height()
    cx = WIDTH // 2
    scale = HEIGHT / 600

    overlay = pygame.Surface((WIDTH, HEIGHT))
    overlay.set_alpha(220)
    overlay.fill((10, 5, 5))
    screen.blit(overlay, (0, 0))

    panel_w = int(500 * scale)
    panel_h = int(240 * scale)
    panel_x = cx - panel_w // 2
    panel_y = HEIGHT // 2 - panel_h // 2
    pygame.draw.rect(screen, (30, 20, 20), (panel_x, panel_y, panel_w, panel_h), border_radius=12)
    pygame.draw.rect(screen, (80, 40, 40), (panel_x, panel_y, panel_w, panel_h), 2, border_radius=12)

    title_font = get_font(_sekuya_font_path, int(32 * scale))
    body_font = get_font(_sekuya_font_path, int(20 * scale))
    btn_font = get_font(_sekuya_font_path, int(24 * scale))

    y = panel_y + int(30 * scale)
    title = title_font.render("WARNING", True, (255, 100, 100))
    screen.blit(title, (cx - title.get_width() // 2, y))
    
    y += int(50 * scale)
    msg1 = body_font.render("This will delete all your coins,", True, (200, 200, 200))
    screen.blit(msg1, (cx - msg1.get_width() // 2, y))
    
    y += int(30 * scale)
    msg2 = body_font.render("levels, and skills. Are you sure?", True, (200, 200, 200))
    screen.blit(msg2, (cx - msg2.get_width() // 2, y))

    y += int(70 * scale)
    mouse_pos = pygame.mouse.get_pos()

    yes_base = btn_font.render("YES, WIPE DATA", True, (255, 80, 80))
    yes_rect = yes_base.get_rect(center=(cx - int(110 * scale), y))
    if yes_rect.collidepoint(mouse_pos):
        hover_font = get_font(_sekuya_font_path, int(28 * scale))
        yes_surf = hover_font.render("YES, WIPE DATA", True, (255, 0, 0))
    else:
        yes_surf = yes_base
    yes_rect = yes_surf.get_rect(center=(cx - int(110 * scale), y))
    screen.blit(yes_surf, yes_rect)

    no_base = btn_font.render("CANCEL", True, (150, 150, 150))
    no_rect = no_base.get_rect(center=(cx + int(110 * scale), y))
    if no_rect.collidepoint(mouse_pos):
        hover_font = get_font(_sekuya_font_path, int(28 * scale))
        no_surf = hover_font.render("CANCEL", True, (200, 200, 200))
    else:
        no_surf = no_base
    no_rect = no_surf.get_rect(center=(cx + int(110 * scale), y))
    screen.blit(no_surf, no_rect)

    return {"yes": yes_rect, "no": no_rect}

def draw_shop_modal(screen, state_obj, warning_msg=""):
    WIDTH = screen.get_width()
    HEIGHT = screen.get_height()
    cx = WIDTH // 2
    scale = min(WIDTH / 1200, HEIGHT / 600)
    mouse_pos = pygame.mouse.get_pos()

    overlay = pygame.Surface((WIDTH, HEIGHT))
    overlay.set_alpha(180)
    overlay.fill((0, 0, 0))
    screen.blit(overlay, (0, 0))

    title_font = get_font(_sekuya_font_path, int(36 * scale))
    body_font = get_font(_sekuya_font_path, int(20 * scale))
    btn_font = get_font(_sekuya_font_path, int(22 * scale))
    small_font = get_font(_sekuya_font_path, int(14 * scale))

    n_rows = 3
    gap_x = int(24 * scale)
    gap_y = int(16 * scale)
    pad = int(30 * scale)
    item_h = int(120 * scale)
    header_h = int(40 * scale) + int(40 * scale) + int(40 * scale)
    grid_h = n_rows * (item_h + gap_y) - gap_y
    footer_h = int(40 * scale) + int(40 * scale)
    panel_h = header_h + grid_h + footer_h + pad * 2
    panel_w = min(int(960 * scale), int(WIDTH * 0.95))
    panel_x = cx - panel_w // 2
    panel_y = max(int(20 * scale), HEIGHT // 2 - panel_h // 2)

    pygame.draw.rect(screen, (18, 18, 20), (panel_x, panel_y, panel_w, panel_h), border_radius=10)
    pygame.draw.rect(screen, (45, 45, 50), (panel_x, panel_y, panel_w, panel_h), 1, border_radius=10)

    y = panel_y + pad

    title = title_font.render("SHOP", True, (240, 240, 240))
    screen.blit(title, (cx - title.get_width() // 2, y))
    y += int(40 * scale)

    coin_text = body_font.render(f"Coins: {state_obj.score}", True, (255, 200, 50))
    screen.blit(coin_text, (cx - coin_text.get_width() // 2, y))
    y += int(40 * scale)

    cols = 2
    item_w = (panel_w - pad * 2 - gap_x) // 2
    start_x = panel_x + pad

    shop_rects = {}

    def draw_item(row, col, title_str, desc_str, price, is_owned, key, draw_icon_fn):
        ix = start_x + col * (item_w + gap_x)
        iy = y + row * (item_h + gap_y)
        rect = pygame.Rect(ix, iy, item_w, item_h)
        is_hover = rect.collidepoint(mouse_pos)

        bg_color = (28, 28, 32) if is_hover else (22, 22, 24)
        bd_color = (70, 70, 80) if is_hover else (40, 40, 45)
        pygame.draw.rect(screen, bg_color, rect, border_radius=8)
        pygame.draw.rect(screen, bd_color, rect, 1, border_radius=8)

        icon_cx = ix + int(36 * scale)
        icon_cy = iy + item_h // 2
        draw_icon_fn(icon_cx, icon_cy)

        text_x = ix + int(70 * scale)

        title_surf = body_font.render(title_str, True, (240, 240, 240))
        screen.blit(title_surf, (text_x, iy + int(14 * scale)))

        desc_surf = small_font.render(desc_str, True, (150, 150, 150))
        screen.blit(desc_surf, (text_x, iy + int(44 * scale)))

        btn_w = int(80 * scale)
        btn_h = int(32 * scale)
        btn_x = ix + item_w - int(14 * scale) - btn_w
        btn_y = iy + item_h - int(12 * scale) - btn_h
        btn_rect = pygame.Rect(btn_x, btn_y, btn_w, btn_h)

        if is_owned:
            skill_key = key.replace("buy_", "")
            is_equipped = state_obj.is_equipped(skill_key)
            hover = btn_rect.collidepoint(mouse_pos)

            if is_equipped:
                btn_bg = (180, 80, 80) if hover else (120, 50, 50)
                txt = "UNEQUIP"
            else:
                btn_bg = (60, 180, 100) if hover else (40, 150, 70)
                txt = "EQUIP"

            pygame.draw.rect(screen, btn_bg, btn_rect, border_radius=6)
            status = small_font.render(txt, True, (255, 255, 255))
            screen.blit(status, (btn_rect.centerx - status.get_width() // 2, btn_rect.centery - status.get_height() // 2))
            shop_rects[key] = btn_rect
        else:
            can_afford = state_obj.score >= price
            buy_hover = btn_rect.collidepoint(mouse_pos)

            btn_bg = (40, 150, 70) if can_afford else (120, 50, 50)
            if buy_hover and can_afford:
                btn_bg = (50, 180, 80)

            pygame.draw.rect(screen, btn_bg, btn_rect, border_radius=6)
            buy_text = btn_font.render(f"{price}c", True, (255, 255, 255))
            screen.blit(buy_text, (btn_rect.centerx - buy_text.get_width() // 2, btn_rect.centery - buy_text.get_height() // 2))
            shop_rects[key] = btn_rect

    def draw_dash(cx, cy):
        s = int(14 * scale)
        for offset in [0, s]:
            pygame.draw.polygon(screen, (220, 220, 220), [
                (cx - s + offset, cy), (cx - s//2 + offset, cy - s//2),
                (cx - s//4 + offset, cy), (cx - s//2 + offset, cy + s//2)
            ])

    def draw_regen(cx, cy):
        pw, pl = int(4 * scale), int(16 * scale)
        pygame.draw.rect(screen, (220, 80, 80), (cx - pw//2, cy - pl//2, pw, pl))
        pygame.draw.rect(screen, (220, 80, 80), (cx - pl//2, cy - pw//2, pl, pw))

    def draw_cd(cx, cy):
        hw, hh = int(12 * scale), int(16 * scale)
        pygame.draw.polygon(screen, (100, 200, 255), [
            (cx - hw//2, cy - hh//2), (cx + hw//2, cy - hh//2), (cx, cy),
            (cx + hw//2, cy + hh//2), (cx - hw//2, cy + hh//2), (cx, cy)
        ], max(2, int(2 * scale)))

    def draw_reach(cx, cy):
        pygame.draw.line(screen, (255, 100, 100), (cx - 15*scale, cy), (cx + 15*scale, cy), int(3*scale))
        pygame.draw.polygon(screen, (255, 100, 100), [(cx+15*scale, cy-5*scale), (cx+20*scale, cy), (cx+15*scale, cy+5*scale)])

    def draw_crit(cx, cy):
        s = int(10 * scale)
        pygame.draw.polygon(screen, (255, 50, 50), [(cx, cy-s), (cx+s, cy), (cx, cy+s), (cx-s, cy)])
        pygame.draw.polygon(screen, (255, 200, 50), [(cx, cy-s//2), (cx+s//2, cy), (cx, cy+s//2), (cx-s//2, cy)])

    def draw_spikes(cx, cy):
        pygame.draw.circle(screen, (150, 150, 180), (cx, cy), int(8*scale), int(2*scale))
        for angle in range(0, 360, 45):
            rad = math.radians(angle)
            pygame.draw.circle(screen, (200, 100, 255), (cx + math.cos(rad) * 12 * scale, cy + math.sin(rad) * 12 * scale), int(2*scale))

    draw_item(0, 0, "Double Dash", "Air dash after jumping", 50, state_obj.has_double_dash, "buy_double_dash", draw_dash)
    draw_item(0, 1, "Regen Health", "Regen health while idle", 25, state_obj.has_regen, "buy_regen", draw_regen)
    draw_item(1, 0, "CD Reduction", "Halve special skill cooldowns", 100, state_obj.has_cd_reduction, "buy_cd_reduction", draw_cd)
    draw_item(1, 1, "Titan's Grip", "Extend attack reach by 30%", 50, state_obj.has_extended_reach, "buy_reach", draw_reach)
    draw_item(2, 0, "Executioner's Blow", "20% chance to double damage", 150, state_obj.has_executioner, "buy_executioner", draw_crit)
    draw_item(2, 1, "Spiked Armor", "Reflect damage to enemies", 100, state_obj.has_spiked_armor, "buy_spiked_armor", draw_spikes)

    y += 3 * (item_h + gap_y) + int(10 * scale)

    if warning_msg:
        msg = body_font.render(warning_msg, True, (220, 80, 80))
        screen.blit(msg, (cx - msg.get_width() // 2, y))

    y += int(40 * scale)

    close_text = btn_font.render("Close", True, (160, 160, 170))
    close_rect = close_text.get_rect(center=(cx, y))

    close_bg = pygame.Rect(close_rect.x - int(20 * scale), close_rect.y - int(10 * scale), close_rect.width + int(40 * scale), close_rect.height + int(20 * scale))
    if close_bg.collidepoint(mouse_pos):
        pygame.draw.rect(screen, (35, 35, 40), close_bg, border_radius=6)
        close_text = btn_font.render("Close", True, (240, 240, 240))

    screen.blit(close_text, close_rect)
    shop_rects["close"] = close_bg

    return shop_rects

def draw_char_select_modal(screen):
    WIDTH = screen.get_width()
    HEIGHT = screen.get_height()
    cx = WIDTH // 2
    scale = HEIGHT / 600

    overlay = pygame.Surface((WIDTH, HEIGHT))
    overlay.set_alpha(180)
    overlay.fill((0, 0, 0))
    screen.blit(overlay, (0, 0))

    panel_w = min(int(600 * scale), int(WIDTH * 0.8))
    panel_h = int(400 * scale)
    panel_x = cx - panel_w // 2
    panel_y = max(int(60 * scale), HEIGHT // 2 - panel_h // 2)
    pygame.draw.rect(screen, (25, 22, 35), (panel_x, panel_y, panel_w, panel_h), border_radius=12)
    pygame.draw.rect(screen, (55, 50, 75), (panel_x, panel_y, panel_w, panel_h), 2, border_radius=12)

    title_font = get_font(_sekuya_font_path, int(36 * scale))
    body_font = get_font(_sekuya_font_path, int(22 * scale))
    btn_font = get_font(_sekuya_font_path, int(22 * scale))

    y = panel_y + int(24 * scale)

    title = title_font.render("SELECT CHARACTER", True, (255, 215, 0))
    screen.blit(title, (cx - title.get_width() // 2, y))
    y += int(60 * scale)

    card_w = int(220 * scale)
    card_h = int(200 * scale)
    gap = int(40 * scale)

    gr_x = cx - gap // 2 - card_w
    gr_rect = pygame.Rect(gr_x, y, card_w, card_h)
    pygame.draw.rect(screen, (35, 32, 45), gr_rect, border_radius=8)
    pygame.draw.rect(screen, (65, 60, 85), gr_rect, 1, border_radius=8)
    gr_title = body_font.render("GraveRobber", True, (200, 200, 200))
    screen.blit(gr_title, (gr_rect.centerx - gr_title.get_width() // 2, y + int(20 * scale)))

    gr_img = _get_char_img("GraveRobber")
    if gr_img:
        screen.blit(gr_img, (gr_rect.centerx - gr_img.get_width() // 2 + int(20 * scale), gr_rect.centery - gr_img.get_height() // 2 + int(5 * scale)))

    gr_desc = get_font(_sekuya_font_path, int(14 * scale)).render("Fast & Agile", True, (150, 150, 150))
    screen.blit(gr_desc, (gr_rect.centerx - gr_desc.get_width() // 2, gr_rect.bottom - int(30 * scale)))

    wc_x = cx + gap // 2
    wc_rect = pygame.Rect(wc_x, y, card_w, card_h)
    pygame.draw.rect(screen, (35, 32, 45), wc_rect, border_radius=8)
    pygame.draw.rect(screen, (65, 60, 85), wc_rect, 1, border_radius=8)
    wc_title = body_font.render("Woodcutter", True, (200, 200, 200))
    screen.blit(wc_title, (wc_rect.centerx - wc_title.get_width() // 2, y + int(20 * scale)))

    wc_img = _get_char_img("Woodcutter")
    if wc_img:
        screen.blit(wc_img, (wc_rect.centerx - wc_img.get_width() // 2 + int(15 * scale), wc_rect.centery - wc_img.get_height() // 2 + int(5 * scale)))

    wc_desc = get_font(_sekuya_font_path, int(14 * scale)).render("Heavy & Strong", True, (150, 150, 150))
    screen.blit(wc_desc, (wc_rect.centerx - wc_desc.get_width() // 2, wc_rect.bottom - int(30 * scale)))

    y += card_h + int(40 * scale)

    close_text = btn_font.render("Close", True, (160, 160, 170))
    close_rect = close_text.get_rect(center=(cx, y))
    screen.blit(close_text, close_rect)

    return {
        "GraveRobber": gr_rect,
        "Woodcutter": wc_rect,
        "close": close_rect
    }

def draw_help_modal(screen):
    WIDTH = screen.get_width()
    HEIGHT = screen.get_height()
    cx = WIDTH // 2
    scale = min(WIDTH / 1280, HEIGHT / 720)

    overlay = pygame.Surface((WIDTH, HEIGHT))
    overlay.set_alpha(200)
    overlay.fill((0, 0, 0))
    screen.blit(overlay, (0, 0))

    title_font = get_font(_sekuya_font_path, int(32 * scale))
    header_font = get_font(_sekuya_font_path, int(17 * scale))
    body_font = get_font(_sekuya_font_path, int(14 * scale))
    btn_font = get_font(_sekuya_font_path, int(20 * scale))

    pad = int(26 * scale)
    col_gap = int(20 * scale)
    row_gap = int(5 * scale)
    section_gap = int(10 * scale)
    key_col_w = int(80 * scale)

    panel_w = min(int(860 * scale), int(WIDTH * 0.92))
    half_w = (panel_w - pad * 2 - col_gap) // 2

    line_color = (60, 50, 90)

    def measure_section_header():
        return header_font.size("X")[1] + int(3 * scale) + section_gap

    def measure_row():
        return body_font.size("X")[1] + row_gap

    def measure_text(text):
        return body_font.size(text)[1] + row_gap

    title_h = title_font.size("X")[1]
    title_block = title_h + int(16 * scale)

    left_items = [
        ("header", "MOVEMENT"),
        ("row", "A / D", "Move left / right"),
        ("row", "W / Up", "Jump"),
        ("gap",),
        ("header", "COMBAT"),
        ("row", "SPACE", "Basic attack"),
        ("row", "E", "Skill 1  (Lv 2+)"),
        ("row", "Q", "Skill 2  (Lv 4+)"),
        ("gap",),
        ("header", "COMBO"),
        ("text", "SPACE \u2192 E \u2192 Q \u2192 SPACE (GraveRobber)"),
        ("text", "W \u2192 E \u2192 Q \u2192 SPACE (Woodcutter)"),
        ("text", "5x damage + HP restore"),
    ]

    right_items = [
        ("header", "GENERAL"),
        ("row", "ESC", "Pause game"),
        ("row", "R", "Restart (paused)"),
        ("row", "M", "Return to lobby"),
        ("gap",),
        ("header", "OBJECTIVES"),
        ("bullet", "Defeat all enemies to advance"),
        ("bullet", "Collect coins from kills"),
        ("bullet", "Spend coins in the Shop"),
        ("bullet", "Gain XP to level up"),
        ("bullet", "Level up raises max HP"),
        ("gap",),
        ("header", "SKILLS (SHOP)"),
        ("bullet", "Double Dash \u2013 air dash in-flight"),
        ("bullet", "Regen \u2013 recover HP when idle"),
        ("bullet", "CD Reduction \u2013 faster skills"),
        ("bullet", "Titan\u2019s Grip \u2013 longer reach"),
        ("bullet", "Executioner \u2013 20% crit chance"),
        ("bullet", "Spiked Armor \u2013 reflect damage"),
    ]

    def measure_items(items):
        h = 0
        for item in items:
            if item[0] == "header":
                h += header_font.size("X")[1] + int(3 * scale) + section_gap
            elif item[0] in ("row", "text", "bullet"):
                h += body_font.size("X")[1] + row_gap
            elif item[0] == "gap":
                h += section_gap
        return h

    left_h = measure_items(left_items)
    right_h = measure_items(right_items)
    content_h = max(left_h, right_h)

    close_h = btn_font.size("X")[1] + int(24 * scale)
    divider_h = int(10 * scale)

    panel_h = pad + title_block + content_h + divider_h + close_h + pad
    max_panel_h = HEIGHT - int(20 * scale)
    panel_h = min(panel_h, max_panel_h)

    panel_x = cx - panel_w // 2
    panel_y = HEIGHT // 2 - panel_h // 2

    pygame.draw.rect(screen, (18, 16, 28), (panel_x, panel_y, panel_w, panel_h), border_radius=12)
    pygame.draw.rect(screen, (80, 60, 120), (panel_x, panel_y, panel_w, panel_h), 2, border_radius=12)

    y = panel_y + pad

    title_surf = title_font.render("HOW TO PLAY", True, (255, 215, 0))
    screen.blit(title_surf, (cx - title_surf.get_width() // 2, y))
    y += title_h + int(16 * scale)

    col_x = panel_x + pad
    col2_x = col_x + half_w + col_gap

    close_bottom = panel_y + panel_h - pad
    close_top = close_bottom - close_h
    content_area_h = close_top - y - divider_h

    clip_rect = pygame.Rect(panel_x + 2, y, panel_w - 4, content_area_h)
    old_clip = screen.get_clip()
    screen.set_clip(clip_rect)

    def draw_section_header(text, x, y_pos):
        surf = header_font.render(text, True, (200, 160, 255))
        screen.blit(surf, (x, y_pos))
        line_y = y_pos + surf.get_height() + int(2 * scale)
        pygame.draw.line(screen, line_color, (x, line_y), (x + half_w, line_y), 1)
        return y_pos + surf.get_height() + int(3 * scale) + section_gap

    def draw_row(key_str, action_str, x, y_pos):
        key_surf = body_font.render(key_str, True, (255, 220, 80))
        act_surf = body_font.render(action_str, True, (190, 190, 190))
        screen.blit(key_surf, (x, y_pos))
        screen.blit(act_surf, (x + key_col_w, y_pos))
        return y_pos + key_surf.get_height() + row_gap

    def draw_text(text, x, y_pos, color=(190, 190, 190)):
        surf = body_font.render(text, True, color)
        screen.blit(surf, (x, y_pos))
        return y_pos + surf.get_height() + row_gap

    def render_items(items, x, start_y):
        cy2 = start_y
        for item in items:
            if item[0] == "header":
                cy2 = draw_section_header(item[1], x, cy2)
            elif item[0] == "row":
                cy2 = draw_row(item[1], item[2], x, cy2)
            elif item[0] == "text":
                color = (255, 120, 200) if "\u2192" in item[1] else (190, 190, 190)
                cy2 = draw_text(item[1], x, cy2, color)
            elif item[0] == "bullet":
                cy2 = draw_text(f"\u2022  {item[1]}", x, cy2)
            elif item[0] == "gap":
                cy2 += section_gap

    render_items(left_items, col_x, y)
    render_items(right_items, col2_x, y)

    screen.set_clip(old_clip)

    pygame.draw.line(screen, (60, 50, 90),
                     (panel_x + pad, close_top),
                     (panel_x + panel_w - pad, close_top), 1)

    mouse_pos = pygame.mouse.get_pos()
    close_cy = close_top + close_h // 2
    close_base = btn_font.render("Close", True, (160, 160, 170))
    close_rect = close_base.get_rect(center=(cx, close_cy))
    if close_rect.collidepoint(mouse_pos):
        hover_font = get_font(_sekuya_font_path, int(24 * scale))
        close_surf = hover_font.render("Close", True, (220, 220, 240))
    else:
        close_surf = close_base
    close_rect = close_surf.get_rect(center=(cx, close_cy))
    screen.blit(close_surf, close_rect)

    return {"close": close_rect}
