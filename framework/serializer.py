# <COPYRIGHT_TAG>

"""
Wrapper class for serializer module
"""
import os
import pickle


class Singleton(type):
    _instances = {}

    def __call__(self, *args, **kwargs):
        if self not in self._instances:
            self._instances[self] = \
                super(Singleton, self).__call__(*args, **kwargs)
        return self._instances[self]


class Serializer(object):

    """
    Two-levels cache implementation for storing/retrieving any kind of object
    using using a key-value model. It uses the pickle module to store objects
    into a file.
    This class implements the Singleton pattern. Everytime its constructor
    is called it will return a reference to the same instance.
    """

    __metaclass__ = Singleton

    def __init__(self):
        self.volatile_cache = {}
        self.filename = 'serializer.cache'

    def save(self, object_name, object_to_save):
        """
        Saves an object into the volatile dictionary cache - which
        resides in memory.
        """
        self.volatile_cache[object_name] = object_to_save

    def load(self, object_name):
        """
        Loads and returns an object from the volatile cache.
        """
        return self.volatile_cache.get(object_name, None)

    def set_serialized_filename(self, filename):
        """
        Sets the name of the non-volatile cache file to be used in the future
        """
        self.filename = filename

    def save_to_file(self):
        """
        Saves the volatile cache to a file (non-volatile) using the pickle
        module. Returns True in case everything went OK, False otherwise.
        """
        try:
            serialized_file = open(self.filename, 'w')
            pickle.dump(self.volatile_cache, serialized_file)
            serialized_file.close()
            return True
        except:
            return False

    def load_from_file(self):
        """
        Reads from a pickle-like file using pickle module and populates the
        volatile cache. Returns True in case everything went OK, False
        otherwise.
        """
        try:
            serialized_file = open(self.filename, 'r')
            self.volatile_cache = pickle.load(serialized_file)
            serialized_file.close()
            return True
        except:
            self.volatile_cache.clear()
            return False

    def discard_cache(self):
        """
        Discards both volatile and non-volatile cache.
        """
        self.volatile_cache.clear()
        if os.path.exists(self.filename):
            os.remove(self.filename)
