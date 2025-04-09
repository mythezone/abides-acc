
class Singleton:
    _instances = {}

    def __new__(cls, *args, **kwargs):
        if cls not in cls._instances:
            instance = super(Singleton, cls).__new__(cls)
            instance.__init__(*args, **kwargs)
            instance._initialized = True 
            cls._instances[cls] = instance
            
        return cls._instances[cls]
    
