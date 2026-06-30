import pygame
import math
import random
import sys

pygame.init()


WIDTH, HEIGHT = 800, 600
FPS = 50

BLUE = (100, 100, 255)
WHITE = (255, 255, 255)
BLACK = (20, 20, 20)
YELLOW = (255, 215, 0)
GREEN = (60, 200, 100)
RED = (200, 0, 0)
GRAY = (60, 60, 70)
LIGHT_GRAY = (100, 100, 115)

SURVIVE_SECONDS = 60          
ENEMY_SPAWN_BASE_MS = 1400    
ENEMY_SPAWN_MIN_MS = 350      

window = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Top-Down Shooter")

font_big = pygame.font.SysFont(None, 64)
font_med = pygame.font.SysFont(None, 40)
font_small = pygame.font.SysFont(None, 28)

clock = pygame.time.Clock()



def draw_text(surface, text, font, color, x, y, center=True):
    """Single reusable text-drawing function (avoids repeated render/blit code)."""
    rendered = font.render(text, True, color)
    rect = rendered.get_rect()
    if center:
        rect.center = (x, y)
    else:
        rect.topleft = (x, y)
    surface.blit(rendered, rect)
    return rect


class Button:
    """Reusable clickable button (used in menu and end screen)."""

    def __init__(self, x, y, width, height, text, base_color=GRAY, hover_color=LIGHT_GRAY):
        self.rect = pygame.Rect(x - width // 2, y - height // 2, width, height)
        self.text = text
        self.base_color = base_color
        self.hover_color = hover_color

    def draw(self, surface):
        mouse_pos = pygame.mouse.get_pos()
        color = self.hover_color if self.rect.collidepoint(mouse_pos) else self.base_color
        pygame.draw.rect(surface, color, self.rect, border_radius=10)
        pygame.draw.rect(surface, WHITE, self.rect, width=2, border_radius=10)
        draw_text(surface, self.text, font_med, WHITE, self.rect.centerx, self.rect.centery)

    def is_clicked(self, event):
        return (
            event.type == pygame.MOUSEBUTTONDOWN
            and event.button == 1
            and self.rect.collidepoint(event.pos)
        )



class Bullet:
    def __init__(self, x, y, angle):
        self.x = x
        self.y = y
        self.radius = 5
        self.speed = 10
        self.angle = angle
        self.color = YELLOW

    def update(self):
        self.x += math.cos(self.angle) * self.speed
        self.y += math.sin(self.angle) * self.speed

    def draw(self):
        pygame.draw.circle(window, self.color, (int(self.x), int(self.y)), self.radius)

    def get_rect(self):
        return pygame.Rect(self.x - self.radius, self.y - self.radius,
                            self.radius * 2, self.radius * 2)

    def off_screen(self):
        return self.x < 0 or self.x > WIDTH or self.y < 0 or self.y > HEIGHT


class Enemy:
    def __init__(self, speed=2):
        side = random.choice(["top", "bottom", "left", "right"])
        if side == "top":
            self.x, self.y = random.randint(0, WIDTH), -20
        elif side == "bottom":
            self.x, self.y = random.randint(0, WIDTH), HEIGHT + 20
        elif side == "left":
            self.x, self.y = -20, random.randint(0, HEIGHT)
        else:
            self.x, self.y = WIDTH + 20, random.randint(0, HEIGHT)

        self.radius = 18
        self.speed = speed
        self.color = RED

    def update(self, target_x, target_y):
        dx = target_x - self.x
        dy = target_y - self.y
        distance = math.hypot(dx, dy)
        if distance != 0:
            dx, dy = dx / distance, dy / distance
            self.x += dx * self.speed
            self.y += dy * self.speed

    def draw(self):
        pygame.draw.circle(window, self.color, (int(self.x), int(self.y)), self.radius)

    def get_rect(self):
        return pygame.Rect(self.x - self.radius, self.y - self.radius,
                            self.radius * 2, self.radius * 2)


class Player:
    def __init__(self):
        self.x = WIDTH // 2
        self.y = HEIGHT // 2
        self.speed = 4
        self.radius = 16
        self.color = (100, 200, 255)
        self.health = 100

    def update(self):
        keys = pygame.key.get_pressed()
        if keys[pygame.K_w]:
            self.y -= self.speed
        if keys[pygame.K_s]:
            self.y += self.speed
        if keys[pygame.K_a]:
            self.x -= self.speed
        if keys[pygame.K_d]:
            self.x += self.speed

        self.x = max(self.radius, min(WIDTH - self.radius, self.x))
        self.y = max(self.radius, min(HEIGHT - self.radius, self.y))

    def get_angle(self):
        mx, my = pygame.mouse.get_pos()
        return math.atan2(my - self.y, mx - self.x)

    def draw(self):
        angle = self.get_angle()
        tip = (self.x + math.cos(angle) * self.radius,
               self.y + math.sin(angle) * self.radius)
        left = (self.x + math.cos(angle + 2.4) * self.radius * 0.7,
                self.y + math.sin(angle + 2.4) * self.radius * 0.7)
        right = (self.x + math.cos(angle - 2.4) * self.radius * 0.7,
                 self.y + math.sin(angle - 2.4) * self.radius * 0.7)
        pygame.draw.polygon(window, self.color, [tip, left, right])

    def get_rect(self):
        return pygame.Rect(self.x - self.radius, self.y - self.radius,
                            self.radius * 2, self.radius * 2)



class Game:
    """Holds all run-time state. Re-created on every restart so nothing leaks
    between play sessions (clean state, no repeated reset code)."""

    def __init__(self):
        self.player = Player()
        self.bullets = []
        self.enemies = [Enemy() for _ in range(3)]
        self.score = 0
        self.start_ticks = pygame.time.get_ticks()
        self.last_spawn = pygame.time.get_ticks()

    def elapsed_seconds(self):
        return (pygame.time.get_ticks() - self.start_ticks) / 1000

    def seconds_left(self):
        return max(0, SURVIVE_SECONDS - self.elapsed_seconds())

    def current_spawn_interval(self):
       
        decay = self.elapsed_seconds() * 20
        return max(ENEMY_SPAWN_MIN_MS, ENEMY_SPAWN_BASE_MS - decay)

    def maybe_spawn_enemy(self):
        now = pygame.time.get_ticks()
        if now - self.last_spawn >= self.current_spawn_interval():
            enemy_speed = 2 + self.elapsed_seconds() / 30  
            self.enemies.append(Enemy(speed=enemy_speed))
            self.last_spawn = now

    def update(self):
        self.player.update()
        self.maybe_spawn_enemy()

        for bullet in self.bullets[:]:
            bullet.update()
            if bullet.off_screen():
                self.bullets.remove(bullet)

        for enemy in self.enemies[:]:
            enemy.update(self.player.x, self.player.y)

            if enemy.get_rect().colliderect(self.player.get_rect()):
                self.player.health -= 1

            for bullet in self.bullets[:]:
                if bullet.get_rect().colliderect(enemy.get_rect()):
                    if bullet in self.bullets:
                        self.bullets.remove(bullet)
                    if enemy in self.enemies:
                        self.enemies.remove(enemy)
                    self.score += 10
                    break

    def draw(self):
        window.fill(BLUE)
        self.player.draw()
        for bullet in self.bullets:
            bullet.draw()
        for enemy in self.enemies:
            enemy.draw()

        draw_text(window, f"Health: {self.player.health}", font_small, WHITE, 80, 25, center=True)
        draw_text(window, f"Score: {self.score}", font_small, WHITE, 80, 60, center=True)
        draw_text(window, f"Time left: {int(self.seconds_left())}s", font_small, WHITE, WIDTH - 100, 25)

    def is_won(self):
        return self.elapsed_seconds() >= SURVIVE_SECONDS

    def is_lost(self):
        return self.player.health <= 0



def draw_menu_screen(high_score):
    window.fill(BLACK)
    draw_text(window, "TOP-DOWN SHOOTER", font_big, WHITE, WIDTH // 2, 140)
    draw_text(window, "Survive 60 seconds. WASD to move, mouse to aim, click to shoot.",
              font_small, WHITE, WIDTH // 2, 210)
    if high_score > 0:
        draw_text(window, f"High Score: {high_score}", font_small, YELLOW, WIDTH // 2, 245)


def draw_end_screen(won, score, high_score):
    window.fill(BLACK)
    if won:
        draw_text(window, "YOU WIN!", font_big, GREEN, WIDTH // 2, 150)
    else:
        draw_text(window, "GAME OVER", font_big, RED, WIDTH // 2, 150)

    draw_text(window, f"Final Score: {score}", font_med, WHITE, WIDTH // 2, 220)
    draw_text(window, f"High Score: {high_score}", font_small, YELLOW, WIDTH // 2, 260)



def main():
    state = "MENU"
    game = None
    high_score = 0
    last_won = False

    play_button = Button(WIDTH // 2, 350, 220, 60, "Play")
    restart_button = Button(WIDTH // 2, 380, 220, 55, "Restart")
    menu_button = Button(WIDTH // 2, 450, 220, 55, "Main Menu")

    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            elif state == "MENU":
                if play_button.is_clicked(event) or (
                    event.type == pygame.KEYDOWN and event.key == pygame.K_SPACE
                ):
                    game = Game()
                    state = "PLAYING"

            elif state == "PLAYING":
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    angle = game.player.get_angle()
                    game.bullets.append(Bullet(game.player.x, game.player.y, angle))

            elif state == "END":
                if restart_button.is_clicked(event):
                    game = Game()
                    state = "PLAYING"
                elif menu_button.is_clicked(event):
                    state = "MENU"

   
        if state == "MENU":
            draw_menu_screen(high_score)
            play_button.draw(window)

        elif state == "PLAYING":
            game.update()
            game.draw()

            if game.is_won() or game.is_lost():
                last_won = game.is_won()
                high_score = max(high_score, game.score)
                state = "END"

        elif state == "END":
            draw_end_screen(last_won, game.score, high_score)
            restart_button.draw(window)
            menu_button.draw(window)

        pygame.display.update()
        clock.tick(FPS)

    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    main()
