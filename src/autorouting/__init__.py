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


class MatchedRoute(NamedTuple):
    routed: Any
    params: dict


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

    def __or__(self, other) -> 'RouteGroup':
        router = self.__class__(other.name or self.name)
        for key, routes in self.items():
            router[key] = [*routes]
        for key, routes in other.items():
            if key in router:
                for route in routes:
                    if route not in router[key]:
                        router[key].append(route)
                router[key].sort(key=lambda r: (-r.priority, -len(r.requirements)))
            else:
                router[key] = [*other[key]]
        return router

    def __ior__(self, other: 'Router') -> 'Router':
        self.name = other.name or self.name
        for key, routes in other.items():
            if key in self:
                for route in other[key]:
                    if route not in self[key]:
                        self[key].append(route)
                self[key].sort(key=lambda r: (-r.priority, -len(r.requirements)))
            else:
                self[key] = [*other[key]]
        return self


class Router(dict[str, RouteGroup]):

    allowed_methods: ClassVar[frozenset[str]] = frozenset({
        "GET", "HEAD", "PUT", "DELETE", "PATCH", "POST", "OPTIONS"
    })

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
                f"Unknown method: {method}. "
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
                    f'Conflict: Path of route {name!r} already '
                    f'belongs to a group named {self[path].name!r}.'
                )
            self[path].add(method, route)
        return route

    def match(self, path: str, method: str, extra: dict | None = None):
        group, params = self._routes.match(path)
        if group and method in group:
            for route in group[method]:
                if not route.requirements:
                    yield MatchedRoute(route.routed, params)
                elif extra:
                    if set(route.requirements.keys()) <= set(extra.keys()):
                        for name, requirement in route.requirements.items():
                            if not requirement.match(extra[name]):
                                break
                        else:
                            yield MatchedRoute(route.routed, params)

    def get(self, path: str, method: str, extra: dict | None = None) -> MatchedRoute | None:
        routes = self.match(path, method, extra)
        try:
            return next(routes)
        except StopIteration:
            return None
        finally:
            routes.close()

    def get_by_name(self, name: str) -> RouteURL | None:
        return self._routes._byname.get(name)

    def finalize(self):
        self._routes = Routes()
        for path, group in self.items():
            if group.name:
                self._routes._byname[group.name] = RouteURL.from_path(path)
            self._routes.add(path, **{method: tuple(routes) for method, routes in group.items()})

    def __or__(self, other) -> 'Router':
        router = self.__class__()
        for path, group in self.items():
            router[path] = RouteGroup(group.name, {
                method: [*routes] for method, routes in group.items()
            })
        for path, group in other.items():
            if path in router:
                router[path] |= group
            else:
                router[path] = RouteGroup(group.name, {
                    method: [*routes] for method, routes in group.items()
                })
        return router

    def __ior__(self, other: 'Router') -> 'Router':
        for path, group in other.items():
            if path in self:
                self[path] |= group
            else:
                self[path] = RouteGroup(group.name, {
                    method: [*routes] for method, routes in group.items()
                })
        return self
