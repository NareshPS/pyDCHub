import FBDBConnect
import FBUser
import sys
import traceback

class FBConnect:
    
    fbUser          = None
    fbAccessToken   = None
    
    def __init__(self, db_filename):
        self.db_filename    = db_filename
        self.db_conn        = None
        
    def dbConnect(self):
        if self.db_conn is None:
            try:
                self.db_conn    = FBDBConnect.FBDBConnect(self.db_filename)
            except:
                print 'Exception in function: '
                traceback.print_exception(sys.exc_info()[ 0 ], sys.exc_info()[ 1 ], sys.exc_info()[ 2 ], limit=4)
                
    def getAccessToken(self, randomToken):
        
        if self.fbAccessToken is None:
            try:
                if self.db_conn is None:
                    self.dbConnect()
                
                userTuple   = self.db_conn.FBDBQuery(randomToken)
                
                if userTuple is not None:
                    self.fbAccessToken  = userTuple[ 2 ]
            except:
                print 'Exception in function: '
                traceback.print_exception(sys.exc_info()[ 0 ], sys.exc_info()[ 1 ], sys.exc_info()[ 2 ], limit=4)
                
        return self.fbAccessToken
    
    def getFBUser(self, randomToken):
        
        if self.fbUser is None:
            try:
                accessToken = self.getAccessToken(randomToken)
                self.fbUser = FBUser.FBUser(accessToken)
            except:
                print 'Exception in function: '
                traceback.print_exception(sys.exc_info()[ 0 ], sys.exc_info()[ 1 ], sys.exc_info()[ 2 ], limit=4)
                
        return self.fbUser
        
    def fetchFriends(self, randomToken):
            return self.getFBUser(randomToken).fetchFriends()
        
    def fetchEMail(self, randomToken):
        return self.getFBUser(randomToken).fetchEMail()