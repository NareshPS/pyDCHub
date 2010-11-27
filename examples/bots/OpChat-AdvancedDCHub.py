import DCHub

class OpChat(DCHub.DCHubBot):
    '''Bot allowing a private chat between the ops
    
    Users can send messages to OpChat, and those messages are relayed to all
    of the ops.  Ops can choose to respond to a specific user by starting their
    private message to OpChat with #usersnick#.  Then the message will get sent
    to that user as well as the other ops (the message to the other user will
    appear to be sent from OpChat).  To avoid having to type #usersnick# over
    and over, you can use ## as a shortcut to send the message to the last user
    specified via #usersnick#.  To check what ## is set to, use #%#.
    
    This version of OpChat uses AdvancedDCHub to keep track of the ## user,
    so it doesn't require any function wrapping/unwrapping.
    '''
    def __init__(self, hub, nick = 'OpChat'):
        DCHub.DCHubBot.__init__(self, hub, nick)
        
    def processcommand(self, user, command):
        '''Send message to all ops'''
        if command.startswith('#') and user.op:
            try:
                nick, message = command[1:].split('#', 1)
                if nick == '':
                    if self.hub.messageuser is not None:
                        command = '#%s# %s' % (nick, message)
                        self.hub.give_PrivateMessage(self, self.hub.messageuser, '%s' % message)
                    else:
                        return self.hub.give_PrivateMessage(self, user, '* ## is unset')
                elif nick == '%':
                    if self.hub.messageuser is None:
                        return self.hub.give_PrivateMessage(self, user, '* ## is unset')
                    return self.hub.give_PrivateMessage(self, user, '## -> %s' % self.hub.messageuser.nick)
                elif nick in self.hub.users:
                    self.hub.messageuser = self.hub.users[nick]
                    command = '#%s# %s' % (nick, message)
                    self.hub.give_PrivateMessage(self, self.hub.messageuser, '%s' % message)
                else:
                    return self.hub.give_PrivateMessage(self, user, '* #%s# is not logged on' % nick)
            except ValueError:
                pass
        for op in self.hub.ops.itervalues():
            if op is not user:
                op.sendmessage('$To: %s From: %s $<%s> %s|' % (op.nick, self.nick, user.nick, command))
