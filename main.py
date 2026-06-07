import pygame
import sys

pygame.init()

WIDTH = 1000
HEIGHT = 600

screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Sword & Wand")

clock = pygame.time.Clock()

MENU = "menu"
STORY = "story"
GAME = "game"
PAUSE = "pause"
OPTIONS = "options"
GAME_OVER = "game_over"

state = MENU

lives = 3
coins = 0

running = True

while running:

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

        if event.type == pygame.KEYDOWN:

            if state == MENU:
                if event.key == pygame.K_RETURN:
                    state = STORY

            elif state == STORY:
                if event.key == pygame.K_RETURN:
                    state = GAME

            elif state == GAME:
                if event.key == pygame.K_ESCAPE:
                    state = PAUSE

            elif state == PAUSE:
                if event.key == pygame.K_ESCAPE:
                    state = GAME

    screen.fill((100, 180, 255))

    if state == MENU:
        draw_menu()

    elif state == STORY:
        draw_story()

    elif state == GAME:
        update_game()

    elif state == PAUSE:
        draw_pause()

    elif state == GAME_OVER:
        draw_game_over()

    pygame.display.flip()
    clock.tick(60)

pygame.quit()
sys.exit()

import pygame

class Player:

    def __init__(self, x, y):

        self.rect = pygame.Rect(x, y, 50, 60)

        self.speed = 5
        self.jump_power = -15

        self.vel_y = 0
        self.gravity = 0.8

        self.on_ground = False

    def update(self):

        keys = pygame.key.get_pressed()

        if keys[pygame.K_LEFT]:
            self.rect.x -= self.speed

        if keys[pygame.K_RIGHT]:
            self.rect.x += self.speed

        if keys[pygame.K_SPACE] and self.on_ground:
            self.vel_y = self.jump_power

        self.vel_y += self.gravity
        self.rect.y += self.vel_y

        if self.rect.bottom >= 500:
            self.rect.bottom = 500
            self.vel_y = 0
            self.on_ground = True

    def draw(self, screen):

        pygame.draw.rect(screen, (255,255,255), self.rect)

import pygame

class Coin:

    def __init__(self, x, y):

        self.rect = pygame.Rect(x, y, 25, 25)

    def draw(self, screen):

        pygame.draw.circle(
            screen,
            (255, 215, 0),
            self.rect.center,
            12
        )

for coin in coins[:]:

    if player.rect.colliderect(coin.rect):

        coins.remove(coin)
        score += 1

#Live system
if player.rect.y > HEIGHT:

    lives -= 1

    player.rect.x = 100
    player.rect.y = 300

if lives <= 0:
    state = GAME_OVER
#pause menu
def draw_pause():

    font = pygame.font.Font(None, 70)

    resume = font.render("Resume", True, (255,255,255))
    restart = font.render("Restart", True, (255,255,255))
    exit_btn = font.render("Exit", True, (255,255,255))

    screen.blit(resume, (350,150))
    screen.blit(restart, (350,250))
    screen.blit(exit_btn, (350,350))

#Game over screen
def draw_game_over():

    font = pygame.font.Font(None, 90)

    title = font.render("GAME OVER", True, (255,0,0))

    screen.blit(title, (250,200))
#HUC hearts coins
def draw_ui():

    font = pygame.font.Font(None, 40)

    hearts = "♥" * lives

    heart_text = font.render(
        hearts,
        True,
        (255,0,0)
    )

    coin_text = font.render(
        f"Coins: {score}",
        True,
        (255,255,0)
    )

    screen.blit(heart_text, (20,20))
    screen.blit(coin_text, (20,60))
#AI example
class Enemy(pygame.sprite.Sprite):

    def __init__(self, x, y):
        super().__init__()

        self.image = pygame.Surface((40, 40))
        self.image.fill((255, 0, 0))

        self.rect = self.image.get_rect(topleft=(x, y))

        self.speed = 2
        self.direction = 1

        self.left_limit = x - 100
        self.right_limit = x + 100

    def update(self):

        self.rect.x += self.speed * self.direction

        if self.rect.x <= self.left_limit:
            self.direction = 1

        if self.rect.x >= self.right_limit:
            self.direction = -1
#sword attack
if keys[pygame.K_z]:

    attack_rect = pygame.Rect(
        player.rect.right,
        player.rect.y,
        50,
        player.rect.height
    )

    for enemy in enemies:
        if attack_rect.colliderect(enemy.rect):
            enemy.kill()
#camera scrolling 
camera_x = player.rect.centerx - WIDTH // 2

for platform in platforms:
    screen.blit(
        platform.image,
        (platform.rect.x - camera_x,
         platform.rect.y)
    )
#parallax background 
bg_x = -(camera_x * 0.3)

screen.blit(background, (bg_x, 0))
#save system 
import json

data = {
    "level": current_level,
    "coins": score,
    "lives": lives
}

with open("save.json", "w") as file:
    json.dump(data, file)
#load
with open("save.json", "r") as file:
    data = json.load(file)

current_level = data["level"]
score = data["coins"]
lives = data["lives"]

#level data
LEVEL_1 = [
    "XXXXXXXXXXXXXXXXXXXXXXXX",
    "X......................X",
    "X......C...............X",
    "X............E.........X",
    "X....P.................X",
    "XXXXXXXXXXXXXXXXXXXXXXXX"
]
#heart system
heart_img = pygame.image.load("assets/heart.png")

for i in range(lives):
    screen.blit(
        heart_img,
        (20 + i * 40, 20)
    )
#victory system 
if current_level == MAX_LEVEL and level_complete:

    state = "victory"
font = pygame.font.Font(None, 90)

text = font.render(
    "YOU WIN!",
    True,
    (255, 255, 0)
)

screen.blit(text, (250, 200))

if lives <= 0:
    state = "game_over"
buttons = [
    "Yes",  # Restart game
    "No"    # Exit to menu
]
#game over
def draw_game_over():

    font = pygame.font.Font(None, 80)

    title = font.render(
        "GAME OVER",
        True,
        (255, 0, 0)
    )

    yes_btn = font.render(
        "Yes",
        True,
        (255, 255, 255)
    )

    no_btn = font.render(
        "No",
        True,
        (255, 255, 255)
    )

    screen.blit(title, (250, 150))
    screen.blit(yes_btn, (320, 300))
    screen.blit(no_btn, (500, 300))

#game over backend
if state == "game_over":

    if event.type == pygame.KEYDOWN:

        if event.key == pygame.K_y:
            restart_game()

        if event.key == pygame.K_n:
            state = "menu"
#game over click able
yes_rect = pygame.Rect(300, 300, 120, 50)
no_rect = pygame.Rect(500, 300, 120, 50)

if event.type == pygame.MOUSEBUTTONDOWN:

    if yes_rect.collidepoint(event.pos):
        restart_game()

    if no_rect.collidepoint(event.pos):
        state = "menu"
#lose condition
lives <= 0

#yes buttom
if yes_button_clicked:
    restart_game()

#no buttom
if no_button_clicked:
    state = "menu"

#patrol Ai
class Enemy(pygame.sprite.Sprite):
    def __init__(self, x, y):
        super().__init__()

        self.image = pygame.Surface((40, 40))
        self.image.fill((255, 0, 0))

        self.rect = self.image.get_rect(topleft=(x, y))

        self.speed = 2
        self.direction = 1

    def update(self):
        self.rect.x += self.speed * self.direction

        if self.rect.x <= 100:
            self.direction = 1

        if self.rect.x >= 300:
            self.direction = -1
