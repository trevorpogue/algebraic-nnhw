from copy import deepcopy, copy
from itertools import repeat
from math import ceil, floor
from typing import Any, List, Tuple, Union
import sections
import snoop
import torch
from sections import MetaSection, Section, SectionNone
from sections.types import GetType
from torch import Tensor
from torch.nn import functional as F
from nnhw import top
from nnhw.top import TileDim as Dim
from nnhw.top import Enum, StrEnum, auto, not_inplace, prod


class DimOrder(StrEnum):
    child_dominant = auto()
    tile_dominant = auto()


def inplace_(method):
    """Convert a non-inplace method to an inpace one.
    See bottom of Space doctring for definition of inplace."""

    def wrapper(self, *args, **kwds):
        space = method(self, *args, **kwds)
        self._update_from_space_(space)
    return wrapper


def totuple(x: Any) -> List[Any]:
    if isinstance(x, list):
        return tuple(x)
    elif isinstance(x, tuple):
        return x
    else:
        return (x, )


class MetaSpace(MetaSection):
    def __call__(self, *args, **kwds):
        if kwds.get('sizes'):
            kwds.setdefault('size', kwds.get('sizes'))
            kwds.pop('sizes')
        if kwds.get('strides'):
            kwds.setdefault('stride', kwds.get('strides'))
            kwds.pop('strides')
        tensor = kwds.pop('tensor', None)
        dims_from_tensor = kwds.pop('dims_from_tensor', False)
        if tensor is not None and dims_from_tensor:
            size, stride = list(tensor.size()), list(tensor.stride())
            kwds['size'] = size
            kwds['stride'] = stride
            kwds['dim_i'] = list(range(len(list(tensor.size()))))
        kwds['_tensor_'] = tensor
        space = super().__call__(*args, **kwds)
        return space


class Space(Section, metaclass=MetaSpace):
    """Space objects are a wrapper around torch.Tensor's, but
    they are more generalized in some regards because each subspace in a space
    can be either a single dimension (like with conventional tensors), or
    another subspace containing multiple more dimensions or subspaces. This is
    essentially just a way to easily organize the dimensions into sections.
    The core of this aspect is done using tree data structures in the sections
    package I put on pypi (see https://github.com/trevorpogue/sections). The
    sections allow for easier printing visualization and conceptualizing of the
    purpose and origin of each dimension. sections also allows for very
    convenient reordering or manipulation of dimensions or groups of dimensions
    at a time. Other differences to Tensor's are that the Space dimensions or
    subspaces can be referred to by names instead of indexes like with tensors
    (although torch seems to have some support for this now).

    One of the main purposed of this class is the functionality in
    Space.unflatten, which does not behave the same as torch.nn.Unflatten and
    is useful for tiling/splitting a space of dimensions into two spaces, while
    maintaining referenced to original dimensions/counters which allow the
    tiling to be still mapped when using hardware counters.

    Each public method below is directly analogous to or at least similar in
    some ways to the same function name in the torch package. So see torch
    documentation for some more details on the methods.

    Method names ending with '_' are done in-place, i.e the following lines are
    equivalent:

    space = space.unflatten()
    space.unflatten_()
    """
    # use_cache = False

    def __init__(self, **kwds):
        super().__init__(**kwds)
        self._printing = False

    def structure_change(self,):
        if self.isleaf:
            if not hasattr(self, 'size'):
                self.size = 1
            if not hasattr(self, 'stride'):
                self.stride = 0
            # if self.size == 1 and self.stride == 0 and self.ischild:
                # self.parent.pop(self.name)
        else:
            delattr(self, 'size')
            delattr(self, 'stride')
        if not self.isroot:
            if isinstance(self.__dict__.get('_tensor_'), torch.Tensor):
                self._tensor = self._tensor_
                delattr(self, '_tensor_')

    @property
    def nofdims(self, ): return len(self.leaves)
    @property
    def dims(self, ): return self.leaves
    @property
    def subspaces(self, ): return self.children

    @property
    def range(self):
        range = []
        for sz, sd in zip(self('size', list), self('stride', list)):
            range.append(sz * sd)
        if len(range) == 1:
            range = range[0]
        return range

###############################################################################
# self.string parsing for visualization and other misc overrides

    def __str__(self):
        if self.hastensor:
            tensor = self._tensor.detach().clone()
        copy = deepcopy(self)
        copy.del_attrs_for_str()
        # if self.hastensor:
        #     self._printing = True
        #     copy._tsize = list(tensor.size())
        #     copy._tstride = list(tensor.stride())
        #     try:
        #         copy._dsize = list(self.data.size())
        #         copy._dstride = list(self.data.stride())
        #     except RuntimeError:
        #         pass
        #     self._printing = False
        return copy._super_str()

    def _super_str(self):
        return super().__str__()

    def del_attrs_for_str(self, _nil=[]):
        for name in [
                'carry', 'count', 'ranges', 'dim_i',
                '_tensor_', '_printing', 'reset_value',
                Dim.tile_fill, Dim.tile_count,
                'total_size', 'total_stride',
        ]:
            if self.__dict__.get(name, _nil) is not _nil:
                delattr(self, name)
        if isinstance(self.name, Enum):
            self.name = self.name.value
        if self.isleaf:
            self.name = f'{self.name}: ({self.size}, <{self.range}>, {self.stride})'
            delattr(self, 'stride')
            delattr(self, 'size')
        else:
            self.name = f'{self.name}: {prod(self("size", list))}'
        for v in self.values():
            v.del_attrs_for_str()

    # def __deepcopy__(self, memo, _nil=[]):
    #     """Tensors don't support deepcopy, making life a bit more difficult."""
    #     copy = self.cls()
    #     memo[id(self)] = copy
    #     for k, v in self.__dict__.items():
    #         if isinstance(v, torch.Tensor):
    #             setattr(copy, k, v.detach().clone())
    #         else:
    #             setattr(copy, k, deepcopy(v, memo))
    #     for k, v in self.items():
    #         copy[k] = deepcopy(v, memo)
    #     return copy

    def __setitem__(self, name, value):
        super().__setitem__(name, value)
        # if self.hastensor:
            # self._test_data()

    def __call__(
            self,
            name: str = SectionNone,
            gettype: GetType = 'default',
            default: Any = SectionNone,
    ) -> Union[Any, List[Any]]:
        returning_tensor = (gettype is Tensor) or (gettype is torch.tensor)
        if returning_tensor:
            gettype = list
        ret = super().__call__(name, gettype, default)
        if returning_tensor:
            ret = Tensor(ret)
        return ret

###############################################################################
# internal data accessors (the data is a torch.Tensor)

    @property
    def _tensor(self):
        """Internal data storage."""
        if self.hastensor:
            tensor = self.root._tensor_
        else:
            size = self.size
            if not isinstance(size, list):
                size = [size]
            if size == [sections.SectionNone]:
                size = [1]
            size = tuple(size)
            tensor = torch.zeros(size)
            tensor = None
        return tensor

    @_tensor.setter
    def _tensor(self, tensor):
        if isinstance(tensor, torch.Tensor):
            self.root._tensor_ = tensor

    @property
    def hastensor(self):
        return isinstance(self.root.__dict__.get('_tensor_'), torch.Tensor)

###############################################################################
# self.attribute and/or children modifications based on tensor or other space

    @not_inplace
    def _copy_from_tensor(self, *args, **kwds):
        return self._update_size_stride_(*args, **kwds)

    def _update_size_stride_(self):
        self._update_stride_()
        self._update_size_()
        return self

    def _update_size_(self):
        self.size = list(self._tensor.size())
        return self

    def _update_stride_(self):
        self.stride = list(self._tensor.stride())
        return self

    def _update_(self):
        self._as_strided_tensor_()
        self._update_size_stride_()
        return self

    def _update_from_space_(self, space):
        self.clear()
        parent = self.parent
        super().update(space)
        self.__dict__ = space.__dict__
        self.parent = parent
        return self

    def _size_stride_lists(self):
        size = self('size', list)
        stride = self('stride', list)
        return size, stride

    def _size_stride_with_size1pairs_stripped(self):
        size_, stride_ = self._size_stride_lists()
        size, stride = [], []
        for sz, strde in zip(size_, stride_):
            if sz != 1:
                size += [sz]
                stride += [strde]
        return size, stride

###############################################################################
# tensor modifications

    def _permute_tensor_(self, *args, **kwds):
        self._as_strided_tensor_()
        self._tensor = self._permute_tensor(*args, **kwds)
        return self._tensor

    def _permute_tensor(self, *dims): return self._tensor.permute(*dims)

    # def _reshape_tensor_(self, *args, **kwds):
    #     self._test_data()
    #     self._tensor = self._reshape_tensor(*args, **kwds)
    #     return self._tensor

    # def _reshape_tensor(self): return self._tensor.reshape(self('size', list))

    def _test_data(self): self.data  # test

    def __as_strided_tensor(self):
        if self.hastensor:
            size, stride = self._size_stride_with_size1pairs_stripped()
            return self._tensor.as_strided(tuple(size), tuple(stride))
        else:
            return None

    def _as_strided_tensor(self):
        try:
            tensor = self.__as_strided_tensor()
        except RuntimeError as e:
            if not self._printing:
                # print debug info before failure:
                print(e)
                print(self.name)
                self._printing = True
                print(self.root)
                self._printing = False
            tensor = self.__as_strided_tensor()
        return tensor

    def _as_strided_tensor_(self, *args, **kwds):
        self._tensor = self._as_strided_tensor(*args, **kwds)
        self._update_stride_()
        # self._update_size_()
        return self._tensor

###############################################################################
# PUBLIC API
# (plus some closely-related non-public methods for organization purposes)
# -----------------------------------------------------------------------------
# data access (accessing the torch.Tensor)

    @property
    def data(self):
        """
        Public data. Updates internal data based on recorded transformations.
        This allows tensor operations to often only be done all at once when
        its data is finally needed by user which means less constant internal
        updating/less code/less bugs.
        """
        tensor = self._as_strided_tensor()
        # tensor = self.flattened_data()
        return tensor

    def flattened_data(self, new_leaf_dims=None, ):
        """Flatten self.or children subspaces each into a single dimension.
        Similar to torch.flatten() or torch.reshape().
        """
        if new_leaf_dims is None:
            new_leaf_dims = self.children
        tensor_size = []
        for child in new_leaf_dims:
            size, stride = child._size_stride_with_size1pairs_stripped()
            if not len(stride):
                size, stride = [1], [0]
            tensor_size.append(prod(size))
        tensor = self._as_strided_tensor()
        if len(tensor_size):
            tensor = tensor.reshape(*tensor_size)
        return tensor

    # def

# -----------------------------------------------------------------------------
# pad, permute

    def pad_(self, pads=None, update_sizes: Union[bool, List[str]] = True):
        "Analogous to torch.Tensor.pad_."
        self._tensor = F.pad(self._tensor, pads)
        self._update_stride_()
        if update_sizes is True:
            update_sizes = self.keys()
        try:
            list(update_sizes)
        except TypeError:
            if update_sizes:
                update_sizes = [update_sizes]
        if update_sizes:
            for name in update_sizes:
                subspace = self[name]
                subspace.size = self._tensor.size(subspace.dim_i)
        return self

    @inplace_
    def permute_(self, *args, **kwds): return self.permute(*args, **kwds)

    def permute(self, *names):
        "Analogous to torch.Tensor.permute."
        space = deepcopy(self)
        space.clear()
        keys = list(self.children.names)
        dim_is = {}
        for subspace_name in names:
            space.append(self[subspace_name])
            dim_is[subspace_name] = keys.index(subspace_name)
        # shouldn't do this:
        # space._permute_tensor_(*dim_is.values())
        # self._test_data()
        return space

# -----------------------------------------------------------------------------
    def to_triangular_shape(self):
        tsize = self('size', list)[-1]
        pads = *(0, 0) * 2, tsize, 0
        # print(pads)
        # self.pad_(pads, False)
        tensor = self._tensor
        # tensor = F.pad(self._tensor, pads)
        size, stride = self._size_stride_with_size1pairs_stripped()
        # size[-1] += tsize
        tensor = tensor.as_strided(size, stride)
        second_last_size = list(tensor.size())[-2]

        last_dim = len(tensor.size()) - 1
        tensor = tensor.flip(last_dim - 1)
        pads = *(0, 0) * 2, tsize, 0
        pads = *(0, 0) * 1, tsize, tsize, *(0, 0) * 4
        tensor = F.pad(tensor, pads)
        # tensor = self._as_strided_tensor()

        strides = list(tensor.stride())
        sizes = list(tensor.size())
        # print(sizes)
        strides[last_dim] = strides[last_dim - 1] + strides[last_dim]
        # sizes[last_dim] = last_size - 1
        # sizes[last_dim - 1] = 8
        # sizes[0] = 2
        # sizes[-2] = 70
        # sizes[-3] = 70
        sizes[last_dim - 1] = sizes[last_dim - 1] - tsize
        # sizes[last_dim - 1] = second_last_size

        tensor = tensor.as_strided(sizes, strides)
        tensor = tensor.flip(last_dim - 1)
        # print(tensor.size())
        # print(tensor.stride())
        return tensor

# -----------------------------------------------------------------------------
# unflatten - similar to torch.nn.Unflatten

    @not_inplace
    def unflatten(self, *args, **kwds): return self.unflatten_(*args, **kwds)

    def unflatten_(self, tile_sizes, tile_strides=None,
                   dim_order: DimOrder = DimOrder.tile_dominant
                   ):
        """ Split self.or children each into two spaces.

        If `tile_sizes` is non-iterable, tile self, otherwise tile each of
        self.s child i using tile parameter `tile_sizes[i]`. If `tile_sizes`,
        is iterable, `dim_order` determines how to group the tiled dims.

        Setting `dim_order` to DimOrder.tile_dominant makes ouput children ordered as:
        [Dim.tile_count, (), 'child_0', ..., 'child_i'],
        [self.tile_fill, (), 'child_0', ..., 'child_i']
        Setting `dim_order` to 'child_dominant' make output children ordered
        as:
        ['child_0', (), Dim.tile_count, self.tile_fill], ...,
        ['child_i', (), Dim.tile_count, self.tile_fill]
        """
        hadtensor = False
        if self.hastensor:
            tensor = self._tensor#.detach().clone()
            hadtensor = True
        tile_sizes = totuple(tile_sizes)
        if tile_strides is None:
            tile_strides = tuple([1] * len(tile_sizes))
        tiled_spaces = self.cls(self.name)
        spaces_to_tile = ([self] if len(tile_sizes) == 1
                          else self.values())
        for i, space_to_tile in enumerate(spaces_to_tile):
            # space_to_tile = deepcopy(space_to_tile)
            self.space_to_tile = space_to_tile
            self.tile_size = tile_sizes[i]
            self.tile_stride = tile_strides[i]
            tiled_spaces[space_to_tile.name] = self._tile_space()
        if dim_order == DimOrder.tile_dominant and len(tile_sizes) > 1:
            tiled_spaces = self._group_dims(tiled_spaces)
        prev_dim = self.cls(size=1, stride=1, total_size=1)
        for dim in reversed(tiled_spaces.dims):
            dim.total_stride = prev_dim.total_size
            dim.total_size = dim.total_stride * dim.size
            prev_dim = dim
        space = tiled_spaces.pop(0) if len(tile_sizes) == 1 else tiled_spaces
        self._update_from_space_(space)
        if hadtensor:
            self._tensor = tensor
        return self

    def _group_dims(self, tiled_spaces):
        tile_dim_names = list(reversed(Dim.__members__))
        spaces = self.cls(self.name, (), *tile_dim_names)
        for tile_dim_name in tile_dim_names:
            for space in tiled_spaces:
                if space.get(tile_dim_name):
                    spaces[tile_dim_name][space.name] = space[tile_dim_name]
        return spaces

    def _tile_space(self):
        space = self.cls(self.space_to_tile.name, (),
                              Dim.tile_count, Dim.tile_fill)
        for self.tile_methodname in Dim.__members__:
            name = ('' if self.name is SectionNone
                    else str(self.name) + '_')
            name = (name + self.tile_methodname)
            self._get_tile_count_or_fill(space)
        return space

    def _get_tile_count_or_fill(self, space):
        tensor = self.space_to_tile.root._tensor_
        self.space_to_tile.root._tensor_ = None  # avoid deepcopying tensor
        space[self.tile_methodname] = deepcopy(self.space_to_tile)
        self.tile_method = getattr(self.cls, '_' + self.tile_methodname)
        self.threshold = (self.tile_size*self.tile_stride)
        self.prev_dim = self.cls(size=1, stride=1, total_size=1)
        self._dims2pop = []
        for i, self.dim in enumerate(reversed(
                space[self.tile_methodname].dims)):
            self._tile_dim(space)
        for dim in self._dims2pop:
            dim.size = 1
        self.space_to_tile.root._tensor_ = tensor

    def _tile_dim(self, space):
        self.dim.total_stride = self.prev_dim.total_size
        self.dim.total_size = self.dim.total_stride * self.dim.size
        use_tiled_dim, use_existing_dim = self._decide_if_tiling_dim()
        if use_tiled_dim:
            self.tile_method(self, space)
        if not(use_tiled_dim or use_existing_dim):
            self._dims2pop.append(self.dim)
        self.prev_dim = self.dim

    def _decide_if_tiling_dim(self):
        use_existing_dim = False
        if self.tile_methodname == Dim.tile_count:
            use_tiled_dim = False
            if (self.dim.total_size > self.threshold
                    and (self.dim.total_stride < self.threshold)):
                use_tiled_dim = True
            if (self.dim.total_stride
                    >= (self.tile_size*self.tile_stride)):
                use_existing_dim = True
        else:
            use_tiled_dim = True
            if (self.dim.total_stride >= self.threshold
                    and self.dim.total_stride > 1):
                use_tiled_dim = False
            if (self.dim.total_size <= self.threshold):
                use_tiled_dim = False
                use_existing_dim = True
        return use_tiled_dim, use_existing_dim

    def _tile_count(self, space):
        self.dim.total_stride = self.threshold
        self.dim.size = ceil(self.dim.total_size / self.dim.total_stride)
        for dim in space[Dim.tile_fill].dims:
            if dim.size != 1:
                break
        self.dim.stride = dim.range

    def _tile_fill(self, space):
        total_stride = self.dim.total_stride
        self.dim.size = max(
            1, ceil(self.threshold / total_stride) % self.dim.size)
        self.dim.stride = self.dim.stride * self.tile_stride

# -----------------------------------------------------------------------------
