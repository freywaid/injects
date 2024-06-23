"""
Decorators to inject or compose arguments at function call time
"""
#
# decorators to compose arguments
#
import asyncio
import contextlib
import copy
import functools
import inspect


class _bindwrap:
    def __init__(self, val):
        self.val = val


def _build_bound_compose(ba, bc):
    def _call(c, a):
        if c is a or c is None:
            return a, False, False
        return c(a), True, c

    bb = type(ba)(ba.signature, copy.copy(ba.arguments))
    bb.arguments |= bc.arguments

    args = (_call(c, a) for c, a in zip(bb.args, ba.args))
    kwargs = ((k, _call(bb.kwargs.get(k), a)) for k, a in ba.kwargs.items())
    return args, kwargs


def composes(*composer_args, **composer_kwargs):
    """
    Re-compose incoming arguments

    >>> @composes(lambda x: x+1, y=lambda y: y+2, hello=lambda x: 'bye')
    ... def foo(x, y=2, *args, **kwargs):
    ...     return x, y
    >>> foo(0, 1, 'me', ignored=7)
    (1, 3)
    >>> foo(1)   # defaults are not composed
    (2, 2)
    """
    def _decorator(fn):
        sig = inspect.signature(fn)
        bc = sig.bind_partial(*composer_args, **composer_kwargs)

        def _compose(*args, **kwargs):
            ba = sig.bind(*args, **kwargs)
            return _build_bound_compose(ba, bc)

        if not asyncio.iscoroutinefunction(fn):
            @functools.wraps(fn)
            def _fn(*args, **kwargs):
                b_args, b_kwargs = _compose(*args, **kwargs)
                args = [v for v, _, _ in b_args]
                kwargs = {k: v for k, (v, _, _) in b_kwargs}
                ba = sig.bind(*args, **kwargs)
                return fn(*ba.args, **ba.kwargs)
        else:
            @functools.wraps(fn)
            async def _fn(*args, **kwargs):
                b_args, b_kwargs = _compose(*args, **kwargs)
                args = [await v if inspect.iscoroutine(awt) else v for v, _, awt in b_args]
                kwargs = {k: await v if inspect.iscoroutine(awt) else v \
                        for k, (v, _, awt) in b_kwargs}
                ba = sig.bind(*args, **kwargs)
                return await fn(*ba.args, **ba.kwargs)

        return _fn
    return _decorator


def composes_ctx(*composer_args, **composer_kwargs):
    """
    Re-compose incoming contexts

    >>> import contextlib
    >>> @contextlib.contextmanager
    ... def ctx(x):
    ...     yield x + 1
    >>> @composes.ctx(arg1=lambda x: ctx(x))
    ... def foo(arg1, arg2='me'):
    ...     return arg1, arg2
    >>> foo(7)
    (8, 'me')
    """
    def _decorator(fn):
        sig = inspect.signature(fn)
        bc = sig.bind_partial(*composer_args, **composer_kwargs)

        def _compose(*args, **kwargs):
            ba = sig.bind(*args, **kwargs)
            return _build_bound_compose(ba, bc)

        if not asyncio.iscoroutinefunction(fn):
            @functools.wraps(fn)
            def _fn(*args, **kwargs):
                with contextlib.ExitStack() as stack:
                    b_args, b_kwargs = _compose(*args, **kwargs)
                    args = [stack.enter_context(v) if ctx else v for v, ctx, _ in b_args]
                    kwargs = {k: stack.enter_context(v) if ctx else v \
                            for k, (v, ctx, _) in b_kwargs}
                    ba = sig.bind(*args, **kwargs)
                    return fn(*ba.args, **ba.kwargs)
        else:
            @functools.wraps(fn)
            async def _fn(*args, **kwargs):
                async with contextlib.AsyncExitStack() as stack:
                    async def _call(v, ctx, awt):
                        if not ctx:
                            return v
                        if not hasattr(v, '__aenter__'):
                            return stack.enter_context(v)
                        return await stack.enter_async_context(v)
                    b_args, b_kwargs = _compose(*args, **kwargs)
                    args = [await _call(*b) for b in b_args]
                    kwargs = {k: await _call(*b) for k, b in b_kwargs}
                    ba = sig.bind(*args, **kwargs)
                    return await fn(*ba.args, **ba.kwargs)
        return _fn
    return _decorator


composes.ctx = composes_ctx


#
# decorators to inject arguments
#
def _call_bound_inject(a):
    if not isinstance(a, _bindwrap):
        return a, False, False
    if not callable(a.val):
        return a.val, False, False
    return a.val(), True, a.val


def _build_bound_inject(ba, bc):
    bb = type(ba)(bc.signature, copy.copy(bc.arguments))
    bb.arguments |= ba.arguments

    b_args = (_call_bound_inject(v) for v in bb.args)
    b_kwargs = ((k, _call_bound_inject(v)) for k, v in bb.kwargs.items())
    return b_args, b_kwargs


def injects(*injector_args, **injector_kwargs):
    """
    Injects arguments into decorated function

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
    """
    def _decorator(fn):
        sig = inspect.signature(fn)
        bc = sig.bind_partial(*(_bindwrap(a) for a in injector_args),
                **{k: _bindwrap(v) for k, v in injector_kwargs.items()})

        if not asyncio.iscoroutinefunction(fn):
            @functools.wraps(fn)
            def _fn(*args, **kwargs):
                ba = sig.bind_partial(*args, **kwargs)
                b_args, b_kwargs = _build_bound_inject(ba, bc)
                args = [v for v, _, _ in b_args]
                kwargs = {k: v for k, (v, _, _) in b_kwargs}
                ba = sig.bind_partial(*args, **kwargs)
                return fn(*ba.args, **ba.kwargs)
        else:
            @functools.wraps(fn)
            async def _fn(*args, **kwargs):
                ba = sig.bind_partial(*args, **kwargs)
                b_args, b_kwargs = _build_bound_inject(ba, bc)
                args = [await v if inspect.iscoroutine(awt) else v for v, _, awt in b_args]
                kwargs = {k: await v if inspect.iscoroutine(awt) else v \
                        for k, (v, _, awt) in b_kwargs}
                ba = sig.bind_partial(*args, **kwargs)
                return await fn(*ba.args, **ba.kwargs)
        return _fn
    return _decorator


def injects_ctx(*injector_args, **injector_kwargs):
    """
    Injects context-wrapped arguments into decorated function

    >>> import contextlib
    >>> @contextlib.contextmanager
    ... def ctx():
    ...     yield 7
    >>> @injects.ctx(arg1=ctx)
    ... def foo(arg1):
    ...     return arg1
    >>> foo()
    7
    """
    def _decorator(fn):
        sig = inspect.signature(fn)
        bc = sig.bind_partial(*(_bindwrap(a) for a in injector_args),
                **{k: _bindwrap(v) for k, v in injector_kwargs.items()})

        async def _enter(stack, r, called, awt):
            if not called:
                return r
            if not hasattr(r, '__aenter__'):
                return stack.enter_context(r)
            return await stack.enter_async_context(r)

        if not asyncio.iscoroutinefunction(fn):
            @functools.wraps(fn)
            def _fn(*args, **kwargs):
                with contextlib.ExitStack() as stack:
                    ba = sig.bind_partial(*args, **kwargs)
                    b_args, b_kwargs = _build_bound_inject(ba, bc)
                    args = [stack.enter_context(v) if cld else v \
                            for v, cld, _ in b_args]
                    kwargs = {k: stack.enter_context(v) if cld else v \
                            for v, cld, _ in b_kwargs}
                    ba = sig.bind_partial(*args, **kwargs)
                    return fn(*ba.args, **ba.kwargs)
        else:
            @functools.wraps(fn)
            async def _fn(*args, **kwargs):
                found = {}
                async with contextlib.AsyncExitStack() as stack:
                    ba = sig.bind_partial(*args, **kwargs)
                    b_args, b_kwargs = _build_bound_inject(ba, bc)
                    args = [await _enter(stack, *b) for b in b_args]
                    kwargs = {k: await _enter(stack, *b) for k, b in b_kwargs}
                    ba = sig.bind_partial(*args, **kwargs)
                    return await fn(*ba.args, **ba.kwargs)
        return _fn
    return _decorator


injects.ctx = injects_ctx
