import logging
import os
import random
from sets import Set as set
import socket
import sys
from thread import get_ident as threadid
import threading
from ThreadedDCHub import ThreadedDCHub, run
import traceback
from time import time, strftime, gmtime

# Necessary to run under chroot
import codecs
from encodings import utf_8, latin_1, aliases

try:
    import sqlite
except ImportError:
    pass
try:
    import apsw
except ImportError:
    pass
try:
    from pysqlite2 import dbapi2 as sqlite2
except ImportError:
    pass

def dbquote(string):
    '''Quote string to make it acceptable for SQLite'''
    return "'%s'" % string.replace("'", "''")

class DCClientLogHandler(logging.Handler):
    '''Logging handler that sends log messages to a Direct Connect client'''
    def __init__(self, user, bot):
        logging.Handler.__init__(self)
        self.escapetranstable = (('\n', '\r\n'), ('|', '&#124;'), ('$', '&#36;'))
        self.user = user
        self.bot = bot
        
    def emit(self, record):
        '''Send user the log message via a private message from the bot
        
        Note that log messages for data sent that include private messages from
        the bot are not sent to the user, as this would allow for an infinite
        loop.  If multiple commands were sent to the user, and even one is a 
        private message from the bot, the user will not get a related log 
        message.
        
        Also note that the user will not be sent tracebacks if the the message
        is logged using exception.
        '''
        message = self.format(record)
        # Note that if the log level for data sent messages is changed from
        # the default of 1, you could get an infinite loop unless you change
        # the value here
        if record.levelno == 1 and message.find('From: %s $<%s>' % (self.bot.nick, self.bot.nick)) != -1:
            # Ignore data sent messages that include private messages from the
            # bot
            return
        # Escape illegal characters
        for changethis, tothis in self.escapetranstable:
            message = message.replace(changethis, tothis)
        self.user.sendmessage("$To: %s From: %s $<%s> %s: %s|" % (self.user.nick, 
          self.bot.nick, self.bot.nick, record.levelname, message))

class AdvancedDCHub(ThreadedDCHub):
    '''Advanced hub with many additional features
    
    This hub is the embodiment of the way I think advanced hubs should be 
    designed using py-dchub.  All core functionality is kept in the hub itself,
    no wrapping/unwrapping of functions occurs when the bots are reloaded.  The
    hub is designed to be used in conjuction with AdvancedBot, which handles 
    some features internally, and is a front end to the hub for others.  Some 
    of the features discussed below are actually coded in AdvancedBot.py.
    
    This hub has many features that are not in the standard hub.  Some of the
    features are similar or identical to features offered by other bots such as
    BanBot and LogBot.  Some of these features are:
    
    Verification: Accounts are created upon first login of any nick.  When
    first created, the accounts are in an unverified state.  They cannot search
    the hub, they cannot connect to other users, they do not see other users
    search messages, and only ops can connect to them (assuming 
    restrictunverifiedusers is True).  After an op has verified them, they can
    search and connect as they would be able to using standard py-dchub.  Users
    can be unverified and/or reverified at any point.
    
    Punishments: Users can be punished, either banned, silenced, or
    stupidified.  Banning users kicks them from the hub (if they are currently
    connected) and disallows their login. Silencing users disallows chat 
    messages from them (private messages are still allowed).  Stupidifying
    users partially jumbles chat messages they send to the hub (private
    messages are unaffected).  All punishments can be by nick or by IP, and
    for a configurable amount of time per punishment.
    
    Notes: Ops can post notes about users, which will be viewable in their
    history.

    History: The hub keeps track of all joins/leaves, punishment changes (adds,
    updates, and removes), notes, and verifies/unverifies.  These can be
    recalled at any point in time, without resorting to grepping a log file
    (which is still available if needed).
    
    Torrents: Verified users can post torrents and view active torrents.  When
    a torrent is posted, ops are notified and can choose whether to approve or
    reject the torrent post.  Inactive torrents can be removed from the
    torrent list at any point.
    
    Password Changes: Verified users can change their password at any point,
    users are asked to change their password as soon as they are verified (if
    they don't already have a password set).
    
    Storage: The hub stores it's accounts, active punishments, historical data
    and torrents in an SQLite database.  SQLite was chosen because it is
    simple to install and use, portable across a wide variety of operating
    systems, and self contained in a single file.  The database can easily be
    sent arbitrary SQL commands.  All database access after initial loading
    of information takes place in separate threads, so database access should
    never block normal hub operation.  You can use either pysqlite or apsw as
    the database driver.
    
    Hostnames: The hub can do a reverse lookup on any user's IP to find their
    hostname.
    
    Reloading Bots: Bots can be reloaded via a command sent to the hub.
    
    UserCommands: There are an extensive number (around 50) UserCommands
    available to make the hub easy to administer.
    
    OpChat-AdvancedDCHub: The hub is designed to work with 
        OpChat-AdvancedDCHub, which doesn't require functions to be wrapped or
        unwrapped when the bot is reloaded (unlike regular OpChat).
    '''
        
    def addevent(self, entry, until, reason, op, user, eventtypeid):
        '''Add an event (punishment) to the database
        
        Adds an event to the list of active events, as well as storing the
        addition for historical purposes.  This is currently only used for 
        storing punishments, since those are only active events.
        '''
        curtime = int(time())
        self.eventtypedict[eventtypeid][entry] = until
        query = 'INSERT INTO activeevents (eventtypeid, entry, until) VALUES (%i, %s, %i);' % (eventtypeid, dbquote(entry), until)
        self.addtask(self.execsql, query)
        noteby, accountid = self.getoid(op), self.getoid(user)
        if accountid != 'NULL':
            query = 'INSERT INTO events (accountid, eventtypeid, time, noteby, note) VALUES (%i, %i, %i, %s, %s);' % (accountid, eventtypeid, curtime, noteby, dbquote('added/%i/%s' % (until - curtime, reason)))
            self.addtask(self.execsql, query)
        
    def addjoin(self, user):
        '''Store a join event in the database
        
        This remembers the time of the join so that when the user leaves the
        amount of time they spent connected can be used to update the join
        record.
        '''
        curtime = int(time())
        query = 'INSERT INTO events (accountid, eventtypeid, time, note) VALUES (%i, 1, %i, %s);' % (user.account['oid'], curtime, dbquote(user.ip))
        self.execsql(query)
        query = 'SELECT oid FROM events WHERE accountid = %i ORDER BY oid DESC LIMIT 1;' % user.account['oid']
        user.joinoid = self.execsql(query, fetch=True)[0][0]
        user.jointime = curtime
        
    def addnote(self, note, op, user):
        '''Add a note on a user to the database'''
        noteby, accountid = self.getoid(op), self.getoid(user)
        if accountid != 'NULL':
            query = 'INSERT INTO events (accountid, eventtypeid, time, noteby, note) VALUES (%i, 7, %i, %s, %s);' % (accountid, int(time()), noteby, dbquote(note))
            self.addtask(self.execsql, query)
            
    def addtorrent(self, user, location, description):
        '''Add a torrent to the database
        
        Note that a torrent will not be available for users to view until it
        has been approved by an op.
        '''
        try:
            curtime = int(time())
            accountid = self.getoid(user)
            if accountid == 'NULL':
                raise ValueError, 'accountid is null for torrent add'
            query = 'INSERT INTO torrents (addedby, addedtime, location, description) VALUES (%i, %i, %s, %s);' % (accountid, curtime, dbquote(location), dbquote(description))
            self.execsql(query)
            query = 'SELECT oid FROM torrents WHERE location = %s;' % dbquote(location)
            torrentoid = self.execsql(query, fetch=True)[0][0]
            self.torrents[torrentoid] = {'oid':torrentoid, 'location': location, 'description': description, 'addedby':user.nick, 'addedtime':curtime}
        except:
            self.debugexception('Error adding torrent, maybe no account id?', self.loglevels['commanderror'])
            return self.give_PrivateMessage(self.advancedbotname, user, 'Error: undefined error adding torrent')
        else:
            self.give_PrivateMessage(self.advancedbotname, user, 'Torrent added, awaiting on approval by op')
            message = 'Torrent (id %i) added by %s, awaiting approval: location=%r description=%r' % (torrentoid, user.nick, location, description)
            for op in self.ops.itervalues():
                self.give_PrivateMessage(self.advancedbotname, op, message)
        
    def adduser(self, user):
        '''Add a new connection to the hub, check that they are not banned'''
        for ip, banuntil in self.bans.items():
            if user.ip.startswith(ip):
                if banuntil > int(time()):
                    user.close()
                    return self.log.log(self.loglevels['useradderror'], '%s is banned, disconnecting them' % user.idstring)
                else:
                    self.removeevent(ip, None, None, 3)
        # All connections are assumed to be unverified until they have
        # submitted a user name and password.  There is no way to have verified
        # IP addresses, for example.
        user.verified = False
        self.supers['AdvancedDCHub'].adduser(user)
        
    def advancedbotreply(self, user, message):
        '''Send a message to the user as a private or chat message
        
        If the user has AdvancedBot2MainChat in their args, send the message as
        a chat message, otherwise send it as a private message from 
        AdvancedBot.
        '''
        if user.account['args'].find('AdvancedBot2MainChat') == -1:
            self.give_PrivateMessage(self.advancedbotname, user, message)
        else:
            user.sendmessage('%s|' % message)
        
    def approvetorrent(self, user, torrent):
        '''Approve a torrent so that it can be seen by users'''
        curtime = int(time())
        accountid = self.getoid(user)
        if accountid == 'NULL':
            raise ValueError, 'no account associated with torrent'
        query = 'UPDATE torrents SET active = 1, approvalby = %i, approvaltime =%i WHERE oid = %i;' % (accountid, curtime, torrent['oid'])
        self.addtask(self.execsql, query)
        torrent['approvalby'] = user.nick
        torrent['approvaltime'] = curtime
        self.give_ChatMessage('Hub-Security', 'Torrent added by <%(addedby)s>: %(location)s - %(description)s' % torrent)
        
    def changepassword(self, user, password):
        '''Change the password for an account
        
        The user can either be a string (nick) or a DCHubClient object.
        '''
        if isinstance(user, str):
            nick = user
        else:
            nick = user.nick
        self.accounts[nick]['password'] = password
        query = 'UPDATE accounts SET password = %s WHERE nick = %s;' % (dbquote(password), dbquote(nick))
        self.addtask(self.execsql, query)
        
    def createaccount(self, user):
        '''Create an account for a user
        
        Usually this is done upon the first login using the nick, but it's
        possible to create accounts in advance by passing a string.
        '''
        if isinstance(user, str):
            nick = user
        else:
            nick = user.nick
        curtime = int(time())
        query = 'INSERT INTO accounts (nick, creationtime) VALUES (%s, %i);' % (dbquote(nick), curtime)
        self.execsql(query)
        query = 'SELECT oid FROM accounts WHERE nick = %s;' % dbquote(nick)
        oid = self.execsql(query, fetch=True)[0][0]
        self.accounts[nick] = {'name':nick, 'oid':oid, 'password':'',
            'args':'', 'op':0, 'verified':0, 'creationtime':curtime}
        if not isinstance(user, str):
            user.account = self.accounts[nick]
            self.addjoin(user)
        
    def clearevents(self, eventtypeid):
        '''Clear all active events of a certain type
        
        Currently this function is unused by the hub.
        '''
        self.eventtypedict[eventtypeid].clear()
        query = 'DELETE FROM activeevents WHERE eventtypeid = %i;' % eventtypeid
        self.addtask(self.execsql, query)
        
    def dbconnect(self, connect = True):
        '''Connect to the database
        
        This function is typically run once per thread, since threads may not
        share database connections in pysqlite.
        '''
        tid = threadid()
        type = connect and 'Connecting to' or 'Disconnecting from'
        self.log.log(self.loglevels['threading'], 'Thread %i %s database' % (tid, type))
        self.threaddata[tid]['dbtype'] = self.dbtype
        getattr(self, 'dbconnect_%s' % self.threaddata[tid]['dbtype'])(connect)
        
    def dbconnect_apsw(self, connect):
        '''Connect to the database using apsw
        
        apsw doesn't have close functions for their connections and cursors,
        so I assume that closing those resources happens when they are garbage
        collected.
        '''
        tid = threadid()
        if connect:
            self.threaddata[tid]['dbconn'] = apsw.Connection(self.dbfile)
            self.threaddata[tid]['dbcursor'] = self.threaddata[tid]['dbconn'].cursor()
            self.threaddata[tid]['dbconn'].setbusytimeout(5000)
        else:
            del self.threaddata[tid]['dbcursor']
            del self.threaddata[tid]['dbconn']
    
    def dbconnect_pysqlite(self, connect):
        '''Connect to the database using pysqlite'''
        tid = threadid()
        if connect:
            self.threaddata[tid]['dbconn'] = sqlite.connect(self.dbfile, encoding="utf8", timeout=5)
            self.threaddata[tid]['dbcursor'] = self.threaddata[tid]['dbconn'].cursor()
        else:
            self.threaddata[tid]['dbcursor'].close()
            self.threaddata[tid]['dbconn'].close()

    def dbconnect_pysqlite2(self, connect):
        '''Connect to the database using pysqlite'''
        tid = threadid()
        if connect:
            self.threaddata[tid]['dbconn'] = sqlite2.connect(self.dbfile, timeout=5)
            self.threaddata[tid]['dbcursor'] = self.threaddata[tid]['dbconn'].cursor()
        else:
            self.threaddata[tid]['dbcursor'].close()
            self.threaddata[tid]['dbconn'].close()

    def enforceverification(self):
        '''Don't allow unverified users to search or connect to other users'''
        if self.restrictunverifiedusers:
            return
        self.restrictunverifiedusers = True
        self.validusercommands -= self.verifiedusercommands
        for user in self.users.itervalues():
            if hasattr(user, 'verified') and not user.verified:
                user.validcommands -= self.verifiedusercommands
        
    def escape(self, message):
        '''Escape characters being sent from the hub to the users
        
        Note that escaping is rarely needed, since clients escape messages they
        send and unescape messages they receive, so in general the hub is just
        passing messages through.
        '''
        for changethis, tothis in self.escapetranstable:
            message = message.replace(changethis, tothis)
        return message
        
    def execsql(self, sql, commit = True, fetch = False, raiseerrors = False):
        '''Execute SQL code on the database
        
        Commits the changes by default (the only time this shouldn't be used is
        if you want to send multiple commands in a single transaction, with the
        ability to make changes to later queries based on the results of 
        earlier queries).
        
        Fetches the resutls if requested.  In general only SELECT statements 
        should set fetch.  If fetch is True, it fetchs the entire result set, 
        otherwise if it is a integer, it fetchs that number of rows.
        fetch=True and fetch=1 are two different commands.
        '''
        tid = threadid()
        connection = self.threaddata[tid]['dbconn']
        cursor = self.threaddata[tid]['dbcursor']
        self.log.log(self.loglevels['sql'], 'Executing SQL: %r' % sql)
        # apsw uses Unicode internally, so if you have a user with a
        # non-ascii nick (common with users from European countries), 
        # it will complain, bitterly, if you give it a string that isn't
        # 7-bit ascii.  pysqlite is different and will happily stick Latin-1
        # formatted strings into the database.  In order to be able to
        # switch between apsw and pysqlite easily, you need to store everything
        # as Unicode strings, which necessitates decoding them before
        # executing them and encoding them after getting back the results.  
        sql = sql.decode('latin1')
        return getattr(self, 'execsql_%s' % self.dbtype)(connection, cursor, sql, commit, fetch, raiseerrors)

    def execsql_apsw(self, connection, cursor, sql, commit, fetch, raiseerrors):
        '''Executes sql code against apsw database
        
        apsw doesn't follow the Python DB-API, so it is left in autocommit
        mode.  It transactions are desired, you need to use BEGIN and COMMIT
        manually.
        '''
        rows = None
        try:
            rowiter = cursor.execute(sql)
            if fetch is True:
                rows = list(rowiter)
            elif isinstance(fetch, int):
                rows = []
                for row in rowiter:
                    rows.append(row)
                    if len(rows) > fetch:
                        break
            if rows:
                rows = [list(row) for row in rows]
                for row in rows:
                    for j, item in enumerate(row):
                        if isinstance(item, unicode):
                            # Convert from Unicode back to string
                            row[j] = item.encode('latin1')
        except Exception, error:
            # APSWException doesn't work.  Unfortunately, this means a lot of
            # other errors will be caught.
            self.log.exception('Database error %r executing %r' % (error, sql))
            if raiseerrors:
                raise error
        return rows

    def execsql_pysqlite(self, connection, cursor, sql, commit, fetch, raiseerrors):
        '''Executes sql code against pysqlite database'''
        rows = None
        try:
            # For some reason, the database doesn't like being accessed by
            # multiple threads at once.  You might want to consider using
            # numtaskrunners = 1 if using pysqlite.  Also note that pysqlite
            # doesn't release the Python Global Interpreter Lock, so anything
            # that blocks the database will block the entire program.
            cursor.execute(sql)
            if commit:
                connection.commit()
            if fetch is True:
                rows = cursor.fetchall()
            elif isinstance(fetch, int) and fetch > 0:
                rows = cursor.fetchmany(fetch)
            if rows:
                rows = [list(row) for row in rows]
                for row in rows:
                    for j, item in enumerate(row):
                        if isinstance(item, str):
                            # Convert from Unicode back to string
                            row[j] = item.decode('utf8').encode('latin1')
        except sqlite.DatabaseError, error:
            self.log.exception('Database error %r executing %r' % (error, sql))
            if raiseerrors:
                raise error
        return rows
        
    def execsql_pysqlite2(self, connection, cursor, sql, commit, fetch, raiseerrors):
        '''Executes sql code against pysqlite2 database'''
        rows = None
        try:
            cursor.execute(sql)
            if commit:
                connection.commit()
            if fetch is True:
                rows = cursor.fetchall()
            elif isinstance(fetch, int) and fetch > 0:
                rows = cursor.fetchmany(fetch)
            if rows:
                rows = [list(row) for row in rows]
                for row in rows:
                    for j, item in enumerate(row):
                        if isinstance(item, str):
                            row[j] = item.decode('utf8')
                        if isinstance(item, unicode):
                            row[j] = item.encode('latin1')
        except sqlite2.DatabaseError, error:
            self.log.exception('Database error %r executing %r' % (error, sql))
            if raiseerrors:
                raise error
        return rows
    
    def formattime(self, seconds):
        '''Return the formated time for the given unix ticks'''
        return strftime(self.historyftime, gmtime(seconds))
        
    def getoid(self, user = ''):
        '''Get the SQLite oid for the user or account (or NULL if nonexistant)'''
        if isinstance(user, str) and user in self.accounts:
            return self.accounts[user]['oid']
        if user and hasattr(user, 'account') and isinstance(user.account, dict):
            return user.account['oid']
        return 'NULL'
        
    def gettime(self, seconds):
        '''Get the unix ticks for the current time plus the given amount of time
        
        If the last character of the time given is recognized, multiple it to
        get the correct number of seconds (1d = 86400), otherwise assume the
        time given is in seconds.
        '''
        curtime = int(time())
        if seconds[-1] in self.timechars:
            seconds = curtime + int(seconds[:-1]) * self.timechars[seconds[-1]]
        else:
            seconds = curtime + int(seconds)
        return seconds
        
    def gettorrents(self, user):
        '''Return the list of approved torrents'''
        message = 'Posted by <%(addedby)s> - %(location)s - %(description)s'
        if user.op:
            message = 'Posted by <%(addedby)s> - %(oid)i - %(location)s - %(description)s'
        return '\n'.join([message % torrent for torrent in self.torrents.itervalues()])
        
    def givehistory(self, user, nick, types, seconds):
        '''Give the history for the nick to the user
        
        To specify eventtypes, pass the related eventtypeids as a sequence.
        To specify recent events, pass the number of seconds in the past after
        which you are interested in getting results.
        '''
        after = int(time()) - seconds
        if nick not in self.accounts:
            return self.give_PrivateMessage(self.advancedbotname, user, 'No account exists for <%s>' % nick)
        verified = self.accounts[nick]['verified'] and 'Verified' or 'Unverified'
        usertype = self.accounts[nick]['op'] and 'Op' or 'User'
        accountid = self.getoid(nick)
        typequery = ''
        lines = ['History for <%s>, %s %s, account created on %s' % (nick, verified, usertype, self.formattime(self.accounts[nick]['creationtime']))]
        if types:
            typequery = 'AND (%s) ' %  ' OR '.join([' events.eventtypeid=%i ' % t for t in types])
        query = 'SELECT events.eventtypeid, accounts.nick, events.time, events.note FROM events LEFT JOIN accounts ON events.noteby = accounts.oid WHERE events.accountid = %i AND events.time > %i %s ORDER BY events.time LIMIT %i;' % (accountid, after, typequery, self.maxhistoryrows)
        try:
            events = self.execsql(query, fetch=True, raiseerrors=True)
        except:
            return self.sendtraceback(self.advancedbotname, user, 'SQL: %r' % query)
        for event in events:
            lines.append(self.historylines[event[0]] % {'noteby':event[1], 'time':self.formattime(event[2]), 'note':event[3]})
        self.advancedbotreply(user, self.escape('\n'.join(lines)))
        
    def givehostname(self, requester, user):
        '''Do a reverse lookup on the user's IP and give it to the requestor'''
        try:
            hostname = socket.gethostbyaddr(user.ip)[0]
        except Exception, e:
            self.advancedbotreply(requester, '<%s> using IP %s, hostname lookup failed: %s' % (user.nick, user.ip, str(e)))
        else:
            self.advancedbotreply(requester, '<%s> using IP %s, hostname %s' % (user.nick, user.ip, hostname))
            
    def ipsearch(self, user, ip):
        '''Give a list of accounts that have used the IP or IP range'''
        iprange = dbquote(ip + '%')
        query = 'SELECT accounts.nick FROM events LEFT JOIN accounts ON events.accountid = accounts.oid WHERE events.eventtypeid = 1 AND events.note LIKE %s GROUP BY accounts.nick;' % iprange
        try:
            rows = self.execsql(query, fetch=True, raiseerrors=True)
        except:
            return self.sendtraceback(self.advancedbotname, user, 'Error searching for IP')   
        if rows is None:
            message = "No logins from %s" % ip
        else:
            message = "The following accounts have logged in from %s: <%s>" % (ip, '> <'.join([row[0] for row in rows]))
        self.advancedbotreply(user, message)

    def kickban(self, user, banlength, reason):
        '''Kick the user from the hub and give a ban message to the chat'''
        self.give_ChatMessage('Hub-Security', '%s is being kickbanned for %s because %s' % (user.nick, banlength, reason))
        user.ignoremessages = True

    def loadaccounts(self):
        '''Load accounts from the database'''
        self.dbconnect()
        accounts = {}
        oids = {}
        query = 'SELECT oid, nick, password, args, op, verified, creationtime FROM accounts ORDER BY oid;'
        try:
            for oid, nick, password, args, op, verified, creationtime in self.execsql(query, fetch=True):
                accounts[nick] = {'name':nick, 'oid':oid, 'password':password,
                    'args':args, 'op':bool(op), 'verified':bool(verified),
                    'creationtime':creationtime}
                oids[oid] = accounts[nick]
        except:
            return self.debugexception('Error loading accounts', self.loglevels['loadfileerror'])
        self.accounts.clear()
        self.accounts.update(accounts)
        self.oids.clear()
        self.oids.update(oids)
        self.log.log(self.loglevels['loading'], 'Loaded %s accounts' % len(accounts.keys()))
        self.log.log(self.loglevels['loadingdebug'], 'Loaded accounts: %s' % ' '.join(accounts.keys()))
        
    def loadpunishments(self):
        '''Load the punishments from the database'''
        bans, silences, stupidifies = {}, {}, {}
        eventtypes = {3:bans, 4:silences, 5:stupidifies}
        query = 'DELETE FROM activeevents WHERE until <= %i;' % int(time())
        self.execsql(query)
        query = 'SELECT eventtypeid, entry, until FROM activeevents ORDER BY oid;'
        try:
            for eventtypeid, entry, until in self.execsql(query, fetch=True):
                eventtypes[eventtypeid][entry] = until
        except:
            return self.debugexception('Error loading punishments', self.loglevels['loadfileerror'])
        self.bans.clear()
        self.bans.update(bans)
        self.silences.clear()
        self.silences.update(silences)
        self.stupidifies.clear()
        self.stupidifies.update(stupidifies)
        self.log.log(self.loglevels['loading'], 'Loaded %s bans' % len(bans.keys()))
        self.log.log(self.loglevels['loadingdebug'], 'Loaded bans: %s' % ' '.join(bans.keys()))
        self.log.log(self.loglevels['loading'], 'Loaded %s silences' % len(silences.keys()))
        self.log.log(self.loglevels['loadingdebug'], 'Loaded silences: %s' % ' '.join(silences.keys()))
        self.log.log(self.loglevels['loading'], 'Loaded %s stupidifies' % len(stupidifies.keys()))
        self.log.log(self.loglevels['loadingdebug'], 'Loaded stupidifies: %s' % ' '.join(stupidifies.keys()))
        
    def loadtorrents(self):
        '''Load the torrents from the database'''
        torrents = {}
        query = 'SELECT oid, addedby, addedtime, approvalby, approvaltime, location, description FROM torrents WHERE active;'
        try:
            for oid, addedby, addedtime, approvalby, approvaltime, location, description in self.execsql(query, fetch=True):
                torrents[oid] = {'oid':oid, 'addedby':self.oids[addedby]['name'], 
                    'addedtime':addedtime, 'approvalby':self.oids[approvalby]['name'], 
                    'approvaltime':approvaltime, 'location':location, 'description':description}
        except:
            return self.debugexception('Error loading torrents', self.loglevels['loadfileerror'])
        self.torrents.clear()
        self.torrents.update(torrents)
        self.log.log(self.loglevels['loading'], 'Loaded %s torrents' % len(torrents.keys()))
        
    def loginuser(self, user):
        '''Log the user into the hub, and create an account for them if necessary
        
        If the user doesn't have an account, create one.  If the user has an
        account, record their join to the database.  If the user is unverified,
        send a message to the ops.
        '''
        self.supers['AdvancedDCHub'].loginuser(user)
        if user.account is not None:
            self.addtask(self.addjoin, user)
            if user.account['verified']:
                self.verifyuser(user)
        else:
            self.addtask(self.createaccount, user)
        if not user.verified:
            if self.restrictunverifiedusers:
                user.sendmessage('<Hub-Security> *********\r\nNOTE: You are an unverified user, you have no search or download privileges. Make sure you are following the rules, and you will be verified as soon as an operator can check you. Please be patient, as there may not be an op around right away.\r\n*********|')
            for op in self.ops.itervalues():
                self.give_PrivateMessage(self.advancedbotname, op, 'Unverified user joined: <%s>' % user.nick)
        if not user.description.lower().startswith(self.descriptionstart.lower()):
            for op in self.ops.itervalues():
                self.give_PrivateMessage(self.advancedbotname, op, '<%s> has a bad description: %r' % (user.nick, user.description))
    
    def makeop(self, nick, makeop=True):
        '''If makeop is True, make the nick an op, otherwise remove op status
        
        If the user is logged in, immediately make them an op and give the hub
        the new op list.
        '''
        if nick not in self.accounts:
            raise ValueError, 'No account for <%s>' % nick
        self.accounts[nick]['op'] = makeop
        query = "UPDATE accounts SET op = %i WHERE nick = %s" % (makeop, dbquote(nick))
        self.addtask(self.execsql, query)
        if nick in self.users:
            user = self.users[nick]
            user.op = makeop
            if makeop:
                user.validcommands |= self.validopcommands
                self.ops[nick] = user
            elif nick in self.ops:
                del self.ops[nick]
                user.validcommands -= self.validopcommands
            self.giveOpList()
            
    def nicksearch(self, user, nick):
        '''Give a list of accounts that have nick as a substring'''
        nicklower = nick.lower()
        rows = [account for account in self.accounts if account.lower().find(nicklower) != -1]
        if not rows:
            message = "No accounts have %r as a substring" % nick
        else:
            message = "The following accounts have %r as a substring: <%s>" % (nick, '> <'.join(rows))
        self.advancedbotreply(user, message)
            
    def removeevent(self, entry, op, user, eventtypeid):
        '''Remove the event (punishment)
        
        In many cases, this is called by the system to remove out of date
        information from the database (similar to scrub).
        '''
        if entry in self.eventtypedict[eventtypeid]:
            del self.eventtypedict[eventtypeid][entry]
        query = 'DELETE FROM activeevents WHERE eventtypeid = %i AND entry = %s;' % (eventtypeid, dbquote(entry))
        self.addtask(self.execsql, query)
        noteby, accountid = self.getoid(op), self.getoid(user)
        if accountid != 'NULL':
            query = "INSERT INTO events (accountid, eventtypeid, time, noteby, note) VALUES (%i, %i, %i, %s, 'removed');" % (accountid, eventtypeid, int(time()), noteby)
            self.addtask(self.execsql, query)
        
    def removeloghandler(self, user):
        '''Stop sending the log message to the user via a private message'''
        if user.loggedin and user.nick in self.handlers:
            self.log.removeHandler(self.handlers[user.nick])
            del self.handlers[user.nick]
            
    def removetorrent(self, user, torrent):
        '''Remove a torrent from the list of active torrents'''
        oid = torrent['oid']
        self.log.log(self.loglevels['torrent'], 'Torrent id %i removed by <%s>' % (oid, user.nick))
        del self.torrents[oid]
        query = 'UPDATE torrents SET active = 0 WHERE oid = %i;' % oid
        self.addtask(self.execsql, query)
            
    def removeuser(self, user):
        '''Remove a user from hub, notate how long they were connected'''
        self.supers['AdvancedDCHub'].removeuser(user)
        self.removeloghandler(user)
        if user is self.messageuser:
            self.messageuser = None
            for op in self.ops.itervalues():
                self.give_PrivateMessage('OpChat', op, '* #%s# left, ## unset' % user.nick)
        if hasattr(user, 'joinoid'):
            query = "UPDATE events SET note = note || '/' || %i WHERE oid = %i;" % (int(time()) - user.jointime, user.joinoid)
            self.addtask(self.execsql, query)

    def runsql(self, user, sql):
        '''Run sql code against the database, return results to user'''
        try:
            rows = self.execsql(sql, fetch=True, raiseerrors=True)
        except:
            return self.sendtraceback(self.advancedbotname, user, 'SQL: %r' % sql)   
        if rows is None:
            message = "SQL executed '%s', nothing returned" % sql
        else:
            message = ["SQL executed: '%s', returing:" % sql]
            for row in rows:
                message.append('\t'.join(['%r' % item for item in row]))
            message = '\n'.join(message)
        self.advancedbotreply(user, message)
        
    def scrubevents(self, eventtypeid):
        '''Remove old events from the database and in memory data structures'''
        curtime = int(time())
        for item, until in self.eventtypedict[eventtypeid].items():
            if until < curtime:
                del self.eventtypedict[eventtypeid][item]
        query = 'DELETE FROM activeevents WHERE eventtypeid = %i AND until < %i;' % (eventtypeid, curtime)
        self.addtask(self.execsql, query)
        
    def sendtraceback(self, sender, receiver, message = ''):
        '''Send traceback for error from sender to receiver as a private message'''
        excinfo = sys.exc_info()
        tb = self.escape(''.join(traceback.format_exception(*excinfo)))
        self.give_PrivateMessage(sender, receiver, ('Error in command: %s\n%s' % (message, tb)))
            
    def setlevel(self, user, level):
        '''Change the verbosity of the log messages sent to a user'''
        if user.op and user.nick in self.handlers:
            self.handlers[user.nick].setLevel(level)
            
    def setupdefaults(self, **kwargs):
        '''Setup defaults for the database, punishments, etc.'''
        super(AdvancedDCHub, self).setupdefaults(**kwargs)
        self.supers['AdvancedDCHub'] = super(AdvancedDCHub, self)
        self.reloadmodules.append('AdvancedDCHub')
        self.loglevels['sql'] = 10
        self.loglevels['torrent'] = 10
        self.dbquote = dbquote
        # Location of SQLite database
        self.dbfile = 'AdvancedDCHub.sqlite'
        self.dbtype = 'apsw'
        self.filelocations.append('dbfile')
        # Multiple task runners accessing the database can cause problems
        self.numtaskrunners = 1
        # Nick of AdvancedBot used with this hub
        self.advancedbotname = 'AdvancedBot'
        self.descriptionstart = ''
        self.messageuser = None
        self.restrictunverifiedusers = True
        self.dbconns = {}
        self.dbcursors = {}
        self.DCClientLogHandler = DCClientLogHandler
        self.bans, self.silences, self.stupidifies = {}, {}, {}
        self.handlers, self.oids, self.connectchecks = {}, {}, {}
        self.torrents = {}
        # Maximum number of rows returned in the history command
        self.maxhistoryrows = 100
        # How stupid to make the users sound if they have been stupidified
        # Note that at less than 5 it can be unreadable
        self.stupidfactor = 8
        # Amount of time to allow a user to send a ConnectToMe command to an
        # op after the op has sent a RevConnectToMe command to the user
        self.connectchecktime = 180
        self.historylines = ['You should not see this', 
            'Logged in on %(time)s from %(note)s',
            'You should not see this',
            'Ban change on %(time)s by <%(noteby)s>: %(note)s',
            'Silence change on %(time)s by <%(noteby)s>: %(note)s',
            'Stupidify change on %(time)s by <%(noteby)s>: %(note)s',
            'Verify change on %(time)s by <%(noteby)s>: %(note)s',
            'Note on %(time)s by <%(noteby)s>: %(note)s',
            ]
        # All times are sent in GMT format so they are portable across time zones
        self.historyftime = '%Y-%m-%d %H:%M:%S GMT'
        self.unescapetranstable = (('&#124;', '|'), ('\|', '&#124;'), ('\r\n', '\n'),
            ('&#36;', '$'), ('\$', '&#36;'))
        self.escapetranstable = (('\n', '\r\n'), ('|', '&#124;'), ('$', '&#36;'))
        self.timechars = {'s': 1, 'm':60, 'h':60*60, 'd':60*60*24, 'w':60*60*24*7, 
            'y':60*60*24*365}
        for char in self.timechars.keys():
            self.timechars[char.upper()] = self.timechars[char]
        # Mapping of event type ids to related data structures
        self.eventtypedict = {3:self.bans, 4:self.silences, 5:self.stupidifies}
        self.eventtypenames = 'NULL join NULL ban silence stupidify verify note'.split()
        # Unverified users can only use the following commands
        self.validusercommands = set('''_ChatMessage _PrivateMessage MyINFO GetINFO
            GetNickList ConnectToMe UserIP'''.split())
        self.validopcommands = set('OpForceMove Kick Close ReloadBots'.split())
        # Verified users can use these commands as well
        self.verifiedusercommands = set('Search SR RevConnectToMe'.split())
        if not self.restrictunverifiedusers:
            self.validusercommands |= self.verifiedusercommands
    
    def setuphub(self):
        self.supers['AdvancedDCHub'].setuphub()
        self.loadtorrents()
        self.loadpunishments()
        # The initial database connection is made in loadaccounts
        self.dbconnect(connect=False)
            
    def taskrunnerclose(self):
        '''Disconnect from the database on thread shutdown'''
        self.dbconnect(connect=False)
        self.supers['AdvancedDCHub'].taskrunnerclose()
            
    def taskrunnerinit(self):
        '''Create a separate database connection for each thread'''
        self.supers['AdvancedDCHub'].taskrunnerinit()
        self.dbconnect()
            
    def unescape(self, message):
        '''Unescape messages received from users.
        
        Generally not used for the reasons listed in the docstring for escape.
        '''
        for changethis, tothis in self.unescapetranstable:
            message = message.replace(changethis, tothis)
        return message
        
    def unenforceverification(self):
        '''Allow unverified users to search and connect to other users'''
        if not self.restrictunverifiedusers:
            return
        self.restrictunverifiedusers = False
        self.validusercommands |= self.verifiedusercommands
        for user in self.users.itervalues():
            if hasattr(user, 'verified') and not user.verified:
                user.validcommands |= self.verifiedusercommands
            
    def updateevent(self, entry, until, reason, op, user, eventtypeid):
        '''Update an event (punishment) to make it for a longer or shorter time'''
        curtime = int(time())
        self.eventtypedict[eventtypeid][entry] = until
        query = 'UPDATE activeevents SET until = %i WHERE eventtypeid = %i AND entry = %s;' % (until, eventtypeid, dbquote(entry))
        self.addtask(self.execsql, query)
        noteby, accountid = self.getoid(op), self.getoid(user)
        if accountid != 'NULL':
            query = 'INSERT INTO events (accountid, eventtypeid, time, noteby, note) VALUES (%i, %i, %i, %s, %s);' % (accountid, eventtypeid, curtime, noteby, dbquote('updated/%i/%s' % (until - curtime, reason)))
            self.addtask(self.execsql, statement)

    def verifyuser(self, user, verify = True):
        '''Mark a user as verified
        
        This allows the user to connect to other users and search the hub. It 
        asks for a password if the account doesn't currently have one.
        '''
        if verify:
            user.validcommands |= self.verifiedusercommands
        else:
            user.validcommands -= self.verifiedusercommands
        user.verified = verify
        if verify and user.nick in self.accounts and not self.accounts[user.nick]['password'] and self.advancedbotname in self.bots:
            self.give_PrivateMessage(self.advancedbotname, user, 'You have been verified.  Please use the Change Password command to give your account a password.  Or send a private message to %s in the form "password %%yourpassword%%" (e.g. sending the command "password rosebud" will change your password to rosebud).' % self.advancedbotname)
        
    def verifynick(self, nick, op, note, verify = True):
        '''Verify an account
        
        Also verifies the user if one is using the account.
        '''
        curtime = int(time())
        type = verify and 'verify' or 'unverify'
        self.accounts[nick]['verified'] = verify
        noteby, accountid = self.getoid(op), self.getoid(nick)
        query = 'UPDATE accounts SET verified = %i WHERE nick = %s;' % (verify, dbquote(nick))
        self.addtask(self.execsql, query)
        query = 'INSERT INTO events (accountid, eventtypeid, time, noteby, note) VALUES (%i, 6, %i, %i, %s);' % (accountid, curtime, noteby, dbquote('%s/%s' % (type, note)))
        self.addtask(self.execsql, query)
        if nick in self.users:
            self.verifyuser(self.users[nick], verify)

    # Commands from users
        
    def check_ChatMessage(self, user, nick, message, *args):
        '''Check the chat message and user for related punishments
        
        If the user is silenced, let them know that and disallow the message.
        If the user is stupidified, alter the message as appropriate
        '''
        curtime = int(time())
        for entry in ('%' + user.nick, user.ip):
            if entry in self.silences:
                if self.silences[entry] > curtime:
                    user.sendmessage('<Hub-Security> You are currently silenced.  Silence will be removed in %i seconds.|' % (self.silences[entry] - curtime))
                    return False
                del self.silences[entry]
            if entry in self.stupidifies:
                if self.stupidifies[entry] > curtime:
                    # Note: decreasing self.stupidfactor makes stupidified
                    # people seem stupider.
                    self.supers['AdvancedDCHub'].check_ChatMessage(user, nick, message, *args)
                    # Stupid people write things such as 'u r stupid'
                    message = message.replace(' you ',  ' u ').replace(' are ', ' r ')
                    # Stupdi epopleo ften trnaspose charcatesr
                    for i in range(random.randint(1, len(message))/self.stupidfactor):
                        idx = random.randint(2, len(message) - 3)
                        message = message[:idx] + message[idx+1] + message[idx] + message[idx+2:]
                    # Stupid people love excessive exclamations!!!!!!!!!!!!!!!!
                    message += '!' * (random.randint(1, len(message))/self.stupidfactor)
                    if random.random() < .1:
                        # sTUPID PEOPLE OFTEN TYPE IN ALL CAPS
                        message = message.swapcase()
                    return (nick, message, args)
                else:
                    del self.stupidifies[entry]
        self.supers['AdvancedDCHub'].check_ChatMessage(user, nick, message, *args)
        
    def checkConnectToMe(self, user, nick, ip, port, *args):
        '''Disallow connections to/from unverified users from non-ops
        
        Only allow connections to unverifed users from ops, and only allow
        connections from unverified users to ops if the ops has requested it
        via RevConnectToMe.
        '''
        self.supers['AdvancedDCHub'].checkConnectToMe(user, nick, ip, port, *args)
        if self.restrictunverifiedusers:
            receiver = self.users[nick]
            if not (hasattr(receiver, 'verified') and receiver.verified) and not user.op:
                raise ValueError, 'Non ops not allowed to connect to unverified users'
            if not user.verified and not (receiver.op and (user, receiver) in self.connectchecks):
                raise ValueError, 'Unverified users can only connect to ops if the op has requested it'
    
    def checkMyINFO(self, user, nick, description, tag, speed, speedclass, email, sharesize, *args):
        '''Disallow connections from NMDC clients
        
        It's possible to fake this, but people who do can be banned for long
        periods of time.
        '''
        if not tag or tag.startswith('<DC '):
            user.sendmessage('<Hub-Security> I\'m sorry, but NMDC is not allowed on this hub, because it allows you to be cloned.  Please use another client, such as DC++ (http://dcplusplus.sourceforge.net/).|')
            user.ignoremessages = True
            return False
        if ',S:0' in tag:
            user.ignoremessages = True
            return False
        self.supers['AdvancedDCHub'].checkMyINFO(user, nick, description, tag, speed, speedclass, email, sharesize, *args)

    def checkRevConnectToMe(self, user, sender, receiver, *args):
        '''Don't allow reverse connection requests to/from unverified users
        
        If the user is an op and the receiver is an unverified user, record
        the connect attempt to allow the ConnectToMe response.
        '''
        self.supers['AdvancedDCHub'].checkRevConnectToMe(user, sender, receiver, *args)
        receiver = self.users[receiver]
        curtime = int(time())
        if self.restrictunverifiedusers and not (hasattr(receiver, 'verified') and receiver.verified):
            if user.op:
                for key, value in self.connectchecks.items():
                    if value <= curtime:
                        del self.connectchecks[key]
                self.connectchecks[(receiver, user)] = curtime + self.connectchecktime
            else:
                raise ValueError, 'Non ops not allowed to connect to unverified users'

    def giveSearch(self, searcher, host, sizerestricted, isminimumsize, size, datatype, searchpattern):
        '''Give search message from searcher to all verified users'''
        message = '$Search %s %s?%s?%s?%s?%s|' % (host, sizerestricted, isminimumsize, size, datatype, searchpattern)
        if self.restrictunverifiedusers:
            for user in self.users.itervalues():
                if (hasattr(user, 'verified') and user.verified):
                    user.sendmessage(message)
        else:
            for user in self.users.itervalues():
                user.sendmessage(message)

    def checkValidateNick(self, user, nick, *args):
        '''Check that the user isn't banned'''
        checknick = '%' + nick
        if checknick in self.bans:
            if self.bans[checknick] > int(time()):
                user.sendmessage('<Hub-Security> You are currently banned from this hub.  You will be allowed to connect after %s.|' % self.formattime(self.bans[checknick]))
                raise ValueError, 'banned nick'
            self.removeevent(checknick, None, None, 3)
        self.supers['AdvancedDCHub'].checkValidateNick(user, nick, *args)
    
if __name__ == '__main__':
    run(AdvancedDCHub)
