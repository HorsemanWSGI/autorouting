from autoroutes import Routes as Autoroutes
from collections import UserDict
from typing import NamedTuple, Any, Literal, ClassVar
from autorouting.url import RouteURL
from frozendict import frozendict


class Routes(Autoroutes):

    def __init__(self):
        self._byname: dict[str, RouteURL] = {}
        super().__init__()


class Route(NamedTuple):
    routed: Any
    requirements: frozendict
    priority: int = 0


class RouteGroup(UserDict[str, list[Route]]):
    name: str | None

    def __init__(self, name: str | None, *args, **kwargs):
        self.name = name
        super().__init__(*args, **kwargs)

    def add(self, method: str, route: Route, append: bool = True):
        if method in self:
            if not append:
                raise KeyError("Route already populated.")
            if route in self[method]:
                raise ValueError('Route already exists.')
            for existing in self[method]:
                if existing == route:
                    raise ValueError('Equivalent route already exists.')
            self[method].append(route)
        else:
            self[method] = [route]
        self[method].sort(key=lambda r: (-r.priority, -len(r.requirements)))


class Router(dict[str, RouteGroup]):

    allowed_methods: ClassVar[frozenset[str]] = {
        "GET", "HEAD", "PUT", "DELETE", "PATCH", "POST", "OPTIONS"
    }

    def __init__(self, *args, **kwargs):
        self._names = set()
        super().__init__(*args, **kwargs)

    def add(self,
            path: str,
            method: str,
            routed: Any,
            name: str | None = None,
            requirements: dict | None = None,
            priority: int = 0):

        if method not in self.allowed_methods:
            raise ValueError(
                f"Unknown method: {key}. "
                f"Expected one of {self.allowed_methods!r}"
            )

        if requirements is None:
            requirements = {}
        route = Route(routed, frozendict(requirements), priority=priority)
        if path not in self:
            if name and name in self._names:
                raise NameError(f"Name {name!r} is already in use.")
            group = self[path] = RouteGroup(name)
            group.add(method, route)
        else:
            if self[path].name is None:
                if name and name in self._names:
                    raise NameError(f"Name {name!r} is already in use.")
                self[path].name = name
            elif self[path].name != name:
                raise NameError(
                    f'Conflict: Route named {name} belongs to a '
                    f'group named: {group.name}'
                )
            self[path].add(method, route)
        return route

    def match(self, path: str, method: str, extra: dict | None = None):
        group, params = self._routes.match(path)
        if group and method in group:
            for route in group[method]:
                if not route.requirements:
                    yield route.routed, params
                elif extra:
                    if set(route.requirements.keys()) <= set(extra.keys()):
                        for name, requirement in route.requirements.items():
                            if not requirement.match(extra[name]):
                                continue
                        else:
                            yield route.routed, params

    def get(self, path: str, method: str, extra: dict | None = None):
        routes = self.match(path, method, extra)
        try:
            route = next(routes)
            return route
        except StopIteration:
            return None, None
        finally:
            routes.close()

    def get_by_name(self, name: str) -> RouteURL | None:
        return self._routes._byname.get(name)

    def finalize(self):
        self._routes = Routes()
        for path, group in self.items():
            if group.name:
                self._routes._byname[group.name] = RouteURL.from_path(path)
            self._routes.add(path, **group)
