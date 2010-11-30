import os
import facebook

class FBUser:  
    fbUtoken    = None
    fbUgraph    = None
    fbUself     = 'me'
    fbUfriends  = 'friends'
    fbUId       = 'id'
    fbUemail    = 'email'
    
    def __init__(self, access_token):
        """Initializes the class"""
        self.fbUtoken   = access_token
        self.fbUgraph   = facebook.GraphAPI(self.fbUtoken)
        
    def fetchFriends(self):
        try:
            friendList = self.fbUgraph.get_connections(self.fbUself, self.fbUfriends)
        except:
            print 'Error validating token'
            return None
        
        return friendList
    
    def fetchEMail(self):
        try:
            user    = self.fbUgraph.get_object(self.fbUself)
        except:
            print 'Error validating token'
            return None
            
        return  user['email']
    
    def fetchUid(self):
        try:
            user    = self.fbUgraph.get_object(self.fbUself)
            print user
        except:
            print 'Error fetching UID'
            return None
        
        return user['id']