# Argument injection and composition

While there are a few dependency injection packages out there, I found that they aren't
very pythonic and thus not very concise.  These decorators have turned out to be
surprising useful for my projects.  Some of the things I've used them for:

1. Dynamic containers at call time (like creating a dict at runtime)
2. Supersede `contextlib.contextmanager` to fetch return value
3. Dealing with async calls inside a sync-style system

One important thing to note, these decorators do not change the signature of the wrapped
function.  That is, the signature will still be the same even though arguments are
effectively defaulted and/or modified just before the function is entered.

## Injection

Look at the docstrings for basic use-cases.  Basically, you can inject and argument
into a function if it's not passed in explicitly.  Kinda acts like a default arg.

### Inject args

    >>> @injects(arg1=lambda: 7, arg2=6, arg3=5)
    ... def foo(arg1, arg2, arg3='ignored'):
    ...     return arg1, arg2, arg3
    >>> foo()           # arg3 default parameter is ignored; `injects` has precedence
    (7, 6, 5)
    >>> foo(9)
    (9, 6, 5)
    >>> foo(arg2=88)    # arg2 takes value passed in
    (7, 88, 5)
    >>> foo(arg1=None)  # arg1 takes value passed in
    (None, 6, 5)

### Inject a context

    >>> import contextlib
    >>> @contextlib.contextmanager
    ... def ctx():
    ...     yield 7
    >>> @injects.ctx(arg1=ctx)
    ... def foo(arg1):
    ...     return arg1
    >>> foo()
    7

## Composition

Again look at docstrings for base use-cases.  You can re-compose an argument passed in
to a function.


### Compose args

    >>> @composes(lambda x: x+1, y=lambda y: y+2, hello=lambda x: 'bye')
    ... def foo(x, y=2, *args, **kwargs):
    ...     return x, y
    >>> foo(0, 1, 'me', ignored=7)
    (1, 3)
    >>> foo(1)   # defaults are not composed
    (2, 2)


### Compose a context

    >>> import contextlib
    >>> @contextlib.contextmanager
    ... def ctx(x):
    ...     yield x + 1
    >>> @composes.ctx(arg1=lambda x: ctx(x))
    ... def foo(arg1, arg2='me'):
    ...     return arg1, arg2
    >>> foo(7)
    (8, 'me')
