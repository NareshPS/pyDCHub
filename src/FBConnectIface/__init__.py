import FBConnect
import sys, traceback

class FBConnectIface:
    friendsList     = None
    uid             = None
    fbconn          = None
    
    def __init__(self, randomToken):
        try:
            self.db_filename    = 'C:/Stuffs/www/db.sqlite'
            self.fbconn         = FBConnect.FBConnect(self.db_filename)
            self.randomToken    = randomToken
        except:
            print 'Exception in function: '
            traceback.print_exception(sys.exc_info()[ 0 ], sys.exc_info()[ 1 ], sys.exc_info()[ 2 ], limit=4)
        
    def fetchFriends(self):
        self.friendsList    = self.fbconn.fetchFriends(self.randomToken)['data']
        return self.friendsList
    
    def isFriend(self, uid):
        friendRet   = False
        try:
            for friend in self.fetchFriends():
                if friend[ 'id' ] == uid:
                    friendRet   = True
        except ValueError:
            friendRet   = False
        except:
            friendRet   = False
            
        print friendRet
            
        return friendRet
        
    def isValidToken(self):
        if self.fbconn.getAccessToken(self.randomToken) is not None:
            return True
        
        return False
    
    def fetchUid(self):
        self.uid        = self.fbconn.getFBUser(self.randomToken).fetchUid() 
        return self.uid