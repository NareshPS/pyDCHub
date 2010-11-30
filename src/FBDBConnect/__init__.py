from sqlite3 import dbapi2
import sys, traceback
import os

class FBDBConnect:
    db_filename     = None
    db_conn         = None
    db_prepStmnt    = 'SELECT * from records where random_token=%s'
    
    def __init__(self, filename):
        
        self.db_filename    = filename
        
        if len(self.db_filename) > 0:
            if os.path.isfile(self.db_filename):
                try:        
                    self.db_conn    = dbapi2.connect(self.db_filename)
                except:
                    print 'Exception in function: '
                    traceback.print_exception(sys.exc_info()[ 0 ], sys.exc_info()[ 1 ], sys.exc_info()[ 2 ], limit=4)
            else:
                self.FBDBCreate()
        else:
            print 'Invalid File Name'
        
    def FBDBCreate(self):
        try:
            self.db_conn    = dbapi2.connect(self.db_filename)
            cur             = self.db_conn.cursor()
            query           = cur.execute('CREATE TABLE records ( uid VARCHAR(20) PRIMARY KEY, random_token VARCHAR(20), access_token VARCHAR(20),session VARCHAR(20), expiry INTEGER)')
            if query is None:
                print 'Error creating database.'
        except:
            print 'Exception in function: '
            traceback.print_exception(sys.exc_info()[ 0 ], sys.exc_info()[ 1 ], sys.exc_info()[ 2 ], limit=4)
        
        
    def FBDBQuery(self, randomToken):     
        dict    = None
        if self.db_conn is not None:
            try:
                cur     = self.db_conn.cursor()
                query   = (self.db_prepStmnt)%randomToken
                cur.execute(query)
                row = cur.fetchone()
                
                return row
                
            except:
                print 'Exception in function: '
                traceback.print_exception(sys.exc_info()[ 0 ], sys.exc_info()[ 1 ], sys.exc_info()[ 2 ], limit=4)
        else:
            print 'Connection not open'
            
    def FBDBClose(self):
        if self.db_conn is not None:
            self.db_conn.close()