
import pygame
import random
import math

class Ball:
    def __init__(self, x, y, width, height, screen_width, screen_height):
        self.original_x = float(x)
        self.original_y = float(y)
        self.x = float(x)
        self.y = float(y)
        self.width = width
        self.height = height
        self.screen_width = screen_width
        self.screen_height = screen_height
        # pixels per second; engine converts to per-substep deltas
        self.speed_min = 420.0
        self.speed_max = 820.0
        self.serve(random.choice([True, False]))

    def serve(self, to_right=True, speed=None):
        if speed is None:
            speed = self.speed_min
        angle = math.radians(random.uniform(25, 65)) * random.choice([1, -1])
        vx = math.cos(angle) * (1 if to_right else -1)
        vy = math.sin(angle)
        self.x = self.original_x
        self.y = self.original_y
        self.vx = vx * speed
        self.vy = vy * speed

    def move(self, dt):
        # integrate position
        self.x += self.vx * dt
        self.y += self.vy * dt
        # wall bounce on top/bottom
        if self.y <= 0 and self.vy < 0:
            self.y = 0
            self.vy *= -1
        elif self.y + self.height >= self.screen_height and self.vy > 0:
            self.y = self.screen_height - self.height
            self.vy *= -1

    def rect(self):
        return pygame.Rect(int(self.x), int(self.y), self.width, self.height)

    def reset_after_score(self, last_dir_right=True):
        # serve to the player who conceded (alternate direction)
        self.serve(to_right=not last_dir_right)

    def speed_up(self, factor=1.05):
        # increase speed but clamp to max
        speed = (self.vx**2 + self.vy**2) ** 0.5
        speed = min(speed * factor, self.speed_max)
        ang = math.atan2(self.vy, self.vx)
        self.vx = math.cos(ang) * speed
        self.vy = math.sin(ang) * speed
