# simcitybuildit
Documenting Simcity Buildit internals


The game is build upon the marmalade game engine.

in .apk files the main binary is in Simcity.s3e, this is a lzma compressed file, you can use 7zip to decompress it.
in .ipa file the s3e binary is embedded in the main executable, and scrambled somewhat. I'll post a decoder later.

The game data is in .group.bin files. These are lz4 compressed, ( `brew install lz4` for the decompressor ).
I'll post a decoder for these later.

