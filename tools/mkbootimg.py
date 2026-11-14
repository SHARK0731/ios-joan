#!/usr/bin/env python3
"""Standalone Android Boot Image (v0-v2) creator with zero dependencies."""
import argparse
import hashlib
import os
import struct
import sys

def parse_os_version(os_version, os_patch_level):
    ver = 0
    if os_version:
        parts = [int(p) for p in os_version.split('.') if p.isdigit()]
        a = parts[0] if len(parts) > 0 else 0
        b = parts[1] if len(parts) > 1 else 0
        c = parts[2] if len(parts) > 2 else 0
        ver |= ((a & 0x7f) << 25) | ((b & 0x7f) << 18) | ((c & 0x7f) << 11)
    if os_patch_level:
        parts = [int(p) for p in os_patch_level.split('-') if p.isdigit()]
        y = parts[0] if len(parts) > 0 else 2000
        m = parts[1] if len(parts) > 1 else 1
        ver |= (((y - 2000) & 0x7f) << 4) | (m & 0xf)
    return ver

def pad(data, page_size):
    remainder = len(data) % page_size
    if remainder:
        data += b'\0' * (page_size - remainder)
    return data

def main():
    parser = argparse.ArgumentParser(description="Create Android boot image")
    parser.add_argument('--kernel', required=True)
    parser.add_argument('--ramdisk', required=True)
    parser.add_argument('--second')
    parser.add_argument('--dtb')
    parser.add_argument('--recovery_dtbo')
    parser.add_argument('--cmdline', default='')
    parser.add_argument('--base', type=lambda x: int(x, 0), default=0)
    parser.add_argument('--kernel_offset', type=lambda x: int(x, 0), default=0x8000)
    parser.add_argument('--ramdisk_offset', type=lambda x: int(x, 0), default=0x02000000)
    parser.add_argument('--second_offset', type=lambda x: int(x, 0), default=0x00f00000)
    parser.add_argument('--tags_offset', type=lambda x: int(x, 0), default=0x01e00000)
    parser.add_argument('--dtb_offset', type=lambda x: int(x, 0), default=0x01f00000)
    parser.add_argument('--pagesize', type=int, default=4096)
    parser.add_argument('--header_version', type=int, default=0)
    parser.add_argument('--os_version', default='')
    parser.add_argument('--os_patch_level', default='')
    parser.add_argument('-o', '--output', required=True)
    args, _ = parser.parse_known_args()

    kernel_data = open(args.kernel, 'rb').read()
    ramdisk_data = open(args.ramdisk, 'rb').read() if args.ramdisk else b''
    second_data = open(args.second, 'rb').read() if args.second else b''
    dtb_data = open(args.dtb, 'rb').read() if args.dtb else b''
    recovery_dtbo_data = open(args.recovery_dtbo, 'rb').read() if args.recovery_dtbo else b''

    ks, ka = len(kernel_data), args.base + args.kernel_offset
    rs, ra = len(ramdisk_data), args.base + args.ramdisk_offset
    ss, sa = len(second_data), args.base + args.second_offset
    ta = args.base + args.tags_offset
    ps = args.pagesize
    ver = args.header_version
    if dtb_data and ver < 2:
        ver = 2

    osv = parse_os_version(args.os_version, args.os_patch_level)

    # Magic: ANDROID! (8 bytes)
    hdr = bytearray(ps)
    struct.pack_into('<8s10I16s512s32s1024s', hdr, 0,
                     b'ANDROID!',
                     ks, ka, rs, ra, ss, sa, ta, ps, ver, osv,
                     b'', # name (16)
                     args.cmdline.encode()[:512],
                     b'\0' * 32, # id
                     b'' # extra_cmdline (1024)
                    )

    if ver >= 1:
        rds = len(recovery_dtbo_data)
        # offset will be computed after kernel+ramdisk+second
        hdr_size = 1660 if ver >= 2 else 1648
        struct.pack_into('<IQI', hdr, 1632, rds, 0, hdr_size)

    if ver >= 2:
        ds, da = len(dtb_data), args.base + args.dtb_offset
        struct.pack_into('<IQ', hdr, 1648, ds, da)

    # Compute SHA1 for id
    sha = hashlib.sha1()
    sha.update(kernel_data)
    sha.update(struct.pack('<I', ks))
    sha.update(ramdisk_data)
    sha.update(struct.pack('<I', rs))
    sha.update(second_data)
    sha.update(struct.pack('<I', ss))
    if dtb_data and ver >= 2:
        sha.update(dtb_data)
        sha.update(struct.pack('<I', len(dtb_data)))
    digest = sha.digest()
    hdr[576:576+len(digest)] = digest

    with open(args.output, 'wb') as f:
        f.write(hdr)
        f.write(pad(kernel_data, ps))
        if rs:
            f.write(pad(ramdisk_data, ps))
        if ss:
            f.write(pad(second_data, ps))
        if ver >= 1 and recovery_dtbo_data:
            f.write(pad(recovery_dtbo_data, ps))
        if ver >= 2 and dtb_data:
            f.write(pad(dtb_data, ps))

    print(f"Created boot image {args.output} (header v{ver}, size {os.path.getsize(args.output)} bytes)")

if __name__ == '__main__':
    main()
