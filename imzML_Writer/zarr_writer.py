"""Utilities for combining imzML scan filters in one Thyra Zarr store."""

from __future__ import annotations

import hashlib
import os
import re
import tempfile
import warnings
import xml.etree.ElementTree as ET
from collections.abc import Iterable, Mapping
from contextlib import contextmanager
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any


_SCAN_FILTER_ACCESSION = "MS:1000512"
_SPATIALDATA_COLLECTIONS = ("images", "labels", "points", "shapes", "tables")


@contextmanager
def _suppress_known_zarr_warnings():
    """Hide non-actionable warnings from the SpatialData/Zarr v3 stack."""
    with warnings.catch_warnings():
        warnings.filterwarnings(
            "ignore",
            message=r"Object at .* is not recognized as a component of a Zarr hierarchy.*",
            category=UserWarning,
        )
        warnings.filterwarnings(
            "ignore",
            message=(
                r"Consolidated metadata is currently not part in the Zarr "
                r"format 3 specification.*"
            ),
            category=UserWarning,
        )
        yield


def _remove_orphaned_ome_label_marker(label_group: Any) -> bool:
    """Remove the optional OME label marker when it has no parent image."""
    attributes = dict(label_group.attrs)
    ome = dict(attributes.get("ome", {}))
    image_label = ome.get("image-label")
    if not isinstance(image_label, dict) or image_label.get("source", {}).get(
        "image"
    ):
        return False
    # SpatialData labels are standalone elements in /labels, whereas OME-Zarr's
    # image-label marker promises a parent image. SpatialData 0.8 emits the
    # marker without a source; ome-zarr consequently logs "no parent found".
    # The multiscales and spatialdata_attrs metadata fully describe this label.
    ome.pop("image-label")
    label_group.attrs["ome"] = ome
    return True


def repair_standalone_label_metadata(zarr_path: str | Path) -> tuple[str, ...]:
    """Silence invalid OME parent warnings on standalone SpatialData labels."""
    import zarr

    store = Path(zarr_path).resolve()
    if not store.is_dir():
        raise ValueError(f"Not an existing Zarr store: {store}")
    repaired = []
    with _suppress_known_zarr_warnings():
        root = zarr.open_group(str(store), mode="r+", use_consolidated=False)
        labels = root.get("labels")
        if labels is not None:
            for name in labels.keys():
                if _remove_orphaned_ome_label_marker(labels[name]):
                    repaired.append(str(name))
        if repaired:
            zarr.consolidate_metadata(str(store))
    return tuple(repaired)


def _load_zarr_dependencies():
    """Import optional, heavyweight dependencies only when Zarr is requested."""
    try:
        from spatialdata import SpatialData, read_zarr
        from thyra import convert_msi
    except ImportError as exc:
        raise ImportError(
            "Combined Zarr output requires Python 3.12 or 3.13 and the optional Zarr "
            "dependencies. Install them with `pip install 'imzML-Writer[zarr]'`."
        ) from exc
    return convert_msi, read_zarr, SpatialData


def _load_optical_dependencies():
    """Import the image-specific pieces of the optional Zarr stack."""
    try:
        import numpy as np
        import tifffile
        import xarray as xr
        from spatialdata import read_zarr
        from spatialdata.models import Image2DModel
        from spatialdata.transformations import Identity
    except ImportError as exc:
        raise ImportError(
            "Adding an optical image requires Python 3.12 or 3.13 and the "
            "optional Zarr dependencies. Install them with "
            "`pip install 'imzML-Writer[zarr]'`."
        ) from exc
    return np, tifffile, xr, read_zarr, Image2DModel, Identity


def _load_registration_dependencies():
    """Import image-registration dependencies only when they are needed."""
    try:
        import cv2
        import numpy as np
        import zarr
        from spatialdata import read_zarr
        from spatialdata.transformations import (
            Scale,
            Sequence,
            Translation,
            get_transformation,
            set_transformation,
        )
        from sklearn.cluster import MiniBatchKMeans
        from sklearn.preprocessing import normalize
    except ImportError as exc:
        raise ImportError(
            "Optical coregistration requires the optional Zarr dependencies. "
            "Install them with `pip install 'imzML-Writer[zarr]'`."
        ) from exc
    return (
        cv2,
        np,
        zarr,
        read_zarr,
        Scale,
        Sequence,
        Translation,
        get_transformation,
        set_transformation,
        MiniBatchKMeans,
        normalize,
    )


def _select_tiff_file() -> Path:
    """Open a native file dialog and return the selected TIFF path."""
    from tkinter import Tk, filedialog

    root = Tk()
    root.withdraw()
    try:
        selected = filedialog.askopenfilename(
            title="Select an optical TIFF image",
            filetypes=[("TIFF images", ("*.tif", "*.tiff")), ("All files", "*")],
        )
    finally:
        root.destroy()
    if not selected:
        raise ValueError("No optical image was selected")
    return Path(selected)


def _safe_element_name(value: str) -> str:
    """Return a SpatialData-safe element name."""
    name = re.sub(r"[^0-9A-Za-z._-]+", "_", value).strip("._-")
    return re.sub(r"_+", "_", name) or "optical_image"


def _prepare_optical_array(image: Any, np: Any) -> Any:
    """Normalize grayscale and RGB(A) TIFF arrays to ``(c, y, x)``."""
    if image.ndim == 2:
        return image[np.newaxis, :, :]
    if image.ndim != 3:
        raise ValueError(
            f"Optical TIFF must be 2D grayscale or RGB(A); got shape {image.shape}"
        )
    if image.shape[-1] in (3, 4):
        return np.moveaxis(image, -1, 0)
    if image.shape[0] in (1, 3, 4):
        return image
    raise ValueError(
        "Could not identify the channel axis in optical TIFF with shape "
        f"{image.shape}"
    )


def _tiff_pixel_size_um(tiff: Any) -> tuple[float, float] | None:
    """Read physical x/y spacing from OME-XML or calibrated TIFF tags."""
    ome_metadata = getattr(tiff, "ome_metadata", None)
    if ome_metadata:
        try:
            root = ET.fromstring(ome_metadata)
            pixels = next(
                element
                for element in root.iter()
                if element.tag.rsplit("}", 1)[-1] == "Pixels"
            )
            x_size = float(pixels.attrib["PhysicalSizeX"])
            y_size = float(pixels.attrib.get("PhysicalSizeY", x_size))
            units = {
                "m": 1_000_000,
                "mm": 1_000,
                "µm": 1,
                "um": 1,
                "nm": 0.001,
            }
            x_factor = units[pixels.attrib.get("PhysicalSizeXUnit", "µm")]
            y_factor = units[pixels.attrib.get("PhysicalSizeYUnit", "µm")]
            return _pixel_size_pair(
                (x_size * x_factor, y_size * y_factor), "OME pixel size"
            )
        except (KeyError, StopIteration, TypeError, ValueError, ET.ParseError):
            pass

    page = tiff.pages[0]
    tags = getattr(page, "tags", {})
    x_tag = tags.get("XResolution")
    y_tag = tags.get("YResolution")
    unit_tag = tags.get("ResolutionUnit")
    if x_tag is None or y_tag is None or unit_tag is None:
        return None
    unit_value = int(unit_tag.value)
    micrometers_per_unit = {2: 25_400.0, 3: 10_000.0}.get(unit_value)
    if micrometers_per_unit is None:
        return None

    def pixels_per_unit(tag: Any) -> float:
        value = tag.value
        if isinstance(value, tuple):
            return float(value[0]) / float(value[1])
        return float(value)

    try:
        return _pixel_size_pair(
            (
                micrometers_per_unit / pixels_per_unit(x_tag),
                micrometers_per_unit / pixels_per_unit(y_tag),
            ),
            "TIFF pixel size",
        )
    except (TypeError, ValueError, ZeroDivisionError):
        return None


def add_optical_image(
    zarr_path: str | Path,
    tiff_path: str | Path | None = None,
    *,
    image_name: str | None = None,
    pixel_size_um: float | tuple[float, float] | None = None,
    overwrite: bool = False,
) -> str:
    """Add an optical TIFF image to an existing SpatialData/Zarr store.

    If ``tiff_path`` is omitted, a native file-selection dialog is opened. The
    image is added in its own ``"optical"`` coordinate system because a TIFF
    alone contains no registration mapping to the MSI ``"global"`` system.

    Args:
        zarr_path: Existing Zarr store to update.
        tiff_path: TIFF image path, or ``None`` to choose one with a file dialog.
        image_name: SpatialData element name. Defaults to ``optical_<TIFF stem>``.
        pixel_size_um: Optical x/y pixel spacing in micrometers. A scalar means
            square pixels. Saving it here lets coregistration use physical scale.
        overwrite: Replace an existing image with the same name when true.

    Returns:
        The name of the added SpatialData image element.
    """
    store = Path(zarr_path).resolve()
    if not store.is_dir():
        raise ValueError(f"Not an existing Zarr store: {store}")

    source = (
        Path(tiff_path) if tiff_path is not None else _select_tiff_file()
    ).resolve()
    if not source.is_file() or source.suffix.lower() not in {".tif", ".tiff"}:
        raise ValueError(f"Not a TIFF file: {source}")

    element_name = _safe_element_name(image_name or f"optical_{source.stem}")
    np, tifffile, xr, read_zarr, Image2DModel, Identity = (
        _load_optical_dependencies()
    )
    with _suppress_known_zarr_warnings():
        spatial_data = read_zarr(store)
    if element_name in spatial_data and not overwrite:
        raise FileExistsError(
            f"SpatialData element already exists: {element_name}"
        )
    if element_name in spatial_data and element_name not in spatial_data.images:
        raise ValueError(
            f"Cannot overwrite non-image SpatialData element: {element_name}"
        )

    with tifffile.TiffFile(source) as tiff:
        detected_pixel_size = _tiff_pixel_size_um(tiff)
        image = _prepare_optical_array(tiff.pages[0].asarray(), np)

    channels, height, width = image.shape
    data_array = xr.DataArray(
        image,
        dims=("c", "y", "x"),
        coords={
            "c": np.arange(channels),
            "y": np.arange(height),
            "x": np.arange(width),
        },
        attrs={"source_file": source.name, "original_path": str(source)},
    )
    optical_image = Image2DModel.parse(
        data_array,
        transformations={"optical": Identity()},
        chunks=(1, min(4096, height), min(4096, width)),
    )
    spatial_data[element_name] = optical_image
    spatial_data.write_element(element_name, overwrite=overwrite)
    pixel_size = (
        _pixel_size_pair(pixel_size_um, "pixel_size_um")
        if pixel_size_um is not None
        else detected_pixel_size
    )
    optical_metadata = dict(
        spatial_data.attrs.get("imzml_writer_optical_images", {})
    )
    element_metadata: dict[str, Any] = {
        "source_file": source.name,
        "original_path": str(source),
    }
    if pixel_size is not None:
        element_metadata["pixel_size_um"] = list(pixel_size)
        element_metadata["pixel_size_source"] = (
            "argument" if pixel_size_um is not None else "tiff_metadata"
        )
    optical_metadata[element_name] = element_metadata
    spatial_data.attrs["imzml_writer_optical_images"] = optical_metadata
    spatial_data.write_attrs()
    return element_name


@dataclass(frozen=True)
class FourierRegistrationResult:
    """Summary of an estimated optical-to-ion translation."""

    optical_image: str
    ion_images: tuple[str, ...]
    translation_pixels: tuple[float, float]
    optical_to_ion_scale: tuple[float, float]
    msi_pixel_size_um: tuple[float, float]
    optical_pixel_size_um: tuple[float, float]
    correlation: float
    dice_overlap: float
    mutual_information: float
    normalized_cross_correlation: float
    registration_method: str
    optical_tissue_cluster: str
    msi_segmentation: str
    minimum_tissue_votes: int | None
    filter_weights: tuple[float, ...]
    optical_roi: tuple[int, int, int, int]
    tissue_label: str
    saved: bool


def _data_array_from_image(element: Any) -> Any:
    """Return the highest-resolution DataArray from a SpatialData image."""
    if hasattr(element, "dims") and hasattr(element, "data"):
        return element
    try:
        scale_zero = element["scale0"]
        dataset = scale_zero.ds
        return next(iter(dataset.data_vars.values()))
    except (KeyError, AttributeError, StopIteration) as exc:
        raise ValueError("Could not read a raster array from the SpatialData image") from exc


def _pixel_size_pair(
    value: float | tuple[float, float] | list[float], name: str
) -> tuple[float, float]:
    """Validate scalar or x/y physical pixel spacing."""
    if isinstance(value, (int, float)):
        pair = (float(value), float(value))
    else:
        if len(value) != 2:
            raise ValueError(f"{name} must be a scalar or an (x, y) pair")
        pair = (float(value[0]), float(value[1]))
    if not all(size > 0 for size in pair):
        raise ValueError(f"{name} values must be positive")
    return pair


def _detected_msi_pixel_size(spatial_data: Any) -> tuple[float, float] | None:
    """Read Thyra's detected imzML x/y spacing without assuming isotropy."""
    info = spatial_data.attrs.get("pixel_size_detection_info", {})
    x_size = info.get("detected_x_um")
    y_size = info.get("detected_y_um")
    if x_size is None or y_size is None:
        x_size = spatial_data.attrs.get("pixel_size_x_um")
        y_size = spatial_data.attrs.get("pixel_size_y_um")
    if x_size is None or y_size is None:
        return None
    return _pixel_size_pair((x_size, y_size), "detected MSI pixel size")


def _grayscale_image(element: Any, np: Any) -> Any:
    """Materialize a SpatialData image and reduce its channels to grayscale."""
    data_array = _data_array_from_image(element)
    values = data_array.data
    if hasattr(values, "compute"):
        values = values.compute()
    values = np.asarray(values)

    if values.ndim == 2:
        return values.astype(np.float32)
    if values.ndim != 3:
        raise ValueError(f"Expected a 2D image, got shape {values.shape}")

    dims = tuple(str(dim) for dim in data_array.dims)
    channel_axis = dims.index("c") if "c" in dims else 0
    channels_first = np.moveaxis(values, channel_axis, 0)
    if channels_first.shape[0] >= 3:
        return (
            0.2126 * channels_first[0]
            + 0.7152 * channels_first[1]
            + 0.0722 * channels_first[2]
        ).astype(np.float32)
    return channels_first.mean(axis=0, dtype=np.float32)


def _kmeans_tissue_masks(image: Any, cv2: Any, np: Any) -> tuple[Any, Any]:
    """Return masks for the darker and brighter clusters from two-class k-means."""
    image = np.asarray(image, dtype=np.float32)
    finite = np.isfinite(image)
    if not finite.any():
        raise ValueError("Cannot segment an image containing no finite values")
    low = float(np.nanmin(image))
    high = float(np.nanmax(image))
    if high <= low:
        raise ValueError("Cannot segment a constant image")
    normalized = np.where(finite, (image - low) / (high - low), 0.0)

    flat = normalized.reshape(-1, 1)
    stride = max(1, len(flat) // 250_000)
    sample = np.ascontiguousarray(flat[::stride])
    cv2.setRNGSeed(0)
    _, _, centers = cv2.kmeans(
        sample,
        2,
        None,
        (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 50, 1e-4),
        5,
        cv2.KMEANS_PP_CENTERS,
    )
    centers = centers.reshape(-1)
    labels = np.abs(flat - centers.reshape(1, 2)).argmin(axis=1).reshape(image.shape)
    dark_label = int(np.argmin(centers))
    bright_label = int(np.argmax(centers))

    def clean(label: int) -> Any:
        mask = (labels == label).astype(np.uint8)
        radius = max(1, min(image.shape) // 250)
        kernel = np.ones((radius * 2 + 1, radius * 2 + 1), dtype=np.uint8)
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
        return cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel).astype(np.float32)

    return clean(dark_label), clean(bright_label)


def _phase_translation(fixed: Any, moving: Any, cv2: Any, np: Any) -> tuple[float, float, float]:
    """Estimate the translation to apply to ``moving`` to align it to ``fixed``."""
    fixed = np.ascontiguousarray(fixed, dtype=np.float32)
    moving = np.ascontiguousarray(moving, dtype=np.float32)
    window = cv2.createHanningWindow((fixed.shape[1], fixed.shape[0]), cv2.CV_32F)
    shift, response = cv2.phaseCorrelate(fixed, moving, window)
    return -float(shift[0]), -float(shift[1]), float(response)


def _mask_overlap_translation(
    fixed: Any, moving: Any, cv2: Any, np: Any
) -> tuple[float, float, float, Any]:
    """Find the non-wrapping translation with maximum binary-mask overlap.

    Phase correlation assumes periodic images, so its highest peak can move most
    of a sparse tissue mask through one edge and back through the other. Padding
    the fixed mask allows an exhaustive linear cross-correlation instead. The
    Dice denominator includes the complete moving mask, which also penalizes
    solutions that leave much of the optical tissue outside the MSI canvas.
    """
    fixed = (np.asarray(fixed) > 0.5).astype(np.float32)
    moving = (np.asarray(moving) > 0.5).astype(np.float32)
    if fixed.ndim != 2 or moving.ndim != 2:
        raise ValueError("Tissue masks must both be two-dimensional")
    if not fixed.any() or not moving.any():
        raise ValueError("Cannot register an empty tissue mask")

    height, width = fixed.shape
    moving_height, moving_width = moving.shape
    padded = cv2.copyMakeBorder(
        fixed,
        moving_height - 1,
        moving_height - 1,
        moving_width - 1,
        moving_width - 1,
        cv2.BORDER_CONSTANT,
        value=0,
    )
    overlap = cv2.matchTemplate(padded, moving, cv2.TM_CCORR)
    padded_canvas = cv2.copyMakeBorder(
        np.ones_like(fixed),
        moving_height - 1,
        moving_height - 1,
        moving_width - 1,
        moving_width - 1,
        cv2.BORDER_CONSTANT,
        value=0,
    )
    retained = cv2.matchTemplate(padded_canvas, moving, cv2.TM_CCORR)
    valid = retained >= 0.6 * float(moving.sum())
    valid_overlap = np.where(valid, overlap, -np.inf)
    intersection = float(valid_overlap.max())
    # Several placements can cover the same fixed mask. Prefer the one that
    # retains the most optical tissue instead of OpenCV's first (top-left) tie.
    tied = valid & np.isclose(overlap, intersection, rtol=0, atol=1e-4)
    retained_ties = np.where(tied, retained, -np.inf)
    _, _, _, location = cv2.minMaxLoc(retained_ties.astype(np.float32))
    dx = float(location[0] - (moving_width - 1))
    dy = float(location[1] - (moving_height - 1))
    dice = 2.0 * intersection / float(fixed.sum() + moving.sum())

    matrix = np.array([[1, 0, dx], [0, 1, dy]], dtype=np.float32)
    transformed = cv2.warpAffine(
        moving,
        matrix,
        (width, height),
        flags=cv2.INTER_NEAREST,
        borderMode=cv2.BORDER_CONSTANT,
        borderValue=0,
    )
    return dx, dy, min(1.0, max(0.0, dice)), transformed


def _spectral_tissue_mask(
    table: Any,
    MiniBatchKMeans: Any,
    normalize: Any,
    cv2: Any,
    np: Any,
) -> tuple[Any, float, Any]:
    """Return a full-spectrum tissue mask, reliability, and soft confidence."""
    if "x" not in table.obs or "y" not in table.obs:
        raise ValueError("MSI table has no x/y pixel coordinates")
    if table.n_obs < 2 or table.n_vars < 1:
        raise ValueError("MSI table is too small for two-class clustering")

    spectra = table.X.tocsr().astype(np.float32, copy=True)
    # Negative baseline-corrected values are not evidence of tissue here. Log
    # compression limits a few abundant ions without discarding any m/z column.
    spectra.data = np.log1p(np.maximum(spectra.data, 0))
    spectra.eliminate_zeros()
    total_signal = np.asarray(spectra.sum(axis=1)).reshape(-1)
    normalize(spectra, norm="l2", axis=1, copy=False)

    seed_rows = [int(np.argmin(total_signal)), int(np.argmax(total_signal))]
    initial_centers = spectra[seed_rows].toarray()
    model = MiniBatchKMeans(
        n_clusters=2,
        random_state=0,
        init=initial_centers,
        n_init=1,
        batch_size=min(1024, table.n_obs),
        max_iter=100,
        reassignment_ratio=0.01,
    )
    previous_cpu_count = os.environ.get("LOKY_MAX_CPU_COUNT")
    # Avoid loky's unreliable macOS physical-core probe. MSI tables here are
    # small in row count and sparse in columns, so one worker also avoids
    # oversubscribing BLAS for this short two-cluster fit.
    os.environ["LOKY_MAX_CPU_COUNT"] = "1"
    try:
        labels = model.fit_predict(spectra)
    finally:
        if previous_cpu_count is None:
            os.environ.pop("LOKY_MAX_CPU_COUNT", None)
        else:
            os.environ["LOKY_MAX_CPU_COUNT"] = previous_cpu_count
    x = np.asarray(table.obs["x"], dtype=int)
    y = np.asarray(table.obs["y"], dtype=int)
    if np.any(x < 0) or np.any(y < 0):
        raise ValueError("MSI table contains negative raster coordinates")
    masks = []
    scores = []
    for label in range(2):
        mask = np.zeros((int(y.max()) + 1, int(x.max()) + 1), dtype=np.uint8)
        mask[y, x] = labels == label
        area = int(mask.sum())
        component_count, _, stats, _ = cv2.connectedComponentsWithStats(
            mask, connectivity=8
        )
        largest_component = (
            int(stats[1:, cv2.CC_STAT_AREA].max())
            if component_count > 1
            else 0
        )
        border = np.concatenate((mask[0], mask[-1], mask[:, 0], mask[:, -1]))
        border_fraction = float(border.mean())
        occupancy = float(mask.mean())
        coherence = largest_component / max(area, 1)
        # Tissue should form one or a few coherent islands, should not occupy
        # nearly the whole border, and should leave some background visible.
        score = coherence * (1 - border_fraction) * 4 * occupancy * (1 - occupancy)
        masks.append(mask.astype(np.float32))
        scores.append(float(score))

    tissue_label = int(np.argmax(scores))
    distances = model.transform(spectra)
    other_label = 1 - tissue_label
    denominator = distances[:, tissue_label] + distances[:, other_label]
    confidence_values = np.divide(
        distances[:, other_label],
        denominator,
        out=np.full(table.n_obs, 0.5, dtype=np.float32),
        where=denominator > 0,
    )
    confidence = np.zeros_like(masks[tissue_label], dtype=np.float32)
    confidence[y, x] = confidence_values
    return masks[tissue_label], scores[tissue_label], confidence


def _display_normalize(image: Any, np: Any) -> Any:
    """Robustly normalize an image to [0, 1] for registration preview."""
    image = np.asarray(image, dtype=np.float32)
    finite = image[np.isfinite(image)]
    if not finite.size:
        return np.zeros_like(image)
    low, high = np.percentile(finite, (1, 99))
    if high <= low:
        low, high = float(finite.min()), float(finite.max())
    if high <= low:
        return np.zeros_like(image)
    return np.clip((image - low) / (high - low), 0, 1)


def _translation_views(
    fixed: Any, moving: Any, dx: int, dy: int
) -> tuple[Any, Any] | None:
    """Return overlapping fixed/moving views for an integer translation."""
    fixed_height, fixed_width = fixed.shape
    moving_height, moving_width = moving.shape
    fixed_x0 = max(0, dx)
    fixed_y0 = max(0, dy)
    moving_x0 = max(0, -dx)
    moving_y0 = max(0, -dy)
    width = min(fixed_width - fixed_x0, moving_width - moving_x0)
    height = min(fixed_height - fixed_y0, moving_height - moving_y0)
    if width <= 0 or height <= 0:
        return None
    return (
        fixed[fixed_y0 : fixed_y0 + height, fixed_x0 : fixed_x0 + width],
        moving[
            moving_y0 : moving_y0 + height, moving_x0 : moving_x0 + width
        ],
    )


def _normalized_mutual_information(first: Any, second: Any, np: Any) -> float:
    """Calculate symmetric normalized mutual information for two vectors."""
    bins = min(32, max(8, int(np.sqrt(first.size / 5))))
    histogram, _, _ = np.histogram2d(
        first, second, bins=bins, range=((0, 1), (0, 1))
    )
    total = float(histogram.sum())
    if total <= 0:
        return 0.0
    joint = histogram / total
    first_probability = joint.sum(axis=1)
    second_probability = joint.sum(axis=0)
    nonzero = joint > 0
    independent = first_probability[:, None] * second_probability[None, :]
    mutual_information = float(
        (joint[nonzero] * np.log(joint[nonzero] / independent[nonzero])).sum()
    )

    def entropy(probability: Any) -> float:
        probability = probability[probability > 0]
        return float(-(probability * np.log(probability)).sum())

    entropy_sum = entropy(first_probability) + entropy(second_probability)
    return 2 * mutual_information / entropy_sum if entropy_sum > 0 else 0.0


def _intensity_registration_metrics(
    fixed: Any,
    moving: Any,
    fixed_mask: Any,
    moving_mask: Any,
    dx: int,
    dy: int,
    np: Any,
) -> tuple[float, float, float] | None:
    """Return NMI, absolute NCC, and conservative mask Dice at a shift."""
    image_views = _translation_views(fixed, moving, dx, dy)
    mask_views = _translation_views(fixed_mask, moving_mask, dx, dy)
    if image_views is None or mask_views is None:
        return None
    fixed_view, moving_view = image_views
    fixed_mask_view, moving_mask_view = mask_views
    retained_fraction = moving_view.size / moving.size
    if retained_fraction < 0.6:
        return None

    region = (fixed_mask_view > 0.5) | (moving_mask_view > 0.5)
    if int(region.sum()) < 32:
        region = np.ones_like(region, dtype=bool)
    first = fixed_view[region].astype(np.float64)
    second = moving_view[region].astype(np.float64)
    nmi = _normalized_mutual_information(first, second, np)
    first -= first.mean()
    second -= second.mean()
    first_energy = float(np.sum(first * first, dtype=np.float64))
    second_energy = float(np.sum(second * second, dtype=np.float64))
    denominator = float(np.sqrt(first_energy * second_energy))
    numerator = float(np.sum(first * second, dtype=np.float64))
    ncc = abs(numerator / denominator) if denominator > 0 else 0.0
    intersection = float(
        np.logical_and(fixed_mask_view > 0.5, moving_mask_view > 0.5).sum()
    )
    dice = 2 * intersection / float(fixed_mask.sum() + moving_mask.sum())
    return nmi, ncc, dice


def _refine_intensity_translation(
    fixed: Any,
    moving: Any,
    fixed_mask: Any,
    moving_mask: Any,
    coarse_translation: tuple[float, float],
    coarse_dice: float,
    radius: tuple[int, int],
    cv2: Any,
    np: Any,
) -> tuple[float, float, float, float, float, Any]:
    """Refine a coarse shift with NMI/NCC while preserving tissue overlap."""
    fixed = _display_normalize(fixed, np)
    moving = _display_normalize(moving, np)
    center_x, center_y = (round(value) for value in coarse_translation)
    best = None
    for dy in range(center_y - radius[1], center_y + radius[1] + 1):
        for dx in range(center_x - radius[0], center_x + radius[0] + 1):
            metrics = _intensity_registration_metrics(
                fixed, moving, fixed_mask, moving_mask, dx, dy, np
            )
            if metrics is None:
                continue
            nmi, ncc, dice = metrics
            # The mask is deliberately only a safety floor here. Optical and
            # spectral masks can have very different outlines, so tying the
            # refinement to a fraction of the coarse Dice score can trap the
            # optimum at the edge of the search window.
            if dice < min(0.1, 0.25 * coarse_dice):
                continue
            score = nmi + 0.25 * ncc
            candidate = (score, nmi, ncc, dice, dx, dy)
            if best is None or candidate > best:
                best = candidate
    if best is None:
        raise ValueError("No valid translation remained during intensity refinement")
    _, nmi, ncc, dice, dx, dy = best
    matrix = np.array([[1, 0, dx], [0, 1, dy]], dtype=np.float32)
    transformed_mask = cv2.warpAffine(
        moving_mask,
        matrix,
        (fixed.shape[1], fixed.shape[0]),
        flags=cv2.INTER_NEAREST,
        borderMode=cv2.BORDER_CONSTANT,
        borderValue=0,
    )
    return float(dx), float(dy), nmi, ncc, dice, transformed_mask


def _validated_roi(
    roi: tuple[float, float, float, float], width: int, height: int
) -> tuple[int, int, int, int]:
    """Round, order, and clip an ``(x0, y0, x1, y1)`` image ROI."""
    import math

    x0, y0, x1, y1 = roi
    left = max(0, min(width, math.floor(min(x0, x1))))
    right = max(0, min(width, math.ceil(max(x0, x1))))
    top = max(0, min(height, math.floor(min(y0, y1))))
    bottom = max(0, min(height, math.ceil(max(y0, y1))))
    if right - left < 2 or bottom - top < 2:
        raise ValueError("The optical ROI must be at least 2x2 pixels")
    return left, top, right, bottom


def _select_optical_roi(
    optical_image: Any,
    msi_tissue_mask: Any,
    segmentation: str,
    msi_pixel_size_um: tuple[float, float],
    np: Any,
) -> tuple[int, int, int, int]:
    """Ask the user to select the optical region corresponding to the MSI FOV."""
    try:
        import matplotlib.pyplot as plt
        from matplotlib.widgets import Button, RectangleSelector
    except ImportError as exc:
        raise ImportError(
            "Interactive ROI selection requires matplotlib. Supply optical_roi="
            "(x0, y0, x1, y1) for non-interactive use."
        ) from exc

    optical_display = _display_normalize(optical_image, np)
    figure, axes = plt.subplots(1, 2, figsize=(13, 6))
    axes[0].imshow(
        msi_tissue_mask,
        cmap="gray",
        vmin=0,
        vmax=1,
        aspect=msi_pixel_size_um[1] / msi_pixel_size_um[0],
    )
    axes[0].set_title(f"MSI {segmentation} k-means tissue mask")
    axes[1].imshow(optical_display, cmap="gray")
    axes[1].set_title("Drag around the matching optical region")
    for axis in axes:
        axis.set_axis_off()
    figure.suptitle(
        "Coarse alignment: select the optical area represented by the MSI scan"
    )

    selection: dict[str, Any] = {"roi": None, "accepted": False}

    def on_select(click, release):
        selection["roi"] = (click.xdata, click.ydata, release.xdata, release.ydata)

    selector = RectangleSelector(
        axes[1],
        on_select,
        useblit=True,
        button=[1],
        minspanx=2,
        minspany=2,
        spancoords="pixels",
        interactive=True,
    )

    def use_selection(_event):
        if selection["roi"] is None:
            axes[1].set_title("Draw a rectangle before choosing Use selection")
            figure.canvas.draw_idle()
            return
        selection["accepted"] = True
        plt.close(figure)

    def use_full_image(_event):
        selection["roi"] = (0, 0, optical_image.shape[1], optical_image.shape[0])
        selection["accepted"] = True
        plt.close(figure)

    def cancel(_event):
        plt.close(figure)

    figure.subplots_adjust(bottom=0.16, top=0.86, wspace=0.06)
    select_axis = figure.add_axes((0.45, 0.035, 0.18, 0.065))
    full_axis = figure.add_axes((0.65, 0.035, 0.14, 0.065))
    cancel_axis = figure.add_axes((0.81, 0.035, 0.12, 0.065))
    select_button = Button(select_axis, "Use selection", color="#b6e3b6")
    full_button = Button(full_axis, "Use full image")
    cancel_button = Button(cancel_axis, "Cancel", color="#efb1b1")
    select_button.on_clicked(use_selection)
    full_button.on_clicked(use_full_image)
    cancel_button.on_clicked(cancel)
    figure._imzml_writer_widgets = (
        selector,
        select_button,
        full_button,
        cancel_button,
    )
    plt.show(block=True)

    if not selection["accepted"]:
        raise ValueError("Optical ROI selection was cancelled")
    return _validated_roi(
        selection["roi"], optical_image.shape[1], optical_image.shape[0]
    )


def _confirm_registration_preview(
    msi_tissue_mask: Any,
    transformed_optical: Any,
    ion_mask: Any,
    transformed_optical_mask: Any,
    result: FourierRegistrationResult,
    manual_alignment: Any | None = None,
) -> bool | tuple[float, float]:
    """Show an overlay preview and ask whether its transform should be saved."""
    try:
        import matplotlib.pyplot as plt
        import numpy as np
        from matplotlib.widgets import Button
    except ImportError as exc:
        raise ImportError(
            "Interactive registration preview requires matplotlib. "
            "Pass save=True or save=False for non-interactive use."
        ) from exc

    optical_display = _display_normalize(transformed_optical, np)
    physical_aspect = (
        result.msi_pixel_size_um[1] / result.msi_pixel_size_um[0]
    )
    mask_overlay = np.zeros((*ion_mask.shape, 3), dtype=np.float32)
    mask_overlay[..., 1] = ion_mask
    mask_overlay[..., 2] = ion_mask
    mask_overlay[..., 0] += transformed_optical_mask
    mask_overlay[..., 2] += transformed_optical_mask
    mask_overlay = np.clip(mask_overlay, 0, 1)

    figure, axes = plt.subplots(1, 2, figsize=(12, 6))
    axes[0].imshow(optical_display, cmap="gray", aspect=physical_aspect)
    axes[0].imshow(
        msi_tissue_mask,
        cmap="cool",
        alpha=0.42,
        vmin=0,
        vmax=1,
        aspect=physical_aspect,
    )
    axes[0].set_title("Optical + MSI clustered tissue")
    axes[1].imshow(mask_overlay, aspect=physical_aspect)
    msi_mask_label = (
        "spectral k-means"
        if result.msi_segmentation == "spectral"
        else "TIC k-means"
    )
    if result.minimum_tissue_votes is None:
        msi_mask_label += ", confidence weighted"
    else:
        msi_mask_label += (
            f", >= {result.minimum_tissue_votes}/{len(result.ion_images)} filters"
        )
    axes[1].set_title(
        f"Tissue masks: MSI {msi_mask_label} cyan, optical magenta"
    )
    for axis in axes:
        axis.set_axis_off()
    title = (
        f"Shift: ({result.translation_pixels[0]:.2f}, "
        f"{result.translation_pixels[1]:.2f}) ion pixels  |  "
        f"NMI: {result.mutual_information:.3f}  |  "
        f"|NCC|: {result.normalized_cross_correlation:.3f}  |  "
        f"mask Dice: {result.dice_overlap:.3f}\n"
        f"MSI pixels: {result.msi_pixel_size_um[0]:g} × "
        f"{result.msi_pixel_size_um[1]:g} µm  |  optical pixels: "
        f"{result.optical_pixel_size_um[0]:g} × "
        f"{result.optical_pixel_size_um[1]:g} µm"
    )
    warnings_text = []
    if (
        result.mutual_information < 0.03
        and result.normalized_cross_correlation < 0.15
    ):
        warnings_text.append("weak intensity agreement")
    if warnings_text:
        title += "\nWARNING: " + "; ".join(warnings_text)
        figure.suptitle(title, color="crimson", fontweight="bold")
    else:
        figure.suptitle(title)

    decision: dict[str, Any] = {"action": "discard"}

    def finish(action: str):
        def callback(_event):
            decision["action"] = action
            plt.close(figure)

        return callback

    figure.subplots_adjust(bottom=0.16, top=0.84, wspace=0.04)
    save_axis = figure.add_axes((0.38, 0.035, 0.18, 0.065))
    manual_axis = figure.add_axes((0.58, 0.035, 0.18, 0.065))
    discard_axis = figure.add_axes((0.78, 0.035, 0.16, 0.065))
    save_button = Button(save_axis, "Save automatic", color="#b6e3b6")
    manual_button = Button(manual_axis, "Manual override", color="#f1d58a")
    discard_button = Button(discard_axis, "Discard", color="#efb1b1")
    save_button.on_clicked(finish("save"))
    manual_button.on_clicked(finish("manual"))
    discard_button.on_clicked(finish("discard"))

    # Keep both Button objects alive until the native Matplotlib window closes.
    figure._imzml_writer_buttons = (save_button, manual_button, discard_button)
    try:
        plt.show(block=True)
    finally:
        plt.close(figure)
    if decision["action"] == "manual":
        return manual_alignment() if manual_alignment is not None else False
    return decision["action"] == "save"


def _manual_translation_from_ion_drag(
    automatic_translation: tuple[float, float],
    ion_drag: tuple[float, float],
) -> tuple[float, float]:
    """Convert an ion-layer drag into the equivalent optical translation."""
    return (
        float(automatic_translation[0] - ion_drag[0]),
        float(automatic_translation[1] - ion_drag[1]),
    )


def _manual_registration_preview(
    transformed_optical: Any,
    ion_sources: list[dict[str, Any]],
    result: FourierRegistrationResult,
    np: Any,
) -> tuple[float, float] | None:
    """Let the user choose an m/z and drag its ion image over the optical."""
    try:
        import matplotlib.pyplot as plt
        from matplotlib.transforms import Affine2D
        from matplotlib.widgets import Button, TextBox
    except ImportError as exc:
        raise ImportError(
            "Manual registration requires matplotlib."
        ) from exc
    if not ion_sources:
        raise ValueError("No MSI tables are available for manual registration")

    physical_aspect = result.msi_pixel_size_um[1] / result.msi_pixel_size_um[0]
    figure, axis = plt.subplots(figsize=(11, 7))
    figure.subplots_adjust(bottom=0.24, top=0.88)
    axis.imshow(
        _display_normalize(transformed_optical, np),
        cmap="gray",
        aspect=physical_aspect,
    )
    state: dict[str, Any] = {
        "source_index": 0,
        "mz_values": [],
        "mz_index": 0,
        "drag": [0.0, 0.0],
        "press": None,
        "accepted": False,
        "translation": None,
    }

    def source_image(source: dict[str, Any], target_mz: float | None):
        if target_mz is None:
            return source["tic"], None
        mz_axis = source["mz"]
        feature_index = int(np.abs(mz_axis - target_mz).argmin())
        column = source["table"].X[:, feature_index]
        values = (
            np.asarray(column.toarray()).ravel()
            if hasattr(column, "toarray")
            else np.asarray(column).ravel()
        )
        image = np.zeros(source["shape"], dtype=np.float32)
        image[source["y"], source["x"]] = values
        return image, float(mz_axis[feature_index])

    initial_source = ion_sources[0]
    ion_artist = axis.imshow(
        np.ma.masked_less_equal(
            _display_normalize(initial_source["tic"], np), 0
        ),
        cmap="magma",
        alpha=0.65,
        aspect=physical_aspect,
    )
    status = axis.set_title("")
    axis.set_axis_off()

    def selected_target() -> float | None:
        values = state["mz_values"]
        return values[state["mz_index"]] if values else None

    def redraw():
        source = ion_sources[state["source_index"]]
        image, actual_mz = source_image(source, selected_target())
        normalized = _display_normalize(image, np)
        ion_artist.set_data(np.ma.masked_less_equal(normalized, 0))
        ion_artist.set_transform(
            Affine2D().translate(*state["drag"]) + axis.transData
        )
        description = "TIC" if actual_mz is None else f"m/z {actual_mz:.5f}"
        status.set_text(
            f"{source['display_name']} — {description}\n"
            "Drag the colored ion image; enter comma-separated m/z values "
            "and use Previous/Next"
        )
        figure.canvas.draw_idle()

    mz_axis = figure.add_axes((0.08, 0.12, 0.38, 0.055))
    mz_box = TextBox(mz_axis, "m/z values ", initial="")

    def set_mz_values(text: str):
        matches = re.findall(r"\d+(?:\.\d+)?", text)
        state["mz_values"] = [float(value) for value in matches]
        state["mz_index"] = 0
        redraw()

    def cycle_mz(step: int):
        def callback(_event):
            if state["mz_values"]:
                state["mz_index"] = (
                    state["mz_index"] + step
                ) % len(state["mz_values"])
                redraw()

        return callback

    def next_dataset(_event):
        state["source_index"] = (
            state["source_index"] + 1
        ) % len(ion_sources)
        redraw()

    def accept(_event):
        state["translation"] = _manual_translation_from_ion_drag(
            result.translation_pixels, tuple(state["drag"])
        )
        state["accepted"] = True
        plt.close(figure)

    def cancel(_event):
        plt.close(figure)

    def on_press(event):
        if event.inaxes is axis and event.button == 1:
            state["press"] = (
                event.xdata,
                event.ydata,
                state["drag"][0],
                state["drag"][1],
            )

    def on_motion(event):
        if state["press"] is None or event.inaxes is not axis:
            return
        start_x, start_y, drag_x, drag_y = state["press"]
        state["drag"] = [
            drag_x + event.xdata - start_x,
            drag_y + event.ydata - start_y,
        ]
        redraw()

    def on_release(_event):
        state["press"] = None

    previous_axis = figure.add_axes((0.49, 0.12, 0.09, 0.055))
    next_axis = figure.add_axes((0.59, 0.12, 0.09, 0.055))
    dataset_axis = figure.add_axes((0.69, 0.12, 0.13, 0.055))
    save_axis = figure.add_axes((0.50, 0.035, 0.20, 0.06))
    cancel_axis = figure.add_axes((0.72, 0.035, 0.14, 0.06))
    previous_button = Button(previous_axis, "Previous")
    next_button = Button(next_axis, "Next")
    dataset_button = Button(dataset_axis, "Next dataset")
    save_button = Button(save_axis, "Save manual shift", color="#b6e3b6")
    cancel_button = Button(cancel_axis, "Cancel", color="#efb1b1")
    mz_box.on_text_change(set_mz_values)
    previous_button.on_clicked(cycle_mz(-1))
    next_button.on_clicked(cycle_mz(1))
    dataset_button.on_clicked(next_dataset)
    save_button.on_clicked(accept)
    cancel_button.on_clicked(cancel)
    figure.canvas.mpl_connect("button_press_event", on_press)
    figure.canvas.mpl_connect("motion_notify_event", on_motion)
    figure.canvas.mpl_connect("button_release_event", on_release)
    figure._imzml_writer_widgets = (
        mz_box,
        previous_button,
        next_button,
        dataset_button,
        save_button,
        cancel_button,
    )
    redraw()
    try:
        plt.show(block=True)
    finally:
        plt.close(figure)
    return state["translation"] if state["accepted"] else None


def coregister_optical_image(
    zarr_path: str | Path,
    optical_image_name: str,
    ion_image_name: str | None = None,
    *,
    save: bool | None = None,
    segmentation: str = "spectral",
    minimum_tissue_votes: int | None = None,
    optical_roi: tuple[float, float, float, float] | None = None,
    select_roi: bool | None = None,
    msi_pixel_size_um: float | tuple[float, float] | None = None,
    optical_pixel_size_um: float | tuple[float, float] | None = None,
    refinement_radius_pixels: tuple[int, int] | None = None,
    preview_dispatch: Any | None = None,
) -> FourierRegistrationResult:
    """Snap an optical image to TIC/ion imagery using tissue masks.

    By default, two-class k-means is fitted to every pixel's complete mass
    spectrum in each selected Thyra table. Cluster labels are mapped back to
    x/y pixels and the spatially coherent class is treated as tissue. A
    non-wrapping mask overlap provides a coarse placement. A bounded local search
    then maximizes normalized mutual information (NMI) plus absolute normalized
    cross-correlation (NCC) between the optical intensity and continuous
    full-spectrum cluster confidence. The transform remains translation-only.

    This estimates translation only. It assumes the optical and MSI images show
    the same field of view without rotation or nonuniform distortion.

    Args:
        zarr_path: Existing SpatialData/Zarr store.
        optical_image_name: Name of the optical image element to align.
        ion_image_name: Specific ion image, or ``None`` to combine all TICs.
        save: ``None`` shows a preview and asks whether to save. ``True`` saves
            without prompting; ``False`` performs a non-mutating dry run.
        segmentation: ``"spectral"`` (default) clusters the complete MSI table.
            ``"tic"`` clusters only log-scaled TIC intensity.
        minimum_tissue_votes: Optional fixed number of selected scan filters
            that must classify a pixel as tissue. The default ``None`` uses
            confidence-weighted masks so coherent filters dominate noisy ones.
        optical_roi: Optional optical ``(x0, y0, x1, y1)`` crop corresponding
            to the MSI field of view.
        select_roi: Opt into the interactive optical ROI selector. The default
            uses the complete optical image.
        msi_pixel_size_um: MSI ``(x, y)`` spacing in micrometers. By default,
            use Thyra's independently detected x/y imzML spacing.
        optical_pixel_size_um: Optical ``(x, y)`` spacing in micrometers, or a
            scalar for square pixels. Required unless it was recorded by
            :func:`add_optical_image`.
        refinement_radius_pixels: Optional x/y search radius around the coarse
            tissue-mask translation. Only translation is optimized.
        preview_dispatch: Optional callable used by GUI integrations to execute
            the interactive preview on their UI thread. It receives a zero-arg
            callable and returns the user's save decision.
    """
    store = Path(zarr_path).resolve()
    if not store.is_dir():
        raise ValueError(f"Not an existing Zarr store: {store}")

    (
        cv2,
        np,
        zarr,
        read_zarr,
        Scale,
        Sequence,
        Translation,
        get_transformation,
        set_transformation,
        MiniBatchKMeans,
        normalize,
    ) = _load_registration_dependencies()
    with _suppress_known_zarr_warnings():
        spatial_data = read_zarr(store)
    if optical_image_name not in spatial_data.images:
        raise ValueError(f"Optical image not found: {optical_image_name}")

    if ion_image_name is not None:
        if ion_image_name not in spatial_data.images:
            raise ValueError(f"Ion image not found: {ion_image_name}")
        ion_names = [ion_image_name]
    else:
        ion_names = sorted(
            name for name in spatial_data.images if name.endswith("_tic")
        )
        if not ion_names:
            raise ValueError("The Zarr store contains no *_tic ion images")

    if minimum_tissue_votes is not None and (
        not isinstance(minimum_tissue_votes, int)
        or not 1 <= minimum_tissue_votes <= len(ion_names)
    ):
        raise ValueError(
            "minimum_tissue_votes must be between 1 and the number of selected "
            f"scan filters ({len(ion_names)})"
        )

    if segmentation not in {"spectral", "tic"}:
        raise ValueError("segmentation must be 'spectral' or 'tic'")

    if msi_pixel_size_um is None:
        detected_size = _detected_msi_pixel_size(spatial_data)
        if detected_size is None:
            raise ValueError(
                "MSI pixel spacing was not found in the Zarr metadata; pass "
                "msi_pixel_size_um=(x_um, y_um)"
            )
        msi_pixel_size = detected_size
    else:
        msi_pixel_size = _pixel_size_pair(
            msi_pixel_size_um, "msi_pixel_size_um"
        )

    if optical_pixel_size_um is None:
        optical_info = spatial_data.attrs.get(
            "imzml_writer_optical_images", {}
        ).get(optical_image_name, {})
        stored_optical_size = optical_info.get("pixel_size_um")
        original_path = optical_info.get("original_path")
        if stored_optical_size is None and original_path:
            try:
                import tifffile

                with tifffile.TiffFile(original_path) as tiff:
                    stored_optical_size = _tiff_pixel_size_um(tiff)
            except (ImportError, OSError, ValueError):
                pass
        if stored_optical_size is None:
            raise ValueError(
                "Optical pixel spacing was not found in the TIFF metadata or "
                "recorded in this Zarr; pass optical_pixel_size_um"
            )
        optical_pixel_size = _pixel_size_pair(
            stored_optical_size, "stored optical pixel size"
        )
    else:
        optical_pixel_size = _pixel_size_pair(
            optical_pixel_size_um, "optical_pixel_size_um"
        )

    reference_element = spatial_data.images[ion_names[0]]
    reference = _grayscale_image(reference_element, np)
    reference_shape = reference.shape
    combined_ion_mask = np.zeros(reference_shape, dtype=np.float32)
    combined_ion_confidence = np.zeros(reference_shape, dtype=np.float32)
    filter_weights = []
    for name in ion_names:
        ion = _grayscale_image(spatial_data.images[name], np)
        if segmentation == "spectral":
            table_name = name.removesuffix("_tic")
            if table_name not in spatial_data.tables:
                raise ValueError(
                    f"No MSI table named {table_name!r} for ion image {name!r}. "
                    "Use segmentation='tic' for intensity-only segmentation."
                )
            tissue_mask, filter_weight, tissue_confidence = _spectral_tissue_mask(
                spatial_data.tables[table_name],
                MiniBatchKMeans,
                normalize,
                cv2,
                np,
            )
        else:
            _, tissue_mask = _kmeans_tissue_masks(
                np.log1p(np.maximum(ion, 0)), cv2, np
            )
            tissue_confidence = _display_normalize(
                np.log1p(np.maximum(ion, 0)), np
            )
            filter_weight = 1.0
        if tissue_mask.shape != reference_shape:
            tissue_mask = cv2.resize(
                tissue_mask,
                (reference_shape[1], reference_shape[0]),
                interpolation=cv2.INTER_NEAREST,
            )
        if tissue_confidence.shape != reference_shape:
            tissue_confidence = cv2.resize(
                tissue_confidence,
                (reference_shape[1], reference_shape[0]),
                interpolation=cv2.INTER_LINEAR,
            )
        filter_weights.append(filter_weight)
        combined_ion_confidence += tissue_confidence * filter_weight
        combined_ion_mask += tissue_mask * (
            filter_weight if minimum_tissue_votes is None else 1.0
        )
    if minimum_tissue_votes is None:
        required_weight = sum(filter_weights) * 0.5
        combined_ion_mask = (combined_ion_mask >= required_weight).astype(
            np.float32
        )
    else:
        combined_ion_mask = (
            combined_ion_mask >= minimum_tissue_votes
        ).astype(np.float32)
    total_filter_weight = sum(filter_weights)
    if total_filter_weight > 0:
        combined_ion_confidence /= total_filter_weight
    occupancy = float(combined_ion_mask.mean())
    if occupancy <= 0.005 or occupancy >= 0.995:
        raise ValueError(
            "MSI clustering produced a non-informative mask covering "
            f"{occupancy:.1%} of the raster; try selecting one full-scan "
            "dataset with ion_image_name instead"
        )
    kernel = np.ones((3, 3), dtype=np.uint8)
    combined_ion_mask = cv2.morphologyEx(
        combined_ion_mask, cv2.MORPH_OPEN, kernel
    )
    combined_ion_mask = cv2.morphologyEx(
        combined_ion_mask, cv2.MORPH_CLOSE, kernel
    )

    optical_element = spatial_data.images[optical_image_name]
    optical = _grayscale_image(optical_element, np)
    dark_mask, bright_mask = _kmeans_tissue_masks(optical, cv2, np)
    if select_roi is None:
        select_roi = False
    if select_roi:
        optical_roi = _select_optical_roi(
            optical,
            combined_ion_mask,
            segmentation,
            msi_pixel_size,
            np,
        )
    elif optical_roi is None:
        optical_roi = (0, 0, optical.shape[1], optical.shape[0])
    roi = _validated_roi(optical_roi, optical.shape[1], optical.shape[0])
    roi_x0, roi_y0, roi_x1, roi_y1 = roi
    optical_crop = optical[roi_y0:roi_y1, roi_x0:roi_x1]
    dark_mask = dark_mask[roi_y0:roi_y1, roi_x0:roi_x1]
    bright_mask = bright_mask[roi_y0:roi_y1, roi_x0:roi_x1]
    scale_x = optical_pixel_size[0] / msi_pixel_size[0]
    scale_y = optical_pixel_size[1] / msi_pixel_size[1]
    scaled_width = max(1, round(optical_crop.shape[1] * scale_x))
    scaled_height = max(1, round(optical_crop.shape[0] * scale_y))

    candidates = []
    for cluster_name, optical_mask in (("dark", dark_mask), ("bright", bright_mask)):
        resized = cv2.resize(
            optical_mask,
            (scaled_width, scaled_height),
            interpolation=cv2.INTER_NEAREST,
        )
        phase_input = np.zeros(reference_shape, dtype=np.float32)
        copy_height = min(reference_shape[0], scaled_height)
        copy_width = min(reference_shape[1], scaled_width)
        phase_input[:copy_height, :copy_width] = resized[
            :copy_height, :copy_width
        ]
        _, _, response = _phase_translation(
            combined_ion_mask, phase_input, cv2, np
        )
        dx, dy, dice_overlap, transformed_mask = _mask_overlap_translation(
            combined_ion_mask, resized, cv2, np
        )
        candidates.append(
            (
                dice_overlap,
                response,
                cluster_name,
                dx,
                dy,
                resized,
                transformed_mask,
            )
        )
    (
        dice_overlap,
        response,
        cluster_name,
        dx,
        dy,
        selected_optical_mask,
        transformed_optical_mask,
    ) = max(
        candidates, key=lambda item: (item[0], item[1])
    )
    resized_optical = cv2.resize(
        optical_crop,
        (scaled_width, scaled_height),
        interpolation=cv2.INTER_AREA,
    )
    if refinement_radius_pixels is None:
        refinement_radius = (
            max(reference_shape[1], scaled_width),
            max(reference_shape[0], scaled_height),
        )
    else:
        if (
            len(refinement_radius_pixels) != 2
            or any(
                not isinstance(value, int) or value < 0
                for value in refinement_radius_pixels
            )
        ):
            raise ValueError(
                "refinement_radius_pixels must contain two non-negative integers"
            )
        refinement_radius = refinement_radius_pixels
    (
        dx,
        dy,
        mutual_information,
        normalized_cross_correlation,
        dice_overlap,
        transformed_optical_mask,
    ) = _refine_intensity_translation(
        combined_ion_confidence,
        resized_optical,
        combined_ion_mask,
        selected_optical_mask,
        (dx, dy),
        dice_overlap,
        refinement_radius,
        cv2,
        np,
    )

    result = FourierRegistrationResult(
        optical_image=optical_image_name,
        ion_images=tuple(ion_names),
        translation_pixels=(dx, dy),
        optical_to_ion_scale=(scale_x, scale_y),
        msi_pixel_size_um=msi_pixel_size,
        optical_pixel_size_um=optical_pixel_size,
        correlation=response,
        dice_overlap=dice_overlap,
        mutual_information=mutual_information,
        normalized_cross_correlation=normalized_cross_correlation,
        registration_method="mask_coarse_nmi_ncc_translation",
        optical_tissue_cluster=cluster_name,
        msi_segmentation=segmentation,
        minimum_tissue_votes=minimum_tissue_votes,
        filter_weights=tuple(filter_weights),
        optical_roi=roi,
        tissue_label=f"msi_{segmentation}_tissue_mask",
        saved=False,
    )
    if save is None:
        translation_matrix = np.array([[1, 0, dx], [0, 1, dy]], dtype=np.float32)
        transformed_optical = cv2.warpAffine(
            resized_optical,
            translation_matrix,
            (reference_shape[1], reference_shape[0]),
            borderMode=cv2.BORDER_CONSTANT,
            borderValue=float(np.median(resized_optical)),
        )
        manual_sources = []
        for name in ion_names:
            table_name = name.removesuffix("_tic")
            table = spatial_data.tables.get(table_name)
            if table is None or "mz" not in table.var or table.n_vars < 1:
                continue
            source_tic = _grayscale_image(spatial_data.images[name], np)
            if source_tic.shape != reference_shape:
                source_tic = cv2.resize(
                    source_tic,
                    (reference_shape[1], reference_shape[0]),
                    interpolation=cv2.INTER_LINEAR,
                )
            manual_sources.append(
                {
                    "display_name": str(
                        table.uns.get("coregistration_display_name", table_name)
                    ),
                    "table": table,
                    "mz": np.asarray(table.var["mz"], dtype=float),
                    "x": np.asarray(table.obs["x"], dtype=int),
                    "y": np.asarray(table.obs["y"], dtype=int),
                    "shape": reference_shape,
                    "tic": source_tic,
                }
            )

        def show_manual_alignment() -> tuple[float, float] | None:
            return _manual_registration_preview(
                transformed_optical,
                manual_sources,
                result,
                np,
            )

        def show_preview() -> bool | tuple[float, float]:
            return _confirm_registration_preview(
                combined_ion_mask,
                transformed_optical,
                combined_ion_mask,
                transformed_optical_mask,
                result,
                manual_alignment=show_manual_alignment,
            )

        preview_decision = (
            preview_dispatch(show_preview)
            if preview_dispatch is not None
            else show_preview()
        )
        if isinstance(preview_decision, tuple):
            dx, dy = preview_decision
            manual_metrics = _intensity_registration_metrics(
                combined_ion_confidence,
                resized_optical,
                combined_ion_mask,
                selected_optical_mask,
                round(dx),
                round(dy),
                np,
            )
            if manual_metrics is None:
                mutual_information = 0.0
                normalized_cross_correlation = 0.0
                dice_overlap = 0.0
            else:
                (
                    mutual_information,
                    normalized_cross_correlation,
                    dice_overlap,
                ) = manual_metrics
            transformed_optical_mask = cv2.warpAffine(
                selected_optical_mask,
                np.array([[1, 0, dx], [0, 1, dy]], dtype=np.float32),
                (reference_shape[1], reference_shape[0]),
                flags=cv2.INTER_NEAREST,
                borderMode=cv2.BORDER_CONSTANT,
                borderValue=0,
            )
            result = replace(
                result,
                translation_pixels=(dx, dy),
                dice_overlap=dice_overlap,
                mutual_information=mutual_information,
                normalized_cross_correlation=normalized_cross_correlation,
                registration_method="manual_mz_translation",
            )
            save = True
        else:
            save = bool(preview_decision)
    if not save:
        return result

    optical_to_ion = Sequence(
        [
            Translation([-roi_x0, -roi_y0], axes=("x", "y")),
            Scale([scale_x, scale_y], axes=("x", "y")),
            Translation([dx, dy], axes=("x", "y")),
        ]
    )
    ion_to_global = get_transformation(
        reference_element, to_coordinate_system="global"
    )
    optical_to_global = Sequence([optical_to_ion, ion_to_global])
    set_transformation(
        optical_element,
        optical_to_global,
        to_coordinate_system="global",
        write_to_sdata=spatial_data,
    )

    # viu_chem uses an optical-pixel coordinate system named ``registered``.
    # Store the inverse mapping on MSI elements as well as our optical->global
    # mapping so either SpatialData convention opens with the saved alignment.
    from spatialdata.models import Labels2DModel
    from spatialdata.transformations import Identity
    import xarray as xr

    ion_to_optical = Sequence(
        [
            Translation([-dx, -dy], axes=("x", "y")),
            Scale([1 / scale_x, 1 / scale_y], axes=("x", "y")),
            Translation([roi_x0, roi_y0], axes=("x", "y")),
        ]
    )
    set_transformation(
        optical_element,
        Identity(),
        to_coordinate_system="registered",
        write_to_sdata=spatial_data,
    )
    transformed_elements = [optical_image_name]
    for name in ion_names:
        set_transformation(
            spatial_data.images[name],
            ion_to_optical,
            to_coordinate_system="registered",
            write_to_sdata=spatial_data,
        )
        transformed_elements.append(name)
        shape_name = f"{name.removesuffix('_tic')}_pixels"
        if shape_name in spatial_data.shapes:
            set_transformation(
                spatial_data.shapes[shape_name],
                ion_to_optical,
                to_coordinate_system="registered",
                write_to_sdata=spatial_data,
            )
            transformed_elements.append(shape_name)

    tissue_label_name = f"msi_{segmentation}_tissue_mask"
    label_transformations = dict(
        get_transformation(reference_element, get_all=True)
    )
    label_transformations["registered"] = ion_to_optical
    tissue_labels = Labels2DModel.parse(
        xr.DataArray(
            combined_ion_mask.astype(np.uint8),
            dims=("y", "x"),
            name=tissue_label_name,
        ),
        transformations=label_transformations,
    )
    if tissue_label_name in spatial_data.labels:
        del spatial_data[tissue_label_name]
        spatial_data.delete_element_from_disk(tissue_label_name)
    spatial_data[tissue_label_name] = tissue_labels
    spatial_data.write_element(tissue_label_name)

    updated_tables = []
    for table_name in (name.removesuffix("_tic") for name in ion_names):
        # Only obs/uns change here. Copying and rewriting the complete AnnData
        # element also copies X, which can be a very large sparse spectral
        # matrix and has caused native crashes in threaded GUI saves.
        table = spatial_data.tables[table_name]
        x_coordinates = np.asarray(table.obs["x"], dtype=int)
        y_coordinates = np.asarray(table.obs["y"], dtype=int)
        valid = (
            (x_coordinates >= 0)
            & (x_coordinates < reference_shape[1])
            & (y_coordinates >= 0)
            & (y_coordinates < reference_shape[0])
        )
        tissue = np.zeros(table.n_obs, dtype=bool)
        tissue_confidence = np.zeros(table.n_obs, dtype=np.float32)
        tissue[valid] = combined_ion_mask[
            y_coordinates[valid], x_coordinates[valid]
        ].astype(bool)
        tissue_confidence[valid] = combined_ion_confidence[
            y_coordinates[valid], x_coordinates[valid]
        ]
        table.obs["tissue"] = tissue
        table.obs["tissue_confidence"] = tissue_confidence
        table.uns["imzml_writer_tissue_segmentation"] = {
            "method": f"{segmentation}_kmeans_2",
            "aggregate_label": tissue_label_name,
            "minimum_tissue_votes": minimum_tissue_votes,
        }
        updated_tables.append((table_name, table))

    for element_name in transformed_elements:
        spatial_data.write_transformations(element_name)
    spatial_data.write_metadata(consolidate_metadata=True)

    # AnnData supports independently encoded obs/uns elements. Update those
    # small groups in place so the spectral X matrix is never materialized or
    # rewritten merely to persist tissue membership.
    from anndata.io import write_elem

    with _suppress_known_zarr_warnings():
        root = zarr.open_group(
            str(store), mode="r+", use_consolidated=False
        )
        for table_name, table in updated_tables:
            table_group = root["tables"][table_name]
            write_elem(table_group, "obs", table.obs)
            write_elem(table_group, "uns", table.uns)

    result = FourierRegistrationResult(
        optical_image=optical_image_name,
        ion_images=tuple(ion_names),
        translation_pixels=(dx, dy),
        optical_to_ion_scale=(scale_x, scale_y),
        msi_pixel_size_um=msi_pixel_size,
        optical_pixel_size_um=optical_pixel_size,
        correlation=response,
        dice_overlap=dice_overlap,
        mutual_information=mutual_information,
        normalized_cross_correlation=normalized_cross_correlation,
        registration_method=result.registration_method,
        optical_tissue_cluster=cluster_name,
        msi_segmentation=segmentation,
        minimum_tissue_votes=minimum_tissue_votes,
        filter_weights=tuple(filter_weights),
        optical_roi=roi,
        tissue_label=tissue_label_name,
        saved=True,
    )
    with _suppress_known_zarr_warnings():
        root = zarr.open_group(
            str(store), mode="r+", use_consolidated=False
        )
        label_group = root["labels"][result.tissue_label]
        _remove_orphaned_ome_label_marker(label_group)
        registrations = dict(root.attrs.get("imzml_writer_coregistrations", {}))
        registrations[optical_image_name] = {
            "ion_images": list(result.ion_images),
            "translation_pixels": list(result.translation_pixels),
            "optical_to_ion_scale": list(result.optical_to_ion_scale),
            "msi_pixel_size_um": list(result.msi_pixel_size_um),
            "optical_pixel_size_um": list(result.optical_pixel_size_um),
            "correlation": result.correlation,
            "dice_overlap": result.dice_overlap,
            "mutual_information": result.mutual_information,
            "normalized_cross_correlation": (
                result.normalized_cross_correlation
            ),
            "optical_tissue_cluster": result.optical_tissue_cluster,
            "msi_segmentation": result.msi_segmentation,
            "minimum_tissue_votes": result.minimum_tissue_votes,
            "filter_weights": list(result.filter_weights),
            "optical_roi": list(result.optical_roi),
            "tissue_label": result.tissue_label,
            "method": (
                f"{result.msi_segmentation}_kmeans_2_"
                f"{result.registration_method}"
            ),
        }
        root.attrs["imzml_writer_coregistrations"] = registrations
        zarr.consolidate_metadata(str(store))
    return result


def scan_filter_from_imzml(imzml_file: str | Path) -> str:
    """Read the full scan-filter value embedded in an annotated imzML file."""
    imzml_path = Path(imzml_file)
    try:
        for _, element in ET.iterparse(imzml_path, events=("end",)):
            if (
                element.tag.rsplit("}", 1)[-1] == "cvParam"
                and element.get("accession") == _SCAN_FILTER_ACCESSION
            ):
                scan_filter = element.get("value")
                if scan_filter:
                    return " ".join(scan_filter.split())
            element.clear()
    except ET.ParseError as exc:
        raise ValueError(f"Invalid imzML XML in {imzml_path}") from exc

    raise ValueError(
        f"No scan filter ({_SCAN_FILTER_ACCESSION}) was found in {imzml_path}"
    )


def scan_filter_display_name(scan_filter: str) -> str:
    """Summarize a Thermo scan filter for display in SpatialData viewers."""
    scan_filter = " ".join(scan_filter.split())
    analyzer_polarity = re.compile(
        r"\b(?P<analyzer>(?:FT|IT|TOF|TQ|SQ)MS)\s*"
        r"(?P<polarity>[+\-\N{MINUS SIGN}])(?=\s|$)",
        flags=re.IGNORECASE,
    )
    polarity_match = analyzer_polarity.search(scan_filter)
    if polarity_match is None:
        polarity_match = re.search(
            r"(?<!\S)(?P<polarity>[+\-\N{MINUS SIGN}])(?!\S)", scan_filter
        )
    polarity = ""
    if polarity_match is not None:
        polarity = (
            "Positive" if polarity_match.group("polarity") == "+" else "Negative"
        )

    def with_polarity(scan_type: str) -> str:
        return f"{polarity} {scan_type}" if polarity else scan_type.capitalize()

    def compact_mz(value: str) -> str:
        value = value.strip()
        return value.rstrip("0").rstrip(".") if "." in value else value

    # In Thermo filters, the value immediately after ms2/ms3 is the precursor;
    # activation expressions repeat it as ``m/z@method``.
    product_match = re.search(
        r"\b(?:Full\s+|PRM\s+|SRM\s+|t)?ms(?P<order>[2-9])\s+"
        r"(?P<precursor>\d+(?:\.\d+)?)",
        scan_filter,
        flags=re.IGNORECASE,
    )
    if product_match is not None:
        precursor = compact_mz(product_match.group("precursor"))
        order = int(product_match.group("order"))
        scan_type = "product ion scan" if order == 2 else f"MS{order} product ion scan"
        return f"{with_polarity(scan_type)} (m/z {precursor})"

    range_match = re.search(r"\[\s*([^\]]+?)\s*\]", scan_filter)
    displayed_range = range_match.group(1) if range_match is not None else ""

    if re.search(r"\bSIM\b|\bmsx\b", scan_filter, flags=re.IGNORECASE):
        centers = []
        for lower, upper in re.findall(
            r"(\d+(?:\.\d+)?)\s*-\s*(\d+(?:\.\d+)?)", displayed_range
        ):
            precision = max(
                len(lower.partition(".")[2]), len(upper.partition(".")[2])
            )
            center = (float(lower) + float(upper)) / 2
            centers.append(compact_mz(f"{center:.{precision}f}"))
        displayed_targets = ", ".join(centers) or displayed_range
        label = with_polarity("SIM scan")
        return f"{label} (m/z {displayed_targets})" if displayed_targets else label
    if re.search(r"\bFull\s+ms(?!\d)", scan_filter, flags=re.IGNORECASE):
        return with_polarity("fullscan")

    # Retain the original text for uncommon scan types rather than assigning a
    # misleading category. Polarity is still expanded to prevent collisions.
    fallback = analyzer_polarity.sub(
        lambda match: f"{polarity} {match.group('analyzer').upper()}".strip(),
        scan_filter,
        count=1,
    )
    return fallback


def _dataset_id(scan_filter: str, used_ids: set[str]) -> str:
    """Return a readable, Zarr-safe, unique ID derived from a scan filter."""
    display_name = scan_filter_display_name(scan_filter)
    safe_name = display_name.replace("m/z", "mz").replace("\N{EN DASH}", "-")
    dataset_id = re.sub(r"[^0-9A-Za-z._-]+", "_", safe_name).strip("._-")
    dataset_id = re.sub(r"_+", "_", dataset_id) or "scan_filter"

    # Dataset IDs become several nested Zarr paths. Keep them compact enough for
    # Windows while retaining a stable link to a long or colliding filter name.
    digest = hashlib.sha1(scan_filter.encode("utf-8")).hexdigest()[:8]
    if len(dataset_id) > 80:
        dataset_id = f"{dataset_id[:71].rstrip('._-')}_{digest}"
    if dataset_id in used_ids:
        base_id = dataset_id[:76].rstrip("._-")
        suffix = 2
        while f"{base_id}_{suffix}" in used_ids:
            suffix += 1
        dataset_id = f"{base_id}_{suffix}"

    used_ids.add(dataset_id)
    return dataset_id


def _resolve_imzml_files(
    imzml_files: str | Path | Iterable[str | Path],
) -> list[Path]:
    if isinstance(imzml_files, (str, Path)):
        source = Path(imzml_files)
        if source.is_dir():
            files = [path for path in source.iterdir() if path.suffix.lower() == ".imzml"]
        else:
            files = [source]
    else:
        files = [Path(path) for path in imzml_files]

    files = sorted((path.resolve() for path in files), key=lambda path: path.name.lower())
    if not files:
        raise ValueError("No imzML files were provided")
    for path in files:
        if not path.is_file() or path.suffix.lower() != ".imzml":
            raise ValueError(f"Not an imzML file: {path}")
    return files


def write_combined_zarr(
    imzml_files: str | Path | Iterable[str | Path],
    output_path: str | Path,
    *,
    thyra_options: Mapping[str, Any] | None = None,
) -> Path:
    """Convert several imzML files into one SpatialData/Zarr store.

    Each input is converted by Thyra with a dataset ID derived from its full
    ``MS:1000512`` scan filter. The exact (unsanitized) filter and source file
    are also recorded in ``sdata.attrs["imzml_writer_scan_filters"]``.

    Args:
        imzml_files: An imzML directory, one imzML path, or an iterable of paths.
        output_path: Destination ``.zarr`` directory. It must not already exist.
        thyra_options: Extra keyword arguments forwarded to ``thyra.convert_msi``.

    Returns:
        The resolved path to the combined Zarr store.
    """
    inputs = _resolve_imzml_files(imzml_files)
    destination = Path(output_path).resolve()
    if destination.exists():
        raise FileExistsError(f"Zarr output already exists: {destination}")
    destination.parent.mkdir(parents=True, exist_ok=True)

    options = dict(thyra_options or {})
    reserved = {"input_path", "output_path", "dataset_id", "format_type"}
    conflicting = reserved.intersection(options)
    if conflicting:
        names = ", ".join(sorted(conflicting))
        raise ValueError(f"thyra_options cannot override: {names}")
    # Thyra's CLI enables automatic mass-axis resampling, but its Python API
    # only does so when a non-None config is supplied. Without this, centroid
    # imzML can produce a raw union axis with nearly one column per peak across
    # the file, making even spatially tiny datasets slow to open and browse.
    options.setdefault("resampling_config", {})

    convert_msi, read_zarr, SpatialData = _load_zarr_dependencies()
    collections: dict[str, dict[str, Any]] = {
        name: {} for name in _SPATIALDATA_COLLECTIONS
    }
    filters: dict[str, dict[str, str]] = {}
    used_ids: set[str] = set()
    display_name_counts: dict[str, int] = {}
    root_attrs: dict[str, Any] = {}

    with tempfile.TemporaryDirectory(
        prefix=".imzml-writer-zarr-", dir=destination.parent
    ) as temporary_directory:
        temporary_root = Path(temporary_directory)
        for index, imzml_path in enumerate(inputs):
            scan_filter = scan_filter_from_imzml(imzml_path)
            display_name_base = scan_filter_display_name(scan_filter)
            display_name_counts[display_name_base] = (
                display_name_counts.get(display_name_base, 0) + 1
            )
            display_name = display_name_base
            if display_name_counts[display_name_base] > 1:
                display_name = (
                    f"{display_name_base} {display_name_counts[display_name_base]}"
                )
            dataset_id = _dataset_id(scan_filter, used_ids)
            temporary_store = temporary_root / f"source-{index}.zarr"

            with warnings.catch_warnings():
                # Older imzML Writer outputs used non-canonical CV display
                # names. pyimzML corrects them automatically; suppress only
                # that known warning while retaining every other warning.
                warnings.filterwarnings(
                    "ignore",
                    message=r"Accession MS:100(?:0799|0031) found with incorrect name.*",
                    category=UserWarning,
                    module=r"pyimzml\.ontology\.ontology",
                )
                success = convert_msi(
                    input_path=imzml_path,
                    output_path=temporary_store,
                    format_type="spatialdata",
                    dataset_id=dataset_id,
                    **options,
                )
            if not success:
                raise RuntimeError(f"Thyra failed to convert {imzml_path}")

            with _suppress_known_zarr_warnings():
                source_data = read_zarr(temporary_store)
            for table_key, table in source_data.tables.items():
                # VIUChem reads these keys directly when constructing its
                # dataset selector; root attributes alone are not consulted.
                if not hasattr(table, "uns"):
                    continue
                table.uns["coregistration_dataset_label"] = dataset_id
                table.uns["coregistration_display_name"] = display_name
                tic_key = f"{table_key}_tic"
                if tic_key in source_data.images:
                    table.uns["coregistration_tic_key"] = tic_key
                shape_key = f"{table_key}_pixels"
                if shape_key in source_data.shapes:
                    table.uns["coregistration_pixel_shape_keys"] = [shape_key]
            if not root_attrs:
                root_attrs.update(dict(source_data.attrs))
            for collection_name in _SPATIALDATA_COLLECTIONS:
                target_collection = collections[collection_name]
                source_collection = getattr(source_data, collection_name, {})
                duplicates = target_collection.keys() & source_collection.keys()
                if duplicates:
                    names = ", ".join(sorted(duplicates))
                    raise ValueError(f"Duplicate SpatialData element names: {names}")
                target_collection.update(source_collection)

            filters[dataset_id] = {
                "display_name": display_name,
                "scan_filter": scan_filter,
                "source_file": imzml_path.name,
            }

        # A single Thyra store's msi_dataset_info describes only one input. The
        # table-level ``uns`` still retains Thyra's complete per-dataset metadata.
        root_attrs.pop("msi_dataset_info", None)
        root_attrs["imzml_writer_scan_filters"] = filters

        combined = SpatialData(**collections)
        combined.attrs.update(root_attrs)
        staged_output = temporary_root / "combined.zarr"
        combined.write(str(staged_output))
        staged_output.replace(destination)

    return destination
