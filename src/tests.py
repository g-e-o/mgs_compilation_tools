import os
import sys
import hashlib
from timeit import default_timer as timer

from gcl_decompile import GclDecomp
from gcl_compile import GclComp
from radio_decompile import RadioDecomp
from radio_compile import RadioComp
from gcx import GcxData
from voice_unpacker import VoiceUnpacker
from demo_unpacker import DemoUnpacker

class Test():
    ''' Test if recompiled gcx files matches '''

    def __init__(self) -> None:

        self.start_time = timer()
        self.total_files_tested = 0
        self.total_bytes_matched = 0
        self.total_success = 0
        self.padding = True

    def __del__(self):

        print('----------------------------------------')
        print('Tests completed in %.1f seconds.' % (self.elapsed()))
        print('  - %d/%d files matched.' % (self.total_success, self.total_files_tested))
        print('  - %.2f mb matched.' % (self.total_bytes_matched / 1000000))
        print('----------------------------------------')

    def test(self, mgs_path, padding=True):
        ''' Tests to perform '''

        self.padding = padding
        self.test_all( os.path.join( mgs_path, 'stage' ),
                       os.path.join( mgs_path, 'RADIO.DAT' ) )

    def elapsed(self):
        ''' Return elapsed time '''
        return timer() - self.start_time

    def test_all(self, stage_path, radio_path):
        ''' Decompile every .gcx files as well as radio.dat
            file and check if recompiled files matches original ones '''

        # Unpack DEMO.DAT if found
        demo_path = radio_path.replace('RADIO.DAT', 'DEMO.DAT').replace('radio.dat', 'demo.dat')
        demo_files = []
        if os.path.isfile( demo_path ):
            print('%.1f Unpacking %s...' % (self.elapsed(), os.path.basename(demo_path)))
            demo_decomp = DemoUnpacker()
            demo_decomp.unpack( demo_path )
            demo_files = demo_decomp.demo_files
            # Repack demo files
            print('%.1f Repacking %s...' % (self.elapsed(), os.path.basename(demo_path)))
            demo_recomp = DemoUnpacker()
            demo_recomp.pack( demo_decomp.demo_files )
            success = self.isMatching( demo_decomp, demo_recomp )
            print('\033[%sm%.1f %s\033[0m' % ('92' if success else '91', self.elapsed(), demo_path))

        # Unpack VOX.DAT if found
        vox_path = radio_path.replace('RADIO.DAT', 'VOX.DAT').replace('radio.dat', 'vox.dat')
        vox_files = []
        if os.path.isfile( vox_path ):
            print('%.1f Unpacking %s...' % (self.elapsed(), os.path.basename(vox_path)))
            voice_decomp = VoiceUnpacker()
            voice_decomp.unpack( vox_path )
            vox_files = voice_decomp.vox_files
            # Repack vox files
            print('%.1f Repacking %s...' % (self.elapsed(), os.path.basename(vox_path)))
            voice_recomp = VoiceUnpacker()
            voice_recomp.pack( voice_decomp.vox_files )
            success = self.isMatching( voice_decomp, voice_recomp )
            print('\033[%sm%.1f %s\033[0m' % ('92' if success else '91', self.elapsed(), vox_path))

        # Decompile RADIO.DAT
        print('%.1f Decompiling %s...' % (self.elapsed(), os.path.basename(radio_path)))
        radio_decomp = RadioDecomp( GcxData( radio_path ), padding=self.padding, vox_files=vox_files )

        # Recompile radio data
        radio_comp = RadioComp( padding=self.padding, vox_files=vox_files )
        print('%.1f Recompiling %s...' % (self.elapsed(), os.path.basename(radio_path)))
        radio_comp.compile_radio_file( radio_decomp.tree_data )
        success = self.isMatching( radio_decomp, radio_comp )
        print('\033[%sm%.1f %s\033[0m' % ('92' if success else '91', self.elapsed(), radio_path))
        self.total_success += int(success)
        self.total_files_tested += 1

        # Decompile GCX files from stage directory
        for subdir, dirs, files in os.walk( stage_path ):
            for file in files:
                if file.endswith( '.gcx' ):
                    gcx_file = os.path.join( subdir, file )
                    decomp = GclDecomp( GcxData( gcx_file ), radio=radio_decomp, vox_files=vox_files, demo_files=demo_files )
                    decomp.decompile_gcx_file()
                    recomp = GclComp( radio=radio_comp, vox_files=vox_files, demo_files=demo_files )
                    # Recompile gcl data
                    recomp.compile_gcl_file( decomp.tree_data )
                    success = self.isMatching( decomp, recomp )
                    print('\033[%sm%.1f %s\033[0m' % ('92' if success else '91', self.elapsed(), gcx_file))
                    self.total_success += int(success)
                    self.total_files_tested += 1

    def isMatching(self, decomp, recomp, compare=True):

        decomp_hash = hashlib.sha256( decomp.gcx ).hexdigest()
        recomp_hash = hashlib.sha256( recomp.gcx ).hexdigest()
        if decomp_hash != recomp_hash:
            if compare:
                self.compare( decomp, recomp )
            return False
        return True

    def compare(self, decomp, recomp):
        ''' Compare a decompiled file with a recompiled file '''

        decomp.gcx.offset = 0
        recomp.gcx.offset = 0

        error_index = 0
        for offset in range( len(decomp.gcx) ):
            if offset >= len(recomp.gcx):
                self.hexdump( offset, decomp.gcx, isValid=True )
                self.hexdump( offset, recomp.gcx, isValid=False )
                print('')
                print('\033[95mError: recompiled file too short (off:%x decomp_len:%x comp_len:%x)\033[0m' \
                    % (offset, len(decomp.gcx), len(recomp.gcx) ))
                #sys.exit(1)
                return False
            if decomp.gcx.read_byte(offset) != recomp.gcx.read_byte(offset):
                error_index += 1
                if error_index <= 1:
                    continue
                self.hexdump( offset, decomp.gcx, isValid=True )
                self.hexdump( offset, recomp.gcx, isValid=False )
                print('')
                print('\033[91mError: byte does not matches (off:%x decomp_byte:%x comp_byte:%x)\033[0m' \
                    % (offset, decomp.gcx.read_byte(offset), recomp.gcx.read_byte(offset)))
                #sys.exit(1)
                return False
        if len(decomp.gcx) != len(recomp.gcx):
            print('\033[91mError: file sizes does not matches (decomp:%x, recomp:%x)\033[0m' \
                  % (len(decomp.gcx), len(recomp.gcx)))
            #sys.exit(1)
            return False
        self.total_bytes_matched += len(decomp.gcx)
        return True

    def hexdump(self, offset, gcx_data: GcxData, backward=16, forward=32, isValid=True):
        ''' Hex view for debugging non matching gcx '''

        fg_color = '\033[92m' if isValid else '\033[91m'
        bg_color = '\033[42m' if isValid else '\033[91m'
        print('%s――――――――――――――――――――――――――――――――――――――――――――――――――――――――\033[0m' % fg_color)

        # Adjust start offset
        off = offset
        loop_min = backward
        while offset - off < loop_min or off % 16 != 0:
            if off <= 0:
                break
            backward += 1
            if forward <= 0:
                pass
            else:
                forward -= 1
            off -= 1

        # Print offsets and bytes
        gcx_data.offset = off
        s = ''
        for i in range(backward + forward + 1):
            if gcx_data.offset >= len(gcx_data):
                print('%s >' % ( s ))
                s = ''
                break
            # Offset
            if i % 16 == 0:
                offset_color = fg_color if offset - gcx_data.offset >= 0 and offset - gcx_data.offset < 16 else ''
                s += '%s%5X\033[0m:' % (offset_color, gcx_data.offset)
            # Space in the middle
            if i % 8 == 0:
                s += ' '
            # Non matching byte
            if i + off == offset:
                s += ' %s%02X\033[0m' % ( bg_color, gcx_data.read_byte() )
            # Bytes after non matching
            elif gcx_data.offset > offset:
                s += ' %s%02X\033[0m' % ( '\033[90m', gcx_data.read_byte() )
            # Matching bytes
            else:
                s += ' %02X' % gcx_data.read_byte()
            if (i+1) % 16 == 0:
                print(s)
                s = ''
        if s != '':
            print(s)
