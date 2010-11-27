import sys
import traceback
import logging
import DCHub

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

class LogBot(DCHub.DCHubBot):
    '''Remote logging bot, allowing ops to register and receive log messages
    
    To register to receive log messages, an op should private message the bot
    with the command start.  To stop receiving messages, an op should private
    message the bot with the command stop. An op can change the logging level 
    (verbosity) by private messaging the bot the command level X, where X is
    the numeric verbosity level (10 - Debug, 20 - Info, etc.).  An op can set
    the initial level by adding a level to the start command (e.g. start 20).
    
    The bot closes all log handlers it has opened when it is reloaded, so after
    reloading the bots, ops that want to continue to receive logging messages
    should resend the start command.
    '''
    
    def __init__(self, hub, nick = 'LogBot'):
        DCHub.DCHubBot.__init__(self, hub, nick)
        self.handlers = {}
        self.execbefore['removeuser'] = self.removeloghandler
                
    def close(self):
        '''Close all handlers that the bot has opened'''
        for handler in self.handlers.values():
            self.hub.log.removeHandler(handler)
        
    def processcommand(self, user, command):
        '''Add/Remove/Change verbosity of log messages sent to users'''
        if not user.op:
            return
        if command.startswith('start'):
            if user.nick not in self.handlers:
                self.handlers[user.nick] = DCClientLogHandler(user, self)
                self.hub.log.addHandler(self.handlers[user.nick])
            try:
                level = int(command[6:])
            except ValueError:
                pass
            else:
                self.setlevel(user, level)
                
        elif command == 'stop':
            self.removeloghandler(user)
        elif command.startswith('level'):
            try:
                level = int(command[6:])
            except ValueError:
                pass
            else:
                self.setlevel(user, level)
                
    def removeloghandler(self, user):
        '''Remove logging handlers for ops that have left the hub'''
        if user.nick in self.handlers and user.loggedin:
            self.hub.log.removeHandler(self.handlers[user.nick])
            del self.handlers[user.nick]
            
    def setlevel(self, user, level):
        '''Change the verbosity of the log messages sent to a user'''
        if user.nick in self.handlers and user.loggedin:
            self.handlers[user.nick].setLevel(level)
