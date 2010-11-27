'''Create the SQLite database necessary for AdvancedDCHub'''
try:
    from pysqlite2 import dbapi2 as sqlite
except ImportError:
    import apsw
    def CreateAdvancedDCHubDB(sqlfile = 'AdvancedDCHub.sql', dbfile = 'AdvancedDCHub.sqlite'):
        '''Create the schema necessary for use of AdvancedDCHub'''
        db = apsw.Connection(dbfile).cursor().execute(file(sqlfile).read())
    except ImportError:
        import sqlite
        def CreateAdvancedDCHubDB(sqlfile = 'AdvancedDCHub.sql', dbfile = 'AdvancedDCHub.sqlite'):
            '''Create the schema necessary for use of AdvancedDCHub'''
            db = sqlite.connect(dbfile)
            db.cursor().execute(file(sqlfile).read())
            db.commit()
else:
    def CreateAdvancedDCHubDB(sqlfile = 'AdvancedDCHub.sql', dbfile = 'AdvancedDCHub.sqlite'):
        '''Create the schema necessary for use of AdvancedDCHub'''
        db = sqlite.connect(dbfile)
        dbc = db.cursor()
        for statement in file(sqlfile).read().split(';'):
            dbc.execute(statement)
        db.commit()

    
if __name__ == '__main__':
    CreateAdvancedDCHubDB()
