################################################################################
#                                                                              #
#          histstack.py copyright 2015 Qiqi Wang (qiqi.wang@gmail.com)         #
#                                                                              #
################################################################################

import math
import collections

class _CheckPoint(object):
    def __init__(self, i_step, x):
        self.i_step = i_step
        self.x = x

class HistoryStack(object):
    def __init__(self, capacity, step_function):
        self._capacity = capacity
        lvl0capacity = int(math.ceil(math.sqrt(capacity)))
        lvl1capacity = lvl0capacity
        self._lvl0stack = collections.deque(maxlen=lvl0capacity)
        self._lvl1stack = collections.deque(maxlen=lvl1capacity)

        self._step_function = step_function

    def __len__(self):
        if len(self._lvl1stack):
            return self.i_step - self._lvl1stack[0].i_step + 1
        elif len(self._lvl0stack):
            return self.i_step - self._lvl0stack[0].i_step + 1
        else:
            return 0

    @property
    def i_step(self):
        if len(self._lvl0stack):
            return self._lvl0stack[-1].i_step
        elif len(self._lvl1stack):
            return self._lvl1stack[-1].i_step
        else:
            return 0

    def _lvl1_gap(self):
        if len(self._lvl1stack) and len(self._lvl0stack):
            return self._lvl0stack[0].i_step - self._lvl1stack[-1].i_step
        else:
            return float('inf')

    def push(self, x):
        if len(self._lvl0stack) == self._lvl0stack.maxlen and \
                self._lvl1_gap() > self._lvl0stack.maxlen:
            self._lvl1stack.append(self._lvl0stack[0])
        self._lvl0stack.append(_CheckPoint(self.i_step + 1, x))

    def _recalculate(self, to_i_step):
        n_steps = to_i_step - 1 - self._lvl1stack[-1].i_step
        assert n_steps < self._lvl1stack.maxlen
        x = self._lvl1stack[-1].x
        for i in range(n_steps):
            x = self._step_function(x)
            self._lvl0stack.append(_CheckPoint(self.i_step + 1, x))

    def pop(self):
        if len(self._lvl0stack):
            checkpoint = self._lvl0stack.pop()
        elif len(self._lvl1stack):
            checkpoint = self._lvl1stack.pop()
        else:
            return None

        if len(self._lvl0stack) == 0 and len(self._lvl1stack) > 0:
            self._recalculate(checkpoint.i_step - 1)
        return checkpoint.x

    def populate(self, x_seed):
        x = x_seed
        for i in range(self._capacity):
            self.push(x)
            x = self._step_function(x)

