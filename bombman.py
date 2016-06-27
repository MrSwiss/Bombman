#!/usr/bin/env python
# coding=utf-8

# Bombman - free and open-source Bomberman clone
#
# Copyright (C) 2016 Miloslav Číž
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

# Map string format (may contain spaces and newlines, which will be ignored):
#
# <environment>;<player items>;<map items>;<tiles>
#    
# <environment>   - Name of the environment of the map (affects only visual appearance).
# <player items>  - Items that players have from the start of the game (can be an empty string),
#                   each item is represented by one letter (the same letter can appear multiple times):
#                     f - flame
#                     F - max flame
#                     b - bomb
#                     k - kicking shoe
#                     s - spring
#                     d - disease
#                     TODO
# <map items>     - Set of items that will appear on the map (in places of destroyed blocks). The items
#                   are specified with the same letter as in <player items>. If an item appears multiple
#                   times, its probability of being generated will be higher (every time a block is
#                   destroyed, an item is chosen from <map items> set randomly). There is also an
#                   additional symbol:
#                     ! - no item
# <tiles>         - left to right, top to bottom sequenced array of map tiles:
#                     . - floor
#                     x - block (destroyable)
#                     # - wall (undestroyable)
#                     <0-9> - starting position of the player specified by the number
#                     TODO

import sys
import pygame
import os
import math

MAP1 = ("env1;"
        "ff;"
        "ffffbbbbsdk!!!!!!!!;"
        "x . x x x x x x . x x x x . x"
        ". 0 . x x x x . 9 . x x . 3 ."
        "x . x x . x x x . x x . x . x"
        "x x x . 4 . x x x x . 5 . x x"
        "x x x x . x x x x x x . x x x"
        "# x x x x x # # # # x x x x #"
        "x x x x . x x x x x x . x x x"
        "x x x . 7 . x x x x . 6 . x x"
        "x . x x . x x . x x x . x . x"
        ". 2 . x x x . 8 . x x x . 1 ."
        "x . x x x x x . x x x x x . x")

# colors used for players and teams
COLOR_WHITE = 0
COLOR_BLACK = 1
COLOR_RED = 2
COLOR_BLUE = 3
COLOR_GREEN = 4
COLOR_CYAN = 5
COLOR_YELLOW = 6
COLOR_ORANGE = 7
COLOR_BROWN = 8
COLOR_PURPLE = 9

COLOR_RGB_VALUES = [
  (0.6,0.6,0.6),                  # white
  (0.1,0.1,0.1),                  # black
  (0.9,0.2,0.2),                  # red
  (0.4,0.5,1.0),                  # blue
  (0.6,0.9,0.4),                  # green
  (0.3,0.9,1.0),                  # cyan
  (0.4,1.0,0.9),                  # yellow
  (1.0,0.9,0.5),                  # orange
  (0.7,0.7,0.6),                  # brown
  (0.7,0.4,0.9)                   # purple
  ]

RESOURCE_PATH = "resources"

## Something that has a float position on the map.

class Positionable(object):
  def __init__(self):
    self.position = (0.0,0.0)

  def set_position(self,position):
    self.position = position

  def get_position(self):
    return self.position
  
  def move_to_tile_center(self):
    self.position = (math.floor(self.position[0]) + 0.5,math.floor(self.position[1]) + 0.5)

class Player(Positionable):
  # possible player states
  STATE_IDLE_UP = 0
  STATE_IDLE_RIGHT = 1
  STATE_IDLE_DOWN = 2
  STATE_IDLE_LEFT = 3
  STATE_WALKING_UP = 4
  STATE_WALKING_RIGHT = 5
  STATE_WALKING_DOWN = 6
  STATE_WALKING_LEFT = 7
  STATE_DEAD = 8

  INITIAL_SPEED = 3

  def __init__(self):
    super(Player,self).__init__()
    self.number = 0                       ##< players number and also color index
    self.team_color = COLOR_WHITE
    self.state = Player.STATE_IDLE_DOWN
    self.state_time = 0                   ##< how much time (in ms) has been spent in current time
    self.speed = Player.INITIAL_SPEED     ##< speed in tiles per second
    self.bombs_left = 5                   ##< how many more bombs the player can put at the time

  def set_number(self,number):
    self.number = number

  ## Must be called when this player's bomb explodes so that their bomb limit is increased again.

  def bomb_exploded(self):
    self.bombs_left += 1

  def get_number(self):
    return self.number

  def get_state(self):
    return self.state

  def get_state_time(self):
    return self.state_time

  ## Sets the state and other attributes like position etc. of this player accoording to a list of input action (returned by PlayerKeyMaps.get_current_actions()).

  def react_to_inputs(self,input_actions,dt,game_map):
    distance_to_travel = dt / 1000.0 * self.speed

    self.position = list(self.position)    # in case position was tuple

    old_state = self.state
 
    if self.state == Player.STATE_WALKING_UP or self.state == Player.STATE_IDLE_UP:
      self.state = Player.STATE_IDLE_UP
    elif self.state == Player.STATE_WALKING_RIGHT or self.state == Player.STATE_IDLE_RIGHT:
      self.state = Player.STATE_IDLE_RIGHT
    elif self.state == Player.STATE_WALKING_DOWN or self.state == Player.STATE_IDLE_DOWN:
      self.state = Player.STATE_IDLE_DOWN
    else:
      self.state = Player.STATE_IDLE_LEFT

    moved = False  # to allow movement along only one axis at a time

    for item in input_actions:
      if item[0] != self.number:
        continue                           # not an action for this player
      
      input_action = item[1]

      if not moved and input_action == PlayerKeyMaps.ACTION_UP:
        self.position[1] -= distance_to_travel
        self.state = Player.STATE_WALKING_UP
        moved = True
      elif not moved and input_action == PlayerKeyMaps.ACTION_DOWN:
        self.position[1] += distance_to_travel
        self.state = Player.STATE_WALKING_DOWN
        moved = True
      elif not moved and input_action == PlayerKeyMaps.ACTION_RIGHT:
        self.position[0] += distance_to_travel
        self.state = Player.STATE_WALKING_RIGHT
        moved = True
      elif not moved and input_action == PlayerKeyMaps.ACTION_LEFT:
        self.position[0] -= distance_to_travel
        self.state = Player.STATE_WALKING_LEFT
        moved = True
        
      if input_action == PlayerKeyMaps.ACTION_BOMB and self.bombs_left >= 1 and not game_map.tile_has_bomb(self.position):
        new_bomb = Bomb()
        new_bomb.set_position(self.position)
        new_bomb.player = self
        new_bomb.move_to_tile_center()
        game_map.add_bomb(new_bomb)
        self.bombs_left -= 1
        
    if old_state == self.state:
      self.state_time += dt
    else:
      self.state_time = 0       # reset the state time

class Bomb(Positionable):
  def __init__(self):
    super(Bomb,self).__init__()
    self.time_of_existence = 0  ##< for how long (in ms) the bomb has existed
    self.player = None          ##< to which player the bomb belongs
    self.explodes_in = 3000     ##< time in ms in which the bomb exploded from the time it was created

## Holds and manipulates the map data including the players, bombs etc.

class Map(object):
  TILE_FLOOR = 0                ##< walkable map tile
  TILE_BLOCK = 1                ##< non-walkable but destroyable map tile
  TILE_WALL = 2                 ##< non-walkable and non-destroyable map tile

  MAP_WIDTH = 15
  MAP_HEIGHT = 11

  ## Initialises a new map from map_data (string) and a PlaySetup object.

  def __init__(self, map_data, play_setup):
    # make the tiles array:
    self.tiles = []
    starting_positions = [(0.0,0.0) for i in range(10)]      # starting position for each player

    map_data = map_data.replace(" ","").replace("\n","")     # get rid of white characters

    string_split = map_data.split(";")

    self.environment_name = string_split[0]

    line = -1
    column = 0

    for i in range(len(string_split[3])):
      tile_character = string_split[3][i]

      if i % Map.MAP_WIDTH == 0:                             # add new row
        line += 1
        column = 0
        self.tiles.append([])

      if tile_character == "x":
        tile = Map.TILE_BLOCK
      elif tile_character == "#":
        tile = Map.TILE_WALL
      else:
        tile = Map.TILE_FLOOR

      self.tiles[-1].append(tile)

      if tile_character.isdigit():
        starting_positions[int(tile_character)] = (float(column),float(line))

      column += 1

    # initialise players:

    self.players = []                                        ##< list of players in the game
    self.players_by_numbers = {}                             ##< mapping of numbers to players
    self.players_by_numbers[-1] = None

    player_slots = play_setup.get_slots()

    for i in range(len(player_slots)):
      if player_slots[i] != None:
        new_player = Player()
        new_player.set_number(i)
        new_player.set_position((starting_positions[i][0] + 0.5,starting_positions[i][1] + 0.5))
        self.players.append(new_player)
        self.players_by_numbers[i] = new_player
      else:
        self.players_by_numbers[i] = None
        
    self.bombs = []                           ##< bombs on the map

  ## Checks if there is a bomb at given tile (coordinates may be float or int).

  def tile_has_bomb(self,tile_coordinates):
    for bomb in self.bombs:
      if int(math.floor(tile_coordinates[0])) == int(math.floor(bomb.position[0])) and int(math.floor(tile_coordinates[1])) == int(math.floor(bomb.position[1])):
        return True
    
    return False

  ## Updates some things on the map that change with time.

  def update(self,dt):
    i = 0
    
    while i <= len(self.bombs) - 1:
      bomb = self.bombs[i]
      bomb.time_of_existence += dt
      
      if bomb.time_of_existence > bomb.explodes_in: # bomb explodes
        bomb.player.bomb_exploded()
        self.bombs.remove(bomb)
      else:
        i += 1

  def add_bomb(self,bomb):
    self.bombs.append(bomb)

  def get_bombs(self):
    return self.bombs

  def get_environment_name(self):
    return self.environment_name

  def get_players(self):
    return self.players

  ## Gets a dict that maps numbers to players (with Nones if player with given number doesn't exist).

  def get_players_by_numbers(self):
    return self.players_by_numbers

  def get_tiles(self):
    return self.tiles

  def __str__(self):
    result = ""

    for line in self.tiles:
      for tile in line:
        if tile == Map.TILE_FLOOR:
          result += " "
        elif tile == Map.TILE_BLOCK:
          result += "x"
        else:
          result += "#"
  
      result += "\n"

    return result

## Defines how a game is set up, i.e. how many players
#  there are, what are the teams etc. Setup does not include
#  the selected map.

class PlaySetup(object):
  def __init__(self):
    self.player_slots = [None for i in range(10)]    ##< player slots: (player_number, team_color), negative player_number = AI, slot index ~ player color index

    # default setup, player 0 vs 3 AI players:
    self.player_slots[0] = (0,0)
    self.player_slots[1] = (-1,1)
    self.player_slots[2] = (-1,2)
    self.player_slots[3] = (-1,3)

  def get_slots(self):
    return self.player_slots

## Handles conversion of keyboard events to actions of players, plus general
#  actions (such as menu, ...).

class PlayerKeyMaps(object):
  ACTION_UP = 0
  ACTION_RIGHT = 1
  ACTION_DOWN = 2
  ACTION_LEFT = 3
  ACTION_BOMB = 4
  ACTION_SPECIAL = 5
  ACTION_MENU = 6       ##< brings up the main menu

  def __init__(self):
    self.key_maps = {}  ##< maps keys to tuples of a format: (player_number, action), for general actions player_number will be -1

  ## Sets a key mapping for a player of specified (non-negative) number.

  def set_player_key_map(self, player_number, key_up, key_right, key_down, key_left, key_bomb, key_special):
    self.key_maps[key_up]      = (player_number,PlayerKeyMaps.ACTION_UP)
    self.key_maps[key_right]   = (player_number,PlayerKeyMaps.ACTION_RIGHT)
    self.key_maps[key_down]    = (player_number,PlayerKeyMaps.ACTION_DOWN)
    self.key_maps[key_left]    = (player_number,PlayerKeyMaps.ACTION_LEFT)
    self.key_maps[key_bomb]    = (player_number,PlayerKeyMaps.ACTION_BOMB)
    self.key_maps[key_special] = (player_number,PlayerKeyMaps.ACTION_SPECIAL)

  def set_special_key_map(self, key_menu):
    self.key_maps[key_menu]      = (-1,PlayerKeyMaps.ACTION_MENU)

  ## From currently pressed keys makes a list of actions being currently performed and returns it, format: (player_number, action).

  def get_current_actions(self):
    keys_pressed = pygame.key.get_pressed()

    result = []

    for key_code in self.key_maps:
      if keys_pressed[key_code]:
        result.append(self.key_maps[key_code])

    return result

class Renderer(object):
  MAP_TILE_WIDTH = 50              ##< tile width in pixels
  MAP_TILE_HEIGHT = 45             ##< tile height in pixels
  MAP_TILE_HALF_WIDTH = MAP_TILE_WIDTH / 2
  MAP_TILE_HALF_HEIGHT = MAP_TILE_HEIGHT / 2
  PLAYER_SPRITE_CENTER = (30,80)   ##< player's feet (not geometrical) center of the sprite in pixels
  BOMB_SPRITE_CENTER = (22,33)

  def __init__(self):
    self.screen_resolution = (800,600)

    self.environment_images = {}

    environment_names = ["env1"]

    for environment_name in environment_names:
      filename_floor = os.path.join(RESOURCE_PATH,"tile_" + environment_name + "_floor.png")
      filename_block = os.path.join(RESOURCE_PATH,"tile_" + environment_name + "_block.png")
      filename_wall = os.path.join(RESOURCE_PATH,"tile_" + environment_name + "_wall.png")

      self.environment_images[environment_name] = (pygame.image.load(filename_floor),pygame.image.load(filename_block),pygame.image.load(filename_wall))

    self.prerendered_map = None     # keeps a reference to a map for which some parts have been prerendered
    self.prerendered_map_background = pygame.Surface((Map.MAP_WIDTH * Renderer.MAP_TILE_WIDTH,Map.MAP_HEIGHT * Renderer.MAP_TILE_HEIGHT))

    self.player_images = []         ##< player images in format [color index]["sprite name"] and [color index]["sprite name"][frame]

    for i in range(10):
      self.player_images.append({})
      
      for helper_string in ["up","right","down","left"]:
        self.player_images[-1][helper_string] =  self.color_surface(pygame.image.load(os.path.join(RESOURCE_PATH,"player_" + helper_string + ".png")),COLOR_RGB_VALUES[i])
        
        string_index = "walk " + helper_string
      
        self.player_images[-1][string_index] = []
        self.player_images[-1][string_index].append(self.color_surface(pygame.image.load(os.path.join(RESOURCE_PATH,"player_" + helper_string + "_walk1.png")),COLOR_RGB_VALUES[i]))
        
        if helper_string == "up" or helper_string == "down":
          self.player_images[-1][string_index].append(self.color_surface(pygame.image.load(os.path.join(RESOURCE_PATH,"player_" + helper_string + "_walk2.png")),COLOR_RGB_VALUES[i]))
        else:
          self.player_images[-1][string_index].append(self.player_images[-1][helper_string])
        
        self.player_images[-1][string_index].append(self.color_surface(pygame.image.load(os.path.join(RESOURCE_PATH,"player_" + helper_string + "_walk3.png")),COLOR_RGB_VALUES[i]))
        self.player_images[-1][string_index].append(self.player_images[-1][string_index][0])
     
    self.bomb_images = []
    self.bomb_images.append(pygame.image.load(os.path.join(RESOURCE_PATH,"bomb1.png")))
    self.bomb_images.append(pygame.image.load(os.path.join(RESOURCE_PATH,"bomb2.png")))
    self.bomb_images.append(pygame.image.load(os.path.join(RESOURCE_PATH,"bomb3.png")))
    self.bomb_images.append(self.bomb_images[0])
     
  ## Returns colored image from another image. This method is slow. Color is (r,g,b) tuple of 0 - 1 floats.

  def color_surface(self,surface,color):
    result = surface.copy()
    
    for j in range(result.get_size()[1]):
      for i in range(result.get_size()[0]):
        pixel_color = result.get_at((i,j))
        
        intensity = float(pixel_color.r + pixel_color.g + pixel_color.b) / float(3 * 255)
        
        if intensity > 0.5:
          intensity = 1.0 - intensity
          
        intensity = 1 - intensity * 2
        
        one_minus_intensity = 1.0 - intensity
        
        pixel_color.r = int(intensity * pixel_color.r + one_minus_intensity * color[0] * 255)
        pixel_color.g = int(intensity * pixel_color.g + one_minus_intensity * color[1] * 255)
        pixel_color.b = int(intensity * pixel_color.b + one_minus_intensity * color[2] * 255)
        
        result.set_at((i,j),pixel_color)
    
    return result

  def tile_position_to_pixel_position(self,tile_position,center=(0,0)):
    return (int(float(tile_position[0]) * Renderer.MAP_TILE_WIDTH) - center[0],int(float(tile_position[1]) * Renderer.MAP_TILE_HEIGHT) - center[1])

  def set_resolution(self, new_resolution):
    self.screen_resolution = new_resolution

  def render_map(self, map_to_render):
    result = pygame.Surface(self.screen_resolution)

    if map_to_render != self.prerendered_map:     # first time rendering this map, prerender some stuff
      print("prerendering map...")

      for j in range(Map.MAP_HEIGHT):
        for i in range(Map.MAP_WIDTH):
          self.prerendered_map_background.blit(self.environment_images[map_to_render.get_environment_name()][0],(i * Renderer.MAP_TILE_WIDTH,j * Renderer.MAP_TILE_HEIGHT))

      self.prerendered_map = map_to_render

    result.blit(self.prerendered_map_background,(0,0))

    # order the players and bombs by their y position so that they are drawn correctly

    ordered_objects_to_render = []
    ordered_objects_to_render.extend(map_to_render.get_players())
    ordered_objects_to_render.extend(map_to_render.get_bombs())
    ordered_objects_to_render.sort(key = lambda what: what.get_position()[1])
    
    # render the map by lines:

    tiles = map_to_render.get_tiles()
    environment_images = self.environment_images[map_to_render.get_environment_name()]
    
    y = Renderer.MAP_TILE_HEIGHT - environment_images[1].get_size()[1]
    
    line_number = 0
    object_to_render_index = 0
    
    for line in tiles:
      x = (Map.MAP_WIDTH - 1) * Renderer.MAP_TILE_WIDTH
      
      while True: # render players and bombs in the current line 
        if object_to_render_index >= len(ordered_objects_to_render):
          break
        
        object_to_render = ordered_objects_to_render[object_to_render_index]
        
        if object_to_render.get_position()[1] > line_number + 1:
          break
        
        if isinstance(object_to_render,Player):
          sprite_center = Renderer.PLAYER_SPRITE_CENTER
          
          animation_frame = (object_to_render.get_state_time() / 100) % 4
          
          if object_to_render.get_state() == Player.STATE_IDLE_UP:
            image_to_render = self.player_images[object_to_render.get_number()]["up"]
          elif object_to_render.get_state() == Player.STATE_IDLE_RIGHT:
            image_to_render = self.player_images[object_to_render.get_number()]["right"]
          elif object_to_render.get_state() == Player.STATE_IDLE_DOWN:
            image_to_render = self.player_images[object_to_render.get_number()]["down"]
          elif object_to_render.get_state() == Player.STATE_IDLE_LEFT:
            image_to_render = self.player_images[object_to_render.get_number()]["left"]
          elif object_to_render.get_state() == Player.STATE_WALKING_UP:
            image_to_render = self.player_images[object_to_render.get_number()]["walk up"][animation_frame]
          elif object_to_render.get_state() == Player.STATE_WALKING_RIGHT:
            image_to_render = self.player_images[object_to_render.get_number()]["walk right"][animation_frame]
          elif object_to_render.get_state() == Player.STATE_WALKING_DOWN:
            image_to_render = self.player_images[object_to_render.get_number()]["walk down"][animation_frame]
          else: # Player.STATE_WALKING_LEFT
            image_to_render = self.player_images[object_to_render.get_number()]["walk left"][animation_frame]
        else:    # bomb
          sprite_center = Renderer.BOMB_SPRITE_CENTER
          animation_frame = (object_to_render.time_of_existence / 100) % 4
          image_to_render = self.bomb_images[animation_frame]
        
        
        render_position = self.tile_position_to_pixel_position(object_to_render.get_position(),sprite_center)
        result.blit(image_to_render,render_position)
      
        object_to_render_index += 1
      
      for tile in line:  # render tiles in the current line
        if tile == Map.TILE_BLOCK:
          result.blit(environment_images[1],(x,y))
        elif tile == Map.TILE_WALL:
          result.blit(environment_images[2],(x,y))

        x -= Renderer.MAP_TILE_WIDTH
  
      y += Renderer.MAP_TILE_HEIGHT
      line_number += 1

    return result

class Game(object):
  def __init__(self):
    pygame.init()
    self.player_key_maps = PlayerKeyMaps()

    self.player_key_maps.set_player_key_map(0,pygame.K_w,pygame.K_d,pygame.K_s,pygame.K_a,pygame.K_g,pygame.K_h)
    self.player_key_maps.set_player_key_map(1,pygame.K_i,pygame.K_l,pygame.K_k,pygame.K_j,pygame.K_o,pygame.K_p)

    self.renderer = Renderer()

  def run(self):
    screen = pygame.display.set_mode((800,600))
    time_before = pygame.time.get_ticks()

    self.game_map = Map(MAP1,PlaySetup())

    while True:     # main loop
      dt = min(pygame.time.get_ticks() - time_before,100)
      time_before = pygame.time.get_ticks()

      self.simulation_step(dt)

      for event in pygame.event.get():
        if event.type == pygame.QUIT: sys.exit()

      screen.blit(self.renderer.render_map(self.game_map),(0,0))
      pygame.display.flip()

  def simulation_step(self,dt):
    actions_being_performed = self.player_key_maps.get_current_actions()
    players = self.game_map.get_players()

    for player in players:
      player.react_to_inputs(actions_being_performed,dt,self.game_map)
      
    self.game_map.update(dt)

# main:

game = Game()
game.run()
