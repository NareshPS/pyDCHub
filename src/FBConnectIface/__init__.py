import FBConnect
import sys, traceback

class FBConnectIface:
    
    def __init__(self):
        try:
            self.db_filename    = 'C:/Stuffs/www/db.sqlite'
            self.fbconn         = FBConnect.FBConnect(self.db_filename)
        except:
            print 'Exception in function: '
            traceback.print_exception(sys.exc_info()[ 0 ], sys.exc_info()[ 1 ], sys.exc_info()[ 2 ], limit=4)
        
    def fetchFriends(self, randomToken):
        print self.fbconn.fetchFriends(randomToken)
        
    def isValidToken(self, randomToken):
        if self.fbconn.getAccessToken(randomToken) is not None:
            return True
        
        return False