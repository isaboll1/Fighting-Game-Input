#Fighting Game Input System Test by Isa Bolling
import os
os.environ['PYSDL2_DLL_PATH'] = os.path.dirname(os.path.abspath(__file__))
from sdl2 import *
from sdl2.sdlttf import *
import ctypes

#CLASSES_______________________________________
class DynamicTextObject:
    def __init__(self, renderer, font, size, color=(0, 0, 0)):
        self.r = renderer
        self.font = TTF_OpenFont(font.encode('utf-8'), size)
        self.characters = dict()
        self.size = size

        for i in range(32, 126):  # Now this converts the ascii values into the characters they represent
            char = chr(i)
            if char not in self.characters:
                surface = TTF_RenderText_Solid(self.font, char.encode('utf-8'),
                                               SDL_Color(color[0], color[1], color[2], 255))
                self.characters[char] = SDL_CreateTextureFromSurface(self.r, surface)
                SDL_FreeSurface(surface)

    def RenderText(self, text, location, offset=0):
        x = 0
        for char in text:
            d_rect = SDL_Rect(location[0] + x, location[1], location[2], location[3])
            SDL_RenderCopy(self.r, self.characters[char], None, d_rect)
            x += location[2] + offset

    def __del__(self):
        for char in list(self.characters):
            SDL_DestroyTexture(self.characters[char])
        TTF_CloseFont(self.font)


class Clock:
    def __init__(self):
        self.__last_time = 0
        self.__current_time = SDL_GetPerformanceCounter()
        self.dt = 0
        self.dt_s = 0

    def Tick(self):
        self.__last_time = self.__current_time
        self.__current_time = SDL_GetPerformanceCounter()
        self.dt = (self.__current_time - self.__last_time) * 1000 / SDL_GetPerformanceFrequency()
        self.dt_s = (self.dt * .001)


class InputNode:
    def __init__(self, button, move_name=''):
        self.input = button
        self.move_name = move_name
        self.__children = {}

    def AddChild(self, button, move_name=''):
        self.__children[button] = InputNode(button, move_name)

    def GetChild(self, button):
        return self.__children.get(button, None)


class InputSystem:       # I will draw out how this works on paper.
    def __init__(self):
        self.__root = InputNode('')

    def AddMove(self, queue, move):
        node = self.__root
        for button in queue:
            if node.GetChild(button) is None:
                node.AddChild(button)
            node = node.GetChild(button)
        node.move_name = move

    def GetMove(self, queue):
        node = self.__root
        for button in queue:
            if node.GetChild(button) is not None:
                node = node.GetChild(button)
        return node.move_name if node.move_name else None


class Controllers:
    def __init__(self):
        self._button_map = {
            'A'   : SDL_CONTROLLER_BUTTON_A,
            'B'   : SDL_CONTROLLER_BUTTON_B,
            'X'   : SDL_CONTROLLER_BUTTON_X,
            'Y'   : SDL_CONTROLLER_BUTTON_Y,
            'UP'  : SDL_CONTROLLER_BUTTON_DPAD_UP,
            'DOWN': SDL_CONTROLLER_BUTTON_DPAD_DOWN,
            'LEFT': SDL_CONTROLLER_BUTTON_DPAD_LEFT,
            'RIGHT':SDL_CONTROLLER_BUTTON_DPAD_RIGHT,
            'LB'  : SDL_CONTROLLER_BUTTON_LEFTSHOULDER,
            'RB'  : SDL_CONTROLLER_BUTTON_RIGHTSHOULDER
        }
        self._axis_map = {
            'LT'   : SDL_CONTROLLER_AXIS_TRIGGERLEFT,
            'RT'   : SDL_CONTROLLER_AXIS_TRIGGERRIGHT
        }
        self.list = []
        self.amount = 0

    def Add(self, index):
        self.list.append(SDL_GameControllerOpen(index))
        self.amount += 1

    def Remove(self, id):
        index = 0
        for i in range(len(self.list)):
            joystick = SDL_GameControllerGetJoystick(self.list[i])
            if joystick == id:
                index = i
        controller = self.list.pop(index)
        self.amount -= 1
        SDL_GameControllerClose(controller)

    def GetButton(self, index, button):
        if index <= (self.amount - 1):
            return SDL_GameControllerGetButton(self.list[index], self._button_map[button])

    def GetTrigger(self, index, trigger):
        if index <= (self.amount - 1):
            # Trigger values range from 0 to 32767,
            # so we divide by that to get a range of numbers from 0 to 1,
            # that is normalization.
            if trigger == 'LT' or trigger == 'RT':
                return (SDL_GameControllerGetAxis(self.list[index], self._axis_map[trigger]) / 32767)
            return 0

def main():

    SDL_Init(SDL_INIT_VIDEO | SDL_INIT_GAMECONTROLLER)
    TTF_Init()

    window = SDL_CreateWindow(b'FGI System Test', SDL_WINDOWPOS_UNDEFINED, SDL_WINDOWPOS_UNDEFINED,
                              640, 480, SDL_WINDOW_SHOWN)
    renderer = SDL_CreateRenderer(window, -1, 0)
    event = SDL_Event()

    # Variables
    running = True
    input_queue = []
    move = ''
    input_process = False
    connected = False
    input_timer = 0
    queue_timer = 0
    message_timer = 0

    # Objects
    text = DynamicTextObject(renderer, 'font/joystix.ttf', 13)
    input_system = InputSystem()
    controllers = Controllers()
    clock = Clock()

    # Input System
    input_system.AddMove(['↓','↘','→','P'], 'Fireball')
    input_system.AddMove(['→','↓','↘','P'], 'Shoryu')
    input_system.AddMove(['↓','↙','←','K'], 'Tatsu')
    input_system.AddMove(['→','↘', '↓', '↙','←', 'P', 'K'], 'The Grab No One Likes')
    input_system.AddMove(['↓','↘','→','↓','↘','→', 'P', 'P'], 'Super Fireball')
    input_system.AddMove(['P', 'K'], 'Grab')
    input_system.AddMove(['K', 'P'], 'Grab')

    while (running):
        clock.Tick()
        # Event Processing
        while (SDL_PollEvent(ctypes.byref(event))):
            if event.type == SDL_CONTROLLERBUTTONDOWN:
                input_process = True

            if event.type == SDL_CONTROLLERDEVICEADDED:
                controllers.Add(event.cdevice.which)
                connected = True

            if event.type == SDL_CONTROLLERDEVICEREMOVED:
                controllers.Remove(event.cdevice.which)

            if event.type == SDL_QUIT:
                running = False
                break

        # Game Logic and Input Processing
        if connected:
            message_timer += clock.dt_s

        if message_timer >= 1.3:
            message_timer = 0
            connected = False

        if input_process:
            input_timer += clock.dt_s
            queue_timer += clock.dt_s

            if input_timer >= .03:
                input_timer = 0
                if controllers.GetButton(0, "UP") and controllers.GetButton(0, "LEFT"):
                    input_queue.append('↖')
                elif controllers.GetButton(0, 'UP') and controllers.GetButton(0, 'RIGHT'):
                    input_queue.append('↗')
                elif controllers.GetButton(0, 'DOWN') and controllers.GetButton(0, 'LEFT'):
                    input_queue.append('↙')
                elif controllers.GetButton(0, 'DOWN') and controllers.GetButton(0, 'RIGHT'):
                    input_queue.append('↘')

                elif controllers.GetButton(0, 'UP'):
                    input_queue.append('↑')
                elif controllers.GetButton(0, 'DOWN'):
                    input_queue.append('↓')
                elif controllers.GetButton(0, 'LEFT'):
                    input_queue.append('←')
                elif controllers.GetButton(0, 'RIGHT'):
                    input_queue.append('→')

                if controllers.GetButton(0, 'X'):
                    input_queue.append('P')
                if controllers.GetButton(0, 'Y'):
                    input_queue.append('P')
                if controllers.GetButton(0, 'RB'):
                    input_queue.append('P')
                if controllers.GetButton(0, 'A'):
                    input_queue.append('K')
                if controllers.GetButton(0, 'B'):
                    input_queue.append('K')
                if controllers.GetTrigger(0, 'RT') >= 0.3:
                    input_queue.append('K')

            if queue_timer >= .4:
                queue_timer = 0
                input_process = False
                attack = input_system.GetMove(input_queue)
                if attack is not None:
                    move = attack
                input_queue.clear()

        # Game Rendering
        SDL_SetRenderDrawColor(renderer, 242, 242, 242, 255)
        SDL_RenderClear(renderer)

        if connected:
            text.RenderText('Controller Connected!', [10, 10, 15, 15])


        text.RenderText('Move: ' + move, [70, 100, 20, 20], 1)

        SDL_RenderPresent(renderer)

    SDL_DestroyRenderer(renderer)
    SDL_DestroyWindow(window)
    SDL_Quit()
    return 0

main()

