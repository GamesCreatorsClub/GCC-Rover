
#
# Copyright 2016-2017 Games Creators Club
#
# MIT License
#

import pygame
import sys
import time

from PIL import Image, ImageEnhance
import numpy
from scipy import misc
from scipy import ndimage

images = []

pygame.init()
frameclock = pygame.time.Clock()
screen = pygame.display.set_mode((1024, 768))

originalPilImage = Image.open("p9.jpg")
whiteBalancePilImage = Image.open("p10.jpg")
t = time.time()


def toPyImage(pilImage):
    pilRGBImage = Image.new("RGB", pilImage.size)
    pilRGBImage.paste(pilImage)
    pyImage = pygame.image.fromstring(pilRGBImage.tobytes("raw"), (80, 64), 'RGB')
    pyImage = pygame.transform.scale(pyImage, (320, 256))
    return pyImage


def toPilImage(buf):
    pilImage = Image.fromarray(buf)
    return pilImage


def calc(ps):
    p = ps[0]
    sum = 0
    for i in range(1, 5):
        pp = ps[i]
        if abs(p - pp) > 5:
            sum = sum + p
        else:
            sum = sum + pp

    return int(sum / 4)


def processAvg(img):
    for y in range(0, 64):
        for x in range(0, 80):
            p = convertedPilImage.getpixel((x, y))
            pu = p
            if y > 0:
                pu = convertedPilImage.getpixel((x, y - 1))

            pd = p
            if y < 63:
                pd = convertedPilImage.getpixel((x, y + 1))

            pl = p
            if x > 0:
                pu = convertedPilImage.getpixel((x - 1, y))

            pr = p
            if x < 79:
                pr = convertedPilImage.getpixel((x + 1, y))

            ps = [p, pu, pd, pl, pr]

            p = calc(ps)
            img.putpixel((x, y), p)
    return img


def circleMask(img, radius):
    for y in range(0, 64):
        for x in range(0, 80):
            d = (x - 40) * (x - 40) + (y - 32) * (y - 32)
            if d > radius * radius:
                img.putpixel((x, y), 255)


def edgeDetection(img):
    nb = numpy.asarray(img).copy()
    sx = ndimage.sobel(nb, axis=0, mode='constant')
    sy = ndimage.sobel(nb, axis=1, mode='constant')
    sob = numpy.hypot(sx, sy)
    return toPilImage(sob)


def minLevel(histogram, level):
    for i in range(0, len(histogram)):
        if histogram[i] > level:
            return i
    return 0

def maxLevel(histogram, level):
    for i in range(len(histogram) - 1, 0, -1):
        if histogram[i] > level:
            return i
    return len(histogram) - 1

def limit(pixel, min, max):
    if pixel > max:
        pixel = max
    if pixel < min:
        pixel < min
    return pixel

def applyWhiteBalance(img, wb):
    histogram = img.histogram()

    min = minLevel(histogram, 20)
    max = maxLevel(histogram, 20)

    for y in range(0, 64):
        for x in range(0, 80):
            wbp = wb.getpixel((x, y))
            wbp = limit(wbp, min, max)

            p = img.getpixel((x, y))
            offset = ((max - wbp) - min)

            p = p + offset
            if p > 255:
                p = 255
            img.putpixel((x, y), p)

    return img

images.append(toPyImage(originalPilImage))

grayPilImage = originalPilImage.convert('L')
images.append(toPyImage(grayPilImage))
images.append(toPyImage(whiteBalancePilImage))

convertedPilImage = grayPilImage.copy()
whiteBalancePilImage = whiteBalancePilImage.convert('L')

convertedPilImage = applyWhiteBalance(convertedPilImage, whiteBalancePilImage)
images.append(toPyImage(convertedPilImage))

contrast = ImageEnhance.Contrast(convertedPilImage)

convertedPilImage = contrast.enhance(10)
images.append(toPyImage(convertedPilImage))

circleMask(convertedPilImage, 37)
images.append(toPyImage(convertedPilImage))

# convertedPilImage = edgeDetection(convertedPilImage)

# for i in range(0, 20):
#     convertedPilImage = processAvg(convertedPilImage)



# convertedNumpyBuf = numpy.asarray(grayPilImage).copy()
#
# # Pixel range is 0...255, 256/2 = 128
# convertedNumpyBuf[convertedNumpyBuf < 128] = 0    # Black
# convertedNumpyBuf[convertedNumpyBuf >= 128] = 255 # White

#bw.save("p5-processed.jpg")




for i in range(0, len(images)):
    images[i] = pygame.transform.scale(images[i], (320, 256))
print("Done! (" + str(time.time() - t) + "s)")
while True:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            pygame.quit()
            sys.exit()

    keys = pygame.key.get_pressed()
    if keys[pygame.K_ESCAPE]:
        sys.exit()
    screen.fill((0, 0, 0))

    for i in range(0, 3):
        screen.blit(images[i], (i * 352 , 50))

    for i in range(3, 6):
        if i < len(images):
            screen.blit(images[i], ((i - 3) * 352, 356))

    pygame.display.flip()
    frameclock.tick(30)