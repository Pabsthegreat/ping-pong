
import pygame

class Paddle:
    def __init__(self, x, y, width, height, speed=420.0):
        self.x = float(x)
        self.y = float(y)
        self.width = width
        self.height = height
        self.speed = float(speed)

    def move(self, dy, screen_height):
        # dy is pixels per frame; typically computed from speed * dt
        self.y += dy
        if self.y < 0:
            self.y = 0
        if self.y + self.height > screen_height:
            self.y = screen_height - self.height

    def rect(self):
        return pygame.Rect(int(self.x), int(self.y), self.width, self.height)

    def auto_track(self, ball, screen_height, react=0.15):
        # simple proportional follow with max speed clamp
        target_delta = (ball.y + ball.height/2.0) - (self.y + self.height/2.0)
        vy = max(min(target_delta * react, self.speed), -self.speed)
        # clamp by screen bounds
        self.move(vy, screen_height)
