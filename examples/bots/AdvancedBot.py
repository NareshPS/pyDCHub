from time import time
import DCHub

class AdvancedBot(DCHub.DCHubBot):
    '''Advanced bot designed to work with AdvancedDCHub
    
    This bot is designed to be a front end for some AdvancedDCHub functions, 
    and handle others itself.  See the docstring for AdvancedDCHub for a better
    idea of the functions it can provide.
    
    The bot understands the following command types: ban, list, log, python,
    silence, note, verify, unverify, history, hostname, stupidify, torrent, 
    scrub, sql, getpassword, and password.  torrent and password can be used by
    any verified user.  python and sql can be used by any op which has 
    "PythonBot" as a substring of their account's args.  All other commands are
    usable by any op.
    
    In general, to execute a command, you send a private message to AdvancedBot
    in the format "$commandtype $command" (note that you do not type in the $).  
    For example "hostname Joe" will execute the hostname function with the 
    argument "Joe".
    
    Also note that in general you are not going to want to interact with the
    bot via private messages.  Using UserCommands makes preforming necessary
    functions quick and easy.
    '''
    def __init__(self, hub, nick = 'AdvancedBot'):
        nick = hub.advancedbotname
        DCHub.DCHubBot.__init__(self, hub, nick)
        self.commands = {}
        # Commands that you don't need to be an op to use
        self.nonopcommands = 'torrent password'.split()
        # Commands that the bot understands
        for command in '''ban list log python silence note verify unverify 
           history hostname stupidify torrent scrub sql password chat
           getpassword'''.split():
            self.commands[command] = getattr(self, command)
        
    def ban(self, user, command):
        '''Ban a nick/IP for a period of time (see punish)'''
        self.punish(user, command, 3)
        
    def chat(self, user, command):
        '''Send a chat message from this bot'''
        self.hub.give_ChatMessage(self, command)
        
    def getpassword(self, user, command):
        '''Give the user's password to requester'''
        if command not in self.hub.accounts:
            return self.hub.advancedbotreply(user, "Account doesn't exist for user %r" % command)
        if self.hub.accounts[command]['op']:
            return self.hub.advancedbotreply(user, "Sorry, can't get passwords for ops")
        self.hub.advancedbotreply(user, "User %r has password %r" % (command, self.hub.accounts[command]['password']))
        
    def history(self, user, command):
        '''Give the history for an account
        
        Command should be in one of the following formats:
        "$nick": full history for nick
        "$nick $type": history for nick for the event ids listed in type, for
            example, a type of "136" would give a history consisting of only
            event ids 1, 3, and 5 (joins, bans, verifies).
        "$nick $type $days": history for nick for the last x number of days for 
            the given type. days can be an integer or a float to get partial
            days.
        "$nick  $days":   history for nick for the last x number of days for all
            types (yes, spaces are important, but in general UserCommands
            should be used to input commands).
        '''
        parts = command.split(' ')
        nick, type, days = '', '', ''
        oid, seconds = 0, 0
        types = []
        if not parts or len(parts) > 3:
            return self.hub.give_PrivateMessage(self, user, 'Error: Too many args for history command')
        if len(parts) == 1:
            (nick,) = parts
        elif len(parts) == 2:
            (nick, type) = parts
        elif len(parts) == 3:
            (nick, type, days) = parts
        if nick not in self.hub.accounts:
            return self.hub.give_PrivateMessage(self, user, 'Error: <%s> not in account database' % nick)
        for char in type:
            if char.isdigit():
                types.append(int(char))
        try:
            if not days:
                days = 365
            seconds = int(float(days) * 86400)
        except ValueError:
            return self.hub.give_PrivateMessage(self, user, 'Error: <%s> not in account database' % nick)
        self.hub.addtask(self.hub.givehistory, user, nick, types, seconds)
        
    def hostname(self, user, command):
        '''Get the hostname for a user
        
        Command should be a nick for a connected user.
        '''
        if command in self.hub.users and command not in self.hub.bots:
            self.hub.addtask(self.hub.givehostname, user, self.hub.users[command])
        else:
            return self.hub.give_PrivateMessage(self, user, 'Error: <%s> not connected' % command)
       
    def list(self, user, command):
        '''Give a list of related data structures
        
        Command should be one of the following:
        "ip $ip" -> list of accounts that have used the ip or ip range
        "nick $nick" -> list of accounts that have nick as a substring
        "silences", "bans", or "stupidifies" -> list of active punishments
        "nicks", "users", "ops", "accounts" -> list of keys of the hub's 
            dictionaries
        "unverified" -> List of unverified users
        '''
        if command.find(' ') != -1:
            searchtype, lookingfor = command.split(' ', 1)
            searchtype += 'search'
            if hasattr(self.hub, searchtype):
                self.hub.addtask(getattr(self.hub, searchtype), user, lookingfor)
            else:
                self.hub.give_PrivateMessage(self, user, 'Bad search type: %r' % searchtype)
            return
        if command in 'silences bans stupidifies'.split():
            message =  command + ':\r\n' +'\r\n'.join([('%s  -  %s' % (entry, self.hub.formattime(banuntil))) for entry, banuntil \
              in getattr(self.hub, command).iteritems()])
        elif command in 'nicks users ops accounts'.split():
            items = getattr(self.hub, command).keys()
            items.sort()
            message = '<%s>' % '> <'.join(items)
        elif command == 'unverified':
            items = []
            for client in self.hub.users.itervalues():
                if hasattr(client, 'verified') and not client.verified:
                    item = 'M:%s %s' % (client.tag[client.tag.find('M:')+2], client.nick)
                    if not client.description.lower().startswith(self.hub.descriptionstart.lower()):
                        item = 'BD %s' % item
                    items.append(item)
            if items:
                items.sort()
                message = 'Unverified Users: <%s>' % '> <'.join(items)
            else:
                message = "No unverified users, that's a w00t!"
        return self.hub.advancedbotreply(user, message)
        
    def log(self, user, command):
        '''Start/Stop/Update remote logging via private messages
        
        Command should be one of the following:
        "start": start logging at the hub's current log level
        "start $level": start logging at the integer log level given. The hub's
            log level should be lower or there will be no ouput
        "stop": stop logging
        "level $level": change the level of log messages for the connection
        '''
        if not user.op:
            return
        if command.startswith('start'):
            if user.nick not in self.hub.handlers:
                self.hub.handlers[user.nick] = self.hub.DCClientLogHandler(user, self)
                self.hub.log.addHandler(self.hub.handlers[user.nick])
            try:
                level = int(command[6:])
            except ValueError:
                pass
            else:
                self.hub.setlevel(user, level)
        elif command == 'stop':
            self.hub.removeloghandler(user)
        elif command.startswith('level'):
            try:
                level = int(command[6:])
            except ValueError:
                pass
            else:
                self.hub.setlevel(user, level)
                
    def note(self, user, command):
        '''Add a note to an account
        
        Command is in the format "$nick $note"
        '''
        nick, note = command.split(None, 1)
        if nick in self.hub.accounts:
            self.hub.addnote(note, user, nick)
            return self.hub.advancedbotreply(user, 'Note added for <%s>' % nick)
        else:
            return self.hub.give_PrivateMessage(self, user, 'Note NOT added for <%s>: no account' % nick)
                
    def parsepunishment(self, command, eventtypeid):
        '''Parse a punishment command into related arguments'''
        removeuser = False
        reason = ''
        nick = ''
        entry, banuntil = command.split(None, 1)
        if ' ' in banuntil:
            banuntil, reason = banuntil.split(' ', 1)
        if banuntil.isdigit():
            banuntil += 's'
        unbantime = self.hub.gettime(banuntil)
        if eventtypeid == 3 and int(time()) < unbantime:
            # eventtypeid 3 is ban, and if the user will be banned, they should
            # be kicked from the server, assuming the time given wasn't
            # negative or 0
            removeuser = True
        if entry.startswith('%'):
            # Punishment is for the nick
            nick = entry[1:]
            if nick in self.hub.nicks and removeuser:
                self.hub.kickban(self.hub.nicks[nick], banuntil, reason)
        else:
            # Punishment is for the IP
            if entry.startswith('<>'):
                # Punishment is for the IP of a user connected using the nick
                nick = entry[2:]
                if nick in self.hub.nicks:
                    entry = self.hub.nicks[nick].ip
                else:
                    raise ValueError, 'bad nick'
            if removeuser:
                for client in self.hub.sockets.itervalues():
                    if client.ip.startswith(entry):
                        self.hub.kickban(client, banuntil, reason)
            parts = entry.split('.')
            if len(parts) > 4:
                raise ValueError, 'bad IP format'
            for part in parts:
                if not part:
                    continue
                part = int(part)
                if not (0 <= part < 256):
                    raise ValueError, 'bad IP format'
        return entry, unbantime, reason, nick
        
    def password(self, user, command):
        '''Change the password for the user's account
        
        Command should be the password.
        '''
        command = command.strip()
        self.hub.give_PrivateMessage(self, user, 'Your password has been changed to: %s' % command)
        self.hub.give_PrivateMessage(self, user, 'Be sure to use this password when you reconnect to the hub.')
        self.hub.changepassword(user, command)
    
    def processcommand(self, user, command):
        '''Parse a private message from a user and launch the appropriate command'''
        fullcommand = command
        command, args = command.split(None, 1)
        if command in self.nonopcommands:
            if not user.verified:
                return self.hub.give_PrivateMessage(self, user, 'Only verified users can get/post torrents or change their password.')
        elif not user.op:
            return
        if command in self.commands:
            try:
                self.commands[command](user, args)
            except:
                self.hub.debugexception('Error in Python command from %s' % user.idstring)
                self.hub.sendtraceback(self, user, 'Python: %s' % args)
        else:
            self.hub.give_PrivateMessage(self, user, 'Bad command - %s' % command)

    def punish(self, user, command, eventtypeid):
        '''Punish a nick or IP for a given period of time
        
        Command should be one of the following:
        "$ip $length $note": Punish the IP for a given period of time.  A
            partial IP can be given to represent a range, any IP that begins
            with the partial IP matches the punishment.  Length is the length
            of the punishment, which is an integer which may be following by
            one of the following letters: s (seconds), m (minutes), h (hours),
            d (days), w (weeks), y (years).  Note is the related note to store
            in the database.
        "%$nick $length $note": Punish the nick for the give period of time.
        "<>$nick $length $note": Punish the IP of the user currently using the
            nick.
        '''
        curtime = int(time())
        entry, until, reason, punishee = self.parsepunishment(command, eventtypeid)
        tup = (self.hub.eventtypenames[eventtypeid], punishee)
        if entry in self.hub.eventtypedict[eventtypeid]:
            if self.hub.eventtypedict[eventtypeid][entry] <= curtime:
                self.scrub(user, '', [eventtypeid])
            elif until <= curtime:
                self.hub.removeevent(entry, user, punishee, eventtypeid)
                self.hub.advancedbotreply(user, '%s removed for <%s>' % tup)
            else:
                self.hub.updateevent(entry, until, reason, user, punishee, eventtypeid)
                self.hub.advancedbotreply(user, '%s updated for <%s>' % tup)
            return
        if until <= curtime:
            self.hub.give_PrivateMessage(self, user, '%s does not exist for <%s>' % tup)
        else:
            self.hub.addevent(entry, until, reason, user, punishee, eventtypeid)
            self.hub.advancedbotreply(user, '%s added for <%s>' % tup)
        
    def python(self, user, command):
        '''Execute Python commands in the hub's process
        
        Command should be a valid python command or commands.
        '''
        hub = self.hub
        command = hub.unescape(command)
        if user.account['args'].find('PythonBot') != -1:
            exec command
        else:
            self.hub.give_PrivateMessage(self, user, 'Sorry, no Python access for you')
            
    def scrub(self, user, command, eventtypeids = range(3,6)):
        '''Scrub old punishment entries
        
        This removes old punishments that ended in the past but are still
        present in the database or hub's memory.  Doesn't change the hub's
        behavior, it's just a housekeeping command.
        '''
        for eventtypeid in eventtypeids:
            self.hub.scrubevents(eventtypeid)
            if eventtypeids == range(3,6):
                self.hub.advancedbotreply(user, '%s list scrubbed' % self.hub.eventtypenames[eventtypeid])
                
    def silence(self, user, command):
        '''Silence a nick/IP for a given period of time (see punish)'''
        self.punish(user, command, 4)
        
    def sql(self, user, command):
        '''Run an SQL command against the database
        
        Command should be the SQL statement or statements to execute.
        '''
        if user.account['args'].find('PythonBot') == -1:
            self.hub.give_PrivateMessage(self, user, 'Sorry, no SQL access for you')
        self.hub.addtask(self.hub.runsql, user, command)
        
    def stupidify(self, user, command):
        '''Stupidify a nick/IP for a given period of time (see punish)'''
        self.punish(user, command, 5)
        
    def torrent(self, user, command):
        '''Manage torrents on the hub
        
        Command should be one of the following:
        "$location $description": Add a torrent with the given location and 
            description (not visible till approved by an op).
        "approve $id": Approve the torrent that has the given id
        "remove $id": Remove the torrent that has the given id.  This can be
            done before approval so that it doesn't show up in the list, or
            after approval to remove it if it is no longer operating or 
            relevant.
        "get": get list of active torrents
        '''
        if command == 'get':
            return self.hub.give_PrivateMessage(self, user, 'Active Torrents:\n%s' % self.hub.gettorrents(user))
        if user.op:
            if command.startswith('approve ') or command.startswith('remove '):
                type, torrentoid = command.split(None, 1)
                try:
                    torrentoid = int(torrentoid)
                except ValueError:
                    return self.hub.give_PrivateMessage(self, user, 'Error: torrent id is not a number')
                if torrentoid not in self.hub.torrents:
                    return self.hub.give_PrivateMessage(self, user, 'Error: torrent id is not valid')
                torrent = self.hub.torrents[torrentoid]
                if type == 'approve':
                    if 'approvalby' in torrent:
                        return self.hub.give_PrivateMessage(self, user, 'Error: torrent already approved by <%s>' % torrent['approvalby'])
                    self.hub.approvetorrent(user, torrent)
                    return self.hub.advancedbotreply(user, 'Torrent id %i approved' % torrentoid)
                if type == 'remove':
                    self.hub.removetorrent(user, torrent)
                    return self.hub.advancedbotreply(user, 'Torrent id %i removed' % torrentoid)
                return
        try:
            location, description = command.split(None, 1)
            if not (location.startswith('http://') or location.startswith('ftp://')) or not location.endswith('.torrent'):
                return self.hub.give_PrivateMessage(self, user, 'Error: torrent location must start with http:// or ftp:// and must end in .torrent')
            for tor in self.hub.torrents.itervalues():
                if location == tor['location']:
                    return self.hub.give_PrivateMessage(self, user, 'Error: torrent has already been added (might not be approved yet).')
            if not description:
                return self.hub.give_PrivateMessage(self, user, 'Error: torrent description is empty')
            self.hub.addtask(self.hub.addtorrent, user, location, description)
        except ValueError:
            return self.hub.give_PrivateMessage(self, user, 'Error: wrong fromat for torrent post.')
        
    def unverify(self, user, command):
        '''Unverify an account (see verify)'''
        self.verify(user, command, verify=False)
        
    def verify(self, user, command, verify = True):
        '''Verify an account
        
        Command should be the nick to verify/unverify
        '''
        type = verify and 'verif' or 'unverif'
        nick, note = command.split(None, 1)
        if nick in self.hub.accounts:
            if (not verify) ^ self.hub.accounts[nick]['verified']:
                return self.hub.give_PrivateMessage(self, user, 'Error: %s is already a %sied user' % (nick, type))
            self.hub.verifynick(nick, user, note, verify)
            for op in self.hub.ops.itervalues():
                self.hub.give_PrivateMessage(self, op, '<%s> %sied by <%s>' % (nick, type, user.nick))
        else:
            self.hub.give_PrivateMessage(self, user, 'Error: %s is not in the account database' % nick)
