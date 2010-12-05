import os
import facebook
import traceback,sys

class FBUser:  
    fbUtoken        = None
    fbUgraph        = None
    fbUser          = None
    fbFriendList    = None
    fbUself         = 'me'
    fbUfriends      = 'friends'
    fbUId           = 'id'
    fbUemail        = 'email'
    
    def __init__(self, access_token):
        """Initializes the class"""
        self.fbUtoken   = access_token
        self.fbUgraph   = facebook.GraphAPI(self.fbUtoken)
        
    def fetchFriends(self):
        try:
            if self.fbFriendList is None:
                self.fbFriendList = self.fbUgraph.get_connections(self.fbUself, self.fbUfriends)
        except:
            print 'Error validating token'
            traceback.print_exception(sys.exc_info()[ 0 ], sys.exc_info()[ 1 ], sys.exc_info()[ 2 ], limit=4)
            return None
        
        return self.fbFriendList
    
    def fetchEMail(self):
        try:
            if self.fbUser is None:
                self.fbUser    = self.fbUgraph.get_object(self.fbUself)
        except:
            print 'Error validating token'
            traceback.print_exception(sys.exc_info()[ 0 ], sys.exc_info()[ 1 ], sys.exc_info()[ 2 ], limit=4)
            return None
            
        return  self.fbUser['email']
    
    def fetchUid(self):
        try:
            if self.fbUser is None:
                self.fbUser    = self.fbUgraph.get_object(self.fbUself)
        except:
            print 'Error fetching UID'
            traceback.print_exception(sys.exc_info()[ 0 ], sys.exc_info()[ 1 ], sys.exc_info()[ 2 ], limit=4)
            return None
        
        return self.fbUser['id']