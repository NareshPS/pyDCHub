from DCHub import DCHub, run
from time import sleep, time
from thread import get_ident as threadid
import threading
from Queue import Queue

emptytask = lambda: None

class ThreadedDCHub(DCHub):
    '''Hub allowing multiple threads
    
    py-dchub is single threaded, which doesn't always mesh well with tasks that
    may block (file/socket reading/writing, database access, etc.).  This
    extension makes it possible to call functions that may block without
    stopping the execution of the hub itself.  If a function may block, instead
    of calling it directly using:
    
        function(*args, **kwargs)
    
    You add it to the task list using addtask:
    
        self.addtask(function, *args, **kwargs)
        
    The hub will execute the function in a separate thread at some later point.
    
    For performance reasons, the hub uses a thread pool, which by default has 5
    threads.  To change the number of threads, add numtaskrunners as a keyword
    argument when instantiating the hub (or to the configuration file).  To 
    change the number of threads, modify self.numtaskrunners.  New threads will
    be created or current threads deleted until the number of threads is equal
    to self.numtaskrunners.
    
    Note that this hub never uses the threads it creates.  To use them, you'll 
    need to subclass this hub or use bots designed with it in mind.
    '''      
    def addtask(self, function, *args, **kwargs):
        '''Add a task to the task queue and tell the task runner to execute it'''
        if not self.exittaskrunner and self.activetaskrunners  < self.numtaskrunners:
            self.log.log(self.loglevels['threading'], 'Fewer active threads (%i) than desired (%i), starting new thread' % (self.activetaskrunners, self.numtaskrunners))
            self.addtaskrunner()
        task = [function, args, kwargs]
        self.log.log(self.loglevels['threading'], 'Adding task to queue: %s' % str(task))
        self.tasks.put(task)
        
    def addtaskrunner(self):
        '''Add an additional task running thread
        
        If increment is True, increase the maximum number of task runners by 1
        '''
        taskrunner = threading.Thread(target=self.taskrunner)
        # The task runners run forever unless explicitly stopped, so have
        # the server exit without waiting for them to finish
        taskrunner.setDaemon(1)
        taskrunner.start()
        
    def cleanup(self):
        '''Wait for all active task runners to stop before exiting
        
        If the active task runners are taking too long, exit anyway.
        '''
        self.supers['ThreadedDCHub'].cleanup()
        curtime = time()
        while self.tasks.qsize() or self.activetaskrunners != self.waitingtaskrunners:
            sleep(.1)
            if time() > curtime + self.cleanuptime:
                self.log.warning('Cleanup taking too long, exiting')
                break
        self.exittaskrunner = True
        for i in range(self.activetaskrunners):
            self.addtask(emptytask)
                
    def handleconnections(self):
        '''Acquire the lock while handling connections'''
        self.rlock.acquire()
        try:
            ret = self.supers['ThreadedDCHub'].handleconnections()
        finally:
            self.rlock.release()
        return ret
        
    def handlereloaderror(self):
        '''Restart threads'''
        self.supers['ThreadedDCHub'].handlereloaderror()
        self.exittaskrunner = False
        
    def handletask(self, task):
        '''Process task'''
        task[0](*task[1], **task[2])
                
    def processcommands(self):
        '''Acquire the lock while processing commands'''
        self.rlock.acquire()
        try:
            ret = self.supers['ThreadedDCHub'].processcommands()
        finally:
            self.rlock.release()
        return ret
        
    def setupdefaults(self, **kwargs):
        '''Setup thread related defaults'''
        super(ThreadedDCHub, self).setupdefaults(**kwargs)
        self.supers['ThreadedDCHub'] = super(ThreadedDCHub, self)
        self.reloadmodules.append('ThreadedDCHub')
        self.threaddata = {threadid():{}}
        self.emptytask = emptytask
        self.cleanuptime = 5
        self.activetaskrunners = 0
        self.exittaskrunner = False
        self.waitingtaskrunners = 0
        self.numtaskrunners = 5
        self.tasks = Queue(0)
        self.rlock = threading.RLock()
        self.loglevels['threading'] = 8
        self.nonreloadableattrs.union_update('exittaskrunner waitingtaskrunners activetaskrunners tasks threaddata'.split())
        
    def taskrunner(self):
        '''Continuously process tasks that may block'''
        tid = threadid()
        self.log.log(self.loglevels['threading'], 'Thread %i started' % tid)
        self.taskrunnerinit()
        self.activetaskrunners += 1
        try:
            while self.activetaskrunners < self.numtaskrunners + 1 and not self.exittaskrunner:
                self.waitingtaskrunners += 1
                try:
                    self.log.log(self.loglevels['threading'], 'Thread %i waiting for tasks' % tid)
                    task = self.tasks.get(block=True)
                    strtask = str(task)
                    self.log.log(self.loglevels['threading'], 'Thread %i got task %s' % (tid, strtask))
                finally:
                    self.waitingtaskrunners -= 1
                try:
                    self.handletask(task)
                except:
                    self.log.exception('Serious error in thread %i while handling task %s' % (tid, strtask))
                else:
                    self.log.log(self.loglevels['threading'], 'Thread %i executed task %s without raising an exception' % (tid, strtask))
        finally:
            self.activetaskrunners -= 1
            self.taskrunnerclose()
            self.log.log(self.loglevels['threading'], 'Thread %i exiting' % tid)
            
    def taskrunnerclose(self):
        '''Preform the necessary actions on thread shutdown'''
        del self.threaddata[threadid()]
        
    def taskrunnerinit(self):
        '''Preform the necessary actions on thread startup'''
        self.threaddata[threadid()] = {}

if __name__ == '__main__':
    run(ThreadedDCHub)
