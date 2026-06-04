"""
Chicken Invaders 2 - CrashTech 2026, Challenge 8
Controls: Joystick=move, KEY[0]=shoot, KEY[1]=pause/restart
"""

import sys
import math
import random
import pygame

SCREEN_W = 1080
SCREEN_H = 1920
FPS      = 60
TITLE    = "Chicken Invaders 2  |  CrashTech 2026"

SCREEN_MENU         = "menu"
SCREEN_INSTRUCTIONS = "instructions"
SCREEN_OPTIONS      = "options"
SCREEN_GAME         = "game"


# ══════════════════════════════════════════════════════════════════════════════
#  Star field
# ══════════════════════════════════════════════════════════════════════════════

class StarField:
    def __init__(self, count=250):
        self.stars = [self._make(random.randint(0, SCREEN_H)) for _ in range(count)]

    def _make(self, y=0):
        return {"x": random.randint(0, SCREEN_W), "y": y,
                "spd": random.uniform(0.2, 1.4), "r": random.randint(1, 3),
                "b": random.randint(120, 255)}

    def update(self):
        for s in self.stars:
            s["y"] += s["spd"]
            if s["y"] > SCREEN_H:
                s.update(self._make(0))

    def draw(self, surf):
        for s in self.stars:
            b = s["b"]
            pygame.draw.circle(surf, (b, b, int(b * 1.1)), (int(s["x"]), int(s["y"])), s["r"])


# ══════════════════════════════════════════════════════════════════════════════
#  Fork cursor
# ══════════════════════════════════════════════════════════════════════════════

def make_fork_surface(size=48):
    """Draw a silver dining fork as a Surface."""
    surf = pygame.Surface((size, size * 3), pygame.SRCALPHA)
    w, h = surf.get_size()
    silver      = (200, 210, 220)
    silver_dark = (140, 150, 160)
    silver_hi   = (240, 248, 255)

    # Handle — long rectangle
    hx = w // 2
    pygame.draw.rect(surf, silver,      (hx - 5, h // 3, 10, h * 2 // 3 - 4), border_radius=3)
    pygame.draw.rect(surf, silver_dark, (hx - 5, h // 3, 3,  h * 2 // 3 - 4))

    # Neck (narrowing to tines)
    pygame.draw.rect(surf, silver, (hx - 4, h // 5, 8, h // 3 - h // 5 + 4), border_radius=2)

    # Four tines at the top
    tine_w = 4
    tine_h = h // 5 + 4
    offsets = [-9, -3, 3, 9]
    for ox in offsets:
        pygame.draw.rect(surf, silver,   (hx + ox - tine_w // 2, 0, tine_w, tine_h), border_radius=2)
        pygame.draw.rect(surf, silver_hi,(hx + ox - tine_w // 2, 0, 2,      tine_h // 2))

    return surf

def draw_fork_cursor(surf, fork_img, mx, my):
    surf.blit(fork_img, (mx - fork_img.get_width() // 2, my - 4))


# ══════════════════════════════════════════════════════════════════════════════
#  Drawing helpers
# ══════════════════════════════════════════════════════════════════════════════

def draw_nebula(surf, tick):
    """Subtle animated blue/purple nebula glow in the background."""
    pulse = int(12 * math.sin(tick * 0.015))
    for cx, cy, base_r, color in [
        (SCREEN_W // 2, SCREEN_H // 3, 380, (20, 30, 100)),
        (SCREEN_W * 3 // 4, SCREEN_H // 2, 260, (40, 10, 80)),
        (SCREEN_W // 4, SCREEN_H * 2 // 3, 200, (10, 50, 90)),
    ]:
        r = base_r + pulse
        glow = pygame.Surface((r * 2, r * 2), pygame.SRCALPHA)
        for step in range(5, 0, -1):
            alpha = step * 8
            cr = r * step // 5
            pygame.draw.circle(glow, (*color, alpha), (r, r), cr)
        surf.blit(glow, (cx - r, cy - r), special_flags=pygame.BLEND_ADD)


def draw_chicken(surf, cx, cy, scale=1.0, tick=0):
    s = scale
    bob = int(6 * math.sin(tick * 0.06))
    cy += bob

    def sc(v): return int(v * s)

    # Shadow on ground
    pygame.draw.ellipse(surf, (0, 0, 30),
                        (cx - sc(80), cy + sc(55), sc(160), sc(30)))

    # Body
    pygame.draw.ellipse(surf, (255, 215, 50),
                        (cx - sc(72), cy - sc(65), sc(144), sc(128)))
    # Body shading
    pygame.draw.ellipse(surf, (220, 180, 30),
                        (cx - sc(72), cy + sc(20), sc(144), sc(44)))

    # Head
    pygame.draw.circle(surf, (255, 215, 50), (cx, cy - sc(100)), sc(48))
    pygame.draw.circle(surf, (235, 195, 40), (cx + sc(10), cy - sc(90)), sc(30))

    # Comb
    for i, (dx, h) in enumerate([(-20, 38), (-5, 48), (12, 38)]):
        pygame.draw.ellipse(surf, (220, 30, 30),
                            (cx + sc(dx) - sc(10), cy - sc(162) - sc(h) + sc(20),
                             sc(22), sc(h)))

    # Wattle
    pygame.draw.ellipse(surf, (220, 30, 30), (cx - sc(8), cy - sc(88), sc(18), sc(22)))

    # Beak
    pts = [(cx - sc(16), cy - sc(95)),
           (cx + sc(16), cy - sc(95)),
           (cx, cy - sc(70))]
    pygame.draw.polygon(surf, (255, 165, 20), pts)
    pygame.draw.line(surf, (200, 120, 10),
                     (cx - sc(16), cy - sc(95)),
                     (cx + sc(16), cy - sc(95)), sc(3))

    # Eyes — angry/determined look
    pygame.draw.ellipse(surf, (255, 255, 255), (cx - sc(26), cy - sc(120), sc(24), sc(20)))
    pygame.draw.ellipse(surf, (255, 255, 255), (cx + sc(2),  cy - sc(120), sc(24), sc(20)))
    pygame.draw.circle(surf, (30, 30, 30),    (cx - sc(15), cy - sc(111)), sc(8))
    pygame.draw.circle(surf, (30, 30, 30),    (cx + sc(13), cy - sc(111)), sc(8))
    pygame.draw.circle(surf, (255, 255, 255), (cx - sc(12), cy - sc(114)), sc(3))
    pygame.draw.circle(surf, (255, 255, 255), (cx + sc(16), cy - sc(114)), sc(3))
    # Angry brow lines
    pygame.draw.line(surf, (80, 40, 0),
                     (cx - sc(28), cy - sc(126)), (cx - sc(8), cy - sc(122)), sc(4))
    pygame.draw.line(surf, (80, 40, 0),
                     (cx + sc(4),  cy - sc(122)), (cx + sc(26), cy - sc(126)), sc(4))

    # Wings — flapping
    flap = int(14 * math.sin(tick * 0.10))
    # Left wing
    wing_pts_l = [
        (cx - sc(72), cy - sc(20)),
        (cx - sc(130), cy - sc(60) + flap),
        (cx - sc(145), cy + sc(10) + flap),
        (cx - sc(100), cy + sc(40)),
    ]
    pygame.draw.polygon(surf, (220, 180, 30), wing_pts_l)
    pygame.draw.polygon(surf, (255, 215, 50), wing_pts_l, sc(3))
    # Right wing
    wing_pts_r = [
        (cx + sc(72), cy - sc(20)),
        (cx + sc(130), cy - sc(60) - flap),
        (cx + sc(145), cy + sc(10) - flap),
        (cx + sc(100), cy + sc(40)),
    ]
    pygame.draw.polygon(surf, (220, 180, 30), wing_pts_r)
    pygame.draw.polygon(surf, (255, 215, 50), wing_pts_r, sc(3))

    # Feet
    for sign in (-1, 1):
        fx = cx + sign * sc(28)
        pygame.draw.line(surf, (255, 165, 20), (fx, cy + sc(62)), (fx + sign * sc(12), cy + sc(95)), sc(7))
        # Three toes
        toe_y = cy + sc(95)
        toe_x = fx + sign * sc(12)
        for tdx in (-sc(18), 0, sc(18)):
            pygame.draw.line(surf, (255, 165, 20), (toe_x, toe_y), (toe_x + tdx, toe_y + sc(16)), sc(5))


def draw_title(surf, cx, y, fonts, tick):
    """'CHICKEN INVADERS 2 - THE NEXT WAVE' title block."""
    wave = int(3 * math.sin(tick * 0.04))

    # "CHICKEN INVADERS 2"
    for line, oy, col, font_key in [
        ("CHICKEN INVADERS 2",  0,   (255, 200, 40), "logo"),
        ("THE  NEXT  WAVE",     145, (120, 200, 255), "sub_title"),
    ]:
        # Drop shadow
        sh = fonts[font_key].render(line, True, (0, 0, 0))
        surf.blit(sh, sh.get_rect(center=(cx + 5, y + oy + 5 + wave)))
        # Outer glow
        for dx, dy in [(-4,0),(4,0),(0,-4),(0,4),(-3,-3),(3,-3),(-3,3),(3,3)]:
            gl = fonts[font_key].render(line, True, (180, 100, 0) if oy == 0 else (40, 80, 180))
            surf.blit(gl, gl.get_rect(center=(cx + dx, y + oy + wave)))
        # Main text
        txt = fonts[font_key].render(line, True, col)
        surf.blit(txt, txt.get_rect(center=(cx, y + oy + wave)))


def draw_menu_button(surf, rect, label, font, hover, tick):
    """CI2-style dark metallic button."""
    r = 18
    # Outer dark frame
    outer_col = (60, 90, 150) if hover else (30, 45, 80)
    pygame.draw.rect(surf, outer_col, rect, border_radius=r)

    # Inner fill — dark metallic gradient approximated
    inner = rect.inflate(-6, -6)
    inner_top    = (25, 35, 70)  if not hover else (40, 60, 110)
    inner_bottom = (10, 15, 35)  if not hover else (20, 35, 70)
    # Top half
    top_half = pygame.Rect(inner.x, inner.y, inner.width, inner.height // 2)
    pygame.draw.rect(surf, inner_top, top_half,
                     border_top_left_radius=r, border_top_right_radius=r)
    # Bottom half
    bot_half = pygame.Rect(inner.x, inner.centery, inner.width, inner.height // 2)
    pygame.draw.rect(surf, inner_bottom, bot_half,
                     border_bottom_left_radius=r, border_bottom_right_radius=r)

    # Top shine strip
    shine_rect = pygame.Rect(inner.x + 12, inner.y + 5, inner.width - 24, inner.height // 4)
    shine = pygame.Surface((shine_rect.w, shine_rect.h), pygame.SRCALPHA)
    shine.fill((255, 255, 255, 28 if not hover else 55))
    surf.blit(shine, shine_rect)

    # Glowing border on hover
    if hover:
        glow_col = (100, 160, 255, 180)
        for thickness in (3, 2, 1):
            gr = rect.inflate(thickness * 2, thickness * 2)
            pygame.draw.rect(surf, (80, 130, 255), gr, width=thickness, border_radius=r + thickness)

    # Label — white with subtle shadow
    sh = font.render(label, True, (0, 0, 0))
    surf.blit(sh, sh.get_rect(center=(rect.centerx + 2, rect.centery + 2)))
    txt = font.render(label, True, (255, 255, 255) if not hover else (180, 220, 255))
    surf.blit(txt, txt.get_rect(center=rect.center))


# ══════════════════════════════════════════════════════════════════════════════
#  Screens
# ══════════════════════════════════════════════════════════════════════════════

class MenuScreen:
    LABELS = ["NEW GAME", "INSTRUCTIONS", "OPTIONS", "EXIT"]
    BTN_W, BTN_H, BTN_GAP = 520, 105, 28

    def __init__(self, fonts):
        self.fonts = fonts
        # Buttons on the LEFT side, vertically centred in lower half
        lx = SCREEN_W // 4 + 20
        start_y = 1160
        self.rects = []
        for i, _ in enumerate(self.LABELS):
            r = pygame.Rect(0, 0, self.BTN_W, self.BTN_H)
            r.centerx = lx
            r.y = start_y + i * (self.BTN_H + self.BTN_GAP)
            self.rects.append(r)

    def handle(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            for i, r in enumerate(self.rects):
                if r.collidepoint(event.pos):
                    return self.LABELS[i]
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            return "EXIT"
        return None

    def draw(self, surf, tick):
        # Nebula glow
        draw_nebula(surf, tick)

        # Title — top centre
        draw_title(surf, SCREEN_W // 2, 120, self.fonts, tick)

        # Chicken — right side, large
        draw_chicken(surf, SCREEN_W * 3 // 4 + 20, 1050, scale=3.2, tick=tick)

        # Buttons — left side
        mx, my = pygame.mouse.get_pos()
        for i, r in enumerate(self.rects):
            draw_menu_button(surf, r, self.LABELS[i], self.fonts["btn"],
                             r.collidepoint(mx, my), tick)

        # Copyright line
        cr = self.fonts["tiny"].render(
            "CrashTech 2026  -  Challenge 8  (inspired by Chicken Invaders 2)",
            True, (100, 120, 160))
        surf.blit(cr, cr.get_rect(center=(SCREEN_W // 2, SCREEN_H - 55)))


class InstructionsScreen:
    LINES = [
        ("INSTRUCTIONS",                      "title"),
        ("",                                   "gap"),
        ("Move your ship to dodge and aim.",   "body"),
        ("Destroy all chickens to advance!",   "body"),
        ("",                                   "gap"),
        ("Joystick       ->  Move ship",       "code"),
        ("KEY[0] / SPACE ->  Shoot",           "code"),
        ("KEY[1] / R     ->  Pause/Restart",   "code"),
        ("",                                   "gap"),
        ("Watch out for falling eggs!",        "body"),
        ("",                                   "gap"),
        ("ESC  ->  Back to menu",              "body"),
    ]

    def __init__(self, fonts):
        self.fonts = fonts
        self.back_rect = pygame.Rect(0, 0, 340, 105)
        self.back_rect.center = (SCREEN_W // 2, SCREEN_H - 140)

    def handle(self, event):
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            return "BACK"
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.back_rect.collidepoint(event.pos):
                return "BACK"
        return None

    def draw(self, surf, tick):
        draw_nebula(surf, tick)
        panel = pygame.Surface((900, 980), pygame.SRCALPHA)
        panel.fill((5, 8, 30, 225))
        pygame.draw.rect(panel, (60, 90, 180), panel.get_rect(), width=3, border_radius=24)
        surf.blit(panel, panel.get_rect(center=(SCREEN_W // 2, SCREEN_H // 2 - 80)))
        y = SCREEN_H // 2 - 510
        for text, kind in self.LINES:
            if kind == "gap":
                y += 20; continue
            if kind == "title":
                s2 = self.fonts["btn"].render(text, True, (255, 200, 40))
            elif kind == "code":
                s2 = self.fonts["mono"].render(text, True, (130, 255, 130))
            else:
                s2 = self.fonts["body"].render(text, True, (210, 225, 255))
            surf.blit(s2, s2.get_rect(center=(SCREEN_W // 2, y)))
            y += s2.get_height() + 18
        mx, my = pygame.mouse.get_pos()
        draw_menu_button(surf, self.back_rect, "BACK", self.fonts["btn"],
                         self.back_rect.collidepoint(mx, my), tick)


class OptionsScreen:
    def __init__(self, fonts):
        self.fonts = fonts
        self.back_rect = pygame.Rect(0, 0, 340, 105)
        self.back_rect.center = (SCREEN_W // 2, SCREEN_H - 140)

    def handle(self, event):
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            return "BACK"
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.back_rect.collidepoint(event.pos):
                return "BACK"
        return None

    def draw(self, surf, tick):
        draw_nebula(surf, tick)
        panel = pygame.Surface((860, 480), pygame.SRCALPHA)
        panel.fill((5, 8, 30, 225))
        pygame.draw.rect(panel, (60, 90, 180), panel.get_rect(), width=3, border_radius=24)
        surf.blit(panel, panel.get_rect(center=(SCREEN_W // 2, SCREEN_H // 2 - 220)))
        t = self.fonts["btn"].render("OPTIONS", True, (255, 200, 40))
        surf.blit(t, t.get_rect(center=(SCREEN_W // 2, SCREEN_H // 2 - 430)))
        n = self.fonts["body"].render("More options coming soon.", True, (200, 215, 255))
        surf.blit(n, n.get_rect(center=(SCREEN_W // 2, SCREEN_H // 2 - 220)))
        mx, my = pygame.mouse.get_pos()
        draw_menu_button(surf, self.back_rect, "BACK", self.fonts["btn"],
                         self.back_rect.collidepoint(mx, my), tick)


# ══════════════════════════════════════════════════════════════════════════════
#  Main
# ══════════════════════════════════════════════════════════════════════════════

def main():
    pygame.init()
    screen = pygame.display.set_mode((SCREEN_W, SCREEN_H), pygame.SCALED | pygame.FULLSCREEN)
    pygame.display.set_caption(TITLE)
    pygame.mouse.set_visible(False)   # hide OS cursor; we draw the fork
    clock = pygame.time.Clock()

    fonts = {
        "logo":      pygame.font.SysFont("impact",   130, bold=True),
        "sub_title": pygame.font.SysFont("impact",    68),
        "btn":       pygame.font.SysFont("consolas",  52, bold=True),
        "body":      pygame.font.SysFont("consolas",  37),
        "mono":      pygame.font.SysFont("consolas",  35),
        "tiny":      pygame.font.SysFont("consolas",  28),
    }

    fork_img    = make_fork_surface(44)
    stars       = StarField(280)
    menu_screen = MenuScreen(fonts)
    instr_screen = InstructionsScreen(fonts)
    opts_screen  = OptionsScreen(fonts)

    current = SCREEN_MENU
    tick    = 0

    running = True
    while running:
        tick += 1
        stars.update()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif current == SCREEN_MENU:
                action = menu_screen.handle(event)
                if action == "NEW GAME":
                    current = SCREEN_GAME
                elif action == "INSTRUCTIONS":
                    current = SCREEN_INSTRUCTIONS
                elif action == "OPTIONS":
                    current = SCREEN_OPTIONS
                elif action == "EXIT":
                    running = False
            elif current == SCREEN_INSTRUCTIONS:
                if instr_screen.handle(event) == "BACK":
                    current = SCREEN_MENU
            elif current == SCREEN_OPTIONS:
                if opts_screen.handle(event) == "BACK":
                    current = SCREEN_MENU
            elif current == SCREEN_GAME:
                if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                    current = SCREEN_MENU

        screen.fill((2, 2, 12))
        stars.draw(screen)

        if current == SCREEN_MENU:
            menu_screen.draw(screen, tick)
        elif current == SCREEN_INSTRUCTIONS:
            instr_screen.draw(screen, tick)
        elif current == SCREEN_OPTIONS:
            opts_screen.draw(screen, tick)
        elif current == SCREEN_GAME:
            draw_nebula(screen, tick)
            msg = fonts["btn"].render("GAME  -  coming next step!", True, (255, 200, 40))
            screen.blit(msg, msg.get_rect(center=(SCREEN_W // 2, SCREEN_H // 2)))
            hint = fonts["body"].render("ESC -> back to menu", True, (180, 200, 240))
            screen.blit(hint, hint.get_rect(center=(SCREEN_W // 2, SCREEN_H // 2 + 120)))

        # Draw fork cursor on top of everything
        mx, my = pygame.mouse.get_pos()
        draw_fork_cursor(screen, fork_img, mx, my)

        pygame.display.flip()
        clock.tick(FPS)

    pygame.quit()
    sys.exit(0)


if __name__ == "__main__":
    main()
