import pygame, sys, time
import paho.mqtt.client as mqtt

#wheel/fr/deg      -90
#wheel/fr/drive    300

wheelsMap = {"fl":{"deg": 0,"speed": 0},
             "fr":{"deg": 0,"speed": 0},
             "bl":{"deg": 0,"speed": 0},
             "br":{"deg": 0,"speed": 0}}
def onMessage(client, data, msg):
    global wheelsMap

    payload = str(msg.payload, 'utf-8')
    topic = msg.topic

    #print(topic,payload)

    if topic.startswith("wheel"): #and topic.endswith("/cal/values"):
        topicsplit = topic.split("/")
        wheelName = topicsplit[1]
        if topicsplit[2] == "deg":
            wheelsMap[wheelName]["deg"] = payload
            #print("Got deg for wheel",wheelName)
        if topicsplit[2] == "speed":
            wheelsMap[wheelName]["speed"] = payload
            #print("Got speed for wheel",wheelName)
    else:
        print("Wrong topic '" + msg.topic + "'")


def processLine(wheelName, line):
    global wheelsMap
    splitline = line.split(",")
    if not len(splitline) == 3:
        print("Received an invalid value for " + wheelName)
    else:
        wheelsMap[wheelName][splitline[0]][splitline[1]] = splitline[2]

def onConnect(client, data, rc):
    #client.subscribe("servo/#")
    #print("servo/# has been subscribed to")
    #client.subscribe("drive/#")
    #print("drive/# has been subscribed to\n")
    
    client.subscribe("wheel/+/deg")
    client.subscribe("wheel/+/speed")
    print("[ wheel/ ] has been subscribed to")

def sendMessage(topic, value):
    client.publish(topic,value)

#def onMessage(client, data, msg):
#    payload = str(msg.payload, 'utf-8')
#    print(msg.topic + payload)

def rotate(image, angle):
    """Rotate an image while keeping its center and size.
    Stolen from http://www.pygame.org/wiki/RotateCenter"""
    loc = image.get_rect().center  #rot_image is not defined 
    rot_sprite = pygame.transform.rotate(image, angle)
    rot_sprite.get_rect().center = loc
    return rot_sprite


frameclock = pygame.time.Clock()
def init():
    global screen, font10, font20, font30, font40, font50
    global boxes, client, gotoAng, gotoRPM,last_keys
    global wheelfr,wheelfl,wheelbr,wheelbl
    global frameclock, selected, address
    
    pygame.init()
    pygame.font.init()

    pygame.display.set_caption("GCC Robot Controller")

    client = mqtt.Client("MyController518")

    address = ["172.24.1.184","172.24.1.185","172.24.1.186"]
    selected = 2 #0 is first
    
    #client.connect(address[selected], 1883, 60) #<--- Useful if not conncected
    print("Connected to",address[selected])
    
    client.on_connect = onConnect
    client.on_message = onMessage
    client.subscribe("robot/servo/#")

    last_keys = pygame.key.get_pressed()
    
    #find range # or 1, time.sleep
    #increments of 2
    #until value set
    #goto value

    screen = pygame.display.set_mode((1024,768))

    frameclock = pygame.time.Clock()

    pygame.display.set_caption("Robot Gui")
    
    font10 = pygame.font.SysFont("Arial",10)
    font20 = pygame.font.SysFont("Arial",20)
    font30 = pygame.font.SysFont("Arial",30)
    font40 = pygame.font.SysFont("Arial",40)
    font50 = pygame.font.SysFont("Arial",50)

    wheelfr = pygame.image.load("Wheel.png")
    wheelfl = pygame.image.load("Wheel.png")
    wheelbr = pygame.image.load("Wheel.png")
    wheelbl = pygame.image.load("Wheel.png")

def Text(text,size,position,colour):
    text = str(text)
    if size==10:
        font = font10
    elif size==20:
        font = font20
    elif size==30:
        font = font30
    elif size==40:
        font = font40
    elif size==50:
        font = font50
    font_colour = pygame.Color(colour)
    rendered_text = font.render(text, 1, font_colour).convert_alpha()
    
    screen.blit(rendered_text, position)

def DrawScreen():
    global emStop
    
    #Box top left
    pygame.draw.rect(screen, (150,150,150),(0,0,1024/2,768/2))
    
    #Box bottom right
    pygame.draw.rect(screen, (150,150,150),(1024/2,768/2,1024/2,768/2))

    #Robot Middle
    pygame.draw.rect(screen, (150,150,255),(1024*0.75-42,768*0.75-60,100,150))


    ###=======###Les wheels###======###
    pos1 = (1024*0.75-50,768*0.75-75)
    pos2 = (1024*0.75+50,768*0.75-75)
    pos3 = (1024*0.75-50,768*0.75+75)
    pos4 = (1024*0.75+50,768*0.75+75)
    #fr
    wheel1 = rotate(wheelfr, 90+float(wheelsMap["fr"]["deg"]))
    screen.blit(wheel1,pos1)
    
    #fl
    wheel2 = rotate(wheelfl, 90+float(wheelsMap["fl"]["deg"]))
    screen.blit(wheel2,pos2)
    
    #br
    wheel3 = rotate(wheelfr, 90+float(wheelsMap["br"]["deg"]))
    screen.blit(wheel3,pos3)
    
    #bl
    wheel4 = rotate(wheelfl, 90+float(wheelsMap["bl"]["deg"]))
    screen.blit(wheel4,pos4)
    
    
    Text("Radar",30,(0,0),"#ffffff")
    Text("Radar",30,(1024/2,0),"#ffffff")

    degColour = "#58ccde"
    Text("Deg",30,(512,768/2),degColour)
    Text("FL:"+str(wheelsMap["fl"]["deg"]),20,(512,768/2+30),degColour)
    Text("FR:"+str(wheelsMap["fr"]["deg"]),20,(512+80,768/2+30),degColour)
    
    Text("BL:"+str(wheelsMap["bl"]["deg"]),20,(512,768/2+50),degColour)
    Text("BR:"+str(wheelsMap["br"]["deg"]),20,(512+80,768/2+50),degColour)

    speed1 = round(float(wheelsMap["fl"]["speed"]),1)
    speed2 = round(float(wheelsMap["fr"]["speed"]),1)
    speed3 = round(float(wheelsMap["bl"]["speed"]),1)
    speed4 = round(float(wheelsMap["br"]["speed"]),1)

    speedColour = "#7ff188"
    Text("Speed",30,(512,768/2+100),speedColour)
    Text("FL:"+str(speed1),20,(512,768/2+130),speedColour)
    Text("FR:"+str(speed2),20,(512+80,768/2+130),speedColour)
    
    Text("BL:"+str(speed3),20,(512,768/2+150),speedColour)
    Text("BR:"+str(speed4),20,(512+80,768/2+150),speedColour)

    Text("Robot "+str(selected+1),50,(1024/4*2.7,700),"White")
    
    pygame.display.flip()

def mainloop():
    global current_keys, last_keys, mousePos, gotoAng, gotoRPM, emStop, frameclock
    global screen, selected

    frameclock.tick(30)
    
    client.loop(1/60)

    current_keys = pygame.key.get_pressed()

    mousePos = pygame.mouse.get_pos()
    
    screen.fill((200,200,200))
    
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            pygame.quit()
            sys.exit()
    """ #Not needed due to pyros library
    if current_keys[pygame.K_1]:
        selected = 0
        
    elif current_keys[pygame.K_2]:
        selected = 1
        
    elif current_keys[pygame.K_3]:
        selected = 2
        
    """
    DrawScreen()

    last_keys = current_keys
init()
while True:
    mainloop()

pygame.quit()
