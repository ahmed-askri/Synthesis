"""Tool registry: every tool call goes through here, and each role
can only call the tools it was given."""


class PermissionDenied(Exception):
    pass


# Who may call what. Anything not listed is forbidden.
PERMISSIONS = {
    "researcher": {"search_arxiv", "search_web"},
    "fact_checker": set(),
    "writer": set(),
}


class ToolRegistry:
    def __init__(self, permissions=None):
        self._tools = {}
        self._permissions = PERMISSIONS if permissions is None else permissions
        self.denied = []  # log of blocked attempts: (role, tool)

    def register(self, name, fn):
        self._tools[name] = fn

    def call(self, role, name, **kwargs):
        allowed = self._permissions.get(role, set())
        if name not in allowed:
            self.denied.append((role, name))
            raise PermissionDenied(f"{role} is not allowed to call {name}")
        if name not in self._tools:
            raise KeyError(f"tool not registered: {name}")
        return self._tools[name](**kwargs)