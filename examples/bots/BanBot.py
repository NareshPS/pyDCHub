import os
from time import time, strftime, localtime
import DCHub

class BanBot(DCHub.DCHubBot):
    '''Bot allowing ops to ban users for configurable amounts of time
       
    This bot supports banning by IP and banning by nick.  To submit a ban, you
    must be an op.  Too ban a specific IP, send the bot a private message with
    the IP and an amount of time:
    
        12.34.56. 10m
        
    That will ban the 12.34.56 subnet for 10 minutes.  By default, the time is 
    in seconds. If the time ends in m, h, d, w, or y, it will make the time for
    minutes, hours, days, weeks, or years, respectively.
    
    To ban a nick, preface the user's nick with %:
    
        %UserToBan 1d
        
    Bans UserToBan for 1 day.  To ban the user's IP, preface the user's nick
    with <>:
    
        <>UserToBan 3w
        
    Bans UserToBan's IP for 3 weeks.  Note that in general you are going to
    want to ban by IP, as the user can change their nick easily (assuming you 
    aren't running PrivateDCHub).
    
    To get a list of the current bans:
    
        !list
        
    To clear all bans:
    
        !clear
        
    There are user commands that make banning easier in the 
    examples/usercommands file.
    
    Note that this code may block when reading or writing the ban file on disk.
    If you don't like this, use ThreadedDCHub and use hub.addtask for loadbans
    and writebans.
    '''
    
    def __init__(self, hub, nick = 'BanBot'):
        DCHub.DCHubBot.__init__(self, hub, nick)
        self.banfile = 'bans'
        self.execafter['checkValidateNick'] = self.checkValidateNick
        self.execafter['adduser'] = self.checkipban
        self.timechars = {'s': 1, 'm':60, 'h':60*60, 'd':60*60*24, 'w':60*60*24*7, 
            'y':60*60*24*365}
        for char in self.timechars.keys():
            self.timechars[char.upper()] = self.timechars[char]
        
    def checkipban(self, returnobj, user):
        '''Remove as soon as they are added, if they have been anned'''
        for ip in self.hub.bans:
            if user.ip.startswith(ip):
                if self.hub.bans[ip] > time():
                    self.hub.log.log(self.hub.loglevels['useradderror'], '%s is banned, disconnecting them' % user.idstring)
                    self.hub.removeuser(user)
                else:
                    self.removeban(checknick)
        return returnobj
        
    def checkValidateNick(self, returnobj, user, nick, *args):
        '''Give an invalid nick message if the nick has been banned'''
        checknick = '%' + nick
        if checknick in self.hub.bans:
            if self.hub.bans[checknick] > time():
                raise ValueError, 'banned nick'
            self.removeban(checknick)
        return returnobj
        
    def loadbans(self):
        '''Load the bans from a file'''
        bans = {}
        curtime = time()
        try: 
            if not os.path.exists(self.banfile):
                file(self.banfile, 'wb').close()
                return self.hub.log.log(self.hub.loglevels['loading'], 'Created banfile')
            fil = file(self.banfile, 'rb')
            try:
                bannedlist = fil.readlines()
            finally:
                fil.close()
            for ban in [line.split(None,1) for line in bannedlist if line.strip() and not line[0] == '#']:
                banuntil = int(ban[1])
                if banuntil > curtime:
                    bans[ban[0]] = banuntil
        except:
            return self.hub.debugexception('Error loading bans', self.hub.loglevels['loadfileerror'])
        self.hub.bans = bans
        self.hub.log.log(self.hub.loglevels['loading'], 'Loaded %s bans' % len(bans.keys()))
        self.hub.log.log(self.hub.loglevels['loadingdebug'], 'Loaded bans: %s' % ' '.join(bans.keys()))
        
    def processcommand(self, user, command):
        '''Add/Remove/List/Clear bans'''
        if not user.op:
            return
        try:
            if command == '!list':
                message = '\r\n'.join([('%s %s' % (entry, strftime('%Y-%m-%d %X', 
                  localtime(banuntil)))) for entry, banuntil in self.hub.bans.items()])
                return self.hub.give_PrivateMessage(self, user, message)
            elif command == '!clear':
                self.hub.bans.clear()
                self.writebans()
                return self.hub.give_PrivateMessage(self, user, 'Ban list cleared') 
            curtime = int(time())
            entry, banuntil = command.split(None, 1)
            if entry.startswith('%'):
                nick = entry[1:]
                if nick in self.hub.nicks:
                    self.hub.removeuser(self.hub.nicks[nick])
            else:
                if entry.startswith('<>'):
                    nick = entry[2:]
                    if nick in self.hub.nicks:
                        entry = self.hub.nicks[nick].ip
                        self.hub.removeuser(self.hub.nicks[nick])
                    else:
                        raise ValueError, 'bad nick'
                for client in self.hub.sockets.values():
                    if client.ip.startswith(entry):
                        self.hub.removeuser(client)
                parts = entry.split('.')
                if len(parts) > 4:
                    raise ValueError,  'bad IP format'
                for part in parts:
                    if not part:
                        continue
                    part = int(part)
                    if not (0 <= part < 256):
                        raise ValueError, 'bad IP format'
            if banuntil[-1] in self.timechars:
                banuntil = curtime + int(banuntil[:-1]) * self.timechars[banuntil[-1]]
            else:
                banuntil = curtime + int(banuntil)
            if entry in self.hub.bans:
                if banuntil <= curtime:
                    self.removeban(entry)
                    return self.hub.give_PrivateMessage(self, user, 'Ban removed')
                self.hub.bans[entry] = banuntil
                self.writebans()
                self.hub.give_PrivateMessage(self, user, 'Ban updated')
            elif banuntil <= curtime:
                return self.hub.give_PrivateMessage(self, user, 'User is not banned')
            else:
                self.writebans(entry, banuntil)
                self.hub.give_PrivateMessage(self, user, 'Ban added')
        except:
            self.hub.debugexception('Error adding ban')
            return self.hub.give_PrivateMessage(self, user, 'Error adding ban')
            
    def removeban(self, entry):
        '''Remove a ban'''
        if entry in self.hub.bans:
            del self.hub.bans[entry]
        self.writebans()
        
    def start(self):
        '''Make sure the hub has a bans attribute'''
        if not hasattr(self.hub, 'bans'):
            self.hub.bans = {}
        self.loadbans()
        
    def writebans(self, entry = None, banuntil = 0):
        '''Write the ban file out to disk'''
        curtime = time()
        if isinstance(entry, str):
            self.hub.bans[entry] = banuntil
            fil = file(self.banfile,'ab')
            try:
                fil.write("\n%s %i" % (entry, banuntil))
            finally:
                fil.close()
            return self.hub.log.log(self.hub.loglevels['loading'], 'Wrote ban file to disk')
        banned = os.linesep.join(["%s %s" % (key, value) for key, value in self.hub.bans.items() if value > curtime])
        try:
            fil = file('%s.new' % self.banfile,'wb')
            try: 
                fil.write(banned)
            finally: 
                fil.close()
            os.rename(self.banfile, '%s.old' % self.banfile)
            os.rename('%s.new' % self.banfile, self.banfile)
            os.remove('%s.old' % self.banfile)
        except:
            return self.hub.debugexception('Error writing ban file to disk', self.hub.loglevels['loadfileerror'])
        self.hub.log.log(self.hub.loglevels['loading'], 'Wrote ban file to disk')
