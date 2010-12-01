'''
Created on Nov 29, 2010

@author: Naresh
'''
import FBConnect
import sys

db_filename     = 'C:/Stuffs/www/db.sqlite'
if __name__ == '__main__':
    try:
        fbconn  = FBConnect.FBConnect(db_filename)
        print fbconn.fetchFriends('18604')
    except:
        print sys.exc_info()
        print 'Exception', __name__
    