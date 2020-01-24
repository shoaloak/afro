<img src="../logo/afro.png" alt="afro logo" align="left">

# afro (APFS file recovery) [![Build Status](https://travis-ci.org/cugu/afro.svg?branch=master)](https://travis-ci.org/cugu/afro)

AFRO can parse APFS volumes. It can also recover deleted files from APFS that other tools do not find. AFRO can also detect hidden data within/besides APFS datastructures.

## Test images

`/test_dumps` contains 6 images with incremental changes to showcase the difference it has on APFS datastructures. These images were created with APFS driver version `1412.61.1`.

`wsdf.dmg` is an image with a number of nested files and directories. This image was created with an older APFS driver version.

## Licenses

The afro software is licensed as [GPLv3](licences/gpl-3.0.txt).
The ksy file (libapfs/apfs.ksy) is licensed under [MIT license](licences/mit.txt).
