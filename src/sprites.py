import os
import pygame


class SequenceSheet:
    """Loads individual PNG frames from a folder (sorted by filename)."""

    def __init__(self, folder, scale=1):
        self.folder = folder
        self.scale = scale
        self.frames = self._load_frames()

    def _load_frames(self):
        frames = []
        if not os.path.isdir(self.folder):
            return frames
        files = sorted([
            f for f in os.listdir(self.folder)
            if f.lower().endswith(".png")
        ])
        for fname in files:
            path = os.path.join(self.folder, fname)
            img = pygame.image.load(path).convert_alpha()
            if self.scale != 1:
                w, h = img.get_size()
                img = pygame.transform.scale(img, (int(w * self.scale), int(h * self.scale)))
            frames.append(img)
        return frames


class SpriteSheet:
    """Loads a sprite sheet and slices it into frames."""

    def __init__(self, path, frame_width, frame_height, scale=1):
        self.sheet = pygame.image.load(path).convert_alpha()
        self.frame_w = frame_width
        self.frame_h = frame_height
        self.scale = scale
        self.frames = self._slice_frames()

    def _slice_frames(self):
        sheet_w, sheet_h = self.sheet.get_size()
        cols = sheet_w // self.frame_w
        rows = sheet_h // self.frame_h
        frames = []
        for row in range(rows):
            for col in range(cols):
                x = col * self.frame_w
                y = row * self.frame_h
                # Skip if would go past sheet edge
                if x + self.frame_w > sheet_w or y + self.frame_h > sheet_h:
                    continue
                frame = self.sheet.subsurface((x, y, self.frame_w, self.frame_h))
                # Skip mostly-transparent frames (padding/empty)
                if self._is_empty(frame):
                    continue
                if self.scale != 1:
                    new_w = int(self.frame_w * self.scale)
                    new_h = int(self.frame_h * self.scale)
                    frame = pygame.transform.scale(frame, (new_w, new_h))
                frames.append(frame)
        # Fallback: if all frames were empty, use whole sheet as single frame
        if not frames:
            frame = self.sheet.copy()
            if self.scale != 1:
                new_w = int(sheet_w * self.scale)
                new_h = int(sheet_h * self.scale)
                frame = pygame.transform.scale(frame, (new_w, new_h))
            frames.append(frame)
        return frames

    def _trim_frame(self, surf):
        """Crop surface to the bounding box of non-transparent pixels."""
        mask = pygame.mask.from_surface(surf)
        rect = mask.get_bounding_rects()
        if not rect:
            return surf
        r = rect[0]
        if r.width == 0 or r.height == 0:
            return surf
        trimmed = pygame.Surface((r.width, r.height), pygame.SRCALPHA)
        trimmed.blit(surf, (0, 0), r)
        return trimmed

    def _is_empty(self, surf):
        """Check if a surface is mostly transparent."""
        mask = pygame.mask.from_surface(surf)
        return mask.count() < 1  # only skip completely empty frames


class AnimatedSprite:
    """Manages animation states and frame cycling."""

    def __init__(self, animations, default_state="idle"):
        """
        animations: dict {state_name: (SpriteSheet, fps)}
        """
        self.anims = animations
        self.state = default_state
        self.frame_index = 0
        self.timer = 0
        self.facing_right = True
        self.oneshot = False
        self._set_fps()

    def _set_fps(self):
        self.fps = self.anims[self.state][1] if self.state in self.anims else 8

    def set_state(self, state, start_frame=0, oneshot=False):
        if state != self.state and state in self.anims:
            self.state = state
            self.frame_index = start_frame
            self.timer = 0
            self.oneshot = oneshot
            self._set_fps()

    def update(self, dt=1):
        frames = self.anims[self.state][0].frames
        if len(frames) <= 1:
            self.frame_index = 0
            return
        self.timer += dt
        if self.timer >= 30 / self.fps:
            self.timer = 0
            next_idx = self.frame_index + 1
            if self.oneshot and next_idx >= len(frames):
                return  # freeze on last frame until state changes
            self.frame_index = next_idx % len(frames)

    def is_finished(self):
        frames = self.anims[self.state][0].frames
        return self.oneshot and self.frame_index >= len(frames) - 1

    def get_frame(self):
        frames = self.anims[self.state][0].frames
        frame = frames[self.frame_index]
        if not self.facing_right:
            frame = pygame.transform.flip(frame, True, False)
        return frame

    def draw(self, screen, x, y, alpha=255):
        frame = self.get_frame()
        if alpha < 255:
            # Need to create a copy to apply alpha if we don't want to modify the cached frame
            temp_frame = frame.copy()
            temp_frame.set_alpha(alpha)
            frame = temp_frame
        rect = frame.get_rect(midbottom=(x, y))
        screen.blit(frame, rect)
