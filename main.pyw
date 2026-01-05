import pygame
import sys
import random
import math
import json
import os
import base64

# Initialize Pygame and Mixer
pygame.init()
pygame.mixer.init()

# Constants
WIDTH, HEIGHT = 800, 600
SCREEN = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("PONG")
CLOCK = pygame.time.Clock()

# Helper for PyInstaller resource pathing
def resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
        return os.path.join(base_path, "data_files", relative_path)
    except Exception:
        # In development, look in the current directory
        return os.path.join(os.path.abspath("."), relative_path)

# Set Icon
try:
    icon_path = resource_path("icon.png")
    if os.path.exists(icon_path):
        icon_surf = pygame.image.load(icon_path).convert_alpha()
        pygame.display.set_icon(icon_surf)
except Exception:
    pass

# Colors (Neon Palette)
BG_COLOR = (10, 10, 20)
NEON_CYAN = (0, 255, 255)
NEON_MAGENTA = (255, 0, 255)
NEON_GREEN = (50, 255, 50)
NEON_RED = (255, 50, 50)
WHITE = (255, 255, 255)
GLOW_WHITE = (200, 200, 255, 50)  # Transparent white for glow
BUTTON_COLOR = (20, 20, 40)
BUTTON_HOVER = (40, 40, 80)

# Fonts
try:
    FONT = pygame.font.Font("Consolas", 30)
except:
    FONT = pygame.font.SysFont("Consolas", 30)
LARGE_FONT = pygame.font.SysFont("Consolas", 60)
TITLE_FONT = pygame.font.SysFont("Consolas", 80, bold=True)

# Game Objects
PLAYER_W, PLAYER_H = 10, 100
BALL_SIZE = 15

player = pygame.Rect(50, HEIGHT//2 - PLAYER_H//2, PLAYER_W, PLAYER_H)
opponent = pygame.Rect(WIDTH - 50 - PLAYER_W, HEIGHT//2 - PLAYER_H//2, PLAYER_W, PLAYER_H)
ball = pygame.Rect(WIDTH//2 - BALL_SIZE//2, HEIGHT//2 - BALL_SIZE//2, BALL_SIZE, BALL_SIZE)

# Assets
try:
    point_sound = pygame.mixer.Sound(resource_path("point.mp3"))
except Exception:
    point_sound = None

# Global State
player_score = 0
opponent_score = 0
b_vel = 7
ball_speed_base = 7 # Default (Easy)
ball_speed_current = 5 
is_first_shot = True
ball_vel = [random.choice([-ball_speed_current, ball_speed_current]), random.choice([-ball_speed_current, ball_speed_current])]
player_vel = 0
opponent_vel = 0
CURRENT_DIFFICULTY = "EASY"

class LeaderboardManager:
    def __init__(self, filename="leaderboard.dat"):
        if os.path.exists("leaderboard.json") and not os.path.exists("leaderboard.dat"):
            try:
                os.rename("leaderboard.json", "leaderboard.dat")
                print("Migrated leaderboard.json to leaderboard.dat")
            except Exception as e:
                print(f"Migration failed: {e}")
                
        self.filename = filename
        self.key = "NEON_PONG_SECRET"
        self.data = self.load_data()
        
        # Ensure file exists
        if not os.path.exists(self.filename):
            self.save_data()
        
    def encrypt(self, text):
        # ROI (Rotated/XOR) Obfuscation -> Base64
        # 1. XOR
        xor_res = []
        for i, char in enumerate(text):
            xor_res.append(chr(ord(char) ^ ord(self.key[i % len(self.key)])))
        xor_str = "".join(xor_res)
        # 2. Base64
        return base64.b64encode(xor_str.encode('utf-8')).decode('utf-8')
        
    def decrypt(self, encoded_text):
        try:
            # 1. Base64 Decode
            xor_str = base64.b64decode(encoded_text).decode('utf-8')
            # 2. XOR Reverse
            res = []
            for i, char in enumerate(xor_str):
                res.append(chr(ord(char) ^ ord(self.key[i % len(self.key)])))
            return "".join(res)
        except:
            return "{}"

    def load_data(self):
        if not os.path.exists(self.filename):
            return {"EASY": [], "MEDIUM": [], "HARD": [], "EXTREME": []}
        try:
            with open(self.filename, 'r') as f:
                content = f.read()
            
            # Migration Support: Try plain JSON first
            try:
                return json.loads(content)
            except json.JSONDecodeError:
                # If fail, assume encrypted
                decrypted = self.decrypt(content)
                return json.loads(decrypted)
                
        except Exception as e:
            print(f"Error loading leaderboard: {e}")
            return {"EASY": [], "MEDIUM": [], "HARD": [], "EXTREME": []}
            
    def save_data(self):
        try:
            json_str = json.dumps(self.data)
            encrypted = self.encrypt(json_str)
            with open(self.filename, 'w') as f:
                f.write(encrypted)
        except Exception as e:
            print(f"Error saving leaderboard: {e}")
            
    def add_score(self, difficulty, name, p_score, o_score):
        if difficulty not in self.data:
            self.data[difficulty] = []
            
        self.data[difficulty].append({
            "name": name, 
            "score": p_score, 
            "opponent_score": o_score
        })
        
        # Sort: Descending Player Score, Ascending Opponent Score
        self.data[difficulty].sort(key=lambda x: (-x['score'], x['opponent_score']))
        
        # Keep top 5
        self.data[difficulty] = self.data[difficulty][:5]
        self.save_data()

LB_MANAGER = LeaderboardManager()

# Particles & Effects
particles = []
ball_trail = []

class Particle:
    def __init__(self, x, y, color, speed=3):
        self.x = x
        self.y = y
        self.color = color
        self.size = random.randint(3, 6)
        self.life = 255
        self.vx = random.uniform(-speed, speed)
        self.vy = random.uniform(-speed, speed)

    def update(self):
        self.x += self.vx
        self.y += self.vy
        self.life -= 5
        self.size -= 0.05

    def draw(self, surface):
        if self.life > 0 and self.size > 0:
            s_surf = pygame.Surface((int(self.size)*2, int(self.size)*2), pygame.SRCALPHA)
            pygame.draw.circle(s_surf, (*self.color, int(self.life)), (int(self.size), int(self.size)), int(self.size))
            surface.blit(s_surf, (int(self.x) - self.size, int(self.y) - self.size))

class Button:
    def __init__(self, text, x, y, w, h, color=BUTTON_COLOR, text_color=WHITE):
        self.rect = pygame.Rect(x, y, w, h)
        self.text = text
        self.color = color
        self.text_color = text_color
        self.hovered = False

    def draw(self, surface):
        color = BUTTON_HOVER if self.hovered else self.color
        border_color = NEON_CYAN if self.hovered else (100, 100, 100)
        
        # Draw button body
        pygame.draw.rect(surface, color, self.rect, border_radius=10)
        pygame.draw.rect(surface, border_color, self.rect, 2, border_radius=10)
        
        # Glow if hovered
        if self.hovered:
             glow_surf = pygame.Surface((self.rect.width + 20, self.rect.height + 20), pygame.SRCALPHA)
             pygame.draw.rect(glow_surf, (*NEON_CYAN, 30), (10, 10, self.rect.width, self.rect.height), border_radius=10)
             surface.blit(glow_surf, (self.rect.x - 10, self.rect.y - 10), special_flags=pygame.BLEND_ADD)

        # Text
        text_surf = FONT.render(self.text, True, self.text_color)
        text_rect = text_surf.get_rect(center=self.rect.center)
        surface.blit(text_surf, text_rect)

    def check_hover(self, mouse_pos):
        self.hovered = self.rect.collidepoint(mouse_pos)

    def is_clicked(self, event):
        return self.hovered and event.type == pygame.MOUSEBUTTONDOWN and event.button == 1

def create_explosion(x, y, color):
    for _ in range(15):
        particles.append(Particle(x, y, color))

def draw_glow_rect(surface, color, rect, glow_radius=15):
    pygame.draw.rect(surface, color, rect, border_radius=5)
    glow_surf = pygame.Surface((rect.width + glow_radius*4, rect.height + glow_radius*4), pygame.SRCALPHA)
    pygame.draw.rect(glow_surf, (*color, 30), (glow_radius, glow_radius, rect.width + 2*glow_radius, rect.height + 2*glow_radius), border_radius=10)
    pygame.draw.rect(glow_surf, (*color, 60), (glow_radius*1.5, glow_radius*1.5, rect.width + 1*glow_radius, rect.height + 1*glow_radius), border_radius=8)
    surface.blit(glow_surf, (rect.x - glow_radius*2, rect.y - glow_radius*2), special_flags=pygame.BLEND_ADD)

def draw_glow_circle(surface, color, center, radius, glow_radius=10):
    pygame.draw.circle(surface, color, center, radius)
    s_surf = pygame.Surface((radius*4 + glow_radius*4, radius*4 + glow_radius*4), pygame.SRCALPHA)
    pygame.draw.circle(s_surf, (*color, 40), (s_surf.get_width()//2, s_surf.get_height()//2), radius + glow_radius)
    surface.blit(s_surf, (center[0] - s_surf.get_width()//2, center[1] - s_surf.get_height()//2), special_flags=pygame.BLEND_ADD)

def draw_net():
    for i in range(0, HEIGHT, 40):
        pygame.draw.rect(SCREEN, (50, 50, 80), (WIDTH//2 - 2, i, 4, 20))

def text_blit(text, x, y, size=30, color=WHITE, center=False):
    f = pygame.font.SysFont("Consolas", size, bold=True)
    rendered = f.render(text, True, color)
    if center:
        rect = rendered.get_rect(center=(x, y))
        SCREEN.blit(rendered, rect)
    else:
        SCREEN.blit(rendered, (x, y))

def game_over_screen(winner):
    global player_score, opponent_score
    
    # Save Score
    if winner == "PLAYER":
        LB_MANAGER.add_score(CURRENT_DIFFICULTY, PLAYER_NAME, player_score, opponent_score)
    else:
        LB_MANAGER.add_score(CURRENT_DIFFICULTY, PLAYER_NAME, player_score, opponent_score)

    replay_btn = Button("PLAY AGAIN", WIDTH//2 - 100, HEIGHT//2, 200, 50)
    menu_btn = Button("MAIN MENU", WIDTH//2 - 100, HEIGHT//2 + 70, 200, 50)
    lb_btn = Button("LEADERBOARD", WIDTH//2 - 100, HEIGHT//2 + 140, 200, 50)
    
    waiting = True
    while waiting:
        SCREEN.fill(BG_COLOR)
        
        update_bg_particles()
        draw_bg_particles()
        
        # Result Text
        if winner == "PLAYER":
            msg = "YOU WIN!"
            col = NEON_GREEN
        else:
            msg = "YOU LOSE!"
            col = NEON_RED
            
        text_blit(msg, WIDTH//2, HEIGHT//4, size=60, color=col, center=True)
        text_blit(f"{player_score} - {opponent_score}", WIDTH//2, HEIGHT//4 + 70, size=50, color=WHITE, center=True)
        
        mouse_pos = pygame.mouse.get_pos()
        for btn in [replay_btn, menu_btn, lb_btn]:
            btn.check_hover(mouse_pos)
            btn.draw(SCREEN)
            
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
                
            if replay_btn.is_clicked(event):
                # Reset scores and restart game loop
                player_score = 0
                opponent_score = 0
                return
            
            if menu_btn.is_clicked(event):
                player_score = 0
                opponent_score = 0
                main_menu()
                return
                
            if lb_btn.is_clicked(event):
                 leaderboard_screen()
                 
        pygame.display.flip()
        CLOCK.tick(60)

def reset_ball(scorer):
    global ball_vel, player_score, opponent_score, ai_target_y, ball_speed_current, is_first_shot, player_vel, opponent_vel
    if scorer == "player":
        player_score += 1
    elif scorer == "opponent":
        opponent_score += 1

    if point_sound:
        point_sound.play()
    
    # Check Win Condition
    if player_score >= 10:
        game_over_screen("PLAYER")
        ball.center = (WIDTH//2, HEIGHT//2)
        player.centery = HEIGHT // 2
        opponent.centery = HEIGHT // 2
        player_vel = 0
        opponent_vel = 0
        is_first_shot = True
        ball_speed_current = 5
        ball_vel = [random.choice([-5, 5]), random.choice([-5, 5])]
        return
    elif opponent_score >= 10:
        game_over_screen("OPPONENT")
        ball.center = (WIDTH//2, HEIGHT//2)
        player.centery = HEIGHT // 2
        opponent.centery = HEIGHT // 2
        player_vel = 0
        opponent_vel = 0
        is_first_shot = True
        ball_speed_current = 5
        ball_vel = [random.choice([-5, 5]), random.choice([-5, 5])]
        return

    # Pause and show result BEFORE resetting ball position
    pause_menu(scorer)

    # Reset ball logic after resume
    ball.center = (WIDTH//2, HEIGHT//2)
    player.centery = HEIGHT // 2
    opponent.centery = HEIGHT // 2
    player_vel = 0
    opponent_vel = 0
    is_first_shot = True
    ball_speed_current = 5
    ball_vel = [random.choice([-5, 5]), random.choice([-5, 5])]
    ball_trail.clear()
    
    # Reset AI
    ai_target_y = HEIGHT // 2
    
    # If ball moves towards AI immediately, predict
    if ball_vel[0] > 0:
        ai_target_y = predict_ball_landing()

def update_bg_particles():
    if len(particles) < 20: # Keep some ambient particles
        particles.append(Particle(random.randint(0, WIDTH), random.randint(0, HEIGHT), random.choice([NEON_CYAN, NEON_MAGENTA]), speed=0.5))
    
    for p in particles[:]:
        p.update()
        if p.life <= 0:
            particles.remove(p)
    
        if abs(p.vx) < 1 and abs(p.vy) < 1:
            if p.life < 100: p.life = 255
            if p.x < 0: p.x = WIDTH
            if p.x > WIDTH: p.x = 0
            if p.y < 0: p.y = HEIGHT
            if p.y > HEIGHT: p.y = 0

def draw_bg_particles():
    for p in particles:
        p.draw(SCREEN)

# Player Data
PLAYER_NAME = ""

class TextInput:
    def __init__(self, x, y, w, h, text=''):
        self.rect = pygame.Rect(x, y, w, h)
        self.color = (100, 100, 100) # Inactive
        self.text = text
        self.txt_surface = FONT.render(text, True, self.color)
        self.active = False

    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN:
            # If the user clicked on the input_box rect.
            if self.rect.collidepoint(event.pos):
                self.active = not self.active
            else:
                self.active = False
            # Change the current color of the input box.
            self.color = NEON_CYAN if self.active else (100, 100, 100)
        
        if event.type == pygame.KEYDOWN:
            if self.active:
                if event.key == pygame.K_RETURN:
                    self.active = False
                    self.color = (100, 100, 100)
                elif event.key == pygame.K_BACKSPACE:
                    self.text = self.text[:-1]
                else:
                    # Limit length
                    if len(self.text) < 10:
                        self.text += event.unicode
                
                # Re-render the text.
                self.txt_surface = FONT.render(self.text, True, NEON_CYAN if self.active else WHITE)

    def draw(self, surface):
        # Draw text
        surface.blit(self.txt_surface, (self.rect.x + 5, self.rect.y + 5))
        # Draw rect
        pygame.draw.rect(surface, self.color, self.rect, 2, border_radius=5)
        
        # Label
        label = FONT.render("ENTER NAME:", True, WHITE)
        surface.blit(label, (self.rect.x, self.rect.y - 30))

def main_menu():
    global PLAYER_NAME
    # Move buttons down slightly
    start_btn = Button("START GAME", WIDTH//2 - 100, HEIGHT//2 + 20, 200, 50)
    lb_btn = Button("LEADERBOARD", WIDTH//2 - 100, HEIGHT//2 + 90, 200, 50)
    quit_btn = Button("QUIT", WIDTH//2 - 100, HEIGHT//2 + 160, 200, 50)
    input_box = TextInput(WIDTH//2 - 100, 250, 200, 40, text=PLAYER_NAME)
    
    run = True
    while run:
        SCREEN.fill(BG_COLOR)
        
        mouse_pos = pygame.mouse.get_pos()
        
        # Background effects
        update_bg_particles()
        draw_bg_particles()
        
        # Title pulsing
        alpha = int(128 + 127 * math.sin(pygame.time.get_ticks() / 500))
        title_surf = TITLE_FONT.render("PONG", True, NEON_CYAN)
        # Move title up
        title_rect = title_surf.get_rect(center=(WIDTH//2, HEIGHT//4)) 
        SCREEN.blit(title_surf, title_rect)
        
        # Input Box
        input_box.draw(SCREEN)
        
        # Buttons
        for btn in [start_btn, lb_btn, quit_btn]:
            btn.check_hover(mouse_pos)
            btn.draw(SCREEN)
            
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            
            input_box.handle_event(event)
            
            if start_btn.is_clicked(event):
                # Save name
                if input_box.text.strip():
                    PLAYER_NAME = input_box.text.strip().upper()
                else:
                    PLAYER_NAME = "PLAYER"
                    
                # Go to difficulty select
                if difficulty_menu():
                    run = False
            
            if lb_btn.is_clicked(event):
                leaderboard_screen()
                
            if quit_btn.is_clicked(event):
                pygame.quit()
                sys.exit()

        pygame.display.flip()
        CLOCK.tick(60)
        
    # Clear particles for game start
    particles.clear()

def pause_menu(reason=None):
    resume_btn = Button("RESUME", WIDTH//2 - 100, HEIGHT//2, 200, 50)
    quit_btn = Button("QUIT", WIDTH//2 - 100, HEIGHT//2 + 70, 200, 50)
    
    # Snapshot of current screen for translucent overlay
    snapshot = SCREEN.copy()
    overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, 150)) # Translucent black
    snapshot.blit(overlay, (0,0))
    
    waiting = True
    while waiting:
        # Draw the frozen game state with overlay
        SCREEN.blit(snapshot, (0,0))
        
        mouse_pos = pygame.mouse.get_pos()
        
        # Message Logic
        msg = "PAUSED"
        if reason == "player":
            msg = f"{PLAYER_NAME} SCORED!"
        elif reason == "opponent":
            msg = "OPPONENT SCORED!"
            
        text_blit(msg, WIDTH//2, HEIGHT//3, size=50, color=WHITE, center=True)
        if reason:
             text_blit("Press SPACE to Continue", WIDTH//2, HEIGHT//3 + 50, size=20, color=NEON_CYAN, center=True)
        
        for btn in [resume_btn, quit_btn]:
            btn.check_hover(mouse_pos)
            btn.draw(SCREEN)
            
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_SPACE or event.key == pygame.K_ESCAPE:
                    waiting = False
            
            if resume_btn.is_clicked(event):
                waiting = False
            if quit_btn.is_clicked(event):
                pygame.quit()
                sys.exit()
                
        pygame.display.flip()
        CLOCK.tick(60)

# AI State
ai_target_y = HEIGHT // 2

# AI Difficulty Parameters (Default: Medium)
AI_SPEED = 7
AI_ERROR_MARGIN = 40

def predict_ball_landing():
    if ball_vel[0] <= 0: # Ball moving away from AI
        return HEIGHT // 2
        
    time_to_intercept = (opponent.left - ball.right) / ball_vel[0]
    predicted_y = ball.centery + (ball_vel[1] * time_to_intercept)
    
    while predicted_y < 0 or predicted_y > HEIGHT:
        if predicted_y < 0:
            predicted_y = -predicted_y
        if predicted_y > HEIGHT:
            predicted_y = 2*HEIGHT - predicted_y
            
    # Add human error/randomness based on Difficulty
    error = random.randint(-AI_ERROR_MARGIN, AI_ERROR_MARGIN)
    return predicted_y + error

def leaderboard_screen():
    # Tabs
    tab_easy = Button("EASY", 100, 100, 150, 40, color=(20, 100, 20))
    tab_med = Button("MEDIUM", 250, 100, 150, 40, color=(100, 100, 20))
    tab_hard = Button("HARD", 400, 100, 150, 40, color=(100, 50, 20))
    tab_ext = Button("EXTREME", 550, 100, 150, 40, color=(100, 20, 20))
    
    back_btn = Button("BACK", WIDTH//2 - 100, HEIGHT - 80, 200, 50)
    
    current_tab = "EASY"
    
    showing = True
    while showing:
        SCREEN.fill(BG_COLOR)
        update_bg_particles()
        draw_bg_particles()
        
        text_blit("LEADERBOARD", WIDTH//2, 50, size=50, color=NEON_CYAN, center=True)
        
        mouse_pos = pygame.mouse.get_pos()
        
        # Draw Tabs
        for btn, name in [(tab_easy, "EASY"), (tab_med, "MEDIUM"), (tab_hard, "HARD"), (tab_ext, "EXTREME")]:
            # Highlight active tab
            if name == current_tab:
                 pygame.draw.rect(SCREEN, NEON_CYAN, (btn.rect.x, btn.rect.y + 40, btn.rect.width, 5))
            
            btn.check_hover(mouse_pos)
            btn.draw(SCREEN)
            
        # Draw Scores for current tab
        scores = LB_MANAGER.data.get(current_tab, [])
        y_offset = 180
        
        # Headers
        text_blit("RANK", 150, 150, size=25, color=NEON_MAGENTA)
        text_blit("NAME", 300, 150, size=25, color=NEON_MAGENTA)
        text_blit("SCORE", 500, 150, size=25, color=NEON_MAGENTA)
        text_blit("OPP", 650, 150, size=25, color=NEON_MAGENTA)
        
        if not scores:
            text_blit("NO SCORES YET", WIDTH//2, 300, size=30, color=(100, 100, 100), center=True)
        else:
            for i, entry in enumerate(scores):
                col = WHITE
                if i == 0: col = NEON_GREEN # 1st place
                
                text_blit(f"{i+1}", 150, y_offset, size=20, color=col)
                text_blit(entry.get("name", "UNK"), 300, y_offset, size=20, color=col)
                text_blit(f"{entry['score']}", 500, y_offset, size=20, color=col)
                text_blit(f"{entry['opponent_score']}", 650, y_offset, size=20, color=col)
                y_offset += 40
                
        back_btn.check_hover(mouse_pos)
        back_btn.draw(SCREEN)
        
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
                
            if tab_easy.is_clicked(event): current_tab = "EASY"
            if tab_med.is_clicked(event): current_tab = "MEDIUM"
            if tab_hard.is_clicked(event): current_tab = "HARD"
            if tab_ext.is_clicked(event): current_tab = "EXTREME"
            
            if back_btn.is_clicked(event):
                showing = False
                
        pygame.display.flip()
        CLOCK.tick(60)

def difficulty_menu():
    global AI_SPEED, AI_ERROR_MARGIN, ball_speed_base, CURRENT_DIFFICULTY
    
    btn_easy = Button("EASY", WIDTH//2 - 100, HEIGHT//2 - 90, 200, 50, color=(20, 100, 20))
    btn_med = Button("MEDIUM", WIDTH//2 - 100, HEIGHT//2 - 20, 200, 50, color=(100, 100, 20))
    btn_hard = Button("HARD", WIDTH//2 - 100, HEIGHT//2 + 50, 200, 50, color=(100, 50, 20))
    btn_extreme = Button("EXTREME", WIDTH//2 - 100, HEIGHT//2 + 120, 200, 50, color=(100, 20, 20))
    
    while True:
        SCREEN.fill(BG_COLOR)
        
        # Background effects
        update_bg_particles()
        draw_bg_particles()
        
        text_blit("SELECT DIFFICULTY", WIDTH//2, HEIGHT//2 - 150, size=40, color=NEON_MAGENTA, center=True)
        
        mouse_pos = pygame.mouse.get_pos()
        
        for btn in [btn_easy, btn_med, btn_hard, btn_extreme]:
            btn.check_hover(mouse_pos)
            btn.draw(SCREEN)
            
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
                
            if btn_easy.is_clicked(event):
                AI_SPEED = 6
                AI_ERROR_MARGIN = 60
                ball_speed_base = 7
                CURRENT_DIFFICULTY = "EASY"
                return True
            if btn_med.is_clicked(event):
                AI_SPEED = 10
                AI_ERROR_MARGIN = 30
                ball_speed_base = 9
                CURRENT_DIFFICULTY = "MEDIUM"
                return True
            if btn_hard.is_clicked(event):
                AI_SPEED = 16
                AI_ERROR_MARGIN = 10
                ball_speed_base = 12
                CURRENT_DIFFICULTY = "HARD"
                return True
            if btn_extreme.is_clicked(event):
                AI_SPEED = 22
                AI_ERROR_MARGIN = 0
                ball_speed_base = 15
                CURRENT_DIFFICULTY = "EXTREME"
                return True
                
        pygame.display.flip()
        CLOCK.tick(60)


# Physics Constants
MAX_BOUNCE_ANGLE = math.radians(50) # ~0.87 radians
MAX_BALL_SPEED = 20

def handle_paddle_collision(ball_obj, paddle_obj, is_player):
    global ball_vel, ball_speed_current, ai_target_y, is_first_shot
    
    # Calculate intersection logic
    intersect_y = paddle_obj.centery - ball_obj.centery
    normalized_intersect = intersect_y / (paddle_obj.height / 2)
    bounce_angle = normalized_intersect * MAX_BOUNCE_ANGLE
    
    # Speed Ramping logic
    if is_first_shot:
        ball_speed_current = ball_speed_base
        is_first_shot = False
    else:
        ball_speed_current += 1.0
        
    if ball_speed_current > MAX_BALL_SPEED: 
        ball_speed_current = MAX_BALL_SPEED
        
    # Calculate new velocity components
    vel_x = ball_speed_current * math.cos(bounce_angle)
    vel_y = ball_speed_current * -math.sin(bounce_angle)
    
    # Direction
    if is_player:
        # Hitting player (left side), want positive X velocity
        ball_vel = [abs(vel_x), vel_y]
        create_explosion(ball_obj.left, ball_obj.centery, NEON_CYAN)
        # AI Prediction Trigger
        ai_target_y = predict_ball_landing()
    else:
        # Hitting opponent (right side), want negative X velocity
        ball_vel = [-abs(vel_x), vel_y]
        create_explosion(ball_obj.right, ball_obj.centery, NEON_MAGENTA)
        # AI Reset
        ai_target_y = HEIGHT // 2

# --- Main Execution ---
main_menu()

# Initial prediction for first serve
if ball_vel[0] > 0:
    ai_target_y = predict_ball_landing()

while True:
    # 1. Event Handling
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            pygame.quit()
            sys.exit()

        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_w:
                player_vel = -16
            if event.key == pygame.K_s:
                player_vel = 16
            if event.key == pygame.K_ESCAPE:
                pause_menu()

        if event.type == pygame.KEYUP:
            if (event.key == pygame.K_w and player_vel < 0) or (event.key == pygame.K_s and player_vel > 0):
                player_vel = 0

    # 2. Game Logic
    
    # Player Movement
    player.y += player_vel
    if player.top < 0: player.top = 0
    if player.bottom > HEIGHT: player.bottom = HEIGHT 

    # AI Movement (Predictive & Parameterized)
    if opponent.centery < ai_target_y - 10:
        opponent_vel = AI_SPEED # Use parameterized speed
    elif opponent.centery > ai_target_y + 10:
        opponent_vel = -AI_SPEED
    else:
        opponent_vel = 0
        
    opponent.y += opponent_vel
    if opponent.top < 0: opponent.top = 0
    if opponent.bottom > HEIGHT: opponent.bottom = HEIGHT

    # Ball Movement & Tunneling Guard
    # Check if ball will skip the paddle in this frame
    tunnel_hit = False
    
    if ball_vel[0] > 0: # Moving Right
        # Predicted next position edge
        next_right = ball.right + ball_vel[0]
        # Check if we cross Opponent Left Edge (740)
        if ball.right < opponent.left and next_right >= opponent.left:
            # Check Y intersection
            if ball.bottom >= opponent.top and ball.top <= opponent.bottom:
                # Force Hit
                ball.right = opponent.left
                handle_paddle_collision(ball, opponent, False)
                tunnel_hit = True

    elif ball_vel[0] < 0: # Moving Left
        next_left = ball.left + ball_vel[0]
        # Check if we cross Player Right Edge (60)
        if ball.left > player.right and next_left <= player.right:
            if ball.bottom >= player.top and ball.top <= player.bottom:
                ball.left = player.right
                handle_paddle_collision(ball, player, True)
                tunnel_hit = True

    if not tunnel_hit:
        ball.x += ball_vel[0]
    
    ball.y += ball_vel[1]

    # Trail Update
    ball_trail.append(ball.center)
    if len(ball_trail) > 15:
        ball_trail.pop(0)

    # Collisions - Walls
    if ball.top <= 0 or ball.bottom >= HEIGHT:
        ball_vel[1] = -ball_vel[1]
        create_explosion(ball.centerx, ball.centery, WHITE)

    # Collisions - Paddles
    if ball.colliderect(player): # Player hit
        if ball_vel[0] < 0: # Check direction to avoid sticky paddle bug
             handle_paddle_collision(ball, player, True)

    if ball.colliderect(opponent): # Opponent hit
        if ball_vel[0] > 0:
             handle_paddle_collision(ball, opponent, False)

    # Scoring
    if ball.left <= 0:
        reset_ball("opponent")
    if ball.right >= WIDTH:
        reset_ball("player")

    # Particle Update
    for p in particles[:]:
        p.update()
        if p.life <= 0 or p.size <= 0:
            particles.remove(p)

    # 3. Drawing
    SCREEN.fill(BG_COLOR)
    
    draw_net()

    # Draw Trail
    for i, pos in enumerate(ball_trail):
        alpha = int(255 * (i / len(ball_trail)))
        radius = int(BALL_SIZE/2 * (i / len(ball_trail)))
        pygame.draw.circle(SCREEN, (255, 255, 200), pos, radius)

    # Draw Particles
    for p in particles:
        p.draw(SCREEN)

    # Draw Objects
    draw_glow_rect(SCREEN, NEON_CYAN, player)
    draw_glow_rect(SCREEN, NEON_MAGENTA, opponent)
    draw_glow_circle(SCREEN, (255, 255, 200), ball.center, BALL_SIZE//2)

    # Draw Score
    text_blit(f"{player_score}", WIDTH//2 - 60, 20, size=50, color=NEON_CYAN)
    text_blit(f"{opponent_score}", WIDTH//2 + 30, 20, size=50, color=NEON_MAGENTA)

    pygame.display.flip()
    CLOCK.tick(60)
