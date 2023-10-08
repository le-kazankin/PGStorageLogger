#!/bin/python3

# begin import region
import uuid
import psycopg2
from psycopg2 import sql
import os
import socket
import datetime
# end import region

class PGStorageLogger:
    def __init__(self, application_name:str, db:str, db_user:str, db_password:str, 
                 db_host:str, db_port:int = 5432, level_limit:str = 'info', proc_uuid:str = '', 
                 hostname:str = '', ip: str = '', pid:int = 0, days_store:int=7) -> None:
        """Constructor of PGStorageLogger.
            Args:
                application_name (str, required) - name of Your application;
                db (str, required) - name of Youe database in PG where logs will be store;
                db_user (str, required) - PG username who granted to create/drop/insert schema, tables;
                db_password (str, required) - password of PG user;
                db_host (str, required) - server with PostgreSQL;
                db_port (str, optional) - port of PostgreSQL. (default 5432);
                level_limit (str, optional) - the logging level above which logs will not be saved. Info default;
                proc_uuid (uuid, optional) - random uuid, that can help You to see a call chain;
                hostname (str, optional) - machine name where script is running on;
                ip (text, optional) - ip local machine or an external request;
                pid (int, optional) - id of running process.
                days_store(int, optional) - how long to store logs in days (instance of the class with lower num has priority).
            
            Return:
                None
        """        
        try:
            self.connection = psycopg2.connect(user=db_user,
                                               password=db_password,
                                               host=db_host,
                                               port=db_port,
                                               database=db)
            cursor = self.connection.cursor()
            cursor.execute("CREATE SCHEMA IF NOT EXISTS pgstorelog")
            cursor.execute("""
                           CREATE TABLE IF NOT EXISTS pgstorelog.logs
                           (
                           "timestamp" timestamp without time zone,
                           application_name text,
                           hostname text,
                           ip text,
                           level text,
                           proc_uuid uuid,
                           pid integer,
                           call_uuid uuid,
                           dpid integer,
                           message text
                           )
                           PARTITION BY RANGE ("timestamp")
                           """)
            self.connection.commit()
            cursor.close()
        except Exception as e:
            print('Connection PG Error: {}'.format(e))
            quit()

        self.application_name = application_name
        self.level_limit = level_limit
        self.proc_uuid = proc_uuid
        self.hostname = hostname
        self.ip = ip
        self.pid = pid

        self.list_not_drop_sections = []
        counter = 0
        while abs(days_store) > counter:
            datetime_section_ts = datetime.datetime.now() - datetime.timedelta(days=counter)
            self.list_not_drop_sections.append('logs{}'.format(datetime_section_ts.strftime('_%d%m%Y')))
            counter += 1

        if (self.proc_uuid == ''): self.proc_uuid = str(uuid.uuid4())
        if (self.hostname == ''): self.hostname = socket.gethostname()
        if (self.pid == 0): self.pid = os.getpid()

    def InsertLog(self, message:str, level:str = 'info', call_uuid:str = '', dpid:int = 0) -> str:
        """Insert log to PG.
            Args:
                message (str, required) - message You want to store;
                level (str, optional) - log level, that can help You to store only important logs;
                call_uuid (uuid, optional) - random uuid, that can help You to see a call chain;
                dpid (int, optional) - id of running process.
            
            Return:
                [str] - UUID that can be helpful to find log.
                      - 'False' - if log was't be inserted because of level_limit
        """
        j_level = {"debug": 1, "info": 2, "warn":3, "error": 4, "crit": 5}
        log_level_limit = j_level[self.level_limit]
        log_level = j_level[level]
        if (log_level_limit > log_level):
            return 'False'
        if (call_uuid == ''): call_uuid = str(uuid.uuid4())
        if (dpid == 0): dpid = os.getpid()
        str_section_name = self.GetCurrentSection()
        cursor = self.connection.cursor()
        cursor.execute("""
                    INSERT INTO pgstorelog.logs VALUES (
                    %(timestamp_cur)s, %(application_name)s, %(hostname)s, %(ip)s, %(level)s, %(proc_uuid)s, 
                    %(pid)s, %(call_uuid)s, %(dpid)s, %(message)s
                    )
                    """,
                    {
                        "timestamp_cur": datetime.datetime.now(),
                        "application_name": self.application_name,
                        "hostname": self.hostname,
                        "ip": self.ip,
                        "level": level,
                        "proc_uuid": self.proc_uuid,
                        "pid": self.pid,
                        "call_uuid":call_uuid,
                        "dpid":dpid,
                        "message":message
                    })
        cursor.close()
        self.connection.commit()
        self.DeleteOldSection()
        return call_uuid

    def GetCurrentSection(self) -> str:
        """Create if not exists and return current section name.
            Args:
                None
            
            Return:
                [str] - current section name.
        """
        str_section_name = 'logs{}'.format(datetime.datetime.now().strftime('_%d%m%Y'))
        str_timestamp_start = '{} 00:00:00.000001+00'.format(datetime.datetime.now().strftime('%Y-%m-%d'))
        dt_nextday = datetime.datetime.now() + datetime.timedelta(days=1)
        str_timestamp_end = '{} 00:00:00.000000+00'.format(dt_nextday.strftime('%Y-%m-%d'))
        cursor = self.connection.cursor()
        cursor.execute(
            sql.SQL("""
                CREATE TABLE IF NOT EXISTS pgstorelog.{} PARTITION OF pgstorelog.logs
                FOR VALUES FROM (%(timestamp_start)s) TO (%(timestamp_end)s)
                """).format(sql.Identifier(str_section_name)),
                {
                    "timestamp_start":str_timestamp_start, 
                    "timestamp_end":str_timestamp_end
                })
        cursor.close()
        self.connection.commit()
        return str_section_name

    def DeleteOldSection(self) -> bool:
        """Delete old sections according to days_store.
            Args:
                None
            
            Return:
                [bool] - True if old sections were deleted successfully.
                       - False if smth went wrong.
        """
        cursor = self.connection.cursor()
        cursor.execute("""
                       SELECT table_name FROM information_schema.tables
                       WHERE table_schema = 'pgstorelog' AND table_name LIKE 'logs_%'
                       """)
        list_sections = cursor.fetchall()
        for section in list_sections:
            if section[0] not in self.list_not_drop_sections:
                cursor.execute(
                    sql.SQL("""
                            DROP TABLE IF EXISTS pgstorelog.{}
                            """).format(sql.Identifier(section[0])))
                self.connection.commit()
        cursor.close()
        return True

    # short call region
    def Debug(self, message:str) -> str:
        """Insert log to PG with debug level. Like InsertLog, but other arguments will be default.
            Args:
                message (str, required) - message You want to store;
            
            Return:
                [str] - UUID that can be helpful to find log.
                      - 'False' - if log was't be inserted because of level_limit
        """
        return self.InsertLog(message, 'debug')
    
    def Info(self, message:str) -> str:
        """Insert log to PG with info level. Like InsertLog, but other arguments will be default.
            Args:
                message (str, required) - message You want to store;
            
            Return:
                [str] - UUID that can be helpful to find log.
                      - 'False' - if log was't be inserted because of level_limit
        """
        return self.InsertLog(message, 'info')

    def Warn(self, message:str) -> str:
        """Insert log to PG with warn level. Like InsertLog, but other arguments will be default.
            Args:
                message (str, required) - message You want to store;
            
            Return:
                [str] - UUID that can be helpful to find log.
                      - 'False' - if log was't be inserted because of level_limit
        """
        return self.InsertLog(message, 'warn')
    
    def Error(self, message:str) -> str:
        """Insert log to PG with error level. Like InsertLog, but other arguments will be default.
            Args:
                message (str, required) - message You want to store;
            
            Return:
                [str] - UUID that can be helpful to find log.
                      - 'False' - if log was't be inserted because of level_limit
        """
        return self.InsertLog(message, 'error')
    
    def Crit(self, message:str) -> str:
        """Insert log to PG with crit level. Like InsertLog, but other arguments will be default.
            Args:
                message (str, required) - message You want to store;
            
            Return:
                [str] - UUID that can be helpful to find log.
                      - 'False' - if log was't be inserted because of level_limit
        """
        return self.InsertLog(message, 'crit')
    # end region
    
if __name__ == '__main__':
    print("""Please, do not use this as a main file. You have to import this module to Your code. 
          See example on https://github.com/le-kazankin/PGStorageLogger/example.py""")