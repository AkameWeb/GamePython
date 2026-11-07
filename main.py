import pygame
import sqlite3
import random
import sys

# --- Константы ---
WIDTH, HEIGHT = 800, 600
FPS = 60
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
BLUE = (0, 100, 255)
GREEN = (0, 255, 0)
RED = (255, 0, 0)
GRAY = (200, 200, 200)


# --- Класс для работы с БД (Требование 6 и 7) ---
class DatabaseManager:
    def __init__(self, db_name="game_scores.db"):
        self.conn = sqlite3.connect(db_name)
        self.cursor = self.conn.cursor()
        # Создаем таблицу, если её нет
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS leaderboard (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                score INTEGER NOT NULL
            )
        ''')
        self.conn.commit()

    def save_score(self, name, score):
        self.cursor.execute("INSERT INTO leaderboard (name, score) VALUES (?, ?)", (name, score))
        self.conn.commit()

    def get_top_5(self):
        self.cursor.execute("SELECT name, score FROM leaderboard ORDER BY score DESC LIMIT 5")
        return self.cursor.fetchall()


# --- Класс главного персонажа (Требование 1 и 7) ---
class Player:
    def __init__(self, x, y):
        self.rect = pygame.Rect(x, y, 50, 50)
        self.speed = 7
        self.lives = 3

    def move(self, keys):
        if keys[pygame.K_LEFT] and self.rect.left > 0:
            self.rect.x -= self.speed
        if keys[pygame.K_RIGHT] and self.rect.right < WIDTH:
            self.rect.x += self.speed
        if keys[pygame.K_UP] and self.rect.top > 0:
            self.rect.y -= self.speed
        if keys[pygame.K_DOWN] and self.rect.bottom < HEIGHT:
            self.rect.y += self.speed

    def draw(self, screen):
        pygame.draw.rect(screen, BLUE, self.rect)


# --- Класс падающих объектов ---
class FallingObject:
    def __init__(self, obj_type):
        self.type = obj_type  # "star" или "bomb"
        self.x = random.randint(20, WIDTH - 20)
        self.y = -20
        self.speed = random.randint(3, 6)
        self.rect = pygame.Rect(self.x, self.y, 30, 30)
        self.color = GREEN if self.type == "star" else RED

    def update(self):
        self.y += self.speed
        self.rect.y = self.y

    def draw(self, screen):
        pygame.draw.ellipse(screen, self.color, self.rect)


# --- Основной класс игры ---
class Game:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        pygame.display.set_caption("Ловец Звезд")
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont("Arial", 24)
        self.large_font = pygame.font.SysFont("Arial", 48)

        self.db = DatabaseManager()
        self.state = "NAME_INPUT"
        self.player_name = ""
        self.score = 0

    def reset_game(self):
        self.player = Player(WIDTH // 2 - 25, HEIGHT - 70)
        self.objects = []
        self.score = 0
        self.spawn_timer = 0
        self.game_over = False
        self.win = False

    def handle_name_input(self, events):
        for event in events:
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_RETURN and len(self.player_name) > 0:
                    self.state = "PLAYING"
                    self.reset_game()
                elif event.key == pygame.K_BACKSPACE:
                    self.player_name = self.player_name[:-1]
                else:
                    if len(self.player_name) < 15 and event.unicode.isprintable():
                        self.player_name += event.unicode

    def run(self):
        running = True
        while running:
            events = pygame.event.get()
            for event in events:
                if event.type == pygame.QUIT:
                    running = False

            if self.state == "NAME_INPUT":
                self.draw_name_input()
                self.handle_name_input(events)

            elif self.state == "PLAYING":
                self.handle_playing(events)

            elif self.state == "GAME_OVER":
                self.draw_game_over()
                for event in events:
                    if event.type == pygame.KEYDOWN:
                        if event.key == pygame.K_SPACE:
                            self.state = "PLAYING"
                            self.reset_game()
                        elif event.key == pygame.K_ESCAPE:
                            running = False

            pygame.display.flip()
            self.clock.tick(FPS)

        pygame.quit()
        sys.exit()

    def draw_name_input(self):
        self.screen.fill(BLACK)
        title = self.large_font.render("Введите ваш никнейм:", True, WHITE)
        self.screen.blit(title, (WIDTH // 2 - title.get_width() // 2, 200))

        input_surface = self.font.render(self.player_name + "|", True, GREEN)
        self.screen.blit(input_surface, (WIDTH // 2 - input_surface.get_width() // 2, 300))

        hint = self.font.render("Нажмите Enter для начала", True, GRAY)
        self.screen.blit(hint, (WIDTH // 2 - hint.get_width() // 2, 400))

    def handle_playing(self, events):
        keys = pygame.key.get_pressed()
        self.player.move(keys)

        # Спавн объектов
        self.spawn_timer += 1
        if self.spawn_timer > 40:
            obj_type = "star" if random.random() > 0.3 else "bomb"
            self.objects.append(FallingObject(obj_type))
            self.spawn_timer = 0

        # Обновление и проверка коллизий
        for obj in self.objects[:]:
            obj.update()

            # Поймали объект
            if self.player.rect.colliderect(obj.rect):
                self.objects.remove(obj)
                if obj.type == "star":
                    self.score += 10
                else:
                    self.player.lives -= 1

            # Объект упал за экран
            elif obj.y > HEIGHT:
                self.objects.remove(obj)
                if obj.type == "star":
                    self.player.lives -= 1

        # Проверка условий победы/поражения
        if self.score >= 100:
            self.state = "GAME_OVER"
            self.win = True
            self.db.save_score(self.player_name, self.score)
        elif self.player.lives <= 0:
            self.state = "GAME_OVER"
            self.win = False
            self.db.save_score(self.player_name, self.score)

        self.draw_playing()

    def draw_playing(self):
        self.screen.fill(BLACK)

        # Отрисовка инструкций (Требование к UX)
        instructions = [
            "Стрелки - движение. Ловите ЗЕЛЕНЫЕ (+10 очков).",
            "Избегайте КРАСНЫХ (-1 жизнь) и не пропускайте звезды (-1 жизнь).",
            "Цель: набрать 100 очков!"
        ]
        for i, text in enumerate(instructions):
            surf = self.font.render(text, True, GRAY)
            self.screen.blit(surf, (10, 10 + i * 25))

        # Отрисовка счета и жизней
        score_text = self.font.render(f"Счет: {self.score} / 100", True, WHITE)
        lives_text = self.font.render(f"Жизни: {'♥' * self.player.lives}", True, RED)
        self.screen.blit(score_text, (WIDTH - 200, 10))
        self.screen.blit(lives_text, (WIDTH - 200, 40))

        self.player.draw(self.screen)
        for obj in self.objects:
            obj.draw(self.screen)

    def draw_game_over(self):
        self.screen.fill(BLACK)

        if self.win:
            msg = self.large_font.render("ВЫ ПОБЕДИЛИ!", True, GREEN)
        else:
            msg = self.large_font.render("ИГРА ОКОНЧЕНА", True, RED)

        self.screen.blit(msg, (WIDTH // 2 - msg.get_width() // 2, 50))

        score_msg = self.font.render(f"Ваш счет: {self.score}", True, WHITE)
        self.screen.blit(score_msg, (WIDTH // 2 - score_msg.get_width() // 2, 120))

        # Вывод Топ-5 (Требование 5)
        top_title = self.font.render("--- ТОП-5 ИГРОКОВ ---", True, BLUE)
        self.screen.blit(top_title, (WIDTH // 2 - top_title.get_width() // 2, 200))

        top_players = self.db.get_top_5()
        for i, (name, score) in enumerate(top_players):
            text = f"{i + 1}. {name} - {score} очков"
            text_surface = self.font.render(text, True, WHITE)
            self.screen.blit(text_surface, (WIDTH // 2 - text_surface.get_width() // 2, 250 + i * 30))

        restart_msg = self.font.render("Нажмите ПРОБЕЛ для рестарта или ESC для выхода", True, GRAY)
        self.screen.blit(restart_msg, (WIDTH // 2 - restart_msg.get_width() // 2, HEIGHT - 100))


# Запуск игры
if __name__ == "__main__":
    game = Game()
    game.run()