"""Bounded one-delivery transport, not a retrieval cache or persistent history."""
import threading,time
class TransientDisplay:
    def __init__(self,ttl=30):self.ttl=ttl;self._items={};self._lock=threading.RLock()
    def put(self,key,owner,value):
        with self._lock:
            if len(self._items)>=32:self._items.pop(next(iter(self._items)))
            marker=object();self._items[key]=(owner,time.monotonic()+self.ttl,value,marker)
        def expire():
            with self._lock:
                if key in self._items and self._items[key][3] is marker:self._items.pop(key,None)
        timer=threading.Timer(self.ttl,expire);timer.daemon=True;timer.start()
    def consume(self,key,owner):
        with self._lock:
            item=self._items.get(key)
            if not item or item[0]!=owner:return None
            self._items.pop(key,None)
            return item[2] if time.monotonic()<item[1] else None
