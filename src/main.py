import os
import json
import sys
import signal
import argparse

from tests import Test
from radio_decompile import RadioDecomp
from radio_compile import RadioComp
from gcx import GcxData, DatFile, GclNode
from gcl_decompile import GclDecomp
from gcl_compile import GclComp
from demo_unpacker import DemoUnpacker
from voice_unpacker import VoiceUnpacker

# Don't print stack trace when using CTRL+C.
def signal_handler(sig, frame):
    print( 'Program stopped.' )
    sys.exit( 0 )
signal.signal( signal.SIGINT, signal_handler )

class Main():
    ''' Main class '''

    def __init__(self) -> None:

        self.init_args()
        self.process_args()

    def init_args(self):
        ''' Init parser '''
        self.parser = argparse.ArgumentParser(
            prog='MGS1_COMPILATION_TOOLS',
            description='Decompile/recompile MGS1 game files.'
        )
        group = self.parser.add_mutually_exclusive_group( required=True )
        group.add_argument('-t', '--test', metavar='path', nargs='+',
                            help='decompile/recompile game files from directory' \
                                 ' and check if recompiled files matches')
        group.add_argument('-d', '--decompile', metavar='path',
                            help='decompile game files from directory')
        group.add_argument('-c', '--compile', metavar='path',
                            help='compile game files from directory')
        self.parser.add_argument('-o', '--output', metavar='path',
                            help='output directory for exporting decompiled/recompiled files')
        self.parser.add_argument('--padding', action=argparse.BooleanOptionalAction, default=True,
                            help='add padding for radio dialogs inside RADIO.DAT')
        self.args = self.parser.parse_args()

    def check_path(self, path):
        ''' Check if provided path is valid '''
        if isinstance( path, list ):
            for p in path:
                self.check_path( p )
        elif not os.path.isdir( path ):
            print('Error: provided path "%s" is not a valid directory' % path)
            self.parser.print_usage()
            sys.exit(1)
        elif self.args.test is None and self.args.output is None:
            print('Error: missing OUTPUT path argument.')
            self.parser.print_usage()
            sys.exit(1)
        return True

    def process_args(self):
        ''' Process args '''
        if self.args.test is not None and self.check_path( self.args.test ):
            self.test_mgs_path( self.args.test )
        elif self.args.decompile is not None and self.check_path( self.args.decompile ):
            self.decompile( self.args.decompile, self.args.output )
        elif self.args.compile is not None and self.check_path( self.args.compile ):
            self.compile( self.args.compile, self.args.output )

    def test_mgs_path(self, input_paths):
        ''' Test all provided paths '''
        tests = Test()
        for input_path in input_paths:
            print( '- Testing "%s":' % (input_path) )
            tests.test( input_path, padding=self.args.padding )

    def decompile(self, input_path, output_dir):
        ''' Decompile game files '''

        print( '- Decompiling "%s" to "%s"' % (input_path, output_dir) )

        # Unpack DEMO.DAT and VOX.DAT
        demo_files = self.unpack( os.path.join( input_path, 'DEMO.DAT' ),
                                  os.path.join( output_dir, 'DEMO' ) )
        vox_files = self.unpack( os.path.join( input_path, 'VOX.DAT' ),
                                 os.path.join( output_dir, 'VOX' ) )

        # Decompile RADIO.DAT
        print( 'Decompiling radio...')
        radio = RadioDecomp( GcxData( os.path.join( input_path, 'RADIO.DAT' ) ),
                             padding=self.args.padding,
                             vox_files=vox_files )
        dialog_files = radio.to_json_files()
        radio_dir = os.path.join( output_dir, 'RADIO' )
        if not os.path.isdir( radio_dir ):
            os.makedirs( radio_dir )
        for dialog_file in dialog_files:
            file_path = os.path.join( radio_dir, dialog_file.name )
            with open( file_path + '.json', 'w', encoding='utf-8' ) as f:
                f.write( dialog_file.data )

        # Decompile GCX files from stage directory
        stage_dir = os.path.join( output_dir, 'STAGE' )
        if not os.path.isdir( stage_dir ):
            os.makedirs( stage_dir )
        for subdir, _dirs, files in os.walk( os.path.join( input_path, 'STAGE' ) ):
            for file in files:
                if file.endswith( '.gcx' ):
                    gcx_file = os.path.join( subdir, file )
                    print('Decompiling gcx file: "%s"' % gcx_file)
                    gcl = GclDecomp( GcxData( gcx_file ),
                                     radio=radio,
                                     vox_files=vox_files,
                                     demo_files=demo_files )
                    gcl.decompile_gcx_file()
                    file_path = gcx_file.replace( input_path, output_dir ) \
                                        .replace( 'a242.gcx', 'demo.gcx' ) \
                                        .replace( 'ea54.gcx', 'scenerio.gcx' ) \
                                        .replace( '.gcx', '' )
                    if not os.path.isdir( os.path.dirname( file_path ) ):
                        os.makedirs( os.path.dirname( file_path ) )
                    with open( file_path + '.json', 'w', encoding='utf-8' ) as f:
                        f.write( gcl.to_json() )

    def compile(self, input_path, output_dir):
        ''' Compile game files '''

        print( '- Compiling "%s" to "%s"' % (input_path, output_dir) )

        # Pack demo and vos files
        demo_files = self.pack( os.path.join( input_path, 'DEMO' ),
                                os.path.join( output_dir, 'DEMO.DAT' ) )
        vox_files = self.pack( os.path.join( input_path, 'VOX' ),
                               os.path.join( output_dir, 'VOX.DAT' ) )

        # Compile dialog files
        print( 'Compiling radio...')
        radio = RadioComp( vox_files=vox_files )
        radio_dir = os.path.join( input_path, 'RADIO' )
        radio_data = []
        for dialog_file in os.listdir( radio_dir ):
            json_data = self.read_json_file( os.path.join( radio_dir, dialog_file ) )
            radio_data.append( GclNode({ 'DIALOG': json_data }) )
        radio.compile_radio_file( radio_data )
        with open( radio_dir.replace( input_path, output_dir ) + '.DAT', 'wb' ) as f:
            f.write( radio.gcx )

        # Compile gcl files
        for subdir, _dirs, files in os.walk( os.path.join( input_path, 'stage' ) ):
            for file in files:
                if file.endswith( '.json' ):
                    gcl_file = os.path.join( subdir, file )
                    print('Compiling gcl file: "%s"' % gcl_file)
                    gcl = GclComp( radio=radio, vox_files=vox_files, demo_files=demo_files )
                    gcl.compile_gcl_file( self.read_json_file( gcl_file ) )
                    file_path = gcl_file.replace( input_path, output_dir ) \
                                        .replace( 'demo.json', 'a242.json' ) \
                                        .replace( 'scenerio.json', 'ea54.json' ) \
                                        .replace( '.json', '' )
                    if not os.path.isdir( os.path.dirname( file_path ) ):
                        os.makedirs( os.path.dirname( file_path ) )
                    with open( file_path + '.gcx', 'wb' ) as f:
                        f.write( gcl.gcx )

        #import hashlib
        #input_path = 'C:/Projects/mgs_compilation_tools/gcx_files/PSX_SLPM-86247'
        #matches = 0
        #total = 0
        #not_found = 0
        #for subdir, _dirs, files in os.walk( input_path ):
        #    for file in files:
        #        input_file = os.path.join( subdir, file )
        #        output_file = os.path.join( subdir.replace('gcx_files/PSX_SLPM-86247', 'compiled/psx'), file )
        #        if not file.endswith('.DAT') and not file.endswith('.gcx'):
        #            continue
        #        if not os.path.isfile(output_file):
        #            not_found += 1
        #            print('not found', input_file, output_file)
        #            continue
        #        input_hash = ''
        #        with open(input_file, 'rb') as f:
        #            input_hash = hashlib.sha256(f.read()).hexdigest()
        #        output_hash = ''
        #        with open(output_file, 'rb') as f:
        #            output_hash = hashlib.sha256(f.read()).hexdigest()
        #        if input_hash != '' and input_hash == output_hash:
        #            matches += 1
        #        else:
        #            print('NON MATCHING', input_file, output_file)
        #        total += 1
        #print('matches %d/%d' % (matches, total))

    def read_json_file(self, json_path):
        ''' Read json file and convert it to tree data '''

        with open( json_path, 'r', encoding='utf-8' ) as f:
            data = json.loads( f.read(), object_hook=GclNode )
            if isinstance( data, dict ):
                data = GclNode( data )
        return data

    def unpack(self, dat_path, output_dir):
        ''' Unpack DAT file '''

        if not os.path.isfile( dat_path ):
            return []
        if dat_path.endswith( 'DEMO.DAT' ):
            dat_file = DemoUnpacker()
            dat_file.unpack( dat_path )
            files = dat_file.demo_files
        elif dat_path.endswith( 'VOX.DAT' ):
            dat_file = VoiceUnpacker()
            dat_file.unpack( dat_path )
            files = dat_file.vox_files
        else:
            return []

        if not os.path.isdir( output_dir ):
            os.makedirs( output_dir )
        for file in files:
            file_path = os.path.join( output_dir, file.name )
            with open( file_path, 'wb' ) as f:
                f.write( file.data )
        return files

    def pack(self, input_dir, dat_path):
        ''' Pack DAT file '''

        if not os.path.isdir( input_dir ):
            return []
        if input_dir.endswith( 'DEMO' ):
            dat_dir = DemoUnpacker()
        elif input_dir.endswith( 'VOX' ):
            dat_dir = VoiceUnpacker()
        else:
            return []

        files = []
        offset = 0
        for file in os.listdir( input_dir ):
            with open( os.path.join( input_dir, file ), 'rb' ) as f:
                data = f.read()
            files.append( DatFile( file, offset, data ) )
            offset += len( data )
            if input_dir.endswith( 'VOX' ):
                offset += 0x800 - ( offset % 0x800 )

        dat_dir.pack( files )
        if not os.path.isdir( os.path.dirname( dat_path ) ):
            os.makedirs( os.path.dirname( dat_path ) )
        with open( dat_path, 'wb' ) as f:
            f.write( dat_dir.gcx )
        return files

if __name__ == '__main__':

    Main()
