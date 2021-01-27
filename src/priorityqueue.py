#!/usr/bin/python

# Copyright (C) 2020 Glenn Matlin, Zhiyang Su
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

import itertools
from heapq import heappush, heappop


class PriorityQueue:
    def __init__(self):
        self._pq = []
        self._entry_map = {}
        self._counter = itertools.count()

    def add_task(self, task, priority=0.0):
        """Add a new task or update the priority of an existing task"""
        if task in self._entry_map:
            self.remove_task(task)
        count = next(self._counter)
        entry = [priority, count, task]
        self._entry_map[task] = entry
        heappush(self._pq, entry)

    def remove_task(self, task):
        """Mark an existing task as REMOVED."""
        entry = self._entry_map.pop(task)
        entry[-1] = "removed"

    def pop_task(self):
        """Remove and return the lowest priority task."""
        while self._pq:
            priority, count, task = heappop(self._pq)
            if task != "removed":
                del self._entry_map[task]
                return task

    def __len__(self):
        return len(self._entry_map)

    def __str__(self):
        return self._entry_map
