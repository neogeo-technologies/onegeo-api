from threading import Thread


class Singleton(type):

    __instances = {}

    def __call__(cls, *args, **kwargs):
        if cls not in cls.__instances:
            cls.__instances[cls] = super().__call__(*args, **kwargs)
        return cls.__instances[cls]


class FuncThread(Thread):

    def __init__(self, target, *args, **kwargs):
        self.target = target
        self.args = args
        self.kwargs = kwargs
        Thread.__init__(self)
 
    def run(self):
        self._target(*self.args, **self.kwargs)


class Promise:
 
    def __init__(self):
        self.callbacks = []
 
    def then(self, callback, *args, **kwargs):
        self.callbacks.append(callback)

    def resolve(self, result):
        print(result)
        while self.callbacks:
            result = self.callbacks.pop(0)(result)
            if isinstance(result, Promise):
                result.then(self.resolve)
                break