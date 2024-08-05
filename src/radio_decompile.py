import sys
import json
import os
import textwrap

from gcx import GclNode, GcxData, DatFile
from gcl_decompile import GclDecomp
from constants import RadioCode

class RadioDecomp():
    ''' Decompile radio.dat file '''

    def __init__(self, gcx: GcxData, padding=True, vox_files={}) -> None:

        self.gcx = gcx
        self.gcl_decomp = GclDecomp( gcx )
        self.tree_data = []
        self.is_pc_version = False
        self.vox_files = vox_files
        self.dialog_files = []
        self.padding = padding

        self.decompile_radio_file()
        self.resolve_dialog_filenames()

    def export_script(self):
        ''' Export script to file '''

        script = ''
        for elem in self.tree_data:
            dialog = elem['DIALOG']
            script += 'frequency: %.2f, ' % ( dialog['FREQ'] / 100 )
            script += 'face_size: %d, ' % dialog['FACE_SIZE']
            script += 'face_offset: %d ' % dialog['FACE_OFFSET']
            script += self.decomp_script( dialog['DATA'] )
            script += '\n'

        with open('radio.gcl', 'w', encoding='utf-8') as f:
            f.write( script )

    def resolve_dialog_filenames(self):
        ''' Attempt to retrieve the original dialog file names from VOX file names '''

        extra_count = 0
        names = {}
        for i, elem in enumerate( self.tree_data ):
            dialog = elem['DIALOG']['DATA']

            # Browse dialog to identify lowest scene id from voice filename(.vox).
            self.lowest_vox_id = -1
            def find_lowest_id(node_type, node_value):
                if node_type == RadioCode.VOICE.name:
                    voice_name, _ = node_value.get()
                    try:
                        voice_code = int( voice_name[2:].replace('.vox', ''), 16 )
                        if self.lowest_vox_id == -1 or self.lowest_vox_id < voice_code:
                            self.lowest_vox_id = voice_code
                    except:
                        pass
            dialog.browse( find_lowest_id )

            if self.lowest_vox_id == -1:
                extra_count += 1
                name = 'RD_EXTRA_%0d' % extra_count
            else:
                vc = '%08X' % ( self.lowest_vox_id << 8 )
                major_scene_id = vc[0:2]
                minor_scene_id = vc[2:3]
                # Uppercase identifier character.
                minor_scene_letter = ''
                letter_value = int( vc[3:4] )
                if letter_value > 0:
                    minor_scene_letter = chr( ord('A') + letter_value - 1 )
                name = 'RD_%s_%s%s' % ( major_scene_id, minor_scene_id, minor_scene_letter )
            # Lowercase identifier character.
            if name in names:
                if not isinstance( names[name], int ):
                    names[name]['NAME'] = names[name]['NAME'] + 'a'
                    names[name] = 0
                names[name] += 1
                if names[name] > 26:
                    name += '_' + str( i )
                else:
                    name += chr( ord('a') + names[name] )
            else:
                names[name] = elem['DIALOG']
            elem['DIALOG']['NAME'] = name.rstrip()

    def export_json_files(self, output_dir):
        ''' Export a json file for each dialog in the output directory '''

        for elem in self.tree_data:
            dialog = elem['DIALOG']
            dialog_file = os.path.join( output_dir, dialog['NAME'] )
            os.makedirs( output_dir, exist_ok=True )
            with open( dialog_file, 'w', encoding='utf-8' ) as f:
                f.write( json.dumps( dialog ) )

    def to_json(self, indent=None) -> str:
        ''' Return decompiled data in json format '''

        return json.dumps( self.tree_data, indent=indent )

    def to_json_files(self, indent=None) -> list:
        ''' Return list of json files '''

        files = []
        for elem in self.tree_data:
            dialog = elem['DIALOG']
            files.append( DatFile( dialog['NAME'],
                                   dialog['OFFSET'],
                                   json.dumps( dialog, indent=indent ) ) )
        return files

    def to_gcl_script(self) -> str:
        ''' Return decompiled data in gcl script format '''

        gcl = ''
        for elem in self.tree_data:
            gcl += self.decomp_script( elem )
        return gcl

    def decompile_radio_file(self):
        ''' Decompile radio file '''

        file_size = len( self.gcx )

        while self.gcx.offset < file_size:

            dialog_offset = self.gcx.offset

            frequency = self.gcx.read_short()
            # In game, face size and offset is read as int and splitted with binary operations.
            face_size = self.gcx.read_byte()
            self.gcx.offset += 1
            face_offset = self.gcx.read_short()
            flags = self.gcx.read_short() # Always 0

            # Dialog data need to be processed after fonts so we save offset.
            dialog_data_offset = self.gcx.offset
            dialog_data_size = self.gcx.read_short( self.gcx.offset + 1 )
            self.gcx.offset += dialog_data_size + 1

            fonts = []
            while self.gcx.offset < file_size:
                val = 0
                font_offset = self.gcx.offset
                for i in range( 36 ):
                    # All fonts glyphs ends with three 0's except one font that ends with 001400.
                    if i >= 33 and self.gcx.read_byte( self.gcx.offset ) != 0 \
                               and self.gcx.read_byte( self.gcx.offset ) != 0x14:
                        self.gcx.offset -= i
                        val = 0
                        break
                    if self.gcx.offset + 1 == len( self.gcx ):
                        self.gcx.offset -= i
                        val = 0
                        break
                    val += self.gcx.read_byte()
                if val == 0:
                    break
                self.gcx.offset = font_offset
                font = self.gcx.read_hex_string( 36 )
                fonts.append( font )
            self.current_fonts = fonts

            # Now go back for decompiling dialog data.
            fonts_end_offset = self.gcx.offset
            self.gcx.offset = dialog_data_offset
            dialog_data = self.decompile()
            self.gcx.offset = fonts_end_offset

            if self.padding:
                self.gcx.offset += ( 0x800 - ( self.gcx.offset % 0x800 ) )

            dialog = GclNode({
                'OFFSET':      dialog_offset, # Shouldn't be needed.
                'FREQ':        frequency,
                'FACE_SIZE':   face_size,
                'FACE_OFFSET': face_offset,
                'FLAGS':       flags,
                'DATA':        dialog_data,
                'FONTS':       fonts,
                'NAME':        'rd_%03d' % ( int(dialog_offset / 0x800) )
            })
            self.tree_data.append( GclNode({ 'DIALOG': dialog }) )
            self.dialog_files.append( DatFile( dialog['NAME'], dialog_offset, self.gcx[dialog_offset:self.gcx.offset] ) )

    def decomp_block(self, size, callback) -> list:
        ''' Decompile data block using callback '''

        data = []
        end_offset = self.gcx.offset + size
        while self.gcx.offset < end_offset:
            data.append( callback() )
        return data

    def decompile(self) -> GclNode:
        ''' Build json tree AST from radio data '''

        radio_code = self.gcx.read_byte()

        if radio_code == RadioCode.ENDLINE.value:
            return GclNode({ RadioCode( radio_code ).name: 0 })

        size = self.gcx.read_short() - 2

        match radio_code:

            case RadioCode.TALK.value:
                chara = self.gcx.read_short()
                anim = self.gcx.read_short()
                unk = self.gcx.read_short()
                text = self.gcx.read_string( fonts=self.current_fonts )
                value = [ chara, anim, unk, text ]

            case RadioCode.VOICE.value:

                voice_code = self.gcx.read_int()
                # PC VOX filename
                if voice_code >> 24 == 0xfc:
                    voice_name = 'vc%06x' % ( voice_code & 0xffffff )
                # PSX VOX offset in VOX.DAT
                else:
                    voice_name = next((vox_file.name for vox_file in self.vox_files if vox_file.block_index == voice_code), '')
                    if voice_name == '':
                        print('Error: could not resolve voice code', hex(voice_code))
                        sys.exit(1)
                voice_data = self.decomp_block( size - 4, self.decompile )
                value = GclNode({ voice_name: voice_data })

            case RadioCode.ANIM.value:
                chara = self.gcx.read_short()
                anim = self.gcx.read_short()
                unk = self.gcx.read_short()
                value = [ chara, anim, unk ]

            case RadioCode.ADD_CONTACT.value:
                frequency = str( self.gcx.read_short() )
                name = self.gcx.read_string()
                value = GclNode({ frequency: name })

            case RadioCode.MEMSAVE.value:
                value = self.decomp_block( size - 1, self.gcl_decomp.decompile_gcx )
                if self.gcx.read_byte() != 0:
                    print('Error: MEMSAVE expected null')
                    sys.exit(1)

            case RadioCode.SOUND.value:
                value = self.gcx.read_hex_string( size )

            case RadioCode.PROMPT.value:
                value = self.decomp_block( size - 1, self.gcl_decomp.decompile_gcx )
                if self.gcx.read_byte() != 0:
                    print('Error: PROMPT expected null')
                    sys.exit(1)

            case RadioCode.VARSAVE.value:
                value = self.decomp_block( size - 1, self.gcl_decomp.decompile_gcx )
                if self.gcx.read_byte() != 0:
                    print('Error: VARSAVE expected null')
                    sys.exit(1)

            case RadioCode.IF.value:
                end_offset = self.gcx.offset + size
                value = []
                value.append( self.gcl_decomp.decompile_gcx() )
                value.append( self.decompile() )
                while self.gcx.offset < end_offset - 1:
                    arg_value = []
                    code  = self.gcx.read_byte()
                    match code:
                        case RadioCode.ELSEIF.value:
                            arg_value.append( self.gcl_decomp.decompile_gcx() )
                            arg_value.append( self.decompile() )
                            value.append( GclNode({ RadioCode( code ).name: arg_value }) )
                        case RadioCode.ELSE.value:
                            arg_value.append( self.decompile() )
                            value.append( GclNode({ RadioCode( code ).name: arg_value }) )
                        case _:
                            self.gcx.offset -= 1
                            value.append( self.decompile() )

                if self.gcx.read_byte() != 0:
                    print('Error: IF expected null', hex(self.gcx.offset))
                    sys.exit(1)

            case RadioCode.SWITCH.value:

                # Not yet implemented, never used by the game anyway...
                #match code:
                #    case RadioCode.SWITCH_CASE.value:
                #    case RadioCode.SWITCH_DEFAULT.value:
                pass

            case RadioCode.RANDSWITCH.value:

                end_offset = self.gcx.offset + size
                switch_value = str( self.gcx.read_short() )
                switch_cases = []
                while self.gcx.offset < end_offset - 1:
                    if self.gcx.read_byte() != RadioCode.RANDSWITCH_CASE.value:
                        print('Error: Unexpected code in randswitch',
                              hex(self.gcx.offset), end_offset - self.gcx.offset )
                        sys.exit(1)
                    case_value = str( self.gcx.read_short() )
                    case_data = self.decompile()
                    switch_cases.append( GclNode({ case_value: case_data }) )
                if self.gcx.read_byte() != 0:
                    print('Error: Missing null after radio randswitch block')
                    sys.exit()
                value = GclNode({ switch_value: switch_cases })

            case RadioCode.EVAL.value:

                value = self.gcl_decomp.decompile_gcx()

            case RadioCode.RD_SCRIPT.value:

                value = self.decomp_block( size - 1, self.decompile )
                if self.gcx.read_byte() != 0:
                    print('Error: Missing null after radio script block')
                    sys.exit()

            case RadioCode.ENDLINE.value:

                value = '\n'

            case _:
                print(f'Error: unexpected radio code (RadioCode: {radio_code}, offset: {hex(self.gcx.offset)})')
                sys.exit(1)

        return GclNode({ RadioCode( radio_code ).name: value })

    def indent_text(self, text) -> str:
        ''' Indent text block '''

        return textwrap.indent( text, 4 * ' ' )

    def decomp_script(self, node) -> str:
        ''' Return tree data converted to gcl script '''

        s = ''

        if isinstance(node, list):
            for elem in node:
                s += self.decomp_script( elem )
            return s

        node_type, value = node.get()

        match node_type:

            case RadioCode.TALK.name:

                s += '%04X %04X %d "%s"' % ( value[0], value[1], value[2], value[3] )

            case RadioCode.VOICE.name:

                voice_code, voice_data = value.get()
                s += '%s ' % ( str(voice_code) )
                s += self.decomp_script( voice_data )

            case RadioCode.ANIM.name:

                s += '%04X %04X %d' % ( value[0], value[1], value[2] )

            case RadioCode.ADD_CONTACT.name:

                contact_freq, contact_name = value.get()
                s += '%.3f %s' % ( int( contact_freq ) / 100, contact_name )

            case RadioCode.MEMSAVE.name:

                for val in value:
                    s += '%s' % ( self.gcl_decomp.decomp_script( val ) )

            case RadioCode.SOUND.name:

                s += '%s' % ( value )

            case RadioCode.PROMPT.name:

                s += '%s %s' % ( self.gcl_decomp.decomp_script( value[0] ),
                                 self.gcl_decomp.decomp_script( value[1] ) )

            case RadioCode.VARSAVE.name:

                for variable in value:
                    s += '%s' % ( self.gcl_decomp.decomp_script( variable ) )

            case RadioCode.IF.name:

                s += '%s ' % ( self.gcl_decomp.decomp_script( value[0] ) )
                for elem in value[1:]:
                    s += '%s' % ( self.decomp_script( elem ) )

            case RadioCode.ELSE.name:

                s += self.decomp_script( value )

            case RadioCode.ELSEIF.name:

                s += '%s ' % ( self.gcl_decomp.decomp_script( value[0] ) )
                s += self.decomp_script( value[1] )

            case RadioCode.SWITCH.name:

                pass

            case RadioCode.RANDSWITCH.name:

                switch_value, switch_cases = value.get()
                s += '%d:\n' % ( int( switch_value ) )
                for case in switch_cases:
                    case_value, case_data = case.get()
                    case_str = 'case %d: %s\n' % ( int( case_value ), self.decomp_script( case_data ) )
                    s += self.indent_text( case_str )

            case RadioCode.EVAL.name:

                s += '%s' % ( self.gcl_decomp.decomp_script( value ) )

            case RadioCode.RD_SCRIPT.name:

                script = ''
                for command in value:
                    script += self.decomp_script( command )

                s += '{' + self.indent_text( script ) + '\n}'
                return s

            case RadioCode.ENDLINE.name:

                s += '\n'
                return s

        return '%s %s' % ( RadioCode[node_type].name.lower(), s )
