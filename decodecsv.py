"""
Script for decoding simcity buildit game files.
First you have to decompress them using 'lz4'

    lz4 -d < csv.group.bin > csv.group.bin.unlz4
    
then dump the contents using:

    python decodecsv.py csv.group.bin.unlz4
    
I did not yet decode all block types, only the most interesting ones.

"""

from __future__ import division, print_function, absolute_import, unicode_literals
import struct
from binascii import *
import sys

verbose = False

def getuint32(data, o, last):
    if o+4<=last:
        return struct.unpack_from("<L", data, o)[0], 4
    return 0, 0
def getfloat32(data, o, last):
    if o+4<=last:
        return struct.unpack_from("<f", data, o)[0], 4
    return 0.0, 0
def getuint16(data, o, last):
    if o+2<=last:
        return struct.unpack_from("<H", data, o)[0], 2
    return 0, 0
def getuint8(data, o, last):
    if o+1<=last:
        return struct.unpack_from("<B", data, o)[0], 1
    return 0, 0

def getstr16(data, first, last):
    o = first
    tlen, n = getuint16(data, o, last) ; o += n
    if o+tlen<=last:
        txt = data[o:o+tlen].decode('utf-8', 'ignore') ; o += tlen
        return txt, o-first
    return None, 0

def hexdump(data, first, last):
    print("hex:", b2a_hex(data[first:last]))

def calcrecsize(types):
    size = 0
    for t in types:
        if type(t)==str:  # python2 compatibility
            t = ord(t)
        if t==0: size += 2    # uint16
        elif t==1: size += 4  # uint32
        elif t==2: size += 4  # float32
        elif t==3: size += 4  # color value
        else:
            print("WARNING: unknown type: %d" % t)
    return size

class RecordBase(object): 
    # baseclass for a database record.
    def __init__(self, data, o, last, types, fields, strs):
        for typ, nam in zip(types, fields):
            if type(typ)==str:  # python2 compatibility
                typ = ord(typ)
            if typ==0:
                value, n = getuint16(data, o, last) ; o += n
                if 0 <= value < len(strs):
                    value = strs[value]
                else:
                    print("WARNING: unknown str index ( %d of %d )" % (value, len(nstrs)))
            elif typ==1:
                value, n = getuint32(data, o, last) ; o += n
            elif typ==2:
                value, n = getfloat32(data, o, last) ; o += n
            elif typ==3:   # color value
                value, n = getuint32(data, o, last) ; o += n
            else:
                print("WARNING: unknown type: %d - %s" % (typ, b2a_hex(data[o:o+8])))
            setattr(self, nam, value)
        if o!=last:
            print("WARNING: reclen mismatch: %d .. %d" % (o, last))
    def __repr__(self):
        l = []
        for name in dir(self):
            if not name.startswith("_"):
                l.append("%s:%s" % (name, repr(getattr(self, name))))
        return "["+(", ".join(l))+"]"


def create_class(name):
    # create a class for database records
    class New(RecordBase):pass
    New.__name__ = str(name)
    return New

def dumpblock_f67cbd74(data, first, last):
    # decode a database table with records.
    o = first
    nstr, n = getuint32(data, o, last) ; o += n
    strs = []
    for _ in range(nstr):
        if o>=last: break

        s, n = getstr16(data, o, last) ; o += n
        strs.append(s)
    ntables, n = getuint32(data, o, last) ; o += n

    for _ in range(ntables):
        if o>=last: break

        tfirst = o

        tname, n = getstr16(data, o, last) ; o += n

        recordcls = create_class(tname)

        nfld, n = getuint32(data, o, last) ; o += n

        fields = []
        for _ in range(nfld):
            if o>=last: break
            s, n = getstr16(data, o, last) ; o += n
            fields.append(s)
        types = data[o:o+nfld] ; o += nfld
        nrec, n = getuint32(data, o, last) ; o += n

        recsize = calcrecsize(types)

        if recsize==0:
            print("invalid record size")
            break
        recs = []
        for _ in range(nrec):
            if o>=last: break
            recs.append(recordcls(data, o, o+recsize, types, fields, strs)) ; o += recsize

        print("%06x: TABLE: %d recs, %d fields '%s'" % (tfirst, nrec, nfld, tname))
        print(recs)

    signature = data[o:o+128] ; o += 128

    if o!=last:
        print("WARNING: %d bytes left after block: %d" % (last - o))

    return o-first

def dumpblock_9b0704c1(data, first, last):
    # font
    path = data[first:last].decode('utf-8', 'ignore').rstrip("\x00")
    print("%06x: '%s'" % (first, path))

def getvariableinit(data, first, last):
    o = first
    dim1, n = getuint32(data, o, last) ; o += n
    dim2, n = getuint32(data, o, last) ; o += n
    flag, n = getuint32(data, o, last) ; o += n

    if flag==9:
        return [], o-first
    if dim2==1:
        if dim1<8:
            datawords = struct.unpack_from("<%df"%(dim1-3), data, o) ; o += 4*(dim1-3)
            return datawords, o-first
        if dim1==14:
            datawords = struct.unpack_from("<%df"%9, data, o) ; o += 4*9
            return datawords, o-first

        if dim1==15:
            datawords = struct.unpack_from("<%df"%16, data, o) ; o += 4*16
            return datawords, o-first
    else:
        n = (dim1+1)*dim2
        datawords = struct.unpack_from("<%df"%n, data, o) ; o += 4*n
        return datawords, min(o-first, last)
    print("WARNING: unknown var format: %08x %08x %08x: %s" % (dim1, dim2, flag, b2a_hex(data[o:last])))


def dumpblock_62ab11c4(data, first, last):
    # gpu / shader code
    o = first
    code1len, n = getuint32(data, o, last) ; o += n
    code1text = data[o:o+code1len] ; o += code1len
    zero1, n = getuint8(data, o, last) ; o += n
    code1text = code1text.decode("utf-8", "ignore")

    code2len, n = getuint32(data, o, last) ; o += n
    code2text = data[o:o+code2len] ; o += code2len
    zero2, n = getuint8(data, o, last) ; o += n
    code2text = code2text.decode("utf-8", "ignore")

    nvars, n = getuint32(data, o, last) ; o += n
    varlist = []
    for _ in range(nvars):
        varlen, n = getuint32(data, o, last) ; o += n
        varname = data[o:o+varlen] ; o += varlen
        varname = varname.decode('utf-8', 'ignore').rstrip("\x00")

        var, n = getvariableinit(data, o, last) ; o += n
        varlist.append((varname, var))

    print("----code1\n%s\n----code2\n%s\n----vars" % (code1text, code2text))
    print(varlist)
    if o!=last:
        print(b2a_hex(data[first:last]))
        print("WARNING: %d bytes left after 62ab11c4" % (last-o))

def dumpblock_c61d838d(data, first, last):
    # html
    o = first
    code1len, n = getuint32(data, o, last) ; o += n
    code1text = data[o:o+code1len] ; o += code1len
    zero1, n = getuint8(data, o, last) ; o += n
    code1text = code1text.decode("utf-8", "ignore").rstrip("\x00")

    print("---- (html)\n%s\n----" % (code1text))

    if o!=last:
        print("WARNING: %d bytes left after c61d838d" % (last-o))


def dumpblock_2544f997(data, first, last):  # color related
    if verbose:
        print("---- (colors?)")
        hexdump(data, first, last)

def dumpblock_3521f539(data, first, last):  # bitmap ?
    o = first
    w = struct.unpack_from("<L5HB4HL", data, o) ; o += 27
    print("--- bitmap? : %08x %04x %04x %04x %04x %04x %02x %04x cols:%04x rows:%04x %04x %08x" % w)
    if verbose:
        print(" (%8x: %8x) %s" % (last-o, w[8]*w[9]*4, b2a_hex(data[o:last])))

def dumpblock_81c24cbe(data, first, last):
    #  00 10 00 00 00 10 08 00 00 00
    if verbose:
        print("---- ???")
        hexdump(data, first, last)

def dumpblock_89546ed9(data, first, last):
    if verbose:
        print("---- ???")
        hexdump(data, first, last)

def dumpblock_c6133cad(data, first, last):
    if verbose:
        print("---- ???")
        hexdump(data, first, last)

def dumpblock_d5610dab(data, first, last):   # vorbis
    if verbose:
        print("---- audio / vorbis")
        hexdump(data, first, last)

def dumpblock_d569853c(data, first, last):
    if verbose:
        print("---- ???")
        hexdump(data, first, last)

def dumpblock_e1ccaf5c(data, first, last):
    print("--- ???")
    o = first
    nr, n = getuint32(data, o, last) ; o += n
    for _ in range(nr):
        w = struct.unpack_from("<11L", data, o) ; o += 44
        print(w, end="; ")
    print()

def dumpblock_e1ccafe2(data, first, last):
    o = first
    one, mg1, mg2, nr = struct.unpack_from("<LLLL", data, o) ; o += 16
    print("3d: %08x %08x %08x #%d items" % (one, mg1, mg2, nr))
    for _ in range(nr):
        mg3, nul, nrpt = struct.unpack_from("<LLL", data, o) ; o += 12
        nra, b = struct.unpack_from("<BB", data, o) ; o += 2
        aa = struct.unpack_from("<%dB" % nra, data, o) ; o += nra

        ids = struct.unpack_from("<%dH" % nrpt, data, o) ; o += nrpt*2
        coord = struct.unpack_from("<%df" % (nrpt*4*nra), data, o) ; o += nrpt*16*nra

        print("  obj#%d: %08x %08x #%d pts (%d,%d,%s) : %s" % (_, mg3, nul, nrpt, nra, b, aa, ids))
        for _ in range(nrpt):
            print("    (%12.8f, %12.8f, %12.8f)" % coord[3*_:3*_+3])
    if o!=last:
        print("WARNING: %d bytes left after 3d objects" % (last-o))


def dumpblock(data, magicnum, first, last):
    o = first

    blocksize, n = getuint32(data, o, last) ; o += n
    if blocksize==0:
        print("%06x: EOF %s" % (first, b2a_hex(data[o:])))
        return o-first

    last = first + blocksize

    blockcheck, n = getuint32(data, o, last) ; o += n

    print("%06x: BLOCK_%08x %08x %08x" % (first, magicnum, blocksize, blockcheck))

    handler = globals().get("dumpblock_%08x" % magicnum, None)
    if handler:
        try:
            handler(data, o, first+blocksize)
        except Exception as e:
            print("ERROR in block @%08x type %08x: %s" % (o, magicnum, e))
            raise
    return blocksize

def dumpsection(data, first, last):
    o = first
    magicnum, n = getuint32(data, o, last) ; o += n    # see below, determines content
    nblocks, n = getuint32(data, o, last) ; o += n
    bb = data[o:o+2]  ; o += 2    # always 01 01

#   351 SECT 2017 BLOCKS 2544f997 -- short: 01 00050000 00000000
#                     -- long:  00 00050000 00000000 00000000 ffcccccc ffa3a3a3 0a7f7f7f 00000004 00000000 00000000 00000000 00000000 000000000000
#   103 SECT  203 BLOCKS 3521f539
#     7 SECT  645 BLOCKS 62ab11c4  -- gpu code   -- len:text, len:text, count: [ len:text, len:floats ]
#   359 SECT 1961 BLOCKS 89546ed9
#     1 SECT    4 BLOCKS 9b0704c1  -- (font) path names : zstr
#    38 SECT  191 BLOCKS c6133cad  -- in 3d file
#     4 SECT  117 BLOCKS c61d838d  -- html
#     2 SECT  392 BLOCKS d5610dab  -- audio
#    61 SECT  110 BLOCKS e1ccaf5c
#    59 SECT  153 BLOCKS e1ccafe2  -- 3d data
#    37 SECT  121 BLOCKS f67cbd74  -- db table
#       SECT             81c24cbe  -- old audio data ( in sound_main file )
#       SECT             d569853c  -- old audio data ( in sound_main file )

    print("%06x: SECT %08lx [%3d blocks]" % (first, magicnum, nblocks))

    for _ in range(nblocks):
        try:
            n = dumpblock(data, magicnum, o, last) ; o += n
        except Exception as e:
            print("ERROR %s in block" % e)
            raise
            blksize, n = getuint32(data, o, last)
            o += blksize

    return o-first

def dumpsections(data, first, last):
    o = first
    totalsize, n = getuint32(data, o, last) ; o += n
    sectcount, n = getuint32(data, o, last) ; o += n

    print("%06x: HDR %08lx [%2d sections]" % (first, totalsize, sectcount))

    newlast = first + totalsize

    for _ in range(sectcount):
        if o>=newlast:
            break
        try:
            n = dumpsection(data, o, newlast) ; o += n
        except Exception as e:
            print("ERROR in section: %s" % e)
            raise
            break

    zero, n = getuint32(data, o, last) ; o += n
    if zero:
        print("WARNING: last word not zero: %08x" % zero)
    if o!=last:
        print("WARNING: %d bytes left after sections" % (last-o))
    return o-first

def processfile(data, first, last):
    o = first

    prefix = data[o:o+10]  ; o += 10      # "3d 03 07 0[01] 00 00 87 e0 81 80" 
    nlen, n = getuint32(data, o, last) ; o += n
    dbname = data[o:o+nlen-9].decode('utf-8', 'ignore') ; o += nlen-9
    ignore = data[o:o+9]  ; o += 9  # always starts with: 00 00 00 00 00 77 21 3c dc

    print("%06x: FILE '%s'" % (first, dbname))

    n = dumpsections(data, o, last) ; o += n

    if o!=last:
        print("WARNING: %d bytes left in file" % (last-o))


def main():
    import sys
    i = 1
    if sys.argv[i] == '-v':
        global verbose
        verbose = True
        i += 1
    filelist = sys.argv[i:]

    for fn in filelist:
        print("==>", fn, "<==")
        try:
            with open(fn, "rb") as fh:
                data = fh.read()
                processfile(data, 0, len(data))
        except Exception as e:
            raise
            print("ERROR: %s" % e)

if __name__ == '__main__':
    main()

