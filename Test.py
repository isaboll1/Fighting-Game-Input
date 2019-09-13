#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Fighting Game Input System Test by Isa Bolling
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


class CommandSystem:       # I will draw out how this works on paper.
    def __init__(self):
        self.__root = InputNode('')

    def AddMove(self, command_list, move):
        node = self.__root
        for button in command_list:
            if node.GetChild(button) is None:
                node.AddChild(button)
            node = node.GetChild(button)
        node.move_name = move

    def GetMove(self, input_queue):
        node = self.__root
        for i in range(len(input_queue.queue)):
            if node.move_name:
                return node.move_name
            if node.GetChild(input_queue.queue[i].button) is not None:
                node = node.GetChild(input_queue.queue[i].button)
        return node.move_name if node.move_name else None


class QueueNode:
    def __init__(self, button):
        self.button = button
        self.time = 0


class InputQueue:
    def __init__(self):
        self.queue = []

    def AddInput(self, input):
        self.queue.append(QueueNode(input))

    def Dequeue(self):
        return self.queue.pop()

    def Update(self, dt_s, buffer_time):
        for input in self.queue:
            input.time += dt_s

        last_input = None
        for input in self.queue:
            if last_input:
                if last_input.time >= buffer_time:
                    expired = self.Dequeue()
                    del expired
            last_input = input

        if last_input:
            if last_input.time >= buffer_time:
                expired = self.Dequeue()
                del expired

    def Clear(self):
        del self.queue[:]
        self.queue[:] = []

    def Print(self):
        queue = []
        for input in self.queue:
            queue.append(input.button)
        print(queue)


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
        if 0 <= index <= (self.amount - 1):
            return SDL_GameControllerGetButton(self.list[index], self._button_map[button])

    def GetTrigger(self, index, trigger):
        if 0 <= index <= (self.amount - 1):
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
    renderer = SDL_CreateRenderer(window, -1, SDL_RENDERER_PRESENTVSYNC)
    event = SDL_Event()

    # Variables
    running = True
    move = ''
    connected = False
    input_timer = 0
    message_timer = 0

    # Objects
    input_queue = InputQueue()
    text = DynamicTextObject(renderer, 'font/joystix.ttf', 13)
    input_system = CommandSystem()
    controllers = Controllers()
    clock = Clock()

    # Input System
    input_system.AddMove(['↓','↘','→','P'], 'Fireball')
    input_system.AddMove(['→','↓','↘','P'], 'Shoryu')
    input_system.AddMove(['↓','↙','←','K'], 'Tatsu')
    input_system.AddMove(['→','↘', '↓', '↙','←', 'G'], 'The Grab No One Likes') # have to fix in the next iteration
    input_system.AddMove(['←','←','←','←', '→', 'P'], 'Napalm Shot')
    input_system.AddMove(['↓','↘','→','↓','↘','→', 'P', 'P'], 'Super Fireball')
    input_system.AddMove(['P'], "Punch")
    input_system.AddMove(['→', 'P'],'Forward Punch')
    input_system.AddMove(['K'], 'Kick')
    input_system.AddMove(['→', 'K'], 'Forward Kick')
    input_system.AddMove(['G'],'Grab')
    input_system.AddMove(['↓','↘','→','G'], 'Super Grab')

    while (running):
        clock.Tick()
        input_queue.Update(clock.dt_s, .6)
        keyboard = SDL_GetKeyboardState(None)
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


        input_timer += clock.dt_s

        if input_timer >= .08:
            input_timer = 0
            if ((controllers.GetButton(0, "UP") and controllers.GetButton(0, "LEFT"))
            or (keyboard[SDL_SCANCODE_UP] and keyboard[SDL_SCANCODE_LEFT])):
                input_queue.AddInput('↖')
            elif ((controllers.GetButton(0, 'UP') and controllers.GetButton(0, 'RIGHT'))
            or (keyboard[SDL_SCANCODE_UP] and keyboard[SDL_SCANCODE_RIGHT])):
                input_queue.AddInput('↗')
            elif ((controllers.GetButton(0, 'DOWN') and controllers.GetButton(0, 'LEFT'))
            or (keyboard[SDL_SCANCODE_DOWN] and keyboard[SDL_SCANCODE_LEFT])):
                input_queue.AddInput('↙')
            elif ((controllers.GetButton(0, 'DOWN') and controllers.GetButton(0, 'RIGHT'))
            or (keyboard[SDL_SCANCODE_DOWN] and keyboard[SDL_SCANCODE_RIGHT])):
                input_queue.AddInput('↘')

            elif controllers.GetButton(0, 'UP') or keyboard[SDL_SCANCODE_UP]:
                input_queue.AddInput('↑')
            elif controllers.GetButton(0, 'DOWN') or keyboard[SDL_SCANCODE_DOWN]:
                input_queue.AddInput('↓')
            elif controllers.GetButton(0, 'LEFT') or keyboard[SDL_SCANCODE_LEFT]:
                input_queue.AddInput('←')
            elif controllers.GetButton(0, 'RIGHT') or keyboard[SDL_SCANCODE_RIGHT]:
                input_queue.AddInput('→')

            if ((controllers.GetButton(0, 'X') and controllers.GetButton(0, 'A'))
            or (keyboard[SDL_SCANCODE_Z] and keyboard[SDL_SCANCODE_A])):
                input_queue.AddInput('G')
            if controllers.GetButton(0, 'X') or keyboard[SDL_SCANCODE_Z]:
                input_queue.AddInput('P')
            if controllers.GetButton(0, 'Y') or keyboard[SDL_SCANCODE_X]:
                input_queue.AddInput('P')
            if controllers.GetButton(0, 'RB') or keyboard[SDL_SCANCODE_C]:
                input_queue.AddInput('P')
            if controllers.GetButton(0, 'A') or keyboard[SDL_SCANCODE_A]:
                input_queue.AddInput('K')
            if controllers.GetButton(0, 'B') or keyboard[SDL_SCANCODE_S]:
                input_queue.AddInput('K')
            if controllers.GetTrigger(0, 'RT') >= 0.3 or keyboard[SDL_SCANCODE_D]:
                input_queue.AddInput('K')

        input_queue.Print()
        attack = input_system.GetMove(input_queue)
        if attack is not None:
            move = attack
            input_queue.Clear()

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

