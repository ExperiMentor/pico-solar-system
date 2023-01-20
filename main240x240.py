# Compared to main branch, this version:
# Changes display to Pico Explorer base at 240x240 instead of 240x135
# Enlarges Orrery to fill larger display
# Spaces planets' orbits to more realistcally simulate positions (toggle view by pressing X and Y together) 
# Adds depiction of Asteroid Belt
# Removes bouncing Pluto that no longer has a space
# Move text to not overlap enlarged Orrery display
# Takes out Backlight as it's not adjustable
# Takes out RGB as there is no RGBled on the board
# adds comments throughout as I reverse-engineered the programming


from picographics import PicoGraphics, DISPLAY_PICO_EXPLORER, PEN_RGB332
from pimoroni import Button
import time
import math
import gc
import machine
from micropython import const

gc.enable()
plusDays = 0
change = 0
orbits = 1 # 0 for Equal, or 1 for Pseudospacing between orbits

display = PicoGraphics(display=DISPLAY_PICO_EXPLORER, rotate=0, pen_type=PEN_RGB332) # 8bit colour as insuf memory for 16bit on larger display
button_a = Button(12) # +1 day
button_b = Button(13) # a AND b for reset to today
button_x = Button(14) # +30 days (previousy backlight adjust)
button_y = Button(15) # x AND y to chaange orbits between Equal and Pseudospaced

def circle(xpos0, ypos0, rad): # centre position and radius in pixels
    x = rad - 1
    y = 0
    dx = 1
    dy = 1
    err = dx - (rad << 1) # << is left bitshift - it means 2*rad
    while x >= y:
        display.pixel(xpos0 + x, ypos0 + y) # economise by drawing 8 points (2 per quadrant) from each calculated place
        display.pixel(xpos0 + y, ypos0 + x)
        display.pixel(xpos0 - y, ypos0 + x)
        display.pixel(xpos0 - x, ypos0 + y)
        display.pixel(xpos0 - x, ypos0 - y)
        display.pixel(xpos0 - y, ypos0 - x)
        display.pixel(xpos0 + y, ypos0 - x)
        display.pixel(xpos0 + x, ypos0 - y)
        if err <= 0:
            y += 1
            err += dy
            dy += 2
        if err > 0:
            x -= 1
            dx += 2
            err += dx - (rad << 1)


def check_for_buttons():
    global plusDays # time to display, number of seconds later than actual time
    global change
    global orbits
    if button_x.is_pressed:
        plusDays += 2592000 # +30 days
        change = 3
        time.sleep(0.2)
    elif button_y.is_pressed:
        plusDays -= 2592000 # -30 days
        change = 3
        time.sleep(0.2)
    if button_x.is_pressed and button_y.is_pressed: # change orbits between Equal and Pseudospaced
        orbits = 1 - orbits
        time.sleep(0.2)
    if button_a.is_pressed and button_b.is_pressed: # resets time to actual clock
        plusDays = 0
        change = 2
        time.sleep(0.5)
    elif button_a.is_pressed:
        plusDays += 86400 # +1 day
        change = 3
        time.sleep(0.2)
    elif button_b.is_pressed:
        plusDays -= 86400 # -1 day
        change = 3
        time.sleep(0.2)

def set_internal_time(utc_time): # can be deleted if use WiFi instead of RTC?
    rtc_base_mem = const(0x4005c000)
    atomic_bitmask_set = const(0x2000)
    (year, month, day, hour, minute, second, wday, yday) = time.localtime(utc_time)
    machine.mem32[rtc_base_mem + 4] = (year << 12) | (month << 8) | day
    machine.mem32[rtc_base_mem + 8] = ((hour << 16) | (minute << 8) | second) | (((wday + 1) % 7) << 24)
    machine.mem32[rtc_base_mem + atomic_bitmask_set + 0xc] = 0x10

def main():
    global change
    import planets
    # from pluto import Pluto
    set_time()
    HEIGHT = const(240)
    WIDTH = const(240)
    radius = (8, 14, 20, 28, 50, 65, 90, 114, 35, 40)
    
    def draw_planets(WIDTH, HEIGHT, ti):
        PL_CENTER = (int(WIDTH / 2), int(HEIGHT / 2)) # centre of sun
        betw = int((int((min(HEIGHT, WIDTH) / 2)) - 2) / 8) # betw pixels between planet orbitals. 14*8 +2 = 114 - fits half HEIGHT or WIDTH
        planets_dict = planets.coordinates(ti[0], ti[1], ti[2], ti[3], ti[4]) # time as Y, M, D, H, M

        display.set_pen(display.create_pen(255, 255, 0)) # draw sun in yellow
        display.circle(int(PL_CENTER[0]), int(PL_CENTER[1]), 4)

        display.set_pen(display.create_pen(90, 10, 90)) # draw asteroid belt
        if orbits == 0: # Equal spacing
            r = int(4.5 * betw + 2.5)
            circle(PL_CENTER[0], PL_CENTER[1], r)
        else: # Pseudospacing
            for r in range(radius[8], radius[9] + 1, 2): # draw several circles
                circle(PL_CENTER[0], PL_CENTER[1], r)
                        
        for i, el in enumerate(planets_dict):
            # i = planets 0 to 7
            # el is co-ordinates of that planet (calculated in planets.py, not the images)
            if orbits == 0: # Equal orbit spacing
                r = (i + 1) * betw + 2 # radius (pixels) of that orbital
            else: # Pseudospacing
                r = radius[i]
            display.set_pen(display.create_pen(40, 40, 40))
            circle(PL_CENTER[0], PL_CENTER[1], r) # draw orbital
            theta = math.atan2(el[0], el[1]) # angle to planet
            coordinates = (r * math.sin(theta), r * math.cos(theta)) # position of planet before offset centre
            coordinates = (coordinates[0] + PL_CENTER[0], HEIGHT - (coordinates[1] + PL_CENTER[1]))
            for ar in range(0, len(planets.planets_a[i][0]), 5): # step through bytes in 5s
                # planets_a contains a 7x7 pixel map for each planet, centred at 50,50
                # this looks up the colours in the array and displays a little picture of the planet at the right place
                x = planets.planets_a[i][0][ar] - 50 + coordinates[0]
                y = planets.planets_a[i][0][ar + 1] - 50 + coordinates[1] 
                if x >= 0 and y >= 0 and x < WIDTH and y < HEIGHT: # If off screen, don't try to display it
                    display.set_pen(display.create_pen(planets.planets_a[i][0][ar + 2], planets.planets_a[i][0][ar + 3],
                                    planets.planets_a[i][0][ar + 4]))
                    display.pixel(int(x), int(y))

    w = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    m = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    display.set_pen(display.create_pen(0, 0, 0))
    display.clear()
    display.update()
    gc.collect()

    mi = -1
    # pl = Pluto(display) # Turned off

    seconds_absolute = time.time()
    ti = time.localtime(seconds_absolute + plusDays)
    da = ti[2]

    draw_planets(WIDTH, HEIGHT, ti)
    start_int = time.ticks_ms()
    while True:
        ticks_dif = time.ticks_diff(time.ticks_ms(), start_int)
        if ticks_dif >= 1000 or time.time() != seconds_absolute:
            seconds_absolute = time.time()
            ti = time.localtime(seconds_absolute + plusDays)
            start_int = time.ticks_ms()
            ticks_dif = 0
        if change > 0:
            ti = time.localtime(seconds_absolute + plusDays)
        if da != ti[2]:
            da = ti[2]
            change = 3

        if change > 0:
            if change == 1:
                display.set_pen(display.create_pen(0, 0, 0))
                display.clear()
                draw_planets(WIDTH, HEIGHT, ti)
            else:
                change -= 1

        display.set_pen(display.create_pen(0, 0, 0))
        display.rectangle(0, 0, 50, 16) # blank over HH:MM
        display.rectangle(WIDTH - 48, HEIGHT - 26, WIDTH, HEIGHT) # Blank DAY
        display.rectangle(0, HEIGHT - 52, 25, HEIGHT - 34)
        display.rectangle(0, HEIGHT - 35, 35, HEIGHT - 19)
        display.rectangle(0, HEIGHT - 18, 50, HEIGHT)
        

        if mi != ti[4]:
            mi = ti[4]
            # pl.reset() # pluto turned off
        # pl.step(ti[5], ticks_dif)
        # pl.draw()

        display.set_font("bitmap8")
        display.set_pen(display.create_pen(244, 170, 30))
        display.text("%02d " % (ti[2]), 0, HEIGHT - 51, 99, 2) # DD MMM YYYY on separate rows
        display.text("%s " %  (m[ti[1] - 1]), 0, HEIGHT - 34, 99, 2) # MMM
        display.text("%d " % (ti[0]), 0, HEIGHT - 17, 99, 2) # YYYY
        # display.set_pen(display.create_pen(65, 129, 50))
        display.text(w[ti[6]], WIDTH - 48, HEIGHT - 25, 99, 3) # weekday name
        display.set_pen(display.create_pen(130, 255, 100))
        display.text("%02d:%02d" % (ti[3], ti[4]), 0, 0, 99, 2) # HH:MM
        display.update()
        check_for_buttons()
        time.sleep(0.01)


def set_time():
    try:
        import wifi_config
        set_time_ntp(wifi_config)
    except ImportError:
        ds3231
        ds = ds3231.ds3231()
        set_internal_time(ds.read_time())


def set_time_ntp(wifi_config):
    import network
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    print("Connecting to:", wifi_config.ssid)
    wlan.connect(wifi_config.ssid, wifi_config.key)
    while not wlan.isconnected() and wlan.status() >= 0:
        print("Waiting for connection...")
        time.sleep(5)
    print(wlan.ifconfig())
    print("Pico clock:", time.localtime())
    print("Setting time via ntp...")
    import ntptime
    ntpsuccess = False
    while not ntpsuccess:
        try:
            ntptime.settime()
            print("Time set: ", time.localtime())
            ntpsuccess = True
        except:
            print("NTP failure. Retrying.")
            time.sleep(5)


time.sleep(0.5)
main()
