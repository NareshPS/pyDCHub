from DCHub import DCHub, run

class PrivateDCHub(DCHub):
    '''Hub allowing only users with valid accounts
    
    If a user does not have a valid account, they are denied access to the hub.
    '''        
    def setupdefaults(self, **kwargs):
        super(PrivateDCHub, self).setupdefaults(**kwargs)
        self.supers['PrivateDCHub'] = super(PrivateDCHub, self)
        self.reloadmodules.append('PrivateDCHub')
    
    def checkValidateNick(self, user, nick):
        '''Don't allow logins without a valid account'''
        if nick not in self.accounts:
            raise ValueError, 'nick not a valid account'
        self.supers['PrivateDCHub'].checkValidateNick(user, nick)
    
if __name__ == '__main__':
    run(PrivateDCHub)
