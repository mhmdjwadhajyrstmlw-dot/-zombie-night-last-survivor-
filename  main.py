
import pygame, math, random, sys, array

pygame.init()
try:
    pygame.mixer.init(22050, -16, 1, 512)
except Exception:
    pass

screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
W, H = screen.get_size()
clock = pygame.time.Clock()
pygame.display.set_caption("ZOMBIE NIGHT: LAST SURVIVOR")

font = pygame.font.Font(None, max(22, H // 29))
big = pygame.font.Font(None, max(42, H // 12))

WHITE = (240, 240, 230)
RED = (235, 35, 30)
GREEN = (50, 220, 90)
YELLOW = (255, 205, 65)

world = [
    "1111111111111111", "1000000000000001",
    "1011000000110001", "1000000000000001",
    "1000110001000001", "1000000000000001",
    "1010001100001001", "1000000000000001",
    "1001000000100001", "1000000000000001",
    "1000011000000001", "1000000000000001",
    "1010000000010001", "1000000000000001",
    "1000000000000001", "1111111111111111"
]
N = len(world)

px, py, ang = 1.8, 1.8, 0.0
hp, reserve, kills, wave = 100, 144, 0, 1
gameover = False
reloading = 0
flash = 0
last_shot = 0
last_groan = 0
daytime = 0.20

# Settings
settings_open = False
sound_enabled = True
look_sensitivity = 0.009
brightness = 1.0
player_speed = 1.0
day_night_enabled = True

# name, magazine capacity, damage, firing interval
weapons = [
    ["PISTOL", 12, 1, 260],
    ["SHOTGUN", 6, 2, 650],
    ["RIFLE", 30, 1, 120]
]
weapon = 0
ammo = weapons[weapon][1]

def make_sound(kind):
    if not pygame.mixer.get_init():
        return None
    rate = 22050
    duration = {"shot": .12, "groan": .5, "hit": .22,
                "reload": .2}[kind]
    samples = array.array("h")
    for i in range(int(rate * duration)):
        t = i / rate
        if kind == "shot":
            v = 19000 * math.exp(-t * 25) * random.uniform(-1, 1)
        elif kind == "reload":
            v = 7000 * math.sin(2 * math.pi * 260 * t)
        elif kind == "hit":
            v = 14000 * (1-t/duration) * math.sin(2*math.pi*75*t)
        else:
            v = 8000 * (1-t/duration) * math.sin(
                2*math.pi*(90+20*math.sin(t*9))*t)
        samples.append(max(-32767, min(32767, int(v))))
    try:
        return pygame.mixer.Sound(buffer=samples.tobytes())
    except Exception:
        return None

sounds = {k: make_sound(k) for k in
          ("shot", "groan", "hit", "reload")}

def play(kind):
    if not sound_enabled:
        return
    s = sounds.get(kind)
    if s:
        try:
            s.play()
        except Exception:
            pass

def wall(x, y):
    ix, iy = int(x), int(y)
    return ix < 0 or iy < 0 or ix >= N or iy >= N or world[iy][ix] == "1"

def txt(s, x, y, color=WHITE, f=None):
    screen.blit((f or font).render(str(s), True, color), (int(x), int(y)))

def button(rect, name, color):
    pygame.draw.rect(screen, color, rect, border_radius=13)
    pygame.draw.rect(screen, (210, 215, 210), rect, 2, border_radius=13)
    im = font.render(name, True, WHITE)
    screen.blit(im, im.get_rect(center=rect.center))

zombies = []

def spawn_wave():
    zombies.clear()
    for _ in range(min(3 + wave*2, 16)):
        for __ in range(200):
            x, y = random.uniform(2, N-2), random.uniform(2, N-2)
            if not wall(x, y) and math.hypot(x-px, y-py) > 4:
                zombies.append({
                    "x": x, "y": y, "hp": 2,
                    "anim": random.random()*6, "atk": 0
                })
                break

spawn_wave()

bs = max(48, min(75, int(min(W, H)*.115)))
fire_btn = pygame.Rect(W-bs-16, H-bs-20, bs, bs)
reload_btn = pygame.Rect(W-bs-16, H-2*bs-30, bs, bs)
run_btn = pygame.Rect(W-2*bs-28, H-bs-20, bs, bs)
aim_btn = pygame.Rect(W-2*bs-28, H-2*bs-30, bs, bs)
gun_btn = pygame.Rect(W-2*bs-28, H-3*bs-40, bs, bs)
settings_btn = pygame.Rect(12, 85, 135, 42)

joy_center = (int(W*.15), int(H*.79))
joy_radius = max(42, int(min(W, H)*.105))
joy_pos = joy_center
joy_active = False
look_active = False
look_x = 0
fire_held = False
sprint = False
aiming = False

def change_weapon():
    global weapon, ammo, reloading
    weapon = (weapon+1) % len(weapons)
    ammo = weapons[weapon][1]
    reloading = 0

def reload_gun():
    global reloading
    if ammo < weapons[weapon][1] and reserve > 0 and reloading == 0:
        reloading = 36
        play("reload")

def shoot():
    global ammo, flash, kills, last_shot
    now = pygame.time.get_ticks()
    if gameover or reloading or ammo <= 0:
        return
    if now-last_shot < weapons[weapon][3]:
        return
    last_shot = now
    ammo -= 1
    flash = 3
    play("shot")

    targets = []
    for z in zombies:
        dx, dy = z["x"]-px, z["y"]-py
        d = math.hypot(dx, dy)
        rel = (math.atan2(dy, dx)-ang+math.pi)%(2*math.pi)-math.pi
        tolerance = min(.19, .055+.45/d)
        if d < 13 and abs(rel) < tolerance:
            targets.append((d, z))
    targets.sort(key=lambda a: a[0])

    for d, z in targets:
        blocked = False
        steps = max(1, int(d*18))
        for i in range(1, steps):
            t = i/steps
            if wall(px+(z["x"]-px)*t, py+(z["y"]-py)*t):
                blocked = True
                break
        if not blocked:
            z["hp"] -= weapons[weapon][2]
            if z["hp"] <= 0 and z in zombies:
                zombies.remove(z)
                kills += 1
            break

def update_zombies():
    global hp, gameover, wave
    for z in zombies:
        dx, dy = px-z["x"], py-z["y"]
        d = math.hypot(dx, dy)
        z["anim"] += .16

        if d > .62:
            speed = .014 + min(wave, 8)*.0017
            nx, ny = z["x"]+dx/d*speed, z["y"]+dy/d*speed
            if not wall(nx, z["y"]):
                z["x"] = nx
            if not wall(z["x"], ny):
                z["y"] = ny
        else:
            z["atk"] += 1
            if z["atk"] >= 22:
                hp = max(0, hp-8)
                z["atk"] = 0
                play("hit")
                if hp == 0:
                    gameover = True

    if not zombies and not gameover:
        wave += 1
        spawn_wave()

def draw_world():
    phase = daytime % 1
    sun = max(0, math.sin(phase*2*math.pi))
    daylight = int(18+sun*95*brightness)
    screen.fill((max(5, daylight//2), max(7, daylight//2+8),
                 max(12, daylight//2+18)))
    horizon = H//2

    if sun > .05:
        sx = int(W*(.75-.5*phase))
        pygame.draw.circle(screen, (255, int(125+sun*100), 95),
                           (sx, int(H*.28)), max(10, H//17))

    pygame.draw.rect(screen,
        (int(15+sun*38), int(17+sun*34), int(17+sun*23)),
        (0, horizon, W, H//2))

    rays = max(100, min(180, W//5))
    rw = W/rays
    zbuf = [15.0]*rays

    for r in range(rays):
        a = ang-math.radians(34)+math.radians(68)*(r+.5)/rays
        d = .05
        while d < 15:
            rx, ry = px+math.cos(a)*d, py+math.sin(a)*d
            if wall(rx, ry):
                break
            d += .04
        d = max(.05, d*math.cos(a-ang))
        zbuf[r] = d
        hh = min(H*2, int(H*.88/d))
        sh = max(12, int((daylight+50)-d*11))
        x = int(r*rw)
        pygame.draw.rect(screen,
            (sh, max(10, sh-9), max(8, sh-15)),
            (x, horizon-hh//2, int(rw)+1, hh))
        if int(rx*4)%4 == 0:
            pygame.draw.line(screen, (sh//2, sh//2, sh//2),
                (x, horizon-hh//2), (x, horizon+hh//2), 1)
    return zbuf

def draw_zombies(zbuf):
    visible = []
    for z in zombies:
        dx, dy = z["x"]-px, z["y"]-py
        d = math.hypot(dx, dy)
        rel = (math.atan2(dy, dx)-ang+math.pi)%(2*math.pi)-math.pi
        if abs(rel) < .8 and d > .1:
            visible.append((d, rel, z))
    visible.sort(reverse=True)

    for d, rel, z in visible:
        sx = W/2+math.tan(rel)*(W/2)/math.tan(math.radians(34))
        size = min(H, int(H*.72/d))
        if size < 4 or sx < -size or sx > W+size:
            continue
        ri = max(0, min(len(zbuf)-1, int(sx/W*len(zbuf))))
        if d > zbuf[ri]+.2:
            continue

        # Anchor feet to the ground plane
        feet = int(H/2+H*.48/d)
        hh = max(8, int(H*.85/d))
        head = max(5, int(hh*.23))
        bw = max(7, int(hh*.36))
        bob = int(math.sin(z["anim"])*hh*.018)
        top = feet-hh+bob
        x = int(sx)
        swing = int(math.sin(z["anim"])*hh*.06)

        pygame.draw.line(screen, (39,62,39),
            (x-bw//5, feet-hh//3),
            (x-bw//4+swing, feet), max(3, hh//13))
        pygame.draw.line(screen, (39,62,39),
            (x+bw//5, feet-hh//3),
            (x+bw//4-swing, feet), max(3, hh//13))

        pygame.draw.rect(screen, (55,84,49),
            (x-bw//2, top+head//2, bw, int(hh*.42)))

        # Arms
        pygame.draw.line(screen, (78,115,65),
            (x-bw//2, top+head),
            (x-bw, top+head+hh//4), max(3, hh//12))
        pygame.draw.line(screen, (78,115,65),
            (x+bw//2, top+head),
            (x+bw, top+head+hh//4), max(3, hh//12))

        # Knife
        kx, ky = x+bw, top+head+hh//4
        pygame.draw.line(screen, (95,67,45),
            (kx-2, ky-2), (kx+max(5,hh//7), ky-hh//10),
            max(2,hh//25))
        pygame.draw.line(screen, (210,215,220),
            (kx+max(5,hh//7), ky-hh//10),
            (kx+max(9,hh//4), ky-hh//5), max(2,hh//35))

        pygame.draw.ellipse(screen, (87,132,73),
            (x-head//2, top, head, head))
        pygame.draw.rect(screen, (35,38,28),
            (x-head//4, top+head//2, head//2, max(2,head//5)))
        er = max(2, size//38)
        pygame.draw.circle(screen, RED, (x-head//6, top+head//3), er)
        pygame.draw.circle(screen, RED, (x+head//6, top+head//3), er)

        bar = max(12, bw)
        pygame.draw.rect(screen, (25,20,20), (x-bar//2, top-8, bar, 4))
        pygame.draw.rect(screen, GREEN,
            (x-bar//2, top-8, int(bar*z["hp"]/2), 4))

def draw_gun():
    gw, gh = W//5, H//4
    x, y = W//2-gw//2, H-gh+int(math.sin(pygame.time.get_ticks()*.009)*3)
    color = [(55,60,62), (80,65,53), (30,35,39)][weapon]
    pygame.draw.rect(screen, (20,22,23), (x+gw//3,y,gw//3,gh))
    pygame.draw.rect(screen, color, (x+gw//5,y+gh//3,gw*3//5,gh//2))
    pygame.draw.rect(screen, (25,26,28), (x+gw//3,y+gh//2,gw//3,gh//2))
    if flash:
        pygame.draw.polygon(screen, YELLOW, [
            (W//2,y), (W//2-24,y-45),
            (W//2,y-25), (W//2+24,y-45)])

# Settings menu
def draw_settings():
    panel = pygame.Rect(W//2-W//3, H//2-H//3, 2*W//3, 2*H//3)
    pygame.draw.rect(screen, (20,25,32), panel, border_radius=18)
    pygame.draw.rect(screen, (180,190,190), panel, 2, border_radius=18)
    title = big.render("SETTINGS", True, WHITE)
    screen.blit(title, title.get_rect(center=(W//2, panel.y+35)))

    values = [
        ("SOUND", "ON" if sound_enabled else "OFF"),
        ("SENSITIVITY", f"{look_sensitivity:.3f}"),
        ("BRIGHTNESS", f"{brightness:.2f}"),
        ("MOVE SPEED", f"{player_speed:.2f}"),
        ("DAY / NIGHT", "ON" if day_night_enabled else "OFF")
    ]
    rows = []
    row_h = max(34, panel.height//8)
    for i, (name, val) in enumerate(values):
        y = panel.y+80+i*row_h
        txt(name, panel.x+20, y)
        r = pygame.Rect(panel.right-140, y-5, 118, 34)
        pygame.draw.rect(screen, (55,75,82), r, border_radius=8)
        im = font.render(val, True, YELLOW)
        screen.blit(im, im.get_rect(center=r.center))
        rows.append(r)

    back = pygame.Rect(W//2-95, panel.bottom-48, 190, 36)
    pygame.draw.rect(screen, (110,45,40), back, border_radius=9)
    im = font.render("BACK TO GAME", True, WHITE)
    screen.blit(im, im.get_rect(center=back.center))
    return rows, back

def settings_click(pos, rows, back):
    global settings_open, sound_enabled, look_sensitivity
    global brightness, player_speed, day_night_enabled
    if back.collidepoint(pos):
        settings_open = False
        return True
    for i, r in enumerate(rows):
        if r.collidepoint(pos):
            if i == 0:
                sound_enabled = not sound_enabled
            elif i == 1:
                look_sensitivity += .003
                if look_sensitivity > .021:
                    look_sensitivity = .003
            elif i == 2:
                brightness += .25
                if brightness > 1.5:
                    brightness = .5
            elif i == 3:
                player_speed += .25
                if player_speed > 1.75:
                    player_speed = .5
            elif i == 4:
                day_night_enabled = not day_night_enabled
            return True
    return False

def handle_press(pos):
    global joy_active, joy_pos, look_active, look_x
    global fire_held, sprint, aiming, settings_open

    if settings_open:
        rows, back = draw_settings()
        settings_click(pos, rows, back)
        return

    if settings_btn.collidepoint(pos):
        settings_open = True
    elif fire_btn.collidepoint(pos):
        fire_held = True
        shoot()
    elif reload_btn.collidepoint(pos):
        reload_gun()
    elif run_btn.collidepoint(pos):
        sprint = not sprint
    elif aim_btn.collidepoint(pos):
        aiming = not aiming
    elif gun_btn.collidepoint(pos):
        change_weapon()
    elif pos[0] < W*.4 and pos[1] > H*.55:
        joy_active = True
        joy_pos = pos
    elif pos[0] > W*.4:
        look_active = True
        look_x = pos[0]

running_game = True
while running_game:
    clock.tick(30)
    flash = max(0, flash-1)

    if day_night_enabled:
        daytime = (daytime+.00010)%1

    if reloading:
        reloading -= 1
        if reloading == 0:
            amount = min(weapons[weapon][1]-ammo, reserve)
            ammo += amount
            reserve -= amount

    for e in pygame.event.get():
        if e.type == pygame.QUIT:
            running_game = False
        elif e.type == pygame.KEYDOWN:
            if e.key == pygame.K_ESCAPE:
                if settings_open:
                    settings_open = False
                else:
                    running_game = False
            elif e.key == pygame.K_SPACE:
                shoot()
            elif e.key == pygame.K_r:
                reload_gun()
            elif e.key == pygame.K_q:
                change_weapon()
            elif e.key == pygame.K_LEFT:
                ang -= .12
            elif e.key == pygame.K_RIGHT:
                ang += .12

        elif e.type == pygame.MOUSEBUTTONDOWN:
            handle_press(e.pos)
        elif e.type == pygame.MOUSEMOTION and pygame.mouse.get_pressed()[0]:
            if joy_active and e.pos[0] < W*.45:
                joy_pos = e.pos
            elif look_active and not settings_open:
                ang += e.rel[0]*look_sensitivity
        elif e.type == pygame.MOUSEBUTTONUP:
            joy_active = False
            joy_pos = joy_center
            look_active = False
            fire_held = False

        elif e.type == pygame.FINGERDOWN:
            handle_press((int(e.x*W), int(e.y*H)))
        elif e.type == pygame.FINGERMOTION:
            pos = (int(e.x*W), int(e.y*H))
            if joy_active and pos[0] < W*.45:
                joy_pos = pos
            elif look_active and not settings_open:
                ang += (pos[0]-look_x)*look_sensitivity
                look_x = pos[0]
        elif e.type == pygame.FINGERUP:
            pos = (int(e.x*W), int(e.y*H))
            if pos[0] < W*.45:
                joy_active = False
                joy_pos = joy_center
            if pos[0] > W*.4:
                look_active = False
            if fire_btn.collidepoint(pos):
                fire_held = False

    keys = pygame.key.get_pressed()
    forward = int(keys[pygame.K_w] or keys[pygame.K_UP]) - int(
        keys[pygame.K_s] or keys[pygame.K_DOWN])
    side = int(keys[pygame.K_d])-int(keys[pygame.K_a])

    if joy_active and not settings_open:
        dx, dy = joy_pos[0]-joy_center[0], joy_pos[1]-joy_center[1]
        mag = max(1, math.hypot(dx,dy))
        power = min(1, mag/joy_radius)
        forward += -dy/mag*power
        side += dx/mag*power

    speed = (.075 if sprint else .043)*player_speed
    if not gameover and not settings_open:
        mx = (math.cos(ang)*forward+math.cos(ang+math.pi/2)*side)*speed
        my = (math.sin(ang)*forward+math.sin(ang+math.pi/2)*side)*speed
        if not wall(px+mx,py):
            px += mx
        if not wall(px,py+my):
            py += my
        update_zombies()

    if fire_held and pygame.time.get_ticks()-last_shot > weapons[weapon][3]:
        shoot()

    now = pygame.time.get_ticks()
    if zombies and now-last_groan > 7000:
        play("groan")
        last_groan = now

    zbuf = draw_world()
    draw_zombies(zbuf)
    draw_gun()

    phase = daytime % 1
    sun = max(0, math.sin(phase*2*math.pi))
    darkness = int((1-sun)*155)
    if darkness > 25:
        shade = pygame.Surface((W,H), pygame.SRCALPHA)
        shade.fill((3,5,19,darkness))
        screen.blit(shade,(0,0))

    gap = 5 if aiming else 9
    pygame.draw.line(screen, WHITE, (W//2-gap,H//2),
                     (W//2+gap,H//2), 2)
    pygame.draw.line(screen, WHITE, (W//2,H//2-gap),
                     (W//2,H//2+gap), 2)

    pygame.draw.rect(screen,(25,20,20),(12,12,W//3,18))
    pygame.draw.rect(screen,RED,(12,12,int(W//3*hp/100),18))
    txt("HP "+str(hp),14,36)
    txt(weapons[weapon][0]+"  "+str(ammo)+"/"+str(reserve),14,64,YELLOW)
    txt("WAVE "+str(wave),W//2-45,15)
    txt("KILLS "+str(kills),W-145,15)
    txt("DAY" if sun>.45 else "NIGHT",W//2-30,H-38,YELLOW)

    pygame.draw.circle(screen,(25,30,34),joy_center,joy_radius)
    pygame.draw.circle(screen,(175,185,180),joy_center,joy_radius,3)
    pygame.draw.circle(screen,(75,100,105),joy_pos,max(18,joy_radius//2))
    pygame.draw.circle(screen,WHITE,joy_pos,max(18,joy_radius//2),2)

    button(fire_btn,"FIRE",(145,30,25))
    button(reload_btn,"RLD",(55,65,68))
    button(run_btn,"RUN" if not sprint else "WALK",(40,90,60))
    button(aim_btn,"AIM ON" if aiming else "AIM",(65,65,85))
    button(gun_btn,"GUN",(95,70,35))
    button(settings_btn,"SETTINGS",(55,65,80))

    if reloading:
        txt("RELOADING...",W//2-65,H//2+45,YELLOW)

    if settings_open:
        rows, back = draw_settings()

    if gameover:
        shade = pygame.Surface((W,H), pygame.SRCALPHA)
        shade.fill((0,0,0,205))
        screen.blit(shade,(0,0))
        txt("YOU DIED",W//2-100,H//2-50,RED,big)
        txt("KILLS "+str(kills),W//2-45,H//2+8)
        txt("Close and run again to restart",
            W//2-140,H//2+45)

    pygame.display.flip()

pygame.quit()
sys.exit()
