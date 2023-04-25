def _update_if_present(d2update, d2pass, name, d2check=None):
    if d2check is None:
        d2check = d2pass
    try:
        _ = d2check[name]
        d2update[name] = d2pass[name]
        ret = True
    except KeyError:
        ret = False
    return ret


def args2attrs(*dec_names, **dec_bindings):
    """Assign the input argument values of a method to the object's attributes.
    The corresponding names will be used for the attribute names.

    Example:
    class C:
        @args2attrs()
        def __init__(self, x, y=0):
            pass

    c = C(0)
    assert c.x = 0
    assert c.y = 0
    c = C(1, 1)
    assert c.x = 1
    assert c.y = 1
    c = C(2, y=2)
    assert c.x = 2
    assert c.y = 2
    """
    def decorator(method, ):
        def wrapper(self, *passed_args, **passed_kwds):
            from inspect import signature
            params = signature(method).parameters

            names = {}
            bindings2pass = {}

            """get all attr names to be assigneb"""
            for name in dec_names:
                dec_bindings[name] = None

            for name in params:
                names[name] = True
            for name in dec_bindings:
                names[name] = True
            self_name = next(iter(names))
            names.pop(self_name, None)
            attrs2update = dict.fromkeys(dec_bindings if dec_bindings
                                         else names, True)
            attrs2update.pop(self_name, None)

            for i, (name, param) in enumerate(params.items(), -1):
                """get attr values from all scopes"""
                # debug(name)
                if name is self_name:
                    continue
                if i < len(passed_args):
                    bindings2pass[name] = passed_args[i]
                else:
                    bindings2pass[name] = passed_kwds.get(name, param.default)

            attr_bindings = {}
            for name in attrs2update:
                # try:
                _update_if_present(attr_bindings, dec_bindings, name)
                _update_if_present(attr_bindings, bindings2pass, name)

            for name in attr_bindings:
                # debug(name)
                # debug(attr_bindings[name])
                setattr(self, name, attr_bindings[name])
                # debug(getattr(self, name))
                # except: pass

            # debug(dec_bindings)
            # debug(bindings2pass)
            # debug([*names.keys()])
            # debug([*attrs2update.keys()])
            # debug(passed_args)
            # debug(passed_kwds)
            # debug(attr_bindings)
            # debug(bindings2pass)
            # print()

            return method(self, **bindings2pass)

        return wrapper
    return decorator
