# cache
from abc import ABC, abstractmethod
from collections import deque
import time

class StorageFullException(Exception):
    pass

class BaseStorage(ABC):
    def __init__(self, capacity=float('inf')):
        self.capacity = capacity
    @abstractmethod
    def put(self, key, value):
        pass
    @abstractmethod
    def get(self, key):
        pass
    
    @abstractmethod
    def remove(self, key):
        pass
    
class HashMapBasedStorage(BaseStorage):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.db = {}
        
    def put(self, key, value):
        
        if len(self.db) == self.capacity:
            raise StorageFullException('Storage full')
        self.db[key] = value
        
    def get(self, key):
        return self.db[key]
    
    def remove(self, key):
        del self.db[key]
    
class BaseKeyAccessPolicy(ABC):
    @abstractmethod
    def key_accessed(self, key):
        pass
    @abstractmethod
    def key_to_remove(self):
        pass

class Node:
    def __init__(self, val, prev=None, next=None):
        self.val = val
        self.prev = prev
        self.next = next
        
class LL:
    def __init__(self, head=None, tail=None):
        self.head = head
        self.tail = tail
    def make_node_head(self, node):
        if node == self.head:
            return
        if self.head is None:
            self.head = self.tail = node
            self.head.next = self.tail
            self.tail.prev = self.head
        else:
            if node.prev is None and node.next is None:
                prev_head = self.head
                node.next = self.head
                self.head.prev = node
                self.head = node
            elif node.next is None: # i.e. tail
                node.prev.next = None
                self.tail = node.prev
                node.prev = node.next = None
                self.make_node_head(node)
            else:
                prev = node.prev
                next = node.next
                prev.next = next
                next.prev = prev
                node.prev = node.next = None
                self.make_node_head(node)
                 
    def key_to_remove(self):
        if self.head == self.tail:
            temp = self.head
            self.head = self.tail = None
            return temp
        temp = self.tail
        self.tail.prev.next = None
        self.tail = self.tail.prev
        return temp
        
class LRUKeyAccessPolicy(BaseKeyAccessPolicy):
    def __init__(self):
        self.hashmap = {}
        self.ll = LL()
    def key_accessed(self, key):
        if key in self.hashmap:
            self.ll.make_node_head(self.hashmap[key])
        else:
            node = Node(key)
            self.hashmap[key] = node
            self.ll.make_node_head(node)
            
    def key_to_remove(self):
        tail = self.ll.key_to_remove()
        del self.hashmap[tail.val]
        return tail.val

class Response(ABC):
    def __init__(self, value, time_took=0.0):
        self.value = value
        self.time_took= time_took
        
    def __repr__(self):
        return f'value={self.value}, time_took={self.time_took}'
        
class ReadResponse(Response):
    pass

class WriteResponse(Response):
    pass

class Cache:
    def __init__(self, storage:BaseStorage, key_access_policy: BaseKeyAccessPolicy):
        self.storage = storage
        self.key_access_policy = key_access_policy
        
    def put(self, key, value):
        try:
            self.storage.put(key, value)
            self.key_access_policy.key_accessed(key)
        except StorageFullException:
            key_to_be_removed = self.key_access_policy.key_to_remove()
            self.storage.remove(key_to_be_removed)
            self.put(key, value)
            self.key_access_policy.key_accessed(key)
        
    def get(self, key):
        value = self.storage.get(key)
        return value
      
 

# multilevel cache
class BasecacheLevel(ABC):
    @abstractmethod
    def get(self, key):
        pass
    @abstractmethod
    def put(self, key, value):
        pass
    
class CacheLevel(BasecacheLevel):
    def __init__(self, name, cache_provider:Cache, next:BasecacheLevel=None):
        self.name = name
        self.cache_provider = cache_provider
        self.next = next
        
    def get(self, key):
        t1 = time.time()
        try:
            value = self.cache_provider.get(key)
            t2 = time.time()
            return ReadResponse(value, t2-t1)
            
        except KeyError as e:
            print(f'unable to find in {self.name}, going to next')
            if self.next is None:
                raise e
            else:
                value = self.next.get(key)
                self.cache_provider.put(key, value)
                t2 = time.time()
                return ReadResponse(value, t2-t1)
                
    def put(self, key, value):
        t1 = time.time()
        self.cache_provider.put(key, value)
        if self.next is not None:
            self.next.put(key, value)
            
        t2 = time.time()
        return WriteResponse(None, t2-t1)
        



class MultilevelCache:
    def __init__(self, front_cache_level:CacheLevel=None, last_num_stat=5):
        self.front_cache_level = front_cache_level
        self.get_queue = deque(maxlen=last_num_stat)
        self.put_queue = deque(maxlen=last_num_stat)
        
    def add_cache_level(self, cache_level:CacheLevel):
        if self.front_cache_level is None:
            self.front_cache_level = cache_level
        else:
            current= self.front_cache_level
            while(current.next):
                current = current.next
            current.next = cache_level
    def get(self, key):
        read_response = self.front_cache_level.get(key)
        self.get_queue.appendleft(read_response)
        return read_response.value
    
    def put(self, key, value):
        write_response = self.front_cache_level.put(key, value)
        self.put_queue.appendleft(write_response)
        
        
        
if __name__ == '__main__':
  mlcache = MultilevelCache()
  L1 = CacheLevel('L1', Cache(HashMapBasedStorage(5), LRUKeyAccessPolicy()))
  L2 = CacheLevel('L2', Cache(HashMapBasedStorage(5), LRUKeyAccessPolicy()))
  L3 = CacheLevel('L3', Cache(HashMapBasedStorage(5), LRUKeyAccessPolicy()))

  mlcache.add_cache_level(L1)
  mlcache.add_cache_level(L2)
  mlcache.add_cache_level(L3)
  
  for i in 'abcdef':
    mlcache.put(i, ord(i))
    
  mlcache.get('a')
