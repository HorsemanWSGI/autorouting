import re
from typing import NamedTuple
from functools import partial
from autoroutes import MATCH_TYPES, PATTERNS
from urllib.parse import urlencode


SLUGS = re.compile('{([^:}]+):?(.*?)}')
UNSLUGIFY = re.compile(r"\{(\w+)[\|\:].*\}")
unslugify = partial(UNSLUGIFY.sub, r"{\1}")


def extract_slugs(url: str):
    slugs: dict[str, tuple[str, re.Pattern]] = {}
    for name, matcher in SLUGS.findall(url):
        if not matcher:
            matcher = 'string'
        if name in slugs:
            raise NameError(f'Duplicate variable name in url: {name}.')
        if matcher in MATCH_TYPES:
            type = matcher
            pattern = PATTERNS[MATCH_TYPES[matcher]]
        else:
            type = 'regexp'
            pattern = matcher
        slugs[name] = (type, re.compile(f'^{pattern}$'))
    return slugs


class RouteURL(NamedTuple):
    url: str
    slugs: dict[str, tuple[str, re.Pattern]] | None = None

    def match(self, **values) -> tuple[dict[str, str], dict[str, str]]:
        matched = {}
        for name, matcher in self.slugs.items():
            if name not in values:
                raise KeyError('Missing URL variable: {name}.')
            type, pattern = matcher
            value = values.pop(name)
            if not pattern.match(value):
                if type != 'regexp':
                    raise ValueError(
                        f'Param {name!r} of wrong type. '
                        f'Expected value of {type!r} type.'
                    )
                raise ValueError(
                    f'{name!r} param does not match pattern {pattern!r}.'
                )
            matched[name] = value
        return matched, values

    def resolve(self, variables: dict[str, str], qstring: bool = True):
        if self.slugs:
            matched, unmatched = self.match(**variables)
            path = self.url.format(**matched)
        else:
            path = self.url
            unmatched = variables

        if unmatched and qstring:
            qs = urlencode(unmatched)
            return f'{path}?{qs}'
        return path

    @classmethod
    def from_path(cls, path: str):
        slugs = extract_slugs(path)
        url = unslugify(path)
        return cls(url=url, slugs=slugs or None)
