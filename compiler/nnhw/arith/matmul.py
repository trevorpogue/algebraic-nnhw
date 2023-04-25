import math
import torch
from nnhw.top import (FIPMethod, nameof, varname, IO, IOs, DTYPE, AttrDict)
from attrs import define, field, Factory
from debug import log


@define
class MatMulScoreboard:
    def __call__(self, device, a, b):
        seqitem = AttrDict()
        seqitem.a, seqitem.b = a, b
        a, b = self._pad(seqitem)
        IO.C = varname()
        self.c_plus_alpha_key = varname()
        self.c_plus_beta_key = varname()
        self.c_plus_alpha_beta_key = varname()
        self.y_key = varname()
        self.alpha_key = varname()
        self.ctypes = [nameof(IO.C),
                       nameof(self.c_plus_alpha_beta_key),
                       nameof(self.c_plus_alpha_key),
                       nameof(self.c_plus_beta_key),
                       nameof(self.y_key),
                       nameof(self.alpha_key),
                       ]
        self._mats = {}
        for member in FIPMethod.__members__.values():
            self._mats[member] = {}
            for ctype in self.ctypes:
                self._mats[member][ctype] = None
        self.mats = self._mats[device.FIP_METHOD]
        c_fip, c_ffip = self._ffip(a, b)
        c_classic_torch = self._classic_torch(a, b)
        assert torch.equal(c_classic_torch, c_fip)
        assert torch.equal(c_classic_torch, c_ffip)
        if device.FIP_METHOD is FIPMethod.FFIP:
            return self.mats[self.c_plus_beta_key]
        elif device.FIP_METHOD is FIPMethod.FIP:
            return self.mats[self.c_plus_beta_key]
        else:
            assert device.FIP_METHOD is FIPMethod.BASELINE
            return c_classic_torch

    def get_beta(self, seqitem):
        a, b = self._pad(seqitem)
        a = a.to(dtype=DTYPE)
        b = b.to(dtype=DTYPE)
        return self._get_beta(a, b).squeeze(0)

    def _get_beta(self, a, b):
        N, K = b.size(1), a.size(1)
        beta = torch.zeros(1, N, dtype=DTYPE)
        for n in range(N):
            for k in range(0, K, 2):
                beta[0, n] += b[k, n] * b[k+1, n]
        return beta

    def get_alpha(self, seqitem):
        a, b = self._pad(seqitem)
        return self._get_alpha(a, b)

    def _get_alpha(self, a, b):
        M, K = a.size(0), a.size(1)
        alpha = torch.zeros(M, 1, dtype=DTYPE)
        for m in range(M):
            for k in range(0, K, 2):
                alpha[m, 0] += a[m, k] * a[m, k+1]
        return alpha

    def _pad(self, seqitem):
        DTYPE = seqitem.dtype
        a, b = seqitem.a, seqitem.b
        M, N, K = a.size(0), b.size(1), a.size(1)
        if K & 1:
            a = torch.cat((a, torch.zeros((M, 1), dtype=DTYPE)), 1)
            b = torch.cat((b, torch.zeros((1, N), dtype=DTYPE)), 0)
        return a, b

    def _classic_torch(self, a, b):
        return torch.as_tensor(torch.matmul(a, b), dtype=DTYPE)

    def _ffip(self, a, b):
        # begin Improved method portion ####
        M, N, K = a.size(0), b.size(1), a.size(1)
        y = torch.zeros(K, N, dtype=DTYPE)
        for k in range(K):
            for n in range(N):
                y[k, n] = (b[k, n] - b[k, n-1] if n > 0 else b[k, n])
        self.mats[self.y_key] = y.detach().clone()
        g = torch.zeros(M, N, K, dtype=DTYPE)
        for m in range(M):
            for n in range(N):
                if (n == 0):
                    for k in range(0, K, 2):
                        # This works:, and
                        g[m, n, k] = (a[m, k+1] + y[k, n])
                        g[m, n, k+1] = (a[m, k] + y[k+1, n])
                        # This works also:
                        # g[i, j, k] = (a[i, k+1] + b[k, j])
                        # g[i, j, k+1] = (a[i, k] + b[k+1, j])
                else:
                    for k in range(K):
                        g[m, n, k] = g[m, n-1, k] + y[k, n]
        # end Improved method portion (except for 2 lines marked below) ####
        alpha = self._get_alpha(a, b)
        self.mats[self.alpha_key] = alpha.detach().clone()
        beta = self._get_beta(a, b, )
        c_fip = torch.zeros(M, N, dtype=DTYPE)
        c_ffip = torch.zeros(M, N, dtype=DTYPE)
        for m in range(M):
            for n in range(N):
                for k in range(0, K, 2):
                    c_fip[m, n] += ((a[m, k] + b[k+1, n])
                                             * (a[m, k+1] + b[k, n]))
                    # Improved portion
                    c_ffip[m, n] += g[m, n, k] * g[m, n, k+1]
        self.mats[self.c_plus_alpha_key] = c_fip.detach().clone()
        self.mats[self.c_plus_beta_key] = c_fip.detach().clone()
        self.mats[self.c_plus_alpha_beta_key] = c_fip.detach().clone()
        self.beta = beta.detach().clone()
        for m in range(M):
            for n in range(N):
                c_fip[m, n] += - alpha[m, 0] - beta[0, n]
                # Improved portion
                c_ffip[m, n] += - alpha[m, 0] - beta[0, n]
                self.mats[self.c_plus_alpha_key][m, n] -= beta[0, n]
                self.mats[self.c_plus_beta_key][m, n] -= alpha[m, 0]
        self.mats[IO.C] = c_fip.detach().clone()
        return c_fip, c_ffip

    def classic_loop(self, a, b):
        M, N, K = a.size(0), b.size(1), a.size(1)
        c = torch.zeros(M, N, dtype=DTYPE)
        for m in range(M):
            for n in range(N):
                ksum = 0
                for k in range(K):
                    ksum += (a[m, k]
                             * b[k, n])
                c[m, n] = ksum
        return c
