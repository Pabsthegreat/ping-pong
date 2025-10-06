
import pygame
import math
from .paddle import Paddle
from .ball import Ball

WHITE = (255, 255, 255)
GREY = (90, 90, 110)
BLACK = (0, 0, 0)

class GameEngine:
    def __init__(self, width, height):
        self.width = width
        self.height = height
        self.paddle_width = 12
        self.paddle_height = 100

        # Entities
        self.player = Paddle(20, height // 2 - self.paddle_height // 2, self.paddle_width, self.paddle_height)
        self.ai = Paddle(width - 20 - self.paddle_width, height // 2 - self.paddle_height // 2, self.paddle_width, self.paddle_height)
        self.ball = Ball(width // 2 - 8, height // 2 - 8, 16, 16, width, height)

        # Scores and state
        self.player_score = 0
        self.ai_score = 0
        self.best_of = 5               # default series length
        self.win_score = self._best_of_to_win(self.best_of)
        self.state = "play"            # play | game_over | replay_menu

        # Timing
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont("Arial", 42, bold=True)
        self.small = pygame.font.SysFont("Arial", 22)

        # Sounds (optional): try to init mixer and create simple beeps
        self.snd_paddle = None
        self.snd_wall = None
        self.snd_score = None
        self._init_sounds()

    def _best_of_to_win(self, n):
        return n // 2 + 1

    def _init_sounds(self):
        try:
            pygame.mixer.init()
            # generate simple tones without external files
            import numpy as np
            def tone(freq, ms=80, vol=0.3):
                rate = 44100
                t = np.linspace(0, ms/1000.0, int(rate * ms/1000.0), False)
                sig = (np.sin(2 * np.pi * freq * t) * 32767 * vol).astype(np.int16)
                return pygame.mixer.Sound(buffer=sig.tobytes())
            self.snd_paddle = tone(900, 60)
            self.snd_wall = tone(600, 60)
            self.snd_score = tone(300, 160)
        except Exception:
            # mixer or numpy not available; proceed silently
            self.snd_paddle = self.snd_wall = self.snd_score = None

    def _play(self, snd):
        if snd:
            snd.play()

    def handle_input(self):
        keys = pygame.key.get_pressed()
        if self.state == "play":
            dy = 0.0
            if keys[pygame.K_w] or keys[pygame.K_UP]:
                dy -= self.player.speed * self._dt
            if keys[pygame.K_s] or keys[pygame.K_DOWN]:
                dy += self.player.speed * self._dt
            if dy != 0.0:
                self.player.move(dy, self.height)
        elif self.state == "replay_menu":
            # choose best-of or exit
            if keys[pygame.K_3]:
                self._start_new_series(best_of=3)
            elif keys[pygame.K_5]:
                self._start_new_series(best_of=5)
            elif keys[pygame.K_7]:
                self._start_new_series(best_of=7)
            elif keys[pygame.K_ESCAPE]:
                pygame.event.post(pygame.event.Event(pygame.QUIT))

    def _start_new_series(self, best_of):
        self.best_of = best_of
        self.win_score = self._best_of_to_win(best_of)
        self.player_score = 0
        self.ai_score = 0
        # serve to random side
        self.ball.serve(to_right=True)
        self.state = "play"

    def _substeps(self):
        # pick substeps based on speed to prevent tunneling
        speed = math.hypot(self.ball.vx, self.ball.vy)
        px_per_step = 180.0  # target pixels per substep
        n = max(1, int(speed / px_per_step))
        return min(n, 8)  # cap to avoid too many iterations

    def update(self):
        # compute dt from internal clock (but main loop also clocks)
        self._dt = self.clock.get_time() / 1000.0 or 1/120.0

        if self.state == "play":
            # AI follows ball
            self.ai.auto_track(self.ball, self.height, react=0.20)

            # Sub-stepped integration & collision
            steps = self._substeps()
            step_dt = self._dt / steps
            for _ in range(steps):
                self.ball.move(step_dt)
                self._check_wall_bounce()
                if self.ball.vx < 0:
                    self._paddle_bounce(self.player)
                else:
                    self._paddle_bounce(self.ai)

                scorer = self._check_score()
                if scorer is not None:
                    if scorer == "player":
                        self.player_score += 1
                    else:
                        self.ai_score += 1
                    self._play(self.snd_score)
                    # reset ball toward the scorer's opponent
                    to_right = (scorer == "player")
                    self.ball.reset_after_score(last_dir_right=to_right)
                    break  # stop remaining substeps this frame

            # Check game over
            if self.player_score >= self.win_score or self.ai_score >= self.win_score:
                self.state = "game_over"
                # small pause so the message is visible before entering menu
                self._game_over_start_time = pygame.time.get_ticks()

        elif self.state == "game_over":
            # after 1.2s, move to replay menu
            if pygame.time.get_ticks() - getattr(self, "_game_over_start_time", 0) > 1200:
                self.state = "replay_menu"

    def _check_wall_bounce(self):
        # top/bottom bounce is handled in Ball.move; play sound if occurred
        # detect bounce by checking if y is exactly at bounds and vy sign flipped in last small step
        # (approximate: play when y==0 or y+height==screen_height)
        if self.ball.y <= 0 or self.ball.y + self.ball.height >= self.height:
            self._play(self.snd_wall)

    def _paddle_bounce(self, paddle):
        brect = self.ball.rect()
        pre = brect.copy()
        if not brect.colliderect(paddle.rect()):
            return
        # push ball outside the paddle and reflect vx
        if self.ball.vx < 0:  # moving left hitting player's right side
            self.ball.x = paddle.x + paddle.width
            self.ball.vx = abs(self.ball.vx)
        else:                  # moving right hitting AI's left side
            self.ball.x = paddle.x - self.ball.width
            self.ball.vx = -abs(self.ball.vx)
        # add "english" based on impact point
        pad_center = paddle.y + paddle.height / 2.0
        ball_center = self.ball.y + self.ball.height / 2.0
        offset = (ball_center - pad_center) / (paddle.height / 2.0)
        self.ball.vy += offset * 200.0  # tweak
        # speed up a little
        self.ball.speed_up(1.04)
        self._play(self.snd_paddle)

    def _check_score(self):
        # left goal (ball past player) -> AI scores
        if self.ball.x + self.ball.width < 0:
            return "ai"
        # right goal (ball past AI) -> Player scores
        if self.ball.x > self.width:
            return "player"
        return None

    def render(self, screen):
        # table
        screen.fill(BLACK)
        for y in range(0, self.height, 24):
            pygame.draw.rect(screen, GREY, (self.width//2 - 2, y, 4, 12), border_radius=2)

        # paddles & ball
        pygame.draw.rect(screen, WHITE, self.player.rect(), border_radius=4)
        pygame.draw.rect(screen, WHITE, self.ai.rect(), border_radius=4)
        pygame.draw.ellipse(screen, WHITE, self.ball.rect())

        # score
        pl = self.font.render(str(self.player_score), True, WHITE)
        pr = self.font.render(str(self.ai_score), True, WHITE)
        screen.blit(pl, (self.width//2 - 80 - pl.get_width(), 20))
        screen.blit(pr, (self.width//2 + 80, 20))

        if self.state == "game_over":
            msg = "You Win!" if self.player_score > self.ai_score else "AI Wins!"
            surf = self.font.render(msg, True, WHITE)
            screen.blit(surf, (self.width//2 - surf.get_width()//2, self.height//2 - 60))
            sub = self.small.render("Preparing replay options…", True, GREY)
            screen.blit(sub, (self.width//2 - sub.get_width()//2, self.height//2 - 20))

        elif self.state == "replay_menu":
            title = self.font.render("Play Again?", True, WHITE)
            screen.blit(title, (self.width//2 - title.get_width()//2, self.height//2 - 100))
            opts = [
                "Press 3  for Best of 3",
                "Press 5  for Best of 5",
                "Press 7  for Best of 7",
                "Press Esc to Exit"
            ]
            for i, line in enumerate(opts):
                s = self.small.render(line, True, WHITE)
                screen.blit(s, (self.width//2 - s.get_width()//2, self.height//2 - 20 + i*28))

        # (Optional) FPS
        fps = self.small.render(f"{self.clock.get_fps():.0f} FPS", True, GREY)
        screen.blit(fps, (8, 8))
