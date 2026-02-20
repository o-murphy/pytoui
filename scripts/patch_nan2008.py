#!/usr/bin/env python3
"""Patch MIPS ELF to set NaN2008 flag for device compatibility."""

import struct
import sys


def patch_nan2008(path):
    with open(path, "r+b") as f:
        # Verify ELF magic
        magic = f.read(4)
        if magic != b"\x7fELF":
            print(f"ERROR: {path} is not an ELF file")
            sys.exit(1)

        # Read EI_CLASS (offset 4): 1=32-bit, 2=64-bit
        ei_class = struct.unpack("B", f.read(1))[0]
        if ei_class != 1:
            print(f"ERROR: expected 32-bit ELF, got class {ei_class}")
            sys.exit(1)

        # e_flags is at offset 0x24 in ELF32
        f.seek(0x24)
        e_flags = struct.unpack("<I", f.read(4))[0]
        print(f"  e_flags before: 0x{e_flags:08x}")

        # Set EF_MIPS_NAN2008 (0x400)
        e_flags |= 0x400
        f.seek(0x24)
        f.write(struct.pack("<I", e_flags))
        print(f"  e_flags after:  0x{e_flags:08x}")

        # Find and patch .MIPS.abiflags section
        # Read e_shoff (section header table offset) at 0x20
        f.seek(0x20)
        e_shoff = struct.unpack("<I", f.read(4))[0]

        # e_shentsize at 0x2E, e_shnum at 0x30, e_shstrndx at 0x32
        f.seek(0x2E)
        e_shentsize = struct.unpack("<H", f.read(2))[0]
        e_shnum = struct.unpack("<H", f.read(2))[0]
        e_shstrndx = struct.unpack("<H", f.read(2))[0]

        # Read section header string table
        shstr_offset_pos = e_shoff + e_shstrndx * e_shentsize + 0x10
        f.seek(shstr_offset_pos)
        shstr_offset = struct.unpack("<I", f.read(4))[0]
        f.seek(shstr_offset_pos + 4)
        shstr_size = struct.unpack("<I", f.read(4))[0]
        f.seek(shstr_offset)
        shstrtab = f.read(shstr_size)

        # Find .MIPS.abiflags section
        for i in range(e_shnum):
            sh_off = e_shoff + i * e_shentsize
            f.seek(sh_off)
            sh_name_idx = struct.unpack("<I", f.read(4))[0]

            # Get section name
            name_end = shstrtab.index(b"\x00", sh_name_idx)
            name = shstrtab[sh_name_idx:name_end].decode("ascii", errors="replace")

            if name == ".MIPS.abiflags":
                f.seek(sh_off + 0x10)  # sh_offset
                sec_offset = struct.unpack("<I", f.read(4))[0]

                # MIPS ABIFlags structure:
                # uint16 version, uint8 isa_level, uint8 isa_rev,
                # uint8 gpr_size, uint8 cpr1_size, uint8 cpr2_size, uint8 fp_abi,
                # uint32 isa_ext, uint32 ases, uint32 flags1, uint32 flags2
                f.seek(sec_offset)
                data = f.read(24)
                (
                    version,
                    isa_level,
                    isa_rev,
                    gpr_size,
                    cpr1_size,
                    cpr2_size,
                    fp_abi,
                    isa_ext,
                    ases,
                    flags1,
                    flags2,
                ) = struct.unpack("<HBBBBBBIIII", data)

                print(
                    f"  abiflags before: fp_abi={fp_abi} cpr1_size={cpr1_size} flags1=0x{flags1:x}"
                )

                # Patch: cpr1_size=2 (64-bit FPR), fp_abi=7 (FP64), flags1=1 (ODDSPREG)
                cpr1_size = 2  # 64-bit FPU registers
                fp_abi = 7  # Hard float (32-bit CPU, 64-bit FPU)
                flags1 = 1  # ODDSPREG

                f.seek(sec_offset)
                f.write(
                    struct.pack(
                        "<HBBBBBBIIII",
                        version,
                        isa_level,
                        isa_rev,
                        gpr_size,
                        cpr1_size,
                        cpr2_size,
                        fp_abi,
                        isa_ext,
                        ases,
                        flags1,
                        flags2,
                    )
                )

                print(
                    f"  abiflags after:  fp_abi={fp_abi} cpr1_size={cpr1_size} flags1=0x{flags1:x}"
                )
                break
        else:
            print("  WARNING: .MIPS.abiflags section not found")

    print(f"  Patched: {path}")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(f"Usage: {sys.argv[0]} <elf-file>")
        sys.exit(1)
    patch_nan2008(sys.argv[1])
