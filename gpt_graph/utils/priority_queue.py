import heapq
from itertools import count

"""
used in Pieline.run
"""


class PriorityQueue:
    def __init__(self):
        self.pq = []  # list of entries arranged in a heap
        self.counter = count()  # unique sequence count

    def push(self, priority, item):
        entry = (-priority, next(self.counter), item)
        heapq.heappush(self.pq, entry)

    def initialize(self):
        """
        Reset the priority queue to an empty state.
        """
        self.pq = []
        self.counter = count()

    def pop(self):
        neg_priority, count, item = heapq.heappop(self.pq)
        priority = neg_priority * -1
        return priority, item

    def __bool__(self):
        return bool(self.pq)

    def __len__(self):
        return len(self.pq)

    def __str__(self):
        # Sort the queue by priority (highest first) for display
        sorted_queue = sorted(self.pq, key=lambda x: x[0])

        # Format each item in the queue
        formatted_items = [f"({-p}, {item})" for p, _, item in sorted_queue]

        # Join the formatted items into a single string
        return "PriorityQueue([" + ", ".join(formatted_items) + "])"

    def __repr__(self):
        return self.__str__()


if __name__ == "__main__":
    # Example usage
    pq = PriorityQueue()

    # Push items with priorities
    pq.push(3, "task A")
    pq.push(1, "task B")
    pq.push(3, "task C")
    pq.push(2, "task D")
    pq.push(1, "task E")

    # Pop and print items
    while pq.pq:
        priority, item = pq.pop()
        print(f"Priority: {priority}, Item: {item}")
