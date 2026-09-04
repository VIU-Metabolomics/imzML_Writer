from pathlib import Path

import pytest

from imzml_writer import zarr_writer


def _write_imzml(path: Path, scan_filter: str) -> None:
    path.write_text(
        "<?xml version='1.0'?>"
        "<mzML xmlns='http://psi.hupo.org/ms/mzml'>"
        f"<cvParam accession='MS:1000512' value='{scan_filter}'/>"
        "</mzML>",
        encoding="utf-8",
    )


def test_scan_filter_from_namespaced_imzml(tmp_path):
    source = tmp_path / "source.imzML"
    _write_imzml(source, "FTMS + p ESI Full ms [100.00-1000.00]")

    assert (
        zarr_writer.scan_filter_from_imzml(source)
        == "FTMS + p ESI Full ms [100.00-1000.00]"
    )


def test_scan_filter_is_required(tmp_path):
    source = tmp_path / "source.imzML"
    source.write_text("<mzML />", encoding="utf-8")

    with pytest.raises(ValueError, match="No scan filter"):
        zarr_writer.scan_filter_from_imzml(source)


@pytest.mark.parametrize(
    ("scan_filter", "display_name"),
    [
        (
            "FTMS + p ESI Full ms [100.00-1000.00]",
            "Positive fullscan",
        ),
        (
            "FTMS \N{MINUS SIGN} c ESI SIM msx ms [398.9-399.3]",
            "Negative SIM scan (m/z 399.1)",
        ),
        (
            "FTMS + p ESI Full ms2 885.54970@hcd30.00 [100-1000]",
            "Positive product ion scan (m/z 885.5497)",
        ),
    ],
)
def test_scan_filter_display_name_expands_polarity_and_mode(
    scan_filter, display_name
):
    assert zarr_writer.scan_filter_display_name(scan_filter) == display_name


def test_dataset_ids_keep_positive_and_negative_scans_distinct():
    used_ids = set()

    positive = zarr_writer._dataset_id("FTMS + p ESI Full ms", used_ids)
    negative = zarr_writer._dataset_id("FTMS - p ESI Full ms", used_ids)

    assert positive == "Positive_fullscan"
    assert negative == "Negative_fullscan"


def test_manual_ion_drag_is_converted_to_optical_translation():
    assert zarr_writer._manual_translation_from_ion_drag(
        (10.0, -4.0), (3.5, -2.0)
    ) == (6.5, -2.0)


def test_orphaned_ome_label_marker_is_removed_without_multiscale_damage():
    class LabelGroup:
        attrs = {
            "ome": {
                "version": "0.5-dev-spatialdata",
                "multiscales": [{"name": "tissue"}],
                "image-label": {"version": "0.5"},
            },
            "spatialdata_attrs": {"version": "0.3"},
        }

    label_group = LabelGroup()

    assert zarr_writer._remove_orphaned_ome_label_marker(label_group) is True
    assert "image-label" not in label_group.attrs["ome"]
    assert label_group.attrs["ome"]["multiscales"] == [{"name": "tissue"}]
    assert label_group.attrs["spatialdata_attrs"] == {"version": "0.3"}


def test_write_combined_zarr_names_each_dataset(monkeypatch, tmp_path):
    first = tmp_path / "sample_pos.imzML"
    second = tmp_path / "sample_neg.imzML"
    _write_imzml(first, "FTMS + p ESI Full ms [100.00-1000.00]")
    _write_imzml(second, "FTMS - p ESI Full ms [100.00-1000.00]")

    stores = {}
    calls = []
    written = {}

    class Table:
        def __init__(self):
            self.uns = {}

    class SourceData:
        def __init__(self, dataset_id):
            self.images = {f"{dataset_id}_z0_tic": object()}
            self.labels = {}
            self.points = {}
            self.shapes = {f"{dataset_id}_z0_pixels": object()}
            self.tables = {f"{dataset_id}_z0": Table()}
            self.attrs = {
                "coordinate_systems": {"global": {"unit": "micrometer"}},
                "msi_dataset_info": {"dataset_id": dataset_id},
            }

    def convert_msi(*, input_path, output_path, dataset_id, **options):
        calls.append((Path(input_path), dataset_id, options))
        Path(output_path).mkdir()
        stores[Path(output_path)] = SourceData(dataset_id)
        return True

    def read_zarr(path):
        return stores[Path(path)]

    class SpatialData:
        def __init__(self, **collections):
            self.collections = collections
            self.attrs = {}

        def write(self, path):
            Path(path).mkdir()
            written["object"] = self

    monkeypatch.setattr(
        zarr_writer,
        "_load_zarr_dependencies",
        lambda: (convert_msi, read_zarr, SpatialData),
    )

    output = tmp_path / "combined.zarr"
    result = zarr_writer.write_combined_zarr(
        tmp_path, output, thyra_options={"streaming": False}
    )

    assert result == output.resolve()
    assert output.is_dir()
    dataset_ids = [call[1] for call in calls]
    assert dataset_ids == [
        "Negative_fullscan",
        "Positive_fullscan",
    ]
    assert all(call[2]["streaming"] is False for call in calls)
    assert all(call[2]["resampling_config"] == {} for call in calls)
    assert set(written["object"].collections["tables"]) == {
        f"{dataset_id}_z0" for dataset_id in dataset_ids
    }
    assert "msi_dataset_info" not in written["object"].attrs
    assert {
        value["scan_filter"]
        for value in written["object"].attrs["imzml_writer_scan_filters"].values()
    } == {
        "FTMS + p ESI Full ms [100.00-1000.00]",
        "FTMS - p ESI Full ms [100.00-1000.00]",
    }
    assert {
        value["display_name"]
        for value in written["object"].attrs["imzml_writer_scan_filters"].values()
    } == {
        "Positive fullscan",
        "Negative fullscan",
    }
    assert {
        table.uns["coregistration_display_name"]
        for table in written["object"].collections["tables"].values()
    } == {"Positive fullscan", "Negative fullscan"}


def test_existing_output_is_not_overwritten(tmp_path):
    source = tmp_path / "source.imzML"
    _write_imzml(source, "filter")
    output = tmp_path / "combined.zarr"
    output.mkdir()

    with pytest.raises(FileExistsError):
        zarr_writer.write_combined_zarr(source, output)


def test_reserved_thyra_options_are_rejected(tmp_path):
    source = tmp_path / "source.imzML"
    _write_imzml(source, "filter")

    with pytest.raises(ValueError, match="dataset_id"):
        zarr_writer.write_combined_zarr(
            source,
            tmp_path / "combined.zarr",
            thyra_options={"dataset_id": "override"},
        )


def test_prepare_optical_array_normalizes_channels():
    class FakeNumpy:
        newaxis = None

        @staticmethod
        def moveaxis(value, source, destination):
            assert (source, destination) == (-1, 0)
            return value.moved

    class Image:
        def __init__(self, shape, moved=None):
            self.shape = shape
            self.ndim = len(shape)
            self.moved = moved

        def __getitem__(self, key):
            assert key == (None, slice(None), slice(None))
            return "grayscale-with-channel"

    assert (
        zarr_writer._prepare_optical_array(Image((10, 20)), FakeNumpy)
        == "grayscale-with-channel"
    )
    assert (
        zarr_writer._prepare_optical_array(
            Image((10, 20, 3), moved="channels-first"), FakeNumpy
        )
        == "channels-first"
    )


def test_tiff_pixel_size_prefers_ome_physical_metadata():
    class Tiff:
        ome_metadata = (
            '<OME xmlns="http://www.openmicroscopy.org/Schemas/OME/2016-06">'
            '<Image><Pixels PhysicalSizeX="2500" PhysicalSizeXUnit="nm" '
            'PhysicalSizeY="0.0025" PhysicalSizeYUnit="mm"/></Image></OME>'
        )
        pages = []

    assert zarr_writer._tiff_pixel_size_um(Tiff()) == (2.5, 2.5)


def test_add_optical_image_uses_dialog_and_writes_element(monkeypatch, tmp_path):
    store = tmp_path / "combined.zarr"
    store.mkdir()
    tiff = tmp_path / "Optical Image.tiff"
    tiff.write_bytes(b"fake TIFF")
    calls = {}

    class Array:
        shape = (4, 5)
        ndim = 2

        def __getitem__(self, key):
            assert key == (None, slice(None), slice(None))
            result = Array()
            result.shape = (1, 4, 5)
            result.ndim = 3
            return result

    class Numpy:
        newaxis = None

        @staticmethod
        def arange(value):
            return list(range(value))

    class Page:
        @staticmethod
        def asarray():
            return Array()

    class TiffFile:
        pages = [Page()]

        def __init__(self, path):
            calls["tiff_path"] = path

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

    Tifffile = type("Tifffile", (), {"TiffFile": TiffFile})

    class Xarray:
        @staticmethod
        def DataArray(image, **kwargs):
            calls["data_array"] = (image, kwargs)
            return "data-array"

    class Image2DModel:
        @staticmethod
        def parse(data, **kwargs):
            calls["parse"] = (data, kwargs)
            return "parsed-image"

    class Identity:
        pass

    class SpatialData:
        def __init__(self):
            self.images = {}
            self.elements = {}
            self.attrs = {}

        def __contains__(self, name):
            return name in self.elements

        def __setitem__(self, name, value):
            self.images[name] = value
            self.elements[name] = value

        def write_element(self, name, overwrite=False):
            calls["write"] = (name, overwrite)

        def write_attrs(self):
            calls["write_attrs"] = True

    spatial_data = SpatialData()
    monkeypatch.setattr(zarr_writer, "_select_tiff_file", lambda: tiff)
    monkeypatch.setattr(
        zarr_writer,
        "_load_optical_dependencies",
        lambda: (Numpy, Tifffile, Xarray, lambda path: spatial_data, Image2DModel, Identity),
    )

    name = zarr_writer.add_optical_image(store, pixel_size_um=2.5)

    assert name == "optical_Optical_Image"
    assert calls["tiff_path"] == tiff
    assert calls["parse"][1]["transformations"].keys() == {"optical"}
    assert calls["write"] == (name, False)
    assert calls["write_attrs"] is True
    assert spatial_data.attrs["imzml_writer_optical_images"][name][
        "pixel_size_um"
    ] == [2.5, 2.5]


def test_phase_translation_recovers_known_shift():
    import cv2
    import numpy as np

    fixed = np.zeros((128, 128), dtype=np.float32)
    fixed[35:75, 20:65] = 1
    moving = np.roll(np.roll(fixed, 13, axis=1), -9, axis=0)

    dx, dy, response = zarr_writer._phase_translation(fixed, moving, cv2, np)

    assert dx == pytest.approx(-13, abs=0.2)
    assert dy == pytest.approx(9, abs=0.2)
    assert response > 0.5


def test_mask_overlap_translation_is_linear_not_wrapping():
    import cv2
    import numpy as np

    fixed = np.zeros((32, 80), dtype=np.float32)
    fixed[9:24, 10:42] = 1
    moving = np.zeros_like(fixed)
    moving[3:18, 37:69] = 1

    dx, dy, dice, transformed = zarr_writer._mask_overlap_translation(
        fixed, moving, cv2, np
    )

    assert dx == -27
    assert dy == 6
    assert dice == pytest.approx(1)
    assert np.array_equal(transformed, fixed)


def test_mask_overlap_translation_penalizes_off_canvas_solution():
    import cv2
    import numpy as np

    fixed = np.zeros((20, 30), dtype=np.float32)
    fixed[5:15, 2:12] = 1
    moving = np.ones_like(fixed)

    dx, dy, dice, transformed = zarr_writer._mask_overlap_translation(
        fixed, moving, cv2, np
    )

    # Every placement covering the fixed square has the same intersection, but
    # the zero shift is the only one that retains the complete moving mask.
    assert (dx, dy) == (0, 0)
    assert dice == pytest.approx(2 * 100 / (100 + 600))
    assert transformed.sum() == moving.sum()


def test_mask_overlap_translation_accepts_physical_resampling_shape():
    import cv2
    import numpy as np

    fixed = np.zeros((30, 80), dtype=np.float32)
    fixed[8:23, 20:60] = 1
    moving = np.ones((15, 40), dtype=np.float32)

    dx, dy, dice, transformed = zarr_writer._mask_overlap_translation(
        fixed, moving, cv2, np
    )

    assert (dx, dy) == (20, 8)
    assert dice == pytest.approx(1)
    assert transformed.sum() == 600


def test_detected_msi_pixel_size_keeps_independent_axes():
    class SpatialData:
        attrs = {
            "pixel_size_x_um": 43.27,
            "pixel_size_y_um": 43.27,
            "pixel_size_detection_info": {
                "detected_x_um": 43.27,
                "detected_y_um": 150,
            },
        }

    assert zarr_writer._detected_msi_pixel_size(SpatialData()) == (43.27, 150)


def test_nmi_and_ncc_prefer_matching_translation():
    import numpy as np

    fixed = np.zeros((20, 30), dtype=np.float32)
    fixed[4:16, 6:22] = np.arange(192, dtype=np.float32).reshape(12, 16)
    moving = fixed[4:16, 6:22].copy()
    fixed = zarr_writer._display_normalize(fixed, np)
    moving = zarr_writer._display_normalize(moving, np)
    fixed_mask = fixed > 0
    moving_mask = np.ones_like(moving)

    aligned = zarr_writer._intensity_registration_metrics(
        fixed, moving, fixed_mask, moving_mask, 6, 4, np
    )
    displaced = zarr_writer._intensity_registration_metrics(
        fixed, moving, fixed_mask, moving_mask, 10, 7, np
    )

    assert aligned[0] > displaced[0]
    assert aligned[1] > displaced[1]


def test_intensity_refinement_can_escape_bad_coarse_translation():
    import cv2
    import numpy as np

    random = np.random.default_rng(4)
    moving = random.random((15, 40), dtype=np.float32)
    fixed = np.zeros((30, 80), dtype=np.float32)
    fixed[8:23, 20:60] = moving
    fixed_mask = np.zeros_like(fixed)
    fixed_mask[8:23, 20:60] = 1
    moving_mask = np.ones_like(moving)

    dx, dy, nmi, ncc, dice, _ = zarr_writer._refine_intensity_translation(
        fixed,
        moving,
        fixed_mask,
        moving_mask,
        coarse_translation=(50, 8),
        coarse_dice=0.4,
        radius=(80, 30),
        cv2=cv2,
        np=np,
    )

    assert (dx, dy) == (20, 8)
    assert nmi > 0.8
    assert ncc > 0.99
    assert dice == pytest.approx(1)


def test_display_normalize_is_robust_to_outlier():
    import numpy as np

    image = np.arange(100, dtype=np.float32).reshape(10, 10)
    image[-1, -1] = 1_000_000

    normalized = zarr_writer._display_normalize(image, np)

    assert normalized.min() == 0
    assert normalized.max() == 1
    assert normalized[5, 5] > 0


def test_spectral_tissue_mask_clusters_complete_spectra():
    from types import SimpleNamespace

    import cv2
    import numpy as np
    import pandas as pd
    from scipy import sparse
    from sklearn.cluster import MiniBatchKMeans
    from sklearn.preprocessing import normalize

    coordinates = [(x, y) for y in range(5) for x in range(5)]
    spectra = [
        [0, 10, 4, 2] if 1 <= x <= 3 and 1 <= y <= 3 else [1, 0, 0, 0]
        for x, y in coordinates
    ]
    matrix = sparse.csr_matrix(spectra, dtype=np.float32)
    table = SimpleNamespace(
        X=matrix,
        obs=pd.DataFrame(
            {
                "x": [coordinate[0] for coordinate in coordinates],
                "y": [coordinate[1] for coordinate in coordinates],
            }
        ),
        n_obs=matrix.shape[0],
        n_vars=matrix.shape[1],
    )

    result = zarr_writer._spectral_tissue_mask(
        table, MiniBatchKMeans, normalize, cv2, np
    )

    tissue_mask, reliability, confidence = result
    assert tissue_mask.shape == (5, 5)
    assert tissue_mask.sum() == 9
    assert reliability > 0
    assert confidence.shape == (5, 5)
    assert confidence[2, 2] > confidence[0, 0]


def test_validated_roi_orders_rounds_and_clips():
    assert zarr_writer._validated_roi((90.8, 80.2, -4.1, 10.7), 80, 70) == (
        0,
        10,
        80,
        70,
    )


def test_validated_roi_rejects_empty_selection():
    with pytest.raises(ValueError, match="at least 2x2"):
        zarr_writer._validated_roi((4, 4, 4.5, 4.5), 20, 20)


def test_minimum_tissue_votes_is_validated_before_clustering(monkeypatch, tmp_path):
    store = tmp_path / "combined.zarr"
    store.mkdir()

    class SpatialData:
        images = {"optical": object(), "scan_z0_tic": object()}
        tables = {}

    dependencies = (None,) * 11
    dependencies = (
        dependencies[0],
        dependencies[1],
        dependencies[2],
        lambda path: SpatialData(),
        *dependencies[4:],
    )
    monkeypatch.setattr(
        zarr_writer, "_load_registration_dependencies", lambda: dependencies
    )

    with pytest.raises(ValueError, match="between 1"):
        zarr_writer.coregister_optical_image(
            store, "optical", minimum_tissue_votes=2, save=False
        )
