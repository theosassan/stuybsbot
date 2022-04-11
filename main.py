import discord
import os
import requests
import json
import random
from keep_alive import keep_alive
import asyncio
from discord.utils import get
import time
import math
import operator
from discord.ext import commands, tasks
import datetime
from discord import Color
from wordlist import wordlist
from brawlers import full_brawlers, brawlers, brawlersLow
from trivia import questions, options
import brawlstats
import socket
#
import asyncio
import json
import logging
import sys
import time
from typing import Union

import aiohttp
import requests
from cachetools import TTLCache

from brawlstats.errors import Forbidden, NotFoundError, RateLimitError, ServerError, UnexpectedError
from brawlstats.models import BattleLog, Brawlers, Club, Constants, Members, Player, Ranking
from brawlstats.utils import API, bstag, typecasted
log = logging.getLogger(__name__)
#

client = discord.Client()
in_play = []
banned = []
queue = {0:'',1:'',2:'',3:'', 4:'', 5:''}
lb = {1: '', 2:'', 3:'', 4:'', 5:''}


def ban_brawler(brawler):
  brawlers.remove(brawler)
  banned.append(brawler)
def unban_brawler(brawler):
  brawlers.append(brawler)
  banned.remove(brawler)
def select_brawlers(number):
  brawlers = ['8bit', 'Amber','Ash','Barley','Bea','Belle','Bibi','Bo','Brock','Bull','Buzz','Byron','Carl','Colette','Ruffs','Colt','Crow','Darryl','Dyna','Edgar','Primo','Emz','Frank','Gale','Gene','Griff','Jacky','Jessie','Leon','Lola','Lou','Max','Meg','Mortis','Mr. P', 'Nani','Nita','Pam','Penny','Piper','Poco','Rico','Rosa','Sandy','Shelly','Spike','Sprout','Squeak','Stu','Surge','Tara','Tick']
  
  for ban in banned:
    brawlers.remove(ban)
  for x in range(number):
    choice = random.choice(brawlers)
    in_play.append(choice)
    brawlers.remove(choice)
    
@client.event

async def on_ready():
  await client.change_presence(status = discord.Status.online, activity=discord.Game('$help'))
  

#START OF API
class Client:
    proxies = {
    "http": os.environ['QUOTAGUARDSTATIC_URL'],
    "https": os.environ['QUOTAGUARDSTATIC_URL']
    }
    res = requests.get("http://us-east-static-08.quotaguard.com/", proxies=proxies)
    #res = requests.get("http://us-east-static-08.quotaguard.com/", "http://lbzz6x1r4y1xf:yujtw4nnp7bs38xpzmw9lk0atw@us-east-static-08.quotaguard.com:9293")
    REQUEST_LOG = '{method} {url} recieved {text} has returned {status}'

    def __init__(self, token, session=None, timeout=30, is_async=False, **options):
        # Async options
        self.is_async = is_async
        self.loop = options.get('loop', asyncio.get_event_loop()) if self.is_async else None
        self.connector = options.get('connector')

        self.debug = options.get('debug', False)
        self.cache = TTLCache(3200 * 3, 60 * 3)  # 3200 requests per minute

        # Session and request options
        self.session = options.get('session') or (
            aiohttp.ClientSession(loop=self.loop, connector=self.connector) if self.is_async else requests.Session()
        )
        self.timeout = timeout
        self.prevent_ratelimit = options.get('prevent_ratelimit', False)
        if self.is_async and self.prevent_ratelimit:
            self.lock = asyncio.Lock(loop=self.loop)
        self.api = API(base_url=options.get('base_url'), version=1)

        # Request/response headers
        self.headers = {
            'Authorization': 'Bearer {}'.format(token),
            'User-Agent': 'brawlstats/{0} (Python {1[0]}.{1[1]})'.format(self.api.VERSION, sys.version_info),
            'Accept-Encoding': 'gzip'
        }

        # Load brawlers for get_rankings
        if self.is_async:
            self.loop.create_task(self.__ainit__())
        else:
            brawlers_info = self.get_brawlers()
            self.api.set_brawlers(brawlers_info)

    async def __ainit__(self):
      self.api.set_brawlers(await self.get_brawlers())


    def __repr__(self):
        return '<Client async={} timeout={} debug={}>'.format(self.is_async, self.timeout, self.debug)

    def close(self):
        return self.session.close()

    def _raise_for_status(self, resp, text):
        """
        Checks for invalid error codes returned by the API.
        """
        try:
            data = json.loads(text)
        except json.JSONDecodeError:
            data = text

        code = getattr(resp, 'status', None) or getattr(resp, 'status_code')
        url = resp.url

        if self.debug:
            log.debug(self.REQUEST_LOG.format(method='GET', url=url, text=text, status=code))

        if 300 > code >= 200:
            return data
        if code == 403:
            raise Forbidden(code, url, data['message'])
        if code == 404:
            raise NotFoundError(code, reason='Resource not found.')
        if code == 429:
            raise RateLimitError(code, url)
        if code == 500:
            raise UnexpectedError(code, url, data)
        if code == 503:
            raise ServerError(code, url)

    def _resolve_cache(self, url):
        """Find any cached response for the same requested url."""
        data = self.cache.get(url)
        if not data:
            return None
        if self.debug:
            log.debug('GET {} got result from cache.'.format(url))
        return data

    async def _arequest(self, url, use_cache=True):
        """Async method to request a url."""
        # Try and retrieve from cache
        if use_cache:
            cache = self._resolve_cache(url)
        else:
            cache = None

        if cache is not None:
            return cache

        try:
            async with self.session.get(url, timeout=self.timeout, headers=self.headers) as resp:
                data = self._raise_for_status(resp, await resp.text())
        except asyncio.TimeoutError:
            raise ServerError(503, url)
        else:
            # Cache the data if successful
            self.cache[url] = data

        return data

    def _request(self, url, use_cache=True):
        """Sync method to request a url."""
        if self.is_async:
            return self._arequest(url, use_cache)

        # Try and retrieve from cache
        if use_cache:
            cache = self._resolve_cache(url)
        else:
            cache = None
        if cache is not None:
            return cache

        try:
            with self.session.get(url, timeout=self.timeout, headers=self.headers) as resp:
                data = self._raise_for_status(resp, resp.text)
        except requests.Timeout:
            raise ServerError(503, url)
        else:
            # Cache the data if successful
            self.cache[url] = data

        return data

    async def _aget_model(self, url, model, use_cache=True, key=None):
        """Method to turn the response data into a Model class for the async client."""
        if self.prevent_ratelimit:
            # Use self.lock if prevent_ratelimit=True
            async with self.lock:
                data = await self._arequest(url, use_cache)
                await asyncio.sleep(0.1)
        else:
            data = await self._arequest(url)

        if model == Constants:
            if key:
                if data.get(key):
                    return model(self, data.get(key))
                else:
                    raise KeyError('No such Constants key "{}"'.format(key))

        return model(self, data)

    def _get_model(self, url, model, use_cache=True, key=None):
        """Method to turn the response data into a Model class for the sync client."""
        if self.is_async:
            # Calls the async function
            return self._aget_model(url, model=model, use_cache=use_cache, key=key)

        data = self._request(url, use_cache)
        if self.prevent_ratelimit:
            time.sleep(0.1)

        if model == Constants:
            if key:
                if data.get(key):
                    return model(self, data.get(key))
                else:
                    raise KeyError('No such Constants key "{}"'.format(key))

        return model(self, data)

  
    def get_player(self, tag: bstag, use_cache=True) -> Player:
  
        url = '{}/{}'.format(self.api.PROFILE, tag)
        return self._get_model(url, model=Player, use_cache=use_cache)


    get_profile = get_player


    def get_battle_logs(self, tag: bstag, use_cache=True) -> BattleLog:

        url = '{}/{}/battlelog'.format(self.api.PROFILE, tag)
        return self._get_model(url, model=BattleLog, use_cache=use_cache)



    def get_club(self, tag: bstag, use_cache=True) -> Club:

        url = '{}/{}'.format(self.api.CLUB, tag)
        return self._get_model(url, model=Club, use_cache=use_cache)



    def get_club_members(self, tag: bstag, use_cache=True) -> Members:
    
        url = '{}/{}/members'.format(self.api.CLUB, tag)
        return self._get_model(url, model=Members, use_cache=use_cache)


    def get_rankings(
        self, *, ranking: str, region: str=None, limit: int=200,
        brawler: Union[str, int]=None, use_cache=True
    ) -> Ranking:
        if brawler is not None:
            if isinstance(brawler, str):
                brawler = brawler.lower()

            # Replace brawler name with ID
            if brawler in self.api.CURRENT_BRAWLERS.keys():
                brawler = self.api.CURRENT_BRAWLERS[brawler]

            if brawler not in self.api.CURRENT_BRAWLERS.values():
                raise ValueError('Invalid brawler.')

        if region is None:
            region = 'global'

        # Check for invalid parameters
        if ranking not in ('players', 'clubs', 'brawlers'):
            raise ValueError("'ranking' must be 'players', 'clubs' or 'brawlers'.")
        if not 0 < limit <= 200:
            raise ValueError('Make sure limit is between 1 and 200.')

        # Construct URL
        url = '{}/{}/{}?limit={}'.format(self.api.RANKINGS, region, ranking, limit)
        if ranking == 'brawlers':
            url = '{}/{}/{}/{}?limit={}'.format(self.api.RANKINGS, region, ranking, brawler, limit)

        return self._get_model(url, model=Ranking, use_cache=use_cache)


    def get_constants(self, key: str=None, use_cache=True) -> Constants:
        return self._get_model(self.api.CONSTANTS, model=Constants, key=key)


    def get_brawlers(self, use_cache=True) -> Brawlers:
        return self._get_model(self.api.BRAWLERS, model=Brawlers)
      
@client.event
#
async def on_message(message):
  if message.author == client.user:
    return
  msg = message.content
  user = message.author
  #token = os.environ['.token']
  token = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzUxMiIsImtpZCI6IjI4YTMxOGY3LTAwMDAtYTFlYi03ZmExLTJjNzQzM2M2Y2NhNSJ9.eyJpc3MiOiJzdXBlcmNlbGwiLCJhdWQiOiJzdXBlcmNlbGw6Z2FtZWFwaSIsImp0aSI6IjIxY2VlNDllLTdhZDctNDM2MC1iODgzLWM3NjRiZjMwOWVhYSIsImlhdCI6MTY0OTYyMTk4Nywic3ViIjoiZGV2ZWxvcGVyLzM3ZmRhMDU0LWUzNzctZmQ2OC02MTdmLTllYTI1ODI1OTUyMCIsInNjb3BlcyI6WyJicmF3bHN0YXJzIl0sImxpbWl0cyI6W3sidGllciI6ImRldmVsb3Blci9zaWx2ZXIiLCJ0eXBlIjoidGhyb3R0bGluZyJ9LHsiY2lkcnMiOlsiMy4yMjcuMTgyLjE5MyIsIjU0LjE2MS45Ni4xMDkiXSwidHlwZSI6ImNsaWVudCJ9XX0.McqIplsiJpBfReXfpPJRBYs5oKBPKRm-JyexaRR22hh9WD3ZUKMfq46k_lBSjb4056-NqruCMMcBqrhhSHwOQQ"
  try:
    bot = Client(token)
  except Exception as e:
    print(e)
 
  with open("save.json", 'r') as f:
      users = json.load(f)
  if msg.startswith('$bregister '):
    id = msg.split('$bregister ',1)[1]
    with open('save.json', 'w') as f:
      json.dump(users, f)
    try:
      await message.channel.send(f"{bot.get_player(tag = brawlstats.utils.bstag(users[str(user.id)]['id']), use_cache=True)} successfully registered!")
      users[str(user.id)]['id'] = id
    except:
      await message.channel.send("Invalid ID. Please use the command again.")
  if msg.startswith('$bprofile'):
    profile = bot.get_player(tag = brawlstats.utils.bstag(users[str(user.id)]['id']), use_cache=True)
    embed = discord.Embed(title = f"{profile.name}'s Profile:", description = f"**Trophies:** {profile.trophies}\n**Highest Trophies: **{profile.highest_trophies}\n**EXP: **{profile.exp_level}\n**Brawlers: **{len(profile.brawlers)}/55\n**3v3 Wins: ** {profile.x3vs3_victories}\n**Solo Wins:** {profile.solo_victories}\n**Duo Wins: **{profile.duo_victories}\n**Club: **{profile.club.name}")
    embed.set_thumbnail(url = user.avatar_url)
    await message.channel.send(embed=embed)
  if msg.startswith('$bbrawlers'):
    profile = bot.get_player(tag = brawlstats.utils.bstag(users[str(user.id)]['id']), use_cache=True)
    brawlers = profile.brawlers
    brawlers2 = []
    newline = '\n'
    for brawler in brawlers:
      brawlers2.append(f"**{(brawler.name).title()}**:  Trophies - **{brawler.trophies}** | Rank - **{brawler.rank}** | Power - **{brawler.power}**")
    embed = discord.Embed(title = f"{profile.name}'s Brawlers:", description = f"{newline.join(brawlers2)}")
    embed.set_thumbnail(url = user.avatar_url)
    await message.channel.send(embed=embed)
  if msg.startswith('$stuyclub'):
    stuyclub = bot.get_club(tag = bstag ('2GP8LPLQG'), use_cache=True)
    stuyclub2 = {}
    stuyclub3 = []
    newline = '\n'
    for player in stuyclub.members:
      stuyclub2[player.name] = player.trophies
    for player in stuyclub2:
      stuyclub3.append(f"**{player} - {stuyclub2[player]}**")
    embed = discord.Embed(title = "Stuyvesant High School In-Game Club", description = f"**Trophies: {stuyclub.trophies}**\n\n{newline.join(stuyclub3)}")
    await message.channel.send(embed = embed)
    
  if msg.startswith('$tlb'):
    players = {}
    lb = {}
    lbList = []
    lbD = []
    playersList = []
    newline = '\n'
    with open("save.json", 'r') as f:
      users = json.load(f)
    for user in users:
      try:
        players[user] = users[user]['id']
      except:
        pass
    for player in players:
      profile = bot.get_player(tag = brawlstats.utils.bstag(users[player]['id']), use_cache=True)
      players[player] = profile.trophies
    players = dict(sorted(players.items(), key = lambda item: item[1], reverse = True))
    for player in players:
      profile = bot.get_player(tag = brawlstats.utils.bstag(users[player]['id']), use_cache=True)
      lb[player] = (f"**{profile.name}** - **{profile.trophies}**")
    for x in lb:
      lbList.append(x)
    for x in players:
      playersList.append(x)
    for x in range(0, (len(lb))):
      profile = bot.get_player(tag = brawlstats.utils.bstag(users[playersList[x]]['id']), use_cache=True)
      lbD.append(f"{x + 1}. **{profile.name}** ({await client.fetch_user(playersList[x])}) - **{profile.trophies}**")
    embed = discord.Embed(title = "Stuyvesant BS's Trophy Leaderboard:", description = f"{newline.join(lbD)}")
    embed.set_thumbnail(url = "https://cdn.discordapp.com/attachments/906615498664452139/962122627198099516/IMG_3210.jpg")
    await message.channel.send(embed = embed)
    
  #END OF API
  
  
  if msg.startswith('$register'):
    user = message.author
    with open("brawl.json", 'r') as f:
      brawl = json.load(f)
    if str(user.id) in brawl:
      await message.channel.send("You are already registered! Use $profile to view your profile.")
    else:
      brawl[str(user.id)] = {}
      brawl[str(user.id)]['brawlers'] = ["Nita", "Colt", "Bull", "Jessie", "Brock", "Dynamike", "Bo", "Tick", "8-Bit", "Emz", "Stu"]
      brawl[str(user.id)]['coins'] = 0
      brawl[str(user.id)]['gems'] = 0
    with open("brawl.json", 'w') as f:
      brawl = json.dump(brawl, f)

  if msg.startswith('$profile'):
    user = message.author
    with open("brawl.json", 'r') as f:
      brawl = json.load(f)
    if str(user.id) not in brawl:
      await message.channel.send("Please first use $register!")
    else:
      brawlers = brawl[str(user.id)]['brawlers']
      coins = brawl[str(user.id)]['coins']
      gems = brawl[str(user.id)]['gems']
      pp = brawl[str(user.id)]['pp']
    embed = discord.Embed(title = f"{user.name}'s Profile:", description = f"\n**Brawlers:** {len(brawlers)}/55\n**Coins**: {coins}\n**Gems:** {gems}\n**Power Points: **{pp}")
    embed.set_thumbnail(url = user.avatar_url)
    await message.channel.send(embed = embed)

    with open("brawl.json", 'w') as f:
      brawl = json.dump(brawl, f)  

  if msg.startswith("$gemshop"):
    embed = discord.Embed(title = "StuyBS Gem Shop", description = "**Gems** - To purchase, type **buygems [gems]**.\n***30 Gems*** - *100 SB*\n***80 Gems*** - *250 SB*\n***170 Gems*** - *500 SB*\n***360 Gems*** - *1000 SB*\n***950 Gems*** - *2500 SB*\n ***2000 Gems*** - *5000 SB*")
    embed.set_image(url = "https://cdn.discordapp.com/attachments/947292794345652225/962387398589829150/IMG_3213.jpg")
    await message.channel.send(embed = embed)

  if msg.startswith("$buygems "):
    user = message.author
    with open("brawl.json", 'r') as f:
      brawl = json.load(f)
    with open("save.json", 'r') as f:
      users = json.load(f)
    amt = int(msg.split("$buygems ",1)[1])
    if amt == 30:
      if users[str(user.id)]['points'] >= 100:
        users[str(user.id)]['points'] -= 100
        brawl[str(user.id)]['gems'] += 30
        await message.channel.send("Purchased **30 Gems** for **100 SB**.")
      else:
        await message.channel.send("Not enough SB!")
    elif amt == 80:
      if users[str(user.id)]['points'] >= 250:
        users[str(user.id)]['points'] -= 250
        brawl[str(user.id)]['gems'] += 80
        await message.channel.send("Purchased **80 Gems** for **250 SB**.")
      else:
        await message.channel.send("Not enough SB!")
    elif amt == 170:
      if users[str(user.id)]['points'] >= 500:
        users[str(user.id)]['points'] -= 500
        brawl[str(user.id)]['gems'] += 170
        await message.channel.send("Purchased **170 Gems** for **500 SB**.")
      else:
        await message.channel.send("Not enough SB!")
    elif amt == 360:
      if users[str(user.id)]['points'] >= 1000:
        users[str(user.id)]['points'] -= 1000
        brawl[str(user.id)]['gems'] += 360
        await message.channel.send("Purchased **360 Gems** for **1000 SB**.")
      else:
        await message.channel.send("Not enough SB!")
    elif amt == 950:
      if users[str(user.id)]['points'] >= 2500:
        users[str(user.id)]['points'] -= 2500
        brawl[str(user.id)]['gems'] += 950
        await message.channel.send("Purchased **950 Gems** for **2500 SB**.")
      else:
        await message.channel.send("Not enough SB!")
    elif amt == 2000:
      if users[str(user.id)]['points'] >= 5000:
        users[str(user.id)]['points'] -= 5000
        brawl[str(user.id)]['gems'] += 2000
        await message.channel.send("Purchased **2000 Gems** for **5000 SB**.")
      else:
        await message.channel.send("Not enough SB!")
    else:
      await message.channel.send("Please use **$sshop** to see what you can buy!")
    with open("brawl.json", 'w') as f:
      brawl = json.dump(brawl, f)  
    with open("save.json", 'w') as f:
      users = json.dump(users, f) 
  if msg.startswith("$doonce"):
    with open("brawl.json", 'r') as f:
      brawl = json.load(f) 
    for user in brawl:
      brawl[user]['brawlers'] = {"Shelly" : 1, "Nita" : 1, "Colt" : 1, "Bull" : 1, "Jessie" : 1, "Brock" : 1, "Dynamike" : 1, "Bo" : 1, "Tick" : 1, "8-Bit" :1, "Emz" : 1, "Stu" : 1}
    with open("brawl.json", 'w') as f:
      brawl = json.dump(brawl, f)  
  trophyRoad1 = ["Nita", "Colt", "Bull", "Jessie", "Brock", "Dynamike", "Bo", "Tick", "8-Bit", "Emz", "Stu"]
  rare1 = ["El Primo", "Barley", "Poco", "Rosa"]
  superRare1 = ["Rico", "Darryl", "Penny", "Carl", "Jacky"]
  epic1 = ["Piper", "Pam", "Frank", "Bibi", "Bea", "Nani","Edgar","Griff","Grom"]
  mythic1 = ["Mortis","Tara","Gene","Max","Mr. P","Sprout","Byron","Squeak"]
  legendary1 = ["Spike","Crow","Leon","Sandy","Amber","Meg"]
  chromatic1 = ["Gale","Surge","Colette","Lou","Colonel Ruffs","Belle","Buzz","Ash","Lols","Fang","Eve"]
  if msg.startswith("$buy bb"):
    with open("brawl.json", 'r') as f:
      brawl = json.load(f)
    user = message.author
    brawlers = brawl[str(user.id)]['brawlers']
    trophyRoad = []
    rare = []
    superRare = []
    epic = []
    mythic = []
    legendary = []
    chromatic = []
    for brawler in trophyRoad1:
      if brawler not in brawlers:
        trophyRoad.append(brawler)
    for brawler in rare1:
      if brawler not in brawlers:
        rare.append(brawler)
    for brawler in superRare1:
      if brawler not in brawlers:
        superRare.append(brawler)
    for brawler in epic1:
      if brawler not in brawlers:
        epic.append(brawler)
    for brawler in mythic1:
      if brawler not in brawlers:
        mythic.append(brawler)
    for brawler in legendary1:
      if brawler not in brawlers:
        legendary.append(brawler)
    for brawler in chromatic1:
      if brawler not in brawlers:
        chromatic.append(brawler)
        
    coins = brawl[str(user.id)]['coins']
    gems = brawl[str(user.id)]['gems']
    pp = brawl[str(user.id)]['pp']
    newline = "\n"
    if brawl[str(user.id)]['gems'] >= 30:
      brawl[str(user.id)]['gems'] -= 30
      bgot = ""
      coinsgot = 0
      gemsgot = 0
      ppgot = 0
      
      for x in range(3):
        coinsgot += random.randint(15,25)
        gemsgot += random.randint(0, 2)
        ppgot += random.randint(5, 20)
      rand = random.randint(0, 1000)
      try:
        if rand in [0]:
          bgot = legendary[random.randint(0, len(legendary) - 1)]
        elif rand in range(0, 5):
          bgot = mythic[random.randint(0, len(mythic) - 1)]
        elif rand in range(0, 20):
          bgot = epic[random.randint(0, len(epic) - 1)]
        elif rand in range(0, 40):
          bgot = superRare[random.randint(0, len(superRare) - 1)]
        elif rand in range(0, 80):
          bgot = rare[random.randint(0, len(rare) - 1)]
        else:
          pass
      except:
        pass
      if bgot != "":
        brawl[str(user.id)]['brawlers'][bgot] = 1
      else:
        pass
      brawl[str(user.id)]['coins'] += coinsgot
      brawl[str(user.id)]['gems'] += gemsgot
      brawl[str(user.id)]['pp'] += ppgot
      with open("brawl.json", 'w') as f:
        brawl = json.dump(brawl, f) 
      #await message.channel.send("Purchasing Big Box...")
      #await asyncio.sleep(1)
      embed = discord.Embed(title = "You got...", description = f"**{coinsgot}** Coins\n**{gemsgot}** Gems\n**{ppgot}** Power Points")
      embed.set_thumbnail(url = "https://cdn.discordapp.com/attachments/947292794345652225/962389536078450698/IMG_3215.png")
      embed.set_footer(text = "-30 gems")
      await message.channel.send(embed = embed)
      if bgot!= "":
        embed = discord.Embed(title = "and...")
        embed.set_image(url = "https://cdn.discordapp.com/attachments/906615498664452139/962946010714366002/IMG_3223.gif")
        await message.channel.send(embed = embed)
        await asyncio.sleep(2)
        await message.channel.send(f"**{bgot.upper()}**!!")
    
    else:
      await message.channel.send(f"You need **{30 - gems}** more gems to purchase this item!")
    
      
  if msg.startswith("$buy mb"):
    
    with open("brawl.json", 'r') as f:
      brawl = json.load(f)
    user = message.author
    brawlers = brawl[str(user.id)]['brawlers']
    coins = brawl[str(user.id)]['coins']
    gems = brawl[str(user.id)]['gems']
    pp = brawl[str(user.id)]['pp']
    newline = "\n"
    trophyRoad = []
    rare = []
    superRare = []
    epic = []
    mythic = []
    legendary = []
    chromatic = []
    for brawler in trophyRoad1:
      if brawler not in brawlers:
        trophyRoad.append(brawler)
    for brawler in rare1:
      if brawler not in brawlers:
        rare.append(brawler)
    for brawler in superRare1:
      if brawler not in brawlers:
        superRare.append(brawler)
    for brawler in epic1:
      if brawler not in brawlers:
        epic.append(brawler)
    for brawler in mythic1:
      if brawler not in brawlers:
        mythic.append(brawler)
    for brawler in legendary1:
      if brawler not in brawlers:
        legendary.append(brawler)
    for brawler in chromatic1:
      if brawler not in brawlers:
        chromatic.append(brawler)
    if brawl[str(user.id)]['gems'] >= 80:
      brawl[str(user.id)]['gems'] -= 80
      bgot = ""
      coinsgot = 0
      gemsgot = 0
      ppgot = 0
      
      for x in range(10):
        coinsgot += random.randint(15,25)
        gemsgot += random.randint(0, 2)
        ppgot += random.randint(5, 20)
      rand = random.randint(0, 350)
      try:
        if rand in [0]:
          bgot = legendary[random.randint(0, len(legendary) - 1)]
        elif rand in range(0, 5):
          bgot = mythic[random.randint(0, len(mythic) - 1)]
        elif rand in range(0, 20):
          bgot = epic[random.randint(0, len(epic) - 1)]
        elif rand in range(0, 40):
          bgot = superRare[random.randint(0, len(superRare) - 1)]
        elif rand in range(0, 80):
          bgot = rare[random.randint(0, len(rare) - 1)]
        else:
          pass
      except:
        pass
      if bgot != "":
        brawl[str(user.id)]['brawlers'][bgot] = 1
      else:
        pass
      brawl[str(user.id)]['coins'] += coinsgot
      brawl[str(user.id)]['gems'] += gemsgot
      brawl[str(user.id)]['pp'] += ppgot
      with open("brawl.json", 'w') as f:
        json.dump(brawl, f) 
      #await message.channel.send("Purchasing Mega Box...")
      #await asyncio.sleep(1)
      embed = discord.Embed(title = "You got...", description = f"**{coinsgot}** Coins\n**{gemsgot}** Gems\n**{ppgot}** Power Points\n")
      embed.set_thumbnail(url = "https://cdn.discordapp.com/attachments/947292794345652225/962389532282601532/IMG_3216.png")
      embed.set_footer(text = "-80 gems")
      await message.channel.send(embed = embed)
      if bgot!= "":
        embed = discord.Embed(title = "and...")
        embed.set_image(url = "https://cdn.discordapp.com/attachments/906615498664452139/962946010714366002/IMG_3223.gif")
        await message.channel.send(embed = embed)
        await asyncio.sleep(2)
        await message.channel.send(f"**{bgot.upper()}**!!")
      
    else:
      await message.channel.send(f"You need **{80 - gems}** more gems to purchase this item!")
    

  if msg.startswith('$brawlers'):
    with open("brawl.json", 'r') as f:
      brawl = json.load(f)
    user = message.author
    brawlers = []
    brawlersD = []
    newline = "\n"
    brawlers2 = brawl[str(user.id)]['brawlers']
    brawlers2 = dict(sorted(brawlers2.items(), key = lambda item: item[1], reverse = True))
    for brawler in brawlers2:
      brawlers.append(brawler)
    for brawler in brawlers:
      brawlersD.append(f"**{brawler}** - Power **{brawl[str(user.id)]['brawlers'][brawler]}**")
      
    embed = discord.Embed(title = f"{user.name}'s StuyBS Simulator Brawlers:", description = f"{newline.join(brawlersD)}")
    embed.set_thumbnail(url = user.avatar_url)
    await message.channel.send(embed=embed)
    
  if msg.startswith('$upgrade '):
    brawler = (msg.split('$upgrade ',1)[1]).title()
    with open("brawl.json", 'r') as f:
      brawl = json.load(f)
    user = message.author
      
    if brawler in brawl[str(user.id)]['brawlers']:
      ppNeeded = math.floor(5 * 1.5 ** (brawl[str(user.id)]['brawlers'][brawler]))
      coinsNeeded = math.floor(5 * 1.6 ** (brawl[str(user.id)]['brawlers'][brawler]))
      if brawl[str(user.id)]['brawlers'][brawler] >= 11:
        await message.channel.send(f"**{brawler.title()}** is already at max level!")
      else:
        if brawl[str(user.id)]['pp'] > ppNeeded and brawl[str(user.id)]['coins'] > coinsNeeded:
          brawl[str(user.id)]['brawlers'][brawler] += 1
          brawl[str(user.id)]['pp'] -= ppNeeded
          brawl[str(user.id)]['coins'] -= coinsNeeded            
          await message.channel.send(f"**{brawler}** has been upgraded to **Power {brawl[str(user.id)]['brawlers'][brawler]}**!")
          with open("brawl.json", 'w') as f:
            brawl = json.dump(brawl, f)  
        else:
          await message.channel.send(f"You need **{ppNeeded} Power Points** and **{coinsNeeded} Coins** to upgrade this brawler!")
    else:
      await message.channel.send(f"You have not yet unlocked **{brawler}**!")


  if msg.lower().startswith('$select'):
    in_play.clear()
    brawlers = []
    number = int(msg.lower().split('$select ',1)[1])
    brawler = select_brawlers(number)
    joined = ', '.join(in_play)
    await message.channel.send(f'The brawlers in play are: **{joined}**')
  if msg.lower().startswith('$teamselect'):
    
    in_play.clear()
    select_brawlers(3)
    joined = ', '.join(in_play)
    await message.channel.send(f'Team 1 brawlers: **{joined}**')
    in_play.clear()
    select_brawlers(3)
    joined = ', '.join(in_play)
    await message.channel.send(f'Team 2 brawlers: **{joined}**')
  if msg.startswith('$ban '):
    
    brawler = (msg.split('$ban ',1)[1]).title()
    brawlers = ['8bit', 'Amber','Ash','Barley','Bea','Belle','Bibi','Bo','Brock','Bull','Buzz','Byron','Carl','Colette','Ruffs','Colt','Crow','Darryl','Dyna','Edgar','Primo','Emz','Frank','Gale','Gene','Griff','Jacky','Jessie','Leon','Lola','Lou','Max','Meg','Mortis','Mr. P', 'Nani','Nita','Pam','Penny','Piper','Poco','Rico','Rosa','Sandy','Shelly','Spike','Sprout','Squeak','Stu','Surge','Tara','Tick']

    for ban in banned:
      brawlers.remove(ban)
    
    if brawler in brawlers:
      ban_brawler(brawler)
      await message.channel.send(f'**{brawler}** has been banned.')
    elif brawler in full_brawlers:
      await message.channel.send(f'**{brawler}** has already been banned!')
    else:
      await message.channel.send(f"Do you work at Supercell? Don't think they've released that one yet.")
    
  if msg.lower().startswith('$unban'):
    brawlers = ['8bit', 'Amber','Ash','Barley','Bea','Belle','Bibi','Bo','Brock','Bull','Buzz','Byron','Carl','Colette','Ruffs','Colt','Crow','Darryl','Dyna','Edgar','Primo','Emz','Frank','Gale','Gene','Griff','Jacky','Jessie','Leon','Lola','Lou','Max','Meg','Mortis','Mr. P', 'Nani','Nita','Pam','Penny','Piper','Poco','Rico','Rosa','Sandy','Shelly','Spike','Sprout','Squeak','Stu','Surge','Tara','Tick']
    for ban in banned:
        brawlers.remove(ban)
    brawler = (msg.split('$unban ',1)[1]).title()
    if brawler in brawlers:
      await message.channel.send(f'**{brawler}** is already in play!')
    else:
      unban_brawler(brawler)
      await message.channel.send(f'**{brawler}** has been unbanned.')
      
  if msg.lower().startswith('$randommap'):
    mode = msg.split('$randommap ',1)[1]
    any = ['Hard Rock Mine', 'Crystal Arcade', 'Deathcap Trap', 'Gem Fort', 'Undermine',' Deep Diner', 'Flooded Mine', 'Four Squared', 'Double Swoosh', 'Minecart Madness', 'Acute Angle', 'Cotton Candy Dreams', 'Pierced', 'Gem Source', 'Skull Creek', 'Scorched Stone',' Rockwall Brawl', 'Feast or Famine', 'Acid Lakes',' Cavern Churn','Double Trouble','Dark Passage','Stocky Stockades','Safety Center','Dark Fantasies','Mystic Touch','Dried Up River','Ruins','Kaboom Canyon','Safe Zone','Hot Potato','Bridge Too Far','Pit Stop','Diagonal Alley','Rattlesnake Ravine','Shooting Star','Hideout','Excel','Layer Cake','Dry Season','Electric Zone','Cube Force','Backyard Bowl','Triple Dribble','Pinhole Punt','Sneaky Fields','Super Stadium','Pinball Dreams','Center Stage','Field Goal','Slalom Slam','Power Shot','Center Field','Sticky Notes','Firm Grip','Binary Coding','Bot Drop','Some Assembly Required','Nuts and Bolts','Junk Park','Factory Rush','Robo Ring','Controller Chaos','Parallel Plays','Split','Ring of Fire','Dueling Beetles','Night at the Museum','Ends Meet','Middle Ground','Goldarm Gulch',"Belle's Rock",'Deep End',"Luis' Revenge",'Flaring Phoenix']
    gemgrab=['Hard Rock Mine', 'Crystal Arcade', 'Deathcap Trap', 'Gem Fort', 'Undermine',' Deep Diner', 'Flooded Mine', 'Four Squared', 'Double Swoosh', 'Minecart Madness', 'Acute Angle', 'Cotton Candy Dreams', 'Pierced', 'Gem Source']
    brawlball=['Backyard Bowl','Triple Dribble','Pinhole Punt','Sneaky Fields','Super Stadium','Pinball Dreams','Center Stage','Field Goal','Slalom Slam','Power Shot','Center Field','Sticky Notes','Firm Grip','Binary Coding']
    showdown=['Skull Creek', 'Scorched Stone',' Rockwall Brawl', 'Feast or Famine', 'Acid Lakes',' Cavern Churn','Double Trouble','Dark Passage','Stocky Stockades','Safety Center','Dark Fantasies','Mystic Touch','Dried Up River','Ruins']
    heist=['Kaboom Canyon','Safe Zone','Hot Potato','Bridge Too Far','Pit Stop','Diagonal Alley','Rattlesnake Ravine']
    bounty=['Shooting Star','Hideout','Excel','Layer Cake','Dry Season','Electric Zone','Cube Force']
    siege=['Bot Drop','Some Assembly Required','Nuts and Bolts','Junk Park','Factory Rush','Robo Ring']
    hotzone=['Controller Chaos','Parallel Plays','Split','Ring of Fire','Dueling Beetles','Night at the Museum']
    knockout=['Ends Meet','Middle Ground','Goldarm Gulch',"Belle's Rock",'Deep End',"Luis' Revenge",'Flaring Phoenix']
    pl = ['Hard Rock Mine', 'Gem Fort','Minecart Madness','Shooting Star','Layer Cake','Dry Season','Hot Potato','Pit Stop','Safe Zone','Dueling Beetles','Ring of Fire','Split','Sneaky Fields','Sunny Soccer','Backyard Bowl']
    stuypl = ['Pierced', 'Double Swoosh', 'Hot Potato', 'Bridge Too Far', 'Pit Stop', 'Backyard Bowl','Pinhole Punt', 'Bot Drop', 'Some Assembly Required', 'Split', 'Ring of Fire', 'Controller Chaos', 'Middle Ground', 'Goldarm Gultch', 'Deep End']
    if mode == 'any':
      show = random.choice(any)
    elif mode == 'gem grab':
      show = random.choice(gemgrab)
    elif mode == 'brawl ball':
      show = random.choice(brawlball)
    elif mode == 'showdown':
      show =random.choice(showdown)
    elif mode == 'heist':
      show =random.choice(heist)
    elif mode == 'bounty':
      show =random.choice(bounty)
    elif mode == 'siege':
      show =random.choice(siege)
    elif mode == 'hot zone':
      show =random.choice(hotzone)
    elif mode == 'knockout':
      show =random.choice(knockout)
    elif mode == 'pl':
      show = random.choice(pl)
    elif mode == 'stuypl':
      show = random.choice(stuypl)
    else:
      await message.channel.send(f"Do you work at Supercell? Don't think that mode exists yet.")
    await message.channel.send(f'Selected map: {show}')


  if msg.lower().startswith('$bans'):
    ban_list = ', '.join(banned)
    await message.channel.send(f'The banned brawlers are: **{ban_list}**')
  if msg.lower().startswith('$choose'):
    
    choice = random.choice(full_brawlers)
    await message.channel.send(f"Hmm... you shall play... **{choice}!**")
  if msg.lower().startswith('$help'):
    
    emh = discord.Embed(color = Color.light_grey(), title = "Help is on the way!", description = "**StuyBS Simluator **\n\n***$register:*** Registers your StuyBS Simulator profile.\n\n***$profile:*** Displays a summary of your StuyBS profile.\n\n***$brawlers:*** Displays a list of your StuyBS Brawlers and their stats.\n\n***$gemshop:*** Displays the StuyBS Simulator gem shop.\n\n***$upgrade [brawler]:*** Upgrades a specificed Brawler.\n\n**Brawl Stars (Currently Disabled)**\n\n***$bregister [id]:*** Registers your in-game profile.\n\n***$bprofile:*** Displays a summary of your in-game profile.\n\n***$bbrawlers:*** Displays a list of your in-game Brawlers and their stats.\n\n***$tlb:*** Displays the server's Trophy Leaderboard.\n\n***$stuyclub:*** Displays the Stuyvesant in-game club. \n\n**StuyBucks**\n\n***$wordle:*** Starts a game of Wordle.\n\n***$trivia:*** Starts a game of brawl stars trivia. \n\n***$hm:*** Starts a game of hangman. \n\n***$hunt:*** Hunt for a randomized brawler to gain or lose points.\n\n***$gtn***: Starts a game of guess the number.\n\n***$sb:*** Displays your StuyBucks count. \n\n***$lb:*** Displays the StuyBucks leaderboard.\n\n***$shop:*** Opens the StuyBucks shop.\n\n***$buy [item]:*** Purchase an item from the shop.\n\n***$bid [amt]:*** Bids a specified amount for the ongoing auction.\n\n***$donate [amt] to [user]:*** Donates a specified amount to a specified user.\n\n**Other**\n\n***$select:*** Randomizes a specified subset of brawlers - *excludes banned brawlers.*\n\n***$ban [brawler]:*** Bans a specified brawler.\n\n***$unban [brawler]:*** Unbans a specified brawler.\n\n***$resetbans:*** Unbans all currently banned brawlers.\n\n***$bans:*** Lists the currently banned brawlers.\n\n***$randommap [mode]:*** Randomizes a map from the specified game mode - *Inputs include 'any' for any mode and 'pl' for power league maps.*\n\n***$choose:*** Randomly selects a brawler for the user to play.")
    await message.channel.send(embed = emh)
  if msg.lower().startswith('$randomizetourney'):
    select_brawlers(8)
    joined_play1 = ', '.join(in_play)
    in_play.clear()
    select_brawlers(7)
    joined_play2 = ', '.join(in_play)
    in_play.clear()
    select_brawlers(7)
    joined_play3 = ', '.join(in_play)
    in_play.clear()
    select_brawlers(7)
    joined_play4 = ', '.join(in_play)
    in_play.clear()
    await message.channel.send(f"\nLooks like we're ready to start the tournament!\n*The brawlers in play for each game are as follows:*\n\n**Game 1 -** {joined_play1}\n\n**Game 2 -** {joined_play2}\n\n**Game 3 -** {joined_play3}\n\n**Game 4 -** {joined_play4}\n\n**Good luck** and **have fun!**")
  async def lottery():
    user = message.author
    with open("lottery.json", 'r') as f:
      lottery = json.load(f)
    randomnum = random.randint(1, len(lottery)) - 1
    ticket = lottery[randomnum]
    lottery.remove(ticket)
    lotteryem = discord.Embed(color = Color.gold(), title = f"{user.name}'s lottery ticket number: **{ticket}**")
    lotteryem.add_field(name = "ID:", value = f"**{user.discriminator}**")
    lotteryem.add_field(name = "Date:", value = f"\n**{str(datetime.date.today())}**")
    lotteryem.set_thumbnail(url = user.avatar_url)
    lotteryem.set_image(url = "https://cdn.discordapp.com/attachments/906615498664452139/946487855348338758/9A38F250-38E0-48C7-BDA6-5E1AB7655256.jpg")
    lotteryem.set_footer(text = "Save a screenshot of this ticket to your device. If your number matches the winning number (TBA at 10PM), send an image of this ticket to @bien#8887.\nNote: This ticket is only valid for the date it was purchased on.\n- 250 SB")
    await user.send(embed = lotteryem)
    verifychannel = client.get_channel(947292794345652225)
    await verifychannel.send(embed = lotteryem)
    with open("lottery.json", 'w') as f:
      lottery = json.dump(lottery, f)
  async def resetlottery():
    with open("lottery.json", 'r') as f:
      lottery = json.load(f)
    lottery.clear()
    x=0
    while x < 1000:
      lottery.append(x)
      x+=1
    with open("lottery.json", 'w') as f:
        lottery = json.dump(lottery, f)
  if msg.lower().startswith('$resetbans'):
    for ban in banned:
      banned.remove(ban)
      brawlers.append(ban)
    await message.channel.send('All brawlers are now in play.')
  if msg.lower().startswith('$waifu'):
    await message.channel.send('Calsie, is that you?')
  if msg.lower().startswith('$joinqueue'):
    user = msg.split('$joinqueue ',1)[1]
    for _ in queue:
      if queue[_] == '':
        queue[_] = user
        break
      else:
        pass

    await message.channel.send(f'**The current club queue is:**\n1st: {queue[0]}\n2nd: {queue[1]}\n3rd: {queue[2]}\n4th: {queue[3]}\n5th: {queue[4]}')
    
  
  if msg.lower().startswith('$queue'):
    await message.channel.send(f'**The current club queue is:**\n1st: {queue[0]}\n2nd: {queue[1]}\n3rd: {queue[2]}\n4th: {queue[3]}\n5th: {queue[4]}')
  if msg.lower().startswith('$unqueue'):
    user = str(msg.split('$unqueue ',1)[1])
    places = list(queue.keys())
    users = list(queue.values())
    pos = users.index(user)
    queue[pos] = ''
    for _ in range(4):
      if queue[_] == '':
          queue[_] = queue[_+1]
          queue[_+1] = ''
    await message.channel.send(f'**The current club queue is:**\n1st: {queue[0]}\n2nd: {queue[1]}\n3rd: {queue[2]}\n4th: {queue[3]}\n5th: {queue[4]}')
  
  if msg.lower() == ('$sb') or msg.lower().startswith('$points') or msg.lower().startswith('$StuyBucks'):
    global correct
    user = message.author
    with open("save.json", 'r') as f:
      users = json.load(f)
    if str(user.id) in users:
      pass
    else:
      users[str(user.id)] = {}
      users[str(user.id)]['huntingdoubler'] = 1
      users[str(user.id)]['triviadoubler'] = 1
      users[str(user.id)]['points'] = 0
      users[str(user.id)]['raffleticket'] = 0
      users[str(user.id)]['gtndoubler'] = 1
      users[str(user.id)]['bid'] = 0
      users[str(user.id)]['wordle'] = 0
    point_amt = users[str(user.id)]['points']
    with open('save.json', 'w') as f:
      json.dump(users, f)
    em = discord.Embed(title = f"{message.author.name}'s Stuybucks:\n{point_amt}")
  
    em.set_thumbnail(url = message.author.avatar_url)
    await message.channel.send(embed = em)
  global wait
  
  if msg.lower().startswith('$trivia'):
    global questions
    global options
    async def playgame():
      global correct
      
      user = message.author
      with open("save.json", 'r') as f:
        users = json.load(f)
      question = random.randint(0,53)
      
      qlist = list(questions.keys())
      
    
      q = questions[qlist[question]]
      question_list = options[question]
      question_sep = ("\n".join(question_list))
      em = discord.Embed(color = Color.teal(), title = f"{qlist[question]}\n{question_sep}")
      msg = await message.channel.send(embed = em)
      async def waiting():
        global done
        
        done = True

      global done
      done = False
      user = message.author
      while done == False:
        await waiting()
        while True:
          ms = await client.wait_for('message')
          if ms.author == user:
            msg2 = ms
            break
        if msg2.content.upper() in ["A", "B", "C", "D"]:
          answer = msg2.content.upper()
          
          if answer == q:
            done = True
            
            correct = 1
          else:
            done = True
            
            correct = 2
        else:
          await message.channel.send('Invalid answer; please respond with a letter from A-D!')
          done = True
          correct = 3
    gain = random.randint(10, 30)
    user = message.author
    
    with open("save.json", 'r') as f:
      users = json.load(f)
    
    with open('save.json', 'w') as f:
      json.dump(users, f)
    await playgame()
    
    with open("save.json", 'r') as f:
      users = json.load(f)
    
    with open('save.json', 'w') as f:
      json.dump(users, f)
    
    if correct == 1:
        with open("save.json", 'r') as f:
          users = json.load(f)
        em = discord.Embed(color = Color.green(), title = f"That is correct!\nYou just gained {(gain * users[str(user.id)]['triviadoubler'])} StuyBucks.")
        em.set_image(url = "https://cdn.discordapp.com/attachments/906615498664452139/942535243133501510/IMG_2527.png")
        await message.channel.send(embed = em)
        
        if str(user.id) in users:
          users[str(user.id)]['points'] += (gain * users[str(user.id)]['triviadoubler'])
        else:
          users[str(user.id)] = {}
          users[str(user.id)]['huntingdoubler'] = 1
          users[str(user.id)]['triviadoubler'] = 1
          users[str(user.id)]['points'] = gain
          users[str(user.id)]['raffleticket'] = 0
          users[str(user.id)]['gtndoubler'] = 1
          users[str(user.id)]['bid'] = 0
        with open('save.json', 'w') as f:
          json.dump(users, f)
        
    
    elif correct == 2:
      with open("save.json", 'r') as f:
          users = json.load(f)
      em = discord.Embed(color = Color.red(), title = f"That is incorrect.\nYou just lost {gain} StuyBucks.")
      em.set_image(url = "https://cdn.discordapp.com/attachments/906615498664452139/942535248510611506/IMG_2526.png")
      await message.channel.send(embed = em)
      if str(user.id) in users:
        users[str(user.id)]['points'] -= (gain)
      else:
        users[str(user.id)] = {}
        users[str(user.id)]['points'] = 0
        users[str(user.id)]['huntingdoubler'] = 1
        users[str(user.id)]['triviadoubler'] = 1
        users[str(user.id)]['raffleticket'] = 0
        users[str(user.id)]['gtndoubler'] = 1
        users[str(user.id)]['bid'] = 0
      with open('save.json', 'w') as f:
        json.dump(users, f)
    async def starttimer():
      global wait
      await asyncio.sleep(60)
      wait = False
    
    #wait = True
    #await starttimer()
  async def hunt():
    with open("save.json", 'r') as f:
          users = json.load(f)
    user = message.author
    em3 = discord.Embed(title = 'You take out your hunting rifle and walk into a bush...')
    em3.set_image(url = 'https://cdn.discordapp.com/attachments/906615498664452139/942939629307441192/IMG_2535.png')
    await message.channel.send(embed = em3)
    await asyncio.sleep(2)
    await message.channel.send('**You find a...**')
    await asyncio.sleep(2)
        #em3.set_image(url = img)
        #await message.channel.send(embed = em)  
    result = random.randint(1,12)
    textr = ''
    imgr = ''
    if result == 1:
      gain = -50
      textr = "SHELLY?!?!\nYou're quickly shotgunned in the face and vanish into thin air."
      descr = '**-50 points**'
      imgr = 'https://cdn.discordapp.com/attachments/906615498664452139/942949097881612419/IMG_2536.png'
    elif result == 2:
      gain = 30
      textr = 'Jessie! Who could harm such a thing?\nShe gifts you a brand new turret for rescuing her from the wilderness.'
      descr = f'**+{gain} points.**'
      imgr = 'https://cdn.discordapp.com/attachments/906615498664452139/942949098334609448/IMG_2537.png'
    elif result == 3:
      gain = 25
      textr = "Byron!\nHe gifts you some herbal tonics so that you will not shoot him, and you pretend that the exchange didn't happen."
      descr = f'**+{gain} points.**'
      gain = 25
      imgr = 'https://cdn.discordapp.com/attachments/906615498664452139/942949100943454249/IMG_2538.png'
    elif result == 4:
      gain = 30
      textr = "Lou!\nHe offers a snow cone, and the sound of his voice makes you instantly shoot him in the head."
      descr = f'**+{gain} points.**'
      imgr = 'https://cdn.discordapp.com/attachments/906615498664452139/942949107134242887/IMG_2539.png'
    elif result == 5:
      gain = -25
      textr = "Frank!\nHe only laughs, calculating the unfortunate health to damage ratio between him and your hunting rifle. You're out of there."
      descr = f'**-{gain} points.**'
      
      imgr = 'https://cdn.discordapp.com/attachments/906615498664452139/942949109512405012/IMG_2540.png'
    elif result == 6:
      gain = -30
      textr = "Piper!\nShe invites you to her house for some homemade recipe. What you don't know is that this recipe contains something you probably shouldn't have eaten."
      descr = f'**-{gain} points.**'
      imgr = 'https://cdn.discordapp.com/attachments/906615498664452139/942949114692382791/IMG_2541.png'
    elif result == 7:
      gain = 40
      textr = "Poco!\nHe plays you a pretty swan song, and suddenly you're too charmed to hunt him..."
      descr = f'**+{gain} points.**'
      imgr = 'https://cdn.discordapp.com/attachments/906615498664452139/942949117922013254/IMG_2542.png'
    elif result == 8:
      gain = -40
      textr = "Leon!\nYou steady your shot and fire. It isn't long before you realize that you shot his clone..."
      descr = f'**-{gain} points.**'
      imgr = 'https://cdn.discordapp.com/attachments/906615498664452139/942949123584299049/IMG_2543.png'
    elif result == 9:
      gain = 0
      textr = "Buzz!\nHe starts crying. Like... sobbing. He asks if he can play his trombone before he dies, and you simply walk away."
      descr = f'**+{gain} points.**'
      imgr = 'https://cdn.discordapp.com/attachments/906615498664452139/942949135135424533/IMG_2544.png'
    elif result == 10:
      gain = -20
      textr = "Emz!\nShe offers you free hair spray and runs while you're gagging and most likely dying."
      descr = f'**-{gain} points**'
      imgr = 'https://cdn.discordapp.com/attachments/906615498664452139/942949140676116500/IMG_2545.png'
    elif result == 11:
      gain = 0
      textr = "Spike!\nHe just stares... You belittle yourself for mistaking an enemy for a cactus."
      descr = f'**+{gain} points (Wait, what was that rustling noise?)**'
      imgr = 'https://cdn.discordapp.com/attachments/906615498664452139/942949142370586726/IMG_2546.png'
    elif result == 12:
      gain = 50
      textr = "Griff!\nHe offers you everything he has. Which is a lot."
      descr = f'**+{gain} points**'
      imgr = 'https://cdn.discordapp.com/attachments/906615498664452139/942951557253718046/IMG_2547.png'
      
    em4 = discord.Embed(title = textr, description = descr)
    em4.set_image(url = imgr)
    await message.channel.send(embed = em4)
    if str(user.id) in users:
        users[str(user.id)]['points'] += gain
    else:
      users[str(user.id)] = {}
      users[str(user.id)]['huntingdoubler'] = 1
      users[str(user.id)]['triviadoubler'] = 1
      users[str(user.id)]['points'] = gain
      users[str(user.id)]['raffleticket'] = 0
      users[str(user.id)]['gtndoubler'] = 1
      users[str(user.id)]['bid'] = 0
    with open('save.json', 'w') as f:
          json.dump(users, f)
  if msg.lower().startswith('$hunt'):
    await hunt()


  async def gtn():
    with open("save.json", 'r') as f:
      users = json.load(f)
    user = message.author
    done = False
    difficulty1 = ''
    numbers = []
    difficulty = ''
    x = 1
    while x < 128:
      numbers.append(x)
      x += 1
    eml = discord.Embed(color = Color.orange(),title = "Welcome to Guess the Number!")
    eml.set_image(url = 'https://cdn.discordapp.com/attachments/906615498664452139/945033116651749476/IMG_2635.gif')
    await message.channel.send(embed = eml)
    await asyncio.sleep(1)
    await message.channel.send("What difficulty level, easy or hard?")
    difficulty = await client.wait_for('message')
    
    while done == False:
      if difficulty.author == user:
        if difficulty.content.lower() in ['easy', 'hard']:
          difficulty1 = difficulty.content.lower()
        else:
          await message.channel.send("Please respond with 'easy' or 'hard'!")
      await message.channel.send("I'm thinking of a number between 1 and 127.")
      number = random.randint(1, 127)
      gain = 0
      if difficulty1 == 'easy':
        turns = 9
        gain = random.randint(30,60)
        turnPoints = 3*turns
      else:
        turns = 7
        gain = random.randint(80, 110)
        turnPoints = 5*turns
      for _ in range(turns):
        answered = False
        while answered == False:
          gues = await client.wait_for('message')
          if gues.author == user:
            guess = gues
            answered = True
            break
        try:
          guessint = int(guess.content)
        except:
          await message.channel.send("Please respond with a number from 1 to 127!")
        if guessint in numbers:
          guess1 = int(guess.content)
          if turns > 0:
            if guess1 == number:
              eml = discord.Embed(color = Color.green(),title = f"You win! The number was {number}.", description = f"+{(gain + turnPoints) * users[str(user.id)]['gtndoubler']} points.")
              eml.set_image(url = 'https://cdn.discordapp.com/attachments/906615498664452139/945039096559054899/IMG_2641.gif')
              await message.channel.send(embed = eml)
              done = True
              if str(user.id) in users:
                  users[str(user.id)]['points'] += (gain + turnPoints) * users[str(user.id)]['gtndoubler']
              else:
                users[str(user.id)] = {}
                users[str(user.id)]['huntingdoubler'] = 1
                users[str(user.id)]['triviadoubler'] = 1
                users[str(user.id)]['points'] = gain
                users[str(user.id)]['raffleticket'] = 0
                users[str(user.id)]['gtndoubler'] = 1
                users[str(user.id)]['bid'] = 0
              done = True
              break
            elif guess1 < number:
              await message.channel.send(f'Too low. You have {turns - 1} guesses remaining.\n')
              turns -=1
              turnPoints -= 4
            else:
              await message.channel.send(f'Too high. You have {turns - 1} guesses remaining.\n')
              turns -=1
              turnPoints -= 4
          if turns == 0:
            eml = discord.Embed(color = Color.red(), title = f"You lose. The number was {number}.", description = f"-{gain} points.")
            eml.set_image(url = 'https://cdn.discordapp.com/attachments/906615498664452139/945037341725179974/IMG_2640.gif')
            await message.channel.send(embed = eml)
            if str(user.id) in users:
              users[str(user.id)]['points'] -= gain
            else:
              users[str(user.id)] = {}
              users[str(user.id)]['huntingdoubler'] = 1
              users[str(user.id)]['triviadoubler'] = 1
              users[str(user.id)]['points'] = 0
              users[str(user.id)]['raffleticket'] = 0
              users[str(user.id)]['gtndoubler'] = 1
              users[str(user.id)]['bid'] = 0
      done = True
      break
      
    with open('save.json', 'w') as f:
          json.dump(users, f)
      
  if msg.lower().startswith('$gtn'):
    await gtn()
    
  if msg.lower().startswith('$play'):
    await message.channel.send('This feature has been renamed to $trivia.')
  if msg.lower().startswith('$sbreset'):
    user = message.author
    with open("save.json", 'r') as f:
          users = json.load(f)
    users[str(user.id)]['points'] = 0
    with open('save.json', 'w') as f:
        json.dump(users, f)
  async def lb():
    with open("save.json", 'r') as f:
      users = json.load(f)
    
    global lb
    usersu = list(users.keys())
    usersa = list(users.values())
    usersp = []
    usersd = {}
    leaderboard = []
    ppl = 0
    for x in usersa:
      usersp.append(x['points'])
    for x in usersp:
      ppl+=1
    for x in range(ppl):
      us = usersp[x]
      usersd[us] = usersu[x]
    current_highest = -1000
    for _ in range(10):
      for x in range(ppl):
        amt = usersp[x]
        if amt > current_highest:
          current_highest = amt
      
      leaderboard.append(current_highest)
      usersp.remove(int(current_highest))
      ppl-=1
      current_highest = -1000
    l1 = (await client.fetch_user(usersd[leaderboard[0]]))
    l2 = (await client.fetch_user(usersd[leaderboard[1]]))
    l3 = (await client.fetch_user(usersd[leaderboard[2]]))
    l4 = (await client.fetch_user(usersd[leaderboard[3]]))
    l5 = (await client.fetch_user(usersd[leaderboard[4]]))
    l6 = (await client.fetch_user(usersd[leaderboard[5]]))
    l7 = (await client.fetch_user(usersd[leaderboard[6]]))
    l8 = (await client.fetch_user(usersd[leaderboard[7]]))
    l9 = (await client.fetch_user(usersd[leaderboard[8]]))
    l10 = (await client.fetch_user(usersd[leaderboard[9]]))
    
    em2 = discord.Embed(title = 'The current StuyBucks leaderboard is:', description = f'**🥇 {l1.name} - {leaderboard[0]}\n🥈 {l2.name} - {leaderboard[1]}\n🥉 {l3.name} - {leaderboard[2]}\n 4. {l4.name} - {leaderboard[3]}\n5. {l5.name} - {leaderboard[4]}\n 6. {l6.name} - {leaderboard[5]}\n7. {l7.name} - {leaderboard[6]}\n 8. {l8.name} - {leaderboard[7]}\n9. {l9.name} - {leaderboard[8]}**\n **10. {l10.name} - {leaderboard[9]}**')
    em2.set_thumbnail(url='https://cdn.discordapp.com/attachments/906615498664452139/962122288038301806/IMG_3209.png')
    await message.channel.send(embed = em2)
    user = message.author
    role = discord.utils.get(user.guild.roles, name = 'Rich')
    
    
    if users[str(user.id)]['points'] == leaderboard[0]:
      await user.add_roles(role)
    else:
      await user.remove_roles(role)
  user = message.author
  if msg.lower().startswith('$lb'):
    await lb()
  async def hangman():
    lives = 5
    game_is_finished = False
    word_list = ['brawl stars', 'mortis', 'penny', 'darryl', 'sandy', 'byron', 'el primo', 'colonel ruffs','brock', 'backyard bowl', 'sneaky fields', 'double swoosh', 'gem fort', 'safe zone', 'hot potato', 'pit stop', 'hideout','shooting star', 'layer cake', 'bot drop', 'parallel plays', 'dueling beetles', 'deep end', 'middle ground', 'skull creek', 'acid lakes', 'pierced', 'jessie', 'dynamike', 'amber', 'cavern churn', 'pinhole punt', 'split', 'crystal arcade', 'colette', 'spike', 'double trouble', 'acid lakes', 'safe zone', 'excel', 'triple dribble', 'ends meet', 'factory rush', 'sprout', 'frank', 'shelly', 'squeak', 'griff', 'jacky']
    chosen_word = random.choice(word_list)
    word_length = len(chosen_word)
    hmt = "Welcome to Brawl Stars Hangman!"
    hmd = '**Guess any letter to begin.**'
    gain = 25
    hmi = 'https://cdn.discordapp.com/attachments/906615498664452139/943266860470792224/45269089-D095-4E1B-AA20-2C6F7121352D.jpg'
    hme = discord.Embed(color = Color.purple(), title = hmt, description = hmd)
    hme.set_image(url = hmi)
    await message.channel.send(embed = hme)
    display = []
    for _ in range(word_length):
      if chosen_word[_] in ["a", "b", "c", "d", "e","f", "g", "h", "i", "j","k", "l", "m", "n", "o","p", "q", "r", "s", "t", "u", "v", "w", "x", "y", "z"]:
        display += '＿'
      else:
        display += 'ㅤ'
    
    while not game_is_finished:
      a = await client.wait_for('message')
      if a.author == user:
        if a.content.lower() in ["a", "b", "c", "d", "e","f", "g", "h", "i", "j","k", "l", "m", "n", "o","p", "q", "r", "s", "t", "u", "v", "w", "x", "y", "z", 'brawl stars', 'mortis', 'penny', 'darryl', 'sandy', 'byron', 'el primo', 'colonel ruffs','brock', 'backyard bowl', 'sneaky fields', 'double swoosh', 'gem fort', 'safe zone', 'hot potato', 'pit stop', 'hideout','shooting star', 'layer cake', 'bot drop', 'parallel plays', 'dueling beetles', 'deep end', 'middle ground', 'skull creek', 'acid lakes', 'pierced', 'jessie', 'dynamike', 'amber', 'cavern churn', 'pinhole punt', 'split', 'crystal arcade','colette', 'spike', 'double trouble', 'acid lakes', 'safe zone', 'excel', 'triple dribble', 'ends meet', 'factory rush', 'sprout', 'frank', 'shelly', 'squeak', 'griff', 'jacky']:
          guess = a.content.lower()
          
      for position in range(word_length):
        letter = chosen_word[position]
        if letter == guess:
          display[position] = letter
          
          

      if guess not in chosen_word:
        lives -= 1
        if lives == 5:
          hmi = 'https://cdn.discordapp.com/attachments/906615498664452139/943266649245642802/4A32EA23-8FC8-484D-A3A0-1783B29C388E.jpg'
        elif lives == 4:
          hmi = 'https://cdn.discordapp.com/attachments/906615498664452139/943266656006860901/E1858DF4-17CB-4CA8-85EE-97CD19539958.jpg'
        elif lives == 3:
          hmi = 'https://cdn.discordapp.com/attachments/906615498664452139/943266660100497478/C2FFB2EC-CAA2-43C3-9F0D-0D3B27A3A9F4.jpg'
        elif lives == 2:
          hmi = 'https://cdn.discordapp.com/attachments/906615498664452139/943266666631024660/F64D9C7F-915F-4F7A-93DB-B2463E583F50.jpg'
        elif lives == 1:
          hmi = 'https://cdn.discordapp.com/attachments/906615498664452139/943266666631024660/F64D9C7F-915F-4F7A-93DB-B2463E583F50.jpg'
        else:
          hmi = 'https://cdn.discordapp.com/attachments/906615498664452139/943266670284267592/E3D4C5B8-9518-4FCD-A167-56EAD93D4BBE.jpg'
        hmt = f"You guessed {guess}, that's not in the word."
        hmd = f"**You have {lives} lives remaining.\n{' '.join(display)}**"
        hme = discord.Embed(color = Color.purple(),title = hmt, description = hmd)
        hme.set_image(url = hmi)
        await message.channel.send(embed = hme)
        if lives == 0:
            game_is_finished = True
            gain = random.randint(90, 120)
            await message.channel.send(f"**You lose. The word was {chosen_word}. -{gain} StuyBucks.**")
            with open("save.json", 'r') as f:
              users = json.load(f)
            if str(user.id) in users:
              users[str(user.id)]['points'] -= gain
            else:
              users[str(user.id)] = {}
              users[str(user.id)]['triviadoubler'] = 1
              users[str(user.id)]['huntingdoubler'] = 1
              users[str(user.id)]['points'] = gain
              users[str(user.id)]['raffleticket'] = 0
              users[str(user.id)]['gtndoubler'] = 1
              users[str(user.id)]['bid'] = 0
            with open('save.json', 'w') as f:
              json.dump(users, f)
      
      else:
        if lives == 5:
          hmi = 'https://cdn.discordapp.com/attachments/906615498664452139/943266649245642802/4A32EA23-8FC8-484D-A3A0-1783B29C388E.jpg'
        elif lives == 4:
          hmi = 'https://cdn.discordapp.com/attachments/906615498664452139/943266656006860901/E1858DF4-17CB-4CA8-85EE-97CD19539958.jpg'
        elif lives == 3:
          hmi = 'https://cdn.discordapp.com/attachments/906615498664452139/943266660100497478/C2FFB2EC-CAA2-43C3-9F0D-0D3B27A3A9F4.jpg'
        elif lives == 2:
          hmi = 'https://cdn.discordapp.com/attachments/906615498664452139/943266666631024660/F64D9C7F-915F-4F7A-93DB-B2463E583F50.jpg'
        elif lives == 1:
          hmi = 'https://cdn.discordapp.com/attachments/906615498664452139/943266666631024660/F64D9C7F-915F-4F7A-93DB-B2463E583F50.jpg'
        else:
          hmi = 'https://cdn.discordapp.com/attachments/906615498664452139/943266670284267592/E3D4C5B8-9518-4FCD-A167-56EAD93D4BBE.jpg'
        hmt = f"You guessed {guess}, that is in the word!"
        hmd = f"**You have {lives} lives remaining\n{' '.join(display)}**"
        hme = discord.Embed(title = hmt, description = hmd)
        hme.set_image(url = hmi)
        await message.channel.send(embed = hme)
    
        
    
      if not "＿" in display or guess == chosen_word:
        game_is_finished = True
        gain = random.randint(90, 120)
        with open("save.json", 'r') as f:
          users = json.load(f)
        ems = discord.Embed(color = Color.green(),title = f"**You win! The word was {chosen_word}. \n+{gain * 2 * users[str(user.id)]['huntingdoubler']} StuyBucks.**")
        await message.channel.send(ems)
        if str(user.id) in users:
          users[str(user.id)]['points'] += gain * users[str(user.id)]['huntingdoubler'] * 2
        else:
          users[str(user.id)] = {}
          users[str(user.id)]['huntingdoubler'] = 1
          users[str(user.id)]['triviadoubler'] = 1
          users[str(user.id)]['points'] = gain * 2
          users[str(user.id)]['raffleticket'] = 0
          users[str(user.id)]['gtndoubler'] = 1
          users[str(user.id)]['bid'] = 0
        with open('save.json', 'w') as f:
          json.dump(users, f)
  numbers = []
  if msg.lower().startswith('$count'):
    count = 0
    while count < 69:
      count +=1
      numbers.append(count)
    x = str(numbers[count - 1])
    x = [str(int) for int in numbers]
    y = ", ".join(x)
    await message.channel.send(y)
    await message.channel.send("https://cdn.discordapp.com/attachments/906615498664452139/944074848076959844/IMG_2596.gif")
    
  if msg.lower().startswith('$yt'):
    await message.channel.send('https://www.youtube.com/channel/UCLmWSnAyBq6XfJy2L1sggqg')

  if msg.lower().startswith('$hm'):
    await hangman()

  if msg.lower().startswith('$beg'):
    with open("save.json", 'r') as f:
      users = json.load(f)
      em = discord.Embed(title = f"You just gained 1 StuyBuck.")
      em.set_thumbnail(url = "https://cdn.discordapp.com/attachments/906615498664452139/945044772677095434/unknown.png")
      await message.channel.send(embed = em)
        
      if str(user.id) in users:
          users[str(user.id)]['points'] += 1
      else:
          users[str(user.id)] = {}
          users[str(user.id)]['huntingdoubler'] = 1
          users[str(user.id)]['triviadoubler'] = 1
          users[str(user.id)]['points'] = 1
          users[str(user.id)]['raffleticket'] = 0
          users[str(user.id)]['gtndoubler'] = 1
          users[str(user.id)]['bid'] = 0
      with open('save.json', 'w') as f:
          json.dump(users, f)
  if msg.lower().startswith('$donate'):
    with open('save.json', 'r') as f:
      users = json.load(f)
    donator = str(message.author.id)
    msg2 = msg.lower().split('$donate',1)[1]#[1:2]
    donation1 = msg2.split(' ',1)[1]
    donation = int(donation1.split(" ")[0])
    receiver1 = msg2.split('to ',1)[1]
    receiver = str(receiver1[3:21])
    print(donation)
    print(receiver)
    if users[donator]['points'] >= donation and donation > 0:
      users[donator]['points'] -= donation
      users[receiver]['points'] += donation
      donationem = discord.Embed(color = Color.green(), title = f"Donated {donation} Stuybucks to {(await client.fetch_user(receiver)).name}!", description = "They thank you for your generosity!")
      donationem.set_image(url = 'https://cdn.discordapp.com/attachments/906615498664452139/946866830419578940/IMG_2709.jpg')
      await message.channel.send(embed = donationem)
    elif donation < 0:
      await message.channel.send('You cheeky bastard...')
    else:
      await message.channel.send("Mr. Beast wannabe...")
    with open('save.json', 'w') as f:
      json.dump(users, f)  


  if msg.lower().startswith('$alter'):
    with open('save.json', 'r') as f:
      users = json.load(f)
    donator = str(message.author.id)
    msg2 = msg.lower().split('$alter',1)[1]#[1:2]
    donation1 = msg2.split(' ',1)[1]
    donation = int(donation1.split(" ")[0])
    receiver1 = msg2.split('for ',1)[1]
    receiver = str(receiver1[3:21])
    print(donation)
    print(receiver)
    if donator == "294184126343282690" or donator == "609145586012127239":
      users[receiver]['points'] += donation
      if donation > 0:
        donationem = discord.Embed(color = Color.green(), title = f"Gave {donation} Stuybucks to {(await client.fetch_user(receiver)).name}.")
      else:
        donationem = discord.Embed(color = Color.red(), title = f"Took away {donation} Stuybucks from {(await client.fetch_user(receiver)).name}.")
      await message.channel.send(embed = donationem)
    else:
      await message.channel.send('You do not have permission to use that command!')
    with open('save.json', 'w') as f:
        json.dump(users, f)  
  
  async def buy(item, author):
    user = author
    with open("save.json", 'r') as f:
      users = json.load(f)
    if item.lower() == "trivia deluxe":
      if users[str(user.id)]['points'] < 5000:
        await message.channel.send('Sorry, you need 5000 StuyBucks to purchase **Trivia Deluxe**.')
      elif users[str(user.id)]['triviadoubler'] == 2:
        await message.channel.send('You already have that item.')
      else:
        users[str(user.id)]['triviadoubler'] = 2
        emt = discord.Embed(title = "Purchased **Trivia Deluxe** for 5000 StuyBucks.", description = "Nice doing business with you!")
        emt.set_image(url = "https://cdn.discordapp.com/attachments/906615498664452139/944665688272932874/IMG_2608.jpg")
        await message.channel.send(embed = emt)
        users[str(user.id)]['points'] -= 5000
    elif item.lower() == "hangman deluxe":
        if users[str(user.id)]['points'] < 5000:
          await message.channel.send('Sorry, you need 5000 StuyBucks to purchase **Hangman Deluxe**.')
        elif users[str(user.id)]['huntingdoubler'] == 2:
          await message.channel.send('You already have that item.')
        else:
          users[str(user.id)]['huntingdoubler'] = 2
          emt = discord.Embed(title = "Purchased **Hangman Deluxe** for 5000 StuyBucks.", description = "Nice doing business with you!")
          emt.set_image(url = "https://cdn.discordapp.com/attachments/906615498664452139/944665688272932874/IMG_2608.jpg")
          await message.channel.send(embed = emt)
          users[str(user.id)]['points'] -= 5000
          
    if item.lower() == "trivia deluxe plus":
      if users[str(user.id)]['points'] < 10000:
        await message.channel.send('Sorry, you need 10,000 StuyBucks to purchase **Trivia Deluxe Plus**.')
      elif users[str(user.id)]['triviadoubler'] == 3:
        await message.channel.send('You already have that item.')
      else:
        users[str(user.id)]['triviadoubler'] = 3
        emt = discord.Embed(title = "Purchased **Trivia Deluxe Plus** for 10,000 StuyBucks.", description = "Nice doing business with you!")
        emt.set_image(url = "https://cdn.discordapp.com/attachments/906615498664452139/944665688272932874/IMG_2608.jpg")
        await message.channel.send(embed = emt)
        users[str(user.id)]['points'] -= 10000
    elif item.lower() == "hangman deluxe plus":
        if users[str(user.id)]['points'] < 10000:
          await message.channel.send('Sorry, you need 10,000 StuyBucks to purchase **Hangman Deluxe Plus**.')
        elif users[str(user.id)]['huntingdoubler'] == 3:
          await message.channel.send('You already have that item.')
        elif users[str(user.id)]['huntingdoubler'] == 2:
          users[str(user.id)]['huntingdoubler'] = 3
          users[str(user.id)]['points'] -= 5000
        else:
          users[str(user.id)]['huntingdoubler'] = 3
          emt = discord.Embed(title = "Purchased **Hangman Deluxe Plus** for 10,000 StuyBucks.", description = "Nice doing business with you!")
          emt.set_image(url = "https://cdn.discordapp.com/attachments/906615498664452139/944665688272932874/IMG_2608.jpg")
          await message.channel.send(embed = emt)
          users[str(user.id)]['points'] -= 10000

    
    elif item.lower() == "rick roll":
      if users[str(user.id)]['points'] < 69:
        await message.channel.send('Sorry, you need 69 StuyBucks to purchase **Rick Roll**.')
      else:
        rick_image = "https://cdn.discordapp.com/attachments/906615498664452139/944664896925212773/IMG_2606.gif"
        em01 = discord.Embed(title = "Never gonna give you up")
        em01.set_image(url = rick_image)
        em02 = discord.Embed(title = "Never gonna let you down")
        em02.set_image(url = rick_image)
        em03 = discord.Embed(title = "Never gonna run around and desert you")
        em03.set_image(url = rick_image)
        em04 = discord.Embed(title = "Never gonna make you cry")
        em04.set_image(url = rick_image)
        em05 = discord.Embed(title = "Never gonna say goodbye")
        em05.set_image(url = rick_image)
        em06 = discord.Embed(title = "Never gonna tell a lie and hurt you...")
        em06.set_image(url = rick_image)
        await message.channel.send(embed = em01)
        await asyncio.sleep(1)
        await message.channel.send(embed = em02)
        await asyncio.sleep(1)
        await message.channel.send(embed = em03)
        await asyncio.sleep(2)
        await message.channel.send(embed = em04)
        await asyncio.sleep(1)
        await message.channel.send(embed = em05)
        await asyncio.sleep(1)
        await message.channel.send(embed = em06)
        emr = discord.Embed(title = "Purchased **Rick Roll** for 69 StuyBucks.", description = "Nice doing business with you!")
        emr.set_image(url = "https://cdn.discordapp.com/attachments/906615498664452139/944665688272932874/IMG_2608.jpg")
        await asyncio.sleep(2)
        await message.channel.send(embed = emr)
        users[str(user.id)]['points'] -= 69
    elif item.lower() == "server picture choice":
      if users[str(user.id)]['points'] < 10000:
        await message.channel.send('Sorry, you need 10,000 StuyBucks to purchase **Server Picture Choice**.')
      else:
        user = author
        receipt = discord.Embed(title = f'Receipt for @{await client.fetch_user(str(user.id))} for Server Picture Choice.', description = f'Please contact @{await client.fetch_user(294184126343282690)} for your picture choice. Please provide this receipt as proof of transaction.')
        receipt.set_image(url = 'https://cdn.discordapp.com/attachments/906615498664452139/946171240194916422/IMG_2671.webp')
        await message.channel.send(embed = receipt)
        users[str(user.id)]['points'] -= 10000
    elif item.lower() == "raffle ticket":
      if (msg.lower().split('buy raffle ticket ',1)[1]) == "max":
        if users[str(user.id)]['raffleticket'] + math.floor(users[str(user.id)]['points']/50) > 50:
          amount = 50 - users[str(user.id)]['raffleticket']
        else:
          amount = math.floor(users[str(user.id)]['points']/50)
      else:
        amount = int(msg.lower().split('buy raffle ticket ',1)[1])

      if users[str(user.id)]['points'] < 50 * amount:
        await message.channel.send(f'Sorry, you need {50*amount} StuyBucks to purchase **Raffle Ticket**.')
      elif users[str(user.id)]['raffleticket'] + amount < 0:
        await message.channel.send("**YOU THINK YOU'RE SO SMART DON'T YOU**")
        users[str(user.id)]['points'] += 50 * users[str(user.id)]['raffleticket']
        users[str(user.id)]['raffleticket'] = 0
        role = discord.utils.get(user.guild.roles, name = 'Scammer')
        await user.add_roles(role)
      elif users[str(user.id)]['raffleticket'] + amount > 50:
        await message.channel.send(f"Sorry, 50 is the maximum amount of tickets. You can buy up to {50 - users[str(user.id)]['raffleticket']} more tickets.")
      else:
        users[str(user.id)]['raffleticket'] += amount
        emt = discord.Embed(title = f"Purchased {amount} **Raffle Ticket(s)** for {amount*50} StuyBucks.", description = "Nice doing business with you!")
        emt.set_image(url = "https://cdn.discordapp.com/attachments/906615498664452139/944665688272932874/IMG_2608.jpg")
        await message.channel.send(embed = emt)
        users[str(user.id)]['points'] -= 50 * amount
    elif item.lower() == 'the almighty role':
      if users[str(user.id)]['points'] < 100000:
        await message.channel.send(f'Sorry, you need 100,000 StuyBucks to purchase **The Almighty Role**.')
      else:
        role = discord.utils.get(user.guild.roles, name = '𝓣𝓱𝓮 𝓐𝓵𝓶𝓲𝓰𝓱𝓽𝔂')
        await user.add_roles(role)
        users[str(user.id)]['points'] -= 100000
    elif item.lower() == 'gtn deluxe':
      if users[str(user.id)]['points'] < 5000:
          await message.channel.send('Sorry, you need 5000 StuyBucks to purchase **GTN Deluxe**.')
      elif users[str(user.id)]['gtndoubler'] == 2:
        await message.channel.send('You already have that item.')
      else:
        users[str(user.id)]['gtndoubler'] = 2
        emt = discord.Embed(title = "Purchased **GTN Deluxe** for 5000 StuyBucks.", description = "Nice doing business with you!")
        emt.set_image(url = "https://cdn.discordapp.com/attachments/906615498664452139/944665688272932874/IMG_2608.jpg")
        await message.channel.send(embed = emt)
        users[str(user.id)]['points'] -= 5000
    elif item.lower() == 'nitro classic':
      if users[str(user.id)]['points'] < 1000000:
        await message.channel.send("Look, we can't just be handing out money here...")
      else:
        emt = discord.Embed(title = "THERE'S NO WAY SOMEONE ACTUALLY GOT IT OMG AFTER THIS TOUCH GRASS PLEASE!!!", description = "HOW MUCH TIME DO YOU HAVE???")
        emt.set_image(url = "https://cdn.discordapp.com/attachments/906615498664452139/945109282704220240/IMG_2643.jpg")
        await message.channel.send(embed = emt)
        users[str(user.id)]['points'] -= 1000000
        await asyncio.sleep(5)
        emt = discord.Embed(title = "You, hopefully, in a few minutes:", description = "Really, please get help.")
        emt.set_image(url = "https://cdn.discordapp.com/attachments/906615498664452139/945110467079188571/IMG_2644.jpg")
        await message.channel.send(embed = emt)
    elif item.lower() == 'gtn deluxe plus':
      if users[str(user.id)]['points'] < 10000:
          await message.channel.send('Sorry, you need 10,000 StuyBucks to purchase **GTN Deluxe Plus**.')
      elif users[str(user.id)]['gtndoubler'] == 3:
        await message.channel.send('You already have that item.')
      else:
        users[str(user.id)]['gtndoubler'] = 3
        emt = discord.Embed(title = "Purchased **GTN Deluxe Plus** for 10,000 StuyBucks.", description = "Nice doing business with you!")
        emt.set_image(url = "https://cdn.discordapp.com/attachments/906615498664452139/944665688272932874/IMG_2608.jpg")
        await message.channel.send(embed = emt)
        users[str(user.id)]['points'] -= 10000
    else: 
      #await message.channel.send("That's not an existing item!")
      pass
    with open('save.json', 'w') as f:
        json.dump(users, f)

  if msg.lower().startswith('$buy '):
    if msg.lower().startswith('$buy raffle ticket'):
      await message.channel.send('Raffle tickets are not being sold right now!')
    elif msg.lower().startswith('$buy lottery ticket'):
      with open("save.json", 'r') as f:
        users = json.load(f)
      user = message.author
      if users[str(user.id)]['points'] > 250:
        users[str(user.id)]['points'] -= 250
        with open("save.json", 'w') as f:
          users = json.dump(users, f)
        await lottery()
      else:
        await message.channel.send('Sorry, you need 250 StuyBucks to purchase **Lottery Ticket.**')
    else:
      item = msg.split('buy ', 1)[1]
      author = message.author
      await buy(item, author)
    
    
  if msg.startswith('$refund'):
    await message.channel.send (f'Please contact @{await client.fetch_user(294184126343282690)} to process your refund.')
  async def endraffle():
    with open("save.json", 'r') as f:
      users = json.load(f)
    raffled = {}
    amtp = 0
    buyers = list(users.keys())
    values = list((users.values()))
    tickets = []
    ticketbox = []
    ticketboxes = {}
    sum = 0
    for user in values:
      tickets.append(user['raffleticket'])
    for user in users:
      amtp += 1
    for user in range(amtp):
      raffled[buyers[user]] = tickets[user]
    ticketamts = list(raffled.values())
    amttickets = 0
    for i in range(0, len(ticketamts)):
      amttickets += ticketamts[i]
    i = 0
    while i < amttickets:
      i += 1
      ticketbox.append(i)
    for buyer in buyers:
      ticketboxes[buyer] = []
    peopleleft = len(buyers)
    while peopleleft > 0:
      for buyer in buyers:
        for x in range(raffled[buyer]):
          ticketboxes[buyer].append(ticketbox.pop())
        peopleleft -= 1
    winningnum = random.randint(1, amttickets)
    winner = ""
    award = random.randint(1, 500)
    if award > 1 and award < 250:
      award = "Hangman Deluxe Plus"
    else:
      award = "Guess the Number Deluxe Plus"

    for buyer in buyers:
      if winningnum in ticketboxes[buyer]:
        winner = str(buyer)
        await message.channel.send("Thank you to everyone who entered the raffle!")
        await asyncio.sleep(3)
        await message.channel.send("\n\nOn this momentous occasion, it is a pleasure to have you all here celebrating with us.")
        await asyncio.sleep(3)
        await message.channel.send("\n\nThis raffle's randomized reward is...")
        await asyncio.sleep(3)
        await message.channel.send(f"\n\n**{award}!**")
        await asyncio.sleep(4)
        await message.channel.send("\n\nBut without further ado...")
        await asyncio.sleep(4)
        await message.channel.send(f"**\nThe winner of the {award} is...**")
        await asyncio.sleep(5)
        emw = discord.Embed(title = f"{await client.fetch_user(winner)}!!! Congratulations! 🎉🎉🎉")
        
        winnera = await client.fetch_user(winner)
        emw.set_image(url = (winnera.avatar_url))
        await message.channel.send(embed = emw)
    with open('save.json', 'w') as f:
      json.dump(users, f)
  
  async def ticketlb():
    with open("save.json", 'r') as f:
      users = json.load(f)
    usersu = list(users.keys())
    usersa = list(users.values())
    usersp = []
    usersd = {}
    ticketleaderboard = []
    ppl = 0
    for x in usersa:
      usersp.append(x['raffleticket'])
    for x in usersp:
      ppl+=1
    for x in range(ppl):
      id = usersu.pop()
      ti = usersp.pop()
      usersd[id] = ti
    current_highest = 0
    print('usersu', usersu)
    print('usersp', usersp)
    print('usersd', usersd)
    for x in usersa:
      usersp.append(x['raffleticket'])
    for _ in range(5):
      for x in range(ppl):
        amt = usersp[x]
        if amt > current_highest:
          current_highest = amt
        elif amt == current_highest:
          pass
          
      ticketleaderboard.append(current_highest)
      
      usersp.remove(current_highest)
      ppl-=1
      current_highest = 0

    usersd2 = dict(sorted(usersd.items(), key = operator.itemgetter(1), reverse=False))
    
    tl1 = (await client.fetch_user((usersd2.popitem())[0]))
    tl2 = (await client.fetch_user((usersd2.popitem())[0]))
    tl3 = (await client.fetch_user((usersd2.popitem())[0]))
    tl4 = (await client.fetch_user((usersd2.popitem())[0]))
    tl5 = (await client.fetch_user((usersd2.popitem())[0]))

    em2 = discord.Embed(title = 'The raffle ends **Tuesday 4PM!**\nThe current Tickets leaderboard is:', description = f'**🥇 {tl1.name} - {ticketleaderboard[0]}\n🥈 {tl2.name} - {ticketleaderboard[1]}\n🥉 {tl3.name} - {ticketleaderboard[2]}\n4. {tl4.name} - {ticketleaderboard[3]}\n5. {tl5.name} - {ticketleaderboard[4]}**')
    em2.set_thumbnail(url='https://cdn.discordapp.com/attachments/906615498664452139/944991040841076776/IMG_2631.png')
    await message.channel.send(embed = em2)

  if msg.lower().startswith('$ticketlb'):
    await ticketlb()

  if msg.lower().startswith('$endraffle'):
    await endraffle()
  
  if msg.lower().startswith('$tickets'):
    user = message.author
    with open("save.json", 'r') as f:
      users = json.load(f)
    ticketuser = users[str(user.id)]['raffleticket']
    em = discord.Embed(title = f"{message.author.name}'s Tickets:\n{ticketuser}")
  
    em.set_thumbnail(url = message.author.avatar_url)
    await message.channel.send(embed = em)

  if msg.startswith('$change'):
    await message.channel.send('The Tickets cap has been **increased to 50.**')
  if msg.lower().startswith('$shop'):
    ems = discord.Embed(color = Color.dark_blue(),title = "Welcome to the StuyBucks shop! Use $buy to purchase.", description = "**Nitro Classic - 1,000,000 SB**\nOne month too many of Nitro Classic!\n\n**The Almighty Role - 100,000 SB**\nAn exclusive role in script. Color of your choice. The biggest flex.\n\n**Server Picture Choice - 10,000 SB**\nChoose the server picture for a week.\n\n**Trivia Deluxe Plus - 10,000 SB**\nTriples the StuyBucks you gain from a Trivia win.\n\n**Hangman Deluxe Plus - 10,000 SB**\nTriples the amount of StuyBucks you gain for a Hangman win.\n\n**GTN Deluxe Plus - 10,000 SB**\nTriples the amount of StuyBucks you gain for a Guess the Number win.\n\n**Trivia Deluxe - 5,000 SB**\nDoubles the StuyBucks you gain from a Trivia win.\n\n**Hangman Deluxe - 5,000 SB**\nDoubles the amount of StuyBucks you gain for a hangman win.\n\n**GTN Deluxe - 5,000 SB**\nDoubles the amount of StuyBucks you gain for a Guess the Number win.\n\n**Lottery Ticket - 250 SB**\nPurchases a lottery ticket (only valid for the day that it's purchased).\n\n**Rick Roll - 69 SB**\nNever gonna give you up...")
    ems.set_thumbnail(url = 'https://cdn.discordapp.com/attachments/906615498664452139/944664791643983932/IMG_2605.gif')
    await message.channel.send(embed = ems)
  
  async def auction(bid):
    global highest_bidder
    with open('save.json', 'r') as f:
      users = json.load(f)
    highest_bid = 0
    bidders = {}
    for bidder in users:
      bidders[users[bidder]['bid']] = bidder
    user_list = list(users.keys())
    for user in user_list:
      if users[user]['bid'] > 0:
        highest_bid = users[user]['bid']
    highest_bidder = bidders[highest_bid]
    user = message.author
    if users[str(user.id)]['points'] >= bid and bid > highest_bid and bid - highest_bid >= 100:
      if str(user.id) in users:
        users[str(user.id)]['points'] += users[str(user.id)]['bid']
        users[str(user.id)]['points'] -= bid
        users[str(user.id)]['bid'] = bid
      else:
        users[str(user.id)] = {}
        users[str(user.id)]['bid'] = bid
      users[highest_bidder]['points'] += users[highest_bidder]['bid']
      users[highest_bidder]['bid'] = 0
      with open('save.json', 'w') as f:
        json.dump(users, f)
      auctionem = discord.Embed(color = Color.dark_orange(), title = f"**{message.author.name}** has raised the bid to **{bid}** StuyBucks!", description = "Use **$bid** if you'd like to raise the bid yourself!")
      auctionem.set_image(url = 'https://cdn.discordapp.com/attachments/906615498664452139/946220309168668682/80394B56-80D7-4639-A1B5-B516A023B7D3.jpg')
      auctionchannel = client.get_channel(946232421920153690)
      await auctionchannel.send(embed = auctionem)
    elif users[str(user.id)]['points'] < bid:
      await message.channel.send(f"Sorry, you need **{bid - users[str(user.id)]['points']}** more StuyBucks to bid that much!")
    elif bid == -1:
      pass
    else:
      await message.channel.send(f"Sorry, your bid must be **at least 100** StuyBucks greater than the current bid. The current bid is **{highest_bid}** StuyBucks.")
      
  if msg.lower().startswith('$bid'):
    bid = int(msg.split('$bid ',1)[1])
    await auction(bid)

  if msg.lower().startswith('$endbid'):
    await auction(-1)
    await message.delete()
    endem = discord.Embed(color = Color.dark_orange(),title = f"Time's up on the auction!\nThe highest bidder was **{(await client.fetch_user(highest_bidder)).name}!**", description = "Congratulations on winning the **Gift Card!!**")
    bidder_a = await client.fetch_user(highest_bidder)
    endem.set_image(url = (bidder_a.avatar_url))
    await message.channel.send(embed = endem)

  if msg.lower().startswith('$raffleupdate'):
    await message.delete()
    updateem = discord.Embed(title = "NOTICE: We've decided to cut the raffles short due to their unrewarding, RNG-dependent nature. This final raffle will now end at **11:59PM today.**", description = "**The raffle system will be replaced by an auctioning system, in which one auction with a better prize will be held over the course of several days. This auction will begin at the same time that today's raffle ends; more info TBA.**")
    updateem.set_image(url = 'https://cdn.discordapp.com/attachments/906615498664452139/946217400972488764/IMG_2679.jpg')
    await message.channel.send(embed = updateem)
  if msg.lower().startswith('$announceauction'):
    await message.delete()
    anauc = discord.Embed(title = "@everyone We're happy to announce an auction for a free $10 iTunes Gift Card, hosted by Theo and Tejas!", description = "Anyone can bid using this server's virtual currency, StuyBucks, which are obtained from playing the StuyBS Bot's minigames. Type **$bid** to enter a bid. For more info on bot commands and minigames, type **$help**.\n\nThe auction will be held from **now** to **Wednesday, 4PM.** The starting bid will be **500** StuyBucks. Don't worry, if someone places a bid that is higher than yours, then you will be compensated for the StuyBucks you'd spent on your bid. **If you win but don't use iTunes, you will receieve Nitro instead.**\n\nFinally, in order to promote the club, inviting a friend to the server grants you **1,000** StuyBucks (alt accounts will not count)!")
    anauc.set_image(url = 'https://cdn.discordapp.com/attachments/906615498664452139/946220309168668682/80394B56-80D7-4639-A1B5-B516A023B7D3.jpg')
    await message.channel.send(embed = anauc)
      
  if msg == '$endlottery':
    user = message.author
    if user.id == 294184126343282690:
      lotem = discord.Embed(color = Color.gold(), title = f"The winning lottery number for **{datetime.date.today()}** is... \n\n**{random.randint(1, 999)}!**", description = "If you bought a ticket today with this number, please dm **@bien#8887** with a screenshot of your ticket to claim your lottery earnings!!")
      lotem.set_image(url = 'https://cdn.discordapp.com/attachments/906615498664452139/946525910776037396/IMG_2698.jpg')
      await message.delete()
      await message.channel.send(embed = lotem)
      await resetlottery()
    else:
      await message.channel.send('You do not have permission to do that!')

  async def wordle():
    #words = open("wordlist.txt", "r")
    global validwords
    with open("save.json", 'r') as f:
      users = json.load(f)
    validwords = open("validwords.txt", "r").read().split("\n")
    word_list = open("wordlist.txt", "r").read().split("\n")
    chosen_word = word_list[random.randint(0, len(word_list) - 1)]
    user = message.author
    embed = discord.Embed(title = "StuyBS presents to you: Brawl Stars Wordle!", description = "Guess any word to begin!")
    embed.set_image(url = 'https://cdn.discordapp.com/attachments/947292794345652225/961836366243704872/60b65fc8668685c9237a3c67_brawlstars3.jpeg')
    await message.channel.send(embed = embed)
    finished = False
    answered = False
    turns = 6
    green = '🟩'
    yellow = '🟨'
    grey = '⬜'
    black = ':white_square_button:'
    corrects = ''
    guesses = []
    squares = ['⬛','⬛','⬛','⬛','⬛']
    squares2 = [':white_square_button:',':white_square_button:',':white_square_button:',':white_square_button:',':white_square_button:']
    letters = {}
    repeats = {}
    convert = {'A' :'🇦', 'B':'🇧', 'C':'🇨', 'D':'🇩', 'E': '🇪', 'F':'🇫', 'G':'🇬', 'H':'🇭', 'I':'🇮', 'J':'🇯', 'K':'🇰', 'L':'🇱', 'M':'🇲', 'N':'🇳', 'O':'🇴', 'P':'🇵', 'Q':'🇶', 'R':'🇷', 'S':'🇸', 'T':'🇹', 'U':'🇺','V':'🇻',  'W':'🇼', 'X':'🇽', 'Y':'🇾', 'Z':'🇿'}
    for letter in convert:
      letters[letter.lower()] = grey
    while finished == False:
      answered = False
      while answered == False:
        input1 = (await client.wait_for('message'))
        input = input1.content
        if input.lower() in validwords and len(input) == 5 and input1.author == user:
          guess = input.lower()
          guesss = input.upper()
          answered = True
          conversion = []
          for letter in guesss:
            conversion.append(convert[letter])
          break
      guesslist = []
      for x in guess:
        guesslist.append(x)
      chosenlist = []
      correct = [grey,grey,grey,grey,grey]
      for x in chosen_word:
        chosenlist.append(x)
      let = 0
      for letter in guesslist:
        repeats[letter] = 0
      for letter in guesslist:
        if letter in chosenlist and guesslist[let] == chosenlist[let]:
          correct[let] = green
          if letters[letter] != green:
            letters[letter] = green
          repeats[letter] += 1
        let += 1
      let = 0
      for letter in guesslist:
        if letter in chosenlist and guesslist[let] != chosenlist[let]:
          if repeats[letter] >= chosenlist.count(letter):
            correct[let] = grey
            if letter not in chosenlist:
              letters[letter] = black
          else:
            correct[let] = yellow
            if letters[letter] != green:
              letters[letter] = yellow
            repeats[letter] += 1
        elif letter not in chosenlist:
          correct[let] = grey
          letters[letter] = black
        let += 1
      guesses.append((f"\n{' '.join(conversion)}\n{' '.join(correct)}"))
      guessstring = ''
      for x in range(len(guesses)):
        guessstring += (f"{guesses[x]}")
      for x in range(turns - 1):
        guessstring += f"\n{' '.join(squares)}"
        guessstring += f"\n{' '.join(squares2)}"
      lettersOrg = []
      lettersOrg.append(" ")
      lettersOrg.append(letters['q'])
      lettersOrg.append(letters['w'])
      lettersOrg.append(letters['e'])
      lettersOrg.append(letters['r'])
      lettersOrg.append(letters['t'])
      lettersOrg.append(letters['y'])
      lettersOrg.append(letters['u'])
      lettersOrg.append(letters['i'])
      lettersOrg.append(letters['o'])
      lettersOrg.append(letters['p'])
      lettersOrg.append('\n')
      lettersOrg.append('\t')
      lettersOrg.append(letters['a'])
      lettersOrg.append(letters['s'])
      lettersOrg.append(letters['d'])
      lettersOrg.append(letters['f'])
      lettersOrg.append(letters['g'])
      lettersOrg.append(letters['h'])
      lettersOrg.append(letters['j'])
      lettersOrg.append(letters['k'])
      lettersOrg.append(letters['l'])
      lettersOrg.append('\n')
      lettersOrg.append('\t')
      lettersOrg.append('\t')
      lettersOrg.append(letters['z'])
      lettersOrg.append(letters['x'])
      lettersOrg.append(letters['c'])
      lettersOrg.append(letters['v'])
      lettersOrg.append(letters['b'])
      lettersOrg.append(letters['n'])
      lettersOrg.append(letters['m'])
      
      await message.channel.send(f"{guessstring}\n\n\n{' '.join(lettersOrg)}")
      corrects += (f"{' '.join(correct)}\n\n")
      correctamt = 0
      for x in range(len(correct)):
        if correct[x] == green:
          correctamt += 1
      
      if correctamt == 5:
        users[str(user.id)]['streak'] += 1
        if users[str(user.id)]['streak'] > 0:
          gain = random.randint(90, 120) * users[str(user.id)]['streak']
        else:
          gain = random.randint(90, 120)
        users[str(user.id)]['wins'] += 1
        embed = discord.Embed(color = Color.green(), title = f"{chosen_word.upper()} was the word, you win!\n\nWins: **{users[str(user.id)]['wins']}**\nStreak: **{users[str(user.id)]['streak']}**\n\n**+{gain} Stuybucks.**", description = f"{corrects}")
        await message.channel.send(embed = embed)
        users[str(user.id)]['points'] += gain
        #users[str(user.id)]['wordle'] = 1
        finished = True
        with open("save.json", 'w') as f:
          users = json.dump(users, f)
        break
      else:
        turns-=1
      if turns <= 0:
        users[str(user.id)]['streak'] = 0
        gain = random.randint(90, 120)
        embed = discord.Embed(color = Color.magenta(), title = f"You lose. The word was {chosen_word.upper()}.\n\nWins: **{users[str(user.id)]['wins']}**\nStreak: **{users[str(user.id)]['streak']}**\n-{gain} Stuybucks.", description = f"{corrects}")
        await message.channel.send(embed = embed)
        users[str(user.id)]['points'] -= gain
        users[str(user.id)]['wordle'] = 1
        with open("save.json", 'w') as f:
          users = json.dump(users, f)
        
        break
        finished = True
      else:
        finished = False
        pass      

  if msg == '$wordle':
    with open("save.json", 'r') as f:
      users = json.load(f)
    user = message.author
    #if users[str(user.id)]['wordle'] == 0:
    await wordle()
    #else:
    #await message.channel.send("You've already played today's Wordle!")

  if msg.startswith('$setwordle'):
    with open("save.json", 'r') as f:
      users = json.load(f)
    global wordoftheday
    wordoftheday = int(msg.split('$setwordle ',1)[1])
    for user in users:
      users[user]['wordle'] = 0
    with open("save.json", 'w') as f:
          users = json.dump(users, f)
    channel = client.get_channel(946997607903936512)
    embed = discord.Embed(title = 'The new Wordle word is out now!', description = 'Type **$wordle** to play!')
    embed.set_image(url = 'https://cdn.discordapp.com/attachments/947292794345652225/948802807069311006/IMG_2807.jpg')
    await channel.send(embed = embed)
  if msg == '$resetwordle':
    
    wordoftheday = 0
  if msg == '$update':
    await message.delete()
    embed = discord.Embed(title = "**INTRODUCING STUYBS BOT V2.0**", description = "**Updates: **\n\n - You can now **VIEW IN-GAME STATS!!** First register your profile with **$register**, and check out the other commands with **$help**.\n\n - **TROPHY LEADERBOARD!!** Star List couldn't get it right, so we did.\n\n - **STUYBS SIMULATOR!!** Purchase gems, open boxes, and expand your Brawler collection! **$help** for more details.\n\n- **$wordle** is now a regular minigame for SB, with **unlimited words and plays!** The higher your answer streak, the more SB you'll earn.\n\n** - Raffles are back!** For **FREE NITRO**; more to be announced later.\n\n**Extras: **\n\n - Improved Wordle functionality.\n - Stuybucks leaderboard now holds 10 players.\n - For Edwin: Added scheduled Club League messages.\n - Some UI changes.")
    embed.set_footer(text = "As always, be sure to check $help for all of the commands!")
    embed.set_image(url = 'https://cdn.discordapp.com/attachments/947292794345652225/961836366243704872/60b65fc8668685c9237a3c67_brawlstars3.jpeg')
    await message.channel.send(embed = embed)

  
#my_secret = os.environ['.env']
import requests
import os

import requests
import os



client.run(os.environ["DISCORD_TOKEN"])

#res = requests.get("http://us-east-static-08.quotaguard.com/", "http://lbzz6x1r4y1xf:yujtw4nnp7bs38xpzmw9lk0atw@us-east-static-08.quotaguard.com:9293")
#keep_alive()
#client.run(my_secret)
