import os
import time
from functools import wraps

TIMING = os.getenv("MEASURE_TIME", 0)


class Decorators:
    @staticmethod
    def timing(func):
        @wraps(func)
        def timeit_wrapper(*args, **kwargs):
            start_time = time.perf_counter()
            result = func(*args, **kwargs)
            end_time = time.perf_counter()
            total_time = end_time - start_time
            if TIMING:
                print(f"Function {func.__name__} Took {total_time:.4f} seconds")
            return result

        return timeit_wrapper