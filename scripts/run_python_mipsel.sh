#!/bin/sh
# Mount and run Python from ext2 image on MIPS device.
#
# Usage:
#   ./run_python_mipsel.sh              # mount + interactive shell
#   ./run_python_mipsel.sh script.py    # mount + run script
#   ./run_python_mipsel.sh -u           # unmount
#
# Place this script and python-*.img on the device's SD/MMC partition.

IMG_DIR="/usr/mmcdata/mmcblk0p8"
MNT="/tmp/python"
PYTHON="${MNT}/install/bin/python3"

case "${1:-}" in
    -u|--unmount)
        echo "Unmounting ${MNT}..."
        umount "${MNT}" 2>/dev/null && rmdir "${MNT}" 2>/dev/null
        echo "Done."
        exit 0
        ;;
esac

# Find the image
IMG=$(ls "${IMG_DIR}"/python-*-mipsel.img 2>/dev/null | head -1)
if [ -z "${IMG}" ]; then
    echo "ERROR: No python-*-mipsel.img found in ${IMG_DIR}/"
    exit 1
fi

# Mount if not already mounted
if ! mountpoint -q "${MNT}" 2>/dev/null; then
    mkdir -p "${MNT}"
    mount -o loop "${IMG}" "${MNT}"
    echo "Mounted ${IMG} -> ${MNT}"
fi

# Add to PATH
export PATH="${MNT}/install/bin:${PATH}"
export LD_LIBRARY_PATH="${MNT}/install/lib:${LD_LIBRARY_PATH:-}"

if [ $# -gt 0 ]; then
    # Run script or arguments
    exec "${PYTHON}" "$@"
else
    # Interactive
    echo "Python ready: ${PYTHON}"
    exec "${PYTHON}"
fi
