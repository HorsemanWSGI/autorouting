from autorouting import Router
import fnmatch


class wildstr:

    def __init__(self, pattern):
        self.pattern = pattern

    def match(self, value):
        return fnmatch.fnmatch(value, self.pattern)


class value:

    def __init__(self, value):
        self.value = value

    def match(self, value):
        return self.value == value


router = Router()


router.add("path/to/{var:digit}", 'GET', 'component A')
router.add("path/to/{var}", 'GET', 'component B')
router.add("download/{name:path}", 'GET', 'component C')


router.finalize()
assert router.get('path/to/1', 'GET') == ('component A', {'var': '1'})
assert router.get('path/to/abc', 'GET') == ('component B', {'var': 'abc'})
assert router.get('download/file', 'GET') == ('component C', {'name': 'file'})


assert router.get('unknown/test', 'GET') == (None, None)



router = Router()

router.add("path/to/{var}", 'GET', 'component A',
           requirements={'name': wildstr('f??')})
router.add("path/to/{var}", 'GET', 'component B',
           requirements={'name': wildstr('f*'), 'user': value('admin')})
router.add("path/to/{var}", 'GET', 'component C')


router.finalize()

assert router.get(
    'path/to/1', 'GET', extra={"name": "fee"}
) == ('component A', {'var': '1'})

assert router.get(
    'path/to/1', 'GET', extra={"name": "fee", "user": "admin"}
) == ('component B', {'var': '1'})

assert router.get('path/to/1', 'GET') == (
    'component C', {'var': '1'}
)

found = list(
    router.match(
        'path/to/1', 'GET', extra={"name": "fee", "user": "admin"}
    )
)
assert found == [
    ('component B', {'var': '1'}),
    ('component A', {'var': '1'}),
    ('component C', {'var': '1'})
]
