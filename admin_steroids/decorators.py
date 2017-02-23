from __future__ import print_function

import time
import math

import six

def retry_exceptionless(tries=3, delay=3, backoff=1, exception_cb=None, commit=True):
    '''
    Retries a function or method until it runs without throwing an exception.

    delay sets the initial delay in seconds, and backoff sets the factor by
    which the delay should lengthen after each failure. backoff must be greater
    than 1, or else it isn't really a backoff. tries must be at least 0, and
    delay greater than 0.

    Based on https://wiki.python.org/moin/PythonDecoratorLibrary#Retry
    '''
    if commit:
        from django.db import transaction

    if backoff < 1:
        raise ValueError("backoff is %s but must be greater than 1" % (backoff,))

    tries = math.floor(tries)
    if tries < 0:
        raise ValueError("tries is %s but must be 0 or greater" % (tries,))

    if delay <= 0:
        raise ValueError("delay is %s but must be greater than 0" % (delay,))

    def deco_retry(f):
        def f_retry(*args, **kwargs):
            mtries, mdelay = tries, delay # make mutable
            for retry in six.moves.range(int(mtries)):
                try:
                    rv = f(*args, **kwargs)
                    if commit:
                        transaction.commit()
                    return rv
                except Exception as e:
                    if retry+1 == mtries:
                        raise
                    if exception_cb:
                        exception_cb(e)
                    # Wait.
                    time.sleep(mdelay)
                    # Make future wait longer.
                    mdelay *= backoff
        return f_retry # true decorator -> decorated function
    return deco_retry # @retry(arg[, ...]) -> true decorator
