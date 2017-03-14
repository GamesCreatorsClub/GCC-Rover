import sys
import time
import math
import pygame
import pyros
import pyros.gcc
import pyros.pygamehelper
from PIL import Image


pygame.init()
bigFont = pygame.font.SysFont("arial", 32)
frameclock = pygame.time.Clock()
screen = pygame.display.set_mode((1024, 800))

cameraImage = Image.new("L", [80, 64])

rawImage = pygame.Surface((80, 64), 24)
receivedProcessedImage = pygame.Surface((80, 64), 24)
whiteBalanceImage = pygame.Surface((80, 64), 24)
processedImage = pygame.Surface((80, 64), 24)



rawImageBig = pygame.Surface((320, 256), 24)
receivedProcessedImageBig = pygame.Surface((320, 256), 24)
whiteBalanceImageBig = pygame.Surface((320, 256), 24)
processedImageBig = pygame.Surface((320, 256), 24)


continuousMode = False
lights = False
resubscribe = time.time()


def toPyImage(imageBytes):
    pilImage = Image.frombytes("L", (80, 64), imageBytes)
    return toPyImage2(pilImage)


def toPyImage2(pilImage):
    pilRGBImage = Image.new("RGB", pilImage.size)
    pilRGBImage.paste(pilImage)
    pyImageSmall = pygame.image.fromstring(pilRGBImage.tobytes("raw"), (80, 64), 'RGB')
    pyImageBig = pygame.transform.scale(pyImageSmall, (320, 256))
    return (pyImageSmall, pyImageBig, pilImage)



def handleWhiteBalance(topic, message, groups):
    global whiteBalanceImage, whiteBalanceImageBig

    images = toPyImage(message)
    whiteBalanceImage = images[0]
    whiteBalanceImageBig = images[1]
    print("  Converted images for white balance.")


def handleCameraRaw(topic, message, groups):
    global rawImage, rawImageBig

    images = toPyImage(message)
    rawImage = images[0]
    rawImageBig = images[1]
    print("  Converted images for raw.")


def handleCameraProcessed(topic, message, groups):
    global receivedProcessedImage, receivedProcessedImageBig, processedImage, processedImageBig, cameraImage

    images = toPyImage(message)
    receivedProcessedImage = images[0]
    receivedProcessedImageBig = images[1]

    images = toPyImage(message)
    processedImage = images[0]
    processedImageBig = images[1]
    cameraImage = images[2]
    print("  Converted images for processed.")

    processImage()


def processImage():
    global processedImageBig, processedImage

    r = 30

    ha = math.atan2(0.5, r + 0.5) * 180 / math.pi
    ha *= 2

    print("Angle is " + str(ha))
    a = -90

    p1 = 255
    p2 = 0

    c = 0
    while a <= 90:
        print("angles to scan: " + str(a))
        a += ha
        ra = a * math.pi / 180 + math.pi

        x = int(r * math.cos(ra) + 40)
        y = int(r * math.sin(ra) + 32)

        p = cameraImage.getpixel((x, y))
        if p > 127:
            processedImage.set_at((x, y), (0, 255, 0))
        else:
            processedImage.set_at((x, y), (255, 0, 0))

        c += 1

    processedImageBig = pygame.transform.scale(processedImage, (320, 256))

    # images = toPyImage2(cameraImage)
    # processedImage = images[0]
    # processedImageBig = images[1]
    print("Scanned " + str(c) + " points")

def goOneStep():
    pass


def onKeyDown(key):
    global continuousMode, lights

    if key == pygame.K_ESCAPE:
        sys.exit()
    elif key == pygame.K_w:
        print("  fetching white balance picture...")
        pyros.publish("camera/whitebalance/fetch", "")
    elif key == pygame.K_r:
        print("  fetching white balance picture...")
        pyros.publish("camera/raw/fetch", "")
    elif key == pygame.K_p:
        print("  fetching white balance picture...")
        pyros.publish("camera/processed/fetch", "")
    elif key == pygame.K_s:
        print("  storing whitebalance image...")
        pyros.publish("camera/whitebalance/store", "")
        pyros.publish("camera/whitebalance/fetch", "")
    elif key == pygame.K_l:
        if lights:
            print("  switching off lights")
            pyros.publish("lights/camera", "on")
            lights = False
        else:
            print("  switching on lights")
            pyros.publish("lights/camera", "off")
            lights = True
    elif key == pygame.K_c:
        continuousMode = not continuousMode
    elif key == pygame.K_g:
        goOneStep()
    elif key == pygame.K_m:
        processImage()
    else:
        pyros.gcc.handleConnectKeys(key)


def onKeyUp(key):
    return


pyros.subscribeBinary("camera/whitebalance", handleWhiteBalance)
pyros.subscribeBinary("camera/raw", handleCameraRaw)
pyros.subscribeBinary("camera/processed", handleCameraProcessed)
pyros.init("camera-display-#", unique=True, host=pyros.gcc.getHost(), port=pyros.gcc.getPort(), waitToConnect=False)


while True:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            pygame.quit()
            sys.exit()

    pyros.pygamehelper.processKeys(onKeyDown, onKeyUp)

    pyros.loop(0.03)

    screen.fill((0, 0, 0))

    if pyros.isConnected():
        text = bigFont.render("Connected to rover: " + pyros.gcc.getSelectedRoverDetailsText(), 1, (128, 255, 128))
    else:
        text = bigFont.render("Connecting to rover: " + pyros.gcc.getSelectedRoverDetailsText(), 1, (255, 128, 128))

    screen.blit(text, (0, 0))

    text = bigFont.render("Continuous mode: " + str(continuousMode), 1, (255, 128, 128))
    screen.blit(text, (300, 50))

    screen.blit(rawImage, (10, 50))
    screen.blit(whiteBalanceImage, (110, 50))
    screen.blit(receivedProcessedImage, (210, 50))

    screen.blit(rawImageBig, (10, 150))
    screen.blit(whiteBalanceImageBig, (362, 150))
    screen.blit(receivedProcessedImageBig, (724, 150))

    screen.blit(processedImageBig, (724, 420))

    pygame.display.flip()
    frameclock.tick(30)

    if continuousMode and time.time() - resubscribe > 2:
        resubscribe = time.time()
        if pyros.isConnected():
            pyros.publish("camera/continuous", "on")
