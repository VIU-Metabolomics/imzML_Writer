"""Regression coverage for decimal scan filters sharing an output prefix."""
from contextlib import ExitStack

import numpy as np
from pyimzml.ImzMLParser import ImzMLParser
from pyimzml.ImzMLWriter import ImzMLWriter

from imzml_writer.utils import _filter_output_stem


def test_decimal_filters_write_separate_readable_pairs(tmp_path):
    filters = [
        'FTMS + p ESI cv=26.10 Full ms2 187.0788@hcd20.00 [42.2151-211.0754]',
        'FTMS + p ESI cv=26.10 Full ms2 193.0988@hcd20.00 [43.4432-217.2158]',
        'FTMS + p ESI cv=26.10 Full ms2 189.0915@hcd20.00 [42.6257-213.1283]',
    ]
    paths = [tmp_path / (_filter_output_stem('brain', f) + '.imzML') for f in filters]
    assert len(set(paths)) == len(filters)
    assert all('.' not in path.stem for path in paths)
    with ExitStack() as stack:
        for index, path in enumerate(paths):
            writer = stack.enter_context(ImzMLWriter(str(path), mode='processed'))
            writer.addSpectrum(np.array([100.0 + index]), np.array([10.0 + index]), (1, 1, 1))
    for index, path in enumerate(paths):
        assert path.exists()
        assert path.with_suffix('.ibd').exists()
        parser = ImzMLParser(str(path))
        mz, intensity = parser.getspectrum(0)
        np.testing.assert_array_equal(mz, [100.0 + index])
        np.testing.assert_array_equal(intensity, [10.0 + index])
        parser.m.close()


def test_filenames_replace_decimal_points_without_serial_codes():
    scan_filter = 'FTMS + p ESI cv=26.10 Full ms2 187.0788@hcd20.00'
    assert _filter_output_stem('brain', scan_filter) == 'brain_' + scan_filter.replace('.', '_')
