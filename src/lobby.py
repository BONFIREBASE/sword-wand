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
                # Scale increased to 4 for larger preview
                sheet = SpriteSheet(path, 48, 48, 4)
                _gr_idle_anim = sheet.frames
        if _gr_idle_anim:
            # 8 frames per second = 125ms per frame. 
            # Added a +300ms offset to GraveRobber so they don't animate in perfect robotic sync!
            frame_idx = ((current_time + 300) // 125) % len(_gr_idle_anim)
            return _gr_idle_anim[frame_idx]
            
    elif char_type == "Woodcutter":
        if _wc_idle_anim is None:
            path = os.path.join("assets", "characters", "1 Woodcutter", "Woodcutter_idle.png")
            if os.path.exists(path):
                # Scale increased to 4 for larger preview
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
    scale = HEIGHT / 600  # reference height

    # Scale to fill width while preserving aspect ratio, then crop/pad to fit height
    bg_w, bg_h = _lobby_bg_raw.get_size()
    scale_w = WIDTH / bg_w
    scale_h = HEIGHT / bg_h
    # Use scale that fills width and shows bottom (floor)
    scale_factor = max(scale_w, scale_h)
    new_w = int(bg_w * scale_factor)
    new_h = int(bg_h * scale_factor)
    
    global _cached_lobby_bg, _cached_lobby_size
    if _cached_lobby_size != (new_w, new_h):
        _cached_lobby_bg = pygame.transform.scale(_lobby_bg_raw, (new_w, new_h)).convert()
        _cached_lobby_size = (new_w, new_h)
        
    # Anchor to bottom center so floor stays visible
    blit_x = (WIDTH - new_w) // 2
    blit_y = HEIGHT - new_h
    screen.blit(_cached_lobby_bg, (blit_x, blit_y))

    cx = WIDTH // 2

    # Text elements
    title_font = get_font(_sekuya_font_path, int(72 * scale))
    btn_font = get_font(_sekuya_font_path, int(44 * scale))
    
    # Title
    title_text = title_font.render("SWORD & WAND", True, (40, 20, 10))
    title_h = title_text.get_height()

    gap_title_play = int(60 * scale)
    btn_spacing = int(25 * scale)

    start_y = HEIGHT // 2 - (title_h + gap_title_play + 3 * int(44 * scale) + 2 * btn_spacing) // 2

    # Title centered
    title_rect = title_text.get_rect(center=(cx, start_y + title_h // 2))
    screen.blit(title_text, title_rect)

    # Button Helper
    def draw_menu_btn(text, center_y, name):
        mouse_pos = pygame.mouse.get_pos()
        
        base_surf = btn_font.render(text, True, (40, 20, 10))
        btn_rect = base_surf.get_rect(center=(cx, center_y))
        
        is_hover = btn_rect.collidepoint(mouse_pos)
        
        # Hover animation: scale up text slightly
        if is_hover:
            hover_font = get_font(_sekuya_font_path, int(50 * scale))
            text_surf = hover_font.render(text, True, (80, 40, 20))
        else:
            text_surf = btn_font.render(text, True, (40, 20, 10))
            
        screen.blit(text_surf, text_surf.get_rect(center=btn_rect.center))
        
        lobby_buttons[name] = btn_rect
        return btn_rect.bottom + btn_spacing

    # Draw Buttons
    next_y = title_rect.bottom + gap_title_play
    next_y = draw_menu_btn("PLAY", next_y + int(22 * scale), "play")
    next_y = draw_menu_btn("SHOP", next_y + int(22 * scale), "shop")
    next_y = draw_menu_btn("OPTIONS", next_y + int(22 * scale), "options")

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

    title_font = get_font(_sekuya_font_path, int(36 * scale))
    body_font = get_font(_sekuya_font_path, int(20 * scale))
    small_font = get_font(_sekuya_font_path, int(16 * scale))
    btn_font = get_font(_sekuya_font_path, int(22 * scale))

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

def draw_shop_modal(screen, state_obj, show_warning=False):
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
    gap_x = int(20 * scale)
    gap_y = int(15 * scale)
    pad = int(24 * scale)
    item_h = int(80 * scale)
    header_h = int(40 * scale) + int(40 * scale) + int(40 * scale)
    grid_h = n_rows * (item_h + gap_y) - gap_y
    footer_h = int(40 * scale) + int(40 * scale)
    panel_h = header_h + grid_h + footer_h + pad * 2
    panel_w = min(int(820 * scale), int(WIDTH * 0.92))
    panel_x = cx - panel_w // 2
    panel_y = max(int(40 * scale), HEIGHT // 2 - panel_h // 2)

    shadow_surf = pygame.Surface((panel_w + 8, panel_h + 8), pygame.SRCALPHA)
    shadow_surf.fill((0, 0, 0, 60))
    screen.blit(shadow_surf, (panel_x - 4, panel_y + 4))
    pygame.draw.rect(screen, (30, 26, 42), (panel_x, panel_y, panel_w, panel_h), border_radius=14)
    pygame.draw.rect(screen, (70, 60, 90), (panel_x, panel_y, panel_w, panel_h), 2, border_radius=14)
    inner = pygame.Rect(panel_x + 3, panel_y + 3, panel_w - 6, panel_h - 6)
    pygame.draw.rect(screen, (38, 34, 52), inner, border_radius=12)

    y = panel_y + pad

    title = title_font.render("SHOP", True, (255, 215, 0))
    screen.blit(title, (cx - title.get_width() // 2, y))
    y += int(40 * scale)

    coin_text = body_font.render(f"Coins: {state_obj.score}", True, (240, 200, 80))
    coin_shadow = body_font.render(f"Coins: {state_obj.score}", True, (180, 140, 40))
    screen.blit(coin_shadow, (cx - coin_text.get_width() // 2 + 1, y + 1))
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

        bg_color = (48, 42, 62) if is_hover else (35, 32, 45)
        bd_color = (90, 80, 110) if is_hover else (65, 60, 85)
        pygame.draw.rect(screen, bg_color, rect, border_radius=10)
        pygame.draw.rect(screen, bd_color, rect, 2 if is_hover else 1, border_radius=10)

        icon_cx = ix + int(30 * scale)
        icon_cy = iy + item_h // 2
        draw_icon_fn(icon_cx, icon_cy)

        item_label = body_font.render(title_str, True, (220, 220, 230) if is_hover else (200, 200, 210))
        screen.blit(item_label, (ix + int(60 * scale), iy + int(14 * scale)))
        desc_surf = small_font.render(desc_str, True, (160, 160, 170))
        screen.blit(desc_surf, (ix + int(60 * scale), iy + int(46 * scale)))

        if is_owned:
            status = btn_font.render("OWNED", True, (100, 255, 100))
            sx = ix + item_w - int(10 * scale) - status.get_width()
            sy = icon_cy - status.get_height() // 2
            screen.blit(status, (sx, sy))
        else:
            buy_text = btn_font.render(f"{price}c", True, (255, 255, 255))
            buy_w = int(70 * scale)
            buy_h = int(38 * scale)
            buy_rect = pygame.Rect(ix + item_w - int(10 * scale) - buy_w, icon_cy - buy_h // 2, buy_w, buy_h)
            can_afford = state_obj.score >= price
            buy_hover = buy_rect.collidepoint(mouse_pos)
            if can_afford:
                color = (70, 180, 90) if buy_hover else (60, 160, 80)
            else:
                color = (140, 70, 70) if buy_hover else (120, 60, 60)
            pygame.draw.rect(screen, color, buy_rect, border_radius=10)
            if buy_hover and can_afford:
                pygame.draw.rect(screen, (100, 220, 120), buy_rect, 2, border_radius=10)
            screen.blit(buy_text, (buy_rect.centerx - buy_text.get_width() // 2, buy_rect.centery - buy_text.get_height() // 2))
            shop_rects[key] = buy_rect

    def draw_dash(cx, cy):
        s = int(16 * scale)
        for offset in [0, s]:
            pygame.draw.polygon(screen, (220, 220, 220), [
                (cx - s + offset, cy),
                (cx - s//2 + offset, cy - s//2),
                (cx - s//4 + offset, cy),
                (cx - s//2 + offset, cy + s//2)
            ])

    def draw_regen(cx, cy):
        pw = int(6 * scale)
        pl = int(20 * scale)
        pygame.draw.rect(screen, (220, 80, 80), (cx - pw//2, cy - pl//2, pw, pl))
        pygame.draw.rect(screen, (220, 80, 80), (cx - pl//2, cy - pw//2, pl, pw))

    def draw_cd(cx, cy):
        hw, hh = int(14 * scale), int(20 * scale)
        pygame.draw.polygon(screen, (100, 200, 255), [
            (cx - hw//2, cy - hh//2), (cx + hw//2, cy - hh//2), (cx, cy),
            (cx + hw//2, cy + hh//2), (cx - hw//2, cy + hh//2), (cx, cy)
        ], max(2, int(2 * scale)))

    def draw_reach(cx, cy):
        pygame.draw.line(screen, (255, 100, 100), (cx - 15*scale, cy), (cx + 15*scale, cy), int(4*scale))
        pygame.draw.polygon(screen, (255, 100, 100), [(cx+15*scale, cy-6*scale), (cx+22*scale, cy), (cx+15*scale, cy+6*scale)])

    def draw_crit(cx, cy):
        s = int(12 * scale)
        pygame.draw.polygon(screen, (255, 50, 50), [(cx, cy-s), (cx+s, cy), (cx, cy+s), (cx-s, cy)])
        pygame.draw.polygon(screen, (255, 200, 50), [(cx, cy-s//2), (cx+s//2, cy), (cx, cy+s//2), (cx-s//2, cy)])

    def draw_spikes(cx, cy):
        pygame.draw.circle(screen, (150, 150, 180), (cx, cy), int(10*scale))
        for angle in range(0, 360, 45):
            rad = math.radians(angle)
            x = cx + math.cos(rad) * 14 * scale
            y = cy + math.sin(rad) * 14 * scale
            pygame.draw.circle(screen, (200, 100, 255), (x, y), int(3*scale))

    draw_item(0, 0, "Double Dash", "Air dash after jumping", 50, state_obj.has_double_dash, "buy_double_dash", draw_dash)
    draw_item(0, 1, "Regen Health", "Regen health while idle", 25, state_obj.has_regen, "buy_regen", draw_regen)
    draw_item(1, 0, "CD Reduction", "Halve special skill cooldowns", 100, state_obj.has_cd_reduction, "buy_cd_reduction", draw_cd)
    draw_item(1, 1, "Titan's Grip", "Extend attack reach by 30%", 50, state_obj.has_extended_reach, "buy_reach", draw_reach)
    draw_item(2, 0, "Executioner's Blow", "20% chance to double damage", 150, state_obj.has_executioner, "buy_executioner", draw_crit)
    draw_item(2, 1, "Spiked Armor", "Reflect damage to enemies", 100, state_obj.has_spiked_armor, "buy_spiked_armor", draw_spikes)

    y += 3 * (item_h + gap_y) + int(10 * scale)

    if show_warning:
        msg = body_font.render("Not enough coins!", True, (220, 80, 80))
        screen.blit(msg, (cx - msg.get_width() // 2, y))

    y += int(40 * scale)

    close_text = btn_font.render("Close", True, (160, 160, 170))
    close_hover = pygame.Rect(0, 0, close_text.get_width() + 20, close_text.get_height() + 10)
    close_rect = close_text.get_rect(center=(cx, y))
    close_hover.center = close_rect.center
    if close_hover.collidepoint(mouse_pos):
        close_text = btn_font.render("Close", True, (200, 200, 210))
    screen.blit(close_text, close_rect)
    shop_rects["close"] = close_rect

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
