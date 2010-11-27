import sys
import traceback
import DCHub

class PythonBot(DCHub.DCHubBot):
    '''Bot allowing users to submit python commands to the hub
    
    If users have an account with 'PythonBot' in its args, they can send a 
    private message to the bot containing python commands, which the bot will
    run.  Note that DCHub is single threaded, so if you want to call a function
    that may block, you should be running ThreadedDCHub and use hub.addtask.
    
    There are user commands that make submitting simple commands and reloading
    bots easy in the examples/usercommands file.
    '''
    
    def __init__(self, hub, nick = 'PythonBot'):
        DCHub.DCHubBot.__init__(self, hub, nick)
        self.translate = (('&#124;', '|'), ('\|', '&#124;'), ('\r\n', '\n'),
            ('&#36;', '$'), ('\$', '&#36;'))
        self.untranslate = (('\n', '\r\n'), ('|', '&#124;'), ('$', '&#36;'))
        
    def processcommand(self, user, command):
        '''Execute Python commands given by users'''
        hub = self.hub
        for changethis, tothis in self.translate:
            command = command.replace(changethis, tothis)
        if user.loggedin and user.account is not None \
          and user.account['args'].find('PythonBot') != -1:
            try:
                exec command
            except:
                hub.debugexception('Error in Python command from %s' % user.idstring)
                excinfo = sys.exc_info()
                message = ''.join(traceback.format_exception(*excinfo))
                for changethis, tothis in self.untranslate:
                    message = message.replace(changethis, tothis)
                hub.give_PrivateMessage(self, user, ('Error in Python command:\n%s' % message))
