import FBConnect
import sys, traceback

class FBConnectIface:
    
    def __init__(self, randomToken):
        try:
            self.db_filename    = 'C:/Stuffs/www/db.sqlite'
            self.fbconn         = FBConnect.FBConnect(self.db_filename)
            self.randomToken    = randomToken
        except:
            print 'Exception in function: '
            traceback.print_exception(sys.exc_info()[ 0 ], sys.exc_info()[ 1 ], sys.exc_info()[ 2 ], limit=4)
        
    def fetchFriends(self):
        print self.fbconn.fetchFriends(self.randomToken)
        
    def isValidToken(self):
        if self.fbconn.getAccessToken(self.randomToken) is not None:
            return True
        
        return False
    
    def fetchUid(self):
        return self.fbconn.getFBUser(self.randomToken).fetchUid()