# simcitybuildit
Documenting Simcity Buildit internals


The game is build upon the marmalade game engine.

in .apk files the main binary is in Simcity.s3e, this is a lzma compressed file, you can use 7zip to decompress it.
in .ipa file the s3e binary is embedded in the main executable, and scrambled somewhat. I'll post a decoder later.

The game data is in .group.bin files. These are lz4 compressed, ( `brew install lz4` for the decompressor ).
I'll post a decoder for these later.

One intereting example i post here: [badwords.txt](badwords.txt).
reading through the list you find the usual profanity, but apparently also the 1989 Tiananmen Square massacre, or Tibettan independence are listed as 'badwords'. ( referred to as 'may 35th' - `5月35日`  or `5月35号` ).

See [badwords.md](badwords.md) for a google-translated version.


group.bin format
================

The compressed files start with the magic bytes: `04 22 4d 18`.
The decompressed files start with the magic bytes: `3d 03 07 01 00 00 87 e0 81 80`.

In older .ipa's the fourth byte is zero instead of one.

| type      | content
| --------- | ------
|  10 bytes    | header magic
|  uint32    | filename length
|  bytes    | filename, followed by 9 bytes: `00 00 00 00 00 77 21 3c dc`
|  uint32   | total content size
|  uint32   | filetype related
|  uint32   | filetype magic
|  uint32   | number of sections
|  2 bytes  | in all but one file: `01 01`
|  ...      | section data

Then followed by section data.

Each section starts with 2 

| type      | content
| --------- | ------
| uint32    | size, including this header
| uint32    | some checksum??
|  ...      | section content

file types
=============

file type 00000001.f67cbd74
=================

| type      | content
| --------- | ------
|  uint32   | string count
|  bytes    | string table, each string has a uint16 length, followed by utf-8 encoded text.
|  uint32   | number of tables
|   ...     | table data
| 128 bytes | probably rsa signature

table layout:

| type      | content
| --------- | ------
|  string   | tablename
|  uint32   | number of fields per record
|  n strings  | field names
|  n bytes    | for each field the data type
|  uint32   | record count
|  ...      | record data

field types:

| type  | encoding |  meaning
| ----- | -------- | ----------
|   0   | uint16 | string, index into the string table at the start of this section.
|   1   | uint32 | number
|   2   | float32 | floating point number
|   3   | uint32  | color value

