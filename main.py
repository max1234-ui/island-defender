import sys
import math
import random
import pygame
from pygame.math import Vector2

pygame.init()
pygame.mixer.init()

SCREEN_WIDTH, SCREEN_HEIGHT = 1000, 700
screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
display_surface = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
pygame.display.set_caption("Terra Crop Defender - Poobert Turret Defense")
clock = pygame.time.Clock()

font_large = pygame.font.SysFont("arial", 64, bold=True)
font_small = pygame.font.SysFont("arial", 28, bold=True)
font_hud = pygame.font.SysFont("arial", 32, bold=True)
font_chat_bold = pygame.font.SysFont("arial", 26, bold=True)
font_chat = pygame.font.SysFont("arial", 22, bold=False)

try:
    full_splash = pygame.mixer.Sound("assets/splash.ogg")
    raw_bytes = full_splash.get_raw()
    init_res = pygame.mixer.get_init()
    if init_res:
        freq, fmt, channels = init_res
        bytes_per_sample = abs(fmt) // 8
        bytes_per_sec = freq * channels * bytes_per_sample
        bytes_to_cut = int(bytes_per_sec * 0.4)
        if len(raw_bytes) > bytes_to_cut:
            splash_sound = pygame.mixer.Sound(buffer=raw_bytes[bytes_to_cut:])
        else:
            splash_sound = full_splash
    else:
        splash_sound = full_splash
except pygame.error:
    splash_sound = None

try:
    crunch_sound = pygame.mixer.Sound("assets/crunch.ogg")
except pygame.error:
    crunch_sound = None

try:
    boss_sound = pygame.mixer.Sound("assets/boss.ogg")
except pygame.error:
    boss_sound = None

try:
    peep_sound = pygame.mixer.Sound("assets/peep.ogg")
except pygame.error:
    peep_sound = None

try:
    hurt_sound = pygame.mixer.Sound("assets/hurt.ogg")
except pygame.error:
    hurt_sound = None

def load_transparent_image(path, scale_factor=1.0):
    image = pygame.image.load(path).convert()
    image.set_colorkey((255, 255, 255))
    if scale_factor != 1.0:
        new_w = int(image.get_width() * scale_factor)
        new_h = int(image.get_height() * scale_factor)
        image = pygame.transform.scale(image, (new_w, new_h))
    return image

background_img = pygame.image.load("assets/background.png").convert()
background_img = pygame.transform.scale(background_img, (SCREEN_WIDTH, SCREEN_HEIGHT))

try:
    bglocked_img = pygame.image.load("assets/bglocked.png").convert()
    bglocked_img = pygame.transform.scale(bglocked_img, (SCREEN_WIDTH, SCREEN_HEIGHT))
except pygame.error:
    bglocked_img = background_img

crop_img = load_transparent_image("assets/crop.png", 0.5)
rat_img = load_transparent_image("assets/rat.png", 1.0)
trap_img = load_transparent_image("assets/trap.png", 0.5)
poobert_img = load_transparent_image("assets/poobert.png", 0.6)
splash_img = load_transparent_image("assets/splash.png", 0.5)

try:
    crumb_img = load_transparent_image("assets/crumb.png", 0.4)
except pygame.error:
    crumb_img = None

carriage_raw = pygame.image.load("assets/ratticus_carriage.png").convert()
carriage_raw.set_colorkey((255, 255, 255))
carriage_img = pygame.transform.scale(carriage_raw, (160, 110))

ratticus_raw = pygame.image.load("assets/ratticus.png").convert()
ratticus_raw.set_colorkey((255, 255, 255))
ratticus_boss_img = pygame.transform.scale(ratticus_raw, (110, 110))

try:
    ratticus_dead_raw = pygame.image.load("assets/ratticusdead.png").convert()
    ratticus_dead_raw.set_colorkey((255, 255, 255))
    ratticus_dead_img = pygame.transform.scale(ratticus_dead_raw, (110, 110))
except pygame.error:
    ratticus_dead_img = ratticus_boss_img

try:
    ratticus2_raw = pygame.image.load("assets/ratticus2.png").convert()
    ratticus2_raw.set_colorkey((255, 255, 255))
    ratticus2_img = pygame.transform.scale(ratticus2_raw, (140, 140))
except pygame.error:
    ratticus2_img = ratticus_boss_img

FARM_CENTER_X, FARM_CENTER_Y = 238, 327
TURRET_POS = Vector2(FARM_CENTER_X - 160, FARM_CENTER_Y)
TOP_RIGHT_EXIT = Vector2(SCREEN_WIDTH + 20, -20)

CROPS_GRID = []
for r in range(-2, 2):
    for c in range(-1, 2):
        CROPS_GRID.append(Vector2(FARM_CENTER_X + c * 45, FARM_CENTER_Y + r * 45))

occupied_crops = set()

class CrumbFX:
    def __init__(self, pos):
        self.particles = []
        for _ in range(5):
            vel = Vector2(random.uniform(-2.5, 2.5), random.uniform(-2.5, 2.5))
            self.particles.append({'pos': Vector2(pos), 'vel': vel, 'timer': random.randint(300, 500)})

    def update(self, dt):
        for p in self.particles:
            p['pos'] += p['vel']
            p['timer'] -= dt
        self.particles = [p for p in self.particles if p['timer'] > 0]

    def draw(self, surface):
        if crumb_img:
            for p in self.particles:
                rect = crumb_img.get_rect(center=(int(p['pos'].x), int(p['pos'].y)))
                surface.blit(crumb_img, rect)

class MiniRatticus:
    def __init__(self, target_crop, current_survival_time):
        self.pos = Vector2(SCREEN_WIDTH + 20, random.randint(150, 550))
        self.target = target_crop
        self.target_key = (target_crop.x, target_crop.y) if target_crop else None
        
        base_speed = 1.3
        time_factor = min(current_survival_time / 60000.0, 1.0)
        speed_multiplier = random.uniform(1.0, 1.0 + (time_factor * 3.5))
        self.speed = base_speed * speed_multiplier
        
        self.state = "APPROACHING"
        self.eat_timer = 2000

    def get_rect(self):
        return rat_img.get_rect(center=(int(self.pos.x), int(self.pos.y)))

    def update(self, dt, crumbs_list):
        if self.state == "APPROACHING":
            direction = (self.target - self.pos)
            if direction.length() <= self.speed:
                self.pos = Vector2(self.target)
                self.state = "EATING"
            else:
                self.pos += direction.normalize() * self.speed

        elif self.state == "EATING":
            self.eat_timer -= dt
            if self.eat_timer <= 0:
                if self.target in CROPS_GRID:
                    crumbs_list.append(CrumbFX(self.target))
                    CROPS_GRID.remove(self.target)
                    if crunch_sound:
                        crunch_sound.play()
                if self.target_key in occupied_crops:
                    occupied_crops.remove(self.target_key)
                self.target = TOP_RIGHT_EXIT
                self.state = "FLEEING"

        elif self.state == "FLEEING":
            direction = (self.target - self.pos)
            if direction.length() <= self.speed:
                return False
            self.pos += direction.normalize() * self.speed
        return True

    def draw(self, surface):
        rect = self.get_rect()
        surface.blit(rat_img, rect)

class MouseTrap:
    def __init__(self, start_pos, target_pos):
        self.pos = Vector2(start_pos)
        self.target = Vector2(target_pos)
        self.speed = 9.0
        self.active = True

    def get_rect(self):
        return trap_img.get_rect(center=(int(self.pos.x), int(self.pos.y)))

    def update(self):
        direction = (self.target - self.pos)
        if direction.length() <= self.speed:
            self.pos = Vector2(self.target)
            self.active = False
        else:
            self.pos += direction.normalize() * self.speed

    def draw(self, surface):
        rect = self.get_rect()
        surface.blit(trap_img, rect)

class SplashFX:
    def __init__(self, pos):
        self.pos = Vector2(pos)
        self.timer = 500

    def update(self, dt):
        self.timer -= dt

    def draw(self, surface):
        rect = splash_img.get_rect(center=(int(self.pos.x), int(self.pos.y)))
        surface.blit(splash_img, rect)

class PoobertTurret:
    def __init__(self, pos):
        self.pos = Vector2(pos)
        self.angle = 0

    def update(self, mouse_pos):
        direction = Vector2(mouse_pos) - self.pos
        if direction.length() > 0:
            self.angle = math.degrees(math.atan2(-direction.y, direction.x))

    def draw(self, surface):
        rotated_poobert = pygame.transform.rotate(poobert_img, self.angle)
        rect = rotated_poobert.get_rect(center=(int(self.pos.x), int(self.pos.y)))
        surface.blit(rotated_poobert, rect)

def reset_game():
    global CROPS_GRID, occupied_crops, rats, traps, splashes, crumbs, army_rats
    global spawn_timer, survival_time, win, game_state, fire_cooldown
    global intro_x, intro_transform, intro_transform_timer, playing_intro_timer
    global boss_pos, boss_retreating, boss_hp, boss_max_hp, boss_eat_timer

    if boss_sound:
        boss_sound.stop()

    CROPS_GRID = [Vector2(FARM_CENTER_X + c * 45, FARM_CENTER_Y + r * 45) for r in range(-2, 2) for c in range(-1, 2)]
    occupied_crops = set()
    rats = []
    traps = []
    splashes = []
    crumbs = []
    army_rats = []
    spawn_timer = 0
    survival_time = 0
    fire_cooldown = 0
    win = False
    game_state = "INTRO_SLIDE"
    intro_x = SCREEN_WIDTH + 160
    intro_transform = False
    intro_transform_timer = 1200
    playing_intro_timer = 0
    boss_pos = Vector2(SCREEN_WIDTH - 150, 350)
    boss_retreating = False
    boss_hp = 20
    boss_max_hp = 20
    boss_eat_timer = 1000

turret = PoobertTurret(TURRET_POS)
rats = []
traps = []
splashes = []
crumbs = []
army_rats = []
spawn_timer = 0
survival_time = 0
fire_cooldown = 0
win = False

game_state = "INTRO_SLIDE"
intro_x = SCREEN_WIDTH + 160
intro_y = 350
intro_target_x = SCREEN_WIDTH - 150
intro_speed = 3.0
intro_transform = False
intro_transform_timer = 1200
playing_intro_timer = 0

boss_pos = Vector2(intro_target_x, intro_y)
boss_retreating = False
boss_hp = 20
boss_max_hp = 20
boss_eat_timer = 1000

opt1_rect = pygame.Rect(380, 580, 250, 45)
opt2_rect = pygame.Rect(650, 580, 250, 45)

running = True
while running:
    dt = clock.tick(60)
    mouse_pos = pygame.mouse.get_pos()
    shake_x, shake_y = 0, 0

    if fire_cooldown > 0:
        fire_cooldown -= dt

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
            
        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_r:
                reset_game()

        elif event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1:
                if game_state == "INTRO_DIALOGUE":
                    if opt1_rect.collidepoint(mouse_pos):
                        game_state = "PLAYING"
                        playing_intro_timer = 3500
                        boss_retreating = True
                        boss_pos = Vector2(intro_target_x, intro_y)
                        if peep_sound:
                            peep_sound.play()
                    elif opt2_rect.collidepoint(mouse_pos):
                        win = True
                        game_state = "VICTORY"
                elif game_state == "BOSS_DIALOGUE":
                    game_state = "BOSS_MARCH"
                    if boss_sound:
                        boss_sound.play(loops=-1)
                elif game_state in ("PLAYING", "BOSS_MARCH"):
                    if fire_cooldown <= 0:
                        traps.append(MouseTrap(turret.pos, mouse_pos))
                        fire_cooldown = 1000
                        if splash_sound:
                            splash_sound.play()

    if game_state == "INTRO_SLIDE":
        intro_x -= intro_speed
        if intro_x <= intro_target_x:
            intro_x = intro_target_x
            game_state = "INTRO_TRANSFORM"
            intro_transform_timer = 1200

    elif game_state == "INTRO_TRANSFORM":
        intro_transform_timer -= dt
        if intro_transform_timer <= 0:
            intro_transform = True
            game_state = "INTRO_DIALOGUE"
            boss_pos = Vector2(intro_target_x, intro_y)
            if peep_sound:
                peep_sound.play()

    elif game_state == "PLAYING":
        spawn_timer += dt
        survival_time += dt

        if survival_time >= 60000:
            game_state = "BOSS_DIALOGUE"
            if peep_sound:
                peep_sound.play()
            for rat in rats:
                rat.state = "FLEEING"
                rat.target = Vector2(SCREEN_WIDTH + 50, rat.pos.y)
            army_rats = [Vector2(SCREEN_WIDTH - 60, 100 + i * 55) for i in range(10)]

        if playing_intro_timer > 0:
            playing_intro_timer -= dt
            if playing_intro_timer <= 1500:
                shake_x = random.randint(-8, 8)
                shake_y = random.randint(-8, 8)

        if boss_retreating:
            direction = (TOP_RIGHT_EXIT - boss_pos)
            if direction.length() <= 4.0:
                boss_retreating = False
            else:
                boss_pos += direction.normalize() * 4.0

        turret.update(mouse_pos)

        if len(CROPS_GRID) == 0:
            game_state = "GAME_OVER"

        available_crops = [c for c in CROPS_GRID if (c.x, c.y) not in occupied_crops]
        if spawn_timer > 1100 and available_crops:
            chosen_crop = random.choice(available_crops)
            occupied_crops.add((chosen_crop.x, chosen_crop.y))
            rats.append(MiniRatticus(chosen_crop, survival_time))
            spawn_timer = 0

        for rat in rats[:]:
            still_active = rat.update(dt, crumbs)
            if not still_active:
                rats.remove(rat)

        for trap in traps[:]:
            trap.update()
            if not trap.active:
                traps.remove(trap)
                continue
                
            trap_rect = trap.get_rect()
            hit = False
            for rat in rats[:]:
                rat_rect = rat.get_rect()
                if trap_rect.colliderect(rat_rect):
                    splashes.append(SplashFX(rat.pos))
                    if rat.state != "FLEEING" and rat.target_key in occupied_crops:
                        occupied_crops.remove(rat.target_key)
                    rats.remove(rat)
                    hit = True
                    break
            if hit:
                traps.remove(trap)

        for splash in splashes[:]:
            splash.update(dt)
            if splash.timer <= 0:
                splashes.remove(splash)

        for crumb_fx in crumbs[:]:
            crumb_fx.update(dt)
            if not crumb_fx.particles:
                crumbs.remove(crumb_fx)

    elif game_state == "BOSS_MARCH":
        turret.update(mouse_pos)
        
        for rat in rats[:]:
            still_active = rat.update(dt, crumbs)
            if not still_active:
                rats.remove(rat)
        
        if len(CROPS_GRID) > 0:
            boss_target = CROPS_GRID[0]
            direction = (boss_target - boss_pos)
            
            if direction.length() <= 1.5:
                boss_pos = Vector2(boss_target)
                boss_eat_timer -= dt
                if boss_eat_timer <= 0:
                    removed_crop = CROPS_GRID.pop(0)
                    crumbs.append(CrumbFX(removed_crop))
                    key = (removed_crop.x, removed_crop.y)
                    if key in occupied_crops:
                        occupied_crops.remove(key)
                    boss_eat_timer = 1000
                    if crunch_sound:
                        crunch_sound.play()
            else:
                boss_pos += direction.normalize() * 1.0
        else:
            boss_target = TURRET_POS
            direction = (boss_target - boss_pos)
            
            if direction.length() <= 1.5:
                game_state = "GAME_OVER"
                if boss_sound:
                    boss_sound.stop()
            else:
                boss_pos += direction.normalize() * 1.0

        boss_rect = ratticus_boss_img.get_rect(center=(int(boss_pos.x), int(boss_pos.y)))

        for trap in traps[:]:
            trap.update()
            if not trap.active:
                traps.remove(trap)
                continue

            trap_rect = trap.get_rect()
            
            hit = False
            for rat in rats[:]:
                rat_rect = rat.get_rect()
                if trap_rect.colliderect(rat_rect):
                    splashes.append(SplashFX(rat.pos))
                    rats.remove(rat)
                    hit = True
                    break
            
            if hit:
                traps.remove(trap)
                continue

            if trap_rect.colliderect(boss_rect):
                boss_hp -= 1
                traps.remove(trap)
                if hurt_sound:
                    hurt_sound.play()
                if boss_hp <= 0:
                    game_state = "VICTORY"
                    if boss_sound:
                        boss_sound.stop()

        for splash in splashes[:]:
            splash.update(dt)
            if splash.timer <= 0:
                splashes.remove(splash)

        for crumb_fx in crumbs[:]:
            crumb_fx.update(dt)
            if not crumb_fx.particles:
                crumbs.remove(crumb_fx)

    display_surface.blit(background_img, (0, 0))

    if game_state in ("PLAYING", "GAME_OVER", "BOSS_DIALOGUE", "BOSS_MARCH", "VICTORY"):
        for crop_pos in CROPS_GRID:
            crop_rect = crop_img.get_rect(center=(int(crop_pos.x), int(crop_pos.y)))
            display_surface.blit(crop_img, crop_rect)

        turret.draw(display_surface)

        for rat in rats:
            rat.draw(display_surface)

        for trap in traps:
            trap.draw(display_surface)

        for splash in splashes:
            splash.draw(display_surface)

        for crumb_fx in crumbs:
            crumb_fx.draw(display_surface)

    if game_state in ("BOSS_DIALOGUE", "BOSS_MARCH", "VICTORY"):
        for army_pos in army_rats:
            a_rect = rat_img.get_rect(center=(int(army_pos.x), int(army_pos.y)))
            display_surface.blit(rat_img, a_rect)

    if game_state == "VICTORY":
        if boss_hp <= 0:
            dead_rect = ratticus_dead_img.get_rect(center=(int(boss_pos.x), int(boss_pos.y)))
            display_surface.blit(ratticus_dead_img, dead_rect)
        elif intro_transform:
            b_rect = ratticus_boss_img.get_rect(center=(int(boss_pos.x), int(boss_pos.y)))
            display_surface.blit(ratticus_boss_img, b_rect)
    elif intro_transform and (game_state not in ("PLAYING", "INTRO_SLIDE", "INTRO_TRANSFORM", "INTRO_DIALOGUE") or playing_intro_timer > 0):
        b_rect = ratticus_boss_img.get_rect(center=(int(boss_pos.x), int(boss_pos.y)))
        display_surface.blit(ratticus_boss_img, b_rect)

        if game_state == "BOSS_MARCH":
            bar_w = 80
            bar_h = 10
            bar_x = boss_pos.x - bar_w // 2
            bar_y = boss_pos.y - 65
            pygame.draw.rect(display_surface, (50, 50, 50), (bar_x, bar_y, bar_w, bar_h))
            fill_w = int(bar_w * (boss_hp / boss_max_hp))
            pygame.draw.rect(display_surface, (220, 40, 40), (bar_x, bar_y, fill_w, bar_h))
            pygame.draw.rect(display_surface, (255, 255, 255), (bar_x, bar_y, bar_w, bar_h), 2)

    if game_state == "PLAYING":
        seconds_survived = min(survival_time // 1000, 60)
        timer_text = font_hud.render(f"TIME: {seconds_survived}s / 60s", True, (255, 255, 255))
        
        hud_bg = pygame.Surface((timer_text.get_width() + 20, timer_text.get_height() + 10), pygame.SRCALPHA)
        hud_bg.fill((0, 0, 0, 150))
        display_surface.blit(hud_bg, (15, 15))
        display_surface.blit(timer_text, (25, 20))

        if playing_intro_timer > 0:
            box_rect = pygame.Rect(50, 480, 900, 170)
            box_surface = pygame.Surface((box_rect.width, box_rect.height), pygame.SRCALPHA)
            box_surface.fill((252, 243, 227))
            display_surface.blit(box_surface, (box_rect.x, box_rect.y))
            pygame.draw.rect(display_surface, (84, 53, 31), box_rect, 5, border_radius=16)

            title_bg = pygame.Rect(75, 452, 160, 40)
            title_surface = pygame.Surface((title_bg.width, title_bg.height), pygame.SRCALPHA)
            title_surface.fill((124, 73, 40))
            display_surface.blit(title_surface, (title_bg.x, title_bg.y))
            pygame.draw.rect(display_surface, (84, 53, 31), title_bg, 4, border_radius=8)

            name_text = font_chat_bold.render("Ratticus", True, (255, 255, 255))
            name_rect = name_text.get_rect(center=title_bg.center)
            display_surface.blit(name_text, name_rect)

            line1 = font_chat.render("Then you will have to defeat me...", True, (40, 20, 10))
            display_surface.blit(line1, (80, 508))

            if playing_intro_timer <= 1500:
                line2 = font_large.render("...AND MY ARMY!!!", True, (200, 40, 40))
                display_surface.blit(line2, (80, 545))

            r2_rect = ratticus2_img.get_rect(center=(box_rect.right - 90, box_rect.centery))
            display_surface.blit(ratticus2_img, r2_rect)

    elif game_state in ("INTRO_SLIDE", "INTRO_TRANSFORM", "INTRO_DIALOGUE"):
        if not intro_transform:
            carriage_rect = carriage_img.get_rect(center=(int(intro_x), int(intro_y)))
            display_surface.blit(carriage_img, carriage_rect)

        if game_state == "INTRO_DIALOGUE":
            box_rect = pygame.Rect(50, 480, 900, 170)
            box_surface = pygame.Surface((box_rect.width, box_rect.height), pygame.SRCALPHA)
            box_surface.fill((252, 243, 227))
            display_surface.blit(box_surface, (box_rect.x, box_rect.y))
            pygame.draw.rect(display_surface, (84, 53, 31), box_rect, 5, border_radius=16)

            title_bg = pygame.Rect(75, 452, 160, 40)
            title_surface = pygame.Surface((title_bg.width, title_bg.height), pygame.SRCALPHA)
            title_surface.fill((124, 73, 40))
            display_surface.blit(title_surface, (title_bg.x, title_bg.y))
            pygame.draw.rect(display_surface, (84, 53, 31), title_bg, 4, border_radius=8)

            name_text = font_chat_bold.render("Ratticus", True, (255, 255, 255))
            name_rect = name_text.get_rect(center=title_bg.center)
            display_surface.blit(name_text, name_rect)

            line1 = font_chat.render("You owe me 2 weeks of rent!", True, (40, 20, 10))
            line2 = font_chat.render("It is now time to pay up...", True, (40, 20, 10))
            display_surface.blit(line1, (80, 508))
            display_surface.blit(line2, (80, 538))

            r2_rect = ratticus2_img.get_rect(center=(box_rect.right - 90, box_rect.centery))
            display_surface.blit(ratticus2_img, r2_rect)

            color_opt1 = (220, 180, 140) if opt1_rect.collidepoint(mouse_pos) else (194, 154, 114)
            pygame.draw.rect(display_surface, color_opt1, opt1_rect, border_radius=8)
            pygame.draw.rect(display_surface, (84, 53, 31), opt1_rect, 3, border_radius=8)
            text_opt1 = font_chat_bold.render("No, Ratticus, go away!", True, (84, 53, 31))
            t1_rect = text_opt1.get_rect(center=opt1_rect.center)
            display_surface.blit(text_opt1, t1_rect)

            color_opt2 = (220, 180, 140) if opt2_rect.collidepoint(mouse_pos) else (194, 154, 114)
            pygame.draw.rect(display_surface, color_opt2, opt2_rect, border_radius=8)
            pygame.draw.rect(display_surface, (84, 53, 31), opt2_rect, 3, border_radius=8)
            text_opt2 = font_chat_bold.render("Ok, I will pay", True, (84, 53, 31))
            t2_rect = text_opt2.get_rect(center=opt2_rect.center)
            display_surface.blit(text_opt2, t2_rect)

    elif game_state == "BOSS_DIALOGUE":
        box_rect = pygame.Rect(50, 480, 900, 170)
        box_surface = pygame.Surface((box_rect.width, box_rect.height), pygame.SRCALPHA)
        box_surface.fill((252, 243, 227))
        display_surface.blit(box_surface, (box_rect.x, box_rect.y))
        pygame.draw.rect(display_surface, (84, 53, 31), box_rect, 5, border_radius=16)

        title_bg = pygame.Rect(75, 452, 160, 40)
        title_surface = pygame.Surface((title_bg.width, title_bg.height), pygame.SRCALPHA)
        title_surface.fill((124, 73, 40))
        display_surface.blit(title_surface, (title_bg.x, title_bg.y))
        pygame.draw.rect(display_surface, (84, 53, 31), title_bg, 4, border_radius=8)

        name_text = font_chat_bold.render("Ratticus", True, (255, 255, 255))
        name_rect = name_text.get_rect(center=title_bg.center)
        display_surface.blit(name_text, name_rect)

        l1 = font_chat.render("So you are resisting...", True, (40, 20, 10))
        l2 = font_large.render("How about THIS!", True, (200, 40, 40))
        display_surface.blit(l1, (80, 505))
        display_surface.blit(l2, (80, 540))

        r2_rect = ratticus2_img.get_rect(center=(box_rect.right - 90, box_rect.centery))
        display_surface.blit(ratticus2_img, r2_rect)

        text_click = font_chat.render("(Click anywhere to fight!)", True, (120, 80, 50))
        display_surface.blit(text_click, (620, 615))

    elif game_state == "GAME_OVER":
        display_surface.blit(bglocked_img, (0, 0))

        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 140))
        display_surface.blit(overlay, (0, 0))

        text_title = font_large.render("You LOST", True, (220, 40, 40))
        title_rect = text_title.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 - 50))
        display_surface.blit(text_title, title_rect)

        text_sub = font_small.render("Your island has been retaken by Ratticus! Next time pay your rent", True, (240, 240, 240))
        sub_rect = text_sub.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 + 10))
        display_surface.blit(text_sub, sub_rect)

        final_seconds = survival_time // 1000
        text_score = font_small.render(f"You survived for {final_seconds} seconds!", True, (255, 215, 0))
        score_rect = text_score.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 + 60))
        display_surface.blit(text_score, score_rect)
        
        text_restart = font_chat.render("Press 'R' to restart", True, (200, 200, 200))
        restart_rect = text_restart.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 + 120))
        display_surface.blit(text_restart, restart_rect)

    elif game_state == "VICTORY":
        if boss_hp <= 0:
            title_str = "VICTORY!"
            sub_str = "You kept your island away from Ratticus's hands!"
        else:
            title_str = "RENT PAID"
            sub_str = "You kept your island by settling your accounts!"

        text_title = font_large.render(title_str, True, (50, 220, 50))
        title_rect = text_title.get_rect(center=(SCREEN_WIDTH // 2, 120))
        display_surface.blit(text_title, title_rect)

        text_sub = font_small.render(sub_str, True, (240, 240, 240))
        sub_rect = text_sub.get_rect(center=(SCREEN_WIDTH // 2, 180))
        display_surface.blit(text_sub, sub_rect)

        text_restart = font_chat.render("Press 'R' to restart", True, (200, 200, 200))
        restart_rect = text_restart.get_rect(center=(SCREEN_WIDTH // 2, 230))
        display_surface.blit(text_restart, restart_rect)

    screen.fill((0, 0, 0))
    screen.blit(display_surface, (shake_x, shake_y))
    pygame.display.flip()

pygame.quit()
sys.exit()