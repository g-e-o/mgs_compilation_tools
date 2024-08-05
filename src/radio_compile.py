import sys
import os
import json

from gcx import GcxData
from gcl_compile import GclComp
from constants import RadioCode

class RadioComp():
    ''' Compile radio script to GCX data '''

    gcx = GcxData()
    gcl_comp = GclComp()

    def __init__(self, vox_files=[]) -> None:

        self.gcx = GcxData()
        self.dialog_calls = {}
        self.vox_files = vox_files
        self.is_pc_version = len( vox_files ) == 0

    def compile_json_files(self, radio_dir):
        ''' Compile the dialog.json files from radio_dir '''

        for subdir, _, files in os.walk( radio_dir ):
            for file in files:
                if file.lower().startswith( 'rd_' ):
                    dialog_file = os.path.join( subdir, file )
                    with open( dialog_file, 'r', encoding='utf-8' ) as f:
                        radio_data = json.loads( f.read() )
                        self.compile_radio_file( radio_data )

    def compile_radio_file(self, node):
        ''' Compile data to RADIO.dat file '''

        data = GcxData()

        # If there is more than 500 dialogs we can assume the game has multi languages..
        has_translation = len( node ) > 500
        last_size = 0
        last_name = ''

        for dialog_index, elem in enumerate( node ):
            dialog = elem['DIALOG']
            dialog_offset = len( data )
            dialog_data = GcxData()
            dialog_data.push_short( dialog['FREQ'] )
            dialog_data.push_byte( dialog['FACE_SIZE'] )
            dialog_data.push_byte( 0 )
            dialog_data.push_short( dialog['FACE_OFFSET'] )
            dialog_data.push_short( 0 )
            dialog_data.extend( self.compile_radio( dialog['DATA'] ) )
            for glyph_image in dialog['FONTS']:
                dialog_data.push_hex_string( glyph_image )
            while (len( data ) + len( dialog_data )) % 0x800 != 0:
                dialog_data.push_byte( 0 )
            data.extend( dialog_data )

            # Prepare radio calls required for recompiling gcl files.
            # First codec call ("This is snake, ..."):
            # - SCENE 01-2B: 潜入無線機デモ (Undercover radio demo): // from screenplay
            #     int value 0x0101013B from PSX integral:
            #       - 01 * 0x800 = jap_size
            #       - 01 * 0x800 = eng_size
            #       - 013B * 0x800 = jap_offset
            #       - jap_offset + jap_size = eng_offset
            offset = int( dialog_offset / 0x800 )
            size = int( len( dialog_data ) / 0x800 )
            if has_translation:
                if ( dialog_index + 1 ) % 2 == 0:
                    call = '%02X%02X%04X' % ( last_size, size, offset - last_size )
                    self.dialog_calls[last_name] = call      # First language (jap in integral)
                    self.dialog_calls[dialog['NAME']] = call # Second language (eng in integral)
            else:
                call = '%02X%02X%04X' % ( size, 0, offset )
                self.dialog_calls[dialog['NAME']] = call
            last_size = size
            last_name = dialog['NAME']

        self.gcx.extend( data )
        return data

    def compile_radio(self, node):
        ''' Compile data to GCX '''

        data = GcxData()

        if isinstance( node, list ):
            for child in node:
                data.extend( self.compile_radio( child ) )
            return data

        radio_type, value = node.get()

        match radio_type:

            case RadioCode.TALK.name:

                data.push_short( value[0] )
                data.push_short( value[1] )
                data.push_short( value[2] )
                data.push_string( value[3] )

            case RadioCode.VOICE.name:

                voice_code, voice_data = value.get()
                if not self.is_pc_version:
                    voice_code = next((vox_file.block_index for vox_file in self.vox_files if vox_file.name == voice_code), '')
                    if voice_code == '':
                        print('Error: could not resolve voice code')
                        sys.exit(1)
                    data.push_int( voice_code )
                else:
                    voice_code = 'f' + voice_code[1:]
                    data.push_int( int( voice_code, 16 ) )
                data.extend( self.compile_radio( voice_data ) )

            case RadioCode.ANIM.name:

                data.push_short( value[0] )
                data.push_short( value[1] )
                data.push_short( value[2] )

            case RadioCode.ADD_CONTACT.name:

                frequency, name = value.get()
                data.push_short( int( frequency ) )
                data.push_string( name )

            case RadioCode.MEMSAVE.name:

                data.extend( self.gcl_comp.compile_gcl( value ) )
                data.push_byte( 0 )

            case RadioCode.SOUND.name:

                data.push_hex_string( value )

            case RadioCode.PROMPT.name:

                data.extend( self.gcl_comp.compile_gcl( value ) )
                data.push_byte( 0 )

            case RadioCode.VARSAVE.name:

                data.extend( self.gcl_comp.compile_gcl( value ) )
                data.push_byte( 0 )

            case RadioCode.IF.name:

                data.extend( self.gcl_comp.compile_gcl( value[0] ) )
                data.extend( self.compile_radio( value[1:] ) )
                data.push_byte( 0 )

            case RadioCode.ELSE.name:

                data.push_byte( RadioCode.ELSE.value )
                data.extend( self.compile_radio( value ) )
                return data

            case RadioCode.ELSEIF.name:

                data.push_byte( RadioCode.ELSEIF.value )
                data.extend( self.gcl_comp.compile_gcl( value[0] ) )
                data.extend( self.compile_radio( value[1] ) )
                return data

            case RadioCode.SWITCH.name:

                pass

            case RadioCode.RANDSWITCH.name:

                switch_value, switch_cases = value.get()
                data.push_short( int( switch_value ) )
                for case in switch_cases:
                    case_value, case_data = case.get()
                    data.push_byte( RadioCode.RANDSWITCH_CASE.value )
                    data.push_short( int( case_value ) )
                    data.extend( self.compile_radio( case_data ) )
                data.push_byte( 0 )

            case RadioCode.EVAL.name:

                data.extend( self.gcl_comp.compile_gcl( value ) )

            case RadioCode.RD_SCRIPT.name:

                script_data = GcxData()
                for elem in value:
                    script_data.extend( self.compile_radio( elem ) )

                data.extend( script_data )
                data.push_byte( 0 )

            case RadioCode.ENDLINE.name:

                data.push_byte( 0xFF )
                return data

            case _:
                print(f'Unexpected type {radio_type} while compiling radio..')
                sys.exit(1)

        _data = GcxData()
        _data.push_byte( RadioCode[ radio_type ].value )
        _data.push_short( len( data ) + 2 )
        _data.extend( data )
        return _data
