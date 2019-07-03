import json
import sqlite3

from .base import Task

sqlite3.register_adapter(dict, lambda o: json.dumps(o))
sqlite3.register_converter("JSON", lambda o: json.loads(o))
sqlite3.register_adapter(bool, int)
sqlite3.register_converter("BOOLEAN", lambda v: bool(int(v)))

class Storage:
    def init_storage(self, *args, **kargs):
        raise NotImplementedError

    def recover(self):
        return {}

    def save_task(self, *args, **kargs):
        raise NotImplementedError

    def get_task(self, *args, **kargs):
        raise NotImplementedError

    def count_task(self, *args, **kargs):
        raise NotImplementedError

    def task_done(self, *args, **kargs):
        raise NotImplementedError

    def close(self):
        raise NotImplementedError


class SqliteStorage(Storage):

    def __init__(self, dbname=None):

        dbname = dbname if dbname else "spider.db"

        self.db = sqlite3.connect(dbname, detect_types=sqlite3.PARSE_COLNAMES | sqlite3.PARSE_DECLTYPES)
        self.db.row_factory = sqlite3.Row
        self.cursor = self.db.cursor()
        self.init_storage()

    def close(self):
        try:
            self.cursor.close()
            self.db.close()
        except:
            pass

    def init_storage(self, *args, **kargs):
        self.cursor.executescript('''
        create table if not exists task(
            task_id text PRIMARY KEY,
            task_type integer,
            done integer,
            content text
        );

        CREATE UNIQUE INDEX
            IF NOT EXISTS
            task_id on task (task_id);
        '''
                                  )
        self.db.commit()

    def recover(self):
        self.cursor.execute('select task_type, count(*) as "count" from task where done = 0 group by task_type ')
        _types = self.cursor.fetchall()
        return dict([(t["task_type"], t["count"]) for t in _types])

    def save_task(self, task: Task):
        self.cursor.execute("INSERT OR IGNORE INTO task(task_id, content, task_type, done) values(:task_id, :content, :task_type, :done);", task.encode())
        self.db.commit()

    def get_task(self, *args, **kargs):
        task_type = kargs.get("task_type", 0)
        if not task_type:
            return None
        rows = self.cursor.execute(
            'select task_type, task_id, done as "done[BOOLEAN]", content as "content[JSON]" from task where task_type = ? and done = 0 limit 1', (task_type,))
        result = rows.fetchone()
        if result:
            return Task.decode(dict(result))

    def count_task(self, *args, **kargs):
        task_type = kargs.get("task_type", 0)
        rows = self.cursor.execute("select count(*) as 'task_count' from task where done = 0 and task_type=:type", {"type": task_type})
        result = rows.fetchone()
        return result['task_count']

    def task_done(self, *args, **kargs):
        task_id = kargs.get("task_id", None)
        if not task_id:
            return
        self.cursor.execute("UPDATE task set done=1 where task_id=:task_id;", {"task_id": task_id})
        self.db.commit()
