class Node:
    def __init__(self, data=None, parent=None, name=None):
        self.parent = parent
        self.data = data
        self.name = name

        self.children = []
        self.weight = 0.0

        self.domains = []
        self.ranges = []

        self.is_leaf = True

    def add_child(self, child: str):
        if child not in self.children:
            self.is_leaf = False
            self.children.append(child)

    def add_domain(self, domain: str):
        if domain not in self.domains:
            self.domains.append(domain)

    def add_range(self, range: str):
        if range not in self.ranges:
            self.ranges.append(range)
