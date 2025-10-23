def upstream_scan() -> None:
    """Run an upstream scan.

    - Uses only upstream crystal
    - Beam stop (diode) in the upstream position
    - Sweep fine yaw with correlated motion of the diode

    """

    ...


def downstream_scan() -> None:
    """Run a downstream scan.

    - Uses both crystals
    - Beam stop (diode) in the downstream position
    - Sweep fine yaw with correlated motion of the diode

    """
    ...


def saxs_waxs_frame() -> None:
    """Take a SAXS/WAXS frame.

    - Uses only upstream crystal
    - Beam stop (diode) in downstream position
    - No sweep

    """
    ...


def interleaved_scan() -> None:
    """Run downsteam scan interleved with SAXS WAXS frames."""
    ...
