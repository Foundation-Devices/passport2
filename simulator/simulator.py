#!/usr/bin/env python3
#
# (c) Copyright 2018 by Coinkite Inc. This file is part of Coldcard <coldcardwallet.com>
# and is covered by GPLv3 license found in COPYING.
#
# Simulate the hardware of a Coldcard. Particularly the OLED display and
# the numberpad.
#
# This is a normal python3 program, not micropython. It communicates with a running
# instance of micropython that simulates the micropython that would be running in the main
# chip.numpad_
#
import fcntl
import math
import os
import pdb
import pty
import subprocess
import sys
import tempfile
import termios
import time
import tty
from binascii import a2b_hex, b2a_hex
from select import select

# Simple interface using OpenCV to show a camera and capture frames at the same resolution
# as the Passport camera.
import cv2
import sdl2.ext
from PIL import Image

MPY_UNIX = 'l-port/micropython'

UNIX_SOCKET_PATH = '/tmp/passport-simulator.sock'

IS_COLOR = True if sys.argv[1] == 'color' else False

if IS_COLOR:
    DISP_WIDTH = 240
    DISP_HEIGHT = 320
    BYTES_PER_SCANLINE = DISP_WIDTH * 2

    # top-left coord of OLED area; size is 1:1 with real pixels
    OLED_ACTIVE = (88, 104)
    # This actually blue, but changing green to blue everywhere would be a huge PR!
    LED_GREEN = (180, 69)
    LED_RED = (158, 67)

    # keypad touch buttons
    NAVPAD_LEFT_LEFT = 147
    NAVPAD_LEFT_TOP = 516
    NAVPAD_RIGHT_LEFT = 231
    NAVPAD_RIGHT_TOP = 516
    NAVPAD_UP_LEFT = 188
    NAVPAD_UP_TOP = 484
    NAVPAD_DOWN_LEFT = 188
    NAVPAD_DOWN_TOP = 550

    NAVPAD_BTN_WIDTH = 36
    NAVPAD_BTN_HEIGHT = 46

    NAVPAD_SELECT_LEFT = 280
    NAVPAD_SELECT_TOP = 468
    NAVPAD_SELECT_WIDTH = 48
    NAVPAD_SELECT_HEIGHT = 120

    NAVPAD_BACK_LEFT = 85
    NAVPAD_BACK_TOP = 468
    NAVPAD_BACK_WIDTH = 48
    NAVPAD_BACK_HEIGHT = 120

    KEYPAD_LEFT = 84
    KEYPAD_TOP = 605
    KEYPAD_KEY_WIDTH = 82
    KEYPAD_KEY_HEIGHT = 70

else:
    DISP_WIDTH = 230
    DISP_HEIGHT = 303
    BYTES_PER_SCANLINE = 30  # Because driver requires 240 pixels

    # top-left coord of OLED area; size is 1:1 with real pixels... 220x303 pixels
    OLED_ACTIVE = (90, 104)
    # This actually blue, but changing green to blue everywhere would be a huge PR!
    LED_GREEN = (180, 69)
    LED_RED = (158, 67)

    # keypad touch buttons
    NAVPAD_LEFT_LEFT = 133
    NAVPAD_LEFT_TOP = 484
    NAVPAD_RIGHT_LEFT = 231
    NAVPAD_RIGHT_TOP = 484
    NAVPAD_UP_LEFT = 182
    NAVPAD_UP_TOP = 434
    NAVPAD_DOWN_LEFT = 182
    NAVPAD_DOWN_TOP = 534

    NAVPAD_BTN_WIDTH = 49
    NAVPAD_BTN_HEIGHT = 50

    NAVPAD_SELECT_LEFT = 281
    NAVPAD_SELECT_TOP = 472
    NAVPAD_SELECT_WIDTH = 50
    NAVPAD_SELECT_HEIGHT = 75

    NAVPAD_BACK_LEFT = 77
    NAVPAD_BACK_TOP = 472
    NAVPAD_BACK_WIDTH = 50
    NAVPAD_BACK_HEIGHT = 75

    KEYPAD_LEFT = 87
    KEYPAD_TOP = 610
    KEYPAD_KEY_WIDTH = 83
    KEYPAD_KEY_HEIGHT = 60


DISP_BUF_SIZE = BYTES_PER_SCANLINE * DISP_HEIGHT
print('BYTES_PER_SCANLINE=' + str(BYTES_PER_SCANLINE))
print('DISP_BUF_SIZE=' + str(DISP_BUF_SIZE))


class OLEDSimulator:

    def __init__(self, factory):
        self.movie = None
        s = factory.create_software_sprite((DISP_WIDTH, DISP_HEIGHT), bpp=32)
        self.sprite = s
        s.x, s.y = OLED_ACTIVE
        s.depth = 1

        # FOUNDATION: Screen colors are defined here
        self.fg = sdl2.ext.prepare_color('#D8D8D8', s)
        self.bg = sdl2.ext.prepare_color('#111', s)
        sdl2.ext.fill(s, self.bg)

        # Camera init
        self.cam = None

    # Take a full-screen update of the OLED contents and display
    def render_mono(self, window, buf):
        assert len(buf) == DISP_BUF_SIZE, len(buf)
        line_count = 0
        for y in range(DISP_HEIGHT):
            byte_offset = y * BYTES_PER_SCANLINE
            line_start = 0
            line_end = 0
            last_val = 1 if buf[byte_offset] & 0x80 else 0

            for x in range(1, DISP_WIDTH):
                val = None
                if x < DISP_WIDTH:
                    b = buf[byte_offset + (x // 8)]
                    mask = 0x80 >> x % 8
                    val = 1 if b & mask else 0
                else:
                    val = 99  # Different from both others

                if val == last_val:
                    line_end = x
                    if x != DISP_WIDTH - 1:
                        # print('last_val=' + str(last_val) + ' val=' + str(val))
                        # print('  y=' + str(y) + ': ' + str(line_start) + ',' + str(line_end))
                        continue

                # Pixel changed, so draw the line
                if (last_val):
                    color = self.fg
                else:
                    color = self.bg

                # Draw the line
                sdl2.ext.line(self.sprite, color,
                              (line_start, y, line_end + 1, y))
                line_count += 1
                # print('  DRAW: y=' + str(y) + ': ' + str(line_start) + ',' + str(line_end), )
                line_start = x
                line_end = line_start
                last_val = val

        # print('render_mono(): line_count={}'.format(line_count))
        if self.movie is not None:
            self.new_frame()

    # Take a full-screen update of the OLED contents and display
    def render_color(self, window, buf):
        assert len(buf) == DISP_BUF_SIZE, len(buf)

        for y in range(DISP_HEIGHT):
            y_offset = (y * DISP_WIDTH) * 2
            line_start = 0
            line_end = 0

            px0 = buf[y_offset + 1]
            px1 = buf[y_offset]
            r = px0 & 0xF8
            g = ((px0 & 0x07) << 5) | ((px1 & 0xE0) >> 3)
            b = (px1 & 0x1F) << 3
            last_color = (r << 16) | (g << 8) | b

            for x in range(1, DISP_WIDTH):
                offset = y_offset + (x * 2)

                if x < DISP_WIDTH:
                    px0 = buf[offset + 1]
                    px1 = buf[offset]
                    r = px0 & 0xF8
                    g = ((px0 & 0x07) << 5) | ((px1 & 0xE0) >> 3)
                    b = (px1 & 0x1F) << 3
                    color = (r << 16) | (g << 8) | b
                else:
                    color = 0xFF000000

                if color == last_color:
                    line_end = x
                    if x != DISP_WIDTH - 1:
                        continue

                sdl2.ext.line(self.sprite, last_color,
                              (line_start, y, line_end + 1, y))

                line_start = x
                line_end = line_start
                last_color = color

        if self.movie is not None:
            self.new_frame()

    def snapshot(self):
        filename = time.strftime('../snapshots/snapshot-$j-%H:%M:%S.png')
        with tempfile.NamedTemporaryFile() as tmp:
            sdl2.SDL_SaveBMP(self.sprite.surface, tmp.name.encode('ascii'))
            tmp.file.seek(0)
            img = Image.open(tmp.file)
            img.save(filename)

        print("Snapshot saved: %s" % filename.split('/', 1)[1])

    def movie_start(self):
        self.movie = []
        self.last_frame = time.time() - 0.1
        print("Movie recording started.")
        self.new_frame()

    def movie_end(self):
        import imageio
        if self.movie == None:
            return

        filename = time.strftime('../movie-%j-%H%M%S.gif')
        # from PIL import Image, ImageSequence
        #
        # dt0, img = self.movie[0]
        #
        # img.save(filename, save_all=True, append_images=[fr for _, fr in self.movie[1:]],
        #          duration=[max(dt, 20) for dt, _ in self.movie], loop=0, optimize=False)

        imageio.mimsave(filename, self.movie, duration=0.3)

        print("Movie saved: %s (%d frames)" %
              (filename.split('/', 1)[1], len(self.movie)))

        self.movie = None

    def new_frame(self):
        from PIL import Image

        dt = int((time.time() - self.last_frame) * 1000)
        self.last_frame = time.time()

        with tempfile.NamedTemporaryFile() as tmp:
            sdl2.SDL_SaveBMP(self.sprite.surface, tmp.name.encode('ascii'))
            tmp.file.seek(0)
            img = Image.open(tmp.file)
            img = img.convert('RGB')
            self.movie.append(img)


class CameraSimulator:
    def __init__(self):
        self.cam = None

    def is_enabled(self):
        return self.cam != None

    def enable(self):
        # TODO: Add command line parameter to select camera index.  Note that sometimes a camera index might be
        #       skipped (e.g., 0 is valid, 1 is not valid, but 2 is valid).
        camera_index = 0
        self.cam = cv2.VideoCapture(camera_index)
        self.cam.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        self.cam.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        self.active = True

    def disable(self):
        self.cam.release()
        cv2.destroyAllWindows()
        self.cam = None

    def capture(self, want_bytes, filename=None):
        # Sometimes this returns NULL the first time
        img = None
        while True:
            ret, img = self.cam.read()
            if ret:
                break

        h, w, c = img.shape
        # print("w={} h={} c={}".format(w, h, c))

        # Crop the image
        new_width = 576
        new_height = 480
        half_excess_width = (w - new_width) // 2
        half_excess_height = (h - new_height) // 2
        # print("new_width={} new_height={} half_excess_width={}".format(new_width, new_height, half_excess_width))

        cropped_img = img[half_excess_height:half_excess_height + new_height,
                          half_excess_width:half_excess_width + new_width]

        h, w, c = cropped_img.shape
        # print("cropped_img: w={} h={} c={}".format(w, h, c))

        cam_width = 350
        cam_height = 350
        resized = cv2.resize(
            cropped_img, (cam_width, cam_height), interpolation=cv2.INTER_CUBIC)
        h, w, c = resized.shape
        # print("########################### resized: w={} h={} c={}".format(w, h, c))

        if not want_bytes:
            return resized

        # # Only rotate for Gen 1, since Gen 1.2 production boards are landscape now
        # if not IS_COLOR:
        #     final = cv2.rotate(resized, cv2.cv2.ROTATE_90_CLOCKWISE)
        #     h, w, c = final.shape
        #     print("########################### rotated: w={} h={} c={}".format(w, h, c))
        # else:
        #     print('NO ROTATION')
        #     final = resized
        final = resized

        # Write to file if filename is given
        if (filename):
            cv2.imwrite(filename, final)

        # Convert to bytes instead of cv2 image
        rgb_bytes = final.tobytes()
        rgb565_bytes = bytearray(cam_height * cam_width * 2)
        for y in range(cam_height):
            for x in range(cam_width):
                pix_pos = ((y * cam_width) + x)
                src_offset = pix_pos * 3
                b = rgb_bytes[src_offset] >> 3
                g = rgb_bytes[src_offset + 1] >> 2
                r = rgb_bytes[src_offset + 2] >> 3
                #print('rgb={} {} {}'.format(hex(r), hex(g), hex(b)))

                # r = 0xFF >> 3
                # g = 0x80 >> 2
                # b = 0xFF >> 3
                dst_offset = pix_pos * 2

                px0 = r << 3 | (g >> 3)
                px1 = ((g & 0x7) << 5) | b
                rgb565_bytes[dst_offset] = px1
                rgb565_bytes[dst_offset + 1] = px0
                # if dst_offset == 0:
                #     print('565={} {}'.format(hex(px0), hex(px1)))

        return rgb565_bytes


def start():
    print('''Passport Simulator: Commands (over simulated window):
  - Control-Q to quit
  - Z to snapshot screen.
  - S/E to start/end movie recording
''')
    sdl2.ext.init()

    factory = sdl2.ext.SpriteFactory(sdl2.ext.SOFTWARE)
    if IS_COLOR:
        bg = factory.from_image("background-gen1.2.png")
    else:
        bg = factory.from_image("background-gen1.png")
    bg.depth = 2
    oled = OLEDSimulator(factory)

    cam = CameraSimulator()

    # for genuine/caution lights
    led_red = factory.from_image("led-red.png")
    led_red.depth = 3
    led_red.x, led_red.y = LED_RED
    led_green = factory.from_image("led-green.png")
    led_green.depth = 3
    led_green.x, led_green.y = LED_GREEN

    window = sdl2.ext.Window("Passport Simulator", size=bg.size)
    window.position = (863, 0)
    window.show()

    ico = factory.from_image('program-icon.png')
    sdl2.SDL_SetWindowIcon(window.window, ico.surface)

    spriterenderer = factory.create_sprite_render_system(window)

    genuine_state = False
    # spriterenderer.process(window, (oled.sprite, bg, led_red))
    spriterenderer.process(window, (oled.sprite, bg))

    # capture exec path and move into intended working directory
    # mpy_exec = os.path.realpath('l-port/passport-mpy')
    env = os.environ.copy()
    env['MICROPYPATH'] = ':' + os.path.realpath('./sim_modules') + \
                         ':' + os.path.realpath('../ports/stm32/boards/Passport/modules') + \
                         ':' + os.path.realpath('../extmod')

    oled_r, oled_w = os.pipe()      # fancy OLED display
    led_r, led_w = os.pipe()        # genuine LED
    numpad_r, numpad_w = os.pipe()  # keys
    cam_cmd_r, cam_cmd_w = os.pipe()  # camera commands
    cam_img_r, cam_img_w = os.pipe()  # camera images

    # manage unix socket cleanup for client
    def sock_cleanup():
        import os
        if os.path.exists(UNIX_SOCKET_PATH):
            os.unlink(UNIX_SOCKET_PATH)
    sock_cleanup()
    import atexit
    atexit.register(sock_cleanup)

    # handle connection to real hardware, on command line
    # - open the serial device
    # - get buffering/non-blocking right
    # - pass in open fd numbers
    pass_fds = [oled_w, numpad_r, led_w, cam_cmd_w, cam_img_r]

    os.chdir('./work')
    # We use RAM for flash simulation, so make sure to allocate enough here.  3m seems good.
    passport_cmd = ['../../ports/unix/passport-mpy',
                    '-X', 'heapsize=30m',
                    '-i', '../sim_boot.py',
                    str(oled_w), str(numpad_r), str(led_w), str(cam_cmd_w), str(cam_img_r)] \
        + sys.argv[1:]
    print('cc_cmd: {}'.format(passport_cmd))

    xterm = subprocess.Popen(['xterm', '-title', 'Passport Simulator REPL',
                              '-geom', '132x72+0+0', '-e'] + passport_cmd,
                             env=env,
                             stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                             pass_fds=pass_fds, shell=False)

    print("COMMAND: " + " ".join(passport_cmd))

    # reopen as binary streams
    oled_rx = open(oled_r, 'rb', closefd=0, buffering=0)
    led_rx = open(led_r, 'rb', closefd=0, buffering=0)
    numpad_tx = open(numpad_w, 'wb', closefd=0, buffering=0)
    cam_cmd_rx = open(cam_cmd_r, 'rb', closefd=0, buffering=0)
    cam_img_wx = open(cam_img_w, 'wb', closefd=0, buffering=0)

    # setup no blocking
    for r in [oled_rx, led_rx]:
        fl = fcntl.fcntl(r, fcntl.F_GETFL)
        fcntl.fcntl(r, fcntl.F_SETFL, fl | os.O_NONBLOCK)

    readables = [oled_rx, led_rx, cam_cmd_rx]

    running = True

    pressed = set()

    def send_event(ch, is_down):
        before = len(pressed)

        if is_down:
            pressed.add(ch)
        else:
            pressed.discard(ch)

        if len(pressed) != before:
            str = '{}:{}'.format(ch, 'd' if is_down else 'u')
            msg = bytes(str, 'ascii') + b'\n'
            numpad_tx.write(msg)

    cam_window_name = 'Passport QR Scanner'

    screen_buf = None

    while running:
        events = sdl2.ext.get_events()
        for event in events:
            if event.type == sdl2.SDL_QUIT:
                running = False
                break

            if event.type == sdl2.SDL_KEYUP or event.type == sdl2.SDL_KEYDOWN:
                try:
                    ch = chr(event.key.keysym.sym)
                    # print('0x%0x => %s  mod=0x%x' %
                    #       (event.key.keysym.sym, ch, event.key.keysym.mod))
                except:
                    # things like 'shift' by itself
                    # print('0x%0x' % event.key.keysym.sym)
                    if 0x4000004f <= event.key.keysym.sym <= 0x40000052:
                        # arrow keys
                        ch = 'rldu'[event.key.keysym.sym - 0x4000004f]
                    else:
                        ch = '\0'

                # remap ESC/Enter
                if ch == '\x1b':
                    ch = 'x'
                elif ch == '\x0d':
                    ch = 'y'

                if ch == 'q' and event.key.keysym.mod == 0x40:
                    # control-Q
                    running = False
                    break

                if ch == '3' and event.key.keysym.mod == 0x01:
                    ch = '#'

                if (ch == '8' and event.key.keysym.mod == 0x01) or ord(ch) == 8:  # Backspace
                    ch = '*'

                if ch == 'w':
                    if event.type == sdl2.SDL_KEYDOWN:
                        if cam.is_enabled():
                            cam.disable()
                        else:
                            cam.enable()
                    break

                if ch in 'zse':
                    if event.type == sdl2.SDL_KEYDOWN:
                        if ch == 'z':
                            oled.snapshot()
                        if ch == 's':
                            oled.movie_start()
                        if ch == 'e':
                            oled.movie_end()
                    continue

                # print('KEY: {}'.format(ch))

                if ch not in '0123456789xyrldu*#':
                    if ch.isprintable():
                        print("Invalid key: '%s'" % ch)
                    continue

                send_event(ch, event.type == sdl2.SDL_KEYDOWN)

            if event.type == sdl2.SDL_MOUSEBUTTONDOWN:
                x = event.button.x
                y = event.button.y
                print("x={} y={}".format(x, y))
                # Up
                if y >= NAVPAD_UP_TOP and y <= NAVPAD_UP_TOP + NAVPAD_BTN_HEIGHT:
                    if x >= NAVPAD_UP_LEFT and x <= NAVPAD_UP_LEFT + NAVPAD_BTN_WIDTH:
                        print('Press: u')
                        send_event('u', True)
                        continue

                # Down
                if y >= NAVPAD_DOWN_TOP and y <= NAVPAD_DOWN_TOP + NAVPAD_BTN_HEIGHT:
                    if x >= NAVPAD_DOWN_LEFT and x <= NAVPAD_DOWN_LEFT + NAVPAD_BTN_WIDTH:
                        print('Press: d')
                        send_event('d', True)
                        continue

                # Left
                if y >= NAVPAD_LEFT_TOP and y <= NAVPAD_LEFT_TOP + NAVPAD_BTN_HEIGHT:
                    if x >= NAVPAD_LEFT_LEFT and x <= NAVPAD_LEFT_LEFT + NAVPAD_BTN_WIDTH:
                        print('Press: l')
                        send_event('l', True)
                        continue

                # Right
                if y >= NAVPAD_RIGHT_TOP and y <= NAVPAD_RIGHT_TOP + NAVPAD_BTN_HEIGHT:
                    if x >= NAVPAD_RIGHT_LEFT and x <= NAVPAD_RIGHT_LEFT + NAVPAD_BTN_WIDTH:
                        print('Press: r')
                        send_event('r', True)
                        continue

                # Back
                if y >= NAVPAD_BACK_TOP and y <= NAVPAD_BACK_TOP + NAVPAD_BACK_HEIGHT:
                    if x >= NAVPAD_BACK_LEFT and x <= NAVPAD_BACK_LEFT + NAVPAD_BACK_WIDTH:
                        print('Press: x')
                        send_event('x', True)
                        continue

                # Select
                if y >= NAVPAD_SELECT_TOP and y <= NAVPAD_SELECT_TOP + NAVPAD_SELECT_HEIGHT:
                    if x >= NAVPAD_SELECT_LEFT and x <= NAVPAD_SELECT_LEFT + NAVPAD_SELECT_WIDTH:
                        print('Press: y')
                        send_event('y', True)
                        continue

                # print('xy = %d, %d' % (event.button.x, event.button.y))
                col = ((x - KEYPAD_LEFT) // KEYPAD_KEY_WIDTH)
                row = ((y - KEYPAD_TOP) // KEYPAD_KEY_HEIGHT)
                print('rc= %d,%d' % (row, col))
                if not (0 <= row < 4):
                    continue
                if not (0 <= col < 3):
                    continue

                ch = '123456789*0#'[(row * 3) + col]
                print('Press: {}'.format(ch))
                send_event(ch, True)

            if event.type == sdl2.SDL_MOUSEBUTTONUP:
                for ch in list(pressed):
                    print('Release: {}'.format(ch))
                    send_event(ch, False)

        # If the camera is showing, show a frame in the window

        if cam.is_enabled():
            img = cam.capture(False)
            mirrored = cv2.flip(img, 1)
            cv2.imshow(cam_window_name, mirrored)
            # This is required in order for the image window to appear!
            cv2.waitKey(1)

        rs, ws, es = select(readables, [], [], .001)
        for r in rs:
            if r is oled_rx:
                # Read data in a loop. We read only 64k at a time.
                # TODO: use shared memory (mmap or sh_mem, faster, doesn't need to "sync").
                screen_buf = bytearray()
                while len(screen_buf) < DISP_BUF_SIZE:
                    buf = r.read(DISP_BUF_SIZE)
                    if not buf:
                        # print('not read')
                        continue
                    screen_buf += buf

                if len(screen_buf) == DISP_BUF_SIZE:
                    # print('render')
                    if IS_COLOR:
                        oled.render_color(window, screen_buf)
                    else:
                        oled.render_mono(window, screen_buf)

                    # spriterenderer.process(window, (oled.sprite, bg, led_green if genuine_state else led_red))
                    spriterenderer.process(window, (oled.sprite, bg))
                    window.refresh()
                    screen_buf = None

            elif r is cam_cmd_rx:
                buf = r.read(DISP_BUF_SIZE)
                if not buf:
                    print('DERP!')
                    break

                # print('Camera command')
                # print('buf={}'.format(buf))
                commands = buf.decode('utf-8')

                commands = commands.split('\n')

                for command in commands:
                    # # See what the command is
                    if command == "enable":
                        print('Enable camera!')
                        cv2.startWindowThread()
                        cv2.namedWindow(cam_window_name)
                        cv2.moveWindow(cam_window_name, 1273, 0)
                        cam.enable()
                        print('Enable camera DONE!')
                    elif command == "disable":
                        print('Disable camera!')
                        cam.disable()
                    elif command == "capture":
                        img_bytes = cam.capture(True)
                        # print('captured len(img_bytes) = {}'.format(len(img_bytes)))
                        cam_img_wx.write(img_bytes)

            elif r is led_rx:
                buf = r.read(DISP_BUF_SIZE)
                if not buf:
                    print('DERP!')
                    break

                print('led')

                for c in buf:
                    # print("LED change: 0x%02x" % c[0])

                    mask = (c >> 4) & 0xf
                    lset = c & 0xf
                    GEN_LED = 0x1

                    if mask & GEN_LED:
                        genuine_state = ((mask & lset) == GEN_LED)

                    spriterenderer.process(
                        window, (oled.sprite, bg, led_green if genuine_state else led_red))

                window.refresh()
            else:
                print('other')

                pass

        if xterm.poll() is not None:
            print("\r\n<xterm stopped: %s>\r\n" % xterm.poll())
            break

    xterm.kill()


if __name__ == '__main__':
    start()
