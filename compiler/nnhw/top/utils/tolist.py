def _item_tolist(var):
    if isinstance(var, list):
        return var
    # elif isinstance(var, tuple):
    else:
        return [*var]
    # else:
    #     try:
    #         len(var)
    #         raise ValueError(f"type {type(var)} to list is not covered")
    #     except TypeError:
    #         # var is a scalar
    #         return [var]


def tolist(*vars, getlen=False):
    """Convert each a non-list element in `vars` to a list.
    If any elements are already a list leave them unchanged.
    """
    gt1_arg = (len(vars) > 1) and not isinstance(vars, list)
    if gt1_arg:
        vars_list = []
        for var in vars:
            vars_list.append(_item_tolist(var))
        return_val = vars_list
        arglen = len(_item_tolist(return_val[0]))
    else:
        L = _item_tolist(*vars)
        arglen = len(L)
        return_val = L
    if getlen:
        return_val += [arglen]
        return return_val
    else:
        return return_val
