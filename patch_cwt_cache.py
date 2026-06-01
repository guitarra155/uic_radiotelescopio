import sys

with open('c:/uic_radiotelescopio/core/dsp_engine.py', 'r', encoding='utf-8') as f:
    content = f.read()

target = """                    _N_SC    = max(32, min(512, int(self.algo_params.get("cwt_n_scales", 64))))
                    _dt      = 1.0 / _sr
                    # Usar el espectro promedio ya calculado (pwr) que no tiene ruido
                    _pwr_lin = 10.0 ** ((pwr - _offset) / 10.0)
                    _omega   = (2 * np.pi * np.linspace(-_sr/2, _sr/2, self.fft_size, endpoint=False)).astype(np.float32)
                    _omega0  = 2 * np.pi * 6.0
                    _fq_hz   = np.linspace(-_sr * 0.49, _sr * 0.49, _N_SC, dtype=np.float32)
                    _fq_safe = np.where(_fq_hz == 0, 1e-5, _fq_hz)
                    _s_col   = (_omega0 / (2 * np.pi * np.abs(_fq_safe)))[:, None]  # (N_SC,1)
                    _sgn_col = np.sign(_fq_safe)[:, None]
                    _arg     = (_s_col * _omega[None, :] - _sgn_col * _omega0).astype(np.float32)
                    _supp    = (_sgn_col * _omega[None, :] > 0).astype(np.float32)
                    _nrm     = (np.pi ** -0.25) * np.sqrt(2 * np.pi * _s_col / _dt)
                    _psi_pw  = ((_nrm ** 2) * np.exp(-(_arg ** 2)) * _supp).astype(np.float32)
                    _psi_pw_sum = np.sum(_psi_pw, axis=1, keepdims=True)
                    _psi_pw_sum = np.where(_psi_pw_sum == 0, 1.0, _psi_pw_sum)
                    _psi_pw /= _psi_pw_sum
                    _line_lin = _psi_pw @ _pwr_lin.astype(np.float32)
                    _line_db  = (10.0 * np.log10(_line_lin + 1e-30) + _offset).astype(np.float32)
                    if _N_SC != _N_out:
                        _x_in  = np.linspace(0, 1, _N_SC)
                        _x_out = np.linspace(0, 1, _N_out)
                        _line_db = np.interp(_x_out, _x_in, _line_db).astype(np.float32)"""

repl = """                    # ---- CWT Caching & High Resolution ----
                    # Quitar límite de 512. Permitir hasta 4096 escalas para altísima resolución
                    _N_SC    = max(32, min(4096, int(self.algo_params.get("cwt_n_scales", 1024))))
                    _dt      = 1.0 / _sr
                    _pwr_lin = 10.0 ** ((pwr - _offset) / 10.0)
                    
                    # Cachear la matriz de wavelets (sólo recalcular si cambian parámetros)
                    cache_key = (_sr, self.fft_size, _N_SC)
                    if not hasattr(self, "_cwt_cache_key") or self._cwt_cache_key != cache_key:
                        _omega   = (2 * np.pi * np.linspace(-_sr/2, _sr/2, self.fft_size, endpoint=False)).astype(np.float32)
                        # Aumentar omega0 de 6 a 12 mejora drásticamente la resolución en frecuencia (hace el pico más fino)
                        _omega0  = 2 * np.pi * 12.0 
                        _fq_hz   = np.linspace(-_sr * 0.49, _sr * 0.49, _N_SC, dtype=np.float32)
                        _fq_safe = np.where(_fq_hz == 0, 1e-5, _fq_hz)
                        _s_col   = (_omega0 / (2 * np.pi * np.abs(_fq_safe)))[:, None]
                        _sgn_col = np.sign(_fq_safe)[:, None]
                        _arg     = (_s_col * _omega[None, :] - _sgn_col * _omega0).astype(np.float32)
                        _supp    = (_sgn_col * _omega[None, :] > 0).astype(np.float32)
                        _nrm     = (np.pi ** -0.25) * np.sqrt(2 * np.pi * _s_col / _dt)
                        _psi_pw  = ((_nrm ** 2) * np.exp(-(_arg ** 2)) * _supp).astype(np.float32)
                        _psi_pw_sum = np.sum(_psi_pw, axis=1, keepdims=True)
                        _psi_pw_sum = np.where(_psi_pw_sum == 0, 1.0, _psi_pw_sum)
                        _psi_pw /= _psi_pw_sum
                        self._cwt_cached_matrix = _psi_pw
                        self._cwt_cache_key = cache_key

                    _line_lin = self._cwt_cached_matrix @ _pwr_lin.astype(np.float32)
                    _line_db  = (10.0 * np.log10(_line_lin + 1e-30) + _offset).astype(np.float32)
                    if _N_SC != _N_out:
                        _x_in  = np.linspace(0, 1, _N_SC)
                        _x_out = np.linspace(0, 1, _N_out)
                        _line_db = np.interp(_x_out, _x_in, _line_db).astype(np.float32)"""

if target in content:
    content = content.replace(target, repl)
    with open('c:/uic_radiotelescopio/core/dsp_engine.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print("Patched successfully!")
else:
    print("Target not found!")
